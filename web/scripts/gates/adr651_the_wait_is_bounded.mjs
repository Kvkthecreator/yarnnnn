// Executing check of ADR-651 — the wait is bounded and speaks one way.
//
// WHAT THIS GATE IS FOR. The 2026-09-13 audit found ~115 hand-drawn spinners
// with no shared shape, zero bounded waits, no request deadline, and a chat
// stream that could hold its spinner up for ever on a dead socket. Each rule
// below is a SET or a BEHAVIOUR, never a spelling (the ADR-544 lesson): a
// rename must not redden it, and a regression of the shape must.
//
// Run from the REPO ROOT: node web/scripts/gates/adr651_the_wait_is_bounded.mjs
import { readFileSync, readdirSync, statSync } from 'fs';
import { join } from 'path';

let pass = 0;
let fail = 0;
function check(name, ok, why = '') {
  if (ok) pass += 1;
  else fail += 1;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${ok || !why ? '' : `\n      ${why}`}`);
}
function read(p) {
  try {
    return readFileSync(p, 'utf8');
  } catch {
    return null;
  }
}
function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (name === 'node_modules' || name === '.next') continue;
    if (statSync(p).isDirectory()) walk(p, out);
    else if (/\.(tsx|ts)$/.test(name)) out.push(p);
  }
  return out;
}
const sources = [...walk('web/app'), ...walk('web/components')].map((p) => [p, read(p) ?? '']);
const PRIMITIVE = 'web/components/shared/Working.tsx';
const primitive = read(PRIMITIVE);
const css = read('web/app/globals.css') ?? '';
const client = read('web/lib/api/client.ts') ?? '';
const sse = read('web/lib/sse.ts') ?? '';
const lanes = read('api/routes/lanes.py') ?? '';

// ── §1 ONE primitive, bounded by construction ───────────────────────────────
check('§1 the primitive exists', primitive !== null, `${PRIMITIVE} is missing`);
const slow = Number((primitive ?? '').match(/SLOW_MS\s*=\s*([\d_]+)/)?.[1]?.replace(/_/g, ''));
const stuck = Number((primitive ?? '').match(/STUCK_MS\s*=\s*([\d_]+)/)?.[1]?.replace(/_/g, ''));
check(
  '§1 a wait admits slowness before it offers an exit, and the exit comes within a minute',
  Number.isFinite(slow) && Number.isFinite(stuck) && slow < stuck && stuck <= 60_000,
  `SLOW_MS=${slow} STUCK_MS=${stuck}`,
);
check(
  '§1 the stuck state renders an exit (a button), not only words',
  /stuck[\s\S]*<button/.test(primitive ?? ''),
);
check(
  '§1 the wait is a live region so a screen reader hears it once',
  /role="status"/.test(primitive ?? ''),
);
check(
  '§1 the patient form (a caller that reports its start) never self-escalates',
  /since\s*!==\s*undefined\)\s*return/.test(primitive ?? ''),
  'the escalation effect must return early when `since` is given — the transport bounds that wait',
);

// ── §2 ONE animation vocabulary in the stylesheet ───────────────────────────
check(
  '§2 exactly one shimmer keyframe and one glyph vocabulary',
  (css.match(/@keyframes\s+working-shimmer\b/g) ?? []).length === 1 &&
    (css.match(/@keyframes\s+shimmer\b/g) ?? []).length === 0 &&
    /\.working-glyph\b/.test(css),
);
check(
  '§2 the dead liveness block is gone',
  !/agent-working|desk-glow|tp-pulse|agent-shimmer|border-hint/.test(css),
);
check(
  '§2 forced-colors mode still shows the label (clip-to-text paints nothing there)',
  /@media\s*\(forced-colors:\s*active\)[\s\S]*working-label/.test(css),
);
check('§2 the reduced-motion guard survives', /prefers-reduced-motion:\s*reduce/.test(css));

// The glyph is six stacked spans, each shown by its own step-end keyframe.
// EXECUTE the keyframes: at every one of the 12 frames exactly one glyph is
// visible, and the visible order is Claude Code's forward-then-back cycle.
function frameOf(name) {
  const body = css.match(new RegExp(`@keyframes\\s+${name}\\s*\\{([\\s\\S]*?)\\n\\}`))?.[1];
  if (!body) return null;
  const stops = [];
  for (const m of body.matchAll(/([\d.]+)%\s*\{\s*opacity:\s*([\d.]+)/g)) {
    stops.push([Number(m[1]), Number(m[2])]);
  }
  stops.sort((a, b) => a[0] - b[0]);
  return (pct) => {
    let v = stops[0]?.[1] ?? 0;
    for (const [at, val] of stops) if (at <= pct) v = val; // step-end: hold until the next stop
    return v;
  };
}
const glyphFns = [0, 1, 2, 3, 4, 5].map((i) => frameOf(`working-glyph-${i}`));
const cycle = [];
let oneAtATime = glyphFns.every(Boolean);
for (let f = 0; f < 12 && oneAtATime; f += 1) {
  const pct = ((f + 0.5) / 12) * 100;
  const on = glyphFns.map((fn, i) => (fn(pct) === 1 ? i : -1)).filter((i) => i >= 0);
  if (on.length !== 1) oneAtATime = false;
  else cycle.push(on[0]);
}
check(
  '§2 the glyph shows exactly one frame at a time across the whole cycle',
  oneAtATime,
  'a frame with zero or two glyphs lit',
);
check(
  '§2 the glyph cycle runs forward then back (0 1 2 3 4 5 5 4 3 2 1 0)',
  cycle.join(' ') === '0 1 2 3 4 5 5 4 3 2 1 0',
  `got: ${cycle.join(' ')}`,
);

// A frame that a font may resolve from the COLOR emulation is not the same
// animation on every platform: U+2733 renders on iOS as a white asterisk on a
// GREEN rounded square, so the Supervisor's wait was green on a phone and
// monochrome on a desktop (operator-observed 2026-09-21). This is invisible
// to a Mac-rendered read of the source, so the gate must decide it by
// CODEPOINT. Every frame that is in the emoji set must carry U+FE0E
// (VARIATION SELECTOR-15, text presentation) — and the stylesheet must say
// the same thing for engines that honour font-variant-emoji.
// Decided by the Unicode property, never a hand-list: the first cut of this
// arm listed U+2736 as at-risk and it is NOT Emoji=true, so a hand-list both
// over- and under-reports. Node's ICU carries the real table.
const IS_EMOJI = /\p{Emoji}/u;
// ASCII digits, # and * are Emoji=true but only inside a keycap sequence.
const KEYCAP_BASE = new Set([...'0123456789#*'].map((c) => c.codePointAt(0)));
const atRisk = (ch) => IS_EMOJI.test(ch) && !KEYCAP_BASE.has(ch.codePointAt(0));
const glyphLiteral = (primitive ?? '').match(/const GLYPHS = \[([^\]]*)\]/)?.[1] ?? '';
const frames = [...glyphLiteral.matchAll(/'([^']*)'/g)].map((m) => m[1]);
const unguarded = frames.filter((f) => {
  if (!atRisk(f)) return false;
  return !f.includes('\uFE0E');
});
check(
  '§2 every emoji-set frame carries U+FE0E, so no platform draws it in colour',
  frames.length > 0 && unguarded.length === 0,
  frames.length === 0
    ? 'could not read GLYPHS from the primitive'
    : `unguarded: ${unguarded.map((f) => 'U+' + f.codePointAt(0).toString(16).toUpperCase()).join(', ')}`,
);
check(
  '§2 the glyph asks for text presentation in CSS too',
  /\.working-glyph\s*\{[^}]*font-variant-emoji:\s*text/.test(css),
  'font-variant-emoji: text is missing from .working-glyph',
);

// ── §3 no hand-drawn wait remains in a block a member reads ─────────────────
// A wordless full-pane spinner: a centred div whose only child is a lucide
// spinner. A worded one: a div (not a button — a control acknowledging itself
// is micro-feedback, ADR-651 D5) holding a lucide spinner and trailing prose.
const wordless = /justify-center[^>]*>\s*<Loader2[^>]*\/>\s*<\/div>/g;
const worded = /<div[^>]*>\s*<Loader2[^>]*\/>\s*(\{`[^`]*`\}|[^<{}]+)<\/div>/g;
const offenders = [];
for (const [p, src] of sources) {
  if (p === PRIMITIVE) continue;
  for (const m of src.matchAll(wordless)) offenders.push(`${p}: wordless spinner`);
  for (const m of src.matchAll(worded)) offenders.push(`${p}: ${m[0].replace(/\s+/g, ' ').slice(0, 80)}`);
}
check('§3 no hand-drawn wait block outside the primitive', offenders.length === 0, offenders.join('\n      '));
const pulses = sources.filter(([, s]) => /animate-pulse/.test(s)).map(([p]) => p);
check('§3 the pulse-block skeleton idiom is gone', pulses.length === 0, pulses.join(', '));
const loadingText = sources
  .filter(([p, s]) => p !== PRIMITIVE && /<p[^>]*>\s*Loading(\.\.\.|…)\s*<\/p>/.test(s))
  .map(([p]) => p);
check('§3 no bare "Loading" paragraph stands in for a wait', loadingText.length === 0, loadingText.join(', '));

// ── §4 every wait at the authentication boundary is the primitive ──────────
// The boundary is small and named (ADR-308): pages survive only there.
const boundary = [
  'web/app/(authenticated)/layout.tsx',
  'web/app/auth/login/page.tsx',
  'web/app/auth/callback/page.tsx',
  'web/app/mcp/auth/page.tsx',
  'web/app/mcp/authorize/page.tsx',
  'web/app/admin/layout.tsx',
];
const unbounded = boundary.filter((p) => !/<Working\b/.test(read(p) ?? ''));
check('§4 every boundary wait renders the primitive', unbounded.length === 0, unbounded.join(', '));

// ── §5 the transport bounds what the primitive cannot see ──────────────────
const requestBody = client.match(/async function request<T>\(([\s\S]*?)\n\}/)?.[0] ?? '';
const reqTimeout = Number(client.match(/REQUEST_TIMEOUT_MS\s*=\s*([\d_]+)/)?.[1]?.replace(/_/g, ''));
check(
  '§5 every request() carries a deadline (≤ 2 min) unless the caller brought a signal',
  /AbortSignal\.timeout\(/.test(requestBody) && Number.isFinite(reqTimeout) && reqTimeout <= 120_000,
  `REQUEST_TIMEOUT_MS=${reqTimeout}`,
);
check(
  '§5 the SSE reader has an idle deadline and the lane stream sets one',
  /idleMs/.test(sse) && /sseEvents\([^)]*idleMs/.test(client),
);
const hb = Number(lanes.match(/_HEARTBEAT_S\s*=\s*([\d.]+)/)?.[1]);
check(
  '§5 the server heartbeats the lane stream faster than the client gives up',
  Number.isFinite(hb) && hb > 0 && /: ping|: heartbeat|":"/.test(lanes) && (() => {
    const idle = Number(client.match(/LANE_IDLE_MS\s*=\s*([\d_]+)/)?.[1]?.replace(/_/g, ''));
    return Number.isFinite(idle) && hb * 1000 * 2 <= idle;
  })(),
  `_HEARTBEAT_S=${hb}`,
);

// ── §6 the chat's in-flight row is the patient form ─────────────────────────
const panel = read('web/components/chat-surface/LanePanel.tsx') ?? '';
const steps = read('web/components/chat-surface/StreamSteps.tsx') ?? '';
check('§6 the in-flight bubble is the primitive with its start time', /<Working[^>]*since=/.test(panel));
check('§6 the stepped thread spins the same glyph', /<WorkingGlyph/.test(steps) && !/Loader2/.test(steps));

// ── §7 no glyph in rendered text is left to the font's emoji preference ─────
// The Working glyph was green on iOS because U+2733 is in the Unicode emoji
// set: a font stack that prefers emoji drew it from the COLOUR font while
// every desktop read of the source showed a plain asterisk (b9af95c). The
// same trap is open to any glyph in any rendered string, so the rule is
// repo-wide, decided by CODEPOINT, and it ignores comments — a character that
// never renders cannot have this defect.
//
// Intentional colour is declared, not inferred: a glyph is clean if it is
// Emoji_Presentation=true (colour on EVERY platform, so it is consistent and
// evidently meant as a picture) or if it already carries a variation selector.
// What fails is the in-between: Emoji=true with a text default, which renders
// one way here and another way on a phone.
const IS_PRES = /\p{Emoji_Presentation}/u;
// Blank comment bodies while preserving offsets and string contents. The "//"
// run needs a preceding delimiter so a URL's scheme is not eaten — the
// comment-stripper lesson from the favicon endpoint.
function stripComments(src) {
  const out = src.split('');
  let i = 0, mode = null, quote = null;
  while (i < src.length) {
    const c = src[i], d = src[i + 1];
    if (mode === 'block') { if (c === '*' && d === '/') { mode = null; out[i] = ' '; out[i + 1] = ' '; i += 2; continue; } if (c !== '\n') out[i] = ' '; i++; continue; }
    if (mode === 'line') { if (c === '\n') { mode = null; i++; continue; } out[i] = ' '; i++; continue; }
    if (quote) { if (c === '\\') { i += 2; continue; } if (c === quote) quote = null; i++; continue; }
    if (c === '"' || c === "'" || c === '`') { quote = c; i++; continue; }
    if (c === '/' && d === '*') { mode = 'block'; out[i] = ' '; out[i + 1] = ' '; i += 2; continue; }
    if (c === '/' && d === '/' && (i === 0 || /[\s({[;,=>]/.test(src[i - 1]))) { mode = 'line'; out[i] = ' '; i++; continue; }
    i++;
  }
  return out.join('');
}
const emojiOffenders = [];
for (const [p, raw] of sources) {
  const src = stripComments(raw);
  src.split('\n').forEach((line, i) => {
    const chars = [...line];
    chars.forEach((ch, ci) => {
      if (ch.codePointAt(0) < 0x00a1 || !atRisk(ch)) return;
      if (IS_PRES.test(ch)) return; // colour everywhere: consistent by construction
      const nx = chars[ci + 1]?.codePointAt(0);
      if (nx === 0xfe0e || nx === 0xfe0f) return; // declared
      emojiOffenders.push(`${p}:${i + 1} U+${ch.codePointAt(0).toString(16).toUpperCase().padStart(4, '0')} ${ch}`);
    });
  });
}
check(
  '\u00a77 no rendered glyph is left to the font\'s emoji preference (add U+FE0E)',
  emojiOffenders.length === 0,
  emojiOffenders.join('\n      '),
);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
