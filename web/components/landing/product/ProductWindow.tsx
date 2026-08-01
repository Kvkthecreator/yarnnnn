"use client";

/**
 * ProductWindow — pixel-faithful replica of the OS window chrome
 * (components/shell/WindowFrame.tsx, ADR-297 D14/D19.1) for marketing
 * surfaces.
 *
 * Matches the shipped frame: rounded-lg border shadow, 32px title bar on
 * bg-muted/30 with the macOS traffic-light cluster (12px circles, real
 * colors #ff5f57 / #febc2e / #28c840) and a centered text-xs title.
 * Non-interactive by design — it is a display replica, not a window.
 *
 * Marketing pages share globals.css with the product, so the token
 * classes (bg-background, border-border, bg-muted…) resolve to the exact
 * same values the authenticated app renders with.
 */

export function ProductWindow({
  title,
  children,
  className = "",
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`flex flex-col overflow-hidden rounded-lg border border-border bg-background shadow-md ${className}`}
    >
      <div className="relative flex h-8 shrink-0 items-center border-b border-border bg-muted/30 px-3">
        <div className="flex shrink-0 items-center gap-1.5" aria-hidden="true">
          <span className="h-3 w-3 rounded-full bg-[#ff5f57] ring-1 ring-[#ff5f57]/30" />
          <span className="h-3 w-3 rounded-full bg-[#febc2e] ring-1 ring-[#febc2e]/30" />
          <span className="h-3 w-3 rounded-full bg-[#28c840] ring-1 ring-[#28c840]/30" />
        </div>
        <div className="absolute inset-x-0 flex items-center justify-center px-16 text-xs font-medium text-foreground/80">
          <span className="pointer-events-none truncate">{title}</span>
        </div>
      </div>
      <div className="flex-1 min-h-0 overflow-hidden">{children}</div>
    </div>
  );
}

/**
 * AgentFace replica — the product's avatar circle (components/agents/
 * AgentFace.tsx shape): uploaded image or a bg-muted circle with a single
 * uppercase initial.
 */
export function FaceCircle({
  initial,
  size = "md",
  tone = "muted",
}: {
  initial: string;
  size?: "sm" | "md";
  tone?: "muted" | "indigo" | "teal";
}) {
  const sz = size === "md" ? "h-9 w-9 text-xs" : "h-6 w-6 text-[10px]";
  const tones: Record<string, string> = {
    muted: "bg-muted text-muted-foreground",
    indigo: "bg-indigo-500/10 text-indigo-600",
    teal: "bg-teal-500/10 text-teal-700",
  };
  return (
    <span
      className={`flex shrink-0 items-center justify-center rounded-full font-medium ${sz} ${tones[tone]}`}
    >
      {initial.toUpperCase()}
    </span>
  );
}
