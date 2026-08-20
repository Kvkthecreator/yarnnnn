// Executing check of ADR-553 — the file set, and the way out of it.
//
// WHAT THIS GATE IS REALLY FOR: the ESCAPE HATCHES, not the selection.
//
// ADR-519 shipped an inescapable multi-selection to production once. That is
// the named risk this phase inherited, and it is why withdrawal is part of the
// feature rather than a follow-up. A gate that only checked "can you select
// two files" would have passed on the broken version too — the trap was never
// in the entering, it was in the leaving.
//
// So the assertions below are weighted toward LEAVING: Escape · an explicit
// Clear · a plain click replacing the set · a single-target verb ending it.
//
// ── RECUT 2026-08-20 (the selection model) ─────────────────────────────────
//
// Two of this ADR's decisions are SUPERSEDED, and this gate follows the code:
//
//  · D1 made ⌘/Ctrl-click the ONLY way into a multi-selection, on accident-
//    prevention grounds. That reasoning held only because a plain click was
//    DESTRUCTIVE — it navigated the surface into an app. A plain click is now
//    inert (it selects and renders nothing new), so plain-click-to-select is
//    safe and expected, and shift-click ranges. The "no way in but the
//    modifier" assertion is therefore GONE — keeping it would gate a rule the
//    system deliberately withdrew.
//
//  · D2's "a SET carried BESIDE the selection, never replacing it" (ADR-519
//    D4.1 inherited) is DELETED with the primary it was carried beside.
//    `selectedPath` + `alsoSelected` + `selectionSet` are one first-class
//    `selection` set. The assertions that pinned the primary-plus-extras shape
//    are replaced by their PURPOSE: whatever the shape, the count must be
//    RENDERED (a set the member cannot see they are in is the ADR-541 D4
//    computed-never-mounted failure) and the bulk picker must name the SET
//    rather than borrowing a member's name.
//
// ── RECUT 2026-08-20, SECOND CUT (two panes, two grammars) ────────────────
//
// The morning's recut applied ONE grammar to BOTH panes. That was the error:
// the LEFT TREE is a NAVIGATOR (folders only, one click navigates — Explorer
// and Finder both), and the CENTRE PANE is the FILE BROWSER. The selection
// model bled into the navigator, which is how the operator met the floating
// Move…/Open/Clear chip: beside Properties, raised by clicking a FILE IN THE
// TREE.
//
// Two more assertions follow the code rather than freezing withdrawn behaviour:
//
//  · The tree's modifier-forwarding and its "a selection click must not also
//    toggle disclosure" carve are GONE. Both existed only because the tree
//    carried a selection. It carries none, so there are no modifiers to forward
//    and no fight over one click. They are REPLACED by the claim that actually
//    holds now: the tree renders no file nodes and takes no selection.
//
//  · EXIT 2's "visible Clear" MOVED rather than vanished. The chip is deleted,
//    but ADR-519's lesson is that withdrawal is part of the feature — so the
//    visible exit is now "Deselect" in the background canvas menu, which is
//    where Finder puts it. This gate follows it there, and would go red if it
//    were simply dropped.
//
// D2's mover (sequential, honest about partial failure) and D3's exits stand
// unchanged and are the bulk of what remains. The full grammar is gated in
// api/test_files_selection_model.py; this file keeps the ADR's own claims.
//
// Run from the REPO ROOT: node web/scripts/gates/adr553_multi_select.mjs
import { readFileSync } from 'fs';

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};

const strip = (s) =>
  s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:])\/\/[^\n]*/g, '$1');

const page = strip(readFileSync('web/app/(authenticated)/files/page.tsx', 'utf8'));
const hook = strip(readFileSync('web/hooks/useFileOrganizeVerbs.tsx', 'utf8'));
const tree = strip(readFileSync('web/components/workspace/WorkspaceTree.tsx', 'utf8'));
const viewer = strip(readFileSync('web/components/workspace/ContentViewer.tsx', 'utf8'));

// ═══════════════════════════════════════════════════════════════════════════
// D1 (RECUT) — the set is FIRST-CLASS state, and the modifier still reaches it.
// The "only by modifier" clause is withdrawn (see the header); what survives is
// that the set is real state and that the tree does not swallow the modifiers
// on the way to the surface.
// ═══════════════════════════════════════════════════════════════════════════
t(
  'the set is first-class state (not a primary plus extras)',
  /const \[selection, setSelection\] = useState<string\[\]>\(\[\]\)/.test(page) &&
    !/alsoSelected|selectionSet/.test(page),
);
// SECOND RECUT: the two tree assertions that stood here are replaced.
//
// They were "the tree forwards the modifiers rather than swallowing them" and
// "a SELECTION click does NOT also toggle folder disclosure". Both were about a
// tree that carried a selection. It does not — so keeping them would gate
// behaviour the system deliberately withdrew, and the second would gate a
// conflict (set-gesture vs browse-gesture over one click) that no longer has
// two parties to it.
//
// What replaces them is the claim the withdrawal rests on: NOTHING IN THE TREE
// IS SELECTABLE, because nothing in it is a file. Asserted on the recursive
// filter — the construct that makes it true — because an absence cannot prove
// a branch is gone, only that one spelling of it is.
const foldersOnly = tree.match(
  /function foldersOnly\(nodes: WorkspaceTreeNode\[\] \| undefined\): WorkspaceTreeNode\[\] \{[\s\S]*?\n\}/,
);
t(
  'D1 [FALSIFIER]: the tree renders FOLDERS ONLY, at every depth',
  !!foldersOnly &&
    /n\.type === 'folder'/.test(foldersOnly[0]) &&
    /children: foldersOnly\(n\.children\)/.test(foldersOnly[0]) &&
    /foldersOnly\(nodes\)/.test(tree),
);
t(
  'D1 [FALSIFIER]: the tree neither reads nor writes the selection',
  !/selection/.test(tree) &&
    !/selectedSet/.test(tree) &&
    !/FileClickIntent/.test(tree),
);

// ═══════════════════════════════════════════════════════════════════════════
// D3 — THE WAY OUT. Four independent exits; ADR-519's trap had none.
// Each is asserted separately because losing any one re-creates the trap in a
// different corner, and three surviving exits would still read as "fine".
// ═══════════════════════════════════════════════════════════════════════════
t(
  'the set has ONE clearing function',
  /const clearSelection = useCallback\(\(\) => \{ setSelection\(\[\]\); setAnchorPath\(null\); \}/.test(
    page,
  ),
);

// Exit 1 — Escape, and it must be armed at ANY size. The earlier shape armed it
// only past size 1; a selection of one is as much a state to get out of as a
// selection of nine, and it is now the state a plain click routinely produces.
const escHandler = page.match(
  /if \(selection\.length ([^)]*?)\) return;\s*const onKey = \(e: KeyboardEvent\) => \{\s*if \(e\.key === 'Escape'\) (\w+)\(\);/,
);
t(
  'D3 [FALSIFIER]: EXIT 1 — Escape clears the set, at any size',
  !!escHandler && escHandler[1].trim() === '=== 0' && escHandler[2] === 'clearSelection',
);

// Exit 2 — a visible, clickable exit. A keyboard-only exit is not an exit for
// someone who never learns the key.
//
// RE-ANCHORED: it used to be the chip's `onClick={clearSelection}`. The chip is
// deleted (a selection should look selected, not announce itself in a toolbar),
// so the visible exit moved to "Deselect" in the background canvas menu — the
// Finder home for it. Asserted at BOTH ends, the mount and the render, because
// either half alone leaves a control that is wired but never drawn (the
// ADR-541 D4 computed-never-mounted shape) or drawn but inert.
const canvas = strip(
  readFileSync('web/components/workspace/CanvasContextMenu.tsx', 'utf8'),
);
t(
  'D3 [FALSIFIER]: EXIT 2 — a visible Deselect is rendered and wired to the clearer',
  /onDeselect=\{clearSelection\}/.test(page) &&
    /selectionCount=\{selection\.length\}/.test(page) &&
    /onDeselect && selectionCount > 0/.test(canvas) &&
    /run\(onDeselect\)/.test(canvas),
);

// Exit 3 — a plain click REPLACES the whole selection (the set does not
// accumulate silently across unmodified clicks).
const selectOne = page.match(/const selectOne = useCallback\(\(path: string\) => \{[\s\S]*?\}, \[\]\);/);
t(
  'D3 [FALSIFIER]: EXIT 3 — a plain click replaces the set, never appends',
  !!selectOne && /setSelection\(\[path\]\)/.test(selectOne[0]),
);

// Exit 4 — a single-target verb ends the set. Without this a set built before
// a rename/move/trash outlives it and points at paths that no longer exist:
// the STALE half of the trap, arriving by a different door than Escape guards.
const afterMutate = page.match(/onAfterMutate:\s*\([^)]*\)\s*=>\s*\{[\s\S]*?\n    \},/);
t(
  'D3 [FALSIFIER]: EXIT 4 — a single-target mutation ends the set',
  !!afterMutate && /(clearSelection\(\)|selectOne\(newPath\))/.test(afterMutate[0]),
);

// Exit 5 (NEW with the selection model) — a click on the listing's empty ground
// clears. Escape serves the keyboard; this serves the hand already on the mouse.
t(
  'D3 [FALSIFIER]: EXIT 5 — a background click on the listing clears',
  /const onGroundClick/.test(viewer) &&
    /onClearSelection\?\.\(\)/.test(viewer) &&
    (viewer.match(/onClick=\{onGroundClick\}/g) || []).length >= 2,
);

// ═══════════════════════════════════════════════════════════════════════════
// D4.1 (RECUT) — ADR-519 D4.1's rule was "a set is STATE beside the selection,
// never a scope that replaces it", which existed to stop a set from becoming an
// invisible mode. The primary it was carried beside is gone; the PURPOSE is
// kept and stated as what it always defended:
//
//   the set must never decide WHAT IS RENDERED.
//
// That is now structural rather than conventional — the two are separate
// states, and only an OPEN moves the rendered one.
// ═══════════════════════════════════════════════════════════════════════════
t(
  'the set never decides what is rendered (two separate states)',
  /const \[viewPath, setViewPath\] = useState<string \| null>\(null\)/.test(page) &&
    /const viewNode = viewPath\s*\?/.test(page),
);
const clickBody = page.match(/const handleFileClick = useCallback\(([\s\S]*?)\n  \);/);
t(
  '[FALSIFIER]: the SELECT branch moves neither the view nor the drill-in',
  !!clickBody &&
    !/setViewPath/.test(clickBody[1]) &&
    !/activateBodyRef/.test(clickBody[1]),
);

// ═══════════════════════════════════════════════════════════════════════════
// D2 — the bulk verb is HONEST about partial failure.
// Moves are non-transactional per file (ADR-337 D3 writes then tombstones), so
// a set can half-land. Reporting a flat success over a partial move is the
// failure this guards.
// ═══════════════════════════════════════════════════════════════════════════
const many = hook.match(/const commitMoveMany = useCallback\([\s\S]*?\n  \);/);
t('D2: the set mover exists', !!many);
if (many) {
  t(
    'D2 [FALSIFIER]: it reports which half landed (moved AND failed)',
    /moved/.test(many[0]) && /failed/.test(many[0]),
  );
  t(
    'D2 [FALSIFIER]: it is SEQUENTIAL — parallel writes race on destination_exists',
    /for \(const/.test(many[0]) && !/Promise\.all/.test(many[0]),
  );
}
// FALSIFIER NOTE: a bare substring test did NOT catch removing the honest
// report from the MODAL Move, because the drag-a-group path declares the same
// message. Both set-taking sites must say it, so COUNT them — a floor, not a
// ceiling, so a third set-taking verb is not read as a violation.
t(
  'D2 [FALSIFIER]: EVERY set-taking site SAYS the partial result',
  /failed\.length/.test(page) &&
    (page.match(/Moved \$\{moved\.length\} of \$\{paths\.length\}\./g) || []).length >= 2,
);
t(
  'D2: the set reuses the SAME picker a single Move uses (no second grammar)',
  /<MoveToFolderModal/.test(page),
);
t(
  'D2 [FALSIFIER]: the picker names the SET, not a borrowed member name',
  /\$\{selection\.length\} files/.test(page),
);
t(
  'D2 [FALSIFIER]: the set-Move takes the WHOLE selection',
  (page.match(/const paths = selection;/g) || []).length >= 2,
);

// The set must be VISIBLE — a set the member cannot see they are in is the
// ADR-541 D4 computed-never-mounted shape.
//
// RE-ANCHORED with the chip's deletion. The chip rendered a `N selected` count
// beside Properties; the selection now says itself the way every file browser
// says it — THE ROWS RING. That is a stronger statement, not a weaker one: the
// count named a number, the rings name WHICH FILES.
//
// So the assertion follows the visibility to where it actually lives: every
// member of the set rings, in BOTH view modes (a set visible in the icon grid
// and invisible in the details list would be half a feature), and the COUNT is
// still spoken where a count is the honest unit — the bulk Move picker's target
// and the canvas menu's Deselect.
t(
  '[FALSIFIER]: every member of the set RINGS, in both view modes',
  (viewer.match(/selected=\{selectedSet\.has\(child\.path\)\}/g) || []).length >= 2,
);
t(
  '[FALSIFIER]: the count is SPOKEN where a count is the unit (bulk picker + Deselect)',
  /\$\{selection\.length\} files/.test(page) &&
    /Deselect \$\{selectionCount\} items/.test(canvas),
);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
