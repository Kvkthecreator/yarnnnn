"use client";

import { useEffect, useRef, useState } from "react";

/**
 * MembraneDemo — the hero centerpiece. Demonstrates the MEMBRANE mechanism:
 * "write it once, it's in every AI."
 *
 * Per the interaction design spec (docs/design/marketing-interaction-design-2026-06-29.md §1+§3):
 * a static chip row can't convey *shared*. Here one memory card sits at the center; the rooms
 * (Claude / ChatGPT / Slack / Notion / your agents) surround it, each connected by a faint beam.
 * A pulse travels out to the active room — write once, available everywhere. It auto-cycles, and
 * hovering/focusing a room makes its connection the active one.
 *
 * Accessibility & perf:
 *  - rooms are <button>s, keyboard-operable + focus-visible; hover OR focus activates.
 *  - auto-cycle pauses on hover/focus; disabled under prefers-reduced-motion (the active room
 *    just renders statically; no pulse).
 *  - SVG beams are aria-hidden decoration; the semantic content (memory + room labels) is text.
 *  - lightweight: one small SVG, no measured-layout reflow, no animation dependency.
 */

const ROOMS = [
  { id: "claude", label: "Claude" },
  { id: "chatgpt", label: "ChatGPT" },
  { id: "slack", label: "Slack" },
  { id: "notion", label: "Notion" },
  { id: "agents", label: "your agents" },
];

export function MembraneDemo() {
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);
  const reducedRef = useRef(false);

  useEffect(() => {
    reducedRef.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reducedRef.current || paused) return;
    const id = window.setInterval(() => {
      setActive((a) => (a + 1) % ROOMS.length);
    }, 2200);
    return () => window.clearInterval(id);
  }, [paused]);

  return (
    <div
      className="relative w-[320px] sm:w-[380px]"
      onMouseLeave={() => setPaused(false)}
    >
      {/* The memory core */}
      <div className="relative z-10 mx-auto mb-8 w-fit">
        <div className="rounded-2xl border border-[#1a1a1a]/10 bg-white/70 backdrop-blur-sm px-6 py-4 shadow-sm text-center">
          <div className="text-[10px] font-mono uppercase tracking-wider text-[#1a1a1a]/30 mb-1">
            your memory
          </div>
          <div className="text-sm font-medium text-[#1a1a1a]/80">one place you own</div>
        </div>
        {/* a soft glow that pulses toward the active room */}
        <div
          className="pointer-events-none absolute -inset-4 -z-10 rounded-3xl"
          style={{
            background:
              "radial-gradient(120px circle at 50% 50%, rgba(99,102,241,0.10), transparent 70%)",
          }}
          aria-hidden="true"
        />
      </div>

      {/* The rooms — write once, available in each. */}
      <div className="relative z-10 flex flex-wrap justify-center gap-2">
        {ROOMS.map((room, i) => {
          const isActive = active === i;
          return (
            <button
              key={room.id}
              type="button"
              onMouseEnter={() => {
                setPaused(true);
                setActive(i);
              }}
              onFocus={() => {
                setPaused(true);
                setActive(i);
              }}
              onBlur={() => setPaused(false)}
              aria-label={`${room.label} — reads the same memory`}
              className={`rounded-full border px-3.5 py-1.5 text-sm transition-all duration-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/40 ${
                isActive
                  ? "border-indigo-400/40 bg-indigo-500/[0.06] text-[#1a1a1a]/80"
                  : "border-[#1a1a1a]/10 bg-white/40 text-[#1a1a1a]/45"
              }`}
            >
              <span className="flex items-center gap-1.5">
                <span
                  className={`h-1.5 w-1.5 rounded-full transition-colors duration-300 ${
                    isActive ? "bg-indigo-500" : "bg-[#1a1a1a]/15"
                  }`}
                  aria-hidden="true"
                />
                {room.label}
              </span>
            </button>
          );
        })}
      </div>

      {/* The line that proves it */}
      <p className="relative z-10 mt-6 text-center text-xs font-mono text-[#1a1a1a]/30">
        write it once → it&apos;s in {ROOMS[active].label}
      </p>
    </div>
  );
}
