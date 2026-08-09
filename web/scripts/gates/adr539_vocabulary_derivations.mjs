// Executing check of ADR-539 — the vocabulary declares behavior (FE half).
//
// Executes the REAL extracted bodies of the derivation helpers the ADR
// introduced (turnIntoTargets / headingLevels / isConvertible / kindTier)
// with a falsifier per claim. The Python twin
// (api/test_adr539_vocabulary_declares.py) owns the cross-language parity
// (registry ↔ static FE constants); this gate owns the FE derivations'
// actual behavior.
//
// Run from the REPO ROOT: node web/scripts/gates/adr539_vocabulary_derivations.mjs
import { readFileSync } from 'fs';

const pane = readFileSync('web/components/studio/StudioDesignTab.tsx', 'utf8');
const menu = readFileSync('web/components/studio/StudioBlockMenu.tsx', 'utf8');
const picker = readFileSync('web/components/studio/StudioCitablePicker.tsx', 'utf8');
const surface = readFileSync('web/components/studio/StudioSurface.tsx', 'utf8');
const ops = readFileSync('web/components/studio/artifactOps.ts', 'utf8');

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};

// Body extractor: from the signature's opening brace to the column-0 close.
function bodyOf(src, sig) {
  const i = src.indexOf(sig);
  if (i < 0) return null;
  // The function's OWN opening brace is the one followed by a newline — a
  // brace inside a TS generic in the signature (`Array<{ tag: ... }>`) is not.
  const open = src.indexOf('{\n', i);
  const close = src.indexOf('\n}', open);
  return src.slice(open + 1, close);
}

// ── 1. headingLevels + turnIntoTargets, EXECUTED ───────────────────────────
const hlBody = bodyOf(pane, 'export function headingLevels');
t('headingLevels exists', hlBody != null);
const headingLevels = new Function('rungs', hlBody);

const levels = headingLevels([1, 2, 3]);
t(
  'headingLevels derives the ramp from the rung set',
  levels.length === 3 && levels[0].tag === 'h1' && levels[2].label === 'Heading 3',
);
t('FALSIFIER: a widened rung set widens the ramp', headingLevels([1, 2, 3, 4]).length === 4);

const titBody = bodyOf(pane, 'export function turnIntoTargets')
  .replace(/const out: Array<\{[^}]*\}> = \[\];/, 'const out = [];');
t('turnIntoTargets body is extractable (TS annotation stripped)', !titBody.includes(': Array<'));
const turnIntoTargets = new Function(
  'blocks',
  'headingRungs',
  'currentKind',
  'currentTag',
  'headingLevels',
  titBody,
);

// A registry-shaped fixture: convertible declared per row, exactly as served.
const BLOCKS = [
  { kind: 'heading', label: 'Heading', fragment: '<h2/>', convertible: true },
  { kind: 'prose', label: 'Text', fragment: '<p/>', convertible: true },
  { kind: 'quote', label: 'Quote', fragment: '<blockquote/>', convertible: true },
  { kind: 'component', label: 'Component', fragment: '<div/>', convertible: false },
  { kind: 'figure', label: 'Image', fragment: '<figure/>', convertible: false },
];
const targets = turnIntoTargets(BLOCKS, [1, 2, 3], 'quote', null, headingLevels);
const keys = targets.map((x) => x.key);
t(
  'a non-convertible row is NEVER offered (component/figure absent)',
  !keys.includes('component') && !keys.includes('figure'),
);
t(
  'heading expands to one target per rung',
  keys.filter((k) => k.startsWith('heading-')).join(',') === 'heading-h1,heading-h2,heading-h3',
);
t('the current kind is excluded (a no-op row is noise)', !keys.includes('quote'));
t('convertible rows survive in served order', keys.includes('prose'));
// FALSIFIER — flip component's declaration: the offer must follow the row.
const flipped = turnIntoTargets(
  BLOCKS.map((b) => (b.kind === 'component' ? { ...b, convertible: true } : b)),
  [1, 2, 3],
  'quote',
  null,
  headingLevels,
);
t(
  'FALSIFIER: declaring component convertible OFFERS it (the row decides)',
  flipped.map((x) => x.key).includes('component'),
);

// ── 2. isConvertible + kindTier, EXECUTED ──────────────────────────────────
const icBody = bodyOf(pane, 'export function isConvertible');
const isConvertible = new Function('blocks', 'kind', icBody);
t(
  'isConvertible reads the row (true/false/absent → false)',
  isConvertible(BLOCKS, 'prose') === true &&
    isConvertible(BLOCKS, 'figure') === false &&
    isConvertible(BLOCKS, 'nope') === false &&
    isConvertible(null, 'prose') === false,
);

const ktBody = bodyOf(pane, 'export function kindTier');
const kindTier = new Function(
  'blocks',
  'kind',
  'TEXT_BLOCK_KINDS',
  ktBody.replace(/\(TEXT_BLOCK_KINDS as readonly string\[\]\)/, 'TEXT_BLOCK_KINDS'),
);
const TIERED = [
  { kind: 'prose', tier: 'text' },
  { kind: 'figure', tier: 'object' },
];
t(
  'kindTier prefers the SERVED tier',
  kindTier(TIERED, 'prose', []) === 'text' && kindTier(TIERED, 'figure', []) === 'object',
);
t(
  'kindTier falls back to the pinned static copy only without a vocabulary',
  kindTier(null, 'prose', ['prose']) === 'text' && kindTier(null, 'metrics', ['prose']) === 'object',
);

// ── 3. Wiring: the derivations are the ONLY source (no resurrected lists) ──
const stripComments = (s) => s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|\s)\/\/[^\n]*/g, '$1');
t(
  'the hand-lists stay deleted (TURN_INTO_KINDS / PICKER_KINDS / CSV_KINDS)',
  !/TURN_INTO_KINDS\s*=/.test(stripComments(pane)) &&
    !/PICKER_KINDS\s*=/.test(stripComments(picker)) &&
    !/CSV_KINDS\s*=/.test(stripComments(picker)),
);
t(
  'the menu and the pane consult ONE convertibility source',
  menu.includes('isConvertible(blocks, target.blockKind)') &&
    pane.includes('isConvertible(vocabulary?.blocks, selection.blockKind)'),
);
t(
  'the picker branches on cites, not on a kind list',
  picker.includes("cites === 'source' ? c.tables : c.images") &&
    surface.includes('cites={citePicker.cites}'),
);
t(
  'the normalize seam clamps out-of-rung headings before promotion',
  /Pass A0[\s\S]*OUT_OF_RUNG_TAGS\.join\(','\)[\s\S]*Pass A —/.test(ops),
);

console.log(`\n${pass}/${pass + fail} passed`);
process.exit(fail === 0 ? 0 : 1);
