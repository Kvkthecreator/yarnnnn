'use client';

/**
 * PerformanceFace — face #3 of the four-face cockpit (ADR-228).
 *
 * Renders attribution against the mandate: how the operation is doing at
 * the things MANDATE said it would do. This is the historical lens —
 * what's accumulated since the mandate was authored.
 *
 * Reads (kernel default):
 *   - `_performance.md` body (per ADR-195 v2) for headline attribution
 *   - `/workspace/review/decisions.md` for Reviewer calibration:
 *       · approve / reject ratio (rolling 7d)
 *       · time since last decision
 *       · operator-Reviewer agreement (when overrides logged)
 *
 * The face is bundle-aware: alpha-trader's PerformanceFace surfaces signal
 * expectancy + accuracy by signal type from `portfolio/_performance.md`;
 * alpha-commerce's surfaces conversion by channel + churn vs target. The
 * structural shape (mandate-attributed performance + Reviewer calibration)
 * is universal; the bundle declares which sub-metrics roll up.
 *
 * Phase 1 (this commit): renders Reviewer calibration headline + a single
 * link to the bundle-declared performance source. Sub-metric rendering
 * lands in Commit 4 of the ADR-228 plan.
 *
 * Empty state: when neither performance file nor decisions.md has content,
 * the face renders "No performance accumulated yet — run a cycle to see
 * how the operation is doing."
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Activity } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useComposition } from '@/lib/compositor';

const DECISIONS_PATH = '/workspace/review/decisions.md';
const DEFAULT_PERFORMANCE = '/workspace/context/_performance_summary.md';

interface ReviewerCalibration {
  approves: number;
  rejects: number;
  defers: number;
  total: number;
  lastDecisionAt: Date | null;
  ratio: number | null;
}

function parseDecisions(content: string): ReviewerCalibration {
  // decisions.md is append-only with Markdown headings per entry. Each entry
  // includes a verdict line like:
  //   verdict: approve|reject|defer
  // and a timestamp in the heading like ## 2026-04-28T08:05:42Z — alpaca.submit_order
  const calib: ReviewerCalibration = {
    approves: 0,
    rejects: 0,
    defers: 0,
    total: 0,
    lastDecisionAt: null,
    ratio: null,
  };
  const cutoff = Date.now() - 7 * 24 * 3600 * 1000;
  const blocks = content.split(/\n##\s+/).slice(1);
  for (const block of blocks) {
    const tsMatch = block.match(/^(\d{4}-\d{2}-\d{2}T[\d:.Z+-]+)/);
    const verdictMatch = block.match(/verdict:\s*(approve|reject|defer)/i);
    if (!tsMatch || !verdictMatch) continue;
    const ts = new Date(tsMatch[1]);
    if (Number.isNaN(ts.getTime())) continue;
    if (!calib.lastDecisionAt || ts > calib.lastDecisionAt) {
      calib.lastDecisionAt = ts;
    }
    if (ts.getTime() < cutoff) continue;
    const verdict = verdictMatch[1].toLowerCase();
    if (verdict === 'approve') calib.approves += 1;
    if (verdict === 'reject') calib.rejects += 1;
    if (verdict === 'defer') calib.defers += 1;
    calib.total += 1;
  }
  if (calib.total > 0) {
    calib.ratio = calib.approves / calib.total;
  }
  return calib;
}

function readPerformanceSource(composition: ReturnType<typeof useComposition>['data']): string {
  const cockpit = composition.composition.tabs?.work?.list as { cockpit?: { performance?: { attribution_source?: string } } } | undefined;
  return cockpit?.cockpit?.performance?.attribution_source ?? DEFAULT_PERFORMANCE;
}

export function PerformanceFace() {
  const { data: composition } = useComposition();
  const performancePath = readPerformanceSource(composition);

  const [calibration, setCalibration] = useState<ReviewerCalibration | null>(null);
  const [hasPerformance, setHasPerformance] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [decisionsR, perfR] = await Promise.allSettled([
        api.workspace.getFile(DECISIONS_PATH),
        api.workspace.getFile(performancePath),
      ]);
      if (cancelled) return;
      const decisionsContent = decisionsR.status === 'fulfilled' ? decisionsR.value?.content ?? '' : '';
      setCalibration(parseDecisions(decisionsContent));
      const perfContent = perfR.status === 'fulfilled' ? perfR.value?.content ?? '' : '';
      setHasPerformance(perfContent.trim().length > 0);
    })();
    return () => { cancelled = true; };
  }, [performancePath]);

  if (calibration === null || hasPerformance === null) return null;

  const isEmpty = !hasPerformance && calibration.total === 0 && !calibration.lastDecisionAt;
  const performanceLink = `/files?path=${encodeURIComponent(performancePath)}`;
  const reviewerLink = '/agents?agent=reviewer';

  if (isEmpty) {
    return (
      <section
        aria-label="Performance"
        className="rounded-lg border border-dashed border-border bg-muted/20 p-5"
      >
        <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
          <Activity className="h-3.5 w-3.5" />
          Performance
        </div>
        <p className="text-sm text-muted-foreground">
          No performance accumulated yet — run a cycle to see how the operation
          is doing against your mandate.
        </p>
      </section>
    );
  }

  const ratioPct = calibration.ratio !== null ? Math.round(calibration.ratio * 100) : null;
  const lastDecision = calibration.lastDecisionAt ? formatRelative(calibration.lastDecisionAt) : null;

  return (
    <section
      aria-label="Performance"
      className="rounded-lg border border-border bg-card p-5"
    >
      <div className="mb-4 flex items-center justify-between text-xs">
        <span className="font-medium uppercase tracking-wide text-muted-foreground/70">
          Performance
        </span>
        {hasPerformance && (
          <Link
            href={performanceLink}
            className="text-muted-foreground/60 underline-offset-4 hover:text-foreground hover:underline"
          >
            attribution detail →
          </Link>
        )}
      </div>

      {/* Reviewer calibration headline — always rendered when there's any
          decision history, even if performance file is empty. */}
      {calibration.total > 0 ? (
        <div className="grid grid-cols-3 gap-6 text-sm">
          <Calib
            label="Reviewer approves"
            value={`${calibration.approves} / ${calibration.total}`}
            sub={ratioPct !== null ? `${ratioPct}% approval rate (7d)` : null}
            href={reviewerLink}
          />
          <Calib
            label="Rejected"
            value={`${calibration.rejects}`}
            sub={calibration.rejects > 0 ? 'mandate-violation guards' : 'none rejected'}
            href={reviewerLink}
          />
          <Calib
            label="Last decision"
            value={lastDecision ?? '—'}
            sub={null}
            href={reviewerLink}
          />
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          Reviewer scaffolded · No decisions yet. Calibration data accumulates
          as proposals flow through the loop.
        </p>
      )}

      {hasPerformance && (
        <p className="mt-4 border-t border-border pt-3 text-xs text-muted-foreground">
          <Link
            href={performanceLink}
            className="font-medium text-foreground underline-offset-4 hover:underline"
          >
            Attribution against mandate
          </Link>
          {' '}— signal expectancy, accuracy, and rolling P&L by attribution
          source.
        </p>
      )}
    </section>
  );
}

function Calib({
  label,
  value,
  sub,
  href,
}: {
  label: string;
  value: string;
  sub: string | null;
  href: string;
}) {
  return (
    <Link href={href} className="block hover:opacity-80">
      <div className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground/60">
        {label}
      </div>
      <div className="mt-1 text-xl font-semibold text-foreground">{value}</div>
      {sub && <div className="mt-0.5 text-[11px] text-muted-foreground/70">{sub}</div>}
    </Link>
  );
}

function formatRelative(d: Date): string {
  const diff = Date.now() - d.getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
