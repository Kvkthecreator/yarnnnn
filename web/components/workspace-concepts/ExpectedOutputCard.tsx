'use client';

/**
 * ExpectedOutputCard — L3 component for
 * /workspace/contract/_expected_output.yaml (ADR-348).
 *
 * The operator-facing FE for ADR-345's Expected Output — the output contract:
 * WHAT the operation owes when it works (kind + delivery-cadence + bar).
 * Mounted in the ADR-347 Contract group of the one Settings door, alongside
 * Budget (Rhythm) + Autonomy (Witness).
 *
 * ADR-348 D2 — the headline is the READ ("Owes: a piece when a draft clears
 * the bar"); the structured editor sits below it.
 *
 * ADR-348 D3 — generic, kind-agnostic structured form (the kernel-fallback;
 * Shape 2's default). kind = free text; delivery_cadence = preset select +
 * free entry; bar = free text. The "zero is on-contract" / floor-gated-not-
 * quota guard (ADR-345) is enforced in the copy: event-shaped cadences read
 * "produces when the trigger fires", so the form cannot render as a quota.
 *
 * Governance-region, operator-only (ADR-345 / ADR-320): operator authors,
 * Reviewer reads-not-authors. WRITE_CONTRACT='configuration' → inline editor
 * (ADR-347 §3 operator-authored → inline).
 */

import { useEffect, useState } from 'react';
import { Target, ArrowRight, Check } from 'lucide-react';
import {
  useExpectedOutput,
  DELIVERY_CADENCES,
  isEventShaped,
  type ExpectedOutputMeta,
} from '@/lib/content-shapes/expected-output';
import { cn } from '@/lib/utils';

export type ExpectedOutputVariant = 'full' | 'compact' | 'chip';

interface ExpectedOutputCardProps {
  variant?: ExpectedOutputVariant;
  onOpen?: () => void;
  initialContent?: string | null;
  className?: string;
}

export function ExpectedOutputCard({
  variant = 'full',
  onOpen,
  initialContent,
  className,
}: ExpectedOutputCardProps) {
  const { meta, loading, summary, setContract } = useExpectedOutput({ initialContent });

  // ---- chip ----
  if (variant === 'chip') {
    if (loading || !meta?.kind) return null;
    return (
      <button
        onClick={onOpen}
        className={cn(
          'inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors',
          className,
        )}
      >
        <Target className="w-3 h-3" />
        {meta.kind}
        {meta.delivery_cadence ? ` · ${meta.delivery_cadence}` : ''}
      </button>
    );
  }

  // ---- compact ----
  if (variant === 'compact') {
    return (
      <div className={cn('rounded-lg border border-border p-3', className)}>
        <div className="flex items-center gap-2 text-sm font-medium">
          <Target className="w-4 h-4 text-muted-foreground" />
          Expected Output
        </div>
        <p className="mt-1 text-sm text-muted-foreground">{summary}</p>
        {onOpen && (
          <button
            onClick={onOpen}
            className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline"
          >
            Tune <ArrowRight className="w-3 h-3" />
          </button>
        )}
      </div>
    );
  }

  // ---- full ----
  return <ExpectedOutputFull meta={meta} loading={loading} summary={summary} setContract={setContract} className={className} />;
}

function ExpectedOutputFull({
  meta,
  loading,
  summary,
  setContract,
  className,
}: {
  meta: ExpectedOutputMeta | null;
  loading: boolean;
  summary: string;
  setContract: (next: Partial<ExpectedOutputMeta>) => Promise<void>;
  className?: string;
}) {
  // Draft state for the structured editor (operator edits, then Save).
  const [kind, setKind] = useState('');
  const [cadence, setCadence] = useState('');
  const [bar, setBar] = useState('');
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState(false);

  // Sync draft from substrate when it loads / changes.
  useEffect(() => {
    setKind(meta?.kind ?? '');
    setCadence(meta?.delivery_cadence ?? '');
    setBar(meta?.bar ?? '');
  }, [meta?.kind, meta?.delivery_cadence, meta?.bar]);

  const dirty =
    kind !== (meta?.kind ?? '') ||
    cadence !== (meta?.delivery_cadence ?? '') ||
    bar !== (meta?.bar ?? '');

  const onSave = async () => {
    setSaving(true);
    setSavedAt(false);
    try {
      await setContract({
        kind: kind.trim() || undefined,
        delivery_cadence: cadence.trim() || undefined,
        bar: bar.trim() || undefined,
      });
      setSavedAt(true);
      setTimeout(() => setSavedAt(false), 2500);
    } finally {
      setSaving(false);
    }
  };

  const eventShaped = isEventShaped(cadence);

  return (
    <div className={cn('space-y-5', className)}>
      {/* Header */}
      <div>
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Target className="w-5 h-5" />
          Expected Output
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          What this operation owes when it works — the output contract. Orthogonal to
          Budget (how often it works) and Autonomy (which beats you witness).
        </p>
      </div>

      {/* The READ — the declared contract in plain words (ADR-348 D2). */}
      <div className="rounded-lg border border-border bg-muted/30 p-4">
        <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground/70">
          The contract
        </div>
        <p className="mt-1 text-sm font-medium">
          {loading ? 'Loading…' : summary}
        </p>
        {meta?.bar && (
          <p className="mt-1 text-xs text-muted-foreground">
            Bar: {meta.bar}
          </p>
        )}
      </div>

      {/* The structured editor (ADR-348 D3 generic kernel-fallback form). */}
      <div className="space-y-4">
        <div>
          <label className="text-sm font-medium">Kind</label>
          <p className="text-xs text-muted-foreground mb-1.5">
            The artifact this operation produces (e.g. piece, trade, campaign, shortlist).
          </p>
          <input
            type="text"
            value={kind}
            onChange={(e) => setKind(e.target.value)}
            placeholder="e.g. piece"
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="text-sm font-medium">Delivery cadence</label>
          <p className="text-xs text-muted-foreground mb-1.5">
            The rhythm of delivery — a <strong>floor-gated cadence, never a quota</strong>. If
            nothing clears the bar this period, the slot slips.
          </p>
          <input
            type="text"
            list="expected-output-cadences"
            value={cadence}
            onChange={(e) => setCadence(e.target.value)}
            placeholder="e.g. event-driven"
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
          />
          <datalist id="expected-output-cadences">
            {DELIVERY_CADENCES.map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
          {eventShaped && (
            <p className="mt-1.5 text-xs text-muted-foreground">
              Event-shaped: the operation produces when the trigger fires, and owes{' '}
              <strong>zero when it doesn&apos;t</strong> — that is on-contract, not a shortfall.
            </p>
          )}
        </div>

        <div>
          <label className="text-sm font-medium">Bar</label>
          <p className="text-xs text-muted-foreground mb-1.5">
            Where the quality floor lives (a pointer, not duplicated here) — the bar is never
            relaxed to meet the cadence.
          </p>
          <input
            type="text"
            value={bar}
            onChange={(e) => setBar(e.target.value)}
            placeholder="e.g. principles.md pre-ship audit"
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
          />
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onSave}
            disabled={!dirty || saving}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving…' : 'Save contract'}
          </button>
          {savedAt && (
            <span className="inline-flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
              <Check className="w-3.5 h-3.5" /> Saved
            </span>
          )}
        </div>
      </div>

      <p className="text-[11px] text-muted-foreground/70 border-t border-border pt-3">
        Operator-authored governance substrate. The agent reads this in its wake envelope and
        holds itself accountable to it (it never authors it). Keep the prose companion —
        <span className="font-mono"> MANDATE ## Expected Output</span> — in agreement (edit it via chat).
      </p>
    </div>
  );
}
