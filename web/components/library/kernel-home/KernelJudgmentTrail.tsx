'use client';

/**
 * KernelJudgmentTrail — Home slot #6 (ADR-312).
 *
 * Kernel-universal: renders for EVERY workspace from kernel substrate
 * (the Reviewer's append-only /workspace/persona/judgment_log.md), independent
 * of the active program. Programs do NOT declare this slot.
 *
 * Compact: the few most-recent Reviewer decisions (approve / reject /
 * defer / observation) as glanceable rows, linking to the raw decisions
 * log in Files. Reuses the canonical content-shape parser + formatters
 * (lib/content-shapes/decisions.ts) — no parallel parsing. Self-hides
 * when the Reviewer has logged nothing yet.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ScrollText, ArrowRight, Check, X, Clock, Eye } from 'lucide-react';
import { api } from '@/lib/api/client';
import {
  parse as parseDecisions,
  formatActionType,
  identityLabel,
  formatRelativeTimestamp,
  type ReviewerDecision,
} from '@/lib/content-shapes/decisions';

const DECISIONS_PATH = '/workspace/persona/judgment_log.md';
const COMPACT_LIMIT = 5;

function VerdictIcon({ decision }: { decision: ReviewerDecision['decision'] }) {
  if (decision === 'approve') return <Check className="h-3 w-3 text-emerald-600 shrink-0" />;
  if (decision === 'reject') return <X className="h-3 w-3 text-rose-600 shrink-0" />;
  if (decision === 'defer') return <Clock className="h-3 w-3 text-amber-600 shrink-0" />;
  // Observation / addressed / null → eye glyph (saw it, no verdict).
  return <Eye className="h-3 w-3 text-muted-foreground/50 shrink-0" />;
}

export function KernelJudgmentTrail() {
  const [decisions, setDecisions] = useState<ReviewerDecision[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.workspace
      .getFile(DECISIONS_PATH)
      .then((file) => {
        if (cancelled) return;
        const parsed = parseDecisions(file?.content ?? '');
        setDecisions(parsed);
      })
      .catch(() => {
        // 404 (no decisions yet) → empty, self-hides.
        if (!cancelled) setDecisions([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!decisions || decisions.length === 0) return null;

  const shown = decisions.slice(0, COMPACT_LIMIT);

  return (
    <section
      aria-label="Judgment trail"
      className="rounded-lg border border-border/60 bg-card/50"
    >
      <header className="flex items-center justify-between px-4 py-2.5 border-b border-border/40">
        <div className="flex items-center gap-2">
          <ScrollText className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <h2 className="text-sm font-medium text-foreground">Recent decisions</h2>
        </div>
        <Link
          href={`/files?path=${encodeURIComponent(DECISIONS_PATH)}`}
          className="inline-flex items-center gap-1 text-[11px] text-muted-foreground/70 hover:text-foreground transition-colors"
        >
          All <ArrowRight className="h-3 w-3" />
        </Link>
      </header>
      <ul className="divide-y divide-border/30">
        {shown.map((d, i) => (
          <li
            key={d.proposalId ?? `${d.timestamp ?? ''}-${i}`}
            className="flex items-center gap-2.5 px-4 py-2.5"
          >
            <VerdictIcon decision={d.decision} />
            <span className="flex-1 min-w-0">
              <span className="block text-sm text-foreground truncate">
                {d.actionType ? formatActionType(d.actionType) : 'Decision'}
              </span>
              <span className="block text-[11px] text-muted-foreground/50 truncate">
                {identityLabel(d.identity)}
              </span>
            </span>
            {d.timestamp && (
              <span className="text-[11px] text-muted-foreground/50 shrink-0 tabular-nums">
                {formatRelativeTimestamp(d.timestamp)}
              </span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
