"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Gauge, Layers, Loader2, UsersRound } from "lucide-react";
import { AnnouncementPill, GlowBackdrop, GrainOverlay } from "@/components/backdrop";
import { Button } from "@/components/button";
import { Logo } from "@/components/logo";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

type SessionOptions = {
  topics: string[];
  difficulties: string[];
  personas: string[];
};

const PERSONA_LABELS: Record<string, string> = {
  neutral: "Neutral & realistic",
  strict: "Strict & high-bar",
};

export default function PracticePage() {
  const router = useRouter();
  const [options, setOptions] = useState<SessionOptions | null>(null);
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [persona, setPersona] = useState("");
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${BACKEND_URL}/api/session-options`)
      .then((res) => res.json())
      .then((data: SessionOptions) => {
        setOptions(data);
        setTopic(data.topics[0]);
        setDifficulty(data.difficulties[0]);
        setPersona(data.personas[0]);
      })
      .catch(() => setError("Couldn't reach the backend. Is it running on :8000?"));
  }, []);

  async function startInterview() {
    setStarting(true);
    setError(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, difficulty, persona }),
      });
      if (!res.ok) throw new Error(`Backend returned ${res.status}`);
      const data = await res.json();
      sessionStorage.setItem(
        "dryrunai_session",
        JSON.stringify({ sessionId: data.session_id, problem: data.problem, persona })
      );
      router.push("/interview");
    } catch (err) {
      setError(`Failed to start session: ${err}`);
      setStarting(false);
    }
  }

  return (
    <div className="relative flex min-h-screen flex-col items-center overflow-hidden px-6 py-24">
      <GlowBackdrop />
      <GrainOverlay />

      <a
        href="/"
        className="relative z-10 mb-10 self-start transition-opacity hover:opacity-80 sm:absolute sm:left-10 sm:top-8 sm:mb-0"
      >
        <Logo className="text-sm" />
      </a>

      <div className="relative flex flex-col items-center gap-3 text-center">
        <AnnouncementPill badge="v0">Three quick choices, then you&apos;re in</AnnouncementPill>
        <h1 className="text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
          Set up your session
        </h1>
        <p className="text-muted-foreground">A practice DSA technical interview, out loud.</p>
      </div>

      {error && (
        <div className="relative mt-8 max-w-md rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {!options ? (
        <div className="relative mt-10 flex items-center gap-2 text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          Loading options&hellip;
        </div>
      ) : (
        <div className="bg-card-wash relative mt-10 flex w-full max-w-lg flex-col gap-7 rounded-md border border-border p-8 shadow-lg">
          <Picker
            icon={Layers}
            label="Category"
            value={topic}
            options={options.topics}
            onChange={setTopic}
          />
          <Picker
            icon={Gauge}
            label="Difficulty"
            value={difficulty}
            options={options.difficulties}
            onChange={setDifficulty}
          />
          <Picker
            icon={UsersRound}
            label="Interviewer style"
            value={persona}
            options={options.personas}
            labels={PERSONA_LABELS}
            onChange={setPersona}
          />

          <Button onClick={startInterview} disabled={starting} size="lg" className="mt-2 w-full">
            {starting ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Starting&hellip;
              </>
            ) : (
              <>
                Start Interview
                <ArrowRight className="size-4" />
              </>
            )}
          </Button>
        </div>
      )}
    </div>
  );
}

function Picker({
  icon: Icon,
  label,
  value,
  options,
  labels,
  onChange,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  options: string[];
  labels?: Record<string, string>;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-col gap-2.5">
      <div className="flex items-center gap-2 font-[family-name:var(--font-display-mono)] text-xs uppercase tracking-wider text-muted-foreground">
        <Icon className="size-3.5 text-chart-1" />
        {label}
      </div>
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => (
          <button
            key={opt}
            onClick={() => onChange(opt)}
            className={`rounded-md border px-4 py-1.5 text-sm transition-colors ${
              value === opt
                ? "border-transparent bg-primary text-primary-foreground shadow-xs"
                : "border-border text-foreground hover:bg-white/5"
            }`}
          >
            {labels?.[opt] ?? opt}
          </button>
        ))}
      </div>
    </div>
  );
}
