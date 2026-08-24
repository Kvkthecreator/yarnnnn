'use client';

/**
 * StreamSteps — the stepped thread a lane turn draws while it works
 * (2026-08-25).
 *
 * WHAT THIS REPLACES. The in-flight bubble used to carry ONE collapsed line —
 * `Lisa · reading a file · searching files…` — with two defects the member
 * actually hit:
 *
 *  1. **It vanished at the first token.** The line was gated on `!m.content`
 *     (LanePanel, the `m.role === 'assistant' && !m.content` branch), so a tool
 *     called AFTER the reply started narrating produced no visible progress at
 *     all until the turn settled. A long turn that read six files mid-narration
 *     looked idle for its whole second half.
 *  2. **It named the verb and nothing else.** "reading a file" — never WHICH
 *     file. Mid-turn is exactly when knowing the subject is worth most, because
 *     it is the only moment a wrong one is cheap to stop.
 *
 * The steps now accumulate as their own rows ABOVE the bubble and survive the
 * first token, each naming its subject when the server gave one (`tool_step`,
 * `lane_runner.tool_subject_from`).
 *
 * ⭐ THE PLACE IS THE WORKSPACE. Every verb that names where it acts says "your
 * workspace" — see the header of `toolLabels.ts`. These acts land in the shared
 * attributed commons, not on the member's disk, and the transcript is the last
 * place that should blur it.
 *
 * ⚠️ NOT the steward rail's `InlineToolCall` (components/tp/). That one is
 * expandable, argument-bearing, and per-call result-stateful, over the whole
 * primitives registry; this is the LANE surface's smaller vocabulary at
 * ADR-441 D1's altitude seam. Two components, deliberately — but if a third
 * appears, that is the moment to unify rather than to add.
 */

import { Check, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { toolStepLine } from './toolLabels';

export type StreamStep = { name: string; subject?: string };

interface StreamStepsProps {
  steps: StreamStep[];
  /** True while the turn is still running: the LAST step spins (it is the one
   *  in flight); every earlier one is settled and gets a check. When the turn
   *  is done, every step is settled. */
  running: boolean;
  className?: string;
}

export function StreamSteps({ steps, running, className }: StreamStepsProps) {
  if (steps.length === 0) return null;
  return (
    // `list` + `listitem` roles: the thread is a sequence of things that
    // happened, and a screen reader should read it as one. `aria-live` is
    // deliberately NOT set here — the rows can arrive several per second on a
    // fan-out, and announcing each would bury the reply that follows.
    <ol role="list" className={cn('flex flex-col gap-0.5', className)}>
      {steps.map((step, i) => {
        const inFlight = running && i === steps.length - 1;
        return (
          <li
            key={`${step.name}-${i}`}
            className="flex items-start gap-1.5 text-[11px] text-muted-foreground"
          >
            {/* The icon column doubles as the thread: a fixed-width rail so
                every row's text starts on the same x, and the connector runs
                between the glyphs rather than beside them. */}
            <span className="relative flex w-3.5 shrink-0 justify-center pt-[3px]">
              {i > 0 && (
                <span
                  aria-hidden
                  className="absolute -top-[3px] h-[5px] w-px bg-border"
                />
              )}
              {inFlight ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <Check className="w-3 h-3 text-muted-foreground/60" />
              )}
            </span>
            <span className={cn('min-w-0 break-words', inFlight && 'text-foreground/70')}>
              {toolStepLine(step)}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
