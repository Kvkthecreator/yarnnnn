"use client";

import { useState } from "react";

/**
 * TraceCard — demonstrates the ledger / `trace` mechanism on the landing page.
 *
 * Per the interaction design spec (docs/design/marketing-interaction-design-2026-06-29.md §1):
 * `trace` — "every change has an author and a version" — is the uncopyable property and it is
 * currently told in prose and shown nowhere. This card SHOWS it: a small revision stack where
 * each entry expands to reveal author · date · what-changed.
 *
 * Data is a tasteful MOCK (decided 2026-06-29) — a hand-crafted, representative revision chain.
 * It is illustrative, not live product data; the shape mirrors the real authored-substrate
 * revision chain (author taxonomy: operator / a model / an agent).
 *
 * Accessibility: each entry is a <button> (keyboard-operable, focus-visible); hover OR
 * focus OR click expands it. Reduced-motion is handled by the global CSS guard.
 */

interface Revision {
  /** Who wrote this version — the principal. */
  author: string;
  /** Author class, for the colored dot. */
  kind: "you" | "model" | "agent";
  when: string;
  /** One-line summary of what changed. */
  change: string;
}

// Mock revision chain — newest first. Representative of a real `trace` over one fact.
const REVISIONS: Revision[] = [
  {
    author: "Claude",
    kind: "model",
    when: "today",
    change: "Refined the positioning line to “one memory, every AI.”",
  },
  {
    author: "you",
    kind: "you",
    when: "3 days ago",
    change: "Corrected the launch date to Q3.",
  },
  {
    author: "your research agent",
    kind: "agent",
    when: "last week",
    change: "Added the competitor summary as source.",
  },
];

const DOT: Record<Revision["kind"], string> = {
  you: "bg-emerald-500",
  model: "bg-indigo-500",
  agent: "bg-sky-500",
};

export function TraceCard() {
  // Index of the open entry; default the newest open so the card reads as alive at rest.
  const [open, setOpen] = useState<number>(0);

  return (
    <div className="p-8 rounded-2xl border border-[#1a1a1a]/[0.06] bg-[#1a1a1a]/[0.02] h-full">
      <div className="text-xs font-mono text-[#1a1a1a]/30 uppercase tracking-wider mb-4">
        Traceable
      </div>
      <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Every version has an author.</h3>
      <p className="text-sm text-[#1a1a1a]/50 leading-relaxed mb-5">
        Every change is signed and dated. Hover a line to see who changed what, and when —
        you, an AI, or one of your agents.
      </p>

      {/* The revision stack — the demonstration. */}
      <div className="space-y-1.5" role="list" aria-label="Example change history">
        {REVISIONS.map((rev, i) => {
          const isOpen = open === i;
          return (
            <button
              key={i}
              type="button"
              role="listitem"
              onMouseEnter={() => setOpen(i)}
              onFocus={() => setOpen(i)}
              onClick={() => setOpen(i)}
              aria-expanded={isOpen}
              className="block w-full text-left rounded-lg border border-[#1a1a1a]/[0.06] bg-white/50 px-3 py-2.5 transition-colors hover:border-[#1a1a1a]/[0.12] focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/40"
            >
              <div className="flex items-center gap-2">
                <span
                  className={`h-1.5 w-1.5 shrink-0 rounded-full ${DOT[rev.kind]}`}
                  aria-hidden="true"
                />
                <span className="text-sm font-medium text-[#1a1a1a]/80">{rev.author}</span>
                <span className="ml-auto text-xs text-[#1a1a1a]/30 font-mono">{rev.when}</span>
              </div>
              {/* Expanding detail — grid-rows trick animates height with no CLS reflow risk. */}
              <div
                className="grid transition-all duration-300 ease-out"
                style={{
                  gridTemplateRows: isOpen ? "1fr" : "0fr",
                  opacity: isOpen ? 1 : 0,
                }}
              >
                <div className="overflow-hidden">
                  <p className="pt-1.5 pl-3.5 text-xs text-[#1a1a1a]/50 leading-relaxed">
                    {rev.change}
                  </p>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      <p className="mt-4 text-xs text-[#1a1a1a]/30 font-mono">
        a plain storage connector can&apos;t show this
      </p>
    </div>
  );
}
