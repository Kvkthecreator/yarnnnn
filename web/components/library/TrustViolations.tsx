'use client';

/**
 * TrustViolations — Cockpit pane #1 in the six-question cockpit framing
 * (2026-04-28 reshape). The pane that answers "did anything just break my
 * trust?"
 *
 * Universal across program bundles — every delegation product needs this
 * pane. Reads `action_proposals` filtered to violation-shaped envelopes
 * (proposals where Reviewer flagged a principle violation, autonomy
 * inconsistency, or risk-cap breach). No bundle-specific logic.
 *
 * Visual discipline: invisible 99% of the time — when zero violations
 * exist, the component renders nothing (returns null). When a violation
 * exists, it dominates the cockpit zone with destructive-tinted chrome.
 * This is the alpha-trader equivalent of an air-quality alert: you don't
 * see it most days, but when you do, it's the only thing that matters.
 *
 * Today's data shape: reads pending proposals where `risk_warnings` is
 * non-empty OR `reviewer_identity` is set with a 'violation' classifier
 * in `reviewer_reasoning`. As Reviewer matures (ADR-194 Phase 4), a
 * dedicated `class='violation'` field on action_proposals lets us
 * filter directly; for now we infer.
 */

import { useEffect, useState } from 'react';
import { ShieldAlert, AlertTriangle } from 'lucide-react';
import Link from 'next/link';
import { api, APIError } from '@/lib/api/client';

type Proposal = Awaited<ReturnType<typeof api.proposals.list>>['proposals'][number];

function isViolation(p: Proposal): boolean {
  // Heuristic until Reviewer adds an explicit class field:
  //   - any non-empty risk_warnings array, or
  //   - reviewer_reasoning contains "violation" / "principle" / "breach"
  const warnings = (p.risk_warnings ?? []) as unknown[];
  if (Array.isArray(warnings) && warnings.length > 0) return true;
  const reasoning = (p as { reviewer_reasoning?: string | null }).reviewer_reasoning ?? '';
  return /violat|principle|breach|exceed/i.test(reasoning);
}

export function TrustViolations() {
  const [violations, setViolations] = useState<Proposal[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { proposals } = await api.proposals.list('pending', 50);
        if (!cancelled) {
          setViolations(proposals.filter(isViolation));
        }
      } catch (err) {
        // Silent fall to no-violations rather than a destructive false-positive
        if (!cancelled) setViolations([]);
        if (!(err instanceof APIError)) {
          console.warn('[TrustViolations] load failed:', err);
        }
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // Loading or zero violations: render nothing.
  if (violations === null || violations.length === 0) return null;

  return (
    <section
      aria-label="Trust violations"
      className="rounded-lg border-2 border-destructive/40 bg-destructive/5 p-4"
    >
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-destructive">
        <ShieldAlert className="h-4 w-4" />
        Trust check — {violations.length} {violations.length === 1 ? 'item' : 'items'} need review
      </div>
      <div className="space-y-2">
        {violations.slice(0, 3).map((v) => (
          <div
            key={v.id}
            className="flex items-start gap-2 rounded-md border border-destructive/30 bg-background px-3 py-2 text-sm"
          >
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-destructive" />
            <div className="flex-1 min-w-0">
              <div className="font-medium text-foreground">{v.action_type}</div>
              {v.rationale && (
                <p className="line-clamp-2 text-xs text-muted-foreground">
                  {v.rationale}
                </p>
              )}
            </div>
            <Link
              href="/agents?agent=reviewer"
              className="shrink-0 text-xs font-medium text-destructive underline-offset-4 hover:underline"
            >
              Review →
            </Link>
          </div>
        ))}
        {violations.length > 3 && (
          <Link
            href="/agents?agent=reviewer"
            className="block text-center text-xs font-medium text-destructive underline-offset-4 hover:underline"
          >
            See {violations.length - 3} more
          </Link>
        )}
      </div>
    </section>
  );
}
