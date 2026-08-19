/**
 * The Usage pane must survive an OLDER API payload (production crash,
 * 2026-08-19).
 *
 * WHAT HAPPENED: the pane shipped reading `usageDetail.by_model.length`,
 * `activity.spend_usd`, `trend_days` and `by_work[].pct_runs` — four fields
 * added in the same change as the component. The FE (Vercel) and the API
 * (Render) are SEPARATELY DEPLOYED services, so the browser held the new
 * component while the API still answered the previous shape. `by_model` was
 * undefined, `.length` threw, and the error escaped to the route boundary:
 * clicking "Usage" replaced the ENTIRE Workspace Settings door with
 * "Application error: a client-side exception has occurred".
 *
 * Neither `tsc` nor `next build` could see it — the old payload is a runtime
 * fact, not a type. The types now mark every post-contract field optional so
 * TypeScript enforces the guard (it immediately caught a fifth unguarded site
 * on the first run), and this gate pins the render-site discipline.
 *
 * THE RULE: a field added after the original response contract is read
 * defensively — `?.`, `??`, or an explicit `!== undefined` guard — forever.
 * The API may be older than the page for an unbounded window.
 *
 * Run: node web/components/subscription/__tests__/usage-pane-survives-old-payload.test.mjs
 * (from the REPO ROOT — the FE .mjs gates read paths relative to cwd.)
 */
import { readFileSync } from 'node:fs';

const PANE = 'web/components/subscription/UsagePaneBody.tsx';
const CLIENT = 'web/lib/api/client.ts';

let failures = 0;
const check = (name, fn) => {
  try { fn(); console.log(`  PASS  ${name}`); }
  catch (e) { failures++; console.log(`  FAIL  ${name}\n        ${e.message}`); }
};

console.log('\nusage-pane-survives-old-payload:');

// Strip comments: an assertion that can match its own explanatory prose proves
// nothing (repeated lesson in this repo).
const strip = (t) => t.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
const pane = strip(readFileSync(PANE, 'utf8'));
const clientRaw = readFileSync(CLIENT, 'utf8');

// The four fields that did not exist in the original contract.
const POST_CONTRACT = ['by_model', 'trend_days', 'spend_usd', 'pct_runs'];

check('the client types mark every post-contract field optional', () => {
  // Scope to the usage-detail block so a same-named field elsewhere cannot
  // satisfy this by accident.
  // Slice on the RAW text (the markers survive there), then strip comments so
  // an assertion cannot be satisfied by a doc-comment mentioning the field.
  const i = clientRaw.indexOf('getUsageDetail');
  const j = clientRaw.indexOf('getSpendByPrincipal');
  if (i < 0 || j < 0) throw new Error('could not locate the getUsageDetail type block');
  const block = strip(clientRaw.slice(i, j));
  for (const f of POST_CONTRACT) {
    if (!block.includes(`${f}?`)) {
      throw new Error(`${f} must be declared optional (${f}?:) so tsc enforces the guard at every read`);
    }
  }
});

check('by_model is never dereferenced bare', () => {
  // `.by_model.` or `.by_model.length` without ?. / ?? is the exact crash.
  const bare = pane.match(/\.by_model\s*\.\s*(length|map)/g);
  if (bare) throw new Error(`unguarded by_model read: ${bare.join(', ')}`);
});

check('every post-contract field read is guarded', () => {
  const unguarded = [];
  for (const f of POST_CONTRACT) {
    // Only reads off the SERVER payload matter. `r.spend_usd` on a
    // spend-by-principal row is a different endpoint with its own contract.
    const re = new RegExp(`usageDetail(?:[\\w\\].]*)\\.${f}\\b`, 'g');
    let m;
    while ((m = re.exec(pane)) !== null) {
      const around = pane.slice(Math.max(0, m.index - 90), m.index + m[0].length + 90);
      const guarded =
        around.includes(`${f}?`) ||          // optional chain on the field
        around.includes(`${f} ??`) ||        // nullish default
        around.includes(`${f} !== undefined`) ||
        /\?\?[^;]*$/.test(around.slice(0, around.indexOf(f) + f.length)) ||
        new RegExp(`\\?\\?[\\s\\S]{0,60}${f}`).test(around) ||
        new RegExp(`${f}[\\s\\S]{0,40}\\?\\?`).test(around) ||
        // an enclosing `field !== undefined &&` conditional block
        new RegExp(`${f}\\s*!==\\s*undefined`).test(pane.slice(Math.max(0, m.index - 400), m.index + 200));
      if (!guarded) unguarded.push(`${m[0].trim()} …in… ${around.replace(/\s+/g, ' ').slice(0, 110)}`);
    }
  }
  if (unguarded.length) {
    throw new Error(`unguarded post-contract read(s):\n        - ${unguarded.join('\n        - ')}`);
  }
});

check('the spend headline has a fallback that does not depend on the server', () => {
  if (!/spendTotal/.test(pane)) throw new Error('expected a derived spendTotal');
  const i = pane.indexOf('const spendTotal');
  const decl = pane.slice(i, i + 260);
  if (!decl.includes('??') || !decl.includes('reduce')) {
    throw new Error('spendTotal must fall back to summing the trend when the server omits spend_usd');
  }
});

console.log(
  failures === 0
    ? '\nusage-pane-survives-old-payload: all checks passed\n'
    : `\nusage-pane-survives-old-payload: ${failures} FAILED\n`,
);
process.exit(failures === 0 ? 0 : 1);
