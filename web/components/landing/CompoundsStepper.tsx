"use client";

import { useEffect, useRef, useState } from "react";

/**
 * CompoundsStepper — demonstrates the "compounds" mechanism on the landing page.
 *
 * Per the interaction design spec (docs/design/marketing-interaction-design-2026-06-29.md §1):
 * "fix once; day 1 → 30 → 90" is a progression the visitor should ADVANCE THROUGH, not three
 * static boxes. Day 1 / 30 / 90 are selectable; advancing one auto-cycles, and the "memory"
 * (a growing stack of bars) visibly thickens as time passes.
 *
 * Accessibility: tabs are <button>s with aria-selected; keyboard-operable. Auto-advance pauses
 * on hover/focus and is disabled under prefers-reduced-motion (the stack just renders the
 * selected state). The global CSS guard neutralizes the bar transitions under reduced-motion.
 */

const STAGES = [
  {
    label: "Day 1",
    bars: 3,
    body: "It’s yours from the start. Add a note or connect a tool, and it’s instantly there in every AI you use.",
  },
  {
    label: "Day 30",
    bars: 7,
    body: "Your corrections have added up. Whatever AI you open starts from the same, better memory.",
  },
  {
    label: "Day 90",
    bars: 12,
    body: "It reads like a full history — nothing forgotten, every change accounted for, all of it yours.",
  },
];

const MAX_BARS = 12;

export function CompoundsStepper() {
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);
  const reducedRef = useRef(false);

  useEffect(() => {
    reducedRef.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reducedRef.current || paused) return;

    const id = window.setInterval(() => {
      setActive((a) => (a + 1) % STAGES.length);
    }, 2600);
    return () => window.clearInterval(id);
  }, [paused]);

  const stage = STAGES[active];

  return (
    <div
      className="rounded-2xl border border-[#1a1a1a]/[0.06] bg-[#1a1a1a]/[0.02] p-6 md:p-8"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocusCapture={() => setPaused(true)}
      onBlurCapture={() => setPaused(false)}
    >
      {/* Tabs */}
      <div className="flex gap-2 mb-8" role="tablist" aria-label="How your memory compounds over time">
        {STAGES.map((s, i) => {
          const isActive = active === i;
          return (
            <button
              key={s.label}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => setActive(i)}
              className={`rounded-full px-4 py-1.5 text-xs font-mono uppercase tracking-wider transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/40 ${
                isActive
                  ? "bg-[#1a1a1a] text-white"
                  : "bg-transparent text-[#1a1a1a]/40 hover:text-[#1a1a1a]/70"
              }`}
            >
              {s.label}
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-[1fr_180px] gap-8 items-center">
        {/* Body copy */}
        <div>
          <p className="text-[#1a1a1a]/60 leading-relaxed text-base md:text-lg">{stage.body}</p>
        </div>

        {/* The thickening memory — bars grow as time passes. */}
        <div
          className="flex flex-col-reverse gap-1.5 h-[140px] justify-start"
          aria-hidden="true"
        >
          {Array.from({ length: MAX_BARS }).map((_, i) => {
            const filled = i < stage.bars;
            return (
              <div
                key={i}
                className="rounded-sm transition-all duration-500 ease-out"
                style={{
                  height: 6,
                  background: filled ? "rgba(26,26,26,0.18)" : "rgba(26,26,26,0.04)",
                  transform: filled ? "scaleX(1)" : "scaleX(0.5)",
                  transformOrigin: "left",
                  opacity: filled ? 1 : 0.5,
                }}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}
