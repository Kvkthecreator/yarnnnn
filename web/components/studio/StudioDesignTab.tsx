'use client';

/**
 * StudioDesignTab — the scope-switching inspector (ADR-453 D4 → ADR-519 D3).
 *
 * The right column's second tab (Chat | Design — the Canva model, never a
 * fourth column). Scope follows the canvas selection's GRAIN (document /
 * page / container / block), and every scope speaks the ONE SPINE:
 *
 *   Identity → Position → Layout → Style → Content
 *
 * A scope renders only the sections its grain has — it never re-orders or
 * renames a section (the one Figma property worth importing is the panel
 * GRAMMAR, not the node types). Per scope:
 *
 *  - DOCUMENT (nothing selected): Identity (the File card) → Style
 *    (typography faces / measure / the design-system picker, ADR-449 D5).
 *  - PAGE: Identity (noun + verb row) → Layout (ADR-516 presets) → Style
 *    (tone, scrim/focus) → Content (the cited background).
 *  - CONTAINER: Identity (operator-word label + verb row — ADR-519 parity;
 *    the id-addressed ops needed no special casing) → Layout (ADR-511 D4 +
 *    ADR-516 D4 presets) → Content (the media-role image picker).
 *  - BLOCK: Identity (kind + verb row) → Position (In flow | Positioned +
 *    X/Y readback, deck-staged) → Layout (size/align tokens + W/H readback)
 *    → Style (typography ramp · colour swatches · the applied-system cue) →
 *    Content (Turn into).
 *
 * Everything here EXECUTES deterministic ops through the surface's applyOp
 * (the one CAS door) — tokens for meaning, inline-CSS presets for geometry
 * (ADR-516 D6); current values are parsed from the artifact SOURCE at
 * render (derived, never stored).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlignCenterHorizontal,
  AlignCenterVertical,
  AlignEndHorizontal,
  AlignEndVertical,
  AlignStartHorizontal,
  AlignStartVertical,
  AlignHorizontalSpaceBetween,
  AlignVerticalSpaceBetween,
  ArrowDown,
  ArrowUp,
  Check,
  ChevronDown,
  ChevronRight,
  Copy,
  FolderInput,
  Link2,
  Loader2,
  MoreHorizontal,
  Palette,
  Pencil,
  StretchHorizontal,
  Trash2,
  type LucideIcon,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import {
  type StudioMeasure,
  type StudioSelection,
  type StudioToken,
  type StudioVocabulary,
} from './StudioToolbar';
import { studioShapeStyle } from './studioShapes';
// ADR-541 D2 — the one selection algebra; this pane derives nothing itself.
import { arityOf, scopeOf, unify, type PaneScope } from './selection';
import { climbChain } from './SelectionBreadcrumb';
import { labelForElement, STRUCTURAL_PAGE_SEL } from './structureLabels';
// ADR-487 D9: the Design tab reads the skin only to PAINT the controls
// (skinVarMap + resolveSkinVar). The var-LIST parse belongs to the manage panel
// alone now — the system-as-object register. Importing it here again would
// re-create the deleted artifact-side list, so the ADR-455 gate forbids it.
import { resolveSkinVar, skinVarMap } from './skinVars';
// ADR-525 D1 — the ONE text-kind list, shared with the projection runtime that
// declares the tier. Imported rather than re-enumerated so the pane's fallback
// cannot drift from the runtime's rule.
import { HEADING_RUNGS, TEXT_BLOCK_KINDS } from '../workspace/viewers/projection';

export type StructVerb = 'duplicate' | 'up' | 'down' | 'delete';

const PAGE_SEL = STRUCTURAL_PAGE_SEL; // ADR-511 Phase 2 — the one structural page selector

/** The block kinds a block can be turned INTO (ADR-456 W2) — text kinds only,
 *  because the conversion rebuilds text units and a citation must never
 *  flatten. Exported so the right-click submenu (ADR-479 D5) offers exactly the
 *  legal set: one list, two mounts. A copy would drift, and a menu offering an
 *  illegal conversion is a promise the op refuses to keep.
 *  ADR-487 D1: `heading` joins — the old exclusion ("headings anchor pages")
 *  was about the re-arrange sweep, which stays; it never needed to make
 *  headings unconvertible. */
/** ADR-539 D2 — the Turn-into set is DERIVED from the served vocabulary's
 *  `convertible` field, never enumerated here. The old `TURN_INTO_KINDS`
 *  hand-list is deleted: it was one of the shadow registries the audit found
 *  (a new kind joined it by editing a second file, or — as ADR-538's
 *  `component` proved — silently didn't). */
export function isConvertible(
  blocks: Array<{ kind: string; convertible?: boolean }> | null | undefined,
  kind: string | null | undefined,
): boolean {
  if (!kind) return false;
  return blocks?.find((b) => b.kind === kind)?.convertible === true;
}

/** ADR-539 D1 — a kind's tier, read from the served vocabulary. Falls back to
 *  the runtime's static copy (pinned to the registry by the parity gate) only
 *  while the vocabulary has not loaded yet. */
export function kindTier(
  blocks: Array<{ kind: string; tier?: 'text' | 'object' }> | null | undefined,
  kind: string | null | undefined,
): 'text' | 'object' | null {
  if (!kind) return null;
  const served = blocks?.find((b) => b.kind === kind)?.tier;
  if (served) return served;
  return (TEXT_BLOCK_KINDS as readonly string[]).includes(kind) ? 'text' : 'object';
}

/** ADR-539 D3 — the heading rungs, derived from the served `heading_rungs`
 *  (the kernel's one declaration; the tag carries the level, ADR-487 D1). */
export function headingLevels(rungs: number[]): Array<{ tag: string; label: string }> {
  return rungs.map((r) => ({ tag: `h${r}`, label: `Heading ${r}` }));
}

/** Build the Turn-into target list (ONE list, two mounts — the Design tab and
 *  the right-click submenu). `heading` expands to its three level targets
 *  (same kind, the tag carries the rung). `currentTag` (when the mount knows
 *  it) excludes the level the block already is; a mount that cannot know the
 *  tag passes null — clicking the current level is a convertBlock no-op, not
 *  a lie. */
export function turnIntoTargets(
  blocks: Array<{ kind: string; label: string; fragment: string; convertible?: boolean }>,
  headingRungs: number[],
  currentKind: string | null,
  currentTag: string | null,
): Array<{ key: string; kind: string; label: string; fragment: string }> {
  const out: Array<{ key: string; kind: string; label: string; fragment: string }> = [];
  // ADR-539 D2: iterate the SERVED roster (already app-scoped at the load
  // chokepoint) and take what declares itself convertible — registry order is
  // the offer order. No membership list lives on this side of the wire.
  for (const b of blocks) {
    if (!b.convertible) continue;
    if (b.kind === 'heading') {
      for (const lvl of headingLevels(headingRungs)) {
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
    if (b.kind === currentKind) continue;
    out.push({ key: b.kind, kind: b.kind, label: b.label, fragment: b.fragment });
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
  /** ADR-527 D4 — drive a RANGE op in the canvas runtime. The pane's buttons
   *  and the inline bar's buttons are two entrances to one `applyFmt`; this is
   *  the pane's. `value` carries a palette ROLE for mark/highlight (null
   *  clears) and is unused by the toggles. */
  onFormat: (op: string, value?: string | null) => void;
  /** ADR-528 — the blocks a live text range intersects. When this holds MORE
   *  THAN ONE, the block-scoped sections are describing a block the member is
   *  no longer looking at, and must say so instead. */
  rangeBlockIds?: string[];
  /** ADR-519 D4.1 — the ⇧-click set on a staged medium. State beside the
   *  selection, never a scope: a set has no label, no box and no tier, so it
   *  cannot be a subject the inspector describes. Length < 2 = no set. */
  groupIds?: string[];
  /** Align/distribute over the set — the one control whose subject genuinely
   *  IS the set. Writes through the existing setGeometryMany (one revision). */
  onAlignMany?: (edge: 'left' | 'hcenter' | 'right' | 'top' | 'vcenter' | 'bottom') => void;
  onDistributeMany?: (axis: 'h' | 'v') => void;
  /** Page verbs (duplicate-page has no other mount; the navigator covers
   *  delete/reorder). */
  onPageVerb: (verb: StructVerb) => void;
  /** ADR-519 D3 — the Identity verb row at container + block scope. The same
   *  id-addressed handler the right-click menu and the block keyboard use
   *  (one implementation, a third entrance); ADR-511 D5 made the ops work on
   *  containers with zero op-side change. The 2026-07-24 removal of the block
   *  row optimized for redundancy; the spine optimizes for a panel the member
   *  learns ONCE — every scope's Identity section carries its verbs. */
  onElementVerb: (verb: StructVerb) => void;
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
  /** ADR-520 D3 — numeric measure entry (keyboard beside the drag): commit a
   *  clamped value for the selected element (block OR staged container — the
   *  op is id-addressed). Same two-clamp specs as the gesture. */
  onSetMeasure: (key: 'w' | 'h' | 'x' | 'y', value: number) => void;
  /** ADR-520 D4 — the structure affordances (path + Contents) select through
   *  the SAME reaches the breadcrumb and navigator use (a new mount, not a
   *  new op): a node by identity, a page by index. */
  onSelectNode: (node: { blockId: string; label: string; kind: string | null }) => void;
  onSelectPage: (index: number) => void;
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
  /** ADR-511 Phase 2 — addressed by container IDENTITY, never by slot name. */
  onInsertImageInSlot: (path: string, containerId: string) => void;
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
 *  the ramp's (largest first), Text closing it, the Figma reading.
 *  ADR-539 D3 — DERIVED from the served rung set, never enumerated. */
function textStyleRows(rungs: number[]): Array<{ key: string; label: string }> {
  return [
    ...rungs.map((r) => ({ key: `h${r}`, label: `Heading ${r}` })),
    { key: 'p', label: 'Text' },
  ];
}

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

/** The structural verb row (Duplicate / Move up / Move down / Delete).
 *
 *  `reorder` gates the two MOVE verbs alone (ADR-525 follow-up, 2026-08-06). The
 *  row was withdrawn wholesale on the text tier, which closed the pane-vs-menu
 *  contradiction for prose and PRESERVED it for objects: a figure in a Docs
 *  artifact still offered Move up/down here while `StudioBlockMenu` refused the
 *  same verbs on the same block (it gates on `isPaged`, not on tier). Same fault
 *  pattern, one tier over — the tier D3 declared "untouched" and did not examine.
 *  Reordering is an ENCLOSURE act: it presumes a sequence of boxes. A figure on
 *  flow is an object (it has a box) but it sits in continuous prose (there is no
 *  sequence to step through), so the medium decides this, not the tier. */
function VerbRow({
  noun,
  onVerb,
  reorder = true,
}: {
  noun: string;
  onVerb: (v: StructVerb) => void;
  reorder?: boolean;
}) {
  const btn =
    'inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[10px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground';
  return (
    <div className="flex flex-wrap gap-1">
      <button type="button" className={btn} onClick={() => onVerb('duplicate')}>
        <Copy className="h-3 w-3" /> Duplicate
      </button>
      {reorder && (
        <>
          <button type="button" className={btn} onClick={() => onVerb('up')} title={`Move ${noun} up`}>
            <ArrowUp className="h-3 w-3" /> Up
          </button>
          <button
            type="button"
            className={btn}
            onClick={() => onVerb('down')}
            title={`Move ${noun} down`}
          >
            <ArrowDown className="h-3 w-3" /> Down
          </button>
        </>
      )}
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
// ADR-528 follow-up (2026-08-06) — MODULE scope, beside its two siblings.
//
// It was a component-body `const` ~450 lines below `turnIntoSection`, which
// ADR-528 lifted out of the render to give `range` and `object` one mount. The
// lift moved the JSX above this declaration and produced a TEMPORAL DEAD ZONE
// crash in production: "Cannot access 't9' before initialization", thrown from
// inside Array.map — the `.map()` in that very block.
//
// `tsc` passed and so did `next build`: the reference sits inside a JSX
// expression, so it is not a direct read TypeScript's use-before-declaration
// check can see (it caught `tagFontSize` in the same commit precisely because
// that one WAS direct). Only executing the component finds it.
//
// It is a static string with no props, no state and no hooks, so a body-local
// binding bought nothing and cost an ordering hazard. Here it cannot be lifted
// past.
const askBtn =
  'inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[10px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground';

/** ADR-519 D4.1 — align/distribute over a ⇧-click SET. The conventional glyph
 *  triplets per axis (ADR-520 D3's presentation rule: alignment is glyphable,
 *  values with magnitudes are not), reusing the SAME six icons the container
 *  align/justify rows already use — one visual vocabulary, two subjects.
 *
 *  The EDGE is the vocabulary, not a CSS property: these act on a set of boxes
 *  through `setGeometryMany`, never through `setContainerLayout` (which moves
 *  every child of one parent — the parent-side verb this is the complement of). */
const ALIGN_MANY = [
  { key: 'left' as const, title: 'Align left edges', Icon: AlignStartVertical },
  { key: 'hcenter' as const, title: 'Align horizontal centres', Icon: AlignCenterVertical },
  { key: 'right' as const, title: 'Align right edges', Icon: AlignEndVertical },
  { key: 'top' as const, title: 'Align top edges', Icon: AlignStartHorizontal },
  { key: 'vcenter' as const, title: 'Align vertical centres', Icon: AlignCenterHorizontal },
  { key: 'bottom' as const, title: 'Align bottom edges', Icon: AlignEndHorizontal },
];
const DISTRIBUTE_MANY = [
  { key: 'h' as const, title: 'Distribute horizontally', Icon: AlignHorizontalSpaceBetween },
  { key: 'v' as const, title: 'Distribute vertically', Icon: AlignVerticalSpaceBetween },
];

/** ADR-527 D2 — the palette roles, as the kernel declares them. Text colour and
 *  highlight name the SAME roles; highlight tints them (the ADR-487 D2
 *  callout-variant precedent), so a skin needs no new variables. Closed sets:
 *  the runtime validates against its own copy, so a raw value cannot reach the
 *  DOM even if this list were edited carelessly. */
const MARK_ROLES = [
  { value: 'muted', label: 'Muted', varName: 'muted', fallback: '#6b6b6b' },
  { value: 'accent', label: 'Accent', varName: 'accent', fallback: '#b4540a' },
  { value: 'fresh', label: 'Success', varName: 'fresh', fallback: '#2e7d32' },
  { value: 'warn', label: 'Warning', varName: 'warn', fallback: '#b45309' },
  { value: 'danger', label: 'Danger', varName: 'danger', fallback: '#b3261e' },
] as const;
const HIGHLIGHT_ROLES = MARK_ROLES.filter((r) => r.value !== 'muted');

/** The TEXT section (ADR-527 D4) — range emphasis, at the pane.
 *
 *  Every control here acts on the SELECTION, not the block: this is ADR-521
 *  D2's text tier, given a home. The inline bar keeps B/I/code/link (it is the
 *  at-the-caret affordance); the pane shows the full set. Two entrances, one
 *  `applyFmt` — the ADR-521 D4 shape, never a second implementation.
 *
 *  Deliberately NOT here: point size, line spacing, font family. Those are
 *  METRICS and the design system owns them (ADR-449) — §4 of the ADR records
 *  the refusal rather than leaving the absence to look like an oversight.
 *
 *  ADR-536 D2 — align + indent are BACK, in the section ADR-527 D3 assigned
 *  them to. They were lost in ADR-528 D2's re-cut: D3 put them in "a new Text
 *  section, not a resurrected Layout section", but the only mount for a
 *  block-grain token was the Layout section, which lives in `object` scope —
 *  so when flow's `block` scope became `range`, the tokens had no reachable
 *  home and silently vanished. This section is where D3 said they go.
 *
 *  They are BLOCK-grain (`onSetToken('block', …)`) while their neighbours are
 *  range ops, and that is not an inconsistency to tidy away: `data-align` is
 *  `text-align`, arrangement of prose inside its own measure. It addresses the
 *  block the caret is in — the STRUCTURE tier, exactly like the typography
 *  ramp and Turn into, both of which already sit at this scope on the same
 *  reasoning. Which is also why they withdraw over a multi-block range: the op
 *  is single-subject, and answering for one of six silently is the `d878242`
 *  defect. */
function TextSection({
  onFormat,
  swatch,
  flowTokens,
  currentOf,
  onSetToken,
}: {
  onFormat: (op: string, value?: string | null) => void;
  swatch: (varName: string, fallback: string) => string;
  /** The `block-flow` tokens (align/indent) applicable to the block the caret
   *  is in — empty over a multi-block range, and empty on a staged medium. */
  flowTokens: StudioToken[];
  currentOf: (key: string) => string | null;
  onSetToken: (key: string, value: string | null) => void;
}) {
  const btn =
    'inline-flex h-6 min-w-6 items-center justify-center rounded border border-border px-1.5 text-[11px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground';
  const dot =
    'h-4 w-4 shrink-0 rounded-full border border-border transition-transform hover:scale-110';
  return (
    <div className={SECTION}>
      <p className={HEADING}>Text</p>
      <div className="flex flex-wrap items-center gap-1">
        <button type="button" className={`${btn} font-semibold`} onClick={() => onFormat('bold')} title="Bold (⌘B)">
          B
        </button>
        <button type="button" className={`${btn} italic`} onClick={() => onFormat('italic')} title="Italic (⌘I)">
          I
        </button>
        <button type="button" className={`${btn} underline`} onClick={() => onFormat('underline')} title="Underline">
          U
        </button>
        <button type="button" className={`${btn} line-through`} onClick={() => onFormat('strike')} title="Strikethrough">
          S
        </button>
        <button type="button" className={`${btn} font-mono`} onClick={() => onFormat('code')} title="Code">
          {'<>'}
        </button>
        <button
          type="button"
          className={btn}
          onClick={() => onFormat('clear')}
          title="Clear formatting (structure is kept — a heading stays a heading)"
        >
          Clear
        </button>
      </div>
      {/* Colour is a ROLE, never a value — the one place this ADR chose canon
          over the benchmark (Google Docs offers a picker; ADR-449 forbids one). */}
      <div className="space-y-1">
        <p className="text-[10px] text-muted-foreground">Colour</p>
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            onClick={() => onFormat('mark', null)}
            title="Default"
            className={`${dot} relative overflow-hidden bg-background`}
          >
            <span className="absolute left-1/2 top-0 h-full w-px -translate-x-1/2 rotate-45 bg-border" />
          </button>
          {MARK_ROLES.map((r) => (
            <button
              key={r.value}
              type="button"
              onClick={() => onFormat('mark', r.value)}
              title={r.label}
              className={dot}
              style={{ background: swatch(r.varName, r.fallback) }}
            />
          ))}
        </div>
      </div>
      <div className="space-y-1">
        <p className="text-[10px] text-muted-foreground">Highlight</p>
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            onClick={() => onFormat('highlight', null)}
            title="None"
            className={`${dot} relative overflow-hidden bg-background`}
          >
            <span className="absolute left-1/2 top-0 h-full w-px -translate-x-1/2 rotate-45 bg-border" />
          </button>
          {HIGHLIGHT_ROLES.map((r) => (
            <button
              key={r.value}
              type="button"
              onClick={() => onFormat('highlight', r.value)}
              title={r.label}
              className={dot}
              style={{
                background: `color-mix(in srgb, ${swatch(r.varName, r.fallback)} 30%, transparent)`,
              }}
            />
          ))}
        </div>
      </div>
      <p className="text-[10px] text-muted-foreground">
        emphasis via the palette variables — never raw color
      </p>
      {/* ADR-536 D2 — align + indent, the block-grain rows of the text tier.
          Same TokenControl every other token renders through: one presentation
          for "pick among enumerated values", never a second shape for the same
          idea (the ADR-487 D9 drift). Served rows, so a value added to the
          vocabulary appears here with no edit. */}
      {flowTokens.map((t) => (
        <TokenControl
          key={t.key}
          token={t}
          current={currentOf(t.key)}
          onSet={(v) => onSetToken(t.key, v)}
        />
      ))}
    </div>
  );
}

/** ADR-520 D3 — a measure as a NUMERIC FIELD (the Figma detail grammar):
 *  editable within the served two-clamp bounds, keyboard instead of drag.
 *  Empty commits the clear (Auto) where a clear exists; the value shown is
 *  always the substrate's own (derived at render, never stored). */
function MeasureField({
  m,
  value,
  onCommit,
  onClear,
}: {
  m: StudioMeasure;
  value: number | null;
  onCommit: (v: number) => void;
  onClear?: () => void;
}) {
  return (
    <div className="flex items-center justify-between gap-2 py-0.5">
      <span className="text-[11px] text-muted-foreground" title={m.description}>
        {m.label}
      </span>
      <span className="flex items-center gap-1">
        <input
          key={value ?? 'auto'}
          type="number"
          min={m.min}
          max={m.max}
          defaultValue={value ?? ''}
          placeholder="Auto"
          aria-label={m.label}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              e.currentTarget.blur();
            }
          }}
          onBlur={(e) => {
            const raw = e.currentTarget.value.trim();
            if (raw === '') {
              if (value != null) onClear?.();
              return;
            }
            const v = Math.max(m.min, Math.min(m.max, Math.round(Number(raw))));
            if (!Number.isFinite(v) || v === value) return;
            onCommit(v);
          }}
          className="w-14 rounded border border-border bg-background px-1.5 py-0.5 text-right text-xs tabular-nums outline-none focus:border-indigo-400/60"
        />
        <span className="w-3 shrink-0 text-[10px] text-muted-foreground">{m.unit}</span>
      </span>
    </div>
  );
}

/** ADR-520 D4 — one row of the selection's structure (the walk the navigator's
 *  tree used before it moved here): a container (identity, no vocabulary) or a
 *  block (leaf). Operator words; the tree bottoms out at the block grammar. */
interface StructNode {
  blockId: string;
  label: string;
  kind: string | null;
  depth: number;
  text: string;
}

/** Walk an element's subtree into the flat, indented contents list.
 *  Containers recurse; blocks are leaves; unaddressed wrappers are
 *  transparent (their children surface at the same depth). */
function walkContents(root: Element): StructNode[] {
  const out: StructNode[] = [];
  const walk = (el: Element, depth: number) => {
    for (const child of Array.from(el.children)) {
      const id = child.getAttribute('data-block-id');
      const isBlock = child.hasAttribute('data-block');
      if (isBlock && id) {
        out.push({
          blockId: id,
          label: labelForElement(child),
          kind: child.getAttribute('data-block'),
          depth,
          text: (child.textContent ?? '').replace(/\s+/g, ' ').trim().slice(0, 60),
        });
        continue; // blocks are leaves — the tree floor
      }
      if (!isBlock && id && child.tagName === 'DIV') {
        out.push({ blockId: id, label: labelForElement(child), kind: null, depth, text: '' });
        walk(child, depth + 1);
        continue;
      }
      walk(child, depth); // transparent wrapper — children at the same depth
    }
  };
  walk(root, 0);
  return out;
}

/** ADR-526 D2 — the OUTLINE: the flow document's headings, in document order.
 *
 *  Docs' structural grain is the heading, and a "section" is the span from one
 *  heading to the next (D1) — so this is a projection of the prose, never a
 *  second structure. It cannot drift: write a heading and it appears, delete one
 *  and it goes. There is nothing to maintain and nothing to sync.
 *
 *  Derived CLIENT-side from the document the pane already parses, because every
 *  heading carries `data-block-id` from normalizeStructure. The server's
 *  `extract_outline` is NOT reused: it returns bare indented strings with no ids
 *  (ADR-522 §182) because its reader is the lane posture, which needs prose.
 *  Two readers, two derivations, each in its own register — never one function
 *  bent to serve both.
 *
 *  Emits StructNode so the EXISTING ContentsRows renders it (one row component,
 *  two mounts — the ADR-520 D4 pattern). `depth` is the heading LEVEL, so h2
 *  indents under h1 without any wrapper existing. */
function walkOutline(root: Element | null, rungs: number[]): StructNode[] {
  if (!root) return [];
  const out: StructNode[] = [];
  // ADR-539 D5 — the outline is ONE rule: a heading whose rung is in the
  // served set, holding a data-block-id, with nonempty text. The selector is
  // BUILT from the declared rungs; until 2026-08-09 this walked a hardcoded
  // 'h1, h2, h3' while promotion admitted h1–h6, which is how a block the
  // pane named "Heading" was invisible to the outline it stood in.
  // Document order, any depth: a heading inside a list or a callout still
  // belongs to the outline. querySelectorAll is already document-ordered.
  const sel = rungs.map((r) => `h${r}`).join(', ');
  for (const h of Array.from(root.querySelectorAll(sel))) {
    const id = h.getAttribute('data-block-id');
    if (!id) continue; // un-normalized (never written since ADR-511) — not addressable
    const text = (h.textContent ?? '').replace(/\s+/g, ' ').trim();
    if (!text) continue; // an empty heading names nothing
    out.push({
      blockId: id,
      label: text.slice(0, 60),
      kind: h.tagName.toLowerCase(), // the rung tag — the level IS the kind here
      depth: Number(h.tagName[1]) - 1,
      text: '',
    });
  }
  return out;
}

/** The Contents rows — the selection's own hierarchy, click-to-select. */
function ContentsRows({
  nodes,
  onSelect,
}: {
  nodes: StructNode[];
  onSelect: (n: { blockId: string; label: string; kind: string | null }) => void;
}) {
  if (!nodes.length) return null;
  return (
    <ul className="space-y-px">
      {nodes.map((n) => (
        <li key={n.blockId}>
          <button
            type="button"
            onClick={() => onSelect(n)}
            title={n.text || n.label}
            style={{ paddingLeft: `${n.depth * 10}px` }}
            className="flex w-full items-baseline gap-1.5 truncate rounded px-1 py-px text-left text-[10px] transition-colors hover:bg-muted/40"
          >
            <span
              className={
                n.kind
                  ? 'shrink-0 text-muted-foreground'
                  : 'shrink-0 font-medium text-emerald-700 dark:text-emerald-500'
              }
            >
              {n.label}
            </span>
            {n.text && <span className="truncate text-muted-foreground/70">{n.text}</span>}
          </button>
        </li>
      ))}
    </ul>
  );
}

/** ADR-516 D1/D3 — the ONE layout-row presentation, at every grain that has
 *  layout (container AND page). Bounded presets writing literal CSS through
 *  `setContainerLayout`; pressed-state reads the element's inline style first,
 *  a legacy token (`data-valign`/`data-pad`) as display-only fallback. */
function LayoutRows({
  rows,
  styleAttr,
  legacy,
  onSet,
}: {
  rows: ReadonlyArray<{
    key: string;
    label: string;
    css: string;
    options: ReadonlyArray<{ v: string; l: string; Icon?: LucideIcon }>;
  }>;
  styleAttr: string;
  legacy?: (cssProp: string) => string | null;
  onSet: (layout: Record<string, string | null>) => void;
}) {
  return (
    <>
      {rows.map((row) => {
        const cur =
          styleAttr
            .match(new RegExp(`(?:^|;)\\s*${row.css}\\s*:\\s*([^;]+)`))?.[1]
            ?.trim() ??
          legacy?.(row.css) ??
          null;
        return (
          <div key={row.key} className="flex items-center justify-between gap-2 py-0.5">
            <span className="text-[11px] text-muted-foreground">{row.label}</span>
            <div className="flex gap-1">
              {row.options.map((o) => (
                <button
                  key={o.v}
                  type="button"
                  onClick={() => onSet({ [row.key]: cur === o.v ? null : o.v })}
                  // ADR-520 D3 — the glyphable options wear the conventional
                  // alignment icons (the Figma detail grammar); the label
                  // survives as the tooltip. Value + mechanism untouched.
                  title={o.l}
                  aria-label={o.l}
                  className={`rounded border px-1.5 py-0.5 text-[10px] transition-colors ${
                    cur === o.v
                      ? 'border-foreground/50 text-foreground'
                      : 'border-border text-muted-foreground hover:bg-muted/40'
                  }`}
                >
                  {o.Icon ? <o.Icon className="h-3.5 w-3.5" /> : o.l}
                </button>
              ))}
            </div>
          </div>
        );
      })}
    </>
  );
}

export function StudioDesignTab({
  vocabulary,
  layout,
  html,
  selection,
  onSetToken,
  onFormat,
  rangeBlockIds,
  groupIds,
  onAlignMany,
  onDistributeMany,
  onPageVerb,
  onElementVerb,
  onTurnInto,
  onReturnToFlow,
  onContainerLayout,
  measures,
  onClearMeasure,
  onSetMeasure,
  onSelectNode,
  onSelectPage,
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
  // layer rule, AUTHORING.md). PowerPoint refuses the same thing: a layout's
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
   *  surface's own `layoutMode` (show the flowing, less-chrome reading first).
   *
   *  ADR-528: hoisted above the scope computation — scope is now DERIVED from
   *  the tier, and the tier needs the medium. */
  const mode = vocabulary?.layouts.find((l) => l.slug === layout)?.mode ?? 'flow';

  /** ADR-525 D3 — the TEXT tier: prose on a continuous writing surface.
   *
   *  Read from the runtime's declaration, never re-derived (D1). The fallback
   *  covers only the frame before a tier-stamped payload arrives (an older
   *  projection still live in the iframe). It reads the SAME exported kind list
   *  the runtime derives from — not a second copy of the rule — so an added
   *  block kind cannot make the two disagree. */
  const isTextTier = selection
    ? (selection.tier ??
        (mode === 'flow' && kindTier(vocabulary?.blocks, selection.blockKind) === 'text'
          ? 'text'
          : 'object')) === 'text'
    : false;

  // ADR-528 D2 — on FLOW the scope set is `document | range | object`. `block`
  // is not a scope a continuous document can produce.
  //
  // The fault this closes: scope used to be committed from `blockId &&
  // blockKind` alone, and the TIER — which the runtime had already declared
  // (ADR-525 D1) — arrived 50 lines later and could only SUBTRACT from a
  // decision already made. That is why the pane matrix's `block (text)` column
  // was defined almost entirely by absence: no path, no verb row, no Hug|Fill,
  // no W/H, no Position. A column of withdrawals is a scope that was never
  // meant to be entered.
  //
  // On a stage `block` genuinely IS a selection scope — a slide object is a
  // thing with a box. On a continuous surface the selection is a RANGE, which
  // may cover half a paragraph or six paragraphs; there is no "the selected
  // block". One word doing two jobs across two media was the whole grammar
  // collision ADR-519 D3 imported from Figma.
  //
  // Derived FROM the declared tier, never re-derived (rule 11 intact — the
  // runtime remains the only party that reads the DOM and the medium together).
  // `container`/`page` never applied to flow anyway (ADR-481 D1).
  //
  // ── THE RANGE IS ITSELF A SELECTION (fix, 2026-08-06) ────────────────────
  //
  // ADR-528 shipped `range` scope and left it UNREACHABLE from the gesture it
  // was built for. Operator screenshot: a live multi-block selection, the bar
  // showing B/I/code/Link, and the pane reading "Document — select a block on
  // the canvas to shape it here" — `document` scope, the nothing-selected
  // state, while the member had six blocks selected.
  //
  // The cause: every branch below keys off `selection`, which is written ONLY
  // by a click (`yarnnn-point`). A drag posts `yarnnn-range` into
  // `rangeBlockIds` — separate state, correctly so (they answer "what did you
  // point at" vs "what have you got"). But nothing bridged them, so a range
  // with no preceding click left `selection` null and the whole TextSection —
  // the ADR-527 D1/D2 emphasis set, the Google Docs half of the benchmark —
  // never mounted.
  //
  // A live range IS a selection on a continuous surface. `!selection` cannot
  // mean "nothing selected" here; it means "nothing CLICKED". Checked FIRST,
  // before the click-derived ladder, because a range outranks a stale click:
  // if the member has both, what they are looking at is the range (which is
  // the `d878242` finding, one gesture earlier).
  //
  // ADR-541 D2 — the ladder itself moved to `scopeOf` in selection.ts: this
  // pane is now a CONSUMER of the one derivation, beside the menu, the
  // toolbar and the focus line, so the surfaces structurally cannot disagree
  // about a selection again (the ADR-525 defect class, closed at the root).
  const unified = unify(selection ?? null, rangeBlockIds, groupIds);
  const scope: PaneScope = scopeOf(unified, mode, isTextTier ? 'text' : 'object');

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
  // ADR-539 D3 — the kernel's declared rung set; the static fallback is the
  // runtime's copy, pinned to the registry by the parity gate.
  const rungs = vocabulary?.heading_rungs ?? [...HEADING_RUNGS];
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
  const pageNoun = mode === 'paged' && layout === 'deck' ? 'slide' : 'section';

  /** ADR-528 — a MULTI-BLOCK range is live.
   *
   *  The defect this closes: `selection` is written by a CLICK and nothing
   *  updated it on a drag, so selecting six blocks left the pane showing
   *  "HEADING · Typography: Heading 2 · Turn into" — describing whichever block
   *  was last clicked into. It did not look wrong, which is precisely what made
   *  it hard to see. It was STALE.
   *
   *  The root cause is a grammar collision, and it is worth naming here because
   *  the fix reads as arbitrary without it: the pane's spine (ADR-519 D3) came
   *  from Figma, where selection IS object selection, so every section presumes
   *  ONE subject. A text range has no single subject. Until that is re-derived
   *  (ADR-528 §the open question), the honest move is for block-scoped sections
   *  to withdraw and SAY they have withdrawn, rather than answer for a block
   *  the member is not looking at. */
  const arity = arityOf(unified);
  const multiBlockRange = arity === 'many' && unified.setKind === 'range';
  /** ADR-519 D4.1 — the same question at the OBJECT tier. A ⇧-click set on a
   *  stage is the paged analogue of a multi-block range on flow: more than one
   *  subject, so every single-subject section must withdraw and say it has.
   *  One member is a selection, not a set — hence `many`, not any set at all.
   *  (ADR-541 D2: both flags are readings of ONE arity + setKind now.) */
  const multiObject = arity === 'many' && unified.setKind === 'objects';

  // ADR-485 follow-on — the SIZE measures a block can carry (w/h), and which of
  // them apply at this scope (ADR-461 D4 `applies`: block-staged = a block on a
  // fixed frame; media = a media block anywhere). This is the read-back the
  // inspector was missing entirely: a member who dragged a block to 60% wide
  // had no numeric confirmation anywhere in the tab (the value lived only in the
  // transient in-gesture frame label). The position measures (x/y) render in
  // the spine's Position section (ADR-519 Phase A), not here.
  const sizeMeasures = useMemo(() => {
    // ADR-528 D2: `object`, never `range` — a range has no box to size.
    if (scope !== 'object' && scope !== 'container') return [];
    const framed = !!selectedEl?.closest('.slide');
    // ADR-520 D2 — a STAGED container carries w/h too (the ops are
    // id-addressed; the runtime's gate was the only block-only half).
    if (scope === 'container') {
      return framed
        ? (measures ?? []).filter(
            (m) => (m.key === 'w' || m.key === 'h') && m.applies.includes('block-staged'),
          )
        : [];
    }
    const isMedia = !!selection?.blockKind && mediaKinds.includes(selection.blockKind);
    return (measures ?? []).filter(
      (m) =>
        (m.key === 'w' || m.key === 'h') &&
        ((framed && m.applies.includes('block-staged')) ||
          (isMedia && m.applies.includes('media'))),
    );
  }, [scope, measures, selection, selectedEl, mediaKinds]);

  // ADR-519 Phase A — the POSITION readback (x/y): the drag's numeric receipt,
  // shown in the Position section when the block is out of flow. Deck-staged
  // only (the one coordinate space, ADR-505 D3); numeric ENTRY is Phase C.
  const posMeasures = useMemo(() => {
    if (scope !== 'object' || !selectedEl?.closest('.slide')) return [];
    return (measures ?? []).filter(
      (m) => (m.key === 'x' || m.key === 'y') && m.applies.includes('block-staged'),
    );
  }, [scope, measures, selectedEl]);

  // ADR-520 D4 — the structure's one home: the ancestor PATH (the breadcrumb's
  // own climbChain — one derivation, two mounts) + the selection's CONTENTS
  // (the walk the navigator's tree carried before it moved here). Derived from
  // the parsed SOURCE at render, never stored.
  const pageEl = useMemo(
    () => (selectedEl ? (selectedEl.closest(PAGE_SEL) ?? null) : null),
    [selectedEl],
  );
  const pageOfSelection = useMemo(() => {
    if (!doc || !pageEl) return null;
    const i = Array.from(doc.querySelectorAll(PAGE_SEL)).indexOf(pageEl);
    return i >= 0 ? i : null;
  }, [doc, pageEl]);
  const pathChain = useMemo(() => {
    if (!selectedEl || !pageEl || (scope !== 'object' && scope !== 'container')) return [];
    return climbChain(selectedEl, pageEl)
      .map((el) => ({
        blockId: el.getAttribute('data-block-id') ?? '',
        label: labelForElement(el),
      }))
      .filter((c) => c.blockId);
  }, [selectedEl, pageEl, scope]);
  const contents = useMemo(() => {
    if (!selectedEl || (scope !== 'page' && scope !== 'container')) return [];
    return walkContents(selectedEl);
  }, [selectedEl, scope]);
  /** ADR-526 D2 — the outline, on FLOW only. On a paged medium the navigator IS
   *  the sequence (ADR-520 D4) and Contents carries the within-page structure;
   *  a third view there would be the "second structure tree" ADR-520 D5
   *  refused. Flow has neither, which is the whole gap this closes. */
  const outline = useMemo(
    () => (mode === 'flow' ? walkOutline(doc?.body ?? null, rungs) : []),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- rungs is served
    // kernel state; its identity changes only with the vocabulary fetch.
    [doc, mode, rungs.join()],
  );
  const pathRow =
    // ADR-528 D2: pathRow is a PAGE_SEL ancestry chain — structurally never
    // present on flow (ADR-481 D1), so `object` here means a paged block.
    (scope === 'object' || scope === 'container') && pageOfSelection != null ? (
      <div className="flex flex-wrap items-center gap-0.5 text-[10px] text-muted-foreground">
        <button
          type="button"
          onClick={() => onSelectPage(pageOfSelection)}
          className="rounded px-0.5 transition-colors hover:bg-muted/40 hover:text-foreground"
        >
          {pageNoun} {pageOfSelection + 1}
        </button>
        {pathChain.map((c) => (
          <span key={c.blockId} className="flex items-center gap-0.5">
            <ChevronRight className="h-2.5 w-2.5 shrink-0 text-muted-foreground/50" />
            <button
              type="button"
              onClick={() => onSelectNode({ blockId: c.blockId, label: c.label, kind: null })}
              className="rounded px-0.5 text-emerald-700 transition-colors hover:bg-muted/40 dark:text-emerald-500"
            >
              {c.label}
            </button>
          </span>
        ))}
      </div>
    ) : null;

  /** ADR-526 D2 — the flow analogue of `pathRow`, which is structurally ALWAYS
   *  NULL on a document: it gates on `pageOfSelection`, resolved through
   *  PAGE_SEL, and ADR-481 D1 flattened flow scaffolds so no <section> ancestor
   *  exists. (AUTHORING.md claimed "✅ path" for block(text) until `a862438`.)
   *
   *  The honest chain on flow is ONE rung — the enclosing heading — because the
   *  document is one rung deep. Sourced from `selection.headingId`, which the
   *  runtime already stamps on every point payload (ADR-522 D4) and which,
   *  until now, only the lane ever read. Clicking it selects the heading
   *  through the same reach the outline uses. */
  const headingRow =
    // ADR-528 D2: `range` — the flow crumb belongs to the text scope, which is
    // the only scope a flow medium can produce for prose. An object on flow
    // (a figure) keeps its own Identity without a heading rung.
    (scope === 'range' || scope === 'object') &&
    mode === 'flow' &&
    selection?.headingId &&
    selection.headingId !== selection.blockId ? (
      <div className="flex flex-wrap items-center gap-0.5 text-[10px] text-muted-foreground">
        <button
          type="button"
          onClick={() =>
            onSelectNode({
              blockId: selection.headingId!,
              label: selection.headingText ?? 'heading',
              kind: null,
            })
          }
          title="Select this heading"
          className="max-w-full truncate rounded px-0.5 text-emerald-700 transition-colors hover:bg-muted/40 dark:text-emerald-500"
        >
          {selection.headingText ?? 'heading'}
        </button>
        <ChevronRight className="h-2.5 w-2.5 shrink-0 text-muted-foreground/50" />
        <span>{selection.label ?? selection.blockKind ?? 'block'}</span>
      </div>
    ) : null;

  /** ADR-528 D2 — the STRUCTURE-tier sections, lifted so `range` and `object`
   *  mount ONE implementation (rule 7: one op, N entrances). They were inline
   *  in the old `block` branch; splitting that branch in two would otherwise
   *  have duplicated them, which is exactly the forked-machinery shape ADR-518
   *  D2 refuses.
   *
   *  Content — Turn into (ADR-456 W2): the id and tokens survive the
   *  conversion (a block with a citation refuses). On ramp blocks
   *  (prose/heading) the Typography select OWNS the ramp, so this list carries
   *  only the STRUCTURAL targets; structural kinds keep the full list.
   *
   *  ADR-541 D3 — mounts over a multi-block range too (the surface routes the
   *  pick through convertBlocks: every covered block, one revision; a block
   *  the conversion refuses per-block is skipped, never a whole-range veto).
   *  A span may have no clicked primary, so every `selection` read here is
   *  optional — a null current kind just means no row is excluded as "what
   *  the block already is". */
  const turnIntoSection =
    (selection?.blockKind && isConvertible(vocabulary?.blocks, selection.blockKind)) ||
    multiBlockRange ? (
      <div className={SECTION}>
        <p className={HEADING}>Turn into</p>
        <div className="flex flex-wrap gap-1">
          {turnIntoTargets(
            vocabulary?.blocks ?? [],
            rungs,
            selection?.blockKind ?? null,
            selectedEl?.tagName ?? null,
          )
            .filter(
              (b) =>
                !(
                  (selection?.blockKind === 'prose' || selection?.blockKind === 'heading') &&
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
    ) : null;

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
    // ADR-528 D2: both block-derived scopes compute their token set here — a
    // `range` still reaches tone + align/indent (meaning and arrangement in the
    // measure, ADR-527 D3), it is the BOX tokens it never had. Which of these
    // actually render is decided per-section below, not by narrowing here.
    if (scope === 'range' || scope === 'object') {
      const isMedia = !!selection?.blockKind && mediaKinds.includes(selection.blockKind);
      // ADR-487 D2: kind-gated grain (the `media` precedent) — the callout's
      // semantic register applies to callouts alone.
      const isCallout = selection?.blockKind === 'callout';
      // ADR-525 D4 — `block-staged` now gates TOKENS, not only measures. The
      // measure half read this grain correctly from the start (sizeMeasures);
      // the token half never did, so a token declaring the narrow grain would
      // have rendered everywhere. Same `.slide` ancestry test, one meaning.
      const isStaged = !!selectedEl?.closest('.slide');
      // ADR-527 D3 — `block-flow` is finally consumed. ADR-525 D4 added the
      // term to the vocabulary and nothing used it; align + indent are its
      // first rows, and they are the reason it exists.
      return tokens.filter(
        (t) =>
          t.applies.includes('block') ||
          (isStaged && t.applies.includes('block-staged')) ||
          (!isStaged && mode === 'flow' && t.applies.includes('block-flow')) ||
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
        : (selectedEl?.querySelectorAll('div.col').length ?? 0) >= 2; // ADR-511 Ph2: structural fallback
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
  /** ADR-527 D2 — resolve a palette ROLE to a paint colour, for the swatch
   *  dots only. The document never receives this value: the write is the role
   *  NAME, and the kernel's `span[data-mark=…]` rule resolves it through the
   *  skin's custom property. So the pane shows the system's colour without ever
   *  hard-coding one, and a skin change re-themes both at once. */
  const swatchOf = useCallback(
    (varName: string, fallback: string) => resolveSkinVar(skinMap, varName, fallback),
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
    () =>
      scope === 'range' || scope === 'object'
        ? applicable.filter((t) => !!tokenSwatches[t.key])
        : [],
    [scope, applicable, tokenSwatches],
  );
  /** ADR-536 D2 — the `block-flow` rows (align + indent), for the Text section.
   *
   *  DERIVED from the served grain, never a hardcoded ['align','indent']: a
   *  token that declares `block-flow` tomorrow joins with no edit here, which
   *  is the same rule `colorTokens` follows one comment up. `applicable`
   *  already computes these at range scope — ADR-527 D3's amendment is what
   *  put `block-flow` in the filter — they simply had nowhere to render.
   *
   *  Withdrawn over a MULTI-BLOCK range: `onSetToken('block', …)` writes to
   *  `selectedEl`, one block, so offering it while six are selected would
   *  answer for the block that happened to be clicked. That is `d878242`
   *  exactly, and the neighbouring ramp/turn-into sections withdraw on the
   *  same rule and SAY so in the multi-block notice. */
  // ADR-541 D3 — align/indent mount over ANY range, single-caret or spanning:
  // the surface's token handler applies a block-flow token to every covered
  // block as ONE revision (the Google Docs contract — a paragraph style
  // reaches every paragraph the range covers).
  const flowTokens = useMemo(
    () =>
      scope === 'range' ? applicable.filter((t) => t.applies.includes('block-flow')) : [],
    [scope, applicable],
  );
  // ...and its complement, so each token renders EXACTLY ONCE. Lifting without
  // this would leave the control mounted twice in one panel — the duplicate-mount
  // defect ADR-466 P12 and ADR-505 D5 each had to delete.
  const nonColorTokens = useMemo(
    () =>
      scope === 'range' || scope === 'object'
        ? applicable.filter((t) => !tokenSwatches[t.key])
        : applicable,
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

  /** ADR-528 D2 — Typography, the second STRUCTURE-tier section (see
   *  `turnIntoSection` above for why both are lifted out of the render).
   *  Declared HERE rather than beside its sibling because it reads
   *  `tagFontSize` and `bodyFace`, both of which derive from the artifact's
   *  own resolved CSS and cannot be hoisted above it.
   *
   *  ADR-487 D3 v2 — the ramp as a visual select, on the two ramp-shaped kinds
   *  (prose/heading), UNIVERSAL across layouts: current rung read from the tag,
   *  previews derived from the artifact's own styles under the applied skin.
   *  Picking a rung IS the turn-into conversion (id + tokens survive). */
  const rampSection =
    // ADR-541 D3 — the ramp mounts over a multi-block range too (a rung pick
    // reaches every covered block via convertBlocks, the Google Docs
    // contract); a span may carry no clicked primary, so the reads are
    // optional and the shown rung falls to Text.
    (selection?.blockKind &&
      (selection.blockKind === 'prose' || selection.blockKind === 'heading')) ||
    multiBlockRange
      ? (() => {
          const tag = selectedEl?.tagName?.toLowerCase() ?? null;
          const rows = textStyleRows(rungs);
          const rungTags = rungs.map((r) => `h${r}`);
          const curTag =
            selection?.blockKind === 'heading' && tag && rungTags.includes(tag) ? tag : 'p';
          // Preview size per rung: the ramp descends 2px per rung from 18,
          // Text at 12 — a preview scale, not the kernel's type scale.
          const agSize = (t: string) =>
            t === 'p' ? 12 : Math.max(12, 18 - 2 * (Number(t.slice(1)) - 1));
          const ag = (t: string) => (
            <span
              className="w-6 shrink-0 text-center leading-none"
              style={{
                fontFamily: bodyFace,
                fontSize: agSize(t),
                fontWeight: t === 'p' ? 400 : 600,
              }}
            >
              Ag
            </span>
          );
          const proseRow = vocabulary?.blocks.find((b) => b.kind === 'prose');
          const curRow = rows.find((r) => r.key === curTag) ?? rows[rows.length - 1];
          return (
            <div className={SECTION}>
              <StyleSelect
                label="Typography"
                description="The block's place on the type ramp — sized by the layout, themed by the design system"
                current={{ preview: ag(curTag), label: curRow.label, detail: tagFontSize(curTag) }}
                options={rows.map((r) => ({
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
                      onTurnInto('heading', r.label, `<${r.key} data-block="heading">…</${r.key}>`);
                    }
                  },
                }))}
              />
            </div>
          );
        })()
      : null;

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
            {/* ADR-526: on flow the invitation named a grain the medium does not
                have — `pageNoun` resolves to "section", and Docs has no section
                unit (ADR-522 D4). Say what is actually selectable. */}
            <p className="text-xs text-muted-foreground">
              {vocabulary?.layouts.find((l) => l.slug === layout)?.label ?? layout} —{' '}
              {mode === 'flow'
                ? 'select a block on the canvas to shape it here.'
                : `select a ${pageNoun} or a block on the canvas to shape it here.`}
            </p>
          </div>
          {/* ADR-526 D2 — the OUTLINE. The document's headings, read back in
              order, click-to-jump. This is the structure the system already
              derived twice and showed to nobody: `extract_outline` fed the lane
              posture and ADR-522's headingId fed the focus line, whose own
              docstring says "which the member never sees". The member had font
              sizes. Housed in the pane per ADR-520 D4 ("the pane is the
              structure's home") — the same reading that deleted Studio's
              navigator tree, so Docs inherits it rather than growing a rail. */}
          {mode === 'flow' && (
            <div className={SECTION}>
              <p className={HEADING}>Outline</p>
              {outline.length > 0 ? (
                <ContentsRows nodes={outline} onSelect={onSelectNode} />
              ) : (
                // The honest empty state: a document whose structure lives in
                // bold paragraphs has none the system can name. Say that, never
                // invent one (ADR-526 §7).
                <p className="text-[10px] text-muted-foreground">
                  No headings yet — add one and it appears here.
                </p>
              )}
            </div>
          )}
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
            {/* ADR-520 D4 — the page's Contents: the within-page hierarchy,
                absorbed from the navigator (whose rail is the SEQUENCE now). */}
            <ContentsRows nodes={contents} onSelect={onSelectNode} />
          </div>
          {/* ADR-516 D3 — the page IS a container: layout rows in the same
              language as container scope (bounded CSS presets, one op). The
              legacy valign/pad tokens read as pressed-state fallback only;
              a write strips them from this element (D2, convergence-by-use). */}
          <div className={SECTION}>
            <p className={HEADING}>Layout</p>
            {layout === 'deck' && !!selectedEl?.matches('section.slide') ? (
              <LayoutRows
                rows={[
                  { key: 'padding', label: 'Padding', css: 'padding', options: [
                    { v: '2rem 2.5rem', l: 'S' }, { v: '3.5rem 4rem', l: 'M' }, { v: '4.5rem 5.5rem', l: 'L' },
                  ] },
                  { key: 'justify', label: 'Vertical align', css: 'justify-content', options: [
                    { v: 'flex-start', l: 'Top', Icon: AlignStartHorizontal },
                    { v: 'center', l: 'Middle', Icon: AlignCenterHorizontal },
                    { v: 'flex-end', l: 'Bottom', Icon: AlignEndHorizontal },
                  ] },
                ]}
                styleAttr={selectedEl?.getAttribute('style') ?? ''}
                legacy={(css) => {
                  const valign = selectedEl?.getAttribute('data-valign');
                  const pad = selectedEl?.getAttribute('data-pad');
                  if (css === 'justify-content' && valign) return `flex-${valign}`;
                  if (css === 'padding' && pad === 's') return '2rem 2.5rem';
                  if (css === 'padding' && pad === 'l') return '4.5rem 5.5rem';
                  return null;
                }}
                onSet={onContainerLayout}
              />
            ) : (
              <LayoutRows
                rows={[
                  { key: 'padY', label: 'Spacing', css: 'padding-block', options: [
                    { v: '0.25rem', l: 'Tight' }, { v: '1rem', l: 'M' }, { v: '2.5rem', l: 'Airy' },
                  ] },
                ]}
                styleAttr={selectedEl?.getAttribute('style') ?? ''}
                legacy={(css) => {
                  const pad = selectedEl?.getAttribute('data-pad');
                  if (css === 'padding-block' && pad === 's') return '0.25rem';
                  if (css === 'padding-block' && pad === 'l') return '2.5rem';
                  return null;
                }}
                onSet={onContainerLayout}
              />
            )}
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

      {/* ── CONTAINER scope (ADR-511 D3/D4 · ADR-519 D3 spine) ──────────────
          A structural container — a column, a columns row, a slot-div — is a
          real element with identity. Spine: Identity (label + verb row — the
          id-addressed ops need no special casing, ADR-511 D5) → Layout
          (bounded plain-CSS presets, never a raw CSS pane — D7) → Content
          (the media-role image picker). */}
      {scope === 'container' && (
        <>
          <div className={SECTION}>
            <p className={HEADING}>{selection?.label ?? 'group'}</p>
            {pathRow}
            <VerbRow noun={selection?.label ?? 'group'} onVerb={onElementVerb} />
            {/* ADR-520 D4 — the container's Contents (structure's one home). */}
            <ContentsRows nodes={contents} onSelect={onSelectNode} />
          </div>
          <div className={SECTION}>
            <p className={HEADING}>Layout</p>
            <LayoutRows
              rows={[
                { key: 'padding', label: 'Padding', css: 'padding', options: [
                  { v: '0', l: 'None' }, { v: '0.5rem', l: 'S' }, { v: '1rem', l: 'M' }, { v: '2rem', l: 'L' },
                ] },
                { key: 'gap', label: 'Gap', css: 'gap', options: [
                  { v: '0', l: 'None' }, { v: '0.5rem', l: 'S' }, { v: '1rem', l: 'M' }, { v: '2rem', l: 'L' },
                ] },
                // ADR-520 D3 — the alignment rows wear the conventional glyphs
                // (a column container: Align = the cross axis, Justify = the
                // main axis). Values + the one op unchanged.
                { key: 'align', label: 'Align', css: 'align-items', options: [
                  { v: 'flex-start', l: 'Start', Icon: AlignStartVertical },
                  { v: 'center', l: 'Center', Icon: AlignCenterVertical },
                  { v: 'flex-end', l: 'End', Icon: AlignEndVertical },
                  { v: 'stretch', l: 'Stretch', Icon: StretchHorizontal },
                ] },
                { key: 'justify', label: 'Justify', css: 'justify-content', options: [
                  { v: 'flex-start', l: 'Start', Icon: AlignStartHorizontal },
                  { v: 'center', l: 'Center', Icon: AlignCenterHorizontal },
                  { v: 'flex-end', l: 'End', Icon: AlignEndHorizontal },
                  { v: 'space-between', l: 'Between', Icon: AlignVerticalSpaceBetween },
                ] },
                // ADR-516 D4 — the container's width as intent: Hug | Fill,
                // the ADR-461 D1 pair at the container grain (Fixed refused).
                { key: 'width', label: 'Width', css: 'width', options: [
                  { v: 'fit-content', l: 'Hug' }, { v: '100%', l: 'Fill' },
                ] },
              ]}
              styleAttr={selectedEl?.getAttribute('style') ?? ''}
              onSet={onContainerLayout}
            />
            {/* ADR-520 D2/D3 — a STAGED container's W/H: the drag's keyboard
                twin (the handles live on the canvas; empty = Auto). */}
            {sizeMeasures.map((m) => (
              <MeasureField
                key={m.key}
                m={m}
                value={measureValue(m)}
                onCommit={(v) => onSetMeasure(m.key as 'w' | 'h', v)}
                onClear={() => onClearMeasure(m.key as 'w' | 'h')}
              />
            ))}
          </div>
          {/* Content — the media-role picker: the one job the old slot scope
              did that a plain container cannot, resolved from the registry
              while data-slot survives as an inert name (ADR-511 D8). */}
          {slotRole === 'media' && (
            <div className={SECTION}>
              <p className={HEADING}>Image</p>
              {slotImages == null ? (
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
                      onClick={() => onInsertImageInSlot(img.path, selection!.blockId!)}
                      className="flex w-full flex-col rounded px-2 py-1 text-left hover:bg-muted/40"
                    >
                      <span className="truncate text-xs">{baseName(img.path)}</span>
                      <span className="truncate text-[10px] text-muted-foreground">
                        {img.path.replace(/^\/workspace\//, '')}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* ── BLOCK scope (ADR-519 D3 spine) ───────────────────────────────
          Identity → Position → Layout → Style → Content. The verb row
          returned with the spine (it left 2026-07-24 as redundant with the
          right-click menu + block keyboard — both remain entrances; the
          spine puts every scope's verbs in its Identity section so the
          panel reads the same at every grain, and it is still the one
          implementation behind three entrances). */}
      {/* ADR-528 D2 — RANGE scope: a text selection on a continuous surface.
          Collapsed (a caret) or spanning six paragraphs, it is the same scope;
          the count is the only thing that varies.

          This scope composes ONLY what a range can answer for. There is no
          verb row, no path, no Layout section and no Position — not because
          they are "withdrawn on the text tier" (ADR-525 D3's apparatus, now
          DELETED per D4) but because a range has no box and no single subject
          to hang them on. The previous shape reached this scope through
          `block` and then subtracted, which is why the pane matrix's
          block(text) column was a column of absences. */}
      {scope === 'range' && (
        <>
          <div className={SECTION}>
            {/* Name the SUBJECT honestly: over a multi-block range the block
                label names whichever block was clicked, not what the member
                has selected.

                A range reached WITHOUT a preceding click has no `selection` at
                all (the 2026-08-06 entrance fix), so the last fallback says
                "Selection" rather than the kind-shaped placeholder "text" —
                which would have named a kind nothing had reported. */}
            <p className={HEADING}>
              {multiBlockRange
                ? `${rangeBlockIds!.length} blocks selected`
                : (selection?.label ?? selection?.blockKind ?? 'Selection')}
            </p>
            {/* ADR-526 D2 — the enclosing-heading crumb, flow's one honest
                ancestry rung. Names ONE block's ancestor, so it withdraws over
                a multi-block range. */}
            {!multiBlockRange && headingRow}
          </div>
          {/* ADR-527 D4 — the TEXT section. Under ADR-528 this is the PRIMARY
              section of range scope rather than a guest in a block scope:
              every control in it acts on the SELECTION (ADR-521 D2's text
              tier), which is exactly what the member has, at any span. */}
          <TextSection
            onFormat={onFormat}
            swatch={swatchOf}
            flowTokens={flowTokens}
            currentOf={(key) => selectedEl?.getAttribute(`data-${key}`) ?? null}
            onSetToken={(key, v) => onSetToken('block', key, v)}
          />
          {/* The STRUCTURE tier (rule 10's second axis): the ramp and turn-into
              address the BLOCKS the range intersects, not the range itself.
              Over a single block — the overwhelmingly common case, since a
              caret is a collapsed range — that block is unambiguous and both
              render.

              ADR-541 D3 — over a MULTI-block range they now mount too, and
              the op takes every covered block as ONE revision (convertBlocks
              / setTokenMany — the surface expands; per-block legality stays
              per-block, so a citation island in the span is skipped, never a
              whole-range veto). This pays ADR-528's owed "span-aware
              structure ops": both benchmarks apply block-grain transforms
              across a selection, and the old withdrawal notice delivered
              neither. The one remaining single-subject row here is the
              heading crumb above — informational, and a span has no one
              enclosing heading to name. */}
          {rampSection}
          {turnIntoSection}
        </>
      )}
      {scope === 'object' && (
        <>
          {/* Identity — the operator-word kind + the ancestor path + verbs.
              A figure, table, chart, gallery or divider: these ARE boxes, and
              on a paged medium every block is one. */}
          <div className={SECTION}>
            {/* ADR-519 D4.1 — name the SUBJECT honestly. Over a ⇧-click set the
                block label names whichever block is the primary, not what the
                member has selected: the same staleness `d878242` found on flow,
                at the object tier. The count is the only honest label a set
                has — a set carries no label, no box and no tier of its own. */}
            <p className={HEADING}>
              {multiObject
                ? `${groupIds!.length} objects selected`
                : (selection?.label ?? selection?.blockKind ?? 'block')}
            </p>
            {/* Single-subject rows: the path names ONE ancestry, the verbs act
                on ONE id. Both withdraw over a set rather than answering for
                the primary while the member is looking at five. */}
            {!multiObject && pathRow}
            {!multiObject && headingRow}
            {!multiObject && (
              <VerbRow
                noun={selection?.label ?? 'block'}
                onVerb={onElementVerb}
                // ADR-525 follow-up: on FLOW the move verbs are withheld even
                // for objects — the menu already refused them there and the
                // pane must say the same thing. `moveBlock` still reaches a
                // flow block through ⌥↑/⌥↓ (the structure-tier keyboard door);
                // what is refused here is the ENCLOSURE presentation of it.
                reorder={mode !== 'flow'}
              />
            )}
          </div>
          {/* ADR-519 D4.1 — ALIGN / DISTRIBUTE: the one section whose subject
              genuinely IS the set, which is exactly why it earns a mount here
              while every single-subject section withdraws. It appears only when
              the set has more than one member, and it writes through the
              existing `setGeometryMany` — one gesture, one revision, no new op
              (ADR-462 D1). Distribute needs three to mean anything: with two,
              "even spacing between them" is just their current spacing. */}
          {multiObject && (onAlignMany || onDistributeMany) && (
            <div className={SECTION}>
              <p className={HEADING}>Align</p>
              {onAlignMany && (
                <div className="flex gap-1">
                  {ALIGN_MANY.map((a) => (
                    <button
                      key={a.key}
                      type="button"
                      title={a.title}
                      aria-label={a.title}
                      onClick={() => onAlignMany(a.key)}
                      className="rounded border border-border px-1.5 py-0.5 text-muted-foreground transition-colors hover:bg-muted/40"
                    >
                      <a.Icon className="h-3.5 w-3.5" />
                    </button>
                  ))}
                </div>
              )}
              {onDistributeMany && (groupIds?.length ?? 0) > 2 && (
                <div className="mt-1 flex gap-1">
                  {DISTRIBUTE_MANY.map((d) => (
                    <button
                      key={d.key}
                      type="button"
                      title={d.title}
                      aria-label={d.title}
                      onClick={() => onDistributeMany(d.key)}
                      className="rounded border border-border px-1.5 py-0.5 text-muted-foreground transition-colors hover:bg-muted/40"
                    >
                      <d.Icon className="h-3.5 w-3.5" />
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
          {/* Say WHY the rest is gone, rather than going quietly empty — the
              `d878242` lesson: a pane that withdraws silently reads as broken,
              and one that answers for the primary reads as correct while being
              stale. Neither is acceptable; saying so is the fix. */}
          {multiObject && (
            <div className={SECTION}>
              <p className="text-[10px] text-muted-foreground">
                Align and distribute apply to everything selected. Identity,
                position, layout and style apply to one object at a time.
              </p>
            </div>
          )}
          {/* Position (ADR-511 D4) — an explicit, visible, reversible state.
              Flow is the default; dragging is what enters the positioned
              state; "In flow" is the reversal. Shown on every STAGED block so
              the state is legible before it surprises. ADR-485 D4 unchanged:
              the kernel rule requires BOTH x and y — read the state the
              kernel reads. X/Y readback (ADR-519 Phase A): the drag's numeric
              receipt; entry lands in Phase C. */}
          {!multiObject && !!selectedEl?.closest('.slide') && (() => {
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
                {positioned && posMeasures.length > 0 && (
                  <div className="space-y-0.5">
                    {/* ADR-520 D3 — X/Y as editable fields (two-clamp, the
                        keyboard beside the drag). "In flow" stays the clear. */}
                    {posMeasures.map((m) => (
                      <MeasureField
                        key={m.key}
                        m={m}
                        value={measureValue(m)}
                        onCommit={(v) => onSetMeasure(m.key as 'x' | 'y', v)}
                      />
                    ))}
                  </div>
                )}
                <p className="text-[10px] text-muted-foreground">
                  {positioned
                    ? 'Dragged to a point on this slide — it no longer follows the layout. "In flow" returns it.'
                    : 'Follows the slide’s layout. Drag the block on the canvas to position it freely.'}
                </p>
              </div>
            );
          })()}
          {/* Layout — the non-colour block tokens (size/align; media add
              height/fit) + the W/H size readback (ADR-485 follow-on), one
              section per the spine. Palette-backed tokens are NOT here — they
              live in Style, and `nonColorTokens` is their complement, so
              every token still renders exactly once.

              ADR-528 D4: the `!isTextTier && !multiBlockRange` guard is DELETED,
              not re-gated. Width Hug|Fill is a CONTAINER row (ADR-516 D4) and
              flow has no containers by derivation (ADR-481 D1); a paragraph in
              a continuous surface has no box to size or align. That is
              AUTHORING.md rule 10's "no layout surface" — and under D2 a range
              cannot reach this scope at all, so the suppression it needed is
              unreachable. A guard behind a scope that cannot be entered is dead
              code that reads as live policy. Objects (a figure) keep the
              section: they ARE boxes. */}
          {!multiObject && (nonColorTokens.length > 0 || sizeMeasures.length > 0) && (
            <div className={SECTION}>
              <p className={HEADING}>Layout</p>
              {nonColorTokens.map((t) => (
                <TokenControl
                  key={t.key}
                  token={t}
                  current={selectedEl?.getAttribute(`data-${t.key}`) ?? null}
                  onSet={(v) => onSetToken('block', t.key, v)}
                />
              ))}
              {/* ADR-520 D3 — W/H as editable fields (two-clamp; emptying
                  the field is the Auto reset). The corner drag still works;
                  this is its keyboard twin. */}
              {sizeMeasures.map((m) => (
                <MeasureField
                  key={m.key}
                  m={m}
                  value={measureValue(m)}
                  onCommit={(v) => onSetMeasure(m.key as 'w' | 'h', v)}
                  onClear={() => onClearMeasure(m.key as 'w' | 'h')}
                />
              ))}
            </div>
          )}
          {!multiObject && rampSection}
          {/* COLOUR sits directly under TYPOGRAPHY — the two shaping questions a
              member asks in sequence ("how big / what role", then "what colour"),
              so they belong adjacent rather than separated by the structural
              verbs. Rendered as a laid-out SWATCH ROW: unlike the type ramp,
              a palette's whole content is legible at a glance, so a dropdown
              would hide behind a click exactly what it could have shown.
              Palette-backed tokens are lifted here; every other token keeps its
              existing home below, so this is a RELOCATION of one control, not a
              second mount of it. */}
          {!multiBlockRange && !multiObject && colorTokens.length > 0 && (
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
          {!multiObject && turnIntoSection}
        </>
      )}

    </div>
  );
}
