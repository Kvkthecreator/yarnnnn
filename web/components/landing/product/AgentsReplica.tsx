"use client";

/**
 * AgentsReplica — pixel-level replica of the shipped Agents surface
 * (components/agents/AgentsSurface.tsx) for marketing pages.
 *
 * REWRITTEN 2026-08-24 (marketing honesty, the ADR-561 discipline): the
 * previous version animated a hire flow — "＋ Make one", a name field typing
 * "Lisa", a Thinker/Researcher/Designer roster — that ADR-599 deleted in
 * full. A replica of a deleted surface is fiction on the homepage.
 *
 * Faithful to the live pane (ADR-600 D6 / ADR-602): beings sectioned by
 * where they live — "In an app" (Editor across the authoring desks, Keeper
 * tending maintained files), the honest "To work with" empty state, and the
 * attribution promise footer. Animation: the beings reveal one by one, then
 * the footer — met where they work, not hired.
 */

import { Sparkles } from "lucide-react";
import { ProductWindow, FaceCircle } from "./ProductWindow";
import { useStagedLoop, reveal } from "./useStagedLoop";

// The served beings (agents_registry blurbs, verbatim) with the desks the
// pane names beside them.
const BEINGS = [
  {
    initial: "E",
    name: "Editor",
    blurb: "Writes with you — decks and documents.",
    homes: "In Slides, Text",
  },
  {
    initial: "K",
    name: "Keeper",
    blurb: "Keeps chosen files up to date.",
    homes: "In Strings",
  },
];

export function AgentsReplica({ className = "" }: { className?: string }) {
  const step = useStagedLoop(3, 2400);

  return (
    <ProductWindow title="Agents" className={className}>
      <div className="h-[340px] overflow-hidden p-4">
        <div className="mx-auto max-w-sm space-y-4">
          {/* In an app — the beings that come with the desks */}
          <div>
            <span className="text-sm font-medium text-foreground">In an app</span>
            <div className="mt-1.5 space-y-1.5">
              {BEINGS.map((b, i) => (
                <div
                  key={b.name}
                  className={`flex items-center gap-3 rounded-md border border-border px-3 py-2 ${
                    step >= i ? reveal(true) : "opacity-0"
                  }`}
                >
                  <FaceCircle initial={b.initial} />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground leading-tight">{b.name}</p>
                    <p className="truncate text-xs text-muted-foreground leading-tight">
                      {b.blurb}
                    </p>
                    <p className="text-[10px] text-muted-foreground/60 leading-tight mt-0.5">
                      {b.homes}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* To work with — the honest empty state, verbatim */}
          <div>
            <span className="text-sm font-medium text-foreground">To work with</span>
            <p className="mt-1.5 rounded-md border border-dashed border-border px-3 py-2 text-xs text-muted-foreground/70">
              Nobody yet — you&rsquo;ll be able to add your own here later.
            </p>
          </div>

          {/* The attribution promise — verbatim product footer */}
          <p
            className={`flex items-start gap-1.5 text-[11px] leading-snug text-muted-foreground ${
              step >= 2 ? reveal(true) : "opacity-0"
            }`}
          >
            <Sparkles className="mt-0.5 h-3 w-3 shrink-0" />
            Your agents work on your files, as you — every edit they make is attributed to
            you and kept in the file&apos;s history.
          </p>
        </div>
      </div>
    </ProductWindow>
  );
}
