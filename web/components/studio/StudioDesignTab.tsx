'use client';

/**
 * StudioDesignTab — the scope-switching inspector (ADR-453 D4).
 *
 * The right column's second tab (Chat | Design — the Canva model, never a
 * fourth column). What it shows follows the canvas selection's GRAIN:
 *
 *  - nothing selected → DOCUMENT scope: the design-system picker (ADR-449 D5
 *    finally homed — discovery from the vocabulary, apply through the one
 *    mechanical door) + the artifact's layout.
 *  - a page (slide/section) → PAGE scope: the Re-arrange thumbnail gallery +
 *    page tokens (tone; valign on deck slides; column ratio on multi-column
 *    arrangements) + Duplicate / Move / Delete.
 *  - a slot → SLOT scope: name + role, and the role-gated quick-add (flow →
 *    a text block; media → the workspace image picker).
 *  - a block → BLOCK scope: block tokens (align/tone; media blocks add
 *    height/fit) + Ask about this (the one judgment bridge) + Duplicate /
 *    Move / Delete + the double-click-to-edit hint.
 *
 * Everything here EXECUTES deterministic ops through the surface's applyOp
 * (the one CAS door) — tokens, not pixels (ADR-453 D1); current values are
 * parsed from the artifact SOURCE at render (derived, never stored).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowDown,
  ArrowUp,
  Check,
  Copy,
  Loader2,
  MessageSquare,
  Palette,
  Trash2,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import {
  type StudioMeasure,
  type StudioSelection,
  type StudioToken,
  type StudioVocabulary,
} from './StudioToolbar';

export type StructVerb = 'duplicate' | 'up' | 'down' | 'delete';

const PAGE_SEL = 'section.slide, [data-arrange]';

/** The TEXT kinds a block can turn into (ADR-456 W2) — text-shaped only:
 *  structured/cited kinds (table/metrics/chart/figure/gallery) and headings
 *  (they anchor pages) are not conversion targets. */
/** The block kinds a block can be turned INTO (ADR-456 W2) — text kinds only,
 *  because the conversion rebuilds text units and a citation must never
 *  flatten. Exported so the right-click submenu (ADR-479 D5) offers exactly the
 *  legal set: one list, two mounts. A copy would drift, and a menu offering an
 *  illegal conversion is a promise the op refuses to keep. */
export const TURN_INTO_KINDS = ['prose', 'callout', 'quote', 'checklist', 'toggle'];

function baseName(p: string): string {
  const parts = p.split('/');
  return parts[parts.length - 1] || p;
}

interface StudioDesignTabProps {
  vocabulary: StudioVocabulary | null;
  /** The artifact's layout slug (document/deck/article). */
  layout: string;
  /** The artifact's SOURCE html — token values + skin ref parse from it. */
  html: string;
  selection: StudioSelection | null;
  /** EXECUTE: set (value) / clear (null) a token on the selected block/page,
   *  or on the artifact ROOT (document grain — ADR-455). */
  onSetToken: (grain: 'block' | 'page' | 'document', key: string, value: string | null) => void;
  onBlockVerb: (verb: StructVerb) => void;
  onPageVerb: (verb: StructVerb) => void;
  /** EXECUTE: turn the selected block into another TEXT kind (ADR-456 W2 —
   *  convertBlock: id + tokens survive, text units rebuilt into the target). */
  onTurnInto: (kind: string, label: string, fragment: string) => void;
  /** ADR-466 D2: clear the selected block's x/y measures — the positioned
   *  block returns to the page's flow (one revision). */
  onReturnToFlow: () => void;
  /** ADR-485 follow-on: the served measures (`vocabulary.measures`) — the Design
   *  tab reads a block's CURRENT w/h back from its --y* style so a member sees
   *  the size the drag authored. Empty until the vocabulary lands. */
  measures: StudioMeasure[];
  /** ADR-485 follow-on: reset a size measure to Auto (the absence-default) — the
   *  read-back's clear affordance, since the drag is the authoring path. */
  onClearMeasure: (key: 'w' | 'h') => void;
  /** Seed the lane with the selection and flip to the Chat tab. */
  onAskAboutSelection: () => void;
  /** EXECUTE: apply a design system's composed skin element (resolve + write). */
  onApplyDesignSystem: (manifestPath: string) => Promise<void>;
  /** EXECUTE: remove the marked skin element. */
  onRemoveDesignSystem: () => void;
  /** ADR-462 D14: a design system was imported — the surface refetches the
   *  served vocabulary so the picker sees it (the payload carries kernel
   *  constants AND workspace state; only the second half goes stale). */
  onImported?: () => void;
  /** EXECUTE: role-gated slot adds (ADR-453 D5). */
  onAddTextInSlot: (slot: string, slideIndex: number | null, pageIndex: number | null) => void;
  onInsertImageInSlot: (
    path: string,
    slot: string,
    slideIndex: number | null,
    pageIndex: number | null,
  ) => void;
  /** EXECUTE: set/remove the page's cited background image (ADR-456 W3). */
  onSetPageBackground: (path: string) => void;
  onRemovePageBackground: () => void;
  /** ADR-458 D3: the artifact-as-file verbs — the SAME shared implementation
   *  the Files surface uses, homed in the document scope (the surface-bar
   *  "File actions" menu is deleted). Trash falls back to the landing. */
  fileVerbs: {
    copyLink: () => void;
    duplicate: () => void;
    rename: () => void;
    move: () => void;
    trash: () => void;
    /** ADR-437 D4 / ADR-465: mint a /s/{token} share link for this artifact and
     *  copy it. Resolves on success, rejects on failure (the tab surfaces the
     *  transient copied/error state). Runs in the parent (artifactPath + api). */
    share: () => Promise<void>;
  };
  /** ADR-466 D6 — the boundary projections: Print/PDF (the browser's print
   *  over the resolved projection) + the AI reference (the interop-face
   *  handle). Both run in the parent. */
  exportVerbs: {
    print: () => void;
    copyAiRef: () => Promise<void>;
    /** ADR-475 §13 — the IMAGES app's raster projection (rasterize the stage,
     *  download a PNG). Present only for IMAGES; undefined for Studio, whose
     *  boundary projection is Print/PDF. */
    exportPng?: () => Promise<void>;
  };
}

/** One token family as a segmented control. "Auto" is the default (absence —
 *  clearing removes the attribute; the default value is never written). */
function TokenControl({
  token,
  current,
  onSet,
}: {
  token: StudioToken;
  current: string | null;
  onSet: (value: string | null) => void;
}) {
  const seg =
    'rounded px-1.5 py-0.5 text-[10px] transition-colors border';
  return (
    <div>
      <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        {token.label}
      </p>
      <div className="flex flex-wrap gap-1" title={token.description}>
        <button
          type="button"
          onClick={() => onSet(null)}
          className={`${seg} ${
            current == null
              ? 'border-foreground/50 text-foreground'
              : 'border-border text-muted-foreground hover:bg-muted/40'
          }`}
        >
          Auto
        </button>
        {token.values.map((v) => (
          <button
            key={v.value}
            type="button"
            onClick={() => onSet(current === v.value ? null : v.value)}
            className={`${seg} ${
              current === v.value
                ? 'border-indigo-400 bg-indigo-50/60 text-indigo-900 dark:bg-indigo-950/40 dark:text-indigo-200'
                : 'border-border text-muted-foreground hover:bg-muted/40'
            }`}
          >
            {v.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/** The typography chips (ADR-455) — the Notion "Ag" affordance, our grammar:
 *  each value previews in its own stack; Auto = the layout/skin default. */
const FONT_STACKS: Record<string, string> = {
  serif: "Georgia, 'Times New Roman', serif",
  sans: "system-ui, -apple-system, 'Segoe UI', sans-serif",
  mono: "ui-monospace, 'SF Mono', Menlo, monospace",
};

function FontControl({
  token,
  current,
  onSet,
}: {
  token: StudioToken;
  current: string | null;
  onSet: (value: string | null) => void;
}) {
  const chip = (value: string | null, label: string, stack?: string) => {
    const active = (current ?? null) === value;
    return (
      <button
        key={label}
        type="button"
        onClick={() => onSet(active && value != null ? null : value)}
        className={`flex w-14 flex-col items-center gap-0.5 rounded-md border px-1 py-1.5 transition-colors ${
          active
            ? 'border-indigo-400 bg-indigo-50/60 dark:bg-indigo-950/40'
            : 'border-border hover:bg-muted/40'
        }`}
      >
        <span className="text-lg leading-none" style={stack ? { fontFamily: stack } : undefined}>
          Ag
        </span>
        <span className="text-[9px] text-muted-foreground">{label}</span>
      </button>
    );
  };
  return (
    <div>
      <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        {token.label}
      </p>
      <div className="flex flex-wrap gap-1.5" title={token.description}>
        {chip(null, 'Auto')}
        {token.values.map((v) => chip(v.value, v.label, FONT_STACKS[v.value]))}
      </div>
    </div>
  );
}

/** The structural verb row (Duplicate / Move up / Move down / Delete). */
function VerbRow({ noun, onVerb }: { noun: string; onVerb: (v: StructVerb) => void }) {
  const btn =
    'inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[10px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground';
  return (
    <div className="flex flex-wrap gap-1">
      <button type="button" className={btn} onClick={() => onVerb('duplicate')}>
        <Copy className="h-3 w-3" /> Duplicate
      </button>
      <button type="button" className={btn} onClick={() => onVerb('up')} title={`Move ${noun} up`}>
        <ArrowUp className="h-3 w-3" /> Up
      </button>
      <button type="button" className={btn} onClick={() => onVerb('down')} title={`Move ${noun} down`}>
        <ArrowDown className="h-3 w-3" /> Down
      </button>
      <button
        type="button"
        className={`${btn} hover:border-red-300 hover:text-red-600`}
        onClick={() => onVerb('delete')}
        title={`Delete this ${noun} (a revision — revertible)`}
      >
        <Trash2 className="h-3 w-3" /> Delete
      </button>
    </div>
  );
}

const SECTION = 'space-y-2 border-b border-border p-3';
const HEADING = 'text-[10px] font-medium uppercase tracking-wide text-muted-foreground';

export function StudioDesignTab({
  vocabulary,
  layout,
  html,
  selection,
  onSetToken,
  onBlockVerb,
  onPageVerb,
  onTurnInto,
  onReturnToFlow,
  measures,
  onClearMeasure,
  onAskAboutSelection,
  onApplyDesignSystem,
  onRemoveDesignSystem,
  onImported,
  onAddTextInSlot,
  onInsertImageInSlot,
  onSetPageBackground,
  onRemovePageBackground,
  fileVerbs,
  exportVerbs,
}: StudioDesignTabProps) {
  const doc = useMemo(() => {
    if (typeof window === 'undefined' || !html) return null;
    return new DOMParser().parseFromString(html, 'text/html');
  }, [html]);

  // A slot is a selection grain only where it is a DISTINGUISHABLE REGION.
  //
  // On 13 of 17 arrangements the page declares exactly one flow slot, and that
  // slot is coextensive with the page's content box (measured on a title
  // slide: slot 992px, slide inner 992px, offset 0). Selecting it drew a box
  // around the whole slide and offered one act — so it read as "you have
  // selected the layout master", an object the member cannot move, resize,
  // reorder or delete, because its geometry belongs to the arrangement (the
  // layer rule, STUDIO.md). PowerPoint refuses the same thing: a layout's
  // content area is not selectable on the slide; you change it via Layout.
  //
  // The two cases where the slot IS a real region survive:
  //   · 2+ slots — two-column / comparison / feature-grid: the outline names a
  //     genuine sub-region, and `ratio` is the act that resizes it.
  //   · a MEDIA slot — `picture-with-caption` / `full-bleed`: this scope is
  //     the image picker's home, and `onAddHere` routes here deliberately for
  //     role='media'. Removing it would strip the picker.
  //
  // Derived from the served registry, never a layout slug (ADR-481 D4: the
  // ladder loses a grain BY DERIVATION, not by suppression).
  const slotIsRegion = useMemo(() => {
    if (!selection?.slot) return false;
    const row = vocabulary?.arrangements?.[layout]?.find((a) => a.slug === selection.arrange);
    if (!row) return true; // unknown arrangement: keep the grain, never hide a real slot
    if (row.slots.length >= 2) return true;
    return row.slots.find((s) => s.name === selection.slot)?.role === 'media';
  }, [selection, vocabulary, layout]);

  const scope: 'document' | 'block' | 'slot' | 'page' = !selection
    ? 'document'
    : selection.blockId
      ? 'block'
      : selection.slot && slotIsRegion
        ? 'slot'
        : selection.slideIndex != null || selection.pageIndex != null
          ? 'page'
          : 'document';

  // The selected SOURCE element — token current-values read from it.
  const selectedEl = useMemo(() => {
    if (!doc || !selection) return null;
    if (selection.blockId) {
      return doc.querySelector(`[data-block-id="${CSS.escape(selection.blockId)}"]`);
    }
    if (selection.slideIndex != null) {
      return doc.querySelectorAll('section.slide')[selection.slideIndex] ?? null;
    }
    if (selection.pageIndex != null) {
      return doc.querySelectorAll(PAGE_SEL)[selection.pageIndex] ?? null;
    }
    return null;
  }, [doc, selection]);

  const tokens = vocabulary?.tokens ?? [];
  const mediaKinds = vocabulary?.media_kinds ?? [];
  const arrangements = vocabulary?.arrangements?.[layout] ?? [];
  const pageNoun = layout === 'deck' ? 'slide' : 'section';

  // ADR-485 follow-on — the SIZE measures a block can carry (w/h), and which of
  // them apply at this scope (ADR-461 D4 `applies`: block-staged = a block on a
  // fixed frame; media = a media block anywhere). This is the read-back the
  // inspector was missing entirely: a member who dragged a block to 60% wide
  // had no numeric confirmation anywhere in the tab (the value lived only in the
  // transient in-gesture frame label). The position measures (x/y/z) stay OUT of
  // this — they are the "Return to flow" state, shown separately below.
  const sizeMeasures = useMemo(() => {
    if (scope !== 'block') return [];
    const isMedia = !!selection?.blockKind && mediaKinds.includes(selection.blockKind);
    const framed = !!selectedEl?.closest('.slide');
    return (measures ?? []).filter(
      (m) =>
        (m.key === 'w' || m.key === 'h') &&
        ((framed && m.applies.includes('block-staged')) ||
          (isMedia && m.applies.includes('media'))),
    );
  }, [scope, measures, selection, selectedEl, mediaKinds]);

  // The current value of a measure, parsed from the block's own --y* style —
  // derived at render, never stored (the ADR-453 D1 convention every token uses).
  const measureValue = useCallback(
    (m: StudioMeasure): number | null => {
      const style = selectedEl?.getAttribute('style') ?? '';
      const rx = new RegExp(`${m.css_var}\\s*:\\s*(-?\\d+(?:\\.\\d+)?)`);
      const hit = style.match(rx);
      return hit ? Number(hit[1]) : null;
    },
    [selectedEl],
  );

  // Which token families apply at the current scope (ADR-453 D1 `applies`).
  const applicable = useMemo(() => {
    if (scope === 'block') {
      const isMedia = !!selection?.blockKind && mediaKinds.includes(selection.blockKind);
      return tokens.filter(
        (t) => t.applies.includes('block') || (isMedia && t.applies.includes('media')),
      );
    }
    if (scope === 'page') {
      const isSlide = layout === 'deck' && !!selectedEl?.matches('section.slide');
      const arrangeSlug = selectedEl?.getAttribute('data-arrange') ?? selection?.arrange ?? null;
      const row = arrangements.find((a) => a.slug === arrangeSlug);
      const multicol = row
        ? row.slots.filter((s) => s.role !== 'heading').length >= 2
        : (selectedEl?.querySelectorAll('[data-slot]').length ?? 0) >= 2;
      const hasBg = selectedEl?.getAttribute('data-ref-kind') === 'background';
      return tokens.filter(
        (t) =>
          t.applies.includes('page') ||
          (isSlide && t.applies.includes('page-deck')) ||
          (multicol && t.applies.includes('page-multicol')) ||
          (hasBg && t.applies.includes('page-bg')),
      );
    }
    return [];
  }, [scope, tokens, mediaKinds, selection, selectedEl, arrangements, layout]);

  // ── Document scope: root-grain tokens (ADR-455) + the design-system
  // picker (ADR-449 D5 homed) ──────────────────────────────────────────────
  const root = doc?.documentElement ?? null;
  const docTokens = useMemo(
    () =>
      tokens.filter(
        (t) =>
          t.applies.includes('document') ||
          // document-flow = document/article only: a deck is a fixed stage and
          // a page is full-width bands — measure applies to neither (W3).
          ((layout === 'document' || layout === 'article') &&
            t.applies.includes('document-flow')) ||
          (layout === 'deck' && t.applies.includes('document-deck')),
        // NOTE: the `canvas` branch (ADR-471 D-c's aspect token) is DELETED —
        // ADR-472 moved the canvas to the IMAGES app's `image` layout, so no
        // served layout is `canvas` and no served token declares
        // `document-canvas`. Verified against the registry, not assumed
        // (ADR-482 §9 recorded it as owed).
      ),
    [tokens, layout],
  );
  const skinRef = doc?.querySelector('head style[data-skin]')?.getAttribute('data-ref') ?? null;
  const designSystems = vocabulary?.design_systems ?? [];
  const [applying, setApplying] = useState<string | null>(null);
  const [applyError, setApplyError] = useState<string | null>(null);
  const importRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importReceipt, setImportReceipt] = useState<{
    name: string;
    written: string[];
    sources: string[];
    skipped: string[];
    warnings: string[];
  } | null>(null);

  const runImport = useCallback(
    async (f: File) => {
      setImporting(true);
      setImportError(null);
      setImportReceipt(null);
      try {
        const r = await api.studio.importDesignSystem(f);
        setImportReceipt(r);
        // The picker reads the served vocabulary, so the new system is
        // invisible until it refetches — the exact staleness that made the
        // picker deny a design system that already existed (2026-07-16).
        onImported?.();
      } catch (e) {
        setImportError(e instanceof Error ? e.message : 'Import failed.');
      } finally {
        setImporting(false);
      }
    },
    [onImported],
  );

  // ADR-456 W3 + DESIGN-SYSTEMS.md §5: the theme panel — the applied skin's
  // custom properties, parsed from the artifact's own marked element (read
  // legibility; the theme's FILES are the source of truth). The kernel now
  // consumes a widened vocabulary (an ink ramp, a radius scale, a type scale)
  // so more of a real system's tokens paint; the ones that theme the chrome
  // are surfaced first. The mechanical var-editor is unblocked (the §5 Q4
  // PATCH permission shipped) but still a named follow-on — it needs a design
  // pass for WHICH flattened source a value writes back to.
  const skinVars = useMemo(() => {
    const css = doc?.querySelector('head style[data-skin]')?.textContent ?? '';
    const out: Array<{ name: string; value: string }> = [];
    const rx = /--([a-z0-9-]+)\s*:\s*([^;}]+)[;}]/gi;
    let m;
    while ((m = rx.exec(css)) && out.length < 40) {
      out.push({ name: m[1], value: m[2].trim() });
    }
    // Surface the kernel-consumed vocabulary first — those are the tokens that
    // actually theme the chrome (§5 Move 1). The rest follow, still legible.
    const consumed = new Set([
      'ink', 'ink-06', 'ink-10', 'paper', 'muted', 'accent', 'deck-stage',
      'radius-sm', 'radius-md', 'radius-lg', 'radius-pill',
      'text-xs', 'text-sm', 'text-base', 'text-lg', 'text-xl',
      'text-2xl', 'text-3xl', 'text-4xl', 'text-5xl', 'fresh', 'danger', 'warn',
    ]);
    return out
      .sort((a, b) => Number(consumed.has(b.name)) - Number(consumed.has(a.name)))
      .slice(0, 12);
  }, [doc]);

  // ADR-456 W3: the page background — cited image on the page element.
  const pageBgRef =
    scope === 'page' && selectedEl?.getAttribute('data-ref-kind') === 'background'
      ? selectedEl.getAttribute('data-ref')
      : null;
  const [bgPicking, setBgPicking] = useState(false);
  const [bgImages, setBgImages] = useState<Array<{ path: string }> | null>(null);
  // Close the picker when the selection moves to a DIFFERENT page. Keying on
  // `selection` itself was a bug (operator, 2026-07-22: "set background doesn't
  // work"): the surface rebuilds that object on every point message, so any
  // re-fire — including the one the click on "Set background…" itself
  // provoked — collapsed the picker before an image could be chosen. Key on
  // the identity of the selected page, not the object's.
  const selectedPageKey =
    selection?.slideIndex ?? selection?.pageIndex ?? null;
  useEffect(() => {
    setBgPicking(false);
  }, [selectedPageKey]);
  useEffect(() => {
    if (!bgPicking || bgImages) return;
    api.studio
      .citable()
      .then((c) => setBgImages(c.images))
      .catch(() => setBgImages([]));
  }, [bgPicking, bgImages]);

  const applyDs = async (manifestPath: string) => {
    setApplying(manifestPath);
    setApplyError(null);
    try {
      await onApplyDesignSystem(manifestPath);
    } catch (e) {
      setApplyError(e instanceof Error ? e.message : 'Could not apply the design system.');
    } finally {
      setApplying(null);
    }
  };

  // ── Share (ADR-437 D4 wedge, surfaced in the Properties document scope) ────
  // The mint-and-copy runs in the PARENT (fileVerbs.share) where artifactPath +
  // api live, matching the file-verb threading. This holds only the button's
  // transient copied/error state. Distinct from fileVerbs.copyLink (the in-app
  // member deep-link): a share link makes the recipient a broad member of the
  // commons on accept (the Figma default, ADR-437 D4.2 / ADR-465 D3).
  const [sharing, setSharing] = useState(false);
  const [shareState, setShareState] = useState<'idle' | 'copied' | 'error'>('idle');
  const runShare = useCallback(async () => {
    setSharing(true);
    setShareState('idle');
    try {
      await fileVerbs.share();
      setShareState('copied');
    } catch {
      setShareState('error');
    } finally {
      setSharing(false);
    }
  }, [fileVerbs]);

  // ── Export (ADR-466 D6): the AI-reference copy's transient receipt ──────
  const [aiRefState, setAiRefState] = useState<'idle' | 'copied'>('idle');
  const runCopyAiRef = useCallback(async () => {
    try {
      await exportVerbs.copyAiRef();
      setAiRefState('copied');
      setTimeout(() => setAiRefState('idle'), 2500);
    } catch {
      /* clipboard denied — nothing durable failed */
    }
  }, [exportVerbs]);

  // ── Raster export (ADR-475 §13, IMAGES only): rasterizing is real work
  // (resolve → re-inline → snapshot), so the button shows a working state and
  // surfaces a failure rather than silently doing nothing. ─────────────────
  const [pngState, setPngState] = useState<'idle' | 'working' | 'error'>('idle');
  const runExportPng = useCallback(async () => {
    if (!exportVerbs.exportPng) return;
    setPngState('working');
    try {
      await exportVerbs.exportPng();
      setPngState('idle');
    } catch {
      setPngState('error');
      setTimeout(() => setPngState('idle'), 3000);
    }
  }, [exportVerbs]);

  // ── Slot scope: role-gated quick-add (media → the image picker) ─────────
  const slotRole = useMemo(() => {
    if (scope !== 'slot' || !selection?.slot) return null;
    const row = arrangements.find((a) => a.slug === selection.arrange);
    return row?.slots.find((s) => s.name === selection.slot)?.role ?? 'flow';
  }, [scope, selection, arrangements]);

  const [slotImages, setSlotImages] = useState<Array<{ path: string }> | null>(null);
  useEffect(() => {
    if (scope !== 'slot' || slotRole !== 'media' || slotImages) return;
    api.studio
      .citable()
      .then((c) => setSlotImages(c.images))
      .catch(() => setSlotImages([]));
  }, [scope, slotRole, slotImages]);

  const askBtn =
    'inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[10px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground';

  return (
    <div className="flex-1 overflow-y-auto text-sm">
      {/* ── The artifact head — EVERY scope, every template ──────────────
          File / Share / Export are document-global acts; scope-gating them
          under "nothing selected" hid them exactly when the member was
          working a section ("share/export … seems to have in deck … but not
          here"). That mode-invariance is preserved exactly.

          ADR-482 D6: the panel is ordered by SCOPE — outermost first. This
          block was the tail, so a block selection read HEADING · T1 → WIDTH →
          ALIGN → TONE → FILE and the file's own identity sat under the
          properties of whatever happened to be clicked. Reading file-first
          (this file → this selection) puts identity where the eye lands and
          makes the fixed half a stable header rather than a drifting footer.
          Nothing else changes: same sections, same verbs, same invariance. */}
      <>
          {/* File (ADR-458 D3) — the artifact-as-file verbs, one settings home
              (Notion's page ⋯ = typography + file verbs; both live HERE now). */}
          <div className={SECTION}>
            <p className={HEADING}>File</p>
            <div className="flex flex-wrap gap-1">
              <button type="button" className={askBtn} onClick={fileVerbs.copyLink}>
                Copy link
              </button>
              <button type="button" className={askBtn} onClick={fileVerbs.duplicate}>
                Duplicate
              </button>
              <button type="button" className={askBtn} onClick={fileVerbs.rename}>
                Rename…
              </button>
              <button type="button" className={askBtn} onClick={fileVerbs.move}>
                Move…
              </button>
              <button
                type="button"
                className={`${askBtn} hover:border-red-300 hover:text-red-600`}
                onClick={fileVerbs.trash}
                title="Move this artifact to Trash (revertible from Files)"
              >
                <Trash2 className="h-3 w-3" /> Trash
              </button>
            </div>
          </div>
          {/* Share (ADR-437 D4 wedge / ADR-465 — the membership act, distinct
              from Copy link's in-app member deep-link). A share link makes the
              recipient a member of this workspace on accept. */}
          <div className={SECTION}>
            <p className={HEADING}>Share</p>
            <button
              type="button"
              className={askBtn}
              onClick={runShare}
              disabled={sharing}
              title="Create a link that lets someone open this artifact and join your workspace"
            >
              {sharing ? 'Creating link…' : shareState === 'copied' ? 'Link copied ✓' : 'Share…'}
            </button>
            <p className="text-[10px] leading-snug text-muted-foreground">
              {shareState === 'error'
                ? 'Could not create the share link. Try again.'
                : shareState === 'copied'
                  ? 'Anyone with the link can open this and join your workspace with full access. Manage or revoke shares from Files.'
                  : 'Creates a link. Whoever opens it joins your workspace with full access — narrow it later.'}
            </p>
          </div>
          {/* Export (ADR-466 D6) — the boundary projections. Print/PDF is the
              browser's print over the resolved projection (no render engine,
              ADR-417); the AI reference is the interop-face handle (recall/
              trace via the yarnnn connector) — the third way out, beside the
              member deep-link (Copy link) and the membership link (Share). */}
          <div className={SECTION}>
            <p className={HEADING}>Export</p>
            <div className="flex flex-wrap gap-1">
              {exportVerbs.exportPng && (
                <button
                  type="button"
                  className={askBtn}
                  onClick={runExportPng}
                  disabled={pngState === 'working'}
                  title="Rasterize this stage and download it as a PNG"
                >
                  {pngState === 'working'
                    ? 'Rendering…'
                    : pngState === 'error'
                      ? 'Export failed — retry'
                      : 'Download PNG'}
                </button>
              )}
              <button
                type="button"
                className={askBtn}
                onClick={exportVerbs.print}
                title="Open the print dialog over the rendered artifact — save as PDF from there"
              >
                Print / PDF…
              </button>
              <button
                type="button"
                className={askBtn}
                onClick={runCopyAiRef}
                title="Copy a reference any connected AI can use to recall this artifact via the yarnnn connector"
              >
                {aiRefState === 'copied' ? 'Reference copied ✓' : 'Copy AI reference'}
              </button>
            </div>
            <p className="text-[10px] leading-snug text-muted-foreground">
              {exportVerbs.exportPng
                ? 'The PNG is a flat projection — the composition stays the source (trace walks its layers). A deck prints one slide per page.'
                : 'A deck prints one slide per page. Markdown export arrives with the interchange wave (ADR-456 W4).'}
            </p>
          </div>
      </>
      {/* ── DOCUMENT scope ─────────────────────────────────────────────── */}
      {scope === 'document' && (
        <>
          <div className={SECTION}>
            <p className={HEADING}>Artifact</p>
            <p className="text-xs text-muted-foreground">
              {vocabulary?.layouts.find((l) => l.slug === layout)?.label ?? layout} — select a{' '}
              {pageNoun} or a block on the canvas to shape it here.
            </p>
          </div>
          {docTokens.length > 0 && (
            <div className={SECTION}>
              {docTokens.map((t) =>
                t.key === 'font' ? (
                  <FontControl
                    key={t.key}
                    token={t}
                    current={root?.getAttribute(`data-${t.key}`) ?? null}
                    onSet={(v) => onSetToken('document', t.key, v)}
                  />
                ) : (
                  <TokenControl
                    key={t.key}
                    token={t}
                    current={root?.getAttribute(`data-${t.key}`) ?? null}
                    onSet={(v) => onSetToken('document', t.key, v)}
                  />
                ),
              )}
              {skinRef && (
                <p className="text-[10px] text-muted-foreground">
                  A design system is applied — its styles may override these.
                </p>
              )}
            </div>
          )}
          <div className={SECTION}>
            <p className={HEADING}>Design system</p>
            {designSystems.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No design system yet. Import your brand&apos;s export — tokens, styles, fonts —
                and every artifact can wear it.
              </p>
            ) : (
              <div className="space-y-1">
                {designSystems.map((ds) => {
                  const active = skinRef === ds.manifest_path;
                  return (
                    <div
                      key={ds.manifest_path}
                      className="flex items-center justify-between gap-2 rounded-md border border-border px-2 py-1.5"
                    >
                      <span className="min-w-0">
                        <span className="flex items-center gap-1 truncate text-xs">
                          <Palette className="h-3 w-3 shrink-0 text-muted-foreground" />
                          {ds.name}
                          {active && <Check className="h-3 w-3 shrink-0 text-emerald-600" />}
                        </span>
                        <span className="block truncate text-[10px] text-muted-foreground">
                          {ds.manifest_path.replace(/^\/workspace\//, '')}
                        </span>
                      </span>
                      {active ? (
                        <button type="button" className={askBtn} onClick={onRemoveDesignSystem}>
                          Remove
                        </button>
                      ) : (
                        <button
                          type="button"
                          className={askBtn}
                          disabled={applying != null}
                          onClick={() => void applyDs(ds.manifest_path)}
                        >
                          {applying === ds.manifest_path ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            'Apply'
                          )}
                        </button>
                      )}
                    </div>
                  );
                })}
                {applyError && <p className="text-[10px] text-red-500">{applyError}</p>}
              </div>
            )}
            {/* The import (ADR-462 D14). A .zip because that is what a design
                system IS on the way over: every export ships a FOLDER, and a
                folder reaches a browser as an archive. One file, one act — the
                flatten, the manifest, and the binary lane are the server's. */}
            <input
              ref={importRef}
              type="file"
              accept=".zip,application/zip"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void runImport(f);
                e.target.value = '';
              }}
            />
            <button
              type="button"
              disabled={importing}
              onClick={() => importRef.current?.click()}
              className={`${askBtn} mt-1.5 w-full justify-center`}
            >
              {importing ? (
                <span className="flex items-center gap-1.5">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Importing…
                </span>
              ) : designSystems.length ? (
                'Import another…'
              ) : (
                'Import a design system…'
              )}
            </button>
            {importError && <p className="mt-1 text-[10px] text-red-500">{importError}</p>}
            {importReceipt && (
              // The receipt, warnings included. An import that half-lands
              // SILENTLY is the failure this whole arc exists to prevent — so
              // what the flatten could not resolve is shown, not swallowed.
              <div className="mt-1.5 space-y-1 rounded-md border border-border bg-muted/20 p-2">
                <p className="text-[11px] font-medium">
                  {importReceipt.name} — {importReceipt.written.length} files
                </p>
                <p className="text-[10px] text-muted-foreground">
                  {importReceipt.sources.length} stylesheets flattened
                  {importReceipt.skipped.length
                    ? ` · ${importReceipt.skipped.length} vendor files skipped`
                    : ''}
                </p>
                {importReceipt.warnings.map((w) => (
                  <p key={w} className="text-[10px] text-amber-700 dark:text-amber-500">
                    {w}
                  </p>
                ))}
              </div>
            )}
          </div>
          {/* Theme (ADR-456 W3) — the applied skin's custom properties, read
              from the artifact's marked element. The theme's FILES are the
              source of truth: change a value through the chat, then Apply
              again here to pick it up (the mechanical var-editor is a named
              follow-on pending the file-edit permission surface). */}
          {skinRef && skinVars.length > 0 && (
            <div className={SECTION}>
              <p className={HEADING}>Theme</p>
              <div className="space-y-1">
                {skinVars.map((v) => (
                  <div key={v.name} className="flex items-center gap-2">
                    {/^(#|rgb|hsl)/i.test(v.value) ? (
                      <span
                        className="h-3.5 w-3.5 shrink-0 rounded-sm border border-border"
                        style={{ background: v.value }}
                      />
                    ) : (
                      <span className="h-3.5 w-3.5 shrink-0" />
                    )}
                    <code className="text-[10px] text-muted-foreground">--{v.name}</code>
                    <span className="ml-auto truncate text-[10px]">{v.value}</span>
                  </div>
                ))}
              </div>
              <p className="text-[10px] text-muted-foreground">
                The theme lives in its files — ask the chat to change a value,
                then Apply again to pick it up.
              </p>
            </div>
          )}
        </>
      )}

      {/* ── PAGE scope ─────────────────────────────────────────────────── */}
      {scope === 'page' && (
        <>
          <div className={SECTION}>
            <p className={HEADING}>
              {pageNoun} {selection?.slideIndex != null ? selection.slideIndex + 1 : ''}
            </p>
            <VerbRow noun={pageNoun} onVerb={onPageVerb} />
          </div>
          {applicable.length > 0 && (
            <div className={SECTION}>
              {applicable.map((t) => (
                <TokenControl
                  key={t.key}
                  token={t}
                  current={selectedEl?.getAttribute(`data-${t.key}`) ?? null}
                  onSet={(v) => onSetToken('page', t.key, v)}
                />
              ))}
            </div>
          )}
          {/* Background (ADR-456 W3) — a CITED image on the page element; the
              scrim/focus tokens light up above once one is set. */}
          <div className={SECTION}>
            <p className={HEADING}>Background</p>
            {pageBgRef ? (
              <div className="flex items-center justify-between gap-2">
                <span className="min-w-0 truncate text-xs">{baseName(pageBgRef)}</span>
                <button type="button" className={askBtn} onClick={onRemovePageBackground}>
                  Remove
                </button>
              </div>
            ) : bgPicking ? (
              bgImages == null ? (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading images…
                </div>
              ) : bgImages.length === 0 ? (
                <p className="text-xs text-muted-foreground">
                  No images in the workspace yet — drop one into Files first.
                </p>
              ) : (
                <div className="max-h-40 space-y-1 overflow-y-auto">
                  {bgImages.map((img) => (
                    <button
                      key={img.path}
                      type="button"
                      onClick={() => {
                        setBgPicking(false);
                        onSetPageBackground(img.path);
                      }}
                      className="flex w-full flex-col rounded px-2 py-1 text-left hover:bg-muted/40"
                    >
                      <span className="truncate text-xs">{baseName(img.path)}</span>
                      <span className="truncate text-[10px] text-muted-foreground">
                        {img.path.replace(/^\/workspace\//, '')}
                      </span>
                    </button>
                  ))}
                </div>
              )
            ) : (
              <button type="button" className={askBtn} onClick={() => setBgPicking(true)}>
                Set background…
              </button>
            )}
          </div>
          {/* (The Re-arrange thumbnail gallery left this panel 2026-07-21 —
              it duplicated the toolbar's Re-arrange gallery in full, and two
              mounts of the same act is exactly the redundancy DP29 names.
              The toolbar button is the one home.) */}
        </>
      )}

      {/* ── SLOT scope ─────────────────────────────────────────────────── */}
      {scope === 'slot' && selection?.slot && (
        <div className={SECTION}>
          {/* A slot has a NAME (which region) and a ROLE (what it accepts),
              and for the heading slots those two words are identical — so this
              rendered the stutter "Slot · heading (heading)". Show the role
              only when it says something the name does not. */}
          <p className={HEADING}>
            Slot · {selection.slot}
            {slotRole && slotRole !== selection.slot ? ` (${slotRole})` : ''}
          </p>
          {slotRole === 'media' ? (
            slotImages == null ? (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading images…
              </div>
            ) : slotImages.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No images in the workspace yet — drop one into Files, or ask the chat for an SVG.
              </p>
            ) : (
              <div className="space-y-1">
                {slotImages.map((img) => (
                  <button
                    key={img.path}
                    type="button"
                    onClick={() =>
                      onInsertImageInSlot(
                        img.path,
                        selection.slot!,
                        selection.slideIndex,
                        selection.pageIndex,
                      )
                    }
                    className="flex w-full flex-col rounded px-2 py-1 text-left hover:bg-muted/40"
                  >
                    <span className="truncate text-xs">{baseName(img.path)}</span>
                    <span className="truncate text-[10px] text-muted-foreground">
                      {img.path.replace(/^\/workspace\//, '')}
                    </span>
                  </button>
                ))}
              </div>
            )
          ) : (
            <button
              type="button"
              className={askBtn}
              onClick={() =>
                onAddTextInSlot(selection.slot!, selection.slideIndex, selection.pageIndex)
              }
            >
              + Add text here
            </button>
          )}
        </div>
      )}

      {/* ── BLOCK scope ────────────────────────────────────────────────── */}
      {scope === 'block' && (
        <>
          <div className={SECTION}>
            {/* The id is an IDENTIFIER, not a heading level — but this row is
                uppercased, so `heading · t1` rendered as "HEADING · T1", which
                reads exactly like Word/PowerPoint's "Heading 1". Two different
                concepts, one string, and the block model has no h-levels at
                all (h1/h2/kicker are all data-block="heading"; the TAG carries
                the level). Keep the id lowercase and mark it as an id so the
                misreading has no surface to land on. */}
            <p className={HEADING}>
              {selection?.blockKind ?? 'block'}
              {selection?.blockId ? (
                <span className="normal-case text-muted-foreground/70">
                  {' '}· id {selection.blockId}
                </span>
              ) : null}
            </p>
            <div className="flex flex-wrap gap-1">
              <button type="button" className={askBtn} onClick={onAskAboutSelection}>
                <MessageSquare className="h-3 w-3" /> Ask about this
              </button>
            </div>
            <VerbRow noun="block" onVerb={onBlockVerb} />
            <p className="text-[10px] text-muted-foreground">
              Double-click the block on the canvas to edit its text in place.
            </p>
          </div>
          {/* Turn into (ADR-456 W2) — text kinds only; the id and tokens
              survive the conversion (a block with a citation refuses). */}
          {selection?.blockKind && TURN_INTO_KINDS.includes(selection.blockKind) && (
            <div className={SECTION}>
              <p className={HEADING}>Turn into</p>
              <div className="flex flex-wrap gap-1">
                {TURN_INTO_KINDS.filter((k) => k !== selection.blockKind).map((k) => {
                  const b = vocabulary?.blocks.find((vb) => vb.kind === k);
                  if (!b) return null;
                  return (
                    <button
                      key={k}
                      type="button"
                      className={askBtn}
                      onClick={() => onTurnInto(b.kind, b.label, b.fragment)}
                    >
                      {b.label}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
          {applicable.length > 0 && (
            <div className={SECTION}>
              {applicable.map((t) => (
                <TokenControl
                  key={t.key}
                  token={t}
                  current={selectedEl?.getAttribute(`data-${t.key}`) ?? null}
                  onSet={(v) => onSetToken('block', t.key, v)}
                />
              ))}
            </div>
          )}
          {/* ADR-485 follow-on — the SIZE read-back. A drag on the canvas
              handle authors w/h; this shows the value it wrote (the tab had no
              numeric confirmation anywhere before) and offers reset-to-Auto,
              the same absence-default a token gives. Drag to size, read here.
              Only rendered where a measure applies (a framed or media block). */}
          {sizeMeasures.length > 0 && (
            <div className={SECTION}>
              <p className={HEADING}>Size</p>
              {sizeMeasures.map((m) => {
                const v = measureValue(m);
                return (
                  <div key={m.key} className="flex items-center justify-between gap-2">
                    <span className="text-xs text-muted-foreground" title={m.description}>
                      {m.label}
                    </span>
                    {v == null ? (
                      <span className="text-xs text-muted-foreground">Auto</span>
                    ) : (
                      <span className="flex items-center gap-1.5">
                        <span className="text-xs tabular-nums text-foreground">
                          {v}
                          {m.unit}
                        </span>
                        <button
                          type="button"
                          className={askBtn}
                          onClick={() => onClearMeasure(m.key as 'w' | 'h')}
                          title={`Reset ${m.label.toLowerCase()} to Auto`}
                        >
                          Auto
                        </button>
                      </span>
                    )}
                  </div>
                );
              })}
              <p className="text-[10px] leading-snug text-muted-foreground">
                Drag the block&apos;s corner on the canvas to size it; the value
                shows here.
              </p>
            </div>
          )}
          {/* ADR-466 D2 — the positioned state's escape hatch. A block the
              member dragged to a point (x/y measures) sits outside the page's
              flow; this returns it (re-arranging the page also does). */}
          {/* ADR-485 D4: the kernel rule is `.slide [data-block][data-x][data-y]`
              — BOTH are required for the positioned state. Testing `data-x`
              alone offered "Return to flow" on a block that was still in flow
              (a lane can write one attribute without the other, since the
              posture teaches them as prose), and clicking it landed a revision
              that changed nothing visible. Read the state the kernel reads. */}
          {selectedEl?.hasAttribute('data-x') && selectedEl?.hasAttribute('data-y') && (
            <div className={SECTION}>
              <p className={HEADING}>Position</p>
              <button type="button" className={askBtn} onClick={onReturnToFlow}>
                Return to flow
              </button>
              <p className="text-[10px] text-muted-foreground">
                Dragged to a point on this slide — it no longer follows the
                slide&apos;s layout. Re-arranging the slide also returns it.
              </p>
            </div>
          )}
        </>
      )}

    </div>
  );
}
