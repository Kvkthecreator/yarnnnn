// Executing check of ADR-519 D4's modifier split — ⇧ multi-select, ⌘ deep-select.
//
// The defect this closes: the click handler read `shift || meta || ctrl` as ONE
// branch, three modifiers doing one job. Only ⇧ was ever argued for (the
// comment above it justifies shift alone, and names flow's range-selection as
// the reason); ⌘ was swept in incidentally and never chosen. Meanwhile ADR-519
// D4 assigned ⌘ to deep-select — so the ADR gave one key two jobs without
// noticing, and §2.4's gap (a container fully tiled by its children is
// unreachable by click) stayed open because the branch that owned ⌘ returned
// before the grain ladder ever ran.
//
// The resolution is convention, not invention: every reference tool separates
// them — ⇧ adds to a selection (Figma, Keynote, PowerPoint, Illustrator,
// Finder) and ⌘ deep-selects (Figma, Illustrator, Sketch).
//
// EXECUTING, not grepping: the claim is about which branch a given modifier
// combination REACHES, and branch reachability is exactly what a spelling
// check cannot see. The two guards are extracted and run against real event
// shapes (the ADR-526 gate's pattern).
//
// Run from the REPO ROOT: node web/scripts/gates/adr519_modifier_split.mjs
import { readFileSync } from 'fs';

const proj = readFileSync('web/components/workspace/viewers/projection.ts', 'utf8');

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};

// ── The two guards, extracted from source and made runnable ───────────────
// Extract by the branch each guard OWNS (the group branch resolves gblk; the
// deep branch resolves dcont), NOT by the expected expression — pinning the
// spelling would make the gate fail at extraction under any mutation, so every
// behavioural check below would be skipped rather than RED. The guard
// expression itself is whatever the source says; the checks then run it.
const grab = (marker) => {
  const i = proj.indexOf(marker);
  if (i < 0) return null;
  const head = proj.lastIndexOf('if (', i);
  if (head < 0) return null;
  const expr = proj.slice(head + 4, proj.indexOf(') {', head));
  return { expr, fn: new Function('e', `return (${expr});`) };
};
const group = grab('var gblk = el && el.closest');
const deep = grab('var dcont = t && t.closest');
t('the group branch exists and its guard is runnable', !!group);
t('the deep-select branch exists as its OWN branch (not the same guard)', !!deep && deep.expr !== group?.expr);

const groupGuard = group?.fn;
const deepGuard = deep?.fn;

// ── 1. Each modifier reaches exactly ONE branch ───────────────────────────
if (groupGuard && deepGuard) {
  const ev = (m) => ({ shiftKey: false, metaKey: false, ctrlKey: false, ...m });

  const shift = ev({ shiftKey: true });
  t('⇧-click → group branch only', groupGuard(shift) && !deepGuard(shift));

  const meta = ev({ metaKey: true });
  t('⌘-click → deep-select branch only', deepGuard(meta) && !groupGuard(meta));

  const ctrl = ev({ ctrlKey: true });
  t('ctrl-click follows ⌘, not ⇧ (same intent across OS)', deepGuard(ctrl) && !groupGuard(ctrl));

  const plain = ev({});
  t('an unmodified click reaches NEITHER (the ladder still owns it)', !groupGuard(plain) && !deepGuard(plain));

  // The regression the split exists to prevent: ⌘ must no longer toggle group.
  t('⌘ no longer reaches the group branch (the defect)', !groupGuard(ev({ metaKey: true })));
  t('ctrl no longer reaches the group branch (the defect)', !groupGuard(ev({ ctrlKey: true })));

  // ⇧⌘ together: deep-select wins by ordering. Stated so the precedence is a
  // decision on the record rather than an accident of branch order.
  const both = ev({ shiftKey: true, metaKey: true });
  t('⇧⌘ is not silently dropped (some branch claims it)', groupGuard(both) || deepGuard(both));
}

// ── 2. The deep-select branch targets the CONTAINER grain ─────────────────
{
  const di = proj.indexOf('DEEP SELECT (ADR-519 D4)');
  t('the deep-select branch is documented at its site', di > 0);
  const body = proj.slice(di, proj.indexOf('ADR-453 D5: the click-grain ladder', di));
  t('deep-select resolves CONTAINER_SEL (the innermost container)', /closest\(CONTAINER_SEL\)/.test(body));
  t('deep-select does NOT target a page (ADR-519 D6 keeps pages out)', !/PAGE_SEL/.test(body));
  t('deep-select marks through the ADR-525 D2 chokepoint', /__yarnnnSelect\(dcont\)/.test(body));
  t("deep-select declares the tier rather than re-deriving it", /tier: tierOf\(dcont\)/.test(body));
  // One derivation, two entrances — the payload must be the SAME shape the
  // miss-branch container rung emits, or the pane reads two answers per grain.
  t('deep-select emits a yarnnn-point payload (not a second message type)', /type: 'yarnnn-point'/.test(body));
  // ADR-546 D5 — assert the payload's SHAPE (the keys the pane reads), never how
  // each value is spelled. This pinned `slot: dslot` and so read a NARROWING as a
  // violation when the region derivation moved to the one mode-aware `regionOf`
  // chokepoint — the exact failure ADR-544 hit three times. The contract is that
  // the container payload carries these four facts; where `slot` comes from is
  // `regionOf`'s business, and ADR-546's own gate is what defends its behaviour.
  t('deep-select carries blockId + label + slot + arrange (the container shape)',
    /blockId: dcont\.getAttribute/.test(body) &&
    /label: labelFor\(dcont\)/.test(body) &&
    /\bslot:/.test(body) &&
    /\barrange:/.test(body));
  t('deep-select returns before the ladder (a gesture, not a navigation)', /\breturn;/.test(body));
}

// ── 3. Every helper the branch calls is in scope ──────────────────────────
// A ReferenceError inside the runtime template is silent until click time —
// the build cannot catch it, so the gate must.
{
  const di = proj.indexOf('DEEP SELECT (ADR-519 D4)');
  const defs = {
    CONTAINER_SEL: proj.indexOf('var CONTAINER_SEL ='),
    tierOf: proj.indexOf('function tierOf('),
    arrangeOf: proj.indexOf('function arrangeOf('),
    slideIndexOf: proj.indexOf('function slideIndexOf('),
    pageIndexOf: proj.indexOf('function pageIndexOf('),
    labelFor: proj.indexOf("labelForJS('labelFor')"),
  };
  for (const [name, at] of Object.entries(defs)) {
    t(`${name} is defined BEFORE the deep-select branch uses it`, at > 0 && at < di);
  }
}

// ── 4. Runtime hygiene — a literal backtick would close the template ──────
// The ADR-521 gate owns this for the whole file; asserted here too because
// this gate's own subject is a block of NEW comment prose inside that template.
{
  const di = proj.indexOf('GROUP click (2026-07-24)');
  const region = proj.slice(di, proj.indexOf('ADR-453 D5: the click-grain ladder', di));
  t('no literal backtick in the modifier-branch prose', !region.includes('`'));
}

console.log(`\n${pass}/${pass + fail} checks passed`);
process.exit(fail ? 1 : 0);
