'use client';

/**
 * SourceList — the sources a piece of standing work reads, as a LIST.
 *
 * ⭐ WHY THIS EXISTS. The kernel has always taken many sources: a prose file
 * may declare up to `_MAX_SOURCES_PROSE` (12) of them, and
 * `_reach_connector_sources` groups selectors PER PLATFORM and loops — so one
 * Slack channel plus three Notion pages plus a web page into one brief is a
 * run the engine already performs. The DOOR could only ever write one: three
 * mutually-exclusive tabs, each composing a single-element array, and a
 * single-choice `<select>` for the slice even when the member had chosen
 * several at the connection's aperture. ADR-658's own worked example — *"keep
 * a weekly brief of my team's channels"*, plural — was unbuildable through the
 * only door that builds it.
 *
 * ⚠️ THE RULES ARE THE SERVER'S, MIRRORED — never invented here. They live in
 * `_classify_sources` (`api/services/standing_work.py`) and a refusal comes
 * back BY NAME, so this component's job is to keep a member from reaching a
 * refusal they could not have predicted, not to be the authority:
 *
 *   md                 1–12 sources, any mix of connection · path · page.
 *   csv · json · txt   EXACTLY ONE, and a FILE rather than a folder.
 *                      (a structured target maps one source to the leaf)
 *
 * A structured format therefore renders the single-source door, unchanged;
 * only prose gets the list. That is not a simplification — it is the rule.
 *
 * ⚠️ IDS MUST BE UNIQUE WITHIN A DECLARATION. They key the fetch receipts, so
 * two sources sharing one id lose a snapshot silently. `nextSourceId` derives
 * from the slice and disambiguates against what is already in the list.
 */

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Link2, Plus, X } from 'lucide-react';
import { ConnectorAvatar } from '@/components/connectors/ConnectorAvatar';
import { connectorMeta } from '@/lib/connectors/registry';
import { lowerFirst } from '@/components/standing/StandingRow';
import type { StandingSource, StandingStart } from '@/lib/api/client';
import { cn } from '@/lib/utils';

/** Mirrors `_MAX_SOURCES_PROSE` in `api/services/standing_work.py`. */
export const MAX_SOURCES_PROSE = 12;

/** Formats whose target maps EXACTLY ONE source to the leaf (`_classify_sources`). */
export function isStructured(format: string): boolean {
  return format === 'csv' || format === 'json' || format === 'txt';
}

function slug(s: string): string {
  return s.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

/** A unique id for a new source — the receipts key on it, so a collision
 *  silently loses a snapshot. */
export function nextSourceId(base: string, taken: readonly StandingSource[]): string {
  const root = slug(base) || 'source';
  const used = new Set(taken.map((s) => s.id));
  if (!used.has(root)) return root;
  for (let i = 2; i < 99; i += 1) {
    if (!used.has(`${root}-${i}`)) return `${root}-${i}`;
  }
  return `${root}-${Date.now()}`;
}

/** One source, described in the member's words. */
export function SourceRow({
  source, onRemove, starts,
}: {
  source: StandingSource;
  onRemove?: () => void;
  starts: StandingStart[];
}) {
  const t = useTranslations('supervisor.sources');
  const meta = source.connector ? connectorMeta(source.connector) : undefined;
  const start = starts.find((s) => s.connector && s.connector === source.connector);
  const label = source.connector
    ? (start?.name ?? source.connector)
    : source.path
      ? source.path
      : source.url ?? '';
  const detail = source.connector
    ? source.selector ?? ''
    : source.path
      ? source.path.endsWith('/') ? t('folder') : t('file')
      : t('page');

  return (
    <li className="flex items-center gap-2.5 rounded-md border border-border/70 bg-background px-3 py-2">
      {source.connector ? (
        <ConnectorAvatar
          size="sm"
          title={label}
          connectorKey={source.connector}
          override={meta ? meta.brand : undefined}
        />
      ) : (
        <span aria-hidden className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-border/60 bg-muted/30">
          <Link2 className="h-3.5 w-3.5 text-muted-foreground" />
        </span>
      )}
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[13px] text-foreground">{label}</span>
        <span className="block truncate text-[11px] text-muted-foreground">{detail}</span>
      </span>
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          aria-label={t('remove')}
          title={t('remove')}
          className="shrink-0 rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground/30"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </li>
  );
}

/**
 * The "add a source" control — a connection slice, a workspace path, or a web
 * page. Collapsed to a button until asked for, so the common case (the start's
 * own source, already filled) stays one glance.
 */
export function AddSource({
  starts, existing, folders, onAdd, disabled,
}: {
  starts: StandingStart[];
  existing: readonly StandingSource[];
  folders: Array<{ path: string; label: string }>;
  onAdd: (s: StandingSource) => void;
  disabled?: boolean;
}) {
  const t = useTranslations('supervisor.sources');
  const [open, setOpen] = useState(false);
  const connectorStarts = starts.filter((s) => s.kind === 'connector');
  const [kind, setKind] = useState<'connector' | 'path' | 'url'>(
    connectorStarts.length > 0 ? 'connector' : 'url',
  );
  const [connector, setConnector] = useState(connectorStarts[0]?.connector ?? '');
  const [selector, setSelector] = useState(connectorStarts[0]?.selectors[0] ?? '');
  const [path, setPath] = useState('');
  const [url, setUrl] = useState('');

  const chosen = connectorStarts.find((s) => s.connector === connector) ?? null;
  // A slice already in the list is not offered twice — adding it again would
  // fetch the same snapshot under a second id.
  const taken = new Set(
    existing.filter((s) => s.connector === connector).map((s) => s.selector ?? ''),
  );
  const free = (chosen?.selectors ?? []).filter((id) => !taken.has(id));

  const reset = () => {
    setOpen(false);
    setPath('');
    setUrl('');
  };

  // ⚠️ THE DISPLAYED SLICE, NOT THE STORED ONE (driven 2026-09-21). The
  // `<select>` falls back to `free[0]` when the stored selector is not in the
  // current connection's free list — but the STATE still held the old value,
  // so switching Slack → Notion and pressing Add re-added a Slack channel
  // that was already in the list. What a member sees selected is what gets
  // added; anything else is a lie the control tells about itself.
  const effectiveSelector = free.includes(selector) ? selector : (free[0] ?? '');

  const canAdd = kind === 'connector'
    ? Boolean(connector && effectiveSelector)
    : kind === 'path'
      ? Boolean(path.trim().replace(/^\/+/, ''))
      : /^https?:\/\//.test(url.trim());

  const add = () => {
    if (!canAdd) return;
    if (kind === 'connector') {
      onAdd({ id: nextSourceId(effectiveSelector, existing), connector, selector: effectiveSelector });
    } else if (kind === 'path') {
      const clean = path.trim();
      const leaf = clean.replace(/\/+$/, '').split('/').pop() ?? '';
      onAdd({ id: nextSourceId(leaf, existing), path: clean });
    } else {
      let host = url.trim();
      try { host = new URL(url.trim()).hostname; } catch { /* a bare host is fine */ }
      onAdd({ id: nextSourceId(host, existing), url: url.trim() });
    }
    reset();
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        disabled={disabled}
        className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs text-foreground transition-colors hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground/30 disabled:opacity-40"
      >
        <Plus className="h-3.5 w-3.5" /> {t('add')}
      </button>
    );
  }

  return (
    <div className="space-y-2 rounded-md border border-border/70 bg-muted/20 p-3">
      <div className="flex flex-wrap gap-2">
        {connectorStarts.length > 0 && (
          <Tab active={kind === 'connector'} onClick={() => setKind('connector')}>
            {t('sourceConnection')}
          </Tab>
        )}
        <Tab active={kind === 'path'} onClick={() => setKind('path')}>{t('sourceWorkspace')}</Tab>
        <Tab active={kind === 'url'} onClick={() => setKind('url')}>{t('sourceWebPage')}</Tab>
      </div>

      {kind === 'connector' ? (
        <div className="space-y-2">
          <select
            value={connector}
            onChange={(e) => {
              const next = connectorStarts.find((s) => s.connector === e.target.value);
              setConnector(e.target.value);
              setSelector(next?.selectors[0] ?? '');
            }}
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
          >
            {connectorStarts.map((s) => (
              <option key={s.connector ?? ''} value={s.connector ?? ''}>{s.name}</option>
            ))}
          </select>
          {free.length > 0 ? (
            <select
              value={effectiveSelector}
              onChange={(e) => setSelector(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
            >
              {free.map((id) => <option key={id} value={id}>{id}</option>)}
            </select>
          ) : (
            <p className="text-[11px] text-amber-700 dark:text-amber-300">
              {(chosen?.selectors.length ?? 0) > 0 ? t('allAdded') : t('nothingChosen')}
            </p>
          )}
          {chosen?.reads && (
            <p className="text-[11px] text-muted-foreground">
              {t('itReads', { reads: lowerFirst(chosen.reads) })}
            </p>
          )}
        </div>
      ) : kind === 'path' ? (
        <>
          <input
            value={path}
            onChange={(e) => setPath(e.target.value)}
            list="standing-source-folders"
            placeholder={t('pathPlaceholder')}
            className="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-sm outline-none focus:border-foreground/30"
          />
          <datalist id="standing-source-folders">
            {folders.map((f) => <option key={f.path} value={f.path}>{f.label}</option>)}
          </datalist>
        </>
      ) : (
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder={t('urlPlaceholder')}
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
        />
      )}

      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={reset}
          className="rounded-md px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground"
        >
          {t('cancel')}
        </button>
        <button
          type="button"
          onClick={add}
          disabled={!canAdd}
          className="rounded-md bg-foreground px-2.5 py-1 text-xs text-background disabled:opacity-40"
        >
          {t('add')}
        </button>
      </div>
    </div>
  );
}

function Tab({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'rounded-md border px-2.5 py-1.5 text-xs transition-colors',
        active
          ? 'border-foreground/40 bg-background text-foreground'
          : 'border-border text-muted-foreground hover:bg-muted/40',
      )}
    >
      {children}
    </button>
  );
}
