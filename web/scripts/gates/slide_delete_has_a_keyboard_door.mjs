/** A selected slide answers the Delete key.
 *
 * The block grain always worked; the PAGE grain never did. The click ladder's
 * miss-branch and the Esc-walk both SELECT a page — the member sees the slide
 * framed — but the runtime's key handler read `data-block-id` off the subject
 * and returned early when it was absent, two lines before the Delete branch it
 * would otherwise have reached. Meanwhile the parent had owned `deletePage`
 * all along, behind exactly one entrance: the Design tab.
 *
 * So the gesture the medium advertises was refused WITHOUT A WORD — the
 * silent-no-op class this codebase already names (ADR-544 D5.1's
 * `yarnnn-refused` notice). This was never a regression; the door was simply
 * never built.
 *
 * What this gate holds:
 *   1. the runtime posts a page-grain verb, addressed by INDEX (a page has no
 *      block id to carry — that is the whole reason the old guard swallowed it);
 *   2. the branch precedes the block-id guard, or it is unreachable;
 *   3. the parent routes it to the EXISTING page verb — one op, N entrances
 *      (ADR-511 D5), never a second delete path;
 *   4. the message discriminates on the ABSENCE of a block id, so the block
 *      grain keeps its own branch untouched.
 *
 * Run from the REPO ROOT:
 *   node web/scripts/gates/slide_delete_has_a_keyboard_door.mjs
 */
import { readFileSync } from 'node:fs';

let pass = 0;
let fail = 0;
const t = (label, cond, detail = '') => {
  if (cond) {
    pass++;
    console.log(`[PASS] ${label}`);
  } else {
    fail++;
    console.log(`[FAIL] ${label}${detail ? ': ' + detail : ''}`);
  }
};

const projection = readFileSync('web/components/workspace/viewers/projection.ts', 'utf8');
const canvas = readFileSync('web/components/authoring/StudioCanvas.tsx', 'utf8');
const surface = readFileSync('web/components/authoring/StudioSurface.tsx', 'utf8');

// ── 1. The runtime speaks for the page grain ───────────────────────────────
t(
  'the runtime posts a page-grain delete',
  /blk\.matches\(PAGE_SEL\)/.test(projection) &&
    /slideIndex: slideIndexOf\(blk\)/.test(projection) &&
    /pageIndex: pageIndexOf\(blk\)/.test(projection),
  'a page carries no block id — it is addressed by index, like every page op',
);

// ── 2. Reachability — the defect was ORDER, not absence ────────────────────
// The old handler returned on `if (!id) return;` before any Delete branch. A
// page branch placed after that guard would be dead code that reads as a fix.
const handlerStart = projection.indexOf("var blk = selectedBlock();");
const pageBranch = projection.indexOf('blk.matches(PAGE_SEL)', handlerStart);
const idGuard = projection.indexOf('if (!id) return;', handlerStart);
t('the key handler is locatable', handlerStart > 0);
t(
  '[FALSIFIER] the page branch PRECEDES the block-id guard',
  pageBranch > 0 && idGuard > 0 && pageBranch < idGuard,
  'after the guard it is unreachable — the exact shape of the original defect',
);

// ── 3. The bridge, discriminating on the absence of a block id ─────────────
t(
  'the bridge routes the page grain separately',
  /d\.type === 'yarnnn-key-verb' && d\.blockId === undefined/.test(canvas) &&
    /onPageKeyVerb\?\.\(/.test(canvas),
  'the block branch tests for a string id; the page branch takes what it leaves',
);
t(
  'the block grain keeps its own branch intact',
  /d\.type === 'yarnnn-key-verb' && typeof d\.blockId === 'string'/.test(canvas),
  'the page door must not widen the block guard',
);

// ── 4. One op, N entrances ─────────────────────────────────────────────────
t(
  'the parent routes the key to the EXISTING page verb',
  /const handlePageKeyVerb = useCallback/.test(surface) &&
    /\(html\) => deletePage\(html, \{ blockId: null, slideIndex, pageIndex \}\)/.test(surface),
  'a second delete implementation is the thing this must not become',
);
t(
  'the surface actually MOUNTS the door',
  /onPageKeyVerb=\{handlePageKeyVerb\}/.test(surface),
  'an unmounted handler is a fix that never runs — the vacuous-pass shape',
);
t(
  '[FALSIFIER] the key verb takes the REPORTED page, not the ambient anchor',
  /deletePage\(html, \{ blockId: null, slideIndex, pageIndex \}\)/.test(surface) &&
    !/handlePageKeyVerb[\s\S]{0,400}?deletePage\(html, anchor\)/.test(surface),
  'a verb about "the page this keystroke named" must say so, not infer it',
);

// ── 5. The refusal it replaces was SILENT ──────────────────────────────────
// Guard against the door regressing into a no-op: the branch must consume the
// key (preventDefault) and post, or the member gets the browser's back-nav on
// Backspace instead of a delete.
const branchBody = projection.slice(pageBranch, pageBranch + 600);
t(
  'the page branch consumes the key it answers',
  /e\.preventDefault\(\)/.test(branchBody) && /parent\.postMessage/.test(branchBody),
  'Backspace unconsumed is browser navigation, not a no-op',
);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
