'use client';

/**
 * Working — the ONE way to say "wait" (ADR-651; docs/design/ACTION-FEEDBACK.md
 * § Waiting).
 *
 * A glyph that cycles Claude Code's asterisk frames beside a label a band of
 * light sweeps across. The motion is CSS (`.working-*` in globals.css): no
 * timer, no per-frame render, safe inside a Suspense fallback, and under
 * `prefers-reduced-motion` it freezes to a still "·" and plain text. Every
 * wait a member reads renders this; a bare lucide spinner beside prose is the
 * shape it replaces. A control acknowledging itself (an icon swap inside a
 * button) is micro-feedback and stays at the control — ADR-651 D5.
 *
 * BOUNDED BY CONSTRUCTION. A wait that cannot report progress is bounded by
 * the primitive: after SLOW_MS the row admits it ("still working"), after
 * STUCK_MS it offers an exit — Try again when the caller has one, else Reload.
 * No caller has to remember; a hung fetch behind any Working can no longer
 * spin for ever. A caller that CAN report progress passes `since` (the chat
 * turn): the row shows elapsed time instead and never escalates on its own —
 * the transport bounds it (the SSE idle deadline in lib/sse.ts).
 */

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

/** Claude Code's spinner frames; the cycle runs forward then back. */
const GLYPHS = ['·', '✢', '✳', '✶', '✻', '✽'] as const;

/** After this the row says "still working". */
export const SLOW_MS = 6_000;
/** After this the row offers an exit. */
export const STUCK_MS = 30_000;
/** Elapsed time is shown once a patient wait passes this — earlier it is noise. */
const ELAPSED_FROM_MS = 3_000;

/** The animated glyph alone — for a row that already carries its own words. */
export function WorkingGlyph({ className }: { className?: string }) {
  return (
    <span aria-hidden className={cn('working-glyph', className)}>
      {GLYPHS.map((g, i) => (
        <span key={i} className={`working-glyph-${i}`}>
          {g}
        </span>
      ))}
    </span>
  );
}

interface WorkingProps {
  /** The whole sentence, ellipsis included — "Reading your documents…". */
  label: string;
  /** Centre in the pane or page (fills a `h-full` parent; 6rem tall in flow). */
  fill?: boolean;
  /**
   * The wait's start, ms since epoch, for a caller that reports progress
   * itself. Shows elapsed time; disables the slow/stuck escalation — the
   * caller's transport is what bounds that wait.
   */
  since?: number;
  /** The exit's verb when stuck. Absent → the exit reloads the page. */
  onRetry?: () => void;
  className?: string;
}

type Phase = 'fresh' | 'slow' | 'stuck';

function formatElapsed(ms: number): string {
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  return `${Math.floor(s / 60)}m ${s % 60}s`;
}

export function Working({ label, fill = false, since, onRetry, className }: WorkingProps) {
  // Neither effect touches the clock during render, so the server and the
  // first client paint agree (a hydration mismatch here would flash).
  const [phase, setPhase] = useState<Phase>('fresh');
  const [elapsedMs, setElapsedMs] = useState<number | null>(null);

  useEffect(() => {
    if (since !== undefined) return; // patient: the transport bounds it
    const slow = setTimeout(() => setPhase('slow'), SLOW_MS);
    const stuck = setTimeout(() => setPhase('stuck'), STUCK_MS);
    return () => {
      clearTimeout(slow);
      clearTimeout(stuck);
    };
  }, [since]);

  useEffect(() => {
    if (since === undefined) return;
    const tick = () => setElapsedMs(Date.now() - since);
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [since]);

  const exit = onRetry ?? (() => window.location.reload());

  return (
    <div
      role="status"
      className={cn(
        'text-muted-foreground',
        fill
          ? 'flex h-full min-h-24 flex-col items-center justify-center gap-1.5 py-6 text-sm'
          : 'inline-flex flex-col items-start gap-1',
        className,
      )}
    >
      <span className="inline-flex items-center gap-1.5">
        <WorkingGlyph />
        <span className="working-label">{label}</span>
        {elapsedMs !== null && elapsedMs >= ELAPSED_FROM_MS && (
          // Hidden from the live region: a counter that re-announced every
          // second would bury the reply it precedes.
          <span aria-hidden className="text-xs tabular-nums opacity-60">
            {formatElapsed(elapsedMs)}
          </span>
        )}
        {phase === 'slow' && <span className="text-xs opacity-60">still working</span>}
      </span>
      {phase === 'stuck' && (
        <span className="text-xs">
          This is taking longer than it should.{' '}
          <button
            type="button"
            onClick={exit}
            className="underline underline-offset-2 hover:text-foreground"
          >
            {onRetry ? 'Try again' : 'Reload'}
          </button>
        </span>
      )}
    </div>
  );
}
