"use client";

import { useEffect, useRef, useState } from "react";

/**
 * StepFlow — the connected step journey on /how-it-works.
 *
 * Per the interaction design spec (docs/design/marketing-interaction-design-2026-06-29.md §3):
 * the five-step loop should read as a CONNECTED JOURNEY, not a flat 01/02/03 list. A vertical
 * progress line fills as the reader scrolls past each step, with a ring pulse on the active step.
 *
 * Harvests the pulse-line / dot-ring technique from the (now retired) AnimatedTimeline, upgraded
 * from a purely-decorative horizontal pulse to a scroll-driven vertical FILL — the line tracks
 * how far the reader has progressed.
 *
 * Dark-variant only (how-it-works is the sole consumer / a dark page).
 *
 * Accessibility & perf:
 *  - the steps are an ordered list; content is plain text, fully present with JS off.
 *  - the fill line + ring are aria-hidden decoration.
 *  - under prefers-reduced-motion: the line renders fully filled and the ring doesn't pulse
 *    (the global CSS guard neutralizes the keyframe; the JS also skips the scroll listener).
 *  - one passive scroll listener, rAF-throttled; no per-step observers.
 */

interface Step {
  number: string;
  title: string;
  body: string;
  /** Optional extra content rendered under the step body (e.g. the verdict trio). */
  extra?: React.ReactNode;
}

interface StepFlowProps {
  steps: Step[];
}

export function StepFlow({ steps }: StepFlowProps) {
  const containerRef = useRef<HTMLOListElement>(null);
  const [progress, setProgress] = useState(0); // 0..1 fill of the spine
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      setProgress(1);
      setActiveIndex(steps.length - 1);
      return;
    }

    let raf = 0;
    const onScroll = () => {
      if (raf) return;
      raf = window.requestAnimationFrame(() => {
        raf = 0;
        const el = containerRef.current;
        if (!el) return;
        const rect = el.getBoundingClientRect();
        const vh = window.innerHeight;
        // The spine fills from when the list top reaches mid-viewport to when its bottom does.
        const start = vh * 0.5;
        const total = rect.height;
        const scrolled = start - rect.top;
        const p = Math.max(0, Math.min(1, scrolled / total));
        setProgress(p);
        setActiveIndex(Math.min(steps.length - 1, Math.floor(p * steps.length)));
      });
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => {
      window.removeEventListener("scroll", onScroll);
      if (raf) window.cancelAnimationFrame(raf);
    };
  }, [steps.length]);

  return (
    <ol ref={containerRef} className="relative max-w-3xl mx-auto pl-2">
      {/* The spine: a faint static rail with a bright fill that tracks scroll progress. */}
      <div
        className="absolute left-[27px] top-3 bottom-3 w-[2px] bg-white/10"
        aria-hidden="true"
      >
        <div
          className="absolute left-0 top-0 w-full bg-gradient-to-b from-indigo-400/70 to-sky-400/40 transition-[height] duration-300 ease-out"
          style={{ height: `${progress * 100}%` }}
        />
      </div>

      {steps.map((step, i) => {
        const reached = i <= activeIndex;
        const isActive = i === activeIndex;
        return (
          <li key={step.number} className="relative flex gap-6 pb-14 last:pb-0">
            {/* Node */}
            <div className="relative z-10 shrink-0">
              <div
                className={`flex h-[52px] w-[52px] items-center justify-center rounded-full border-2 transition-colors duration-500 ${
                  reached
                    ? "border-indigo-400/50 bg-indigo-500/[0.12] text-white"
                    : "border-white/15 bg-[#0f1419] text-white/40"
                }`}
              >
                <span className="text-sm font-semibold">{step.number}</span>
              </div>
              {isActive && (
                <div
                  className="absolute inset-0 rounded-full border-2 border-indigo-400/30"
                  style={{ animation: "step-ring 2s ease-out infinite" }}
                  aria-hidden="true"
                />
              )}
            </div>

            {/* Content */}
            <div className="pt-2">
              <h2
                className={`text-2xl md:text-3xl font-medium mb-3 transition-colors duration-500 ${
                  reached ? "text-white" : "text-white/70"
                }`}
              >
                {step.title}
              </h2>
              <p className="text-white/55 leading-relaxed max-w-2xl text-lg font-light">
                {step.body}
              </p>
              {step.extra}
            </div>
          </li>
        );
      })}

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes step-ring {
          0% { transform: scale(1); opacity: 0.5; }
          100% { transform: scale(1.7); opacity: 0; }
        }
      `}} />
    </ol>
  );
}
