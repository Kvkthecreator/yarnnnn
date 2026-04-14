'use client';

/**
 * PlatformSourcesSection — Inline source picker for platform tasks.
 *
 * Rendered inside TrackingMiddle (accumulates_context) and ActionMiddle
 * (external_action) when the task has a platform dependency (slack-digest,
 * notion-digest, github-digest, slack-respond, notion-update).
 *
 * Design decisions:
 * - Collapsible panel — collapsed by default when sources are already set,
 *   expanded when no sources are configured (first-run nudge).
 * - Uses getLandscape for the full resource list (same data as Context page).
 * - On save: patches TASK.md via PATCH /tasks/{slug}/sources, then notifies
 *   parent to refresh (so metadata strip re-reads updated task).
 * - Deliberately lighter than the full ResourceList (no attention/coverage
 *   tabs) — Work surface is operational, not a source management hub.
 *
 * ADR-158 Phase 2: per-task source selection.
 */

import { useEffect, useState, useCallback } from 'react';
import {
  ChevronDown, ChevronRight, Hash, FileText, GitBranch,
  Loader2, AlertCircle, Check, Save,
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
  iconSmall: React.ReactNode;
}

const PLATFORM_CONFIG: Record<SupportedPlatform, PlatformConfig> = {
  slack: {
    label: 'Slack',
    resourceLabel: 'channels',
    icon: <Hash className="w-4 h-4" />,
    iconSmall: <Hash className="w-3 h-3" />,
  },
  notion: {
    label: 'Notion',
    resourceLabel: 'pages',
    icon: <FileText className="w-4 h-4" />,
    iconSmall: <FileText className="w-3 h-3" />,
  },
  github: {
    label: 'GitHub',
    resourceLabel: 'repositories',
    icon: <GitBranch className="w-4 h-4" />,
    iconSmall: <GitBranch className="w-3 h-3" />,
  },
};

// Derive the platform from task type_key.
// Returns null for non-platform tasks.
function resolvePlatform(typeKey: string | undefined): SupportedPlatform | null {
  if (!typeKey) return null;
  if (typeKey.startsWith('slack')) return 'slack';
  if (typeKey.startsWith('notion')) return 'notion';
  if (typeKey.startsWith('github')) return 'github';
  return null;
}

// ─── Resource row ─────────────────────────────────────────────────────────────

interface ResourceItem {
  id: string;
  name: string;
  resource_type: string;
  coverage_state: string;
  last_extracted_at: string | null;
}

function ResourceCheckRow({
  resource,
  platform,
  selected,
  onToggle,
}: {
  resource: ResourceItem;
  platform: SupportedPlatform;
  selected: boolean;
  onToggle: () => void;
}) {
  const config = PLATFORM_CONFIG[platform];
  const isFresh = resource.last_extracted_at !== null;

  return (
    <button
      type="button"
      onClick={onToggle}
      className={cn(
        'flex items-center gap-2.5 w-full px-3 py-2 rounded-md text-left transition-colors text-xs',
        selected
          ? 'bg-primary/8 border border-primary/20 text-foreground'
          : 'border border-transparent hover:bg-muted/50 text-muted-foreground hover:text-foreground',
      )}
    >
      {/* Checkbox */}
      <span
        className={cn(
          'flex-shrink-0 w-3.5 h-3.5 rounded border flex items-center justify-center',
          selected
            ? 'bg-primary border-primary'
            : 'border-border',
        )}
      >
        {selected && <Check className="w-2.5 h-2.5 text-primary-foreground" />}
      </span>

      {/* Platform icon */}
      <span className={cn('flex-shrink-0', selected ? 'text-primary' : 'text-muted-foreground/60')}>
        {config.iconSmall}
      </span>

      {/* Name */}
      <span className="flex-1 min-w-0 truncate font-medium">
        {platform === 'slack' ? `#${resource.name}` : resource.name}
      </span>

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

// ─── Main component ──────────────────────────────────────────────────────────

interface PlatformSourcesSectionProps {
  task: Task;
  onSourcesUpdated?: () => void; // parent refreshKey bump
}

export function PlatformSourcesSection({ task, onSourcesUpdated }: PlatformSourcesSectionProps) {
  const platform = resolvePlatform(task.type_key);
  if (!platform) return null;

  const config = PLATFORM_CONFIG[platform];

  // Current selected IDs from task TASK.md (may be undefined on first render)
  const initialSelected = new Set<string>(task.sources?.[platform] ?? []);

  const [open, setOpen] = useState(initialSelected.size === 0); // expand if no sources
  const [resources, setResources] = useState<ResourceItem[]>([]);
  const [loadingResources, setLoadingResources] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(initialSelected);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Re-sync selectedIds when task.sources changes (e.g. after save)
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
  }, [platform, config]);

  // Load resources when expanded
  useEffect(() => {
    if (open && resources.length === 0 && !loadingResources) {
      void loadResources();
    }
  }, [open]);

  const hasChanges = (() => {
    const current = new Set(task.sources?.[platform] ?? []);
    if (current.size !== selectedIds.size) return true;
    return Array.from(selectedIds).some(id => !current.has(id));
  })();

  const toggle = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
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
      setSaveError('Failed to save sources. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const selectedCount = selectedIds.size;

  return (
    <div className="border-b border-border/40">
      {/* Header / toggle */}
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="flex w-full items-center gap-2 px-6 py-3 text-left hover:bg-muted/20 transition-colors"
      >
        <span className="text-muted-foreground/60">
          {config.icon}
        </span>
        <span className="flex-1 text-[11px] font-medium text-muted-foreground/70 uppercase tracking-wide">
          {config.label} {config.resourceLabel}
        </span>
        <span className="text-[10px] text-muted-foreground/50 mr-2">
          {selectedCount > 0 ? `${selectedCount} selected` : 'none selected'}
        </span>
        {open
          ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground/40" />
          : <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/40" />
        }
      </button>

      {/* Expanded content */}
      {open && (
        <div className="px-6 pb-4 space-y-3">
          {/* No sources nudge */}
          {selectedCount === 0 && !loadingResources && (
            <p className="text-[11px] text-amber-600 dark:text-amber-400">
              No {config.resourceLabel} selected — this task won't read any {config.label} data until you select at least one.
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
              No {config.resourceLabel} found in {config.label}. Make sure {config.label} is connected in Settings.
            </p>
          ) : (
            <div className="space-y-1 max-h-[280px] overflow-auto">
              {resources.map(r => (
                <ResourceCheckRow
                  key={r.id}
                  resource={r}
                  platform={platform}
                  selected={selectedIds.has(r.id)}
                  onToggle={() => toggle(r.id)}
                />
              ))}
            </div>
          )}

          {/* Save / error */}
          {saveError && (
            <div className="flex items-center gap-1.5 text-[11px] text-destructive">
              <AlertCircle className="w-3 h-3" />
              {saveError}
            </div>
          )}

          {(hasChanges || saveSuccess) && (
            <div className="flex items-center gap-2">
              {hasChanges && (
                <button
                  onClick={() => void save()}
                  disabled={saving}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                >
                  {saving
                    ? <Loader2 className="w-3 h-3 animate-spin" />
                    : <Save className="w-3 h-3" />
                  }
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
