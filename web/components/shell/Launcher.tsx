'use client';

/**
 * Launcher — ADR-297 D4 + D14.
 *
 * Summon-first overlay listing every atomic surface available in the
 * workspace. Opens from TopBarSurface's launcher trigger button or
 * Escape-closes. Type to filter; Enter to navigate; click to navigate.
 *
 * Surface grouping per ADR-297 D4 — subtle tier headers ("Workspace" /
 * "<Program>" / "Custom"). Tier groups derived from surface.tier values
 * emitted by the compositor (per kernel_surface_entries + program bundle
 * SURFACES.yaml surfaces[]).
 *
 * Keep/release affordance (D14 — was pin/unpin): each row carries a
 * pin icon toggle so operators customize the Dock from the launcher
 * itself (no separate settings surface needed). The icon stays a pin
 * (universal "keep this around" visual); the verb shifted in D14 from
 * "pin" to "Keep in Dock" / "Remove from Dock" so the right-click
 * Dock context menu and the launcher per-row toggle speak the same
 * language. ADR-297 §D14.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { Pin, PinOff, Search, X } from 'lucide-react';
import type { Surface } from '@/lib/compositor/types';
import { resolveSurfaceIcon } from '@/lib/shell/surface-icons';
import { useDesk } from '@/contexts/DeskContext';
import { isKernelSurfaceSlug } from '@/types/desk';
import { cn } from '@/lib/utils';

interface LauncherProps {
  open: boolean;
  onClose: () => void;
  surfaces: Surface[];
  /** Dock-permanence surfaces (D14 — was `pinned`). */
  kept: string[];
  /** Add a surface to the Dock-permanence list. */
  onKeep: (slug: string) => void;
  /** Remove a surface from the Dock-permanence list. */
  onRelease: (slug: string) => void;
  /** Open a surface + bring it to the foreground (D13). The pre-D13
   *  setSurface dispatch is retained as a side-effect inside this
   *  handler for legacy DeskState consumers; this prop is the D13
   *  canonical action. */
  onForeground: (slug: string) => void;
  bundleTitleBySlug: Record<string, string>;
}

interface SurfaceGroup {
  label: string;
  tierKey: string;
  surfaces: Surface[];
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
      groupKey = 'kernel';
      groupLabel = 'Workspace';
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

  // Order: kernel first, then program groups (insertion order from compositor),
  // then composed.
  const ordered: SurfaceGroup[] = [];
  if (groups.has('kernel')) ordered.push(groups.get('kernel')!);
  Array.from(groups.entries()).forEach(([key, group]) => {
    if (key !== 'kernel' && key !== 'composed') ordered.push(group);
  });
  if (groups.has('composed')) ordered.push(groups.get('composed')!);
  return ordered;
}

export function Launcher({
  open,
  onClose,
  surfaces,
  kept,
  onKeep,
  onRelease,
  onForeground,
  bundleTitleBySlug,
}: LauncherProps) {
  const { setSurface } = useDesk();
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

  const grouped = useMemo(
    () => groupSurfaces(filtered, bundleTitleBySlug),
    [filtered, bundleTitleBySlug]
  );

  const navigate = (surface: Surface) => {
    // D13/D14: foregroundSurface opens + foregrounds in one action.
    // setSurface kept in sync for legacy DeskState consumers.
    if (isKernelSurfaceSlug(surface.slug)) {
      onForeground(surface.slug);
      setSurface({ type: 'atomic', slug: surface.slug });
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
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 backdrop-blur-sm pt-[10vh]"
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

        {/* Surface list */}
        <div className="max-h-[60vh] overflow-y-auto">
          {grouped.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-muted-foreground">
              No surfaces match &ldquo;{query}&rdquo;
            </div>
          ) : (
            grouped.map((group) => (
              <div key={group.tierKey} className="py-2">
                <div className="px-4 pb-1 pt-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/70">
                  {group.label}
                </div>
                {group.surfaces.map((surface) => {
                  const Icon = resolveSurfaceIcon(surface.icon_key);
                  const isKept = kept.includes(surface.slug);
                  return (
                    <div
                      key={surface.slug}
                      className="flex items-center gap-3 px-4 py-2 hover:bg-muted/60"
                    >
                      <button
                        type="button"
                        onClick={() => navigate(surface)}
                        className="flex flex-1 items-center gap-3 text-left"
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
                      <button
                        type="button"
                        onClick={() => (isKept ? onRelease(surface.slug) : onKeep(surface.slug))}
                        aria-label={
                          isKept
                            ? `Remove ${surface.title} from Dock`
                            : `Keep ${surface.title} in Dock`
                        }
                        title={isKept ? 'Remove from Dock' : 'Keep in Dock'}
                        className={cn(
                          'rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground',
                          isKept && 'text-foreground'
                        )}
                      >
                        {isKept ? <PinOff className="h-3.5 w-3.5" /> : <Pin className="h-3.5 w-3.5" />}
                      </button>
                    </div>
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
