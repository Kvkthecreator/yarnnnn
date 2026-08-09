// ADR-518 D7 follow-through — the chrome speaks in the APP's voice, derived
// from the AuthoringApp declaration, never a hardcoded per-site string.
//
// The carve left three classes of Studio-voiced strings in the shared surface:
//   1. 47 revision-message prefixes (`Studio: insert …`) — every mechanical
//      edit made in Docs landed in the attributed record reading "Studio:".
//      Now `${app.label}: …` at every site; this gate BANS the literal.
//   2. The landing's hardcoded subtitle + Palette glyph — Docs arrived
//      wearing the layout app's invitation and icon. Now declared per app
//      (tagline + icon on the AuthoringApp contract).
//   3. Stale cross-app copy (the `article` starter set outlived its type).
//
// The ban is a per-site sweep by construction: ANY site that reintroduces a
// hardcoded `Studio: ` message prefix trips it, wherever it lands.
//
// Run from the REPO ROOT: node web/scripts/gates/adr518_app_voice.mjs
import { readFileSync, readdirSync } from 'fs';

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};

const files = readdirSync('web/components/authoring').map((f) => ({
  name: f,
  src: readFileSync(`web/components/authoring/${f}`, 'utf8'),
}));
const surface = files.find((f) => f.name === 'StudioSurface.tsx').src;

// ── 1. The hardcoded op-message prefix is BANNED ────────────────────────────
// Matches `Studio: …` / 'Studio: …' / "Studio: …" as a string-literal prefix.
const BANNED = /['"`]Studio: /;
const offenders = (fs) => fs.filter((f) => BANNED.test(f.src)).map((f) => f.name);
t('no studio component hardcodes a `Studio: ` message prefix', offenders(files).length === 0);

// The replacement is live: the op messages derive from the app declaration.
const derivedCount = (surface.match(/\$\{app\.label\}: /g) ?? []).length;
t(`op messages derive from app.label (${derivedCount} sites, expected ≥ 40)`, derivedCount >= 40);

// ── 2. Every app declaration carries the voice fields ───────────────────────
// The slice ends at the declaration's own `};` — a fixed width would bleed
// into the NEXT app's declaration and pass on its fields.
const declOf = (src, name) => {
  const at = src.indexOf(`export const ${name}`);
  return at < 0 ? '' : src.slice(at, src.indexOf('};', at) + 2);
};
for (const name of ['DOCS_APP', 'STUDIO_APP', 'IMAGES_APP']) {
  const decl = declOf(surface, name);
  t(`${name} declares label + tagline + icon`, /label:/.test(decl) && /tagline:/.test(decl) && /icon:/.test(decl));
}

// The landing consumes the declaration, not a constant.
t('the landing renders app.tagline', surface.includes('{app.tagline}'));
t('the landing renders the app glyph (<app.icon)', surface.includes('<app.icon'));

// ── 3. The dead article starter set did not survive ─────────────────────────
const sugAt = surface.indexOf('const TEMPLATE_SUGGESTIONS');
const sugBlock = surface.slice(sugAt, surface.indexOf('};', sugAt));
t('TEMPLATE_SUGGESTIONS carries no article entry (type died in ADR-505)', !/\barticle:/.test(sugBlock));

// ── FALSIFIERS ──────────────────────────────────────────────────────────────
{
  const mutated = [...files, { name: '__mut__.tsx', src: 'applyOp(fn, `Studio: insert block`)' }];
  console.log('mutated: reintroduced a hardcoded `Studio: ` prefix (in memory)');
  t('FALSIFIER: the ban trips on a reintroduced prefix', offenders(mutated).length === 1);
}
{
  const mutated = surface.replace(/tagline:\s*\n?\s*'[^']*',\s*\n(\s*)icon: FileText,/, '$1icon: FileText,');
  console.log('mutated: removed DOCS_APP tagline (in memory)');
  if (mutated === surface) {
    t('FALSIFIER: the tagline removal actually mutated the source', false);
  } else {
    t('FALSIFIER: the declaration check trips on a missing tagline', !/tagline:/.test(declOf(mutated, 'DOCS_APP')));
  }
}

console.log(`\nADR-518 app voice: ${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
