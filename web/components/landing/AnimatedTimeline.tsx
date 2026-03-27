"use client";

/**
 * AnimatedTimeline — horizontal step flow with a connecting line
 * and animated pulse dots moving along it. Supports light and dark variants.
 */

interface TimelineStep {
  number: string;
  title: string;
  description: string;
}

interface AnimatedTimelineProps {
  steps?: TimelineStep[];
  variant?: "light" | "dark";
}

const defaultSteps: TimelineStep[] = [
  {
    number: "01",
    title: "Describe the work",
    description:
      "Tell yarnnn what you need in plain language. Share context through conversation, documents, or connected tools.",
  },
  {
    number: "02",
    title: "Tasks run on schedule",
    description:
      "Each task is assigned to the right agent and runs on your cadence — daily, weekly, or on-demand.",
  },
  {
    number: "03",
    title: "You review. They learn.",
    description:
      "Edit, redirect, or approve. Your feedback becomes learned behavior that compounds every cycle.",
  },
];

export function AnimatedTimeline({ steps = defaultSteps, variant = "light" }: AnimatedTimelineProps) {
  const isDark = variant === "dark";

  const lineColor = isDark ? "bg-white/[0.08]" : "bg-[#1a1a1a]/[0.06]";
  const dotBg = isDark ? "bg-white/[0.06] border-white/[0.15]" : "bg-white border-[#1a1a1a]/[0.08] shadow-sm";
  const dotText = isDark ? "text-white/60" : "text-[#1a1a1a]/60";
  const titleColor = isDark ? "text-white" : "text-[#1a1a1a]";
  const descColor = isDark ? "text-white/50" : "text-[#1a1a1a]/50";
  const pulseGradient = isDark
    ? "linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)"
    : "linear-gradient(90deg, transparent, rgba(99,102,241,0.4), transparent)";
  const ringColor = isDark ? "border-white/20" : "border-indigo-400/30";

  // For >3 steps, adjust grid cols
  const gridCols =
    steps.length === 4
      ? "grid-cols-4"
      : steps.length === 5
        ? "grid-cols-5"
        : "grid-cols-3";

  return (
    <div className="w-full">
      {/* Desktop: horizontal */}
      <div className="hidden md:block relative">
        {/* Connecting line */}
        <div className={`absolute top-[28px] left-[60px] right-[60px] h-[2px] ${lineColor}`}>
          <div
            className="absolute top-0 left-0 h-full w-[80px] rounded-full"
            style={{
              background: pulseGradient,
              animation: "timeline-pulse 3s ease-in-out infinite",
            }}
          />
        </div>

        <div className={`grid ${gridCols} gap-8 relative`}>
          {steps.map((step, i) => (
            <div key={step.number} className="flex flex-col items-center text-center">
              <div className="relative mb-6">
                <div className={`w-14 h-14 rounded-full border-2 flex items-center justify-center z-10 relative ${dotBg}`}>
                  <span className={`text-sm font-semibold ${dotText}`}>{step.number}</span>
                </div>
                {i === 0 && (
                  <div
                    className={`absolute inset-0 rounded-full border-2 ${ringColor}`}
                    style={{ animation: "dot-ring 2s ease-out infinite" }}
                  />
                )}
              </div>

              <h3 className={`text-base font-medium mb-2 ${titleColor}`}>{step.title}</h3>
              <p className={`text-sm leading-relaxed max-w-[260px] ${descColor}`}>
                {step.description}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Mobile: vertical */}
      <div className="md:hidden space-y-8">
        {steps.map((step) => (
          <div key={step.number} className="flex gap-4">
            <div className="flex flex-col items-center">
              <div className={`w-10 h-10 rounded-full border-2 flex items-center justify-center shrink-0 ${dotBg}`}>
                <span className={`text-xs font-semibold ${dotText}`}>{step.number}</span>
              </div>
              <div className={`w-[2px] flex-1 mt-2 ${lineColor}`} />
            </div>
            <div className="pb-4">
              <h3 className={`text-base font-medium mb-1 ${titleColor}`}>{step.title}</h3>
              <p className={`text-sm leading-relaxed ${descColor}`}>{step.description}</p>
            </div>
          </div>
        ))}
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes timeline-pulse {
          0% { left: -80px; opacity: 0; }
          10% { opacity: 1; }
          90% { opacity: 1; }
          100% { left: calc(100% + 80px); opacity: 0; }
        }
        @keyframes dot-ring {
          0% { transform: scale(1); opacity: 0.5; }
          100% { transform: scale(1.8); opacity: 0; }
        }
      `}} />
    </div>
  );
}
