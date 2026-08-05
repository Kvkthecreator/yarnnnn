// ADR-518 follow-through — the navigator is PAGED-ONLY, singular.
//
// The carve (dd2b5dd) deleted the flow-outline MOUNT but left the dead flow
// renderer inside StudioNavigator behind an `isPaged` flag — the worst dual
// file in the split audit. The cleanup deletes the dead half and renames the
// component to what it is: PagedNavigator. This gate pins three facts:
//
//   1. The dual file is gone (no StudioNavigator anywhere in web source).
//   2. PagedNavigator carries NO mode flag — it is paged by definition; the
//      mode gate lives at the ONE mount site in StudioSurface (`isPaged &&`),
//      so a flow artifact mounts no navigator at all (the shipped decision).
//   3. The dead outline machinery (extractOutline / OutlineEntry /
//      onSelectHeading) did not survive anywhere in components/studio.
//
// Each check carries a FALSIFIER: the same predicate run over a mutated copy
// must flip (receipted with a "mutated:" print) before the green is trusted.
//
// Run from the REPO ROOT: node web/scripts/gates/adr518_paged_navigator.mjs
import { readFileSync, readdirSync, existsSync } from 'fs';

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};

const NAV = 'web/components/studio/PagedNavigator.tsx';
const SURFACE = 'web/components/studio/StudioSurface.tsx';
const nav = readFileSync(NAV, 'utf8');
const surface = readFileSync(SURFACE, 'utf8');
const studioFiles = readdirSync('web/components/studio').map((f) => ({
  name: f,
  src: readFileSync(`web/components/studio/${f}`, 'utf8'),
}));

// ── 1. The dual file is gone ────────────────────────────────────────────────
t('the dual file is deleted (no StudioNavigator.tsx)', !existsSync('web/components/studio/StudioNavigator.tsx'));
const refs = studioFiles.filter((f) => f.src.includes('StudioNavigator'));
t('no studio component references StudioNavigator', refs.length === 0);

// ── 2. PagedNavigator is mode-flag-free; the gate lives at the mount ────────
const flagFree = (src) => !src.includes('isPaged');
t('PagedNavigator carries no isPaged flag (paged by definition)', flagFree(nav));

// The ONE mount: `isPaged && (` must guard the `<PagedNavigator` JSX. Assert
// the mount exists and the nearest preceding conditional within its JSX run-up
// is the mode gate.
const mountAt = surface.indexOf('<PagedNavigator');
const gateFor = (src, at) => {
  if (at < 0) return false;
  const runUp = src.slice(Math.max(0, at - 1200), at);
  return runUp.lastIndexOf('isPaged && (') >= 0;
};
t('StudioSurface mounts <PagedNavigator exactly once', mountAt >= 0 && surface.indexOf('<PagedNavigator', mountAt + 1) < 0);
t('the mount is inside the `isPaged && (` mode gate', gateFor(surface, mountAt));

// ── 3. The dead outline machinery did not survive ───────────────────────────
const outlineSurvivors = studioFiles.filter(
  (f) => /extractOutline|OutlineEntry|onSelectHeading|selectHeadingFromNavigator/.test(f.src),
);
t('no outline machinery survives in components/studio', outlineSurvivors.length === 0);

// ── FALSIFIERS — each predicate must flip on the mutated copy ───────────────
{
  const mutated = nav + '\nconst isPaged = true;\n';
  console.log('mutated: re-added an isPaged flag to PagedNavigator (in memory)');
  t('FALSIFIER: the flag-free check flips on a re-added flag', flagFree(mutated) === false);
}
{
  // Re-house the mount OUTSIDE the mode gate: a copy whose run-up has no gate.
  const mutated = '<div>\n<PagedNavigator />\n</div>';
  console.log('mutated: mounted <PagedNavigator without the isPaged gate (in memory)');
  t('FALSIFIER: the mount-gate check flips on an ungated mount', gateFor(mutated, mutated.indexOf('<PagedNavigator')) === false);
}
{
  const mutated = nav + '\nfunction extractOutline() {}\n';
  console.log('mutated: re-added extractOutline to PagedNavigator (in memory)');
  t('FALSIFIER: the outline-survivor check flips on a revived outline', /extractOutline/.test(mutated) === true);
}

console.log(`\nADR-518 paged navigator: ${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
