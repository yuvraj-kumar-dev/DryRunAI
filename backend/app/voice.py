"""v0a voice spike: mic -> Silero VAD -> Deepgram Flux (STT) -> Groq (LLM) -> Deepgram Aura-2 (TTS) -> speaker.

Minimal on purpose -- this only proves the real-time interruptible conversation feels right.
Not connected to problems, code, or session persistence yet (see docs/01_SPEC.md v0a scope).
"""

import asyncio

from fastapi import WebSocket
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
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
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams, FastAPIWebsocketTransport
from pipecat.workers.runner import WorkerRunner

from app import config

SYSTEM_INSTRUCTION = """You are a friendly technical interviewer conducting a practice DSA
(data structures and algorithms) interview. Keep responses brief and conversational -- this is
a spoken conversation, not text chat. This is an early connection test (v0a): just have a
natural conversation to confirm the voice pipeline works. Greet the candidate, ask them how
they're doing, and chat naturally about a simple topic like their favorite programming language."""

# One long-lived runner for the app's lifetime -- Pipecat's documented pattern for embedding
# in a persistent host like a FastAPI server (workers are added/removed per session).
# Constructed inside start_runner() (not at module level) because WorkerRunner() needs a
# running event loop, which doesn't exist yet at import time.
runner: WorkerRunner | None = None
_runner_task: asyncio.Task | None = None


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


async def handle_voice_websocket(websocket: WebSocket) -> None:
    """Build and register one PipelineWorker for a single voice session."""
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

    llm = GroqLLMService(
        api_key=config.GROQ_API_KEY,
        settings=GroqLLMService.Settings(
            model=config.GROQ_MODEL,
            system_instruction=SYSTEM_INSTRUCTION,
        ),
    )

    context = LLMContext()
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
        logger.info("Voice client ready")
        context.add_message({"role": "developer", "content": "Greet the candidate now."})
        await worker.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Voice client connected")

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Voice client disconnected")
        await worker.cancel()

    await runner.add_workers(worker)
