"""Voice pipeline: mic -> Silero VAD -> Deepgram Flux (STT) -> Groq (LLM) -> Deepgram Aura-2 (TTS) -> speaker.

Wires the problem bank + interview logic (see problems.py / interview.py) into the pipeline
validated in v0a: problem/persona selection, the get_current_code and escalate_to_harder_problem
tools, and session persistence (transcript + code snapshots + scorecard) on disconnect.
"""

import asyncio
import json
import time
import uuid

from fastapi import WebSocket
from loguru import logger
from pipecat.adapters.schemas.direct_function import tool_options
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import ErrorFrame, LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.services.deepgram.flux.stt import DeepgramFluxSTTService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams, FastAPIWebsocketTransport
from pipecat.workers.runner import WorkerRunner

from app import config, interview, problems

# One long-lived runner for the app's lifetime -- Pipecat's documented pattern for embedding
# in a persistent host like a FastAPI server (workers are added/removed per session).
# Constructed inside start_runner() (not at module level) because WorkerRunner() needs a
# running event loop, which doesn't exist yet at import time.
runner: WorkerRunner | None = None
_runner_task: asyncio.Task | None = None

# Live sessions, keyed by session_id, so the HTTP code-snapshot endpoint (main.py) and the
# get_current_code tool (below) can share state without any extra plumbing.
ACTIVE_SESSIONS: dict[str, dict] = {}

# Sessions created via POST /api/sessions (main.py) but not yet connected to /ws/voice -- lets
# the frontend know the exact problem selected (to render it as text) before opening the voice
# WebSocket, instead of the problem being picked (again, differently) at connect time.
PENDING_SESSIONS: dict[str, dict] = {}


async def start_runner() -> None:
    global runner, _runner_task
    # handle_sigint=False: Windows' asyncio event loop doesn't support add_signal_handler,
    # which WorkerRunner uses by default -- uvicorn already owns signal handling for the process.
    runner = WorkerRunner(handle_sigint=False)
    _runner_task = asyncio.create_task(runner.run(auto_end=False))
    logger.info("Voice pipeline WorkerRunner started")


async def stop_runner() -> None:
    await runner.cancel()
    if _runner_task:
        await _runner_task
    logger.info("Voice pipeline WorkerRunner stopped")


def _pick_initial_problem(topic: str | None, difficulty: str | None) -> dict:
    topic = topic if topic in problems.TOPICS else problems.TOPICS[0]
    difficulty = difficulty if difficulty in problems.DIFFICULTY_ORDER else problems.DIFFICULTY_ORDER[0]
    return problems.select_problem(topic, difficulty)


def _write_session_file(session: dict, transcript: list[dict], scorecard: dict | None) -> None:
    config.SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = config.SESSIONS_DIR / f"{time.strftime('%Y%m%dT%H%M%S')}-{session['session_id']}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "session_id": session["session_id"],
                "persona": session["persona"],
                "initial_problem_id": session["initial_problem_id"],
                "final_problem_id": session["current_problem"]["id"],
                "escalated": session["escalated"],
                "code_snapshots": session["code_snapshots"],
                "final_code": session["latest_code"],
                "transcript": transcript,
                "scorecard": scorecard,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    logger.info(f"Session written to {path}")


async def handle_voice_websocket(websocket: WebSocket) -> None:
    """Build and register one PipelineWorker for a single voice session."""
    query_params = websocket.query_params
    session_id = query_params.get("session_id") or str(uuid.uuid4())

    # Check for an already-active session with this id FIRST, before consuming PENDING_SESSIONS.
    # PENDING_SESSIONS.pop() is a one-time read -- without this check, a second connection for
    # the same session_id (React Strict Mode double-invoking the connect effect in dev, or a
    # real page reload reusing the session_id cached in sessionStorage) would find it already
    # consumed and silently fall back to a brand new random problem, desyncing from whatever the
    # frontend still has displayed. Reusing everything from the existing session (shallow-copied
    # into a fresh dict, not the same object, so two concurrent worker closures don't share
    # mutable state) keeps any reconnect consistent instead of randomly diverging.
    existing = ACTIVE_SESSIONS.get(session_id)
    if existing is not None:
        persona = existing["persona"]
        initial_problem = existing["current_problem"]
        session = {**existing, "llm_error_timestamps": []}
    else:
        pending = PENDING_SESSIONS.pop(session_id, None)
        if pending is not None:
            # Normal flow: frontend already called POST /api/sessions, so the problem shown on
            # screen and the problem the voice pipeline discusses are guaranteed to match.
            persona = pending["persona"]
            initial_problem = pending["problem"]
        else:
            # Fallback for direct/manual connections (e.g. quick testing) that skip the REST call.
            persona = query_params.get("persona") if query_params.get("persona") in interview.PERSONAS else "neutral"
            initial_problem = _pick_initial_problem(query_params.get("topic"), query_params.get("difficulty"))
        session = {
            "session_id": session_id,
            "persona": persona,
            "initial_problem_id": initial_problem["id"],
            "current_problem": initial_problem,
            "escalated": False,
            "latest_code": "",
            "code_snapshots": [],
            "llm_error_timestamps": [],
        }
    ACTIVE_SESSIONS[session_id] = session

    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=ProtobufFrameSerializer(),
        ),
    )

    stt = DeepgramFluxSTTService(
        api_key=config.DEEPGRAM_API_KEY,
        settings=DeepgramFluxSTTService.Settings(
            model="flux-general-en",
            eot_threshold=0.7,
            eot_timeout_ms=5000,
        ),
    )

    tts = DeepgramTTSService(
        api_key=config.DEEPGRAM_API_KEY,
        settings=DeepgramTTSService.Settings(voice="aura-2-thalia-en"),
    )

    # cancel_on_interruption=False: these are near-instant (dict lookups), and cancelling them
    # mid-flight when the candidate talks again (very common -- they're often still mid-sentence
    # right when the tool is invoked) left the result forever stuck as the "IN_PROGRESS"
    # placeholder in context, so the LLM never actually saw the real code or the escalation
    # result. See CLAUDE.md Corrections Log.
    #
    # Both tools require a real (non-optional) `reason` argument -- not just documentation, a
    # workaround for a confirmed Pipecat/Groq bug: a zero-parameter tool gets called with the
    # literal string "null" as its arguments, and Pipecat's `arguments or "{}"` guard only
    # catches an *empty* string, not "null" -- so json.loads("null") returns None, and
    # `function(**None)` crashes. Giving the schema a real parameter sidesteps the zero-argument
    # code path entirely. See CLAUDE.md Corrections Log.
    @tool_options(cancel_on_interruption=False, timeout_secs=10)
    async def get_current_code(params: FunctionCallParams, reason: str):
        """Read the candidate's current code so far, exactly as it's written in their editor.

        Call this whenever it's relevant to see what they've written -- don't ask them to read
        their code aloud.

        Args:
            reason: One short phrase for why you're checking now (e.g. "candidate said they're
                done", "checking approach so far"). Used for the session log, not spoken aloud.
        """
        logger.debug(f"get_current_code called ({reason})")
        code = session["latest_code"]
        await params.result_callback(
            {"code": code or "(the candidate hasn't written any code yet)"}
        )

    @tool_options(cancel_on_interruption=False, timeout_secs=10)
    async def escalate_to_harder_problem(params: FunctionCallParams, reason: str):
        """Move to a harder follow-up problem in the same topic, once the candidate has solved
        the current one well (correct, good complexity discussion, handled edge cases).

        Args:
            reason: One short phrase for why the candidate earned the escalation (e.g. "correct
                O(n) solution, explained space complexity correctly"). Used for the session log.
        """
        logger.debug(f"escalate_to_harder_problem called ({reason})")
        candidate = problems.get_escalation_candidate(session["current_problem"])
        if candidate is None:
            await params.result_callback(
                {"escalated": False, "message": "Already at the hardest tier for this topic."}
            )
            return
        session["current_problem"] = candidate
        session["escalated"] = True
        await params.result_callback(
            {
                "escalated": True,
                "title": candidate["title"],
                "difficulty": candidate["difficulty"],
                "problem_statement": candidate["problem_statement"],
                "constraints": candidate["constraints"],
            }
        )

    llm = GroqLLMService(
        api_key=config.GROQ_API_KEY,
        settings=GroqLLMService.Settings(
            model=config.GROQ_MODEL,
            system_instruction=interview.build_system_instruction(initial_problem, persona),
        ),
    )

    context = LLMContext(tools=[get_current_code, escalate_to_harder_problem])
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
    )

    @worker.rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        logger.info(f"Voice client ready (session={session_id}, problem={initial_problem['id']})")
        context.add_message({"role": "developer", "content": "Greet the candidate and present the problem now."})
        await worker.queue_frames([LLMRunFrame()])

    @worker.event_handler("on_pipeline_error")
    async def on_pipeline_error(worker, frame: ErrorFrame):
        # Groq occasionally fails a completion outright (e.g. a malformed tool-call attempt --
        # "Failed to call a function. Please adjust your prompt."). Left alone, this means the
        # candidate just gets silence with no idea whether they were heard. Scoped to the LLM
        # service specifically (via frame.processor) so this doesn't fire for STT/TTS hiccups,
        # which already have their own reconnect logic. Rate-limited to at most 2 retries per
        # 30s so a genuinely stuck/looping failure doesn't hammer the API instead of just giving
        # up and staying silent for that one turn.
        if frame.fatal or not isinstance(frame.processor, GroqLLMService):
            return
        now = time.monotonic()
        recent = [t for t in session["llm_error_timestamps"] if now - t < 30]
        if len(recent) >= 2:
            logger.warning(f"LLM error, already retried twice in the last 30s -- not retrying again: {frame.error}")
            session["llm_error_timestamps"] = recent
            return
        recent.append(now)
        session["llm_error_timestamps"] = recent
        logger.warning(f"LLM completion failed non-fatally ({frame.error}) -- retrying so the candidate isn't left in silence")
        await worker.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Voice client connected")

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Voice client disconnected")
        await worker.cancel()

    await runner.add_workers(worker)
    # add_workers() starts the worker in the background and returns immediately -- without
    # waiting here, this route handler (and the @app.websocket function above it) returns right
    # away, and Starlette closes the WebSocket out from under the still-running pipeline.
    await worker.wait()

    transcript = list(context.messages)
    scorecard = None
    try:
        scorecard = await interview.generate_scorecard(
            transcript, session["latest_code"], session["current_problem"]
        )
    except Exception:
        logger.exception("Scorecard generation failed -- session will still be saved without it")
    # This app runs one shared event loop across every concurrent session (see start_runner
    # above) -- a synchronous file write here would briefly stall every *other* active session's
    # real-time audio/LLM/TTS processing too, not just this one. asyncio.to_thread keeps it off
    # the loop.
    await asyncio.to_thread(_write_session_file, session, transcript, scorecard)
    ACTIVE_SESSIONS.pop(session_id, None)
