"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { CheckCircle2, CircleSlash, Loader2, XCircle } from "lucide-react";
import { GlowBackdrop, GrainOverlay } from "@/components/backdrop";
import { LinkButton } from "@/components/button";
import { Logo } from "@/components/logo";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

// The scorecard is written by the backend at the moment the interview ends, so a report opened
// the instant the session closes can land a beat before the record exists. Poll briefly rather
// than showing the candidate an error for a report that's seconds away.
const POLL_INTERVAL_MS = 1500;
const MAX_POLLS = 20;

type Scorecard = {
  correctness: string;
  complexity: string;
  problem_solving_approach: string;
  communication: string;
  overall_verdict: string;
  summary: string;
};

type Attempt = {
  problem_id: string;
  title: string;
  difficulty: string;
  topic: string;
  code: string;
  solved: boolean | null;
};

type SessionRecord = {
  session_id: string;
  persona: string;
  plan_size: number;
  problems_attempted: Attempt[];
  scorecard: Scorecard | null;
};

const RUBRIC_ROWS: { key: keyof Scorecard; label: string }[] = [
  { key: "correctness", label: "Correctness" },
  { key: "complexity", label: "Complexity" },
  { key: "problem_solving_approach", label: "Problem solving" },
  { key: "communication", label: "Communication" },
];

export default function ReportPage() {
  // useSearchParams needs a Suspense boundary above it, otherwise everything up to the nearest
  // one is forced to client-side render (Next 16, use-search-params docs).
  return (
    <Suspense fallback={<Centered>Loading&hellip;</Centered>}>
      <Report />
    </Suspense>
  );
}

function Report() {
  const sessionId = useSearchParams().get("session");
  const [record, setRecord] = useState<SessionRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    let polls = 0;

    async function load() {
      while (!cancelled && polls < MAX_POLLS) {
        polls += 1;
        try {
          const res = await fetch(`${BACKEND_URL}/api/sessions/${sessionId}`);
          if (res.ok) {
            const data: SessionRecord = await res.json();
            if (!cancelled) setRecord(data);
            return;
          }
          // 409 = still in progress, 404 = not written yet. Both are worth waiting out.
          if (res.status !== 409 && res.status !== 404) {
            throw new Error(`Backend returned ${res.status}`);
          }
        } catch (err) {
          if (polls >= MAX_POLLS) {
            if (!cancelled) setError(`Couldn't load the report: ${err}`);
            return;
          }
        }
        await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
      }
      if (!cancelled) setError("The report didn't arrive. The session may not have finished.");
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  if (!sessionId) return <Centered>No session in the link. Reports are per-session.</Centered>;
  if (error) return <Centered>{error}</Centered>;
  if (!record) {
    return (
      <Centered>
        <Loader2 className="size-4 animate-spin" />
        Scoring your interview&hellip;
      </Centered>
    );
  }

  const { scorecard } = record;

  return (
    <div className="relative flex min-h-screen flex-col items-center overflow-hidden px-6 py-16">
      <GlowBackdrop />
      <GrainOverlay />

      <Link href="/" className="relative z-10 mb-10 self-start transition-opacity hover:opacity-80">
        <Logo className="text-sm" />
      </Link>

      <div className="relative w-full max-w-3xl">
        <div className="flex flex-col items-center gap-3 text-center">
          <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">Your scorecard</h1>
          <p className="text-muted-foreground">
            {record.problems_attempted.length} problem
            {record.problems_attempted.length === 1 ? "" : "s"} &middot; {record.persona} interviewer
          </p>
        </div>

        {!scorecard ? (
          <div className="mt-10 rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            The interview was saved, but scoring failed. Your transcript and code are still in the
            session file.
          </div>
        ) : (
          <>
            <Verdict verdict={scorecard.overall_verdict} />

            <div className="bg-card-wash mt-6 rounded-md border border-border p-6">
              <p className="text-sm leading-relaxed text-foreground/90">{scorecard.summary}</p>
            </div>

            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              {RUBRIC_ROWS.map(({ key, label }) => (
                <div key={key} className="rounded-md border border-border bg-card p-5">
                  <div className="font-[family-name:var(--font-display-mono)] text-xs uppercase tracking-wider text-muted-foreground">
                    {label}
                  </div>
                  <p className="mt-2 text-sm leading-relaxed text-foreground/85">{scorecard[key]}</p>
                </div>
              ))}
            </div>
          </>
        )}

        <h2 className="mt-12 font-[family-name:var(--font-display-mono)] text-xs uppercase tracking-wider text-muted-foreground">
          Problems &amp; your code
        </h2>
        <div className="mt-3 flex flex-col gap-4">
          {record.problems_attempted.map((attempt, i) => (
            <div key={`${attempt.problem_id}-${i}`} className="rounded-md border border-border bg-card p-5">
              <div className="flex flex-wrap items-center gap-3">
                <span className="font-[family-name:var(--font-display-mono)] text-xs text-muted-foreground">
                  {i + 1}
                </span>
                <span className="font-medium">{attempt.title}</span>
                <span className="text-sm text-muted-foreground">
                  ({attempt.difficulty}, {attempt.topic})
                </span>
                {attempt.solved !== null && (
                  <span
                    className={`ml-auto inline-flex items-center gap-1.5 text-xs ${
                      attempt.solved ? "text-chart-1" : "text-muted-foreground"
                    }`}
                  >
                    {attempt.solved ? <CheckCircle2 className="size-3.5" /> : <CircleSlash className="size-3.5" />}
                    {attempt.solved ? "Solved" : "Moved on"}
                  </span>
                )}
              </div>
              <pre className="mt-3 overflow-x-auto rounded-md bg-background p-4 font-[family-name:var(--font-code)] text-xs text-foreground/85">
                {attempt.code?.trim() || "(no code written)"}
              </pre>
            </div>
          ))}
        </div>

        <div className="mt-12 flex justify-center">
          <LinkButton href="/practice" size="lg">
            Practice again
          </LinkButton>
        </div>
      </div>
    </div>
  );
}

function Verdict({ verdict }: { verdict: string }) {
  const isNoHire = verdict.toLowerCase().includes("no hire");
  const Icon = isNoHire ? XCircle : CheckCircle2;
  return (
    <div className="mt-10 flex justify-center">
      <div
        className={`inline-flex items-center gap-2.5 rounded-full border px-5 py-2.5 ${
          isNoHire
            ? "border-destructive/40 bg-destructive/10 text-destructive"
            : "border-border bg-gradient-to-r from-chart-1/20 via-chart-2/20 to-chart-3/20 text-foreground"
        }`}
      >
        <Icon className="size-4" />
        <span className="font-[family-name:var(--font-display-mono)] text-sm uppercase tracking-wider">
          {verdict}
        </span>
      </div>
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-screen items-center justify-center gap-2 px-6 text-muted-foreground">
      <GlowBackdrop />
      {children}
    </div>
  );
}
