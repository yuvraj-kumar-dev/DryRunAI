"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
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

// Messages the backend pushes down the voice WebSocket (voice.py's push_to_client). Without this
// channel the displayed problem could never change: the server would move the interview on while
// the browser went on rendering whatever it was handed at session creation.
const SESSION_KEY = "dryrunai_session";

type StoredSession = { sessionId: string; problem: Problem; planSize?: number } | null;

// useSyncExternalStore calls getSnapshot on every render and re-renders if the result changes
// identity, so the parse has to be cached against the raw string -- parsing fresh each call
// would return a new object every time and loop forever.
let cachedRaw: string | null = null;
let cachedSession: StoredSession = null;

function readStoredSession(): StoredSession {
  const raw = sessionStorage.getItem(SESSION_KEY);
  if (raw !== cachedRaw) {
    cachedRaw = raw;
    try {
      cachedSession = raw ? (JSON.parse(raw) as StoredSession) : null;
    } catch {
      cachedSession = null;
    }
  }
  return cachedSession;
}

// The stored session is written once by /practice before this page ever mounts and never changes
// while the interview is running, so there is genuinely nothing to subscribe to.
function subscribeToStoredSession() {
  return () => {};
}

type ServerMessage =
  | { type: "problem_changed"; problem: Problem; index: number; total: number }
  | { type: "interview_ended"; session_id: string; reason: string | null; scorecard: unknown };

export default function InterviewPage() {
  const router = useRouter();
  // The session picked on the previous screen. sessionStorage is an external store, so it's read
  // with useSyncExternalStore rather than loaded into state from an effect: the server render
  // gets a definite null (no hydration mismatch) while the client gets the real value on its
  // first render, with no cascading re-render on mount.
  const stored = useSyncExternalStore(subscribeToStoredSession, readStoredSession, () => null);

  // The problem and plan size start from what /practice handed us, then the backend can replace
  // them mid-interview (problem_changed). Layering an override over the stored value keeps that
  // possible without copying the initial value into state on mount.
  const [problemOverride, setProblemOverride] = useState<Problem | null>(null);
  const [planSizeOverride, setPlanSizeOverride] = useState<number | null>(null);
  const [problemNumber, setProblemNumber] = useState(1);
  const [problemCollapsed, setProblemCollapsed] = useState(false);
  const [code, setCode] = useState("");
  const [status, setStatus] = useState<VoiceStatus>("connecting");
  const [ending, setEnding] = useState(false);

  const sessionId = stored?.sessionId ?? null;
  const problem = problemOverride ?? stored?.problem ?? null;
  const planSize = planSizeOverride ?? stored?.planSize ?? 1;

  const clientRef = useRef<PipecatClient | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const lastSentCodeRef = useRef("");
  const codeRef = useRef("");
  // Set the moment the interview is known to be over, so the snapshot timer and the disconnect
  // handler can tell "finished" apart from "the socket dropped".
  const endedRef = useRef(false);

  // Nothing to interview about without a session -- bounce back to the picker.
  useEffect(() => {
    if (!stored) router.replace("/practice");
  }, [stored, router]);

  const goToReport = useCallback(() => {
    if (endedRef.current || !sessionId) return;
    endedRef.current = true;
    setStatus("ended");
    router.replace(`/report?session=${sessionId}`);
  }, [router, sessionId]);

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
        onServerMessage: (data: ServerMessage) => {
          if (!data || typeof data !== "object") return;
          if (data.type === "problem_changed") {
            // The interviewer is about to introduce this out loud, so swap the screen now --
            // the two have to agree, which is the entire reason this message exists.
            setProblemOverride(data.problem);
            setProblemNumber(data.index);
            setPlanSizeOverride(data.total);
            setProblemCollapsed(false);
            // The new problem gets a blank editor. The previous problem's code is already
            // archived server-side (session_state.advance_to_next_problem), and the server has
            // reset its own idea of "current code" in lockstep, so clearing here keeps the two
            // in agreement rather than carrying the last solution into the new question.
            setCode("");
            codeRef.current = "";
            lastSentCodeRef.current = "";
          } else if (data.type === "interview_ended") {
            goToReport();
          }
        },
        // A disconnect after the interview has properly ended is expected -- the backend closes
        // the pipeline once the scorecard is away. Anything else is a genuine drop.
        onDisconnected: () => setStatus((s) => (endedRef.current ? s : "ended")),
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
  }, [sessionId, goToReport]);

  // Periodic (not per-keystroke) code snapshots.
  useEffect(() => {
    if (!sessionId) return;
    const interval = setInterval(() => {
      if (endedRef.current) return;
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

  async function endInterview() {
    if (!sessionId || ending || endedRef.current) return;
    if (!confirm("End the interview now and generate your scorecard?")) return;
    setEnding(true);
    try {
      // Push the final state of the editor first -- otherwise whatever was typed since the last
      // 8s snapshot never reaches the scorecard.
      await fetch(`${BACKEND_URL}/api/sessions/${sessionId}/code`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: codeRef.current }),
      }).catch(() => {});
      await fetch(`${BACKEND_URL}/api/sessions/${sessionId}/end`, { method: "POST" });
    } finally {
      clientRef.current?.disconnect();
      goToReport();
    }
  }

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
            {planSize > 1 && (
              <span className="shrink-0 rounded-full border border-border px-2 py-0.5 font-[family-name:var(--font-display-mono)] text-[0.6875rem] uppercase tracking-wider text-muted-foreground">
                {problemNumber}/{planSize}
              </span>
            )}
            <span className="truncate font-medium">{problem.title}</span>
            <span className="hidden shrink-0 text-muted-foreground sm:inline">
              ({problem.difficulty}, {problem.topic})
            </span>
            <ChevronDown
              className={`size-4 shrink-0 text-muted-foreground transition-transform ${problemCollapsed ? "" : "rotate-180"}`}
            />
          </button>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <StatusPill status={status} />
          <button
            onClick={endInterview}
            disabled={ending || status === "ended"}
            className="inline-flex h-8 items-center gap-1.5 rounded-full border border-destructive/40 bg-destructive/10 px-3 font-[family-name:var(--font-display-mono)] text-xs uppercase tracking-wider text-destructive transition-colors hover:bg-destructive/20 disabled:pointer-events-none disabled:opacity-50"
          >
            {ending ? <Loader2 className="size-3.5 animate-spin" /> : <PhoneOff className="size-3.5" />}
            <span className="hidden sm:inline">{ending ? "Scoring" : "End"}</span>
          </button>
        </div>
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
