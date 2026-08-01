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
 *  - a slot → SLOT scope: name + role, plus the MEDIA slot's image picker —
 *    which is not a second insert route but the terminal step of the canvas
 *    "+ Add" on a media slot (onAddHere routes here by role). A flow slot's
 *    duplicate add-text button was deleted by ADR-505 D5.
 *  - a block → BLOCK scope: SHAPING only — Turn into + block tokens
 *    (align/tone; media blocks add height/fit) + measures. The verb row
 *    (ask / duplicate / move / delete) left the pane 2026-07-24: the
 *    right-click menu + block keyboard are the entrances, and the
 *    ask-about act relocated into the menu's AI group.
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
  ChevronDown,
  Copy,
  FolderInput,
  Link2,
  Loader2,
  MoreHorizontal,
  Palette,
  Pencil,
  Trash2,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import {
  type StudioMeasure,
  type StudioSelection,
  type StudioToken,
  type StudioVocabulary,
} from './StudioToolbar';
import { studioShapeStyle } from './studioShapes';
// ADR-487 D9: the Design tab reads the skin only to PAINT the controls
// (skinVarMap + resolveSkinVar). The var-LIST parse belongs to the manage panel
// alone now — the system-as-object register. Importing it here again would
// re-create the deleted artifact-side list, so the ADR-455 gate forbids it.
import { resolveSkinVar, skinVarMap } from './skinVars';

export type StructVerb = 'duplicate' | 'up' | 'down' | 'delete';

const PAGE_SEL = 'section.slide, [data-arrange]';

/** The block kinds a block can be turned INTO (ADR-456 W2) — text kinds only,
 *  because the conversion rebuilds text units and a citation must never
 *  flatten. Exported so the right-click submenu (ADR-479 D5) offers exactly the
 *  legal set: one list, two mounts. A copy would drift, and a menu offering an
 *  illegal conversion is a promise the op refuses to keep.
 *  ADR-487 D1: `heading` joins — the old exclusion ("headings anchor pages")
 *  was about the re-arrange sweep, which stays; it never needed to make
 *  headings unconvertible. */
export const TURN_INTO_KINDS = ['prose', 'heading', 'callout', 'quote', 'checklist', 'toggle'];

/** The heading rungs (ADR-487 D1) — the tag carries the level; the kernel
 *  sizes each from the type scale, so the rungs are design-system-fed. */
export const HEADING_LEVELS: Array<{ tag: string; label: string }> = [
  { tag: 'h1', label: 'Heading 1' },
  { tag: 'h2', label: 'Heading 2' },
  { tag: 'h3', label: 'Heading 3' },
];

/** Build the Turn-into target list (ONE list, two mounts — the Design tab and
 *  the right-click submenu). `heading` expands to its three level targets
 *  (same kind, the tag carries the rung). `currentTag` (when the mount knows
 *  it) excludes the level the block already is; a mount that cannot know the
 *  tag passes null — clicking the current level is a convertBlock no-op, not
 *  a lie. */
export function turnIntoTargets(
  blocks: Array<{ kind: string; label: string; fragment: string }>,
  currentKind: string | null,
  currentTag: string | null,
): Array<{ key: string; kind: string; label: string; fragment: string }> {
  const out: Array<{ key: string; kind: string; label: string; fragment: string }> = [];
  for (const k of TURN_INTO_KINDS) {
    if (k === 'heading') {
      for (const lvl of HEADING_LEVELS) {
        if (currentKind === 'heading' && currentTag?.toLowerCase() === lvl.tag) continue;
        out.push({
          key: `heading-${lvl.tag}`,
          kind: 'heading',
          label: lvl.label,
          fragment: `<${lvl.tag} data-block="heading">…</${lvl.tag}>`,
        });
      }
      continue;
    }
    if (k === currentKind) continue;
    const b = blocks.find((vb) => vb.kind === k);
    if (b) out.push({ key: k, kind: b.kind, label: b.label, fragment: b.fragment });
  }
  return out;
}

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
  /** Page verbs only — the BLOCK verb row left this pane (2026-07-24; the
   *  right-click menu + block keyboard are the entrances). Page verbs stay:
   *  duplicate-page has no other mount (the navigator covers delete/reorder). */
  onPageVerb: (verb: StructVerb) => void;
  /** EXECUTE: turn the selected block into another TEXT kind (ADR-456 W2 —
   *  convertBlock: id + tokens survive, text units rebuilt into the target). */
  onTurnInto: (kind: string, label: string, fragment: string) => void;
  /** ADR-466 D2: clear the selected block's x/y measures — the positioned
   *  block returns to the page's flow (one revision). */
  onReturnToFlow: () => void;
  /** ADR-511 D4 — bounded container-layout properties (padding/gap/align/justify). */
  onContainerLayout: (layout: Record<string, string | null>) => void;
  /** ADR-485 follow-on: the served measures (`vocabulary.measures`) — the Design
   *  tab reads a block's CURRENT w/h back from its --y* style so a member sees
   *  the size the drag authored. Empty until the vocabulary lands. */
  measures: StudioMeasure[];
  /** ADR-485 follow-on: reset a size measure to Auto (the absence-default) — the
   *  read-back's clear affordance, since the drag is the authoring path. */
  onClearMeasure: (key: 'w' | 'h') => void;
  /** EXECUTE: apply a design system's composed skin element (resolve + write). */
  onApplyDesignSystem: (manifestPath: string) => Promise<void>;
  /** EXECUTE: remove the marked skin element. */
  onRemoveDesignSystem: () => void;
  /** ADR-487 D9: open the applied system in the MANAGE panel (the third render
   *  state, `studio.system=`) — the system-as-object register. This is the
   *  route the tab never had: block scope said "themed by the design system"
   *  and offered no way to reach it, so the member had to deselect to get back
   *  to document scope, then hunt the picker row. */
  onOpenSystem: (manifestPath: string) => void;
  /** ADR-462 D14: a design system was imported — the surface refetches the
   *  served vocabulary so the picker sees it (the payload carries kernel
   *  constants AND workspace state; only the second half goes stale). */
  onImported?: () => void;
  /** EXECUTE: role-gated slot adds (ADR-453 D5). */
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
    move: () => void;
    trash: () => void;
  };
  /** The artifact's display name (the surface's ONE derivation, ADR-483) —
   *  shown as the File card's identity line. */
  artifactName: string;
  /** Commit a rename — the surface's `commitRename`, the SAME one commit path
   *  the crumb uses. The card owns only the inline input; the write, the
   *  path-follow and the error surface all live in the parent. */
  onRenameCommit: (next: string) => void | Promise<void>;
  /* Share + export verbs left this pane (2026-07-24) — they are header acts
   * now (StudioShareExport, right of zoom). */
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

/** The kernel's own face stacks (ADR-455) — the fallbacks a SKIN-LESS artifact
 *  paints with, and the fallback each `--font-*` slot resolves through. */
const FONT_STACKS: Record<string, string> = {
  serif: "Georgia, 'Times New Roman', serif",
  sans: "system-ui, -apple-system, 'Segoe UI', sans-serif",
  mono: "ui-monospace, 'SF Mono', Menlo, monospace",
};

// ── ADR-487 D3 v2 — the visual style select (the Figma presentation) ────────
// One dropdown shape, two consumers (Typography + Color): the trigger shows
// the CURRENT style as it resolves under the applied system; each option row
// is rendered in what IT resolves to. The values stay the closed kernel
// vocabulary — only the presentation speaks the system.
function StyleSelect({
  label,
  description,
  current,
  options,
}: {
  label: string;
  description?: string;
  current: { preview: React.ReactNode; label: string; detail?: string };
  options: Array<{
    key: string;
    preview: React.ReactNode;
    label: string;
    detail?: string;
    active?: boolean;
    onPick: () => void;
  }>;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);
  return (
    <div ref={ref} className="relative">
      <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        title={description}
        className="flex w-full items-center gap-2 rounded-md border border-border px-2 py-1.5 text-left text-xs transition-colors hover:bg-muted/40"
      >
        {current.preview}
        <span className="min-w-0 truncate">{current.label}</span>
        {current.detail && (
          <span className="shrink-0 text-[10px] text-muted-foreground">· {current.detail}</span>
        )}
        <ChevronDown className="ml-auto h-3 w-3 shrink-0 text-muted-foreground/60" />
      </button>
      {open && (
        <div className="absolute left-0 right-0 top-full z-20 mt-1 max-h-56 overflow-y-auto rounded-md border border-border bg-popover py-1 shadow-md">
          {options.map((o) => (
            <button
              key={o.key}
              type="button"
              onClick={() => {
                setOpen(false);
                o.onPick();
              }}
              className={`flex w-full items-center gap-2 px-2 py-1.5 text-left text-xs hover:bg-accent ${
                o.active ? 'bg-muted/40' : ''
              }`}
            >
              {o.preview}
              <span className="min-w-0 truncate">{o.label}</span>
              {o.detail && (
                <span className="ml-auto shrink-0 text-[10px] text-muted-foreground">{o.detail}</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/** The Typography ramp rows (ADR-487 D3 v2) — the tag IS the rung. Order is
 *  the ramp's (largest first), Text closing it, the Figma reading. */
const TEXT_STYLE_ROWS: Array<{ key: string; label: string }> = [
  { key: 'h1', label: 'Heading 1' },
  { key: 'h2', label: 'Heading 2' },
  { key: 'h3', label: 'Heading 3' },
  { key: 'p', label: 'Text' },
];

/** The `font` token (ADR-455 + D4 face slots) as a visual select — ADR-487 D9.
 *
 *  It was the last chip-row left in the panel: document scope rendered "Ag"
 *  chips while block scope rendered the ramp as a StyleSelect, so ONE word
 *  ("Typography") had two presentations ~130 lines apart in one scroll. Same
 *  shape now — each option previews in the face it RESOLVES to under the
 *  applied system (--font-serif/sans/mono), kernel stacks unskinned. The value
 *  stays the closed three-category vocabulary; only the presentation speaks the
 *  system. */
function FaceTokenSelect({
  token,
  current,
  stacks,
  onSet,
}: {
  token: StudioToken;
  current: string | null;
  stacks: Record<string, string>;
  onSet: (value: string | null) => void;
}) {
  const ag = (stack?: string) => (
    <span
      className="w-6 shrink-0 text-center text-base leading-none"
      style={stack ? { fontFamily: stack } : undefined}
    >
      Ag
    </span>
  );
  const cur = token.values.find((v) => v.value === current) ?? null;
  return (
    <StyleSelect
      label={token.label}
      description={token.description}
      current={{
        preview: ag(current ? stacks[current] : undefined),
        label: cur?.label ?? 'Auto',
      }}
      options={[
        {
          key: '__auto',
          preview: ag(undefined),
          label: 'Auto',
          active: current == null,
          onPick: () => onSet(null),
        },
        ...token.values.map((v) => ({
          key: v.value,
          preview: ag(stacks[v.value]),
          label: v.label,
          active: current === v.value,
          onPick: () => onSet(current === v.value ? null : v.value),
        })),
      ]}
    />
  );
}

/** A palette-backed token as a LAID-OUT SWATCH ROW rather than a dropdown —
 *  the colour half of the shaping pair, sitting directly under Typography.
 *
 *  Why a row and not the select: a colour choice is the one control whose whole
 *  content is visible at a glance, so hiding N swatches behind a trigger costs a
 *  click to see what the select could have shown outright. Typography cannot do
 *  this (nine rungs, each needing its name and size to be legible), which is why
 *  the two controls differ in shape while sharing a scope — the shape follows
 *  what the choice IS, the same reasoning ADR-487 D3 v2 used to make Typography
 *  a preview-select instead of a chip row.
 *
 *  ADR-487 D9 SAFETY — this is the APPLIED register, so it may only show slots
 *  that are a CHOICE. It renders `token.values` (the served, member-actable
 *  values) and nothing else: never the kernel vocabulary, never --paper /
 *  --ink-06 / --deck-stage, which D9 named member-invisible identity and deleted
 *  from the artifact side precisely because showing them is an anti-affordance.
 *  Every swatch here is a value the member can pick; Auto is the absence.
 *
 *  The values are the applied system's RESOLVED colours (`swatches`), so the row
 *  answers "what will this do when I pick it?" in the resolved value — D3 v2's
 *  rule, which is why nothing here is a raw hex the member must decode. */
function ColorTokenSwatches({
  token,
  current,
  swatches,
  onSet,
}: {
  token: StudioToken;
  current: string | null;
  swatches: Record<string, string>;
  onSet: (value: string | null) => void;
}) {
  const swatch = (color: string | null, active: boolean, label: string, onClick: () => void) => (
    <button
      key={label}
      type="button"
      onClick={onClick}
      title={label}
      aria-label={label}
      aria-pressed={active}
      className={`flex h-7 w-7 items-center justify-center rounded-full border transition ${
        active
          ? 'border-foreground ring-2 ring-foreground/20'
          : 'border-black/10 hover:border-foreground/40'
      }`}
    >
      <span
        className="h-4 w-4 rounded-full"
        style={
          color
            ? { background: color }
            : {
                // Auto = the absence of a choice, drawn as the slashed dot the
                // select already uses, so one idea keeps one glyph.
                backgroundImage:
                  'linear-gradient(135deg, transparent 45%, #bbb 45%, #bbb 55%, transparent 55%)',
              }
        }
      />
    </button>
  );
  const cur = token.values.find((v) => v.value === current) ?? null;
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <p className={HEADING}>{token.label}</p>
        {/* The resolved choice is NAMED, not only shown: a swatch alone cannot
            say "accent", and the role is the thing the member is choosing
            (ADR-487 D3 — every control names a role, never a raw value). */}
        <span className="text-[10px] text-muted-foreground">{cur?.label ?? 'Auto'}</span>
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
        {swatch(null, current == null, 'Auto', () => onSet(null))}
        {token.values.map((v) =>
          swatch(swatches[v.value] ?? null, current === v.value, v.label, () =>
            onSet(current === v.value ? null : v.value),
          ),
        )}
      </div>
      {token.description && (
        <p className="mt-1 text-[10px] leading-snug text-muted-foreground">{token.description}</p>
      )}
    </div>
  );
}

/** The applied-system cue (ADR-487 D9) — the one line the shaping scopes carry
 *  about the system. It NAMES the system (an anonymous "a design system is
 *  applied" told the member nothing they could act on) and is the ROUTE to the
 *  manage panel, where the system is legible as an object. One component, two
 *  mounts (document + block), so the two scopes can never drift into two
 *  different sentences about the same fact. */
function AppliedSystemCue({
  name,
  manifestPath,
  onOpen,
  note,
}: {
  name: string;
  manifestPath: string;
  onOpen: (manifestPath: string) => void;
  /** Scope-specific clause — what the system is doing HERE. */
  note: string;
}) {
  return (
    <p className="text-[10px] leading-snug text-muted-foreground">
      <button
        type="button"
        onClick={() => onOpen(manifestPath)}
        title="Open this design system — its palette, type, files and what else wears it"
        className="inline-flex items-center gap-1 rounded font-medium text-foreground/80 underline decoration-dotted underline-offset-2 transition-colors hover:text-foreground"
      >
        <Palette className="h-3 w-3 shrink-0" />
        {name}
      </button>{' '}
      {note}
    </p>
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
  onPageVerb,
  onTurnInto,
  onReturnToFlow,
  onContainerLayout,
  measures,
  onClearMeasure,
  onApplyDesignSystem,
  onRemoveDesignSystem,
  onOpenSystem,
  onImported,
  onInsertImageInSlot,
  onSetPageBackground,
  onRemovePageBackground,
  fileVerbs,
  artifactName,
  onRenameCommit,
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
  // ADR-511 D3 — the structural grain: blockId + blockKind is a vocabulary
  // BLOCK; blockId with no kind is a structural CONTAINER (a column/columns/
  // slot-div carrying identity but no vocabulary). The ADR-453 slot scope and
  // its registry region-gate are DELETED — a slot-div now selects as a
  // container with real affordances (layout properties, the id-addressed
  // verbs), so there is no grain left to hide.
  const scope: 'document' | 'block' | 'container' | 'page' = !selection
    ? 'document'
    : selection.blockId && selection.blockKind
      ? 'block'
      : selection.blockId
        ? 'container'
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
  /** The layout's composition mode, read from the SERVED kernel row (ADR-466).
   *
   *  This pane used to spell the flow/paged split out longhand, testing the two
   *  flow slugs by name — which is exactly the flow set, re-enumerated. That
   *  made the kernel's claim "the FE never learns another slug" (studio.py)
   *  false here: a new flow layout registering `mode: "flow"` would get correct
   *  chrome everywhere else and SILENTLY lose its `document-flow` tokens in
   *  this panel. Derive it; never re-enumerate it.
   *
   *  Undefined until the vocabulary lands — the `?? 'flow'` default matches the
   *  surface's own `layoutMode` (show the flowing, less-chrome reading first). */
  const mode = vocabulary?.layouts.find((l) => l.slug === layout)?.mode ?? 'flow';
  const pageNoun = mode === 'paged' && layout === 'deck' ? 'slide' : 'section';

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
      // ADR-487 D2: kind-gated grain (the `media` precedent) — the callout's
      // semantic register applies to callouts alone.
      const isCallout = selection?.blockKind === 'callout';
      return tokens.filter(
        (t) =>
          t.applies.includes('block') ||
          (isMedia && t.applies.includes('media')) ||
          (isCallout && t.applies.includes('block-callout')),
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
          // document-flow = the FLOW layouts: a deck is a fixed stage and a
          // page is full-width bands — measure applies to neither (W3). Read
          // from the served `mode`, not a slug list (see `mode` above).
          (mode === 'flow' && t.applies.includes('document-flow')) ||
          // document-deck stays slug-keyed on purpose: it is a DECK affordance
          // (slide numbers), not a paged one — `page` is paged too and has no
          // slides to number.
          (layout === 'deck' && t.applies.includes('document-deck')),
        // NOTE: the `canvas` branch (ADR-471 D-c's aspect token) is DELETED —
        // ADR-472 moved the canvas to the IMAGES app's `image` layout, so no
        // served layout is `canvas` and no served token declares
        // `document-canvas`. Verified against the registry, not assumed
        // (ADR-482 §9 recorded it as owed).
      ),
    [tokens, layout, mode],
  );
  const skinRef = doc?.querySelector('head style[data-skin]')?.getAttribute('data-ref') ?? null;
  const designSystems = vocabulary?.design_systems ?? [];
  /** The applied system as an OBJECT (ADR-487 D9) — the marked element carries
   *  only its manifest path, so the served list supplies the name. Null when
   *  nothing is applied, or when the ref names a system the vocabulary doesn't
   *  know (a deleted folder): the cue names what it can prove, never a path
   *  dressed as a name. */
  const appliedSystem = useMemo(
    () => (skinRef ? (designSystems.find((d) => d.manifest_path === skinRef) ?? null) : null),
    [skinRef, designSystems],
  );
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

  // ADR-487 D9: INSIDE AN ARTIFACT THE SYSTEM IS WORN, NEVER LISTED.
  //
  // This used to also parse a `--var: value` list for a read-only Theme panel
  // (ADR-456 W3). It is DELETED, and deleted rather than restyled, for three
  // reasons measured against the shipped controls:
  //
  //  1. It was redundant where it mattered. The painted controls already carry
  //     every slot a member can ACT on — accent/muted/ink (tone), ink-10/fresh/
  //     warn (variant), font-serif/sans/mono (faces), the nine --text-* rungs
  //     (via tagFontSize). What the list uniquely added was --paper, --ink-06,
  //     --deck-stage, --danger and the four --radius-* — precisely the slots
  //     ADR-487's audit classified as member-INVISIBLE (identity, not a
  //     per-artifact choice). It showed the member exactly what they cannot
  //     touch, in the one grammar §3 forbids, under controls that already
  //     showed everything they can.
  //  2. It read the wrong source. This parse reads THIS ARTIFACT'S copy of the
  //     skin; the system itself is the resolved skin_element (maps bridge
  //     included) the manage panel reads. After a re-import the two diverge and
  //     this one silently showed values the system no longer has. Restyling
  //     would have made a stale reading prettier and more trustworthy.
  //  3. The register is the manage panel's. Inspecting a system AS AN OBJECT
  //     (what it defines, what wears it, what a re-import changed) is a
  //     different act by a different reader — and that panel is already the
  //     named home of the deferred token editor.
  //
  // The map below stays: it is what PAINTS the controls (the applied register).
  const skinCss = useMemo(
    () => doc?.querySelector('head style[data-skin]')?.textContent ?? '',
    [doc],
  );
  // ADR-487 D3 — the full definition map: the controls paint themselves with
  // the applied system's RESOLVED values (kernel literals when unskinned).
  // Derived from the artifact's own marked element at render, never stored.
  const skinMap = useMemo(() => skinVarMap(skinCss), [skinCss]);
  const resolvedFontStacks = useMemo(
    () => ({
      serif: resolveSkinVar(skinMap, 'font-serif', FONT_STACKS.serif),
      sans: resolveSkinVar(skinMap, 'font-sans', FONT_STACKS.sans),
      mono: resolveSkinVar(skinMap, 'font-mono', FONT_STACKS.mono),
    }),
    [skinMap],
  );
  // Value→resolved-color per palette-backed token (tone; the D2 variant).
  const tokenSwatches = useMemo<Record<string, Record<string, string>>>(
    () => ({
      tone: {
        accent: resolveSkinVar(skinMap, 'accent', '#b4540a'),
        muted: resolveSkinVar(skinMap, 'muted', '#6b6b6b'),
        inverse: resolveSkinVar(skinMap, 'ink', '#1a1a1a'),
      },
      variant: {
        note: resolveSkinVar(skinMap, 'ink-10', '#dddddd'),
        success: resolveSkinVar(skinMap, 'fresh', '#2e7d32'),
        warning: resolveSkinVar(skinMap, 'warn', '#b45309'),
      },
    }),
    [skinMap],
  );

  // The palette-backed subset, split out so BLOCK scope can lift colour up
  // beside Typography (the two shaping questions a member asks in sequence
  // belong adjacent) while every other token keeps its existing home. A token is
  // palette-backed iff resolved swatches exist for it — DERIVED, never a
  // hard-coded key list, so a new palette token joins by supplying swatches
  // rather than by editing this condition.
  const colorTokens = useMemo(
    () => (scope === 'block' ? applicable.filter((t) => !!tokenSwatches[t.key]) : []),
    [scope, applicable, tokenSwatches],
  );
  // ...and its complement, so each token renders EXACTLY ONCE. Lifting without
  // this would leave the control mounted twice in one panel — the duplicate-mount
  // defect ADR-466 P12 and ADR-505 D5 each had to delete.
  const nonColorTokens = useMemo(
    () => (scope === 'block' ? applicable.filter((t) => !tokenSwatches[t.key]) : applicable),
    [scope, applicable, tokenSwatches],
  );

  // ADR-487 D3 v2 — the Typography previews derive from the ARTIFACT'S OWN
  // styles: every layout bakes its tag sizes as `h1 { font-size: var(--text-*,
  // LIT) }`, so a textual last-match + skin resolution is truthful per layout
  // AND per skin — nothing is hand-mapped, so a layout or skin change
  // re-truths the dropdown on its own.
  const allCss = useMemo(
    () =>
      Array.from(doc?.querySelectorAll('style') ?? [])
        .map((s) => s.textContent ?? '')
        .join('\n'),
    [doc],
  );
  const resolveCssValue = useCallback(
    (raw: string) => {
      const m = raw.trim().match(/^var\(\s*--([a-z0-9-]+)\s*(?:,\s*([^)]+))?\)$/i);
      if (!m) return raw.trim();
      return skinMap.get(m[1]) ?? m[2]?.trim() ?? raw.trim();
    },
    [skinMap],
  );
  const tagFontSize = useCallback(
    (tag: string) => {
      const rx = new RegExp(`(?:^|[\\s,{}])${tag}[^{]*\\{[^}]*font-size:\\s*([^;}]+)`, 'gi');
      let last: string | null = null;
      let m;
      while ((m = rx.exec(allCss))) last = m[1];
      if (last) return resolveCssValue(last);
      return { h1: '2rem', h2: '1.3rem', h3: '1.17em', p: '1rem' }[tag] ?? '1rem';
    },
    [allCss, resolveCssValue],
  );
  const bodyFace = useMemo(() => {
    const fontToken = doc?.documentElement?.getAttribute('data-font');
    if (fontToken && fontToken in resolvedFontStacks) {
      return resolvedFontStacks[fontToken as keyof typeof resolvedFontStacks];
    }
    const rx = /(?:^|[\s,{}])body[^{]*\{[^}]*font-family:\s*([^;}]+)/gi;
    let last: string | null = null;
    let m;
    while ((m = rx.exec(allCss))) last = m[1];
    return last ? resolveCssValue(last) : FONT_STACKS.serif;
  }, [allCss, doc, resolvedFontStacks, resolveCssValue]);

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

  // Share + Export left this pane (2026-07-24) — they are header verbs now
  // (StudioShareExport, right of zoom): document-global boundary acts, not
  // shaping properties. Their transient states moved with them.

  // ── The File card (2026-07-24 re-presentation of ADR-458 D3) ────────────
  // The verb-chip row read as developer buttons; the layman grammar is the
  // Finder's: the file shows its NAME, the name IS the rename affordance
  // (double-click, edit in place), and every other verb waits behind ⋯.
  // One commit path — the input calls the parent's commitRename, the same
  // function the crumb's input calls; two entry fields, one write.
  const [nameEditing, setNameEditing] = useState(false);
  const [nameBusy, setNameBusy] = useState(false);
  const [fileMenu, setFileMenu] = useState(false);
  const fileMenuRef = useRef<HTMLDivElement>(null);
  const commitNameEdit = useCallback(
    async (value: string) => {
      setNameBusy(true);
      try {
        await onRenameCommit(value);
      } finally {
        setNameBusy(false);
        setNameEditing(false);
      }
    },
    [onRenameCommit],
  );
  useEffect(() => {
    if (!fileMenu) return;
    const close = () => setFileMenu(false);
    const onDown = (e: MouseEvent) => {
      if (fileMenuRef.current && !fileMenuRef.current.contains(e.target as Node)) close();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [fileMenu]);

  // ── Container scope: role-gated quick-add (a media region keeps the image
  // picker — the one job the old slot scope did that a plain container
  // cannot, resolved from the registry while data-slot survives Phase 2). ──
  const slotRole = useMemo(() => {
    if (scope !== 'container' || !selection?.slot) return null;
    const row = arrangements.find((a) => a.slug === selection.arrange);
    return row?.slots.find((s) => s.name === selection.slot)?.role ?? 'flow';
  }, [scope, selection, arrangements]);

  const [slotImages, setSlotImages] = useState<Array<{ path: string }> | null>(null);
  useEffect(() => {
    if (scope !== 'container' || slotRole !== 'media' || slotImages) return;
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
          The File verbs are document-global acts; scope-gating them under
          "nothing selected" hid them exactly when the member was working a
          section ("share/export … seems to have in deck … but not here").
          That mode-invariance is preserved exactly. Share + Export moved to
          the header cluster (StudioShareExport, 2026-07-24).

          ADR-482 D6: the panel is ordered by SCOPE — outermost first. This
          block was the tail, so a block selection read HEADING · T1 → WIDTH →
          ALIGN → TONE → FILE and the file's own identity sat under the
          properties of whatever happened to be clicked. Reading file-first
          (this file → this selection) puts identity where the eye lands and
          makes the fixed half a stable header rather than a drifting footer.
          Nothing else changes: same sections, same verbs, same invariance. */}
      <>
          {/* File (ADR-458 D3, re-presented 2026-07-24) — a FILE CARD, not a
              verb row: the file shows its name (the Finder grammar), the name
              is the rename affordance (double-click, edit in place — the same
              one commit path as the crumb), and the remaining verbs wait
              behind ⋯. Common to every scope and every template. */}
          <div className={SECTION}>
            <p className={HEADING}>File</p>
            <div ref={fileMenuRef} className="relative flex items-center gap-1.5">
              {(() => {
                const { icon: ShapeIcon, color } = studioShapeStyle(layout);
                return <ShapeIcon className={`h-4 w-4 shrink-0 ${color}`} aria-hidden />;
              })()}
              {nameEditing ? (
                <input
                  autoFocus
                  // SELECT, don't just focus — an armed name is only an offer
                  // if typing REPLACES it (the crumb input, ADR-470 D1).
                  onFocus={(e) => e.currentTarget.select()}
                  defaultValue={artifactName}
                  disabled={nameBusy}
                  onBlur={(e) => void commitNameEdit(e.currentTarget.value)}
                  onKeyDown={(e) => {
                    // ADR-483 — an IME composition owns Enter first (the
                    // crumb's guard, kept in lockstep).
                    if (e.nativeEvent.isComposing) return;
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      void commitNameEdit(e.currentTarget.value);
                    } else if (e.key === 'Escape') {
                      e.preventDefault();
                      setNameEditing(false);
                    }
                  }}
                  className="min-w-0 flex-1 rounded border border-indigo-400/60 bg-background px-1.5 py-0.5 text-xs font-medium outline-none disabled:opacity-50"
                  aria-label="Rename this artifact"
                />
              ) : (
                <button
                  type="button"
                  onDoubleClick={() => setNameEditing(true)}
                  title="Double-click to rename"
                  className="min-w-0 flex-1 cursor-text truncate rounded px-1 py-0.5 text-left text-xs font-medium text-foreground/90 hover:bg-muted/40"
                >
                  {artifactName}
                </button>
              )}
              <button
                type="button"
                onClick={() => setFileMenu((v) => !v)}
                title="File actions"
                aria-label="File actions"
                className="shrink-0 rounded p-1 text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground"
              >
                <MoreHorizontal className="h-4 w-4" />
              </button>
              {fileMenu && (
                <div className="absolute right-0 top-full z-30 mt-1 w-48 rounded-md border border-border bg-background p-1 shadow-md">
                  {(
                    [
                      ['Copy link', Link2, fileVerbs.copyLink],
                      ['Duplicate', Copy, fileVerbs.duplicate],
                      ['Rename…', Pencil, () => setNameEditing(true)],
                      ['Move…', FolderInput, fileVerbs.move],
                    ] as const
                  ).map(([label, Icon, run]) => (
                    <button
                      key={label}
                      type="button"
                      onClick={() => {
                        setFileMenu(false);
                        run();
                      }}
                      className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-[11px] text-foreground/80 transition-colors hover:bg-muted/40"
                    >
                      <Icon className="h-3.5 w-3.5 text-muted-foreground" /> {label}
                    </button>
                  ))}
                  <div className="mx-1 my-1 border-t border-border/60" />
                  <button
                    type="button"
                    onClick={() => {
                      setFileMenu(false);
                      fileVerbs.trash();
                    }}
                    title="Move this artifact to Trash (revertible from Files)"
                    className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-[11px] text-red-600 transition-colors hover:bg-red-50 dark:hover:bg-red-950/30"
                  >
                    <Trash2 className="h-3.5 w-3.5" /> Move to Trash
                  </button>
                </div>
              )}
            </div>
          </div>
          {/* Share + Export moved to the header (StudioShareExport, right of
              zoom, 2026-07-24) — boundary acts, not shaping properties. */}
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
                  <FaceTokenSelect
                    key={t.key}
                    token={t}
                    current={root?.getAttribute(`data-${t.key}`) ?? null}
                    stacks={resolvedFontStacks}
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
              {appliedSystem && (
                <AppliedSystemCue
                  name={appliedSystem.name}
                  manifestPath={appliedSystem.manifest_path}
                  onOpen={onOpenSystem}
                  note="is applied — its styles may override these."
                />
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
          {/* (The read-only Theme var-list is DELETED — ADR-487 D9. Inside an
              artifact the system is WORN, never listed: the controls above
              already carry every slot the member can act on, and the system AS
              AN OBJECT is the manage panel's register. The rationale is in full
              at the skinCss parse above.) */}
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
              {/* Page scope uses the SAME swatch row as block scope. One idea,
                  one presentation: leaving the dropdown here would put two
                  shapes of "pick a colour" in one panel two scopes apart —
                  precisely the drift ADR-487 D9 named when one word
                  ("Typography") had two presentations in one scroll. */}
              {applicable.map((t) =>
                tokenSwatches[t.key] ? (
                  <ColorTokenSwatches
                    key={t.key}
                    token={t}
                    current={selectedEl?.getAttribute(`data-${t.key}`) ?? null}
                    swatches={tokenSwatches[t.key]}
                    onSet={(v) => onSetToken('page', t.key, v)}
                  />
                ) : (
                  <TokenControl
                    key={t.key}
                    token={t}
                    current={selectedEl?.getAttribute(`data-${t.key}`) ?? null}
                    onSet={(v) => onSetToken('page', t.key, v)}
                  />
                ),
              )}
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

      {/* ── CONTAINER scope (ADR-511 D3/D4) ─────────────────────────────────
          A structural container — a column, a columns row, a slot-div — is a
          real element with identity: it duplicates/deletes/moves via the
          right-click menu (the id-addressed ops need no special casing), and
          this panel carries what only a container owns: its LAYOUT, as
          bounded plain-CSS properties (never a raw CSS pane — D7). */}
      {scope === 'container' && (
        <>
          <div className={SECTION}>
            <p className={HEADING}>{selection?.label ?? 'group'}</p>
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
                          selection!.slot!,
                          selection!.slideIndex,
                          selection!.pageIndex,
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
            ) : null}
          </div>
          <div className={SECTION}>
            <p className={HEADING}>Layout</p>
            {(
              [
                { key: 'padding', label: 'Padding', options: [
                  { v: '0', l: 'None' }, { v: '0.5rem', l: 'S' }, { v: '1rem', l: 'M' }, { v: '2rem', l: 'L' },
                ] },
                { key: 'gap', label: 'Gap', options: [
                  { v: '0', l: 'None' }, { v: '0.5rem', l: 'S' }, { v: '1rem', l: 'M' }, { v: '2rem', l: 'L' },
                ] },
                { key: 'align', label: 'Align', options: [
                  { v: 'flex-start', l: 'Start' }, { v: 'center', l: 'Center' },
                  { v: 'flex-end', l: 'End' }, { v: 'stretch', l: 'Stretch' },
                ] },
                { key: 'justify', label: 'Justify', options: [
                  { v: 'flex-start', l: 'Start' }, { v: 'center', l: 'Center' },
                  { v: 'flex-end', l: 'End' }, { v: 'space-between', l: 'Between' },
                ] },
              ] as const
            ).map((row) => {
              const style = selectedEl?.getAttribute('style') ?? '';
              const cssProp = { padding: 'padding', gap: 'gap', align: 'align-items', justify: 'justify-content' }[row.key];
              const cur = style.match(new RegExp(`(?:^|;)\\s*${cssProp}\\s*:\\s*([^;]+)`))?.[1]?.trim() ?? null;
              return (
                <div key={row.key} className="flex items-center justify-between gap-2 py-0.5">
                  <span className="text-[11px] text-muted-foreground">{row.label}</span>
                  <div className="flex gap-1">
                    {row.options.map((o) => (
                      <button
                        key={o.v}
                        type="button"
                        onClick={() => onContainerLayout({ [row.key]: cur === o.v ? null : o.v })}
                        className={`rounded border px-1.5 py-0.5 text-[10px] transition-colors ${
                          cur === o.v
                            ? 'border-foreground/50 text-foreground'
                            : 'border-border text-muted-foreground hover:bg-muted/40'
                        }`}
                      >
                        {o.l}
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* ── BLOCK scope ────────────────────────────────────────────────── */}
      {/* The identity/verb section (kind · id, the ask-about act, duplicate/
          up/down/delete, the double-click hint) is DELETED (2026-07-24):
          every verb already had a faster mouse entrance — the right-click
          menu (mode-gated, ADR-462) and the block keyboard (⌫/⌘C/⌘D/⌘V,
          ADR-477) — and editing is double-click on the canvas itself. The
          ask-about act relocated to the right-click menu (its only remaining
          mount). The pane keeps what only it can do: SHAPING (Turn into ·
          tokens · measures). The canvas selection box is the scope
          indicator. */}
      {scope === 'block' && (
        <>
          {/* Typography (ADR-487 D3 v2) — the ramp as a visual select, on the
              two ramp-shaped kinds (prose/heading), UNIVERSAL across layouts:
              current rung read from the tag, previews derived from the
              artifact's own styles under the applied skin. Picking a rung IS
              the turn-into conversion (id + tokens survive). */}
          {selection?.blockKind &&
            (selection.blockKind === 'prose' || selection.blockKind === 'heading') &&
            (() => {
              const tag = selectedEl?.tagName?.toLowerCase() ?? null;
              const curTag =
                selection.blockKind === 'heading' && tag && ['h1', 'h2', 'h3'].includes(tag)
                  ? tag
                  : 'p';
              const AG_SCALE: Record<string, number> = { h1: 18, h2: 16, h3: 14, p: 12 };
              const ag = (t: string) => (
                <span
                  className="w-6 shrink-0 text-center leading-none"
                  style={{
                    fontFamily: bodyFace,
                    fontSize: AG_SCALE[t] ?? 12,
                    fontWeight: t === 'p' ? 400 : 600,
                  }}
                >
                  Ag
                </span>
              );
              const proseRow = vocabulary?.blocks.find((b) => b.kind === 'prose');
              const curRow =
                TEXT_STYLE_ROWS.find((r) => r.key === curTag) ??
                TEXT_STYLE_ROWS[TEXT_STYLE_ROWS.length - 1];
              return (
                <div className={SECTION}>
                  <StyleSelect
                    label="Typography"
                    description="The block's place on the type ramp — sized by the layout, themed by the design system"
                    current={{ preview: ag(curTag), label: curRow.label, detail: tagFontSize(curTag) }}
                    options={TEXT_STYLE_ROWS.map((r) => ({
                      key: r.key,
                      preview: ag(r.key),
                      label: r.label,
                      detail: tagFontSize(r.key),
                      active: r.key === curTag,
                      onPick: () => {
                        if (r.key === curTag) return;
                        if (r.key === 'p') {
                          if (proseRow) onTurnInto(proseRow.kind, proseRow.label, proseRow.fragment);
                        } else {
                          onTurnInto(
                            'heading',
                            r.label,
                            `<${r.key} data-block="heading">…</${r.key}>`,
                          );
                        }
                      },
                    }))}
                  />
                </div>
              );
            })()}
          {/* COLOUR sits directly under TYPOGRAPHY — the two shaping questions a
              member asks in sequence ("how big / what role", then "what colour"),
              so they belong adjacent rather than separated by the structural
              verbs. Rendered as a laid-out SWATCH ROW: unlike the type ramp,
              a palette's whole content is legible at a glance, so a dropdown
              would hide behind a click exactly what it could have shown.
              Palette-backed tokens are lifted here; every other token keeps its
              existing home below, so this is a RELOCATION of one control, not a
              second mount of it. */}
          {colorTokens.length > 0 && (
            <div className={SECTION}>
              {colorTokens.map((t) => (
                <ColorTokenSwatches
                  key={t.key}
                  token={t}
                  current={selectedEl?.getAttribute(`data-${t.key}`) ?? null}
                  swatches={tokenSwatches[t.key]}
                  onSet={(v) => onSetToken('block', t.key, v)}
                />
              ))}
            </div>
          )}
          {/* Turn into (ADR-456 W2) — the id and tokens survive the conversion
              (a block with a citation refuses). On ramp blocks (prose/heading)
              the Typography select above OWNS the ramp, so this list carries
              only the STRUCTURAL targets; structural kinds keep the full list. */}
          {selection?.blockKind && TURN_INTO_KINDS.includes(selection.blockKind) && (
            <div className={SECTION}>
              <p className={HEADING}>Turn into</p>
              <div className="flex flex-wrap gap-1">
                {turnIntoTargets(
                  vocabulary?.blocks ?? [],
                  selection.blockKind,
                  selectedEl?.tagName ?? null,
                )
                  .filter(
                    (b) =>
                      !(
                        (selection.blockKind === 'prose' || selection.blockKind === 'heading') &&
                        (b.kind === 'heading' || b.kind === 'prose')
                      ),
                  )
                  .map((b) => (
                    <button
                      key={b.key}
                      type="button"
                      className={askBtn}
                      onClick={() => onTurnInto(b.kind, b.label, b.fragment)}
                    >
                      {b.label}
                    </button>
                  ))}
              </div>
            </div>
          )}
          {/* The remaining block tokens. Palette-backed ones are NOT here — they
              were lifted to the swatch row under Typography, and `nonColorTokens`
              is their complement, so every token still renders exactly once. */}
          {nonColorTokens.length > 0 && (
            <div className={SECTION}>
              {nonColorTokens.map((t) => (
                <TokenControl
                  key={t.key}
                  token={t}
                  current={selectedEl?.getAttribute(`data-${t.key}`) ?? null}
                  onSet={(v) => onSetToken('block', t.key, v)}
                />
              ))}
            </div>
          )}
          {/* ADR-487 D9 — the block scope's route OUT. The controls above are
              painted in the system's values and the Typography description says
              "themed by the design system", but this scope named no system and
              offered no way to reach one: the member had to deselect, then find
              the picker row. Same one line, same component, as document scope.

              ⭐ Its own section, gated on the SYSTEM rather than on a token list.
              It used to live inside the token section, and splitting colour out
              would have stranded it: a block whose only tokens are palette-backed
              (the common case — a callout has tone + variant) would render an
              empty complement, drop the section, and silently lose the route out
              that D9 exists to provide. */}
          {appliedSystem && (
            <div className={SECTION}>
              <AppliedSystemCue
                name={appliedSystem.name}
                manifestPath={appliedSystem.manifest_path}
                onOpen={onOpenSystem}
                note="supplies these values."
              />
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
          {/* ADR-511 D4 — Position is an explicit, visible, reversible state
              (the Claude Design benchmark's Inline/Absolute, in operator
              words). Flow is the default; dragging is what enters the
              positioned state; "In flow" is the reversal. Shown on every
              STAGED block so the state is legible before it surprises.
              ADR-485 D4 unchanged: the kernel rule requires BOTH x and y —
              read the state the kernel reads. */}
          {!!selectedEl?.closest('.slide') && (() => {
            const positioned =
              selectedEl.hasAttribute('data-x') && selectedEl.hasAttribute('data-y');
            const chip = (active: boolean) =>
              `rounded border px-1.5 py-0.5 text-[10px] transition-colors ${
                active
                  ? 'border-foreground/50 text-foreground'
                  : 'border-border text-muted-foreground hover:bg-muted/40'
              }`;
            return (
              <div className={SECTION}>
                <p className={HEADING}>Position</p>
                <div className="flex gap-1">
                  <button
                    type="button"
                    className={chip(!positioned)}
                    onClick={positioned ? onReturnToFlow : undefined}
                    disabled={!positioned}
                  >
                    In flow
                  </button>
                  <button type="button" className={chip(positioned)} disabled>
                    Positioned
                  </button>
                </div>
                <p className="text-[10px] text-muted-foreground">
                  {positioned
                    ? 'Dragged to a point on this slide — it no longer follows the layout. "In flow" returns it.'
                    : 'Follows the slide’s layout. Drag the block on the canvas to position it freely.'}
                </p>
              </div>
            );
          })()}
        </>
      )}

    </div>
  );
}
