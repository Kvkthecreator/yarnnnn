'use client';

/**
 * StudioBlockInsertMenu — THE insert door (ADR-586 D1/D2/D3/D5/D7).
 *
 * One [+ Add] button, one door, on every medium: provenance stopped being a
 * door decision (the ADR-579 triad's toolbar topology is superseded; its laws
 * survive — one grouping module, one landing, named target, the WHO seam).
 *
 * The door is the PowerPoint-gallery shape the operator locked: a category
 * RAIL (Slide · Components · Text · Media · Data — derived, ordered by the
 * medium, never subsetting) beside a GALLERY of schematic thumbnails for the
 * active category. Two-pane rather than flyouts, so positioning is
 * accommodative BY CONSTRUCTION: one measured box, clamped to the viewport —
 * there is no nested panel to run off an edge.
 *
 * D5 — under the narrow breakpoint the SAME component renders as a bottom
 * sheet (categories as a chip row, gallery full-width). One list, two
 * housings; the housing is chrome, never a second mechanism.
 *
 * D7 — the Components gallery de-silos: the kernel's per-instance kinds and
 * the workspace's cited `*.component.html` library render in ONE gallery;
 * library items carry the "shared" marker and land their citation DIRECTLY
 * (the gallery item IS the file — no picker hop).
 *
 * It renders and reports picks. Choosing the target and landing the fragment
 * stay with the surface (ADR-443 D2 — never an eighth operation).
 */

import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { Link2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import {
  categorizeBlockRows,
  type BlockCategory,
  type BlockRowItem,
} from './blockRows';
import { BlockThumb } from './BlockThumb';
import { ArrangementThumb } from './ArrangementThumb';
import type { StudioArrangement, StudioVocabulary } from './StudioToolbar';

interface LibraryComponent {
  path: string;
  head_version_id: string | null;
}

interface StudioBlockInsertMenuProps {
  vocabulary: StudioVocabulary | null;
  /** ADR-586 D2 — the medium orders the categories (paged: Slide+Components
   *  lead; flow: Text leads, no Slide). Null = unresolved, treated as flow. */
  medium?: 'paged' | 'flow' | null;
  /** Viewport point to anchor at (the toolbar button's rect, or the
   *  right-click point already mapped to the page by the canvas). */
  x: number;
  y: number;
  /** Names where the block will land, so the member is never guessing. */
  targetLabel: string;
  onPick: (kind: string, label: string, fragment: string) => void;
  /** ADR-586 D7 — a library pick lands its citation directly (path + pin);
   *  the surface builds the cited fragment and lands it through the ONE
   *  landing. Absent = the library section does not render. */
  onPickLibrary?: (path: string, pin: string | null) => void;
  onClose: () => void;
  /** The Slide/Section category (paged only): the arrangement gallery. */
  pageSection?: {
    noun: string;
    arrangements: StudioArrangement[];
    onPick: (fragment: string, label: string) => void;
  };
}

function relPath(p: string): string {
  return p.replace(/^\/workspace\//, '');
}

function baseName(p: string): string {
  const parts = p.split('/');
  return (parts[parts.length - 1] || p).replace(/\.component\.html$/, '');
}

/** The rail's category keys for this open: 'slide' (chrome-owned, paged only)
 *  + the derived block categories in the medium's order. */
type RailKey = 'slide' | BlockCategory;

export function StudioBlockInsertMenu({
  vocabulary,
  medium = null,
  x,
  y,
  targetLabel,
  onPick,
  onPickLibrary,
  onClose,
  pageSection,
}: StudioBlockInsertMenuProps) {
  const boxRef = useRef<HTMLDivElement | null>(null);
  const [clamped, setClamped] = useState<{ left: number; top: number } | null>(null);
  // D5 — the housing decision is measured once per open. A menu that jumps
  // housings on live resize would re-anchor under the pointer; resize already
  // closes the door (the listener below), so the measure cannot go stale.
  const [sheet] = useState<boolean>(
    () => typeof window !== 'undefined' && window.innerWidth < 640,
  );
  const items: BlockRowItem[] = vocabulary?.blocks ?? [];
  const groups = categorizeBlockRows(items, medium);

  const hasSlide = !!pageSection && pageSection.arrangements.length > 0;
  const rail: Array<{ key: RailKey; label: string }> = [
    ...(hasSlide ? [{ key: 'slide' as const, label: `New ${pageSection!.noun}` }] : []),
    ...groups.map((g) => ({ key: g.key, label: g.label })),
  ];
  const [active, setActive] = useState<RailKey | null>(null);
  const activeKey = active ?? rail[0]?.key ?? null;

  // D7 — the library, fetched on open (the picker's own precedent: the
  // component lists itself). A failed fetch renders the kernel kinds alone —
  // the library is additive, never load-bearing for the door.
  const [library, setLibrary] = useState<LibraryComponent[]>([]);
  useEffect(() => {
    if (!onPickLibrary) return;
    let live = true;
    api.studio
      .citable()
      .then((c) => {
        if (live) setLibrary(c.components ?? []);
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [onPickLibrary]);

  // Measured clamp, not a guessed constant (popover housing only — the sheet
  // pins itself to the viewport bottom and needs no clamp). Re-runs when the
  // active category changes the box's real size: accommodative positioning is
  // the RE-MEASURE, not a guess.
  useLayoutEffect(() => {
    if (sheet) return;
    const el = boxRef.current;
    if (!el) return;
    const { width, height } = el.getBoundingClientRect();
    const MARGIN = 8;
    setClamped({
      left: Math.max(MARGIN, Math.min(x, window.innerWidth - width - MARGIN)),
      top: Math.max(MARGIN, Math.min(y, window.innerHeight - height - MARGIN)),
    });
  }, [x, y, items.length, activeKey, sheet]);

  // Dismissal, including the iframe blind spot: the canvas is a sandboxed,
  // opaque-origin frame, so a click or an Escape inside it never reaches these
  // parent listeners. The runtime bridges both out (yarnnn-canvas-press and
  // yarnnn-canvas-escape) — without the bridge this menu could only be closed
  // by clicking the thin chrome around the canvas.
  useEffect(() => {
    const close = () => onClose();
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    const onFrame = (e: MessageEvent) => {
      const t = (e.data as { type?: string } | null)?.type;
      // Scroll joins press and Escape: this menu is anchored to a point in the
      // page, and the canvas scrolling underneath it moves what that point
      // meant. The parent's own scroll listener is deaf to the iframe's
      // scroller (opaque origin), so the runtime's report is the only route.
      if (t === 'yarnnn-canvas-press' || t === 'yarnnn-canvas-escape' || t === 'yarnnn-scroll-pos') {
        onClose();
      }
    };
    window.addEventListener('mousedown', close);
    window.addEventListener('keydown', onKey);
    window.addEventListener('resize', close);
    window.addEventListener('message', onFrame);
    return () => {
      window.removeEventListener('mousedown', close);
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('resize', close);
      window.removeEventListener('message', onFrame);
    };
  }, [onClose]);

  // An empty vocabulary means the registry has not answered yet. Render nothing
  // rather than an empty bordered box that must be dismissed (the ADR-482 D9
  // rule: a menu with no acts is not a menu).
  if (items.length === 0) return null;

  const left = clamped?.left ?? x;
  const top = clamped?.top ?? y;

  const activeGroup = groups.find((g) => g.key === activeKey) ?? null;

  const gallery = (
    <div className="min-w-0 flex-1 overflow-y-auto p-1.5">
      {activeKey === 'slide' && hasSlide ? (
        <div className={`grid gap-1.5 ${sheet ? 'grid-cols-3' : 'grid-cols-2'}`}>
          {pageSection!.arrangements.map((a) => (
            <button
              key={a.slug}
              type="button"
              onClick={() => pageSection!.onPick(a.fragment, a.label)}
              title={a.description}
              className="flex flex-col gap-1 rounded-md border border-transparent p-1.5 text-left hover:border-border hover:bg-muted/20"
            >
              <ArrangementThumb areas={a.areas} fragment={a.fragment} />
              <span className="truncate text-[11px]">{a.label}</span>
            </button>
          ))}
        </div>
      ) : (
        <>
          <div className={`grid gap-1.5 ${sheet ? 'grid-cols-4' : 'grid-cols-3'}`}>
            {(activeGroup?.items ?? []).map((b) => (
              <button
                key={b.kind}
                type="button"
                // mousedown would fire the dismissal listener first and close
                // the menu before the click lands (both mounts live in the
                // parent document while the press may be reported from the
                // frame — the blockRows lesson, kept here).
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => onPick(b.kind, b.label, b.fragment)}
                title={b.description}
                className="flex flex-col gap-1 rounded-md border border-transparent p-1.5 text-left hover:border-border hover:bg-muted/20"
              >
                <BlockThumb kind={b.kind} />
                <span className="truncate text-[11px]">{b.label}</span>
              </button>
            ))}
          </div>
          {/* D7 — the library, inside the SAME gallery (one gallery, marked).
              A pick lands the citation directly through the one landing. */}
          {activeKey === 'components' && onPickLibrary && (
            <div className="mt-1 border-t border-border/60 pt-1">
              {library.length > 0 ? (
                library.map((c) => (
                  <button
                    key={c.path}
                    type="button"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => onPickLibrary(c.path, c.head_version_id)}
                    title={`${relPath(c.path)} — shared: edits at source reach every use`}
                    className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left hover:bg-muted/30"
                  >
                    <Link2 className="h-3 w-3 shrink-0 text-indigo-500/80" />
                    <span className="min-w-0 flex-1 truncate text-[11px]">{baseName(c.path)}</span>
                    <span className="shrink-0 text-[9px] uppercase tracking-wide text-muted-foreground">
                      shared
                    </span>
                  </button>
                ))
              ) : (
                <p className="px-2 py-1.5 text-[10px] leading-snug text-muted-foreground">
                  No shared components yet — ask the chat to compose one from a
                  screenshot or a source; it lands here.
                </p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );

  const railEl = (
    <div
      className={
        sheet
          ? 'flex shrink-0 gap-1 overflow-x-auto border-b border-border p-1.5'
          : 'flex w-28 shrink-0 flex-col gap-0.5 border-r border-border p-1'
      }
    >
      {rail.map((r) => (
        <button
          key={r.key}
          type="button"
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => setActive(r.key)}
          className={`rounded px-2 py-1.5 text-left text-[11.5px] ${
            sheet ? 'whitespace-nowrap' : 'w-full'
          } ${activeKey === r.key ? 'bg-muted/60 font-medium' : 'hover:bg-muted/30'}`}
        >
          {r.label}
        </button>
      ))}
    </div>
  );

  return (
    <div
      ref={boxRef}
      style={sheet ? undefined : { left, top }}
      className={
        sheet
          ? 'fixed inset-x-0 bottom-0 z-50 flex max-h-[70vh] flex-col rounded-t-lg border-t border-border bg-popover shadow-lg'
          : 'fixed z-50 flex max-h-[min(26rem,calc(100vh-16px))] w-[26rem] flex-col rounded-md border border-border bg-popover shadow-md'
      }
      onMouseDown={(e) => e.stopPropagation()}
      onContextMenu={(e) => e.preventDefault()}
    >
      {/* The target is NAMED. On a spatial surface "insert" without a stated
          destination is the ambiguity that makes members undo and retry. */}
      <p className="shrink-0 border-b border-border/60 px-2.5 py-1.5 text-[10px] uppercase tracking-wide text-muted-foreground">
        Add — into {targetLabel}
      </p>
      <div className={`flex min-h-0 flex-1 ${sheet ? 'flex-col' : ''}`}>
        {railEl}
        {gallery}
      </div>
    </div>
  );
}
