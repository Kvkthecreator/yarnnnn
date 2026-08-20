// Executing check of the FILES ARRIVAL law (2026-08-13 redirect-handling audit).
//
// WHAT THIS GATE IS FOR. The operator clicked "open folder" in Radar and landed
// on generic Recents: correct URL, no highlight, param never drained. Every FE
// gate was green, because the defect lived in the SEAM between two modules that
// each read correctly alone — Radar delivered the right param, Files knew how to
// open a path, and nothing tested the handoff. Two independent causes stacked:
//
//   C1  `files` was absent from BOTH shell param registries. normalizeWindowParams
//       returns early for an unlisted slug ("unconstrained — leave as-is"), so any
//       key delivered to Files was accepted and persisted; and because `files.path`
//       was never classified EPHEMERAL, reconcileUrl's `incoming < remembered`
//       merge let a stale remembered path OUTRANK the live deep-link on every
//       foreground. Same trapdoor class the map already closed for studio/images.
//
//   C2  Files consumed the param through TWO handlers — a seed captured on first
//       render, plus a post-mount effect gated on a ref that flipped only after
//       loadExplorer's network round-trip. In canvas/mobile mode SurfaceViewport
//       renders ONLY the foregrounded surface, so a backgrounded Files window is
//       UNMOUNTED and a jump REMOUNTS it. The seed then captured null (the param
//       arrives via replaceState, which has not re-rendered useSearchParams yet)
//       while the effect early-returned — and, keyed on values that never changed
//       again, it never re-fired.
//
// NEVER PIN A SPELLING. The registry assertions EXECUTE the shipped functions
// against real inputs. The Files-surface assertions are necessarily source-shaped
// (a React component's effect ordering is not executable here), so they assert
// STRUCTURE — how many handlers consume the param, and whether any guard can
// outvote it — never a literal that a rename would break.
//
// Run from the REPO ROOT: node web/scripts/gates/files_arrival_door.mjs
import { readFileSync } from 'fs';

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};

// Execute the SHIPPED source of the two registry functions plus the two maps
// they read. Importing the module is not an option (it pulls the app's whole
// API client through a `@/` alias), and re-implementing the rules here would
// let the gate pass while the app was broken — so we lift the real
// declarations and run them. Only type annotations are erased.
const prefs = readFileSync('web/lib/shell/surface-preferences.ts', 'utf8');
const lift = (name, kind) => {
  const re =
    kind === 'const'
      ? new RegExp(`const ${name}[^=]*=\\s*\\{[\\s\\S]*?\\n\\};`)
      : new RegExp(`export function ${name}\\([\\s\\S]*?\\n\\}`);
  const m = prefs.match(re);
  if (!m) throw new Error(`gate could not lift ${name} — the source shape moved`);
  return m[0].replace(/^export\s+/, '');
};
const erase = (s) =>
  s
    // `const X: Record<string, readonly string[]> = {` → `const X = {`
    .replace(/(const \w+)\s*:\s*Record<[^=]+>\s*=/, '$1 =')
    // param + return annotations on the two lifted functions
    .replace(/(\w+)\s*:\s*Record<string, string>\s*\|\s*undefined/g, '$1')
    .replace(/(\w+)\s*:\s*string(?=[,)])/g, '$1')
    .replace(/\)\s*:\s*Record<string, string>\s*\|\s*undefined\s*\{/g, ') {')
    .replace(/:\s*Record<string, string>\s*=/g, ' =');
const { normalizeWindowParams, stripEphemeralParams } = new Function(`
  ${erase(lift('SURFACE_PARAM_KEYS', 'const'))}
  ${erase(lift('SURFACE_EPHEMERAL_PARAM_KEYS', 'const'))}
  ${erase(lift('normalizeWindowParams', 'fn'))}
  ${erase(lift('stripEphemeralParams', 'fn'))}
  return { normalizeWindowParams, stripEphemeralParams };
`)();

// ── C1: the registries, executed ──────────────────────────────────────────
//
// Falsifier watched go red: removing the `files` row from SURFACE_PARAM_KEYS
// turns A1/A2 red; removing it from SURFACE_EPHEMERAL_PARAM_KEYS turns A3 red.

// A1 — the two keys Files actually reads survive the allowlist. This is the
// live deep-link working at all; a wrong entry here silently eats every jump.
const kept = normalizeWindowParams('files', {
  path: '/workspace/operation/ai-frontier',
  domain: 'competitors',
});
t(
  'A1 the params the Files surface reads survive normalization',
  kept.path === '/workspace/operation/ai-frontier' && kept.domain === 'competitors',
);

// A2 — Files is CONSTRAINED, not unconstrained. An unlisted slug returns its
// input untouched, so this is the assertion that distinguishes "registered"
// from "defaulted". A param the surface never reads must be dropped.
t(
  'A2 a param the surface does not read is dropped (files is constrained)',
  normalizeWindowParams('files', { platform: 'slack' }).platform === undefined,
);

// A3 — the drill-in is not replayed on a bare launch. `path` names a specific
// node opened once; replaying it makes the dock icon resume a stale document
// instead of opening the app's front door, and outranks the incoming link.
const remembered = stripEphemeralParams('files', {
  path: '/workspace/operation/ai-frontier',
  domain: 'competitors',
});
t(
  'A3 the opened-node param is not remembered across a bare launch',
  remembered.path === undefined,
);

// A4 — ...while the resting POSTURE is. The distinction is the whole point of
// the ephemeral map: drill-ins are forgotten, postures are restored.
t('A4 the resting-folder param IS remembered', remembered.domain === 'competitors');

// A5 — the two maps stay coherent for every CONSTRAINED surface: a key named
// ephemeral must also be owned, or the rule is inert (normalization drops it
// before the ephemeral test ever runs). Executed across the whole registry, so
// a future entry cannot get this wrong either.
const probe = { path: 'p', domain: 'd', file: 'f', system: 's', agent: 'a', pane: 'x', connector: 'c' };
const inert = [];
for (const slug of ['files', 'studio', 'docs', 'images', 'agents']) {
  const owned = normalizeWindowParams(slug, probe);
  const surviving = stripEphemeralParams(slug, probe);
  for (const k of Object.keys(probe)) {
    const namedEphemeral = surviving[k] === undefined;
    const isOwned = owned[k] !== undefined;
    if (namedEphemeral && !isOwned) inert.push(`${slug}.${k}`);
  }
}
t(`A5 no ephemeral rule names an unowned key (inert: ${inert.join(', ') || 'none'})`, inert.length === 0);

// ── C2: one arrival door, structurally ────────────────────────────────────
const files = readFileSync('web/app/(authenticated)/files/page.tsx', 'utf8');
// Strip comments so no assertion can match its own explanatory prose — the
// gate_assertion_matches_its_own_comment trap (this file's comments SAY
// "seedConsumedRef", which would pass a naive source grep).
const code = files
  .replace(/\/\*[\s\S]*?\*\//g, '')
  .split('\n')
  .map((l) => l.replace(/(^|[^:])\/\/.*$/, '$1'))
  .join('\n');

// A6 — the racing guards are GONE from executable code, not merely unused.
// These are the refs whose flip-after-network ordering stranded the param.
t(
  'A6 no mount-seed guard remains in executable code',
  !/seedRef|seedConsumedRef/.test(code),
);

// A7 — exactly ONE site consumes the arrival param by opening it. Two handlers
// for one job is the shape that produced the bug.
//
// RE-ANCHORED 2026-08-20. This counted EVERY `openPathRef.current(` in the file
// and required exactly 2 — a hand-kept whole-file count that reads GROWTH as a
// violation. `openPathRef` is the surface's late-bound handle on the funnel and
// is legitimately reached from several places that have nothing to do with a
// deep link (Enter-opens-the-selection, the selection bar's Open). The gate had
// already gone RED at HEAD for exactly that reason — a real failure nobody
// caused — and each new legitimate caller made it redder.
//
// Scope the count to what the check actually claims: the ARRIVAL EFFECT. Inside
// that one handler there must be exactly two handoffs (the `?files.path=` leg
// and the `?files.domain=` leg) and no third; outside it, callers are free.
const arrivalEffect = code.match(
  /if \(!pathParam && !domainParam\) return;[\s\S]*?fp\.set\(/,
);
const opens = arrivalEffect
  ? (arrivalEffect[0].match(/openPathRef\.current\(/g) || []).length
  : -1;
t(
  `A7 exactly one arrival handler opens the deep-link (handoffs inside it: ${opens})`,
  opens === 2,
);

// A8 — the param is DRAINED once honoured. Without the drain a stale path
// re-applies on later refetches, which is what the deleted seed defended
// against; the drain is what makes that defence unnecessary.
t(
  'A8 the arrival handler drains the param after opening',
  /fp\.set\(\s*\{\s*path:\s*null,\s*domain:\s*null\s*\}\s*\)/.test(code),
);

// A9 — the tree loader no longer consumes the param. loadExplorer re-runs on a
// 30s timer and on window focus; coupling the open to it is what put the
// handoff behind a network round-trip.
// Bounded at the loader's OWN end (its `}, []);` terminator), not a fixed
// character window — an overshooting slice would read the arrival effect's
// body and report a violation that isn't there.
const loaderStart = code.indexOf('const loadExplorer');
const loaderEnd = code.indexOf('}, []);', loaderStart);
if (loaderStart < 0 || loaderEnd < 0) throw new Error('gate could not bound loadExplorer');
const loader = code.slice(loaderStart, loaderEnd);
t(
  'A9 the tree loader does not consume the arrival param',
  !/openPathRef\.current\(/.test(loader) && !/fp\.set\(/.test(loader),
);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
