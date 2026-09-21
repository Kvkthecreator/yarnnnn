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
import { useTranslations } from 'next-intl';
import { Rss, Plus, X, CheckCircle2, AlertCircle, Clock, Globe } from 'lucide-react';
import { Working } from '@/components/shared/Working';
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
import { useFeedback } from '@/contexts/FeedbackContext';
import { isSubmitKey } from '@/lib/shell/submit-key';

type T = ReturnType<typeof useTranslations<'workspaceSettings.sources'>>;

export type SourcesVariant = 'full' | 'compact';

interface SourcesCardProps {
  variant?: SourcesVariant;
  className?: string;
}

export function SourcesCard({ variant = 'full', className }: SourcesCardProps) {
  const t = useTranslations('workspaceSettings.sources');
  const { watches, loading, noWatch, setSources } = useSources();

  if (loading) {
    return <Working label={t('loading')} fill className={className} />;
  }

  if (noWatch) {
    return (
      <div className={cn('rounded-lg border border-dashed border-border/60 px-4 py-6 text-center', className)}>
        <Rss className="mx-auto h-5 w-5 text-muted-foreground/50" />
        <p className="mt-2 text-sm font-medium text-foreground/80">{t('noWatchTitle')}</p>
        <p className="mt-1 text-xs text-muted-foreground/70 max-w-sm mx-auto">
          {t('noWatchBody')}
        </p>
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* ADR-340 P4 F2 — consequence preview (the Night-Shift pattern,
          ADR-338 §7.3): the pane teaches what the declaration DOES, not
          just what the file says. Full variant only — the compact overlay
          is a glance, not the teaching moment. */}
      {variant === 'full' && (
        <p className="text-xs text-muted-foreground/80 rounded-md bg-muted/40 border border-border/50 px-3 py-2">
          {t('consequence')}
        </p>
      )}
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
  const t = useTranslations('workspaceSettings.sources');
  const { runAction } = useFeedback();
  const [saving, setSaving] = useState(false);
  const observedById = new Map<string, ObservedSourceHealth>(watch.observed.map((o) => [o.id, o]));

  // `writeShape` is a library helper several layers below this component and
  // holds no hook, so the report belongs HERE — the caller that knows what the
  // member did. try/finally with no catch left a failed source edit silent.
  const save = async (next: WatchSource[]) => {
    setSaving(true);
    try {
      await runAction(() => onSave(watch.declaration_path, next), {
        pending: t('savePending'),
        success: t('saveSuccess'),
        error: t('saveFailed'),
      });
    } catch {
      /* reported; the next load shows what is actually stored */
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
          {watch.observed_at
            ? t('observedAt', { when: relativeTime(watch.observed_at, t) })
            : t('notObserved')}
        </div>
      </div>

      {/* Declared sources + observed health */}
      <ul className="divide-y divide-border/40">
        {watch.declared.length === 0 ? (
          <li className="px-4 py-3 text-xs text-muted-foreground/50 italic">
            {t('noSources')}
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
                  <HealthLine health={health} maxEntries={s.max_entries} t={t} />
                </div>
                {!compact && (
                  <button
                    type="button"
                    onClick={() => void remove(s.url)}
                    disabled={saving}
                    aria-label={t('removeAria', { id: s.id })}
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
              {t('atCap', { cap: watch.source_cap || SOURCE_CAP })}
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
  const t = useTranslations('workspaceSettings.sources');
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
            if (isSubmitKey(e, { allowShift: true })) {
              e.preventDefault();
              add();
            }
          }}
          placeholder={t('urlPlaceholder')}
          disabled={disabled}
          className="flex-1 rounded-md border border-border/60 bg-transparent px-2 py-1 text-xs outline-none focus:border-border disabled:opacity-40"
        />
        <button
          type="button"
          onClick={add}
          disabled={disabled || !url.trim()}
          className="shrink-0 inline-flex items-center gap-1 rounded-md bg-muted/60 px-2 py-1 text-[11px] font-medium hover:bg-muted disabled:opacity-40"
        >
          <Plus className="h-3 w-3" /> {t('add')}
        </button>
      </div>
      <div className="flex items-center gap-1.5">
        <input
          type="text"
          value={id}
          onChange={(e) => setId(e.target.value)}
          placeholder={t('idPlaceholder')}
          disabled={disabled}
          className="flex-1 rounded-md border border-border/60 bg-transparent px-2 py-1 text-[11px] outline-none focus:border-border disabled:opacity-40"
        />
        <select
          value={attestation}
          onChange={(e) => setAttestation(e.target.value as Attestation)}
          disabled={disabled}
          className="shrink-0 rounded-md border border-border/60 bg-transparent px-2 py-1 text-[11px] outline-none focus:border-border disabled:opacity-40"
          title={t('attestationTitle')}
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
  const t = useTranslations('workspaceSettings.sources');
  if (!health) {
    return (
      <span
        className="h-2 w-2 shrink-0 rounded-full bg-muted-foreground/30"
        title={t('notObservedDot')}
      />
    );
  }
  if (health.status === 'error') {
    return <AlertCircle className="h-3.5 w-3.5 shrink-0 text-rose-500" />;
  }
  return <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />;
}

function HealthLine({
  health,
  maxEntries,
  t,
}: {
  health?: ObservedSourceHealth;
  maxEntries: number;
  t: T;
}) {
  if (!health) {
    return (
      <p className="text-[11px] text-muted-foreground/40 mt-0.5">
        {t('awaiting', { max: maxEntries })}
      </p>
    );
  }
  if (health.status === 'error') {
    return (
      <p className="text-[11px] text-rose-500/80 mt-0.5 truncate">
        {health.error ? t('fetchFailedWith', { error: health.error }) : t('fetchFailed')}
      </p>
    );
  }
  return (
    <p className="text-[11px] text-muted-foreground/60 mt-0.5">
      {health.observed_at
        ? t('entriesObservedWhen', {
            count: health.entry_count,
            when: relativeTime(health.observed_at, t),
          })
        : t('entriesObserved', { count: health.entry_count })}
    </p>
  );
}

// ---------------------------------------------------------------------------
// Relative-time helper (small, dependency-free)
// ---------------------------------------------------------------------------

function relativeTime(iso: string, t: T): string {
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) return iso;
  const diffMs = Date.now() - parsed;
  const mins = Math.round(diffMs / 60000);
  if (mins < 1) return t('time.justNow');
  if (mins < 60) return t('time.minutes', { n: mins });
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return t('time.hours', { n: hrs });
  const days = Math.round(hrs / 24);
  return t('time.days', { n: days });
}
