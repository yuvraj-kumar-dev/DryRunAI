"""
Throwaway A/B test: Deepgram Flux (model-integrated end-of-turn) vs Nova-3 +
utterance_end_ms (naive silence-based turn detection).

Talk naturally into your mic as if explaining a DSA approach out loud, including real
thinking pauses ("so I'd iterate through the array... and then... for each element I'd
check if..."). Watch how long after you actually stop talking each model takes to decide
you're "done" (marked >>> in the output), and whether it fires too early during a pause.

Usage:
    python _ab_test_stt.py flux
    python _ab_test_stt.py nova3 [utterance_end_ms]   # default 2000

Ctrl+C to stop.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
import numpy as np
import sounddevice as sd
import websockets

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
DEEPGRAM_API_KEY = os.environ["DEEPGRAM_API_KEY"]

SAMPLE_RATE = 16000
CHUNK_MS = 80
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_MS / 1000)

audio_queue: asyncio.Queue = asyncio.Queue()
loop: asyncio.AbstractEventLoop | None = None
last_activity = time.monotonic()


def audio_callback(indata, frames, time_info, status):
    pcm16 = (indata[:, 0] * 32767).astype(np.int16).tobytes()
    loop.call_soon_threadsafe(audio_queue.put_nowait, pcm16)


def since_last_activity_ms() -> int:
    return int((time.monotonic() - last_activity) * 1000)


async def sender(ws):
    while True:
        chunk = await audio_queue.get()
        await ws.send(chunk)


async def stream_flux():
    global last_activity
    uri = "wss://api.deepgram.com/v2/listen?model=flux-general-en&encoding=linear16&sample_rate=16000"
    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}
    async with websockets.connect(uri, additional_headers=headers) as ws:
        send_task = asyncio.create_task(sender(ws))
        print("=== FLUX ===  talk naturally, include real thinking pauses. Ctrl+C to stop.\n")
        try:
            async for msg in ws:
                data = json.loads(msg)
                t = time.strftime("%H:%M:%S")
                mtype = data.get("type")
                if mtype == "TurnInfo":
                    transcript = data.get("transcript", "")
                    if transcript:
                        last_activity = time.monotonic()
                        print(f"[{t}] (speaking) {transcript}")
                elif mtype == "EndOfTurn":
                    print(f"[{t}] >>> EndOfTurn -- {since_last_activity_ms()}ms after last words <<<\n")
                elif mtype == "EagerEndOfTurn":
                    print(f"[{t}] (eager end-of-turn signal)")
                elif mtype == "TurnResumed":
                    print(f"[{t}] (turn resumed -- kept talking after eager signal)")
        finally:
            send_task.cancel()


async def stream_nova3(utterance_end_ms=2000):
    global last_activity
    uri = (
        "wss://api.deepgram.com/v1/listen?model=nova-3&encoding=linear16&sample_rate=16000"
        f"&channels=1&interim_results=true&vad_events=true&utterance_end_ms={utterance_end_ms}"
    )
    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}
    async with websockets.connect(uri, additional_headers=headers) as ws:
        send_task = asyncio.create_task(sender(ws))
        print(f"=== NOVA-3 (utterance_end_ms={utterance_end_ms}) ===  talk naturally. Ctrl+C to stop.\n")
        try:
            async for msg in ws:
                data = json.loads(msg)
                t = time.strftime("%H:%M:%S")
                mtype = data.get("type")
                if mtype == "Results":
                    alt = data["channel"]["alternatives"][0]
                    transcript = alt.get("transcript", "")
                    is_final = data.get("is_final")
                    speech_final = data.get("speech_final")
                    if transcript:
                        last_activity = time.monotonic()
                        tag = "FINAL" if is_final else "interim"
                        extra = " [speech_final]" if speech_final else ""
                        print(f"[{t}] ({tag}{extra}) {transcript}")
                elif mtype == "UtteranceEnd":
                    print(f"[{t}] >>> UtteranceEnd -- {since_last_activity_ms()}ms after last words <<<\n")
        finally:
            send_task.cancel()


async def main():
    global loop
    loop = asyncio.get_running_loop()
    model = sys.argv[1] if len(sys.argv) > 1 else "flux"
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, callback=audio_callback,
        blocksize=CHUNK_SAMPLES, dtype="float32",
    )
    with stream:
        if model == "flux":
            await stream_flux()
        else:
            utterance_ms = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
            await stream_nova3(utterance_ms)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
