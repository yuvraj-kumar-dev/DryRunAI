"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

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

export default function Home() {
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
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 bg-[#0a0a0f] p-10 text-[#e5e5ea]">
      <div className="text-center">
        <h1 className="bg-gradient-to-r from-indigo-400 to-cyan-300 bg-clip-text text-4xl font-semibold text-transparent">
          DryRunAI
        </h1>
        <p className="mt-2 text-sm text-[#8b8b96]">A practice DSA technical interview, out loud.</p>
      </div>

      {error && (
        <div className="max-w-md rounded-lg border border-red-900 bg-red-950/40 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {!options ? (
        <p className="text-[#8b8b96]">Loading options...</p>
      ) : (
        <div className="flex w-full max-w-sm flex-col gap-6 rounded-xl border border-white/10 bg-[#13131a] p-6">
          <Picker label="Category" value={topic} options={options.topics} onChange={setTopic} />
          <Picker
            label="Difficulty"
            value={difficulty}
            options={options.difficulties}
            onChange={setDifficulty}
          />
          <Picker
            label="Interviewer style"
            value={persona}
            options={options.personas}
            labels={PERSONA_LABELS}
            onChange={setPersona}
          />

          <button
            onClick={startInterview}
            disabled={starting}
            className="mt-2 rounded-lg bg-gradient-to-r from-indigo-500 to-cyan-400 px-5 py-3 font-medium text-[#0a0a0f] disabled:opacity-40"
          >
            {starting ? "Starting..." : "Start Interview"}
          </button>
        </div>
      )}
    </div>
  );
}

function Picker({
  label,
  value,
  options,
  labels,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  labels?: Record<string, string>;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-xs uppercase tracking-wide text-[#8b8b96]">{label}</label>
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => (
          <button
            key={opt}
            onClick={() => onChange(opt)}
            className={`rounded-full border px-4 py-1.5 text-sm transition-colors ${
              value === opt
                ? "border-transparent bg-gradient-to-r from-indigo-500 to-cyan-400 text-[#0a0a0f]"
                : "border-white/15 text-[#e5e5ea] hover:border-white/30"
            }`}
          >
            {labels?.[opt] ?? opt}
          </button>
        ))}
      </div>
    </div>
  );
}
