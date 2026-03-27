"use client";

/**
 * AnimatedTimeline — horizontal 3-step flow with a connecting line
 * and animated pulse dots moving along it.
 */

interface TimelineStep {
  number: string;
  title: string;
  description: string;
}

const steps: TimelineStep[] = [
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

export function AnimatedTimeline() {
  return (
    <div className="w-full">
      {/* Desktop: horizontal */}
      <div className="hidden md:block relative">
        {/* Connecting line */}
        <div className="absolute top-[28px] left-[60px] right-[60px] h-[2px] bg-[#1a1a1a]/[0.06]">
          {/* Animated pulse traveling along the line */}
          <div
            className="absolute top-0 left-0 h-full w-[80px] rounded-full"
            style={{
              background: "linear-gradient(90deg, transparent, rgba(99,102,241,0.4), transparent)",
              animation: "timeline-pulse 3s ease-in-out infinite",
            }}
          />
        </div>

        <div className="grid grid-cols-3 gap-8 relative">
          {steps.map((step, i) => (
            <div key={step.number} className="flex flex-col items-center text-center">
              {/* Dot */}
              <div className="relative mb-6">
                <div className="w-14 h-14 rounded-full bg-white border-2 border-[#1a1a1a]/[0.08] flex items-center justify-center shadow-sm z-10 relative">
                  <span className="text-sm font-semibold text-[#1a1a1a]/60">{step.number}</span>
                </div>
                {/* Outer ring pulse (on first dot only, to draw the eye) */}
                {i === 0 && (
                  <div
                    className="absolute inset-0 rounded-full border-2 border-indigo-400/30"
                    style={{ animation: "dot-ring 2s ease-out infinite" }}
                  />
                )}
              </div>

              <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">{step.title}</h3>
              <p className="text-[#1a1a1a]/50 text-sm leading-relaxed max-w-[260px]">
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
              <div className="w-10 h-10 rounded-full bg-white border-2 border-[#1a1a1a]/[0.08] flex items-center justify-center shadow-sm shrink-0">
                <span className="text-xs font-semibold text-[#1a1a1a]/60">{step.number}</span>
              </div>
              <div className="w-[2px] flex-1 bg-[#1a1a1a]/[0.06] mt-2" />
            </div>
            <div className="pb-4">
              <h3 className="text-base font-medium mb-1 text-[#1a1a1a]">{step.title}</h3>
              <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">{step.description}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Animations — global keyframes (idempotent, same names won't conflict) */}
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
