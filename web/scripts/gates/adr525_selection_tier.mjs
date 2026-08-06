// Executing check of ADR-525 — the selection carries its tier.
//
// The claim under test: ONE declaration (the runtime's `tierOf`) is read by
// every surface, so the pane, the menu and the keyboard cannot answer one block
// three ways. This gate executes the REAL bodies (extracted from source, never
// re-typed) and carries a falsifier per claim — a gate that cannot fail is not
// a gate.
//
// Run from the REPO ROOT: node web/scripts/gates/adr525_selection_tier.mjs
import { readFileSync } from 'fs';

const proj = readFileSync('web/components/workspace/viewers/projection.ts', 'utf8');
const pane = readFileSync('web/components/studio/StudioDesignTab.tsx', 'utf8');
const menu = readFileSync('web/components/studio/StudioBlockMenu.tsx', 'utf8');
const studio = readFileSync('api/services/studio.py', 'utf8');

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};

// ── 1. D1 — the tier derivation, executed ──────────────────────────────────
const tierIdx = proj.indexOf('function tierOf(el) {');
if (tierIdx === -1) {
  console.error('[FAIL] tierOf() not found — ADR-525 D1 is not implemented');
  process.exit(1);
}
const tierBody = proj.slice(proj.indexOf('{', tierIdx) + 1, proj.indexOf('\n  }', tierIdx));
const TEXT_KINDS = ['prose', 'callout', 'quote', 'checklist', 'toggle', 'heading'];

function tierOf(flow, blockKind) {
  const el = { getAttribute: (k) => (k === 'data-block' ? blockKind : null) };
  const win = { __yarnnnFlowMode: () => flow };
  return new Function('window', 'TEXT_KINDS', 'el', `${tierBody}`)(win, TEXT_KINDS, el);
}

// On FLOW, prose is text — the caret speaks for it.
t("D1: prose on flow  → 'text'", tierOf(true, 'prose') === 'text');
t("D1: heading on flow → 'text'", tierOf(true, 'heading') === 'text');
t("D1: callout on flow → 'text'", tierOf(true, 'callout') === 'text');
// Objects are objects in BOTH media — nothing else can speak for them.
t("D1: figure on flow  → 'object'", tierOf(true, 'figure') === 'object');
t("D1: table on flow   → 'object'", tierOf(true, 'table') === 'object');
t("D1: divider on flow → 'object'", tierOf(true, 'divider') === 'object');
// On PAGED every block is an enclosure (ADR-480 D1) — prose included.
t("D1: prose on paged   → 'object' (the enclosure grain)", tierOf(false, 'prose') === 'object');
t("D1: heading on paged → 'object'", tierOf(false, 'heading') === 'object');
// No data-block at all = a container/page.
t("D1: a container → 'structure'", tierOf(true, null) === 'structure');
t("D1: a page on paged → 'structure'", tierOf(false, null) === 'structure');

// FALSIFIER: drop the medium term; prose on flow would read as an object and
// the whole ADR collapses back to the medium-blind shape it replaced.
const noMedium = tierBody.replace(
  /var flow = window\.__yarnnnFlowMode \? window\.__yarnnnFlowMode\(\) : false;/,
  'var flow = false;',
);
const falsified1 = (() => {
  const el = { getAttribute: (k) => (k === 'data-block' ? 'prose' : null) };
  return new Function('window', 'TEXT_KINDS', 'el', noMedium)(
    { __yarnnnFlowMode: () => true },
    TEXT_KINDS,
    el,
  );
})();
t("FALSIFIER: without the medium term prose on flow reads 'object'", falsified1 === 'object');

// ── 2. D1 — the tier is STAMPED on every payload a consumer reads ──────────
// A declaration nothing carries is not a declaration. Count the point emitters
// and assert each one stamps a tier.
const pointEmitters = [...proj.matchAll(/type: 'yarnnn-point',/g)].length;
const tierStamps = [...proj.matchAll(/tier: /g)].length;
t(
  `D1: every yarnnn-point emitter stamps a tier (${pointEmitters} emitters, ${tierStamps} stamps)`,
  tierStamps >= pointEmitters,
);
// Scoped to the payload literal itself (from the type key to its closing
// `}, '*')`) rather than a fixed character window — a comment or a new field
// must not be able to push the stamp out of range and report a false failure.
const ctxStart = proj.indexOf("type: 'yarnnn-context-menu',");
const ctxPayload = ctxStart === -1 ? '' : proj.slice(ctxStart, proj.indexOf("}, '*');", ctxStart));
t(
  'D1: the context-menu payload carries the tier too (D5 reads it)',
  /\btier: /.test(ctxPayload),
);

// ── 3. D1 — ONE kind list, shared. Never two copies. ──────────────────────
t(
  'D1: TEXT_BLOCK_KINDS is exported for the FE fallback',
  /export const TEXT_BLOCK_KINDS/.test(proj),
);
t(
  'D1: the runtime derives its injected list FROM that export (no second copy)',
  /const TEXT_KINDS_JS = JSON\.stringify\(TEXT_BLOCK_KINDS\)/.test(proj),
);
t(
  'D1: the pane imports the shared list rather than re-enumerating it',
  /import \{ TEXT_BLOCK_KINDS \}/.test(pane) &&
    !/'prose',\s*'callout',\s*'quote'/.test(pane),
);

// ── 4. D3 — the pane composes by tier ─────────────────────────────────────
t('D3: the pane derives isTextTier from the declaration', /const isTextTier =/.test(pane));
t(
  'D3: the pane READS selection.tier (never re-derives the rule)',
  /selection\.tier \?\?/.test(pane),
);
// ADR-528 D2/D4 RE-CUT (2026-08-06) — the INTENT is preserved, the mechanism
// changed. These two assertions pinned SUPPRESSION: `{!isTextTier && (<VerbRow`
// and the same guard on Layout. ADR-528 made the text tier its own scope
// (`range`), so those sections are no longer composed for prose at all and the
// suppression guards were DELETED as dead code (a guard behind an unreachable
// scope reads as live policy).
//
// The invariant D3 actually protects — prose never gets the enclosure grammar —
// is now stronger and is asserted here by NON-COMPOSITION: the verb row and the
// Layout section live inside the `object` branch, and a text-tier selection
// cannot reach it. `adr528_range_scope.mjs` proves the derivation EXECUTES that
// way over the full payload×tier matrix; these two pin the structural half.
const rangeBranch = pane.match(/\{scope === 'range' && \(([\s\S]*?)\n\s*<\/>/);
const objectBranch = pane.match(/\{scope === 'object' && \(([\s\S]*?)\n\s*<\/>/);
t('D3 (re-cut): the pane has a distinct range branch', !!rangeBranch);
t('D3 (re-cut): the pane has a distinct object branch', !!objectBranch);
t(
  'D3 (re-cut): the verb row is composed for OBJECT only — prose cannot reach it',
  !!objectBranch && /<VerbRow/.test(objectBranch[1]) &&
    (!rangeBranch || !/<VerbRow/.test(rangeBranch[1])),
);
t(
  'D3 (re-cut): the Layout section is composed for OBJECT only',
  !!objectBranch && /nonColorTokens\.length > 0/.test(objectBranch[1]) &&
    (!rangeBranch || !/nonColorTokens\.length > 0/.test(rangeBranch[1])),
);
// The tiers that must be UNTOUCHED — Studio's pane is byte-identical (D3).
t(
  'D3: Typography survives (turn-into by another door, ADR-487 D3)',
  /label="Typography"/.test(pane),
);
t('D3: Turn into survives (structure tier, ADR-521 D2)', /Turn into/.test(pane));

// ── 5. D5 — the menu reads the SAME field ────────────────────────────────
t('D5: the menu derives its tier from the target', /const isTextTier = target\.tier === 'text'/.test(menu));
t(
  'D5: Duplicate/Delete are withheld on the text tier',
  /\{!isTextTier && \([\s\S]{0,400}?Duplicate[\s\S]{0,300}?Delete/.test(menu),
);
// The pane-vs-menu contradiction this ADR closes: BOTH now gate on one field.
t(
  'D5: the pane and the menu gate on the same declared field',
  /isTextTier/.test(pane) && /isTextTier/.test(menu),
);

// ── 6. D4 — the registry gained the term and re-keyed the two tokens ──────
t('D4: block-flow enters the applies vocabulary', /"block-flow":/.test(studio));
t(
  'D4: `size` no longer claims the widest grain',
  /"size": \{\s*"label": "Width",\s*"applies": \["block-staged", "media"\]/.test(studio),
);
// ADR-527 D3 AMENDED this row: `align` gained `block-flow`, because the kernel
// rule is `text-align` — arrangement of prose in its own measure, which a flow
// block has. ADR-525 D4 had applied `size`'s reasoning to it by adjacency.
//
// The assertion's INTENT is unchanged and is what is pinned: align must not
// claim the WIDEST grain (bare "block", which is what made a Docs paragraph
// render a layout row). Which narrow grains it names is the amendable part —
// pinning the exact list would have made a legitimate amendment look like a
// regression, which is the "don't pin a spelling" lesson one level up.
t(
  'D4: `align` no longer claims the widest grain (narrow grains only)',
  /"align": \{\s*"label": "Align",\s*"applies": \[(?![^\]]*"block")[^\]]*\]/.test(studio) ||
    /"align": \{\s*"label": "Align",\s*"applies": \["block-staged", "media", "block-flow"\]/.test(studio),
);
t(
  'D4 (as amended by ADR-527 D3): align reaches flow through block-flow, never bare block',
  /"align": \{\s*"label": "Align",\s*"applies": \[[^\]]*"block-flow"[^\]]*\]/.test(studio) &&
    !/"align": \{\s*"label": "Align",\s*"applies": \[[^\]]*"block"[,\]]/.test(studio),
);
t(
  'D4: the pane gates TOKENS on block-staged (not only measures)',
  /isStaged && t\.applies\.includes\('block-staged'\)/.test(pane),
);

// ── 7. The follow-up (2026-08-06) — the OBJECT tier's half of the same law ─
// D3 withdrew the whole verb row on the text tier and declared the object tier
// "untouched" — which closed the pane-vs-menu contradiction for prose and
// PRESERVED it for figures: the pane offered Move up/down on a figure in a Docs
// artifact while StudioBlockMenu refused the same verbs on the same block (it
// gates on isPaged, not on tier). Same fault pattern, one tier over.
t(
  'follow-up: VerbRow can withhold the MOVE verbs alone (not only the whole row)',
  /reorder = true/.test(pane) && /\{reorder && \(/.test(pane),
);
t(
  'follow-up: the block scope withholds move on FLOW (matching the menu)',
  /reorder=\{mode !== 'flow'\}/.test(pane),
);
// FALSIFIER: an always-true reorder gate re-opens the contradiction.
t(
  'FALSIFIER: an ungated reorder prop would NOT match the flow test',
  !/reorder=\{true\}/.test(pane),
);
// The menu's side of the same law, pinned so the two cannot drift apart again.
t(
  'follow-up: the menu still refuses move on flow (the rule the pane now matches)',
  /hasBlock && isPaged/.test(menu),
);

console.log(`\nADR-525: ${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 1 - 1 : 1);
