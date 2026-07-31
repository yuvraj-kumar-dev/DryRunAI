"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { PipecatClient, TransportState } from "@pipecat-ai/client-js";
import { WebSocketTransport, ProtobufFrameSerializer } from "@pipecat-ai/websocket-transport";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const WS_URL = BACKEND_URL.replace(/^http/, "ws") + "/ws/voice";
const SNAPSHOT_INTERVAL_MS = 8000;

type Problem = {
  id: string;
  title: string;
  topic: string;
  difficulty: string;
  problem_statement: string;
  constraints: string[];
  examples: { input: string; output: string; explanation?: string }[];
};

type VoiceStatus = "connecting" | "listening" | "thinking" | "speaking" | "error" | "ended";

export default function InterviewPage() {
  const router = useRouter();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [problem, setProblem] = useState<Problem | null>(null);
  const [problemCollapsed, setProblemCollapsed] = useState(false);
  const [code, setCode] = useState("");
  const [status, setStatus] = useState<VoiceStatus>("connecting");

  const clientRef = useRef<PipecatClient | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const lastSentCodeRef = useRef("");
  const codeRef = useRef("");

  // Load the session picked on the previous screen; bounce back if there isn't one.
  useEffect(() => {
    const raw = sessionStorage.getItem("dryrunai_session");
    if (!raw) {
      router.replace("/");
      return;
    }
    const parsed = JSON.parse(raw);
    setSessionId(parsed.sessionId);
    setProblem(parsed.problem);
  }, [router]);

  // Connect voice once we know which session to join.
  useEffect(() => {
    if (!sessionId) return;

    const client = new PipecatClient({
      transport: new WebSocketTransport({ serializer: new ProtobufFrameSerializer() }),
      enableMic: true,
      enableCam: false,
      callbacks: {
        onTransportStateChanged: (state: TransportState) => {
          if (state === "error") setStatus("error");
        },
        onBotReady: () => setStatus("listening"),
        onUserStartedSpeaking: () => setStatus("listening"),
        onBotStartedSpeaking: () => setStatus("speaking"),
        onBotStoppedSpeaking: () => setStatus("listening"),
        onDisconnected: () => setStatus("ended"),
        onTrackStarted: (track: MediaStreamTrack, participant?: { local?: boolean }) => {
          if (!participant?.local && track.kind === "audio" && audioRef.current) {
            audioRef.current.srcObject = new MediaStream([track]);
          }
        },
      },
    });
    clientRef.current = client;

    (async () => {
      await client.initDevices();
      await client.connect({ wsUrl: `${WS_URL}?session_id=${sessionId}` });
    })().catch(() => setStatus("error"));

    return () => {
      client.disconnect();
    };
  }, [sessionId]);

  // Periodic (not per-keystroke) code snapshots.
  useEffect(() => {
    if (!sessionId) return;
    const interval = setInterval(() => {
      const current = codeRef.current;
      if (current === lastSentCodeRef.current) return;
      lastSentCodeRef.current = current;
      fetch(`${BACKEND_URL}/api/sessions/${sessionId}/code`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: current }),
      }).catch(() => {
        /* best-effort -- a missed snapshot isn't fatal, the next timer tick will catch up */
      });
    }, SNAPSHOT_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [sessionId]);

  function onCodeChange(value: string) {
    setCode(value);
    codeRef.current = value;
    if (!problemCollapsed && value.trim().length > 0) setProblemCollapsed(true);
  }

  if (!problem) return null;

  return (
    <div className="flex min-h-screen flex-col bg-[#0a0a0f] text-[#e5e5ea]">
      <div className="border-b border-white/10">
        <button
          onClick={() => setProblemCollapsed((v) => !v)}
          className="flex w-full items-center justify-between px-6 py-3 text-left"
        >
          <span className="font-medium">
            {problem.title}{" "}
            <span className="text-[#8b8b96]">
              ({problem.difficulty}, {problem.topic})
            </span>
          </span>
          <span className="text-[#8b8b96]">{problemCollapsed ? "▾" : "▴"}</span>
        </button>
        {!problemCollapsed && (
          <div className="space-y-3 px-6 pb-5 text-sm text-[#c5c5cc]">
            <p>{problem.problem_statement}</p>
            <div>
              <div className="text-xs uppercase tracking-wide text-[#8b8b96]">Constraints</div>
              <ul className="list-inside list-disc">
                {problem.constraints.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </div>
            {problem.examples.map((ex, i) => (
              <div key={i} className="rounded-lg bg-[#13131a] p-3 font-mono text-xs">
                <div>input: {ex.input}</div>
                <div>output: {ex.output}</div>
                {ex.explanation && <div className="text-[#8b8b96]">{ex.explanation}</div>}
              </div>
            ))}
          </div>
        )}
      </div>

      <textarea
        value={code}
        onChange={(e) => onCodeChange(e.target.value)}
        placeholder="# write your solution here"
        spellCheck={false}
        className="flex-1 resize-none bg-[#0d0d14] p-6 font-mono text-sm text-[#e5e5ea] outline-none"
      />

      <audio ref={audioRef} autoPlay />

      <div className="flex items-center gap-2 border-t border-white/10 bg-[#13131a] px-6 py-3 text-sm">
        <span
          className={`h-2 w-2 rounded-full ${
            status === "error"
              ? "bg-red-400"
              : status === "speaking"
                ? "bg-gradient-to-r from-indigo-400 to-cyan-300"
                : "bg-emerald-400"
          }`}
        />
        <span className="text-[#8b8b96]">{statusLabel(status)}</span>
      </div>
    </div>
  );
}

function statusLabel(status: VoiceStatus): string {
  switch (status) {
    case "connecting":
      return "Connecting...";
    case "listening":
      return "Listening";
    case "thinking":
      return "Thinking...";
    case "speaking":
      return "Speaking";
    case "error":
      return "Connection error";
    case "ended":
      return "Session ended";
  }
}
