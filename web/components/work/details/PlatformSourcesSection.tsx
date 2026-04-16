'use client';

/**
 * PlatformSourcesSection — Inline source picker for platform tasks.
 *
 * Rendered inside TrackingEntityGrid (accumulates_context) and ActionMiddle
 * (external_action) when the task has a platform dependency.
 *
 * Design:
 * - Collapsed header shows chip strip of currently-selected sources.
 * - Expanding reveals the full checkbox list to add/remove sources.
 * - Every toggle auto-saves immediately (no explicit Save button).
 * - Soft cap: Slack 10, Notion 10, GitHub 5 — enforced in UI.
 * - Resources loaded eagerly so chip names are always friendly, never raw IDs.
 *
 * ADR-158 Phase 2: per-task source selection.
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import {
  ChevronDown, ChevronRight, Hash, FileText, GitBranch,
  Loader2, AlertCircle, Check, X,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type { Task } from '@/types';

// ─── Platform config ──────────────────────────────────────────────────────────

type SupportedPlatform = 'slack' | 'notion' | 'github';

interface PlatformConfig {
  label: string;
  resourceLabel: string;
  icon: React.ReactNode;
  selectionCap: number | undefined;
}

const PLATFORM_CONFIG: Record<SupportedPlatform, PlatformConfig> = {
  slack: {
    label: 'Slack',
    resourceLabel: 'channels',
    icon: <Hash className="w-3.5 h-3.5" />,
    selectionCap: 10,
  },
  notion: {
    label: 'Notion',
    resourceLabel: 'pages',
    icon: <FileText className="w-3.5 h-3.5" />,
    selectionCap: 10,
  },
  github: {
    label: 'GitHub',
    resourceLabel: 'repositories',
    icon: <GitBranch className="w-3.5 h-3.5" />,
    selectionCap: 5,
  },
};

function resolvePlatform(typeKey: string | undefined): SupportedPlatform | null {
  if (!typeKey) return null;
  if (typeKey.startsWith('slack')) return 'slack';
  if (typeKey.startsWith('notion')) return 'notion';
  if (typeKey.startsWith('github')) return 'github';
  return null;
}

// ─── Resource item ────────────────────────────────────────────────────────────

interface ResourceItem {
  id: string;
  name: string;
  resource_type: string;
  coverage_state: string;
  last_extracted_at: string | null;
}

// ─── Selected source chip ────────────────────────────────────────────────────

function SourceChip({
  name,
  onRemove,
  saving,
}: {
  name: string;
  onRemove?: () => void;
  saving?: boolean;
}) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-muted/60 border border-border/60 text-[10px] text-muted-foreground font-medium max-w-[140px]">
      <span className="truncate">{name}</span>
      {onRemove && (
        <button
          type="button"
          onClick={e => { e.stopPropagation(); onRemove(); }}
          disabled={saving}
          className="flex-shrink-0 text-muted-foreground/50 hover:text-foreground disabled:opacity-30"
          aria-label={`Remove ${name}`}
        >
          <X className="w-2.5 h-2.5" />
        </button>
      )}
    </span>
  );
}

// ─── Checkbox row (expanded state) ───────────────────────────────────────────

function ResourceCheckRow({
  resource,
  selected,
  disabled,
  saving,
  onToggle,
}: {
  resource: ResourceItem;
  selected: boolean;
  disabled: boolean;
  saving: boolean;
  onToggle: () => void;
}) {
  const isFresh = resource.last_extracted_at !== null;

  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={(disabled && !selected) || saving}
      className={cn(
        'flex items-center gap-2.5 w-full px-3 py-2 rounded-md text-left transition-colors text-xs',
        selected
          ? 'bg-primary/8 border border-primary/20 text-foreground'
          : disabled
            ? 'border border-transparent text-muted-foreground/30 cursor-not-allowed'
            : 'border border-transparent hover:bg-muted/50 text-muted-foreground hover:text-foreground',
        saving && 'opacity-60',
      )}
    >
      <span
        className={cn(
          'flex-shrink-0 w-3.5 h-3.5 rounded border flex items-center justify-center',
          selected ? 'bg-primary border-primary' : 'border-border',
        )}
      >
        {selected && <Check className="w-2.5 h-2.5 text-primary-foreground" />}
      </span>

      <span className="flex-1 min-w-0 truncate font-medium">{resource.name}</span>

      <span
        className={cn(
          'flex-shrink-0 w-1.5 h-1.5 rounded-full',
          isFresh ? 'bg-green-500/60' : 'bg-muted-foreground/20',
        )}
        title={isFresh ? 'Has data' : 'No data yet'}
      />
    </button>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

function nameToSlug(name: string): string {
  return name
    .replace(/^#/, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

interface PlatformSourcesSectionProps {
  task: Task;
  onSourcesUpdated?: () => void;
  existingEntitySlugs?: Set<string>;
}

export function PlatformSourcesSection({ task, onSourcesUpdated, existingEntitySlugs }: PlatformSourcesSectionProps) {
  const platform = resolvePlatform(task.type_key);
  if (!platform) return null;

  const config = PLATFORM_CONFIG[platform];
  const cap = config.selectionCap;

  const savedIds = task.sources?.[platform] ?? [];
  const [open, setOpen] = useState(savedIds.length === 0);
  const [resources, setResources] = useState<ResourceItem[]>([]);
  const [loadingResources, setLoadingResources] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set(savedIds));
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [lastSaved, setLastSaved] = useState(false);

  // Re-sync when task.sources changes externally
  useEffect(() => {
    setSelectedIds(new Set(task.sources?.[platform] ?? []));
  }, [task.sources, platform]);

  // Load resources eagerly on mount so chip names are always friendly
  const loadResources = useCallback(async () => {
    setLoadingResources(true);
    setLoadError(null);
    try {
      const data = await api.integrations.getLandscape(platform as 'slack' | 'notion' | 'github');
      setResources(data.resources ?? []);
    } catch {
      setLoadError(`Could not load ${config.label} ${config.resourceLabel}.`);
    } finally {
      setLoadingResources(false);
    }
  }, [platform, config.label, config.resourceLabel]);

  useEffect(() => {
    if (resources.length === 0 && !loadingResources) {
      void loadResources();
    }
  }, []);

  // Auto-save: persist immediately on every toggle
  const saveRef = useRef(0);
  const persistSources = useCallback(async (ids: Set<string>) => {
    const token = ++saveRef.current;
    setSaving(true);
    setSaveError(null);
    setLastSaved(false);
    try {
      await api.tasks.updateSources(task.slug, { [platform]: Array.from(ids) });
      if (saveRef.current === token) {
        setLastSaved(true);
        setTimeout(() => setLastSaved(false), 1500);
        onSourcesUpdated?.();
      }
    } catch {
      if (saveRef.current === token) {
        setSaveError('Failed to save');
      }
    } finally {
      if (saveRef.current === token) {
        setSaving(false);
      }
    }
  }, [task.slug, platform, onSourcesUpdated]);

  const atCap = cap !== undefined && selectedIds.size >= cap;

  const toggle = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else if (!atCap || cap === undefined) {
        next.add(id);
      } else {
        return prev; // at cap, no change
      }
      void persistSources(next);
      return next;
    });
  };

  const remove = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.delete(id);
      void persistSources(next);
      return next;
    });
  };

  // Name lookup — falls back to ID only if resources haven't loaded yet
  const nameById: Record<string, string> = {};
  for (const r of resources) nameById[r.id] = r.name;

  const selectedArray = Array.from(selectedIds);

  const pendingCount = existingEntitySlugs
    ? selectedArray.filter(id => {
        const name = nameById[id] ?? id;
        return !existingEntitySlugs.has(nameToSlug(name));
      }).length
    : 0;

  // Sort: selected first, then alphabetical
  const sortedResources = [...resources].sort((a, b) => {
    const aSelected = selectedIds.has(a.id) ? 0 : 1;
    const bSelected = selectedIds.has(b.id) ? 0 : 1;
    if (aSelected !== bSelected) return aSelected - bSelected;
    return a.name.localeCompare(b.name);
  });

  return (
    <div className="border-b border-border/40">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="flex w-full items-center gap-2 px-6 py-3 text-left hover:bg-muted/20 transition-colors"
      >
        <span className="text-muted-foreground/50 flex-shrink-0">{config.icon}</span>

        <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wide flex-shrink-0">
          {config.label}
        </span>

        {/* Chip strip */}
        <div className="flex-1 flex flex-wrap gap-1 min-w-0 overflow-hidden">
          {selectedArray.length === 0 ? (
            <span className="text-[10px] text-amber-500/80">no {config.resourceLabel} selected</span>
          ) : (
            selectedArray.slice(0, 5).map(id => (
              <SourceChip
                key={id}
                name={nameById[id] ?? id}
                onRemove={!open ? () => remove(id) : undefined}
                saving={saving}
              />
            ))
          )}
          {selectedArray.length > 5 && (
            <span className="text-[10px] text-muted-foreground/50 self-center">
              +{selectedArray.length - 5} more
            </span>
          )}
        </div>

        {/* Status indicators */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {saving && <Loader2 className="w-3 h-3 animate-spin text-muted-foreground/50" />}
          {lastSaved && !saving && <Check className="w-3 h-3 text-green-500/70" />}
          {saveError && !saving && <AlertCircle className="w-3 h-3 text-destructive/60" />}

          {pendingCount > 0 && !open && (
            <span className="text-[10px] text-muted-foreground/40">
              {pendingCount} pending
            </span>
          )}

          {cap !== undefined && (
            <span className={cn(
              'text-[10px]',
              atCap ? 'text-amber-500/80' : 'text-muted-foreground/40',
            )}>
              {selectedArray.length}/{cap}
            </span>
          )}

          {open
            ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground/40" />
            : <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/40" />
          }
        </div>
      </button>

      {/* ── Expanded content ──────────────────────────────────────────────── */}
      {open && (
        <div className="px-6 pb-4 space-y-2">
          {atCap && (
            <p className="text-[11px] text-amber-600 dark:text-amber-400">
              {cap} {config.resourceLabel} selected — deselect one to add another.
            </p>
          )}

          {selectedIds.size === 0 && !loadingResources && (
            <p className="text-[11px] text-amber-600 dark:text-amber-400">
              No {config.resourceLabel} selected — pick at least one for this task to read {config.label} data.
            </p>
          )}

          {loadingResources ? (
            <div className="flex items-center gap-2 py-2">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Loading {config.resourceLabel}…</span>
            </div>
          ) : loadError ? (
            <div className="flex items-start gap-2 text-xs text-destructive/80">
              <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <span>{loadError}</span>
            </div>
          ) : resources.length === 0 ? (
            <p className="text-xs text-muted-foreground/60">
              No {config.resourceLabel} found. Make sure {config.label} is connected.
            </p>
          ) : (
            <div className="space-y-0.5 max-h-[260px] overflow-auto">
              {sortedResources.map(r => (
                <ResourceCheckRow
                  key={r.id}
                  resource={r}
                  selected={selectedIds.has(r.id)}
                  disabled={atCap}
                  saving={saving}
                  onToggle={() => toggle(r.id)}
                />
              ))}
            </div>
          )}

          {saveError && (
            <div className="flex items-center gap-1.5 text-[11px] text-destructive">
              <AlertCircle className="w-3 h-3" />{saveError}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
