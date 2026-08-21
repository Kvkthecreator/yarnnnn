/**
 * A lane pinned to a RETIRED engine must NAME it, never render its raw id.
 *
 * THE DEFECT (operator-observed 2026-08-21, from a screenshot). The chat lane
 * filter chip read `anthropic/claude-sonnet-4-6` — a raw model id, provider
 * prefix and all — where every other surface reads a label.
 *
 * THE MECHANISM, and why it is a design seam rather than a typo:
 *   • `/api/lanes` serves `models[]` from `offered_lane_models()` — correctly
 *     the CHOOSER's view, which drops retired rows (ADR-559 D2).
 *   • But a lane's engine is persisted at creation and is a HISTORICAL FACT
 *     (ADR-460 D4). A lane on a retired engine therefore has NO row in
 *     `models[]`, and every `modelLabel`-shaped lookup fell through to the id.
 *   • Not hypothetical: at the ADR-559 roster refresh, ALL 65 live lanes were
 *     pinned to `claude-sonnet-4-6`.
 *
 * ADR-559 already draws this line ("one dict, two audiences") — it was simply
 * never carried to the envelope. `model_names` is the second audience: id →
 * label for EVERY engine, naming only. It is deliberately NOT merged into
 * `models`, because that would leak retired engines back into the chooser.
 *
 * Run: node web/lib/workspace/__tests__/retired-engine-naming.test.mjs
 * (from the REPO ROOT — the FE .mjs gates read paths relative to cwd.)
 */
import { readFileSync } from 'node:fs';

const read = (p) => readFileSync(p, 'utf8');
let failures = 0;
const check = (name, fn) => {
  try { fn(); console.log(`  PASS  ${name}`); }
  catch (e) { failures++; console.log(`  FAIL  ${name}\n        ${e.message}`); }
};
// Strip comments before asserting: an assertion that can match its own
// explanatory prose proves nothing (a repeated lesson in this repo).
const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
const stripPy = (s) => s.replace(/^\s*#.*$/gm, '').replace(/#.*$/gm, '');

console.log('\nretired-engine-naming:');

// ---- 1. The server serves the naming table, from the FULL registry ---------
check('/api/lanes serves `model_names` built from the FULL LANE_MODELS', () => {
  const py = stripPy(read('api/routes/lanes.py'));
  const m = py.match(/"model_names":\s*\{[^}]*for\s+mid,\s*meta\s+in\s+(\w+)/);
  if (!m) throw new Error('no `model_names` key built by comprehension in the lanes envelope');
  if (m[1] !== 'LANE_MODELS') {
    throw new Error(
      `model_names is built from ${m[1]}, not LANE_MODELS — a retired engine would have no name`,
    );
  }
});

check('`models` (the CHOOSER) still serves only the OFFERED roster', () => {
  // The inverse failure: "fixing" naming by serving retired rows in `models`
  // would put retired engines back in the picker, which ADR-559 D2 forbids.
  const py = stripPy(read('api/routes/lanes.py'));
  const m = py.match(/"models":\s*\[[\s\S]{0,600}?for\s+mid,\s*meta\s+in\s+(\w+)\(\)/);
  if (!m) throw new Error('could not parse the `models` comprehension');
  if (m[1] !== 'offered_lane_models') {
    throw new Error(`the chooser is built from ${m[1]} — retired engines would leak to the door`);
  }
});

// ---- 2. Every naming site consults it BEFORE falling back to the raw id ----
const SITES = [
  ['web/components/chat-surface/ChatSurface.tsx', 'model_names'],
  ['web/components/desk/DeskHousing.tsx', 'modelNames'],
  ['web/components/authoring/StudioSurface.tsx', 'modelNames'],
];

for (const [file, token] of SITES) {
  check(`${file.split('/').pop()} names a retired engine before falling back to the id`, () => {
    const src = strip(read(file));
    if (!src.includes(token)) {
      throw new Error(`no ${token} lookup — a retired engine renders its raw id here`);
    }
    // The ORDER is the whole point: the naming table must be consulted BEFORE
    // the bare `?? lane.model` fallback, or it never runs for the broken case.
    const nameIdx = src.indexOf(token + (token === 'model_names' ? '?.[' : '['));
    const rawIdx = src.search(/\?\?\s*(boundLane\??\.model|modelId)/);
    if (nameIdx === -1) throw new Error(`${token} is present but never indexed by model id`);
    if (rawIdx !== -1 && rawIdx < nameIdx) {
      throw new Error('the raw-id fallback is consulted BEFORE the naming table');
    }
  });
}

// ---- 3. The client type exposes it ----------------------------------------
check('the API client type declares model_names', () => {
  const src = strip(read('web/lib/api/client.ts'));
  if (!/model_names\??:\s*Record<string,\s*string>/.test(src)) {
    throw new Error('client.ts does not type `model_names` — the FE cannot read it');
  }
});

console.log(
  failures === 0
    ? '\nretired-engine-naming: all checks passed\n'
    : `\nretired-engine-naming: ${failures} FAILED\n`,
);
process.exit(failures === 0 ? 0 : 1);
