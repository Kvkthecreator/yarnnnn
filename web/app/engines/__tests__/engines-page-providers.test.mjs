/**
 * The /engines page must stay honest about WHO it points at, and must not
 * grow the thing it exists to avoid (ADR-490 amendment 2026-08-19).
 *
 * Two failure modes, one gate:
 *
 *  1. A NEW PROVIDER lands in LANE_MODELS and nobody updates the page, so it
 *     sends members to rate cards for a subset of the engines they can pick.
 *     The page enumerates by PROVIDER on purpose — a model release must never
 *     require an edit here, but a provider addition must.
 *
 *  2. The page grows a comparison table / price / ranking. That is exactly the
 *     content whose staleness is INVISIBLE (a stale table looks like a current
 *     one) and the reason the page links out instead. Also the ADR-490 §1②
 *     line: no surface states the platform margin.
 *
 * Run: node web/app/engines/__tests__/engines-page-providers.test.mjs
 * (from the REPO ROOT — the FE .mjs gates read paths relative to cwd.)
 */
import { readFileSync } from 'node:fs';

const PAGE = 'web/app/engines/page.tsx';
const LANE_RUNNER = 'api/services/lane_runner.py';

const read = (p) => readFileSync(p, 'utf8');
let failures = 0;
const check = (name, fn) => {
  try { fn(); console.log(`  PASS  ${name}`); }
  catch (e) { failures++; console.log(`  FAIL  ${name}\n        ${e.message}`); }
};

console.log('\nengines-page-providers:');

const page = read(PAGE);

// Strip comments before asserting on content: an assertion that can match its
// own explanatory prose proves nothing (a repeated lesson in this repo).
const pageCode = page
  .replace(/\/\*[\s\S]*?\*\//g, '')
  .replace(/^\s*\/\/.*$/gm, '');

// ---- 1. Every offered provider is represented on the page ------------------
check('every provider offered in LANE_MODELS appears on the page', () => {
  const py = read(LANE_RUNNER);
  const block = py.slice(py.indexOf('LANE_MODELS'), py.indexOf('def offered_lane_models'));

  // Provider = the prefix before `/` on a non-retired LANE_MODELS row.
  const offered = new Set();
  const rowRe = /"([a-z0-9_]+)\/[a-z0-9.\-]+":\s*\{([^}]*)\}/g;
  let m;
  while ((m = rowRe.exec(block)) !== null) {
    if (!/retired["']?\s*:\s*True/.test(m[2])) offered.add(m[1]);
  }
  if (offered.size === 0) throw new Error('parsed zero providers — the LANE_MODELS shape moved');

  // gemini/ rows are Google's; the page names the vendor, not the API prefix.
  const VENDOR = { anthropic: 'Anthropic', openai: 'OpenAI', gemini: 'Google', deepseek: 'DeepSeek', xai: 'xAI' };
  const missingVendor = [...offered].filter((p) => !VENDOR[p]);
  if (missingVendor.length) {
    throw new Error(
      `LANE_MODELS offers provider(s) this gate has no vendor name for: ${missingVendor.join(', ')}. ` +
      `Add them to VENDOR here AND to PROVIDERS on ${PAGE}.`,
    );
  }
  const missing = [...offered].map((p) => VENDOR[p]).filter((v) => !pageCode.includes(v));
  if (missing.length) {
    throw new Error(`offered but absent from ${PAGE}: ${missing.join(', ')}`);
  }
});

// ---- 2. The page must not become the thing it replaces ---------------------
check('the page states no price', () => {
  // A $-figure or a "per million tokens" rate is the maintenance burden the
  // page exists to outsource.
  const priced = pageCode.match(/\$\s?\d|\bper\s+million\b|\/M\s+tokens/i);
  if (priced) throw new Error(`price-shaped text found: "${priced[0]}"`);
});

check('the page does not state the platform margin', () => {
  // ADR-490 §1② as amended: the margin is on no surface.
  const margin = pageCode.match(/\b\d{1,3}\s?%|\bmargin\b|\bmarkup\b|cost\s*\+/i);
  if (margin) throw new Error(`margin-shaped text found: "${margin[0]}"`);
});

check('the page ranks no engine', () => {
  // "best for X" / "fastest" / "smartest" is a claim that expires silently.
  const ranked = pageCode.match(/\bbest\s+(for|at|engine|model)\b|\bfastest\b|\bsmartest\b|\bmost capable engine\b/i);
  if (ranked) throw new Error(`ranking-shaped text found: "${ranked[0]}"`);
});

check('the page names no specific model', () => {
  // Naming a model dates the page to that model's lifetime. Provider names are
  // fine and required; model names are not.
  const named = pageCode.match(/\b(sonnet|haiku|opus|gpt-\d|gemini\s+(pro|flash)|deepseek-)\b/i);
  if (named) throw new Error(`model name found: "${named[0]}" — enumerate providers, never models`);
});

// ---- 3. The outbound links are the whole mechanism -------------------------
check('the page links out to maintained sources', () => {
  // ONE maintained benchmark (LMArena removed 2026-08-21 — a leaderboard we
  // neither run nor audit is a claim we cannot stand behind). The page's whole
  // mechanism is linking OUT, so losing the last benchmark source must fail
  // here rather than leave a section headed "where the current numbers live"
  // that names nowhere.
  for (const host of ['artificialanalysis.ai']) {
    if (!pageCode.includes(host)) throw new Error(`missing outbound source: ${host}`);
  }
  // The removal must STAY removed: re-adding it should be a deliberate edit to
  // this gate, not a silent revert.
  if (pageCode.includes('lmarena.ai')) {
    throw new Error('lmarena.ai is back on the page — removed deliberately; re-add here first if that is intended');
  }
  // Count HREFS, not `target="_blank"` literals — both link lists render via
  // .map(), so the literal appears once per list while the page carries many
  // outbound links. Counting literals would under-count and, worse, would pass
  // if someone replaced the lists with two hardcoded anchors.
  const hrefs = pageCode.match(/href:\s*"https?:\/\//g) ?? [];
  if (hrefs.length < 5) {
    throw new Error(`expected >=5 outbound sources (1 benchmark + providers); found ${hrefs.length}`);
  }
  // Every outbound list that renders must still open in a new tab.
  const blanks = pageCode.match(/target="_blank"/g) ?? [];
  if (blanks.length < 2) {
    throw new Error(`outbound links must open externally; found ${blanks.length} target="_blank"`);
  }
});

check('the chat chooser points at the page', () => {
  // The page is useless if the decision point does not reach it.
  const modal = read('web/components/chat-surface/NewChatModal.tsx').replace(/\{\/\*[\s\S]*?\*\/\}/g, '');
  if (!modal.includes('/engines')) {
    throw new Error('NewChatModal no longer links to /engines — the door asks "which engine?" with no answer');
  }
});

console.log(
  failures === 0
    ? '\nengines-page-providers: all checks passed\n'
    : `\nengines-page-providers: ${failures} FAILED\n`,
);
process.exit(failures === 0 ? 0 : 1);
