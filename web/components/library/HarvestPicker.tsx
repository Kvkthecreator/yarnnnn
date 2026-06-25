'use client';

/**
 * HarvestPicker — the "bring in your reality" scope picker (ADR-331 D4).
 *
 * The Migration-Assistant motion: the operator sees their actually-connected
 * sources, dials scope, sees an inline dry-run estimate ("~N items → these
 * domains"), and confirms. Confirm fires the curated harvest invocation (D3)
 * which writes attributed agent:harvest substrate.
 *
 * Selection state is EPHEMERAL (ADR-331 D4 no-stored-state): it lives in this
 * component's state until confirm; nothing about what the operator considered
 * or intends is persisted. The substrate records only what got brought in (the
 * files the harvest wrote). Re-entering /setup re-renders the picker fresh from
 * current connections — no resume, no saved selection.
 *
 * v1 scope is PROVIDER-LEVEL (harvest from Slack / Notion / GitHub, with a
 * range window) rather than per-container (per-channel/page/repo). The dry-run
 * estimates counts; the LLM harvest reads across the provider's accessible
 * containers and curates. Per-container granularity is a refine-later concern
 * (ADR-331 open question #1) — the picker shows only connected providers either
 * way.
 */

import { useEffect, useMemo, useState } from 'react';
import {
  Loader2,
  Check,
  AlertCircle,
  Sparkles,
  Download,
  Link2,
} from 'lucide-react';
import { api, APIError, type HarvestSource } from '@/lib/api/client';
import { getPlatformDisplay } from '@/lib/platform-display';
import { SurfaceLink } from '@/components/shell/SurfaceLink';

/** Providers harvest can read from (the ones with read tools, ADR-331 D3). */
const HARVESTABLE_PROVIDERS = ['slack', 'notion', 'github'] as const;
type HarvestProvider = (typeof HARVESTABLE_PROVIDERS)[number];

const RANGE_OPTIONS: Array<{ label: string; days: number | null }> = [
  { label: 'Last 30 days', days: 30 },
  { label: 'Last 90 days', days: 90 },
  { label: 'Last year', days: 365 },
  { label: 'Everything', days: null },
];

interface HarvestPickerProps {
  /** Called after a successful harvest run so the parent can re-derive step state. */
  onHarvested?: () => void;
}

export function HarvestPicker({ onHarvested }: HarvestPickerProps) {
  const [connected, setConnected] = useState<HarvestProvider[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Ephemeral selection state (never persisted).
  const [selected, setSelected] = useState<Set<HarvestProvider>>(new Set());
  const [rangeDays, setRangeDays] = useState<number | null>(30);

  const [estimate, setEstimate] = useState<{
    item_count: number;
    source_count: number;
    target_domains: string[];
  } | null>(null);
  const [estimating, setEstimating] = useState(false);

  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<{ files: number; summary: string } | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  // Load connected, harvestable providers.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.integrations.list();
        const provs = (res.integrations || [])
          .filter((i) => i.status === 'active')
          .map((i) => i.provider)
          .filter((p): p is HarvestProvider =>
            (HARVESTABLE_PROVIDERS as readonly string[]).includes(p),
          );
        if (!cancelled) setConnected(Array.from(new Set(provs)));
      } catch (err) {
        if (!cancelled) {
          setLoadError(err instanceof APIError ? err.message : 'Failed to load connections');
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const sources: HarvestSource[] = useMemo(
    () =>
      Array.from(selected).map((provider) => ({
        provider,
        label: getPlatformDisplay(provider).name,
        range_days: rangeDays,
      })),
    [selected, rangeDays],
  );

  // Re-estimate (dry-run, no writes) whenever selection or range changes.
  useEffect(() => {
    if (sources.length === 0) {
      setEstimate(null);
      return;
    }
    let cancelled = false;
    setEstimating(true);
    (async () => {
      try {
        const res = await api.harvest.dryRun(sources);
        if (!cancelled && res.success) {
          setEstimate({
            item_count: res.estimate.item_count,
            source_count: res.estimate.source_count,
            target_domains: res.target_domains || [],
          });
        }
      } catch {
        if (!cancelled) setEstimate(null);
      } finally {
        if (!cancelled) setEstimating(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sources]);

  const toggle = (p: HarvestProvider) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(p)) next.delete(p);
      else next.add(p);
      return next;
    });
    setRunResult(null);
    setRunError(null);
  };

  const handleConfirm = async () => {
    if (sources.length === 0) return;
    setRunning(true);
    setRunError(null);
    try {
      const res = await api.harvest.run(sources);
      if (res.success) {
        setRunResult({
          files: res.files_written?.length ?? 0,
          summary: res.summary || 'Harvest complete.',
        });
        onHarvested?.();
      } else {
        setRunError(res.message || res.error || 'Harvest failed');
      }
    } catch (err) {
      setRunError(err instanceof APIError ? err.message : 'Harvest failed');
    } finally {
      setRunning(false);
    }
  };

  // ── Render ────────────────────────────────────────────────────────────

  if (loadError) {
    return (
      <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive flex items-center gap-2">
        <AlertCircle className="w-3.5 h-3.5 shrink-0" />
        <span>{loadError}</span>
      </div>
    );
  }

  if (connected === null) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground py-2">
        <Loader2 className="w-3.5 h-3.5 animate-spin" /> Loading connected sources…
      </div>
    );
  }

  if (connected.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border bg-muted/10 px-3 py-3 text-xs text-muted-foreground">
        No harvestable platforms connected yet. Connect Slack, Notion, or GitHub
        first —{' '}
        <SurfaceLink to="connectors" className="text-primary hover:text-primary/80 inline-flex items-center gap-1">
          <Link2 className="w-3 h-3" /> Connectors
        </SurfaceLink>
        . You can also upload files directly below.
      </div>
    );
  }

  if (runResult) {
    return (
      <div className="rounded-md border border-green-500/30 bg-green-500/5 px-3 py-3 text-xs text-green-700 dark:text-green-400">
        <div className="flex items-center gap-2 font-medium">
          <Check className="w-3.5 h-3.5" />
          Brought in {runResult.files} file{runResult.files !== 1 ? 's' : ''}.
        </div>
        <p className="mt-1 text-muted-foreground">{runResult.summary}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded-lg border border-border bg-card/50 p-3">
      {/* Provider toggles */}
      <div className="space-y-1.5">
        <p className="text-[11px] uppercase tracking-wide text-muted-foreground/70">
          Sources
        </p>
        {connected.map((p) => {
          const display = getPlatformDisplay(p);
          const isSel = selected.has(p);
          return (
            <button
              key={p}
              type="button"
              onClick={() => toggle(p)}
              className={`w-full flex items-center gap-2 rounded-md border px-3 py-2 text-left text-xs transition-colors ${
                isSel
                  ? 'border-primary/50 bg-primary/5'
                  : 'border-border bg-background hover:bg-muted/20'
              }`}
            >
              <span
                className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 ${
                  isSel ? 'bg-primary border-primary' : 'border-muted-foreground/40'
                }`}
              >
                {isSel && <Check className="w-3 h-3 text-primary-foreground" />}
              </span>
              <span className="font-medium">{display.name}</span>
            </button>
          );
        })}
      </div>

      {/* Range selector */}
      <div className="space-y-1.5">
        <p className="text-[11px] uppercase tracking-wide text-muted-foreground/70">Range</p>
        <div className="flex flex-wrap gap-1.5">
          {RANGE_OPTIONS.map((opt) => (
            <button
              key={opt.label}
              type="button"
              onClick={() => setRangeDays(opt.days)}
              className={`rounded-md border px-2.5 py-1 text-[11px] transition-colors ${
                rangeDays === opt.days
                  ? 'border-primary/50 bg-primary/5 text-foreground'
                  : 'border-border bg-background text-muted-foreground hover:bg-muted/20'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Dry-run estimate */}
      {sources.length > 0 && (
        <div className="rounded-md bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
          {estimating ? (
            <span className="flex items-center gap-1.5">
              <Loader2 className="w-3 h-3 animate-spin" /> Estimating…
            </span>
          ) : estimate ? (
            <span>
              ~{estimate.item_count} item{estimate.item_count !== 1 ? 's' : ''} across{' '}
              {estimate.source_count} source{estimate.source_count !== 1 ? 's' : ''}
              {estimate.target_domains.length > 0 && (
                <> → {estimate.target_domains.join(', ')}</>
              )}
            </span>
          ) : (
            <span>Select a range to estimate.</span>
          )}
        </div>
      )}

      {runError && (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive flex items-center gap-2">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          <span>{runError}</span>
        </div>
      )}

      {/* Confirm */}
      <button
        type="button"
        onClick={handleConfirm}
        disabled={sources.length === 0 || running}
        className="w-full inline-flex items-center justify-center gap-1.5 rounded-md border border-border bg-background px-3 py-2 text-xs font-medium hover:bg-muted/30 disabled:opacity-40 transition-colors"
      >
        {running ? (
          <>
            <Loader2 className="w-3.5 h-3.5 animate-spin" /> Bringing in your reality…
          </>
        ) : (
          <>
            <Download className="w-3.5 h-3.5" /> Bring in reality
            {estimate && estimate.item_count > 0 && <Sparkles className="w-3 h-3" />}
          </>
        )}
      </button>
      <p className="text-[10px] text-muted-foreground/50 leading-snug">
        Harvest reads the selected sources, curates them, and writes attributed
        notes into your context domains. Nothing here is saved until you confirm.
      </p>
    </div>
  );
}
