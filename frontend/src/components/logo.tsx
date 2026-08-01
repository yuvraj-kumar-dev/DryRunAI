export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`font-[family-name:var(--font-display-mono)] tracking-wide text-foreground ${className}`}>
      <span className="text-gradient">Dry</span>RunAI
    </span>
  );
}
