"use client";

/**
 * AgentsReplica — pixel-level replica of the shipped Agents surface
 * (components/agents/AgentsSurface.tsx) for marketing pages.
 *
 * Faithful details: the centered single-column list; "Your agents" with
 * the dashed "＋ Make one" door; the real kernel roster (Thinker /
 * Researcher / Designer) with the real blurbs and the engine as the quiet
 * third line; the attribution promise footer (ADR-460 — agents work on
 * your files, as you).
 *
 * Animation: the hire form's name field types itself ("Lisa"), then Lisa
 * appears under Your agents — the make-an-agent moment in four seconds.
 */

import { useEffect, useState } from "react";
import { Sparkles, Upload } from "lucide-react";
import { ProductWindow, FaceCircle } from "./ProductWindow";
import { useStagedLoop, reveal } from "./useStagedLoop";

const ROSTER = [
  {
    initial: "T",
    name: "Thinker",
    blurb: "Thinks a problem through with you — writing, judgment, hard calls.",
    engine: "GPT-5",
  },
  {
    initial: "R",
    name: "Researcher",
    blurb: "Digs through material fast — the workspace and the web, with sources.",
    engine: "Gemini",
  },
  {
    initial: "D",
    name: "Designer",
    blurb: "Makes the thing itself — decks, docs, the artifact in front of you.",
    engine: "Claude",
  },
];

const TYPED_NAME = "Lisa";

export function AgentsReplica({ className = "" }: { className?: string }) {
  const step = useStagedLoop(3, 2400);
  const [chars, setChars] = useState(0);

  // Type the name during step 1; reset on loop restart.
  useEffect(() => {
    if (step === 0) {
      setChars(0);
      return;
    }
    if (step !== 1) {
      setChars(TYPED_NAME.length);
      return;
    }
    let i = 0;
    const t = window.setInterval(() => {
      i += 1;
      setChars(i);
      if (i >= TYPED_NAME.length) window.clearInterval(t);
    }, 220);
    return () => window.clearInterval(t);
  }, [step]);

  const hired = step >= 2;

  return (
    <ProductWindow title="Agents" className={className}>
      <div className="h-[340px] overflow-hidden p-4">
        <div className="mx-auto max-w-sm space-y-4">
          {/* Your agents */}
          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <span className="text-sm font-medium text-foreground">Your agents</span>
              <span className="rounded-md border border-dashed border-border px-2 py-0.5 text-xs text-muted-foreground">
                ＋ Make one
              </span>
            </div>

            {/* The hire form — name field types itself */}
            <div className={`rounded-lg border border-border p-2.5 ${hired ? "hidden" : ""}`}>
              <div className="flex items-center gap-2.5">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-dashed border-border text-muted-foreground/50">
                  <Upload className="h-3 w-3" />
                </span>
                <div className="min-w-0 flex-1 rounded-md border border-border px-2 py-1.5">
                  {chars > 0 ? (
                    <span className="text-xs text-foreground">
                      {TYPED_NAME.slice(0, chars)}
                      <span className="animate-pulse text-muted-foreground">|</span>
                    </span>
                  ) : (
                    <span className="text-xs text-muted-foreground/50">
                      Name them — Lisa, Marcus, whoever
                    </span>
                  )}
                </div>
              </div>
              <p className="mt-1.5 text-[10px] text-muted-foreground/60">
                Hired as Critic <span className="text-muted-foreground/40">· runs on GPT-5</span>
              </p>
            </div>

            {/* Lisa lands in the roster */}
            <div className={hired ? reveal(true) : "hidden"}>
              <div className="flex items-center gap-3 rounded-md border border-border px-3 py-2">
                <FaceCircle initial="L" tone="indigo" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-foreground leading-tight">Lisa</p>
                  <p className="truncate text-xs text-muted-foreground leading-tight">
                    Critic · GPT-5
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Who you can hire — the real kernel roster */}
          <div>
            <span className="text-sm font-medium text-foreground">Who you can hire</span>
            <div className="mt-1.5 space-y-1.5">
              {ROSTER.map((a) => (
                <div
                  key={a.name}
                  className="flex items-center gap-3 rounded-md border border-border px-3 py-2"
                >
                  <FaceCircle initial={a.initial} />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground leading-tight">{a.name}</p>
                    <p className="truncate text-xs text-muted-foreground leading-tight">
                      {a.blurb}
                    </p>
                    <p className="text-[10px] text-muted-foreground/60 leading-tight mt-0.5">
                      {a.engine}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* The attribution promise — verbatim product footer */}
          <p className="flex items-start gap-1.5 text-[11px] leading-snug text-muted-foreground">
            <Sparkles className="mt-0.5 h-3 w-3 shrink-0" />
            Your agents work on your files, as you — every edit they make is attributed to
            you and kept in the file&apos;s history.
          </p>
        </div>
      </div>
    </ProductWindow>
  );
}
