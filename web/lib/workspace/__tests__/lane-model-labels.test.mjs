/**
 * The FE attribution mirror must not drift from LANE_MODELS, and every label
 * must carry its version.
 *
 * WHY THIS GATE EXISTS. `web/lib/workspace/attribution.ts` duplicates all 12
 * `LANE_MODELS` rows as a last-resort map for attribution strings. It is a
 * deliberate mirror (the FE cannot import Python), and it HAD ALREADY DRIFTED:
 * `anthropic/claude-haiku-4-5-20251001` read 'Claude Haiku' on the FE while
 * lane_runner.py said 'Claude Haiku (4.5)', so one id rendered two different
 * names depending on which path drew it. Nothing failed; it just quietly lied.
 *
 * The version rule (2026-08-21): a label is written into every revision's
 * attribution string AND told to the model as "You are {label}". Two engines
 * sharing a label makes the ledger unreadable — which is exactly what
 * 'Claude Sonnet' did for both the retired 4-6 and the live 5.
 *
 * Run: node web/lib/workspace/__tests__/lane-model-labels.test.mjs
 * (from the REPO ROOT — the FE .mjs gates read paths relative to cwd.)
 */
import { readFileSync } from 'node:fs';

const TS = 'web/lib/workspace/attribution.ts';
const PY = 'api/services/lane_runner.py';

const read = (p) => readFileSync(p, 'utf8');
let failures = 0;
const check = (name, fn) => {
  try { fn(); console.log(`  PASS  ${name}`); }
  catch (e) { failures++; console.log(`  FAIL  ${name}\n        ${e.message}`); }
};

console.log('\nlane-model-labels:');

// ---- Parse the Python registry (the source of truth) ----------------------
const py = read(PY);
const pyBlock = py.slice(py.indexOf('LANE_MODELS'), py.indexOf('def offered_lane_models'));
// Strip comments first: an assertion that can match its own explanatory prose
// proves nothing (a repeated lesson in this repo).
const pyCode = pyBlock.replace(/^\s*#.*$/gm, '').replace(/#.*$/gm, '');

const pyLabels = new Map();
const pyRetired = new Set();
const rowRe = /"([a-z0-9_]+\/[a-z0-9.\-]+)":\s*\{([^}]*)\}/g;
let m;
while ((m = rowRe.exec(pyCode)) !== null) {
  const labelMatch = m[2].match(/"label":\s*"([^"]+)"/);
  if (!labelMatch) throw new Error(`LANE_MODELS row ${m[1]} has no label — the shape moved`);
  pyLabels.set(m[1], labelMatch[1]);
  if (/retired["']?\s*:\s*True/.test(m[2])) pyRetired.add(m[1]);
}

// ---- Parse the TS mirror --------------------------------------------------
const ts = read(TS);
const tsBlock = ts.slice(ts.indexOf('const LANE_MODEL_NAMES'), ts.indexOf('function laneModelName'));
const tsCode = tsBlock.replace(/\/\/.*$/gm, '');
const tsLabels = new Map();
const tsRe = /'([a-z0-9_]+\/[a-z0-9.\-]+)':\s*'([^']+)'/g;
while ((m = tsRe.exec(tsCode)) !== null) tsLabels.set(m[1], m[2]);

check('both registries parsed', () => {
  if (pyLabels.size === 0) throw new Error('parsed zero LANE_MODELS rows — the Python shape moved');
  if (tsLabels.size === 0) throw new Error(`parsed zero rows from ${TS} — the TS shape moved`);
});

check('the FE mirror covers every LANE_MODELS row, and no extras', () => {
  const missing = [...pyLabels.keys()].filter((k) => !tsLabels.has(k));
  const extra = [...tsLabels.keys()].filter((k) => !pyLabels.has(k));
  if (missing.length) throw new Error(`in LANE_MODELS but absent from ${TS}: ${missing.join(', ')}`);
  if (extra.length) throw new Error(`in ${TS} but absent from LANE_MODELS: ${extra.join(', ')}`);
});

check('every mirrored label matches the server verbatim', () => {
  const drift = [];
  for (const [id, pyLabel] of pyLabels) {
    const tsLabel = tsLabels.get(id);
    if (tsLabel !== undefined && tsLabel !== pyLabel) {
      drift.push(`${id}: server "${pyLabel}" vs FE "${tsLabel}"`);
    }
  }
  if (drift.length) throw new Error(`label drift:\n        ${drift.join('\n        ')}`);
});

check('no two engines share a label', () => {
  // The ledger collision this rule exists to prevent: a member reading their
  // own history must be able to tell WHICH engine authored a revision.
  const byLabel = new Map();
  for (const [id, label] of pyLabels) {
    if (!byLabel.has(label)) byLabel.set(label, []);
    byLabel.get(label).push(id);
  }
  const collisions = [...byLabel.entries()].filter(([, ids]) => ids.length > 1);
  if (collisions.length) {
    throw new Error(
      `two engines share a label (the attribution string cannot distinguish them):\n        ` +
      collisions.map(([l, ids]) => `"${l}" ← ${ids.join(' + ')}`).join('\n        '),
    );
  }
});

check('every label carries a version', () => {
  // A bare family name is what made "Claude Sonnet" mean two different engines.
  // A version = any digit in the label. Checked on OFFERED rows: a retired row
  // keeps whatever name it authored revisions under and must not be rewritten.
  const bare = [...pyLabels.entries()]
    .filter(([id]) => !pyRetired.has(id))
    .filter(([, label]) => !/\d/.test(label));
  if (bare.length) {
    throw new Error(
      `offered engine(s) with no version in the label: ${bare.map(([i, l]) => `${i} → "${l}"`).join(', ')}`,
    );
  }
});

console.log(
  failures === 0
    ? '\nlane-model-labels: all checks passed\n'
    : `\nlane-model-labels: ${failures} FAILED\n`,
);
process.exit(failures === 0 ? 0 : 1);
