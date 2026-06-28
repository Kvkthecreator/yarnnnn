"use client";

import { useEffect, useRef, useState } from "react";

/**
 * ScrollReveal — the connective motion layer for the marketing pages.
 *
 * Fades + rises a section into view once, when it first enters the viewport.
 * Per the interaction design spec (docs/design/marketing-interaction-design-2026-06-29.md §2):
 *
 *  - opacity + transform ONLY — never height/margin, so no layout shift (CLS).
 *  - honors `prefers-reduced-motion`: renders its final, visible state immediately.
 *  - reveals once, then disconnects the observer.
 *  - the element holds its final box from first paint; only its appearance transitions.
 *
 * It is intentionally NOT used on hero sections — above-the-fold renders instantly.
 */

interface ScrollRevealProps {
  children: React.ReactNode;
  /** Extra classes on the wrapper (e.g. the section's own layout/border classes). */
  className?: string;
  /** Stagger delay in ms, for sequencing sibling reveals. */
  delay?: number;
  /** Render as a different element (default div). Use "section" to replace a <section>. */
  as?: "div" | "section";
}

export function ScrollReveal({
  children,
  className = "",
  delay = 0,
  as = "div",
}: ScrollRevealProps) {
  const ref = useRef<HTMLDivElement>(null);
  // Start hidden ONLY when motion is allowed and JS has hydrated. The SSR/no-JS
  // and reduced-motion paths render fully visible, so content is never gated on JS.
  const [visible, setVisible] = useState(true);
  const [armed, setArmed] = useState(false);

  useEffect(() => {
    const prefersReduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;
    if (prefersReduced) {
      setVisible(true);
      return;
    }

    // Motion allowed: arm the transition and hide until intersection.
    setArmed(true);
    setVisible(false);

    const el = ref.current;
    if (!el) {
      setVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            if (delay > 0) {
              window.setTimeout(() => setVisible(true), delay);
            } else {
              setVisible(true);
            }
            observer.disconnect();
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [delay]);

  const Tag = as;

  return (
    <Tag
      ref={ref}
      className={className}
      style={
        armed
          ? {
              opacity: visible ? 1 : 0,
              transform: visible ? "none" : "translateY(12px)",
              transition:
                "opacity 700ms cubic-bezier(0.22,1,0.36,1), transform 700ms cubic-bezier(0.22,1,0.36,1)",
              willChange: "opacity, transform",
            }
          : undefined
      }
    >
      {children}
    </Tag>
  );
}
