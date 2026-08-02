import Image from "next/image";
import {
  BadgeCheck,
  BrainCircuit,
  Captions,
  ExternalLink,
  FileClock,
  MessageCircleQuestion,
  UsersRound,
} from "lucide-react";
import { AnnouncementPill, GlowBackdrop, GrainOverlay } from "@/components/backdrop";
import { LinkButton } from "@/components/button";
import { Logo } from "@/components/logo";

const GITHUB_URL = "https://github.com/yuvraj-kumar-dev/DryRunAI";

const NAV_LINKS = [
  { label: "Problems", href: "#problems" },
  { label: "How it works", href: "#how-it-works" },
  { label: "Why I built this", href: "#why" },
];

const CAPABILITIES = [
  {
    icon: MessageCircleQuestion,
    title: "Clarifying questions first",
    body: "Nothing gets coded until the constraints are nailed down. It won't hand you the edge cases - you have to ask.",
  },
  {
    icon: Captions,
    title: "Sees your code as you write it",
    body: "Snapshots, not surveillance. Close enough to follow your approach, not close enough to hover.",
  },
  {
    icon: BrainCircuit,
    title: "Adaptive hints",
    body: "Stuck? One nudge at a time - the smallest hint that gets you moving again, never the answer.",
  },
  {
    icon: UsersRound,
    title: "Two interviewer personas",
    body: "Pick your pressure: neutral and realistic, or strict and high-bar. Same logic, different bar.",
  },
  {
    icon: BadgeCheck,
    title: "A real scorecard at the end",
    body: "Correctness, complexity, communication - scored like an actual debrief, not a pass/fail buzzer.",
  },
];

const STEPS = [
  { n: "01", title: "Pick a problem", body: "Category, difficulty, interviewer style. Takes ten seconds." },
  { n: "02", title: "Talk through your approach", body: "Constraints, edge cases, your plan - out loud, before a single line of code." },
  { n: "03", title: "Code while it watches", body: "Write your solution live. It discusses complexity and nudges you if you stall." },
  { n: "04", title: "Get a scorecard", body: "A real debrief plus the full transcript, saved so you can actually learn from it." },
];

function IconBadge({ icon: Icon }: { icon: React.ComponentType<{ className?: string }> }) {
  return (
    <div className="bg-card-wash flex aspect-square size-10 items-center justify-center rounded-md border border-border">
      <Icon className="size-4.5 text-foreground" />
    </div>
  );
}

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <header
        className="relative z-10 flex items-center justify-between px-6 sm:px-10"
        style={{ height: "var(--header-height)" }}
      >
        <Logo className="text-sm" />
        <nav className="hidden items-center gap-8 text-sm text-muted-foreground md:flex">
          {NAV_LINKS.map((l) => (
            <a key={l.href} href={l.href} className="transition-colors hover:text-foreground">
              {l.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-4">
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="hidden text-sm text-muted-foreground transition-colors hover:text-foreground sm:inline"
          >
            GitHub
          </a>
          <LinkButton href="/practice" size="nav">
            Start practicing
          </LinkButton>
        </div>
      </header>

      <section className="relative overflow-hidden px-6 pb-15 pt-10 sm:px-10 md:pb-20 lg:pb-24">
        <GlowBackdrop />
        <GrainOverlay />
        <div className="relative mx-auto flex max-w-6xl flex-col gap-10 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex max-w-2xl flex-1 flex-col items-start gap-5">
            <AnnouncementPill badge="v0">Voice-first interviews, not another LeetCode grind</AnnouncementPill>
            <h1 className="text-balance text-5xl leading-none tracking-tight text-foreground md:text-6xl lg:text-7xl">
              Practice the interview <span className="text-gradient">before it counts</span>
            </h1>
            <p className="text-balance leading-snug text-muted-foreground md:text-lg lg:text-xl">
              An AI interviewer that asks real questions, watches you code, and pushes back when
              you&apos;re stuck - out loud, like the real thing.
            </p>
          </div>
          <div className="space-y-3">
            <div className="flex gap-4.5">
              <LinkButton href="/practice" size="lg" className="flex-1 md:min-w-45">
                Start a mock interview
              </LinkButton>
              <LinkButton href={GITHUB_URL} variant="outline" size="lg" className="flex-1 md:min-w-45">
                View on GitHub
              </LinkButton>
            </div>
            <div className="text-center text-sm text-muted-foreground">
              Real voice conversation &middot; Adaptive hints &middot; Structured scorecard
            </div>
          </div>
        </div>
        <div className="relative mx-auto mt-10 max-w-6xl md:mt-16 lg:mt-20">
          <div
            aria-hidden
            className="absolute -inset-x-10 -top-20 h-48 rounded-full opacity-80 blur-[90px] sm:-inset-x-24 sm:h-64"
            style={{
              background:
                "radial-gradient(ellipse 70% 100% at 50% 20%, color-mix(in oklab, var(--chart-2) 65%, transparent), transparent 70%)",
            }}
          />
          <div
            className="relative rounded-xl p-px shadow-[0_0_100px_-25px_color-mix(in_oklab,var(--chart-2)_55%,transparent)]"
            style={{
              backgroundImage:
                "linear-gradient(140deg, var(--chart-1), var(--border) 35%, var(--border) 65%, var(--chart-3))",
            }}
          >
            <Image
              src="/images/hero-product.png"
              alt="The DryRunAI interview screen: a problem statement with constraints and examples expanded at the top, a gradient-bordered code editor below it, and a Listening status pill in the top-right corner"
              width={1600}
              height={760}
              priority
              className="relative w-full rounded-[calc(var(--radius-lg)-1px)]"
            />
          </div>
        </div>
      </section>

      <section id="problems" className="border-t border-border px-6 py-15 sm:px-10 md:py-20 lg:py-24">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-4xl leading-tight tracking-tight md:text-5xl">
            Built like a real interview loop, not a quiz
          </h2>
          <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {CAPABILITIES.map((c) => (
              <div key={c.title} className="bg-card-wash flex flex-col gap-3 rounded-md border border-border p-6 shadow-sm">
                <IconBadge icon={c.icon} />
                <h3 className="font-medium text-foreground">{c.title}</h3>
                <p className="text-sm leading-snug text-muted-foreground">{c.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-border px-6 py-15 sm:px-10 md:py-20 lg:py-24">
        <div className="mx-auto grid max-w-5xl grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="bg-card-wash rounded-md border border-border p-6 shadow-sm lg:p-8">
            <IconBadge icon={Captions} />
            <h3 className="mt-3 text-lg font-bold text-foreground">Talk like it&apos;s the real thing</h3>
            <p className="mt-1 leading-snug text-muted-foreground">
              Audio only. No captions, no transcript on screen. If you can&apos;t re-read it in a
              real interview, you can&apos;t here either.
            </p>
            <div className="mt-6 flex items-center gap-2 rounded-md border border-border bg-background px-4 py-3">
              <span className="h-2 w-2 animate-pulse rounded-full bg-chart-1" />
              <span className="font-[family-name:var(--font-display-mono)] text-xs uppercase tracking-wider text-muted-foreground">
                Listening&hellip;
              </span>
            </div>
          </div>
          <div className="bg-card-wash rounded-md border border-border p-6 shadow-sm lg:p-8">
            <IconBadge icon={FileClock} />
            <h3 className="mt-3 text-lg font-bold text-foreground">Everything saved for review</h3>
            <p className="mt-1 leading-snug text-muted-foreground">
              Nothing&apos;s lost when the call ends. Transcript, code, scorecard - all saved,
              all yours.
            </p>
            <div className="mt-6 space-y-2 rounded-md border border-border bg-background p-4">
              {[
                ["Correctness", 90],
                ["Complexity", 75],
                ["Communication", 95],
              ].map(([label, pct]) => (
                <div key={label as string} className="flex items-center gap-3 text-xs">
                  <span className="w-28 shrink-0 text-muted-foreground">{label}</span>
                  <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-border">
                    <span
                      className="block h-full rounded-full"
                      style={{
                        width: `${pct}%`,
                        backgroundImage:
                          "linear-gradient(to right in oklab, var(--chart-1), var(--chart-2), var(--chart-3))",
                      }}
                    />
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section id="how-it-works" className="border-t border-border px-6 py-15 sm:px-10 md:py-20 lg:py-24">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-4xl leading-tight tracking-tight md:text-5xl">How a session works</h2>
          <div className="mt-10 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((s) => (
              <div key={s.n}>
                <span className="font-[family-name:var(--font-display-mono)] text-sm text-chart-1">
                  {s.n}
                </span>
                <h3 className="mt-2 font-bold text-foreground">{s.title}</h3>
                <p className="mt-1 leading-snug text-muted-foreground">{s.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="why" className="border-t border-border px-6 py-15 sm:px-10 md:py-20 lg:py-24">
        <div className="bg-card-wash mx-auto max-w-2xl rounded-md border border-border p-8 shadow-sm">
          <h2 className="text-lg font-bold text-foreground">Why I built this</h2>
          <p className="mt-3 leading-snug text-muted-foreground">
            Most practice tools grade a final answer. Real interviews don&apos;t work like that -
            you think out loud, get follow-ups, and have to handle a nudge without losing the
            thread. DryRunAI is a solo build meant to rehearse exactly that: the conversation, not
            just the code.
          </p>
        </div>
      </section>

      <section className="relative overflow-hidden border-t border-border px-6 pb-10 pt-15 text-center sm:px-10 md:pt-20 lg:pt-24">
        <GlowBackdrop />
        <GrainOverlay />
        <div className="relative mx-auto flex max-w-2xl flex-col items-center">
          <Logo className="text-lg" />
          <h2 className="my-6 text-2xl leading-tight lg:my-8 lg:text-5xl">
            Talk it through. <span className="text-gradient">Dry run it. Then walk in ready.</span>
          </h2>
          <div className="mx-auto flex max-w-sm justify-center gap-4.5">
            <LinkButton href="/practice" className="flex-1">
              Start a mock interview
            </LinkButton>
            <LinkButton href={GITHUB_URL} variant="outline" className="flex-1">
              View on GitHub
            </LinkButton>
          </div>
          <p className="mt-3 text-sm text-muted-foreground">
            Real voice conversation &middot; Adaptive hints &middot; Structured scorecard
          </p>
        </div>

        <div className="relative mx-auto mt-20 flex max-w-6xl flex-col-reverse items-center justify-between gap-6 text-xs text-muted-foreground lg:mt-30 lg:flex-row">
          <span>&copy; 2026 DryRunAI | Built by Yuvraj Kumar</span>
          <div className="flex flex-wrap items-center justify-center gap-4 lg:gap-8">
            {NAV_LINKS.map((l) => (
              <a key={l.href} href={l.href} className="transition-opacity hover:opacity-80">
                {l.label}
              </a>
            ))}
          </div>
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub"
            className="flex items-center gap-1.5 transition-opacity hover:opacity-80"
          >
            GitHub
            <ExternalLink className="size-3.5" />
          </a>
        </div>
      </section>
    </div>
  );
}
