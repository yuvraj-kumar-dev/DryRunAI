export function GrainOverlay() {
  return <div aria-hidden className="bg-grain pointer-events-none absolute inset-0" />;
}

/**
 * Full-bleed saturated radial wash behind hero/CTA sections -- fading from black at the
 * top/edges into the violet -> magenta accent toward the bottom-center. This is the actual
 * "glow" mechanic (a large radial gradient, not a couple of small blurred blobs) plus the
 * grain overlay riding on top of it, same as the reference.
 */
export function GlowBackdrop() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 75% 55% at 58% 88%, color-mix(in oklab, var(--chart-2) 45%, transparent) 0%, color-mix(in oklab, var(--chart-1) 32%, transparent) 40%, transparent 72%)",
        }}
      />
      <div className="animate-glow-pulse absolute inset-x-0 bottom-0 h-1/2 bg-[radial-gradient(ellipse_55%_45%_at_55%_100%,color-mix(in_oklab,var(--chart-3)_28%,transparent),transparent_70%)]" />
    </div>
  );
}

/** The "What's New?" style announcement pill: a muted rounded badge inset in a bordered pill. */
export function AnnouncementPill({ badge, children }: { badge: string; children: React.ReactNode }) {
  return (
    <div className="inline-flex items-center rounded-full border border-border p-1 text-xs">
      <span className="rounded-full bg-white/10 px-3 py-1 font-[family-name:var(--font-display-mono)] uppercase tracking-wider text-foreground">
        {badge}
      </span>
      <span className="px-3 text-muted-foreground">{children}</span>
    </div>
  );
}
