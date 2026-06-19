'use client';

/**
 * Launcher — ADR-297 D4 + D14 + D14.1.
 *
 * Summon-first overlay listing every atomic surface available in the
 * workspace. Opens from TopBarSurface's launcher trigger button or
 * Escape-closes. Type to filter; Enter to navigate; click to navigate.
 *
 * Surface grouping per ADR-297 D4 — subtle tier headers. Tier groups derived
 * from surface.tier values emitted by the compositor (per
 * kernel_surface_entries + program bundle SURFACES.yaml surfaces[]).
 *
 * ADR-340 P3 (2026-06-12) — act-derived launcher IA, two modes:
 *
 *   AT REST (no query): the kernel tier groups by `launcher_tier` —
 *   "Workspace" (primary: Home · Operation · Files, the standing-loop
 *   compositions — ADR-346 promoted Operation and demoted Feed/Queue,
 *   which Operation now fronts), then the two Settings doors as SEPARATE
 *   labeled groups (ADR-341): "Operation" (Workspace Settings) ABOVE
 *   "System" (System Settings) — two objects, the operation vs the OS,
 *   not one "Configure" lump — then "Utilities" (Setup · Recurrence ·
 *   Agents · Feed · Queue).
 *   `search-only` surfaces are HIDDEN at rest — the constitution
 *   mirrors' first-class door is the Home constitution band (ADR-312
 *   slot #1; their pane door is Workspace Settings); the Settings panes'
 *   door is their parent container. Registers stay code-level taxonomy
 *   (ADR-309/312 unchanged); the operator-facing sort key is the act
 *   tier.
 *
 *   SEARCHING (query non-empty): FLAT — every navigable surface
 *   including search-only mirrors and pane-grade panes matches by
 *   title/summary/slug (ADR-340 D5 "search stays flat"; the Spotlight
 *   role). Selecting a pane opens System Settings at that pane via
 *   foregroundSurface resolution (ADR-340 P2).
 *
 * Program + composed tiers keep their single-group shape in both modes.
 *
 * D14.1 (2026-05-22): the per-row Keep toggle is DELETED. macOS
 * Launchpad has no pin affordance — clicking an app opens it; "Keep
 * in Dock" is discovered after using the app, via right-click on the
 * open Dock icon. The Launcher becomes pure launch. Keep is
 * exclusively a Dock-right-click action (TopBarSurface owns the
 * context menu). Singular Implementation: one Keep affordance, not
 * two.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { Search, X } from 'lucide-react';
import type { Surface } from '@/lib/compositor/types';
import { resolveSurfaceIcon } from '@/lib/shell/surface-icons';
import { Z_LAUNCHER_OVERLAY } from '@/lib/shell/z-tiers';
import { isKernelSurfaceSlug } from '@/types/desk';

interface LauncherProps {
  open: boolean;
  onClose: () => void;
  surfaces: Surface[];
  /** Open a surface + bring it to the foreground (D13). Singular
   *  action; the pre-D19.2 setSurface URL-write side-effect was
   *  deleted because URL is informational add-on, not a tracker of
   *  the foregrounded window (D19.2). */
  onForeground: (slug: string) => void;
  bundleTitleBySlug: Record<string, string>;
}

interface SurfaceGroup {
  label: string;
  tierKey: string;
  surfaces: Surface[];
}

// ADR-340 P3: kernel surfaces group by `launcher_tier` (the act-derived
// at-rest IA). Order top→bottom follows visit-frequency: the standing
// loop (Workspace), the one config door (System), then the utility
// class. `search-only` surfaces never appear at rest. Kernel surfaces
// missing a tier (a registry omission) fall to Utilities — never
// silently drop a surface from the index.
const KERNEL_TIER_GROUPS: { key: string; label: string; tier: string }[] = [
  { key: 'kernel:primary', label: 'Workspace', tier: 'primary' },
  // ADR-341 (2026-06-18): the two Settings doors are their OWN labeled
  // groups, Workspace Settings ABOVE System Settings — two objects (the
  // operation vs the OS), not one "Configure" lump. Order top→bottom.
  { key: 'kernel:workspace-config', label: 'Operation', tier: 'workspace-config' },
  { key: 'kernel:system-config', label: 'System', tier: 'system-config' },
  { key: 'kernel:utilities', label: 'Utilities', tier: 'utilities' },
];

function kernelTierGroupFor(s: Surface): { key: string; label: string } | null {
  if (s.launcher_tier === 'search-only') return null;
  const match = KERNEL_TIER_GROUPS.find((g) => g.tier === s.launcher_tier);
  return match ?? { key: 'kernel:utilities', label: 'Utilities' };
}

function groupSurfaces(
  surfaces: Surface[],
  bundleTitleBySlug: Record<string, string>
): SurfaceGroup[] {
  const groups = new Map<string, SurfaceGroup>();

  surfaces.forEach((s) => {
    let groupKey: string;
    let groupLabel: string;
    if (s.tier === 'kernel') {
      const g = kernelTierGroupFor(s);
      if (!g) return; // search-only: hidden at rest (found via flat search)
      groupKey = g.key;
      groupLabel = g.label;
    } else if (s.tier === 'composed') {
      groupKey = 'composed';
      groupLabel = 'Custom';
    } else {
      // tier="program:{slug}"
      const slug = (s.tier as string).slice('program:'.length);
      groupKey = `program:${slug}`;
      groupLabel = bundleTitleBySlug[slug] || slug;
    }
    if (!groups.has(groupKey)) {
      groups.set(groupKey, { label: groupLabel, tierKey: groupKey, surfaces: [] });
    }
    groups.get(groupKey)!.surfaces.push(s);
  });

  // Order: the three kernel act-tier groups (Workspace → System →
  // Utilities) first, then program groups (compositor insertion order),
  // then composed. Empty kernel groups are skipped.
  const ordered: SurfaceGroup[] = [];
  for (const g of KERNEL_TIER_GROUPS) {
    if (groups.has(g.key)) ordered.push(groups.get(g.key)!);
  }
  const kernelKeys = new Set(KERNEL_TIER_GROUPS.map((g) => g.key));
  Array.from(groups.entries()).forEach(([key, group]) => {
    if (!kernelKeys.has(key) && key !== 'composed') ordered.push(group);
  });
  if (groups.has('composed')) ordered.push(groups.get('composed')!);
  return ordered;
}

export function Launcher({
  open,
  onClose,
  surfaces,
  onForeground,
  bundleTitleBySlug,
}: LauncherProps) {
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus search on open; reset query on close.
  useEffect(() => {
    if (open) {
      setQuery('');
      setTimeout(() => inputRef.current?.focus(), 10);
    }
  }, [open]);

  // Escape closes
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  // Filter out launcher-non-navigable surfaces (chrome: route="" per
  // D11+D12+D14). The Dock has its own entry; we shouldn't list itself
  // as a navigation target.
  const navigableSurfaces = useMemo(
    () => surfaces.filter((s) => s.route !== ''),
    [surfaces]
  );

  // ADR-341: parent-container slug → title, for labeling pane rows in
  // search ("Workspace Settings pane" / "System Settings pane" / etc.).
  const parentTitleBySlug = useMemo(() => {
    const map: Record<string, string> = {};
    surfaces.forEach((s) => {
      map[s.slug] = s.title;
    });
    return map;
  }, [surfaces]);

  const filtered = useMemo(() => {
    if (!query.trim()) return navigableSurfaces;
    const q = query.toLowerCase();
    return navigableSurfaces.filter(
      (s) =>
        s.title.toLowerCase().includes(q) ||
        s.summary.toLowerCase().includes(q) ||
        s.slug.toLowerCase().includes(q)
    );
  }, [navigableSurfaces, query]);

  // ADR-340 P3 two modes: at rest → act-tier groups (search-only hidden);
  // searching → FLAT across every navigable surface incl. search-only
  // mirrors + pane-grade panes (the Spotlight role; D5 "search stays flat").
  const isSearching = query.trim().length > 0;

  const grouped = useMemo(
    () => groupSurfaces(filtered, bundleTitleBySlug),
    [filtered, bundleTitleBySlug]
  );

  const navigate = (surface: Surface) => {
    // D19.2 (2026-05-22): foregroundSurface is the SINGULAR action.
    // Pre-D19.2 we also called setSurface({type:'atomic', slug}) which
    // wrote the URL via window.history.replaceState — that's what made
    // clicking a Launcher item feel like a page redirect (operator
    // observed KVK 2026-05-22). Per the macOS-faithful frame, the URL
    // is informational add-on of the workspace, not a tracker of the
    // foregrounded window. The Dock indicator is the canonical
    // "what's foregrounded" signal. URL stays on /desktop (or whatever
    // the cold-load was) after first paint.
    if (isKernelSurfaceSlug(surface.slug)) {
      onForeground(surface.slug);
    }
    onClose();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const first = filtered[0];
    if (first) navigate(first);
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 flex items-start justify-center bg-black/40 backdrop-blur-sm pt-[10vh]"
      style={{ zIndex: Z_LAUNCHER_OVERLAY }}
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Surface launcher"
    >
      <div
        className="w-full max-w-lg overflow-hidden rounded-xl border border-border bg-background shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search */}
        <form onSubmit={handleSubmit} className="flex items-center gap-2 border-b border-border px-4 py-3">
          <Search className="h-4 w-4 text-muted-foreground" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search surfaces…"
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
          <button
            type="button"
            onClick={onClose}
            aria-label="Close launcher"
            className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </form>

        {/* Surface list — flat when searching (Spotlight role), act-tier
            groups at rest (Dock/Launchpad role). ADR-340 P3. */}
        <div className="max-h-[60vh] overflow-y-auto">
          {isSearching ? (
            filtered.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-muted-foreground">
                No surfaces match &ldquo;{query}&rdquo;
              </div>
            ) : (
              <div className="py-2">
                {filtered.map((surface) => {
                  const Icon = resolveSurfaceIcon(surface.icon_key);
                  return (
                    <button
                      key={surface.slug}
                      type="button"
                      onClick={() => navigate(surface)}
                      className="flex w-full items-center gap-3 px-4 py-2 text-left hover:bg-muted/60"
                    >
                      <div className="flex h-8 w-8 items-center justify-center rounded-md bg-muted text-muted-foreground">
                        <Icon className="h-4 w-4" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-medium">
                          {surface.title}
                          {surface.pane_of && (
                            // ADR-341: label by the parent door's title —
                            // panes now belong to System Settings,
                            // Workspace Settings, or Recurrence (ADR-340 D8).
                            <span className="ml-2 text-xs font-normal text-muted-foreground">
                              {parentTitleBySlug[surface.pane_of]
                                ? `${parentTitleBySlug[surface.pane_of]} pane`
                                : 'Settings pane'}
                            </span>
                          )}
                        </div>
                        <div className="truncate text-xs text-muted-foreground">
                          {surface.summary}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            )
          ) : grouped.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-muted-foreground">
              No surfaces available
            </div>
          ) : (
            grouped.map((group) => (
              <div key={group.tierKey} className="py-2">
                <div className="px-4 pb-1 pt-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/70">
                  {group.label}
                </div>
                {group.surfaces.map((surface) => {
                  const Icon = resolveSurfaceIcon(surface.icon_key);
                  return (
                    <button
                      key={surface.slug}
                      type="button"
                      onClick={() => navigate(surface)}
                      className="flex w-full items-center gap-3 px-4 py-2 text-left hover:bg-muted/60"
                    >
                      <div className="flex h-8 w-8 items-center justify-center rounded-md bg-muted text-muted-foreground">
                        <Icon className="h-4 w-4" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-medium">{surface.title}</div>
                        <div className="truncate text-xs text-muted-foreground">
                          {surface.summary}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
