'use client';

/**
 * PlatformSourcesSection — Inline source picker for platform tasks.
 *
 * Rendered inside TrackingEntityGrid (accumulates_context) and ActionMiddle
 * (external_action) when the task has a platform dependency.
 *
 * Design:
 * - Collapsed header shows chip strip of currently-selected sources so
 *   "selected" is always visible even without expanding. This closes the
 *   gap between the "X selected" count and the tracked entity grid below.
 * - Expanding reveals the full checkbox list to add/remove sources.
 * - Soft cap: Slack 10, Notion 10, GitHub unlimited (repos are naturally
 *   bounded by what the user has OAuth'd to). Cap is enforced in the UI —
 *   at-limit unchecked rows are disabled with a tooltip.
 * - Names are rendered as-is from the landscape (which already stores
 *   Slack names as "#channel-name" and Notion names as plain titles).
 *
 * ADR-158 Phase 2: per-task source selection.
 */

import { useEffect, useState, useCallback } from 'react';
import {
  ChevronDown, ChevronRight, Hash, FileText, GitBranch,
  Loader2, AlertCircle, Check, Save, X,
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
  // Soft cap on selections. undefined = no cap.
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
    selectionCap: undefined,
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
  name: string;      // already formatted by landscape (e.g. "#general", "My Page")
  resource_type: string;
  coverage_state: string;
  last_extracted_at: string | null;
}

// ─── Selected source chip (collapsed state) ───────────────────────────────────

function SourceChip({
  name,
  onRemove,
}: {
  name: string;
  onRemove?: () => void;
}) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-muted/60 border border-border/60 text-[10px] text-muted-foreground font-medium max-w-[120px]">
      <span className="truncate">{name}</span>
      {onRemove && (
        <button
          type="button"
          onClick={e => { e.stopPropagation(); onRemove(); }}
          className="flex-shrink-0 text-muted-foreground/50 hover:text-foreground"
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
  onToggle,
}: {
  resource: ResourceItem;
  selected: boolean;
  disabled: boolean;
  onToggle: () => void;
}) {
  const isFresh = resource.last_extracted_at !== null;

  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={disabled && !selected}
      className={cn(
        'flex items-center gap-2.5 w-full px-3 py-2 rounded-md text-left transition-colors text-xs',
        selected
          ? 'bg-primary/8 border border-primary/20 text-foreground'
          : disabled
            ? 'border border-transparent text-muted-foreground/30 cursor-not-allowed'
            : 'border border-transparent hover:bg-muted/50 text-muted-foreground hover:text-foreground',
      )}
    >
      {/* Checkbox */}
      <span
        className={cn(
          'flex-shrink-0 w-3.5 h-3.5 rounded border flex items-center justify-center',
          selected ? 'bg-primary border-primary' : 'border-border',
        )}
      >
        {selected && <Check className="w-2.5 h-2.5 text-primary-foreground" />}
      </span>

      {/* Name — landscape already formats (e.g. "#general" for Slack) */}
      <span className="flex-1 min-w-0 truncate font-medium">{resource.name}</span>

      {/* Freshness dot */}
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

// Derive likely workspace entity slug from a landscape resource name.
// Heuristic: strip # prefix, lowercase, collapse non-alphanumeric to -.
// Matches how agents name entity subfolders (e.g. "#general" → "general").
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
  // Set of entity slugs that already have workspace data — used to mark
  // selected sources as "has data" vs "pending first run".
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
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Re-sync when task.sources changes after save
  useEffect(() => {
    setSelectedIds(new Set(task.sources?.[platform] ?? []));
  }, [task.sources, platform]);

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
    if (open && resources.length === 0 && !loadingResources) {
      void loadResources();
    }
  }, [open]);

  const hasChanges = (() => {
    const current = new Set(savedIds);
    if (current.size !== selectedIds.size) return true;
    return Array.from(selectedIds).some(id => !current.has(id));
  })();

  const atCap = cap !== undefined && selectedIds.size >= cap;

  const toggle = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else if (!atCap || cap === undefined) {
        next.add(id);
      }
      return next;
    });
  };

  const quickRemove = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  const save = async () => {
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    try {
      await api.tasks.updateSources(task.slug, { [platform]: Array.from(selectedIds) });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
      onSourcesUpdated?.();
    } catch {
      setSaveError('Failed to save. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  // Build a name lookup from loaded resources (or fall back to ID)
  const nameById: Record<string, string> = {};
  for (const r of resources) nameById[r.id] = r.name;

  const selectedArray = Array.from(selectedIds);

  // Classify selected sources: which have existing entity data vs pending first run.
  // Uses heuristic slug derivation to match source names → entity slugs.
  const pendingCount = existingEntitySlugs
    ? selectedArray.filter(id => {
        const name = nameById[id] ?? id;
        return !existingEntitySlugs.has(nameToSlug(name));
      }).length
    : 0;

  // Sort resource list: selected first, then alphabetical
  const sortedResources = [...resources].sort((a, b) => {
    const aSelected = selectedIds.has(a.id) ? 0 : 1;
    const bSelected = selectedIds.has(b.id) ? 0 : 1;
    if (aSelected !== bSelected) return aSelected - bSelected;
    return a.name.localeCompare(b.name);
  });

  return (
    <div className="border-b border-border/40">
      {/* ── Collapsed header ─────────────────────────────────────────────── */}
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="flex w-full items-center gap-2 px-6 py-3 text-left hover:bg-muted/20 transition-colors"
      >
        <span className="text-muted-foreground/50 flex-shrink-0">{config.icon}</span>

        <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wide flex-shrink-0">
          {config.label}
        </span>

        {/* Chip strip — selected sources always visible */}
        <div className="flex-1 flex flex-wrap gap-1 min-w-0 overflow-hidden">
          {selectedArray.length === 0 ? (
            <span className="text-[10px] text-amber-500/80">no {config.resourceLabel} selected</span>
          ) : (
            selectedArray.slice(0, 5).map(id => (
              <SourceChip
                key={id}
                name={nameById[id] ?? id}
                onRemove={!open ? () => {
                  // Remove and immediately persist — single-click removal from chip strip
                  setSelectedIds(prev => {
                    const next = new Set(prev);
                    next.delete(id);
                    api.tasks.updateSources(task.slug, { [platform]: Array.from(next) })
                      .then(() => onSourcesUpdated?.())
                      .catch(() => {});
                    return next;
                  });
                } : undefined}
              />
            ))
          )}
          {selectedArray.length > 5 && (
            <span className="text-[10px] text-muted-foreground/50 self-center">
              +{selectedArray.length - 5} more
            </span>
          )}
        </div>

        {/* Pending indicator — selected sources not yet in entity grid */}
        {pendingCount > 0 && !open && (
          <span className="text-[10px] text-muted-foreground/40 flex-shrink-0 mr-1">
            {pendingCount} pending
          </span>
        )}

        {/* Cap indicator */}
        {cap !== undefined && (
          <span className={cn(
            'text-[10px] flex-shrink-0 mr-1.5',
            atCap ? 'text-amber-500/80' : 'text-muted-foreground/40',
          )}>
            {selectedArray.length}/{cap}
          </span>
        )}

        {open
          ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground/40 flex-shrink-0" />
          : <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/40 flex-shrink-0" />
        }
      </button>

      {/* ── Expanded content ──────────────────────────────────────────────── */}
      {open && (
        <div className="px-6 pb-4 space-y-2">
          {/* Cap warning */}
          {atCap && (
            <p className="text-[11px] text-amber-600 dark:text-amber-400">
              {cap} {config.resourceLabel} selected — limit reached.
              {platform !== 'github' && ' Deselect one to add another.'}
            </p>
          )}

          {/* No sources nudge */}
          {selectedIds.size === 0 && !loadingResources && (
            <p className="text-[11px] text-amber-600 dark:text-amber-400">
              No {config.resourceLabel} selected — task won't read any {config.label} data until you pick at least one.
            </p>
          )}

          {/* Resource list */}
          {loadingResources ? (
            <div className="flex items-center gap-2 py-2">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Loading {config.label} {config.resourceLabel}…</span>
            </div>
          ) : loadError ? (
            <div className="flex items-start gap-2 text-xs text-destructive/80">
              <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <span>{loadError}</span>
            </div>
          ) : resources.length === 0 ? (
            <p className="text-xs text-muted-foreground/60">
              No {config.resourceLabel} found. Make sure {config.label} is connected in Settings.
            </p>
          ) : (
            <div className="space-y-0.5 max-h-[260px] overflow-auto">
              {sortedResources.map(r => (
                <ResourceCheckRow
                  key={r.id}
                  resource={r}
                  selected={selectedIds.has(r.id)}
                  disabled={atCap}
                  onToggle={() => toggle(r.id)}
                />
              ))}
            </div>
          )}

          {/* Save / error / reset row */}
          {saveError && (
            <div className="flex items-center gap-1.5 text-[11px] text-destructive">
              <AlertCircle className="w-3 h-3" />{saveError}
            </div>
          )}

          {(hasChanges || saveSuccess) && (
            <div className="flex items-center gap-2 pt-1">
              {hasChanges && (
                <button
                  onClick={() => void save()}
                  disabled={saving}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                >
                  {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                  Save
                </button>
              )}
              {!hasChanges && saveSuccess && (
                <span className="inline-flex items-center gap-1 text-[11px] text-green-600 dark:text-green-400">
                  <Check className="w-3 h-3" /> Saved
                </span>
              )}
              {hasChanges && !saving && (
                <button
                  onClick={() => setSelectedIds(new Set(task.sources?.[platform] ?? []))}
                  className="text-[11px] text-muted-foreground hover:text-foreground"
                >
                  Reset
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
