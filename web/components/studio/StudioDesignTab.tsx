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
import { ArrangementThumb } from './ArrangementThumb';
import type { StudioSelection, StudioToken, StudioVocabulary } from './StudioToolbar';

export type StructVerb = 'duplicate' | 'up' | 'down' | 'delete';

const PAGE_SEL = 'section.slide, [data-arrange]';

/** The TEXT kinds a block can turn into (ADR-456 W2) — text-shaped only:
 *  structured/cited kinds (table/metrics/chart/figure/gallery) and headings
 *  (they anchor pages) are not conversion targets. */
const TURN_INTO_KINDS = ['prose', 'callout', 'quote', 'checklist', 'toggle'];

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
  /** EXECUTE: re-lay the SELECTED page to this arrangement. */
  onApplyArrangement: (fragment: string, label: string) => void;
  onBlockVerb: (verb: StructVerb) => void;
  onPageVerb: (verb: StructVerb) => void;
  /** EXECUTE: turn the selected block into another TEXT kind (ADR-456 W2 —
   *  convertBlock: id + tokens survive, text units rebuilt into the target). */
  onTurnInto: (kind: string, label: string, fragment: string) => void;
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
  onApplyArrangement,
  onBlockVerb,
  onPageVerb,
  onTurnInto,
  onAskAboutSelection,
  onApplyDesignSystem,
  onRemoveDesignSystem,
  onImported,
  onAddTextInSlot,
  onInsertImageInSlot,
  onSetPageBackground,
  onRemovePageBackground,
  fileVerbs,
}: StudioDesignTabProps) {
  const doc = useMemo(() => {
    if (typeof window === 'undefined' || !html) return null;
    return new DOMParser().parseFromString(html, 'text/html');
  }, [html]);

  const scope: 'document' | 'block' | 'slot' | 'page' = !selection
    ? 'document'
    : selection.blockId
      ? 'block'
      : selection.slot
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
  useEffect(() => {
    setBgPicking(false);
  }, [selection]);
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
          {arrangements.length > 0 && (
            <div className={SECTION}>
              <p className={HEADING}>Re-arrange</p>
              <div className="grid grid-cols-2 gap-1.5">
                {arrangements.map((a) => {
                  const current = selectedEl?.getAttribute('data-arrange') === a.slug;
                  return (
                    <button
                      key={a.slug}
                      type="button"
                      title={a.description}
                      onClick={() => onApplyArrangement(a.fragment, a.label)}
                      className={`flex flex-col gap-1 rounded-md border p-1.5 text-left hover:bg-muted/20 ${
                        current ? 'border-indigo-400' : 'border-transparent hover:border-border'
                      }`}
                    >
                      <ArrangementThumb slots={a.slots} fragment={a.fragment} />
                      <span className="truncate text-[11px]">{a.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}

      {/* ── SLOT scope ─────────────────────────────────────────────────── */}
      {scope === 'slot' && selection?.slot && (
        <div className={SECTION}>
          <p className={HEADING}>
            Slot · {selection.slot}
            {slotRole ? ` (${slotRole})` : ''}
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
            <p className={HEADING}>
              {selection?.blockKind ?? 'block'}
              {selection?.blockId ? ` · ${selection.blockId}` : ''}
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
        </>
      )}
    </div>
  );
}
