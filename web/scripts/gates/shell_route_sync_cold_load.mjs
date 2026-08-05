// Executing check of the cold-load route-foreground race (recorded in the
// ADR-518 click-pass run 1; pre-existing, every content surface).
//
// THE DEFECT: AuthenticatedLayout's pathname→surface effect stamped
// `lastSyncedPathname` BEFORE looking for a match. Cold-loading a bare route
// (`/docs`) ran the effect against the SEEDED chrome-only composition (routes
// all empty), stamped the pathname, and then no-op'd when the real roster
// landed on the same pathname — the shell kept the REMEMBERED foreground.
//
// THE CONTRACT: a pathname is synced only once it RESOLVES to a surface.
//
// This gate EXECUTES (adr484 house pattern):
//   1. the real `resolveRouteSurface` (lib/shell/route-sync.ts, types stripped)
//   2. the real effect body (components/shell/AuthenticatedLayout.tsx),
//      replayed through the cold-load sequence and the churn re-run
// and FALSIFIES by restoring the pre-fix stamp-before-match body — the race
// must return (receipted with a "mutated:" print) before the green is trusted.
//
// Run from the REPO ROOT: node web/scripts/gates/shell_route_sync_cold_load.mjs
import { readFileSync } from 'fs';

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};

// ── 1. The pure resolver, executed ──────────────────────────────────────────
// Compile the module tail (routeOf + resolveRouteSurface) with types
// stripped; the factory returns the real resolver.
const pureSrc = readFileSync('web/lib/shell/route-sync.ts', 'utf8');
const compileResolver = (src) => {
  const start = src.indexOf('function routeOf');
  const code = src
    .slice(start)
    .replace(/: RouteSurfaceEntry\[\]/g, '')
    .replace(/: RouteSurfaceEntry/g, '')
    .replace(/: string \| null/g, '')
    .replace(/: string/g, '')
    .replace(/export function/g, 'function');
  return new Function(code + '\nreturn resolveRouteSurface;')();
};
const resolveRouteSurface = compileResolver(pureSrc);

const SEEDED = [
  { slug: 'chat', route: '' },
  { slug: 'files', route: '' },
]; // the chrome-only seed — routes empty until /api/programs/surfaces lands
const ROSTER = [
  { slug: 'chat', route: '/chat' },
  { slug: 'files', route: '/files' },
  { slug: 'docs', route: '/docs' },
  { slug: 'studio', route: '/studio' },
];

t('seeded chrome-only composition resolves NOTHING (routes empty)', resolveRouteSurface('/docs', SEEDED) === null);
t('the real roster resolves /docs → docs', resolveRouteSurface('/docs', ROSTER) === 'docs');
t('the run-1 control: /studio → studio', resolveRouteSurface('/studio', ROSTER) === 'studio');
t('a sub-path resolves by prefix (/docs/x → docs)', resolveRouteSurface('/docs/x', ROSTER) === 'docs');
t(
  'longest prefix wins',
  resolveRouteSurface('/files/detail/a', [
    { slug: 'files', route: '/files' },
    { slug: 'file-detail', route: '/files/detail' },
  ]) === 'file-detail',
);
t('an unroutable pathname resolves null against a full roster', resolveRouteSurface('/desktop', ROSTER) === null);

// The wire contract is BEST-EFFORT at the program tier
// (composition_resolver._resolve_program_surfaces guarantees only slug +
// title): a route-less row must never crash the sort and never match. This
// crashed in prod on 2026-08-05 ("Cannot read properties of undefined
// (reading 'length')") before the routeOf hardening.
const WITH_ROUTELESS = [...ROSTER, { slug: 'program-x', title: 'X' }];
{
  let crashed = false, res = 'unset';
  try { res = resolveRouteSurface('/desktop', WITH_ROUTELESS); } catch { crashed = true; }
  t('a route-less program row never crashes the resolver', !crashed);
  t('a route-less program row never matches', res === null);
  t('a route-less row does not shadow real routes', resolveRouteSurface('/docs', WITH_ROUTELESS) === 'docs');
}

// ── 2. The real effect body, replayed ───────────────────────────────────────
const layoutSrc = readFileSync('web/components/shell/AuthenticatedLayout.tsx', 'utf8');
const refAt = layoutSrc.indexOf('const lastSyncedPathname = useRef');
const effAt = layoutSrc.indexOf('useEffect(() => {', refAt);
const effEnd = layoutSrc.indexOf('}, [pathname, composition.surfaces, foregroundSurface, hydrated]);', effAt);
if (effAt < 0 || effEnd < 0) {
  console.log('[FAIL] could not extract the effect body — the anchor drifted');
  process.exit(1);
}
const effBody = layoutSrc.slice(effAt + 'useEffect(() => {'.length, effEnd);

/** Replay a sequence of {pathname, surfaces, hydrated} effect runs; returns
 *  the foreground calls in order. `hydrated` defaults true so the pre-existing
 *  scenarios read as post-restore runs. */
function replay(body, runs) {
  const lastSyncedPathname = { current: null };
  const calls = [];
  const fire = new Function(
    'pathname',
    'composition',
    'lastSyncedPathname',
    'foregroundSurface',
    'resolveRouteSurface',
    'hydrated',
    body,
  );
  for (const r of runs) {
    fire(r.pathname, { surfaces: r.surfaces }, lastSyncedPathname, (slug) => calls.push(slug), resolveRouteSurface, r.hydrated ?? true);
  }
  return calls;
}

// The run-1 sequence: cold-load on the seed, then the roster lands, same pathname.
const coldLoad = [
  { pathname: '/docs', surfaces: SEEDED },
  { pathname: '/docs', surfaces: ROSTER },
];
t('cold-load: the roster arrival DOES foreground docs (the fix)', replay(effBody, coldLoad).join(',') === 'docs');

// The 2026-06-01 loop must not return: after a successful sync, churn re-runs
// (same pathname, roster unchanged) fire nothing.
const churn = [
  { pathname: '/docs', surfaces: SEEDED },
  { pathname: '/docs', surfaces: ROSTER },
  { pathname: '/docs', surfaces: ROSTER },
  { pathname: '/docs', surfaces: ROSTER },
];
t('churn after sync stays a no-op (the 2026-06-01 loop guard holds)', replay(effBody, churn).join(',') === 'docs');

// An unresolved pathname churning against a full roster never fires — the
// null find has no foreground call to re-fire.
const unroutable = [
  { pathname: '/desktop', surfaces: ROSTER },
  { pathname: '/desktop', surfaces: ROSTER },
];
t('an unroutable pathname never fires foreground', replay(effBody, unroutable).length === 0);

// The RESTORE race (browser-observed 2026-08-05: the same cold /docs load
// foregrounded Docs on one run, the remembered surface on the next): the
// sync must never fire before the mount restore has landed (hydrated), so
// the URL's explicit intent deterministically outranks remembered posture.
// Sequence: roster lands BEFORE the restore (the losing order pre-guard) —
// the sync defers, then fires after hydration.
const rosterBeforeRestore = [
  { pathname: '/docs', surfaces: SEEDED, hydrated: false },
  { pathname: '/docs', surfaces: ROSTER, hydrated: false }, // roster won the fetch race
  { pathname: '/docs', surfaces: ROSTER, hydrated: true },  // restore landed; sync now runs
];
t('the sync never fires before the restore (hydrated gate)', replay(effBody, rosterBeforeRestore).join(',') === 'docs');
t(
  'pre-hydration runs do not stamp (the sync still fires after)',
  replay(effBody, [{ pathname: '/docs', surfaces: ROSTER, hydrated: false }]).length === 0,
);

// ── FALSIFIER: the pre-fix body (stamp before match) races again ───────────
const preFix = `
    if (pathname === lastSyncedPathname.current) return;
    if (!composition.surfaces || composition.surfaces.length === 0) return;
    lastSyncedPathname.current = pathname;
    const slug = resolveRouteSurface(pathname, composition.surfaces);
    if (slug) foregroundSurface(slug);
`;
console.log('mutated: restored the pre-fix stamp-before-match effect body (in memory)');
t('FALSIFIER: the pre-fix body drops the cold-load foreground (the race returns)', replay(preFix, coldLoad).length === 0);

// ── FALSIFIER: without the hydrated gate, the sync fires under the restore ─
{
  const mutated = effBody.replace(/\s*if \(!hydrated\) return;[^\n]*\n/, '\n');
  console.log('mutated: removed the hydrated gate from the effect body (in memory)');
  if (mutated === effBody) {
    t('FALSIFIER: the hydrated-gate removal actually mutated the source', false);
  } else {
    const fired = replay(mutated, [{ pathname: '/docs', surfaces: ROSTER, hydrated: false }]);
    t('FALSIFIER: without the gate, the sync fires BEFORE the restore (clobberable)', fired.join(',') === 'docs');
  }
}

// ── FALSIFIER: the pre-hardening resolver crashes on a route-less row ──────
{
  const mutated = pureSrc
    .replace(/routeOf\(b\)\.length - routeOf\(a\)\.length/, 'b.route.length - a.route.length');
  console.log('mutated: restored the direct b.route.length sort (in memory)');
  if (mutated === pureSrc) {
    t('FALSIFIER: the sort de-hardening actually mutated the source', false);
  } else {
    let crashed = false;
    try { compileResolver(mutated)('/desktop', [...ROSTER, { slug: 'program-x', title: 'X' }]); } catch { crashed = true; }
    t('FALSIFIER: the un-hardened sort DOES crash on a route-less row', crashed);
  }
}

console.log(`\nshell route-sync cold load: ${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
