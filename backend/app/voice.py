"""Voice pipeline: mic -> Silero VAD -> Deepgram Flux (STT) -> Groq (LLM) -> Deepgram Aura-2 (TTS) -> speaker.

Wires the problem bank + interview logic (see problems.py / interview.py / session_state.py) into
the pipeline validated in v0a: problem/persona selection, the get_current_code,
move_to_next_problem and end_interview tools, pushing session changes back to the browser, and
session persistence (transcript + code snapshots + scorecard).
"""

import asyncio
import json
import time
import uuid

from fastapi import WebSocket
from loguru import logger
from pipecat.adapters.schemas.direct_function import tool_options
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    BotStoppedSpeakingFrame,
    ErrorFrame,
    LLMRunFrame,
    LLMSetToolChoiceFrame,
    LLMTextFrame,
    MetricsFrame,
)
from pipecat.observers.base_observer import BaseObserver, FramePushed
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
from app import session_state as state

# One long-lived runner for the app's lifetime -- Pipecat's documented pattern for embedding
# in a persistent host like a FastAPI server (workers are added/removed per session).
# Constructed inside start_runner() (not at module level) because WorkerRunner() needs a
# running event loop, which doesn't exist yet at import time.
runner: WorkerRunner | None = None
_runner_task: asyncio.Task | None = None

# Live sessions, keyed by session_id, so the HTTP endpoints in main.py (code snapshots, manual
# end) and the tools below can share state without any extra plumbing.
ACTIVE_SESSIONS: dict[str, dict] = {}

# Sessions created via POST /api/sessions (main.py) but not yet connected to /ws/voice -- lets
# the frontend know the exact problem selected (to render it as text) before opening the voice
# WebSocket, instead of the problem being picked (again, differently) at connect time.
PENDING_SESSIONS: dict[str, dict] = {}

# Finished sessions, keyed by session_id, so GET /api/sessions/{id} can serve the report after
# the WebSocket is gone. In-memory only, capped -- the durable copy is the file in sessions/,
# this just spares the report screen from having to read the disk format.
COMPLETED_SESSIONS: dict[str, dict] = {}
MAX_COMPLETED_SESSIONS = 50

# How long to wait for the interviewer's closing line before winding the session up anyway.
# Without this, an LLM failure right after end_interview would leave the session hanging open
# with the candidate staring at a screen that never moves on to their report.
END_INTERVIEW_TIMEOUT_SECS = 25

# How many problems an interview runs for. 2 is the default because that's what a real 45-minute
# round actually fits, and because it's the smallest plan that exercises the problem-change path
# at all -- a 1-problem interview never calls move_to_next_problem.
DEFAULT_PLAN_SIZE = 2
MAX_PLAN_SIZE = 4


def coerce_plan_size(raw) -> int:
    """Clamp whatever arrives (query string, JSON body) into a sane plan size."""
    try:
        return max(1, min(int(raw), MAX_PLAN_SIZE))
    except (TypeError, ValueError):
        return DEFAULT_PLAN_SIZE


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


class _LatencyObserver(BaseObserver):
    """Logs every MetricsFrame (TTFB/TTFA per service) with elapsed time since session start.

    `enable_metrics=True` on PipelineWorker already computes these numbers internally, but
    they're normally only surfaced to an RTVI-aware client, not the server log. Added to
    diagnose the ~10-15s first-response latency seen in early voice tests -- this pinpoints
    which service (STT connect, Groq TTFB, Deepgram TTS TTFA) the time is actually going to,
    instead of guessing from the framework's source.
    """

    def __init__(self, session_start: float):
        super().__init__()
        self._session_start = session_start

    async def on_push_frame(self, data: FramePushed):
        if not isinstance(data.frame, MetricsFrame):
            return
        elapsed = time.monotonic() - self._session_start
        for m in data.frame.data:
            logger.info(f"[metrics +{elapsed:.2f}s] {m}")


class _ToolCallLoopBreaker(BaseObserver):
    """Deterministic circuit breaker for a confirmed real failure mode: Llama 3.3 (via Groq)
    sometimes keeps calling the same tool repeatedly instead of ever producing a spoken response.
    One real session logged 13 consecutive get_current_code calls with total silence, across
    three repeated candidate requests to "read out my code." Prompt wording (rule 4 in
    INTERVIEWER_BEHAVIOR) can reduce how often this happens but can't guarantee it won't -- this
    makes it structurally impossible to exceed MAX_CONSECUTIVE_TOOL_CALLS silent tool calls in a
    row, independent of what the model "decides" to do.

    note_tool_call() is called from inside a tool handler on every invocation; once the streak
    hits the threshold, it forces tool_choice="none" via a real pipeline frame (not just mutating
    the context object -- LLMSetToolChoiceFrame is how Pipecat actually propagates this to the
    LLM service), so the *next* completion is structurally incapable of calling a tool and must
    produce text. This observer watches for LLMTextFrame (the frame carrying actual spoken/text
    output) to detect that a real response landed, and resets the streak + tool_choice back to
    "auto" at that point so normal tool-calling resumes.
    """

    MAX_CONSECUTIVE_TOOL_CALLS = 2

    def __init__(self, session: dict):
        super().__init__()
        self._session = session
        self.worker: PipelineWorker | None = None  # set right after PipelineWorker() is built

    async def on_push_frame(self, data: FramePushed):
        if not isinstance(data.frame, LLMTextFrame):
            return
        if self._session.get("consecutive_tool_calls", 0) == 0 or self.worker is None:
            return
        self._session["consecutive_tool_calls"] = 0
        await self.worker.queue_frames([LLMSetToolChoiceFrame(tool_choice="auto")])


class _EndOfInterviewObserver(BaseObserver):
    """Winds the session up once the interviewer has finished saying its closing line.

    end_interview can't just tear the pipeline down itself: the model's goodbye is still queued
    for TTS at that point, so the candidate would get cut off mid-sentence (or hear nothing at
    all). Instead the tool sets end_requested, and this waits for the next
    BotStoppedSpeakingFrame -- i.e. the closing line has actually been spoken -- before running
    the finalize step. Finalize is dispatched as its own task rather than awaited here: it
    cancels the worker, and doing that from inside a pipeline callback would be cancelling the
    thing currently running us.
    """

    def __init__(self, session: dict):
        super().__init__()
        self._session = session
        self.worker: PipelineWorker | None = None

    async def on_push_frame(self, data: FramePushed):
        if not isinstance(data.frame, BotStoppedSpeakingFrame):
            return
        if not self._session.get("end_requested") or self._session.get("finalizing"):
            return
        if self.worker is None:
            return
        self._session["finalizing"] = True
        logger.info("Closing line delivered -- finalizing session")
        asyncio.create_task(finalize_session(self._session, self.worker))


async def note_tool_call(session: dict, worker: PipelineWorker) -> None:
    """Call from inside every tool handler on every invocation -- see _ToolCallLoopBreaker."""
    streak = session.get("consecutive_tool_calls", 0) + 1
    session["consecutive_tool_calls"] = streak
    if streak >= _ToolCallLoopBreaker.MAX_CONSECUTIVE_TOOL_CALLS:
        logger.warning(f"{streak} consecutive tool calls with no spoken response -- forcing tool_choice=none")
        await worker.queue_frames([LLMSetToolChoiceFrame(tool_choice="none")])


async def push_to_client(worker: PipelineWorker, data: dict) -> None:
    """Send an out-of-band message down the same WebSocket the audio uses.

    This is the channel the interview screen had no equivalent of before, which is why the
    displayed problem could never change: the server would move to a new problem while the
    browser went on rendering the one it was handed at session creation. RTVI server messages
    survive ProtobufFrameSerializer (it explicitly sets ignore_rtvi_messages = False, since a
    WebSocket transport is exactly the delivery channel for them) and surface in the browser as
    the client's onServerMessage callback.
    """
    try:
        await worker.rtvi.send_server_message(data)
    except Exception:
        logger.exception(f"Failed to push {data.get('type')!r} to client")


def _remember_completed(session_id: str, record: dict) -> None:
    COMPLETED_SESSIONS[session_id] = record
    while len(COMPLETED_SESSIONS) > MAX_COMPLETED_SESSIONS:
        COMPLETED_SESSIONS.pop(next(iter(COMPLETED_SESSIONS)))


def _write_session_file(record: dict) -> None:
    config.SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = config.SESSIONS_DIR / f"{time.strftime('%Y%m%dT%H%M%S')}-{record['session_id']}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    logger.info(f"Session written to {path}")


async def finalize_session(session: dict, worker: PipelineWorker | None) -> dict:
    """Score the interview, hand the report to the browser, persist it, and stop the pipeline.

    Idempotent: the closing-line observer, the manual "end interview" button, the safety timeout
    and plain socket teardown can all reach this, and more than one of them usually does.

    Deliberately runs while the WebSocket is still open -- the scorecard used to be generated
    only after the socket had closed, which meant it was written to a file nobody was ever shown.
    """
    if session.get("finished"):
        return session.get("record")
    session["finished"] = True
    session["end_requested"] = False

    context = session.get("context")
    transcript = list(context.messages) if context is not None else []
    scorecard = None
    try:
        scorecard = await interview.generate_scorecard(transcript, state.attempted_problems(session))
    except Exception:
        logger.exception("Scorecard generation failed -- session will still be saved without it")
    session["scorecard"] = scorecard

    record = state.session_record(session, transcript, scorecard)
    session["record"] = record
    _remember_completed(session["session_id"], record)

    if worker is not None:
        await push_to_client(
            worker,
            {
                "type": "interview_ended",
                "session_id": session["session_id"],
                "reason": session.get("end_reason"),
                "scorecard": scorecard,
            },
        )
        # Give the message a moment to actually get serialized out of the pipeline and onto the
        # wire before the transport goes away underneath it. The report screen re-fetches from
        # GET /api/sessions/{id} regardless, so a dropped push costs a round trip, not the report.
        await asyncio.sleep(0.5)

    # This app runs one shared event loop across every concurrent session (see start_runner) --
    # a synchronous file write here would briefly stall every *other* active session's real-time
    # audio/LLM/TTS processing too, not just this one. asyncio.to_thread keeps it off the loop.
    await asyncio.to_thread(_write_session_file, record)
    ACTIVE_SESSIONS.pop(session["session_id"], None)

    if worker is not None:
        await worker.cancel()
    return record


async def _end_interview_timeout(session: dict, worker: PipelineWorker) -> None:
    """Safety net for end_interview: if no closing line ever gets spoken (an LLM or TTS failure
    right at the end), finalize anyway rather than leaving the candidate on a dead screen.
    """
    await asyncio.sleep(END_INTERVIEW_TIMEOUT_SECS)
    if session.get("finished") or session.get("finalizing") or not session.get("end_requested"):
        return
    logger.warning("No closing line within the timeout -- finalizing session anyway")
    session["finalizing"] = True
    await finalize_session(session, worker)


def _pick_initial_problem(topic: str | None, difficulty: str | None) -> dict:
    topic = topic if topic in problems.TOPICS else problems.TOPICS[0]
    difficulty = difficulty if difficulty in problems.DIFFICULTY_ORDER else problems.DIFFICULTY_ORDER[0]
    return problems.select_problem(topic, difficulty)


async def handle_voice_websocket(websocket: WebSocket) -> None:
    """Build and register one PipelineWorker for a single voice session."""
    session_start = time.monotonic()
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
        session = {**existing, "llm_error_timestamps": []}
    else:
        pending = PENDING_SESSIONS.pop(session_id, None)
        if pending is not None:
            # Normal flow: frontend already called POST /api/sessions, so the problem shown on
            # screen and the problem the voice pipeline discusses are guaranteed to match.
            persona = pending["persona"]
            initial_problem = pending["problem"]
            plan_size = pending["plan_size"]
        else:
            # Fallback for direct/manual connections (e.g. quick testing) that skip the REST call.
            persona = query_params.get("persona") if query_params.get("persona") in interview.PERSONAS else "neutral"
            initial_problem = _pick_initial_problem(query_params.get("topic"), query_params.get("difficulty"))
            plan_size = coerce_plan_size(query_params.get("plan_size"))
        session = state.new_session(session_id, initial_problem, persona, plan_size)
    ACTIVE_SESSIONS[session_id] = session

    persona = session["persona"]
    current_problem = session["current_problem"]

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
    # placeholder in context, so the LLM never actually saw the real code or the new problem.
    # See CLAUDE.md Corrections Log.
    #
    # Every tool takes at least one real (non-optional) argument -- not just documentation, a
    # workaround for a confirmed Pipecat/Groq bug: a zero-parameter tool gets called with the
    # literal string "null" as its arguments, and Pipecat's `arguments or "{}"` guard only
    # catches an *empty* string, not "null" -- so json.loads("null") returns None, and
    # `function(**None)` crashes. See CLAUDE.md Corrections Log.
    @tool_options(cancel_on_interruption=False, timeout_secs=10)
    async def get_current_code(params: FunctionCallParams, reason: str):
        """Read the candidate's current code so far, exactly as it's written in their editor.

        You normally do NOT need this -- the Reminder message already carries their current code
        and is refreshed automatically. Only call it if you have specific reason to think the
        Reminder went stale.

        Args:
            reason: One short phrase for why you're checking now (e.g. "candidate said they just
                changed it"). Used for the session log, not spoken aloud.
        """
        logger.debug(f"get_current_code called ({reason})")
        await note_tool_call(session, worker)
        code = session["latest_code"]
        await params.result_callback(
            {"code": code or "(the candidate hasn't written any code yet)"}
        )

    @tool_options(cancel_on_interruption=False, timeout_secs=10)
    async def move_to_next_problem(params: FunctionCallParams, reason: str, solved: bool):
        """Finish with the current problem and move the interview on to the next one.

        Call this once the discussion on the current problem has run its course -- either they
        solved it, or they're stuck and it's time to move on. Do not stay on one problem for the
        whole interview.

        After calling this, the Reminder message will name a NEW problem. Present that problem,
        exactly as the Reminder states it. Do not invent your own follow-up.

        Args:
            reason: One short phrase for why you're moving on (e.g. "correct O(n) solution,
                explained space complexity"). Used for the session log.
            solved: true if they genuinely solved this problem (correct, sensible complexity,
                edge cases considered), false if they were stuck or gave up. This only decides
                how hard the next problem is -- either way the interview moves on.
        """
        logger.info(f"move_to_next_problem called (solved={solved}, {reason})")
        await note_tool_call(session, worker)
        nxt = state.advance_to_next_problem(session, solved=solved, reason=reason)
        if nxt is None:
            await params.result_callback(
                {
                    "moved": False,
                    "instruction": (
                        "That was the last problem of the interview -- there is no next one. "
                        "Say a brief closing line and call end_interview now."
                    ),
                }
            )
            return
        await push_to_client(
            worker,
            {
                "type": "problem_changed",
                "problem": problems.public_problem(nxt),
                "index": session["problem_index"] + 1,
                "total": session["plan_size"],
            },
        )
        # Force the next completion to be speech. Without this, the model has been seen calling
        # move_to_next_problem and then end_interview back-to-back in a single turn -- ending the
        # interview having never said a word about the problem it had just moved to, while the
        # candidate's screen sat on a question nobody ever introduced. Presenting the new problem
        # is not optional, so make it structural rather than a prompt request.
        # _ToolCallLoopBreaker flips this back to "auto" as soon as real text comes out.
        await worker.queue_frames([LLMSetToolChoiceFrame(tool_choice="none")])
        # Deliberately terse: the new problem's full text goes into the Reminder, not here. When
        # the statement was returned in the tool result instead, the model treated it as one
        # suggestion among many and presented a problem it made up instead -- see the
        # update_context_reminder docstring.
        await params.result_callback(
            {
                "moved": True,
                "instruction": (
                    "The interview has moved on. The Reminder message now states the new problem "
                    "and the candidate's screen already shows it. Present THAT problem "
                    "conversationally right now -- do not describe any other problem."
                ),
                "problem_number": session["problem_index"] + 1,
                "of": session["plan_size"],
            }
        )

    @tool_options(cancel_on_interruption=False, timeout_secs=10)
    async def end_interview(params: FunctionCallParams, reason: str):
        """End the interview and send the candidate their scorecard.

        Call this after the last problem is done, or whenever the candidate asks to stop.
        Say a short closing line immediately after calling it -- thank them and tell them their
        scorecard is on the way. The session wraps up on its own once you've said it.

        Args:
            reason: One short phrase for why the interview is ending (e.g. "completed both
                problems", "candidate asked to stop"). Used for the session log.
        """
        logger.info(f"end_interview called ({reason})")
        await note_tool_call(session, worker)
        session["end_requested"] = True
        session["end_reason"] = reason
        asyncio.create_task(_end_interview_timeout(session, worker))
        await params.result_callback(
            {
                "ok": True,
                "instruction": (
                    "Interview is ending. Say ONE short closing line now -- thank them and tell "
                    "them their scorecard is on its way. Do not ask another question, and do not "
                    "tell them how they did."
                ),
            }
        )

    llm = GroqLLMService(
        api_key=config.GROQ_API_KEY,
        settings=GroqLLMService.Settings(
            model=config.GROQ_MODEL,
            # No problem text here on purpose -- a system prompt is fixed for the life of the
            # connection, so a problem baked into it would go stale the moment the interview
            # moved on. The current problem lives only in the Reminder message.
            system_instruction=interview.build_system_instruction(persona, session["plan_size"]),
        ),
    )

    context = LLMContext(tools=[get_current_code, move_to_next_problem, end_interview])
    # Referenced by state.update_context_reminder() -- both from the tools above and from main.py's
    # code-snapshot endpoint, which has no other way to reach this connection's context.
    # Reset the per-connection bookkeeping too: on a reconnect, `session` was shallow-copied from
    # a previous connection's state, so any old reminder message object belongs to that
    # connection's (now-discarded) context, not this one.
    session["context"] = context
    session["context_reminder_message"] = None
    session["consecutive_tool_calls"] = 0
    session["end_requested"] = False
    session["finalizing"] = False
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

    tool_loop_breaker = _ToolCallLoopBreaker(session)
    end_observer = _EndOfInterviewObserver(session)
    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
        observers=[_LatencyObserver(session_start), tool_loop_breaker, end_observer],
    )
    # Can't construct these observers with the worker reference they need to queue frames -- the
    # worker doesn't exist until after observers are already handed to PipelineWorker(). Safe to
    # backfill immediately after: nothing invokes an observer until the pipeline actually starts
    # running, well after this point.
    tool_loop_breaker.worker = worker
    end_observer.worker = worker
    # The manual "end interview" button (POST /api/sessions/{id}/end) has no other route to this
    # connection's worker.
    session["worker"] = worker

    @worker.rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        elapsed = time.monotonic() - session_start
        logger.info(
            f"Voice client ready (session={session_id}, problem={current_problem['id']}, "
            f"plan_size={session['plan_size']}, +{elapsed:.2f}s since session start)"
        )
        # Seed the Reminder before the first completion -- it carries the problem statement now,
        # so without it the interviewer has no problem to present at all.
        state.update_context_reminder(session)
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

    # Normally already done (end_interview, or the manual end button) -- this covers the
    # candidate simply closing the tab, which is still a finished interview worth scoring.
    # finalize_session is idempotent, and with the worker gone it skips the client push.
    await finalize_session(session, worker=None)

