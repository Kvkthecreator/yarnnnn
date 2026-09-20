/**
 * The landing strip's roster must equal the kernel's `primary` tier (2026-09-20).
 *
 * `AppStrip` shows a signed-out visitor "your workspace includes: …" as a row
 * of app marks. The visitor has no workspace, so there is no served roster to
 * fetch — the list is a LITERAL in the component, which means it can drift
 * from the product the moment an app is promoted, retired, or re-iconed.
 *
 * That drift is the exact class this repo keeps paying for: a marketing
 * surface that is prose no gate reads, and stays wrong for weeks while every
 * check around it is green. `/how-it-works` sold a cast ADR-599 had deleted;
 * two setup screenshots showed a retired origin. Both were caught by a human
 * reading the page, not by a test.
 *
 * So this gate reads `api/services/kernel_surfaces.py` — the declaration
 * itself — and asserts the strip against it in BOTH directions:
 *   - every `launcher_tier: "primary"` surface appears in the strip
 *     (catches a forgotten ADDITION, the direction a negative check cannot see)
 *   - every strip row is a primary surface (catches a retired app lingering)
 *   - each row's `icon_key` and label match the kernel's, so the strip cannot
 *     resolve a different glyph than the Launcher and the Dock do.
 *
 * Run: node web/components/landing/__tests__/app-strip-matches-primary-roster.test.mjs
 * (from the REPO ROOT — the FE .mjs gates read paths relative to cwd.)
 */
import { readFileSync } from 'node:fs';
import assert from 'node:assert';

const STRIP = 'web/components/landing/AppStrip.tsx';
const KERNEL = 'api/services/kernel_surfaces.py';
const PAGE = 'web/app/page.tsx';

const strip = readFileSync(STRIP, 'utf8');
const kernel = readFileSync(KERNEL, 'utf8');
const page = readFileSync(PAGE, 'utf8');

let failures = 0;
let checks = 0;
const check = (ok, msg) => {
  checks += 1;
  if (!ok) {
    failures += 1;
    console.error(`  ✗ ${msg}`);
  }
};

// ─── The kernel's primary roster ────────────────────────────────────────────
// Each surface is a brace-balanced dict literal; a non-greedy `{...}` with no
// nested braces is enough because these rows carry only flat scalars.
const kernelPrimary = new Map();
for (const m of kernel.matchAll(/\{[^{}]*?"slug"[^{}]*?\}/gs)) {
  const body = m[0];
  const slug = /"slug":\s*"([^"]+)"/.exec(body)?.[1];
  const title = /"title":\s*"([^"]+)"/.exec(body)?.[1];
  const iconKey = /"icon_key":\s*"([^"]+)"/.exec(body)?.[1];
  const tier = /"launcher_tier":\s*"([^"]+)"/.exec(body)?.[1];
  if (slug && tier === 'primary') kernelPrimary.set(slug, { title, iconKey });
}

// A regex that matched NOTHING would make every "is in the strip" assertion
// vacuously true — the green-against-nothing fault. Assert the parse first.
assert.ok(
  kernelPrimary.size >= 5,
  `parsed only ${kernelPrimary.size} primary surfaces from ${KERNEL} — the ` +
    `regex has stopped matching, and every check below would be vacuous`,
);

// ─── The strip's roster ─────────────────────────────────────────────────────
const stripRows = new Map();
for (const m of strip.matchAll(
  /\{\s*slug:\s*"([^"]+)",\s*label:\s*"([^"]+)",\s*iconKey:\s*"([^"]+)"\s*\}/g,
)) {
  stripRows.set(m[1], { label: m[2], iconKey: m[3] });
}
assert.ok(
  stripRows.size >= 5,
  `parsed only ${stripRows.size} rows from ${STRIP} — the STRIP_APPS literal ` +
    `has changed shape and this gate no longer reads it`,
);

console.log(
  `AppStrip roster parity — ${kernelPrimary.size} kernel primary, ${stripRows.size} strip rows`,
);

// ─── Direction 1: every primary surface is on the strip ─────────────────────
for (const [slug, { title, iconKey }] of kernelPrimary) {
  const row = stripRows.get(slug);
  check(
    row !== undefined,
    `kernel declares "${slug}" (${title}) as launcher_tier primary, but the ` +
      `landing strip omits it — promote it in STRIP_APPS or demote the surface`,
  );
  if (!row) continue;
  check(
    row.iconKey === iconKey,
    `"${slug}" wears icon_key "${row.iconKey}" on the strip and "${iconKey}" ` +
      `in the kernel — the landing page would render a different glyph than ` +
      `the Launcher and the Dock`,
  );
  check(
    row.label === title,
    `"${slug}" is labelled "${row.label}" on the strip and "${title}" in the ` +
      `kernel — one app, two names`,
  );
}

// ─── Direction 2: nothing on the strip has left the roster ──────────────────
for (const slug of stripRows.keys()) {
  check(
    kernelPrimary.has(slug),
    `the landing strip advertises "${slug}", which is not a launcher_tier ` +
      `primary surface — a signed-out visitor is being sold an app they will ` +
      `not find after signing up`,
  );
}

// ─── The strip is actually mounted ──────────────────────────────────────────
// A component nothing renders is a green gate over a page that never changed.
check(
  /<AppStrip\s*\/>/.test(page),
  `${PAGE} does not render <AppStrip /> — the component exists but the ` +
    `landing page never mounts it`,
);
check(
  page.indexOf('<AppStrip />') > page.indexOf('human clipboard') &&
    page.indexOf('<AppStrip />') < page.indexOf('<AppShowcase />'),
  `<AppStrip /> is not between the problem chapter and the product chapter — ` +
    `it answers "made of what" and must land after the recognition line and ` +
    `before AppShowcase walks four apps slowly`,
);

// ─── The theme-token trap ───────────────────────────────────────────────────
// `resolveSurfaceAccent` falls back to `text-muted-foreground`, whose value is
// redefined under `.dark`. next-themes runs attribute="class" + enableSystem,
// and this page is hardcoded light — so an OS-dark visitor would get the
// dark-mode grey on a white tile. The strip must name its own neutral.
check(
  !/resolveSurfaceAccent\(app\.slug\)/.test(strip),
  `${STRIP} uses resolveSurfaceAccent directly — its text-muted-foreground ` +
    `fallback is theme-dependent and this page is hardcoded light; go through ` +
    `stripAccent()`,
);
check(
  /text-muted-foreground/.test(strip) && /STRIP_NEUTRAL/.test(strip),
  `${STRIP} no longer intercepts the text-muted-foreground fallback — an ` +
    `accent-less app would render a dark-mode grey on the light page`,
);

console.log(`\n${checks - failures}/${checks} checks passed`);
if (failures > 0) {
  console.error(`\nFAILED: ${failures} check(s)`);
  process.exit(1);
}
console.log('PASS');
