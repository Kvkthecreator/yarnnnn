// Executing check of ADR-552 — direct manipulation where members actually look.
//
// ADR-400 deferred this BY NAME: "Grid drag-drop remains a later fast-follow
// (tree is the primary folder-structure target)". It never followed. Drag lived
// only in the narrow left tree, files only — while the folder listing and the
// Recents grid, where files are actually looked at, carried ZERO `draggable`.
//
// WHAT THIS GATE DEFENDS. Not "drag exists" — that a rename or a refactor
// cannot silently make the two halves of one surface refuse each other's
// drags. The failure mode is specific and was live in the first draft of this
// change: the tree declared `const DRAG_MIME = 'application/x-yarnnn-path'`
// and the tile declared the same literal independently. Two spellings of one
// token, and a rename of either would break dragging ACROSS panes while every
// per-module test stayed green — the seam-between-correct-modules shape.
//
// Run from the REPO ROOT: node web/scripts/gates/adr552_grid_drag.mjs
import { readFileSync } from 'fs';

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};

// Strip comments before any ABSENCE assertion — an absence check otherwise
// matches its own explanatory comment (feedback_gate_assertion_matches_its_own_comment).
const strip = (s) =>
  s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:])\/\/[^\n]*/g, '$1');

const tile = readFileSync('web/components/workspace/FileTile.tsx', 'utf8');
const list = readFileSync('web/components/workspace/FileListView.tsx', 'utf8');
const tree = readFileSync('web/components/workspace/WorkspaceTree.tsx', 'utf8');
const viewer = readFileSync('web/components/workspace/ContentViewer.tsx', 'utf8');
const page = readFileSync('web/app/(authenticated)/files/page.tsx', 'utf8');

const tileCode = strip(tile);
const listCode = strip(list);
const treeCode = strip(tree);

// ═══════════════════════════════════════════════════════════════════════════
// ONE MIME TOKEN. The load-bearing invariant: the grid, the list and the tree
// must agree on the dataTransfer key, or a drag from one pane is invisible to
// another. Asserted as "declared ONCE and imported", not "the strings match" —
// matching strings is what the broken version also had.
// ═══════════════════════════════════════════════════════════════════════════
const declarations = [
  ['FileTile', tileCode],
  ['FileListView', listCode],
  ['WorkspaceTree', treeCode],
].filter(([, src]) => /=\s*['"]application\/x-yarnnn-path['"]/.test(src));

t(
  `the drag MIME is declared in exactly ONE module (found ${declarations.length}: ${declarations
    .map(([n]) => n)
    .join(', ') || 'none'})`,
  declarations.length === 1,
);
t(
  '…and it is the tile module that owns it',
  declarations.length === 1 && declarations[0][0] === 'FileTile',
);
t(
  '[FALSIFIER]: the list imports that token rather than re-declaring it',
  /import\s*\{[^}]*TILE_DRAG_MIME[^}]*\}/.test(listCode),
);
t(
  '[FALSIFIER]: the tree imports it too (cross-pane drags depend on this)',
  /import\s*\{[^}]*TILE_DRAG_MIME[^}]*\}/.test(treeCode),
);

// ═══════════════════════════════════════════════════════════════════════════
// THE GRID AND LIST ACTUALLY DRAG. ADR-400's deferral is closed.
// Both renderers must set the drag data AND accept a drop — a `draggable`
// attribute with no `onDragStart` looks right and does nothing.
// ═══════════════════════════════════════════════════════════════════════════
for (const [name, src] of [
  ['tile', tileCode],
  ['list row', listCode],
]) {
  t(`the ${name} can be picked up (draggable + onDragStart + setData)`,
    /draggable:\s*true/.test(src) &&
      /onDragStart/.test(src) &&
      /setData\(TILE_DRAG_MIME/.test(src));
  t(`the ${name} accepts a drop (onDragOver + onDrop + preventDefault)`,
    /onDragOver/.test(src) && /onDrop:/.test(src) && /preventDefault\(\)/.test(src));
  // The props must reach the rendered element — computed-but-never-spread is
  // the ADR-541 D4 shape (exported, never mounted) and ships green.
  t(`[FALSIFIER]: the ${name}'s drag props are SPREAD onto the element`,
    (src.match(/\{\.\.\.dragProps\}/g) || []).length >= 1 &&
      (src.match(/\{\.\.\.dropProps\}/g) || []).length >= 1);
}

// Both render branches (button mount and SurfaceLink mount) must carry them —
// a tile that drags in Files but not on the Home deep-link is half-shipped.
for (const [name, src] of [
  ['tile', tileCode],
  ['list row', listCode],
]) {
  t(`[FALSIFIER]: BOTH ${name} render branches carry the props`,
    (src.match(/\{\.\.\.dragProps\}/g) || []).length === 2);
}

// ═══════════════════════════════════════════════════════════════════════════
// THE TREE'S RULE, INHERITED — not re-invented.
// A FILE drags; a FOLDER receives. A folder is never draggable (there is no
// backend folder-move — folders are implicit in paths), and a file is never a
// drop target (dropping onto a file has no meaning).
// ═══════════════════════════════════════════════════════════════════════════
const viewerCode = strip(viewer);
const adapter = viewerCode.match(/function tileDnd\([\s\S]*?\n}/);
t('the listing derives per-row affordances in ONE place', !!adapter);
if (adapter) {
  const a = adapter[0];
  t('[FALSIFIER]: a FOLDER is not draggable (no backend folder-move)',
    /draggable:\s*!isFolder/.test(a));
  t('[FALSIFIER]: a FILE is not a drop target (only folders receive)',
    /droppable:\s*isFolder/.test(a));
  t('both sides consult the organize predicate',
    (a.match(/canOrganize\(/g) || []).length >= 2);
}

// ═══════════════════════════════════════════════════════════════════════════
// ONE MOVE PATH, ONE IMPORT PATH. The listing must reuse the handlers the tree
// already uses — a second mover would drift from the first (and would miss
// ADR-550's projection carry, which lives in the primitive below them).
// ═══════════════════════════════════════════════════════════════════════════
const pageCode = strip(page);
t('[FALSIFIER]: the listing reuses the tree\'s move handler (commitMove)',
  /onDropPath:\s*commitMove/.test(pageCode));
t('[FALSIFIER]: …and the same import path as the drop-on-folder gesture',
  /onDropFiles:\s*\(files,\s*folder\)\s*=>\s*openUpload\(files,\s*folder\)/.test(pageCode));
t('the listing highlight is its own state, not the tree\'s',
  /listingDropTarget/.test(pageCode) && /dropTarget/.test(treeCode));

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
