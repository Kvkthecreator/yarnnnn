// EXECUTING check of ADR-485 — the frame a percent is a percent of.
//
// This is the gate class the audit found missing. Every Studio gate before it
// asserted the SHAPE of the source (a symbol exists, a value is in a registry,
// a call site routes through the one door). test_adr461_geometry.py has 47 such
// checks and asserts, correctly, that the committed value is "a PERCENT OF THE
// FRAME, not a pixel" — while never asking WHICH RECTANGLE the frame is. The
// defect lived in exactly that gap for as long as the gate has been green.
//
// So this one runs the REAL commit bodies, extracted from projection.ts, over a
// synthetic frame whose padding is known, and asserts the ROUND TRIP: what CSS
// would paint from the committed value equals what the member drew. Each
// section ships a FALSIFIER that restores the pre-fix arithmetic and asserts
// the check goes red — a gate that cannot fail is not evidence.
import { readFileSync } from 'fs';

const src = readFileSync('web/components/workspace/viewers/projection.ts', 'utf8');

function extractFn(name) {
  const i = src.indexOf(`function ${name}(`);
  if (i < 0) throw new Error(`ADR-485 gate: function ${name} not found in projection.ts`);
  // Brace-match from the signature's opening brace.
  let d = 0, start = src.indexOf('{', i);
  for (let j = start; j < src.length; j++) {
    if (src[j] === '{') d++;
    else if (src[j] === '}') { d--; if (d === 0) return src.slice(i, j + 1); }
  }
  throw new Error(`ADR-485 gate: could not brace-match ${name}`);
}

/** Strip comments before asserting an ABSENCE. A source that documents the
 *  rectangle it no longer draws will match a bare regex looking for that
 *  rectangle — the assertion reads its own explanation and passes (or fails)
 *  for the wrong reason. Every `!/.../` check below runs on stripped source. */
function stripComments(s) {
  return s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '');
}

let pass = 0, fail = 0;
const t = (label, cond) => { console.log((cond ? '[PASS] ' : '[FAIL] ') + label); cond ? pass++ : fail++; };

// ── The world: a deck slide at the live skin's geometry ────────────────────
// .slide { width:992px; height:558px; padding:3.5rem 4rem } under the kernel's
// global box-sizing:border-box. These are the numbers from the live artifact.
const PAD_X = 64, PAD_Y = 56, BORDER = 0;
const FRAME = { left: 0, top: 0, width: 992, height: 558 };
const CONTENT_W = FRAME.width - 2 * PAD_X;   // 864 — what width:% resolves against
const CONTENT_H = FRAME.height - 2 * PAD_Y;  // 446 — what height:% resolves against

const frameEl = {
  getBoundingClientRect: () => ({ ...FRAME, right: FRAME.width, bottom: FRAME.height }),
};
const stubs = {
  getComputedStyle: () => ({
    paddingLeft: PAD_X + 'px', paddingRight: PAD_X + 'px',
    paddingTop: PAD_Y + 'px', paddingBottom: PAD_Y + 'px',
    borderLeftWidth: BORDER + 'px', borderRightWidth: BORDER + 'px',
    borderTopWidth: BORDER + 'px', borderBottomWidth: BORDER + 'px',
  }),
  zf: () => 1,
};

const frameRects = new Function(
  'getComputedStyle', 'zf',
  extractFn('frameRects') + '; return frameRects;',
)(stubs.getComputedStyle, stubs.zf);

// ── 1. frameRects names the two rectangles the CSS box model actually uses ──
const f = frameRects(frameEl);
t('frameRects: contentW is the box width:% resolves against (864, not 992)', f.contentW === CONTENT_W);
t('frameRects: contentH is the box height:% resolves against (446, not 558)', f.contentH === CONTENT_H);
t('frameRects: padW is the box left:% resolves against (992 — no border)', f.padW === 992);
t('frameRects: padLeft is the origin left:% measures FROM', f.padLeft === 0);

// ── 2. THE ROUND TRIP: drag-to-fill commits 100 and the block does not move ──
// The member drags the east handle to the true right edge of the content
// column. `br.width` is therefore the content width. What does the commit say,
// and what would CSS paint back from it?
const commitW = (drawnPx) => Math.round((drawnPx / f.contentW) * 100);
const paintW = (pct) => (pct / 100) * CONTENT_W;

const drawn = CONTENT_W;                 // the member fills the column
const committed = commitW(drawn);
const painted = paintW(committed);
t('round trip: drag-to-fill commits 100%', committed === 100);
t('round trip: the block does not move on release (painted === drawn)', Math.abs(painted - drawn) < 0.5);

// The ratchet: repeat the same gesture five times. Pre-fix this decayed
// 100 -> 87 -> 76 -> 66 -> 57 (measured in Chrome). It must now be a fixpoint.
let v = 100, trail = [100];
for (let i = 0; i < 5; i++) { v = commitW(paintW(v)); trail.push(v); }
t(`round trip: five repeats do not decay (${trail.join(' -> ')})`, trail.every((x) => x === 100));

// Height, which was worse (20% loss per drag against width's 13%).
const commitH = (px) => Math.round((px / f.contentH) * 100);
t('round trip: height drag-to-fill commits 100%', commitH(CONTENT_H) === 100);

// ── 2b. D6: THE EAST/SOUTH ORIGIN — can a block reach its frame's edge? ─────
// The round trip above proves the DENOMINATOR. It says nothing about the
// ORIGIN, and that is where the defect lived for as long as this gate has been
// green: `pct = (e.clientX - br.left) / f.contentW` measured from the BLOCK's
// own left edge and divided by the FRAME's content width. For a block laid out
// flush at the content-left the two agree — which is why every synthetic case
// here passed. For a block INSET from it (a flow block in a padded container,
// a `.col` offset by its gap) they do not, and the value is short by exactly
// the inset: the member drags to the true right edge and the number stops
// below 100, so `maxPct = 100` never binds and full width is unreachable.
{
  const INSET = 120; // the block sits 120px right of the frame's content-left
  const blockLeft = f.contentLeft + INSET;
  const contentRight = f.contentLeft + f.contentW;

  // The member drags the EAST handle to the frame's true content-right edge.
  const fixedPct = ((contentRight - f.contentLeft) / f.contentW) * 100;
  const oldPct = ((contentRight - blockLeft) / f.contentW) * 100;

  t('D6: frameRects names the content ORIGIN, not only the content WIDTH',
    f.contentLeft === PAD_X && f.contentTop === PAD_Y);
  t('D6: dragging east to the frame edge reaches 100% (frame-relative origin)',
    Math.round(fixedPct) === 100);
  t(`FALSIFIER: the block-relative origin tops out at ${Math.round(oldPct)}%, short by the inset`,
    Math.round(oldPct) === Math.round(100 - (INSET / f.contentW) * 100) && oldPct < 100);
  // The same defect on the vertical axis — the south drag is the twin.
  const blockTop = f.contentTop + 60;
  const contentBottom = f.contentTop + f.contentH;
  t('D6: dragging south to the frame edge reaches 100%',
    Math.round(((contentBottom - f.contentTop) / f.contentH) * 100) === 100);
  t('FALSIFIER: the block-relative vertical origin cannot reach 100%',
    ((contentBottom - blockTop) / f.contentH) * 100 < 100);

  // And the SHIPPED source must use the origin, not the block's own edge.
  const body = stripComments(extractFn('resizeMove'));
  t('D6: resizeMove measures width from f.contentLeft', /f\.contentLeft/.test(body));
  t('D6: resizeMove measures height from f.contentTop', /f\.contentTop/.test(body));
  t('D6: no east/south drag divides a block-relative delta by contentW',
    !/e\.clientX\s*-\s*br\.left/.test(body) && !/e\.clientY\s*-\s*br\.top/.test(body));
}

// ── 2c. D6: the OVERLAY draws the rectangle the math uses ──────────────────
// The green frame outline is the affordance the member aims at. It drew the
// BORDER box while every percent resolves against the CONTENT box, so it was
// larger than the addressable area by the frame's padding — the member aimed
// at green, the clamp stopped them short, and the two rectangles disagreed.
{
  // Strip comments before asserting an ABSENCE: this file documents the
  // rectangle it no longer draws, and a bare regex matched its own explanation.
  const body = stripComments(extractFn('showFrame'));
  t('D6: showFrame reads frameRects (the one place the box model is answered)',
    /frameRects\(/.test(body));
  t('D6: showFrame no longer draws the raw border box',
    !/frame\.getBoundingClientRect\(\)/.test(body));
  t('D6: it paints the content box, so the green outline IS 100%',
    /f\.contentW/.test(body) && /f\.contentLeft/.test(body));
  // FALSIFIER: the border box overstates the addressable width by the padding.
  t('FALSIFIER: the border box overstates the frame by 2x padding (992 vs 864)',
    FRAME.width - f.contentW === 2 * PAD_X);
}

// ── 3. FALSIFIER — restore the border-box denominator, the ratchet returns ──
const badCommitW = (px) => Math.round((px / FRAME.width) * 100);
let bv = 100; const badTrail = [100];
for (let i = 0; i < 5; i++) { bv = badCommitW(paintW(bv)); badTrail.push(bv); }
t(`FALSIFIER: the border-box denominator DOES decay (${badTrail.join(' -> ')})`,
  badTrail[1] === 87 && badTrail[badTrail.length - 1] < 60);
t('FALSIFIER: and its first drag loses ~112px', Math.abs(CONTENT_W - paintW(badCommitW(CONTENT_W)) - 112.3) < 1);

// ── 4. The source no longer divides a measure by a raw border-box rect ──────
// The arithmetic above proves the FORMULA; this proves the SHIPPED CODE uses
// it. resizeEnd/moveEnd must not reach for frame.getBoundingClientRect().
for (const fn of ['resizeEnd', 'moveEnd', 'resizeMove', 'moveMove']) {
  const body = stripComments(extractFn(fn));
  t(`${fn}: takes its rectangles from frameRects()`, /frameRects\(/.test(body));
  t(`${fn}: no raw frame.getBoundingClientRect() denominator`,
    !/frame\.getBoundingClientRect\(\)/.test(body));
}
{
  const body = extractFn('resizeEnd');
  t('resizeEnd: width divides by contentW (what width:% resolves against)', /f\.contentW/.test(body));
  t('resizeEnd: height divides by contentH', /f\.contentH/.test(body));
  t('resizeEnd: x divides by padW (what left:% resolves against)', /f\.padW/.test(body));
}

// ── 5. D3 — the clamp reads the SERVED bound, not a hardcoded 1 ─────────────
{
  const body = extractFn('resizeMove');
  t('resizeMove: width clamps from the served bound (MEASURE_MIN.w)', /MEASURE_MIN\.w/.test(body));
  t('resizeMove: height clamps from the served bound (MEASURE_MIN.h)', /MEASURE_MIN\.h/.test(body));
  t('resizeMove: no hardcoded Math.max(1, ...) floor survives',
    !/Math\.max\(1,\s*Math\.min/.test(body));
  const commit = extractFn('resizeEnd');
  t('resizeEnd: the COMMIT clamps too, so the receipt states what landed',
    /clampMeasure\(/.test(commit));
}
// The bound must arrive as DATA from the kernel, never be re-derived here.
t('D3: the served bounds reach the runtime via __yarnnnMeasureBounds',
  src.includes('__yarnnnMeasureBounds') && src.includes('measureBounds'));
{
  // FALSIFIER: a 3% width under the served w.min=10 must clamp to 10, and the
  // fallback must stay permissive when the kernel served nothing.
  const clamp = (bounds, key, v) => {
    const b = bounds[key];
    const mn = b && typeof b.min === 'number' ? b.min : 0;
    const mx = b && typeof b.max === 'number' ? b.max : 100;
    return Math.max(mn, Math.min(mx, v));
  };
  t('D3: a 3% width clamps to the served floor of 10', clamp({ w: { min: 10, max: 100 } }, 'w', 3) === 10);
  t('D3: height keeps its own floor of 1 (the axes honestly differ)',
    clamp({ h: { min: 1, max: 100 } }, 'h', 3) === 3);
  t('FALSIFIER: the hardcoded floor of 1 would have let 3% through',
    Math.max(1, Math.min(100, 3)) === 3);
}

// ── 6. D2 — the clear-grain matches the write-grain ─────────────────────────
{
  const ops = readFileSync('web/components/authoring/artifactOps.ts', 'utf8');
  const i = ops.indexOf('function returnToFlow(');
  const body = ops.slice(i, ops.indexOf('\n}', i));
  for (const k of ['x', 'y', 'w', 'h', 'z']) {
    t(`returnToFlow: clears data-${k} (setGeometry writes all five as one unit)`,
      /keys\s*=\s*\[[^\]]*'x'[^\]]*'y'[^\]]*'w'[^\]]*'h'[^\]]*'z'/.test(body));
  }
  t('returnToFlow: strips every geometry custom property, not just --yx/--yy',
    ops.includes("'--yw:'") && ops.includes("'--yh:'") && ops.includes("'--yz:'"));
  // FALSIFIER: the pre-fix version kept --yw, which a re-arrange then re-based.
  // 60% of the slide's content box (518px) vs 60% of a flex:1 column (~412px).
  const colW = (CONTENT_W - 40) / 2;
  t('FALSIFIER: a surviving --yw:60% re-bases from 518px to 247px on a carry',
    Math.round(0.6 * CONTENT_W) === 518 && Math.round(0.6 * colW) === 247);
}

// ── 7. D4 — the positioned test reads BOTH attributes, as the kernel does ───
{
  const tab = readFileSync('web/components/authoring/StudioDesignTab.tsx', 'utf8');
  // ADR-511 D4 loosened the spelling pin (the Position row rewrote the
  // render); the invariant is unchanged — the positioned test reads BOTH.
  t("D4: 'Return to flow' requires data-x AND data-y (the kernel rule)",
    /hasAttribute\('data-x'\)\s*&&\s*\w+\.hasAttribute\('data-y'\)/.test(tab));
}

// ── 8. D5 — the dead export is gone, with its false promise ────────────────
// The DECLARATION must be gone; the tombstone comment explaining why is
// deliberately kept (a bare `!src.includes(...)` would forbid recording the
// reason, which is the opposite of what this repo wants).
t('D5: STAGE_DEFAULT_W (exported, zero importers, promised a mapping that never existed) is deleted',
  !/^\s*(export\s+)?const\s+STAGE_DEFAULT_W\b/m.test(src));

// ── 9. The ADR-461 D4 aperture is UNCHANGED — this ADR widens nothing ──────
{
  const py = readFileSync('api/services/authoring.py', 'utf8');
  // ADR-544 D3 — asserted as a SET, not a literal. The aperture must never
  // WIDEN past frame-bounded grains (ADR-461 D4: a reflowing page has no frame
  // to bound a measure). It narrowed instead: position moved from `staged`
  // (either frame) to `artboard` (IMAGES only), so the deck's free placement is
  // gone while its SIZE measures still admit `staged`. Pinning the literal set
  // made a NARROWING read as a violation.
  const grains = /MEASURE_GRAINS = \{([^}]*)\}/.exec(py)?.[1] ?? '';
  const declared = new Set(
    [...grains.matchAll(/"([a-z]+)"/g)].map((m) => m[1]),
  );
  t('aperture: measures apply to frame-bounded grains only (never a reflowing page)',
    declared.size > 0 &&
      [...declared].every((g) => ['staged', 'artboard', 'media'].includes(g)));
  t('aperture: free POSITION is artboard-scoped — a deck block holds a place, not a coordinate',
    /"x":\s*\{[^}]*"grains":\s*\("artboard",\)/s.test(py) ||
      /"grains":\s*\("artboard",\)/.test(py));
  t('aperture: the kernel measure rules are still .slide/media-scoped',
    py.includes('.slide [data-w]') && !/\[data-template="document"\][^\n]*data-w/.test(py));
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
