"use client";

import { useRef, useState } from "react";
import { PipecatClient, TransportState } from "@pipecat-ai/client-js";
import { WebSocketTransport, ProtobufFrameSerializer } from "@pipecat-ai/websocket-transport";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const WS_URL = BACKEND_URL.replace(/^http/, "ws") + "/ws/voice";

type Status = "idle" | "connecting" | "connected" | "error";

export default function V0aPage() {
  const [status, setStatus] = useState<Status>("idle");
  const [log, setLog] = useState<string[]>([]);
  const clientRef = useRef<PipecatClient | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  function appendLog(message: string) {
    setLog((prev) => [...prev.slice(-49), `${new Date().toLocaleTimeString()} — ${message}`]);
  }

  async function connect() {
    setStatus("connecting");
    appendLog(`Connecting to ${WS_URL}...`);

    const client = new PipecatClient({
      transport: new WebSocketTransport({ serializer: new ProtobufFrameSerializer() }),
      enableMic: true,
      enableCam: false,
      callbacks: {
        onTransportStateChanged: (state: TransportState) => appendLog(`transport: ${state}`),
        onConnected: () => setStatus("connected"),
        onDisconnected: () => {
          setStatus("idle");
          appendLog("disconnected");
        },
        onBotReady: () => appendLog("bot ready"),
        onUserStartedSpeaking: () => appendLog("you started speaking"),
        onUserStoppedSpeaking: () => appendLog("you stopped speaking"),
        onBotStartedSpeaking: () => appendLog("bot started speaking"),
        onBotStoppedSpeaking: () => appendLog("bot stopped speaking"),
        onTrackStarted: (track: MediaStreamTrack, participant?: { local?: boolean }) => {
          if (!participant?.local && track.kind === "audio" && audioRef.current) {
            audioRef.current.srcObject = new MediaStream([track]);
          }
        },
      },
    });

    clientRef.current = client;

    try {
      await client.initDevices();
      await client.connect({ wsUrl: WS_URL });
    } catch (err) {
      setStatus("error");
      appendLog(`connect failed: ${err}`);
    }
  }

  async function disconnect() {
    await clientRef.current?.disconnect();
    clientRef.current = null;
  }

  return (
    <div className="flex min-h-screen flex-col items-center gap-6 bg-zinc-950 p-10 text-zinc-100">
      <h1 className="text-2xl font-semibold">v0a — Voice Pipeline Spike</h1>
      <p className="max-w-md text-center text-sm text-zinc-400">
        Talk naturally. Mic → Silero VAD → Deepgram Flux → Groq → Deepgram Aura-2 → speaker.
        Nothing here is connected to problems/code yet — this only tests the raw conversation.
      </p>

      <div className="flex gap-3">
        <button
          onClick={connect}
          disabled={status === "connecting" || status === "connected"}
          className="rounded-lg bg-gradient-to-r from-indigo-500 to-cyan-400 px-5 py-2 font-medium text-zinc-950 disabled:opacity-40"
        >
          Connect
        </button>
        <button
          onClick={disconnect}
          disabled={status !== "connected"}
          className="rounded-lg border border-zinc-700 px-5 py-2 font-medium disabled:opacity-40"
        >
          Disconnect
        </button>
      </div>

      <div className="text-sm">
        status: <span className="font-mono">{status}</span>
      </div>

      <audio ref={audioRef} autoPlay />

      <div className="w-full max-w-lg flex-1 overflow-y-auto rounded-lg bg-zinc-900 p-3 font-mono text-xs text-zinc-400">
        {log.length === 0 ? (
          <div className="text-zinc-600">Log will appear here...</div>
        ) : (
          log.map((line, i) => <div key={i}>{line}</div>)
        )}
      </div>
    </div>
  );
}
