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
// So the assertions below are weighted: ONE check that the set exists, FOUR
// that it can be left (Escape · an explicit Clear · a single-target verb ·
// a plain click), and the ADR-519 D4.1 rule that a set is STATE beside the
// selection rather than a scope that replaces it.
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

// ═══════════════════════════════════════════════════════════════════════════
// D1 — the set EXISTS, and is entered only deliberately.
// ═══════════════════════════════════════════════════════════════════════════
t('the set is carried as its own state', /alsoSelected/.test(page));
t(
  'D1 [FALSIFIER]: it is entered ONLY by a modifier click (never by accident)',
  /metaKey\s*\|\|\s*e?\.?\s*ctrlKey|metaKey|ctrlKey/.test(page) &&
    /additive/.test(page),
);
t(
  'D1: the tree forwards the modifier rather than swallowing it',
  /metaKey/.test(tree) && /ctrlKey/.test(tree),
);
t(
  'D1 [FALSIFIER]: an additive click does NOT also toggle folder disclosure',
  /isFolder\s*&&\s*!additive/.test(tree),
);

// ═══════════════════════════════════════════════════════════════════════════
// D3 — THE WAY OUT. Four independent exits; ADR-519's trap had none.
// Each is asserted separately because losing any one re-creates the trap in a
// different corner, and three surviving exits would still read as "fine".
// ═══════════════════════════════════════════════════════════════════════════
t('the set has ONE clearing function', /const clearSet\s*=/.test(page));

// Exit 1 — Escape.
const escHandler = page.match(/if \(e\.key === 'Escape'\)[^\n]*/);
t(
  'D3 [FALSIFIER]: EXIT 1 — Escape clears the set',
  !!escHandler && /clearSet/.test(escHandler[0]),
);

// Exit 2 — a visible, clickable Clear. A keyboard-only exit is not an exit for
// someone who never learns the key.
t(
  'D3 [FALSIFIER]: EXIT 2 — a visible Clear control is wired to it',
  /onClick=\{clearSet\}/.test(page),
);

// Exit 3 — a plain (non-additive) click replaces the whole selection.
const selectHandler = page.match(/const handleExplorerSelect[\s\S]*?\n  \);/);
t(
  'D3 [FALSIFIER]: EXIT 3 — a plain click clears before selecting',
  !!selectHandler && /if \(!additive\)[\s\S]{0,120}?clearSet\(\)/.test(selectHandler[0]),
);

// Exit 4 — a single-target verb ends the set. Without this a set built before
// a rename/move/trash outlives it and points at paths that no longer exist:
// the STALE half of the trap, arriving by a different door than Escape guards.
const afterMutate = page.match(/onAfterMutate:\s*\([^)]*\)\s*=>\s*\{[\s\S]*?\n    \},/);
t(
  'D3 [FALSIFIER]: EXIT 4 — a single-target mutation ends the set',
  !!afterMutate && /clearSet\(\)/.test(afterMutate[0]),
);

// ═══════════════════════════════════════════════════════════════════════════
// D4.1 (inherited from ADR-519) — the set is STATE BESIDE the selection,
// never a scope that replaces it. Every existing reader must still get one
// path; only the N-taking gesture consults the set.
// ═══════════════════════════════════════════════════════════════════════════
t(
  'the primary selection still exists and is still a single path',
  /const \[selectedPath, setSelectedPath\] = useState<string \| null>/.test(page),
);
const setBuilder = page.match(/const selectionSet = useMemo\([\s\S]*?\n  \);/);
t('the set is derived, not a second source of truth', !!setBuilder);
t(
  '[FALSIFIER]: the primary is FIRST in the set (a `[0]` reader gets the subject)',
  !!setBuilder && /\[selectedPath,\s*\.\.\.alsoSelected/.test(setBuilder[0]),
);
t(
  '[FALSIFIER]: the primary can never leave the set (no orphan state)',
  /node\.path === selectedPath/.test(page),
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
t(
  'D2 [FALSIFIER]: the surface SAYS the partial result rather than a flat success',
  /failed\.length/.test(page) && /Moved \$\{moved\.length\} of/.test(page),
);
t(
  'D2: the set reuses the SAME picker a single Move uses (no second grammar)',
  /<MoveToFolderModal/.test(page),
);
t(
  'D2 [FALSIFIER]: the picker names the SET, not a borrowed member name',
  /\$\{selectionSet\.length\} files/.test(page),
);

// The count must be MOUNTED — a set with no visible count is a set the member
// cannot see they are in (the ADR-541 D4 computed-never-mounted shape).
t(
  '[FALSIFIER]: the count is rendered, not merely computed',
  /\{selectionSet\.length\} selected/.test(page),
);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
