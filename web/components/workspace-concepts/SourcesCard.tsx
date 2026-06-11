'use client';

/**
 * SourcesCard — L3 component for the standing-watch `_sources.yaml`
 * (ADR-336 / ADR-338 D4.1). The "drivers" view of the standing watch.
 *
 * Shows, per active-bundle watch:
 *   1. The declared source list (id + url + attestation + max_entries) —
 *      operator-editable, structured rows (no hand-typed YAML).
 *   2. Per-source OBSERVED health from the distilled signal substrate
 *      (_watch_signal.yaml): last-observed time + ok/error + entry count —
 *      read-only (system-written by TrackWebSources). The Check-7
 *      declared-vs-observed shape.
 *
 * Above the consent line (ADR-338 D3): declaring a watch source changes what
 * the operation PERCEIVES, so it gets first-class surface. Direct-manipulation
 * contract — add/remove/edit source rows; writes route through
 * useSources.setSources → writeShape('sources', …) → WriteFile (ADR-235 D1.b).
 *
 * Empty state: when no active bundle declares a watch, the honest
 * "no standing watch" message — perception is a flow, never a gate
 * (ADR-332 §2). Uploads + websearch remain context-in.
 */

import { useState } from 'react';
import { Rss, Plus, X, CheckCircle2, AlertCircle, Clock, Globe } from 'lucide-react';
import {
  useSources,
  SOURCE_CAP,
  ATTESTATIONS,
  DEFAULT_MAX_ENTRIES,
  type WatchSource,
  type WatchView,
  type ObservedSourceHealth,
  type Attestation,
} from '@/lib/content-shapes/sources';
import { cn } from '@/lib/utils';

export type SourcesVariant = 'full' | 'compact';

interface SourcesCardProps {
  variant?: SourcesVariant;
  className?: string;
}

export function SourcesCard({ variant = 'full', className }: SourcesCardProps) {
  const { watches, loading, noWatch, setSources } = useSources();

  if (loading) {
    return <div className={cn('h-24 rounded-md bg-muted/30 animate-pulse', className)} />;
  }

  if (noWatch) {
    return (
      <div className={cn('rounded-lg border border-dashed border-border/60 px-4 py-6 text-center', className)}>
        <Rss className="mx-auto h-5 w-5 text-muted-foreground/50" />
        <p className="mt-2 text-sm font-medium text-foreground/80">No standing watch declared</p>
        <p className="mt-1 text-xs text-muted-foreground/70 max-w-sm mx-auto">
          Your active program declares no web watch. Uploads and websearch remain your context-in —
          perception is a flow, never a gate. A program with a web/RSS watch (e.g. an interest scout)
          surfaces its source editor here.
        </p>
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {watches.map((w) => (
        <WatchEditor key={w.declaration_path} watch={w} onSave={setSources} compact={variant === 'compact'} />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// WatchEditor — one watch: declared sources (editable) + observed health
// ---------------------------------------------------------------------------

function WatchEditor({
  watch,
  onSave,
  compact,
}: {
  watch: WatchView;
  onSave: (declarationPath: string, sources: WatchSource[]) => Promise<void>;
  compact: boolean;
}) {
  const [saving, setSaving] = useState(false);
  const observedById = new Map<string, ObservedSourceHealth>(watch.observed.map((o) => [o.id, o]));

  const save = async (next: WatchSource[]) => {
    setSaving(true);
    try {
      await onSave(watch.declaration_path, next);
    } finally {
      setSaving(false);
    }
  };

  const remove = (url: string) => save(watch.declared.filter((s) => s.url !== url));
  const atCap = watch.declared.length >= (watch.source_cap || SOURCE_CAP);

  return (
    <div className="rounded-lg border border-border/60 overflow-hidden">
      {/* Watch header — what + cadence + last-observed */}
      <div className="flex items-center justify-between gap-3 border-b border-border/60 bg-muted/20 px-4 py-2">
        <div className="flex items-center gap-2 min-w-0">
          <Rss className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground truncate">
            {watch.watch_id}
          </span>
          {watch.recurrence && (
            <span className="text-[10px] text-muted-foreground/60 shrink-0">· {watch.recurrence}</span>
          )}
        </div>
        <div className="flex items-center gap-1.5 shrink-0 text-[11px] text-muted-foreground/70">
          <Clock className="h-3 w-3" />
          {watch.observed_at ? `observed ${relativeTime(watch.observed_at)}` : 'not yet observed'}
        </div>
      </div>

      {/* Declared sources + observed health */}
      <ul className="divide-y divide-border/40">
        {watch.declared.length === 0 ? (
          <li className="px-4 py-3 text-xs text-muted-foreground/50 italic">
            No sources declared — this watch is a deliberate no-op.
          </li>
        ) : (
          watch.declared.map((s) => {
            const health = observedById.get(s.id);
            return (
              <li key={s.url} className="flex items-center gap-3 px-4 py-2.5">
                <HealthDot health={health} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-medium truncate">{s.id}</span>
                    <span className="text-[10px] rounded-full bg-muted/60 px-1.5 py-0.5 text-muted-foreground shrink-0">
                      {s.attestation}
                    </span>
                  </div>
                  <div className="flex items-center gap-1 text-[11px] text-muted-foreground/70">
                    <Globe className="h-3 w-3 shrink-0" />
                    <span className="truncate">{s.url}</span>
                  </div>
                  <HealthLine health={health} maxEntries={s.max_entries} />
                </div>
                {!compact && (
                  <button
                    type="button"
                    onClick={() => void remove(s.url)}
                    disabled={saving}
                    aria-label={`Remove ${s.id}`}
                    className="shrink-0 rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-40"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </li>
            );
          })
        )}
      </ul>

      {/* Add-source row (full variant only) */}
      {!compact && (
        <div className="border-t border-border/60 px-4 py-2.5">
          {atCap ? (
            <p className="text-[11px] text-muted-foreground/60">
              At the {watch.source_cap || SOURCE_CAP}-source cap — a portfolio of attention, not a crawler.
              Remove one to add another.
            </p>
          ) : (
            <AddSourceRow
              disabled={saving}
              onAdd={(src) => {
                if (watch.declared.some((d) => d.url === src.url)) return;
                void save([...watch.declared, src]);
              }}
            />
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// AddSourceRow — structured add (id + url + attestation), no YAML typing
// ---------------------------------------------------------------------------

function AddSourceRow({
  onAdd,
  disabled,
}: {
  onAdd: (src: WatchSource) => void;
  disabled: boolean;
}) {
  const [url, setUrl] = useState('');
  const [id, setId] = useState('');
  const [attestation, setAttestation] = useState<Attestation>('platform');

  const add = () => {
    const u = url.trim();
    if (!u || !/^https?:\/\//.test(u)) return;
    const derivedId = id.trim() || u.replace(/^https?:\/\//, '').split('/')[0].replace(/^www\./, '');
    onAdd({ id: derivedId, url: u, attestation, max_entries: DEFAULT_MAX_ENTRIES });
    setUrl('');
    setId('');
    setAttestation('platform');
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1.5">
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              add();
            }
          }}
          placeholder="https://example.com/feed/"
          disabled={disabled}
          className="flex-1 rounded-md border border-border/60 bg-transparent px-2 py-1 text-xs outline-none focus:border-border disabled:opacity-40"
        />
        <button
          type="button"
          onClick={add}
          disabled={disabled || !url.trim()}
          className="shrink-0 inline-flex items-center gap-1 rounded-md bg-muted/60 px-2 py-1 text-[11px] font-medium hover:bg-muted disabled:opacity-40"
        >
          <Plus className="h-3 w-3" /> Add
        </button>
      </div>
      <div className="flex items-center gap-1.5">
        <input
          type="text"
          value={id}
          onChange={(e) => setId(e.target.value)}
          placeholder="id (optional — derived from domain)"
          disabled={disabled}
          className="flex-1 rounded-md border border-border/60 bg-transparent px-2 py-1 text-[11px] outline-none focus:border-border disabled:opacity-40"
        />
        <select
          value={attestation}
          onChange={(e) => setAttestation(e.target.value as Attestation)}
          disabled={disabled}
          className="shrink-0 rounded-md border border-border/60 bg-transparent px-2 py-1 text-[11px] outline-none focus:border-border disabled:opacity-40"
          title="Who attests these facts?"
        >
          {ATTESTATIONS.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Health rendering
// ---------------------------------------------------------------------------

function HealthDot({ health }: { health?: ObservedSourceHealth }) {
  if (!health) {
    return <span className="h-2 w-2 shrink-0 rounded-full bg-muted-foreground/30" title="Not yet observed" />;
  }
  if (health.status === 'error') {
    return <AlertCircle className="h-3.5 w-3.5 shrink-0 text-rose-500" />;
  }
  return <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />;
}

function HealthLine({ health, maxEntries }: { health?: ObservedSourceHealth; maxEntries: number }) {
  if (!health) {
    return <p className="text-[11px] text-muted-foreground/40 mt-0.5">Awaiting first observation · keeps ≤{maxEntries} entries</p>;
  }
  if (health.status === 'error') {
    return (
      <p className="text-[11px] text-rose-500/80 mt-0.5 truncate">
        Last fetch failed{health.error ? `: ${health.error}` : ''}
      </p>
    );
  }
  return (
    <p className="text-[11px] text-muted-foreground/60 mt-0.5">
      {health.entry_count} {health.entry_count === 1 ? 'entry' : 'entries'} last observed
      {health.observed_at ? ` ${relativeTime(health.observed_at)}` : ''}
    </p>
  );
}

// ---------------------------------------------------------------------------
// Relative-time helper (small, dependency-free)
// ---------------------------------------------------------------------------

function relativeTime(iso: string): string {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return iso;
  const diffMs = Date.now() - t;
  const mins = Math.round(diffMs / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.round(hrs / 24);
  return `${days}d ago`;
}
