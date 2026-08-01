"use client";

import { useEffect, useState } from "react";

/**
 * useStagedLoop — drives the product-replica animations on marketing pages.
 *
 * Cycles a step counter 0 → stepCount-1, holding the final (complete) frame
 * longer, then restarting. Under prefers-reduced-motion the loop never runs
 * and the final frame renders statically — the replica is fully legible
 * with no motion at all.
 */
export function useStagedLoop(stepCount: number, stepMs = 1800, holdMs = 4200) {
  const [step, setStep] = useState(0);
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    if (mq.matches) return;

    let i = 0;
    let t: number;
    const tick = () => {
      i = (i + 1) % stepCount;
      setStep(i);
      // Hold the finished frame, breathe briefly on the empty frame.
      t = window.setTimeout(tick, i === stepCount - 1 ? holdMs : i === 0 ? 700 : stepMs);
    };
    t = window.setTimeout(tick, stepMs);
    return () => window.clearTimeout(t);
  }, [stepCount, stepMs, holdMs]);

  return reduced ? stepCount - 1 : step;
}

/** Reveal-transition classes for a staged element. */
export function reveal(visible: boolean) {
  return `transition-all duration-500 ease-out ${
    visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-1.5"
  }`;
}
