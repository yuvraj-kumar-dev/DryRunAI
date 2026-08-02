"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { PipecatClient, TransportState } from "@pipecat-ai/client-js";
import { WebSocketTransport, ProtobufFrameSerializer } from "@pipecat-ai/websocket-transport";
import { AlertTriangle, AudioLines, ChevronDown, Loader2, Mic, PhoneOff } from "lucide-react";
import { Logo } from "@/components/logo";

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
      router.replace("/practice");
      return;
    }
    const parsed = JSON.parse(raw);
    setSessionId(parsed.sessionId);
    setProblem(parsed.problem);
  }, [router]);

  // Connect voice once we know which session to join.
  //
  // React Strict Mode (default for the App Router since Next.js 13.5.1, and we don't override
  // it) deliberately double-invokes effects in dev: mount -> cleanup -> mount again. Without the
  // `cancelled` guard below, the first (soon-to-be-torn-down) invocation's async connect() could
  // still complete and reach the backend before cleanup takes effect -- and since
  // PENDING_SESSIONS.pop() server-side is a one-time read, a second real connection for the same
  // session_id would find it already consumed and silently fall back to a random new problem,
  // while the screen keeps showing the original one. Checking `cancelled` at every await boundary
  // ensures a torn-down effect invocation never actually calls connect().
  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;

    const client = new PipecatClient({
      transport: new WebSocketTransport({ serializer: new ProtobufFrameSerializer() }),
      enableMic: true,
      enableCam: false,
      callbacks: {
        onTransportStateChanged: (state: TransportState) => {
          if (state === "error") setStatus("error");
        },
        // Deliberately no onBotReady -> "listening" transition here. "Ready" just means the
        // pipeline can accept input -- the interviewer hasn't greeted the candidate yet at that
        // point (the greeting is still being generated/synthesized), so jumping straight to
        // "Listening" told the candidate it was their turn to talk before the interviewer had
        // said anything. Staying on "connecting" until onBotStartedSpeaking fires for the
        // greeting gives the correct connecting -> speaking (greeting) -> listening sequence.
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
      if (cancelled) return;
      await client.connect({ wsUrl: `${WS_URL}?session_id=${sessionId}` });
      if (cancelled) await client.disconnect();
    })().catch(() => setStatus("error"));

    return () => {
      cancelled = true;
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
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header
        className="flex items-center justify-between gap-4 border-b border-border px-6"
        style={{ height: "var(--header-height)" }}
      >
        <div className="flex min-w-0 items-center gap-3">
          <Logo className="shrink-0 text-sm" />
          <span className="hidden text-border sm:inline">/</span>
          <button
            onClick={() => setProblemCollapsed((v) => !v)}
            className="flex min-w-0 items-center gap-2 text-left"
          >
            <span className="truncate font-medium">{problem.title}</span>
            <span className="hidden shrink-0 text-muted-foreground sm:inline">
              ({problem.difficulty}, {problem.topic})
            </span>
            <ChevronDown
              className={`size-4 shrink-0 text-muted-foreground transition-transform ${problemCollapsed ? "" : "rotate-180"}`}
            />
          </button>
        </div>
        <StatusPill status={status} />
      </header>

      {!problemCollapsed && (
        <div className="space-y-3 border-b border-border px-6 py-5 text-sm text-foreground/80">
          <p>{problem.problem_statement}</p>
          <div>
            <div className="font-[family-name:var(--font-display-mono)] text-xs uppercase tracking-wider text-muted-foreground">
              Constraints
            </div>
            <ul className="list-inside list-disc">
              {problem.constraints.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          </div>
          {problem.examples.map((ex, i) => (
            <div key={i} className="rounded-md border border-border bg-card p-3 font-[family-name:var(--font-code)] text-xs">
              <div>input: {ex.input}</div>
              <div>output: {ex.output}</div>
              {ex.explanation && <div className="text-muted-foreground">{ex.explanation}</div>}
            </div>
          ))}
        </div>
      )}

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden p-4 sm:p-6">
        <div className="flex min-h-0 flex-1 flex-col rounded-md bg-gradient-to-br from-chart-1 via-chart-2 to-chart-3 p-px shadow-lg">
          <textarea
            value={code}
            onChange={(e) => onCodeChange(e.target.value)}
            placeholder="# write your solution here"
            spellCheck={false}
            className="w-full flex-1 resize-none rounded-[7px] bg-card p-6 font-[family-name:var(--font-code)] text-sm text-foreground outline-none"
          />
        </div>
      </div>

      <audio ref={audioRef} autoPlay />
    </div>
  );
}

const STATUS_CONFIG: Record<
  VoiceStatus,
  { label: string; icon: React.ComponentType<{ className?: string }>; glow: boolean; tone: "active" | "muted" | "error" }
> = {
  connecting: { label: "Connecting", icon: Loader2, glow: false, tone: "muted" },
  listening: { label: "Listening", icon: Mic, glow: true, tone: "active" },
  thinking: { label: "Thinking", icon: Loader2, glow: true, tone: "active" },
  speaking: { label: "Speaking", icon: AudioLines, glow: true, tone: "active" },
  error: { label: "Connection error", icon: AlertTriangle, glow: false, tone: "error" },
  ended: { label: "Session ended", icon: PhoneOff, glow: false, tone: "muted" },
};

function StatusPill({ status }: { status: VoiceStatus }) {
  const { label, icon: Icon, glow, tone } = STATUS_CONFIG[status];
  const spin = status === "connecting" || status === "thinking";

  return (
    <div className="relative shrink-0">
      {glow && (
        <div className="animate-glow-pulse absolute inset-0 rounded-full bg-gradient-to-r from-chart-1 via-chart-2 to-chart-3 opacity-70 blur-md" />
      )}
      <div
        className={`relative flex items-center gap-2 rounded-full border px-3 py-1.5 backdrop-blur ${
          tone === "error"
            ? "border-destructive/40 bg-destructive/10 text-destructive"
            : "border-border bg-background/80 text-foreground"
        }`}
      >
        <Icon className={`size-3.5 ${spin ? "animate-spin" : ""}`} />
        <span className="font-[family-name:var(--font-display-mono)] text-xs uppercase tracking-wider">
          {label}
        </span>
      </div>
    </div>
  );
}
