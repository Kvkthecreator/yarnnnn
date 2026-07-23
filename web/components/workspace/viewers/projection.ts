'use client';

/**
 * The reference projection pass (ADR-440 D5; re-homed by ADR-441 D3).
 *
 * An artifact cites workspace objects by REFERENCE (`data-ref` = the living
 * path, `data-ref-rev` = the last-resolved pin), never by copy. This pass
 * walks the HTML, resolves every citation against the commons, and rewrites
 * the element so a fully sandboxed iframe (no scripts, no network reach into
 * the API) can display it.
 *
 * ADR-441 D3: the projection is a property of the FILE TYPE, not of any one
 * mount — "an app owns file types and draws their content" (ADR-436), and
 * drawing an HTML file that cites the commons includes resolving its
 * citations. It therefore lives in the viewers layer and runs in TWO places:
 *   - the Web Viewer app (`useArtifactProjection` below) — so every FileBody
 *     mount (ArtifactCard, FileOpenModal, the Files detail) renders citations
 *     identically to the Studio canvas;
 *   - the Studio canvas, which adds its mount-specific pointer runtime via
 *     `opts.pointer` (deixis under sandbox="allow-scripts").
 *
 * Resolution rules (ADR-440 D5):
 *  - `./…` refs are ARTIFACT-RELATIVE (resolved against the artifact's own
 *    folder — the project moves as a unit); everything else is a workspace
 *    path (leading `/workspace/` optional, same normalization as getFile).
 *  - Images: binary → signed blob URL (the single content_url consumer path,
 *    ADR-395/427); SVG text → inline data: URL.
 *  - `data-ref-kind="table"` or a `.csv` ref → a rendered read-only table.
 *  - Other text files → escaped <pre> projection (read-only, ADR-440's
 *    OpenDoc guard: references RENDER, they are never embedded editors).
 *  - A dangling path falls back to the pin (`data-ref-rev` → readRevision,
 *    text-native only) and the element is flagged `data-ref-broken` with a
 *    visible marker — broken-but-rendering, never silently absent.
 *
 * Reads only. The pass NEVER writes pins back — pins refresh on authoring
 * turns (the lane), because reads must not write (read-only grants render).
 */

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import type { WorkspaceFile } from '@/types';

function artifactDir(artifactPath: string): string {
  const abs = artifactPath.startsWith('/') ? artifactPath : `/workspace/${artifactPath}`;
  return abs.slice(0, abs.lastIndexOf('/'));
}

function resolveRefPath(ref: string, artifactPath: string): string {
  if (ref.startsWith('./')) {
    // Artifact-relative — normalize `./assets/x.png` against the artifact dir.
    return `${artifactDir(artifactPath)}/${ref.slice(2)}`;
  }
  return ref.startsWith('/') ? ref : `/workspace/${ref}`;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** Naive CSV → table rows (v1: no quoted-comma handling — honest ceiling). */
function csvToTableHtml(csv: string, maxRows = 50): string {
  const lines = csv.trim().split(/\r?\n/).filter(Boolean).slice(0, maxRows + 1);
  if (!lines.length) return '<p>(empty table)</p>';
  const [head, ...rows] = lines.map((l) => l.split(','));
  const th = head.map((c) => `<th>${escapeHtml(c.trim())}</th>`).join('');
  const trs = rows
    .map((r) => `<tr>${r.map((c) => `<td>${escapeHtml(c.trim())}</td>`).join('')}</tr>`)
    .join('');
  return `<table><thead><tr>${th}</tr></thead><tbody>${trs}</tbody></table>`;
}

function markBroken(el: Element, ref: string): void {
  el.setAttribute('data-ref-broken', 'true');
  el.innerHTML = `<span style="display:inline-block;padding:0.4rem 0.6rem;border:1px dashed #c66;color:#a44;font-size:0.8rem;border-radius:4px;">citation broken: ${escapeHtml(ref)}</span>`;
}

const IMAGE_EXT = /\.(png|jpe?g|gif|webp|avif)$/i;

/** A workspace-absolute `url("/workspace/…")` inside a stylesheet's text. */
const CSS_WORKSPACE_URL = /url\(\s*["']?(\/workspace\/[^"')]+)["']?\s*\)/g;

/** Resolve the skin's cited binaries (ADR-462 D13) — url()s in the TEXT.
 *
 *  A design system's @font-face points at its own font, and the flatten made
 *  that path workspace-absolute. A browser cannot fetch a workspace path, so
 *  each one is swapped for a signed blob URL — exactly what an <img
 *  data-ref> already gets, just reached through CSS instead of an element.
 *
 *  An SVG resolves to a data: URI (it is text substrate, no bucket); a binary
 *  resolves through content_url. A miss leaves the url() alone: the @font-face
 *  simply fails and the font-family falls back to the stack beside it, which
 *  is what a missing font should do.
 */
async function resolveStyleUrls(el: HTMLStyleElement): Promise<void> {
  const css = el.textContent || '';
  const paths = Array.from(new Set(Array.from(css.matchAll(CSS_WORKSPACE_URL), (m) => m[1])));
  if (!paths.length) return;
  const resolved = new Map<string, string>();
  await Promise.all(
    paths.map(async (p) => {
      try {
        const file = await api.workspace.getFile(p);
        if (p.toLowerCase().endsWith('.svg') && file.content) {
          resolved.set(p, `data:image/svg+xml;charset=utf-8,${encodeURIComponent(file.content)}`);
        } else if (file.content_url) {
          const { url } = await api.documents.blobUrl(file.content_url);
          resolved.set(p, url);
        }
      } catch {
        /* a missing cited asset degrades to the fallback — never a broken skin */
      }
    }),
  );
  if (!resolved.size) return;
  el.textContent = css.replace(CSS_WORKSPACE_URL, (whole, p) =>
    resolved.has(p) ? `url("${resolved.get(p)}")` : whole,
  );
}

async function resolveOne(el: Element, artifactPath: string): Promise<void> {
  // The MARKED style elements (data-skin / data-kernel, ADR-449/453) carry
  // data-ref as an EDGE citation (trace/dependents) — their CSS is already
  // composed in place. Resolving "into" them would replace the skin's CSS
  // with the manifest's text (ADR-456 W3 fix — never touch a style element).
  //
  // But a skin's CSS can CITE binaries its @font-face needs (ADR-462 D13): the
  // flatten rewrites `url("../assets/fonts/X.ttf")` to an absolute workspace
  // path, and a workspace path is not a URL a browser can fetch. So the skin
  // gets its own resolution — url()s INSIDE the text, never the text itself.
  if (el.tagName === 'STYLE') {
    if (el.hasAttribute('data-skin')) await resolveStyleUrls(el as HTMLStyleElement);
    return;
  }
  const ref = el.getAttribute('data-ref') || '';
  if (!ref) return;
  const pin = el.getAttribute('data-ref-rev') || '';
  const kind = el.getAttribute('data-ref-kind') || '';
  const path = resolveRefPath(ref, artifactPath);

  try {
    const file = await api.workspace.getFile(path);
    const isImg = el.tagName === 'IMG';

    if (isImg && path.toLowerCase().endsWith('.svg') && file.content) {
      (el as HTMLImageElement).src =
        `data:image/svg+xml;charset=utf-8,${encodeURIComponent(file.content)}`;
      return;
    }
    if (isImg && file.content_url) {
      const { url } = await api.documents.blobUrl(file.content_url);
      (el as HTMLImageElement).src = url;
      return;
    }
    if (isImg && IMAGE_EXT.test(path) && !file.content_url) {
      markBroken(el, ref); // a binary image with no serving handle yet (ADR-427 Ph1)
      return;
    }
    // ADR-456 W3: a cited page BACKGROUND — the projection does the pixel
    // work (backgroundImage on the projected DOM); the source stays a clean
    // citation + tokens. Never innerHTML here — the band's content lives
    // inside the element, and a failure just renders the band without the
    // image (the tokens still style it).
    if (kind === 'background') {
      if (path.toLowerCase().endsWith('.svg') && file.content) {
        (el as HTMLElement).style.backgroundImage =
          `url("data:image/svg+xml;charset=utf-8,${encodeURIComponent(file.content)}")`;
        return;
      }
      if (file.content_url) {
        const { url } = await api.documents.blobUrl(file.content_url);
        (el as HTMLElement).style.backgroundImage = `url("${url}")`;
      }
      return;
    }
    if (kind === 'table' || path.toLowerCase().endsWith('.csv')) {
      el.innerHTML = csvToTableHtml(file.content || '');
      return;
    }
    if (file.content != null) {
      // Read-only text projection — render, never embed an editor (D5).
      el.innerHTML = `<pre style="white-space:pre-wrap;">${escapeHtml(file.content)}</pre>`;
      return;
    }
    markBroken(el, ref);
  } catch {
    // A dangling BACKGROUND never falls to the text-pin path — the band's
    // children are real content that must not be replaced (ADR-456 W3).
    if (kind === 'background') return;
    // The living path dangled (moved/deleted) — fall back to the pin
    // (text-native only; binary pins harden at ADR-427 Phase 2).
    if (pin) {
      try {
        const rev = await api.workspace.readRevision(path, pin);
        if (rev.content != null) {
          el.setAttribute('data-ref-pinned', 'true');
          if (el.tagName === 'IMG' && path.toLowerCase().endsWith('.svg')) {
            (el as HTMLImageElement).src =
              `data:image/svg+xml;charset=utf-8,${encodeURIComponent(rev.content)}`;
          } else if (kind === 'table' || path.toLowerCase().endsWith('.csv')) {
            el.innerHTML = csvToTableHtml(rev.content);
          } else {
            el.innerHTML = `<pre style="white-space:pre-wrap;">${escapeHtml(rev.content)}</pre>`;
          }
          return;
        }
      } catch {
        /* fall through to broken */
      }
    }
    markBroken(el, ref);
  }
}

// ── The pointer runtime (ADR-440 v1.1 pointing · ADR-443 D6 block grain) ──
//
// Injected into the projected document so the member can POINT at an element
// (deixis, never editing): a click selects the nearest pointable element,
// walks to its enclosing BLOCK (`[data-block]`, ADR-443 D4) when one exists,
// outlines the block, and posts {type:'yarnnn-point', tag, text, dataRef,
// blockId, blockKind} to the parent (StudioCanvas listens). Runs under
// sandbox="allow-scripts" with an OPAQUE origin — no same-origin access, no
// credentials, no top-navigation. The projection pass strips every
// artifact-authored script and inline handler first (D5's no-script rule,
// enforced mechanically), so this is the ONLY code that executes in the
// canvas.

const POINTABLE =
  'h1,h2,h3,h4,p,li,img,figure,figcaption,table,blockquote,pre,[data-ref],[data-block]';

// The TEXT-editable block kinds (ADR-456 W2's Turn-into set): a single click on
// one of these enters edit-at-caret (F4); media/data/structured kinds
// (figure/gallery/table/metrics/chart) stay select-only. Kept in sync with the
// StudioDesignTab TURN_INTO_KINDS + the heading anchor kind. (Declared before
// POINTER_CSS, which derives the cursor:text rule from it.)
const TEXT_KINDS_JS = JSON.stringify(['prose', 'callout', 'quote', 'checklist', 'toggle', 'heading']);

// ── ADR-481 D2/D3: the FLOW pointer chrome ────────────────────────────────
//
// A from-scratch cue set for a continuous writing surface, derived from
// ADR-480's axiom rather than inherited from the Notion benchmark. What the
// paged sheet carries and this one deliberately does NOT:
//
//   • no [data-block]:hover outline — the caret and the I-beam already say
//     where a click lands; boxing prose as the pointer travels re-asserts the
//     enclosure ADR-480 dissolved (the operator's "mouse fights me")
//   • no [data-slot] outline/label and no "+ Add here" — flow serves no
//     arrangements (D1), so there is no slot
//
// What survives, because it still means something: a non-text OBJECT (figure,
// table, chart, gallery, divider) is still an object — selectable, right-
// clickable, addressable — so it keeps the neutral selection outline and the
// pointer cursor. Text is pure caret territory.
const FLOW_POINTER_CSS = `
/* ADR-482 D8: the BROWSER'S focus ring on the flow root is suppressed.
   ADR-480 D1 put contenteditable on <main>/<article>, and a focused editable
   element gets the UA's default focus outline for free — so the whole document
   wore a saturated box for the entire session. It is not our chrome (no rule of
   ours draws it, which is why the earlier passes looking at [data-block] rules
   never found it), but it is chrome we CAUSED, and it says the one thing a
   continuous writing surface never needs to say: "this is the editable region."
   The whole page is. The caret says where you are; a permanent frame around
   everything is the enclosure ADR-480 dissolved, redrawn by the UA.
   Paged is untouched — there the per-block outline is meaningful (one block is
   live at a time), and it is OUR rule, in EDIT_CSS. */
main[contenteditable="true"]:focus, article[contenteditable="true"]:focus,
main[contenteditable="true"]:focus-visible, article[contenteditable="true"]:focus-visible {
  outline: none;
}
/* Text is caret territory — the I-beam is the honest cursor, no outline. */
[data-block] { cursor: text; }
/* Objects stay objects: pointer cursor + a quiet hover cue on the OBJECT
   kinds only (never prose). These are the block kinds a click SELECTS
   rather than places a caret in. */
[data-block="figure"], [data-block="table"], [data-block="chart"],
[data-block="gallery"], [data-block="metrics"], [data-block="divider"],
[data-block="button"] { cursor: pointer; }
[data-block="figure"]:hover, [data-block="table"]:hover, [data-block="chart"]:hover,
[data-block="gallery"]:hover, [data-block="metrics"]:hover {
  outline: 1px dashed rgba(120,115,107,0.4); outline-offset: 2px;
}
/* Selection stays NEUTRAL (ADR-462 D5) — a thin rule, never a saturated box. */
.yarnnn-pointed {
  outline: 1px solid rgba(60,58,54,0.5) !important; outline-offset: 2px;
}
/* ADR-481 D2 — the cold-start hint. CSS-only (:empty on the flow root, no
   script, never serialized): an untouched document says how to reach the
   palette, and the hint vanishes the moment anything is typed. The Notion/
   Craft convention — one line, no persistent chrome. */
main:empty::before, article:empty::before {
  content: 'Type / for blocks, or just start writing';
  color: rgba(120,115,107,0.55);
  font: 400 1rem/1.6 system-ui, sans-serif;
  pointer-events: none;
}
`;

const POINTER_CSS = `
/* The hover cue lights the CLICK GRAIN — the enclosing block, never the raw
   elements inside it (2026-07-21, the flow-mouse pass). The old rule outlined
   every pointable element individually (h3:hover, p:hover), so a prose block
   holding a heading + sentence grew THREE competing dashed boxes and a
   pointer cursor over text whose click means "place the caret" — the noise
   the operator read as "mouse actions not working as intended". The ladder
   resolves a click to the block; the cue must agree with the ladder.
   :has() keeps only the INNERMOST hovered block lit (a nested block does not
   double-light its ancestor). */
[data-block]:hover:not(:has([data-block]:hover)) {
  outline: 1px dashed rgba(120,115,107,0.4); outline-offset: 2px;
}
[data-block] { cursor: pointer; }
/* Text blocks invite the CARET, not a click-target: the I-beam is the honest
   cursor for click-to-type (Notion), pointer stays for object-like blocks. */
${JSON.parse(TEXT_KINDS_JS).map((k: string) => `[data-block="${k}"]`).join(', ')} { cursor: text; }
/* Bare pointables OUTSIDE any block (legacy/unblocked content + citation
   islands) keep the old per-element cue — there is no block to light. */
${POINTABLE.split(',').map((s) => `${s}:hover:not([data-block] *):not([data-block])`).join(',\n')} {
  outline: 1px dashed rgba(120,115,107,0.4); outline-offset: 2px; cursor: pointer;
}
/* QUIET WHILE TYPING: inside the block being edited, no hover chrome at all —
   the caret owns it (matches PowerPoint/Notion: no boxes chase the mouse
   through text you are writing). Slot outlines + labels also rest while any
   edit is live; the green tag reappears the moment the caret leaves. */
[contenteditable="true"] :hover, [data-block][contenteditable="true"]:hover {
  outline: none !important;
}
body:has([contenteditable="true"]) [data-slot]:hover { outline: none; }
body:has([contenteditable="true"]) [data-slot]:hover::after { content: none; }
/* Selection is NEUTRAL (ADR-462 D5). A saturated outline reads as the app
   asserting itself over the member's page — PowerPoint/Keynote/Figma all draw
   selection as a thin neutral rule, and reserve colour for what is NOT your
   content. The accent survives where it means something the page cannot say
   for itself: the editing state (you are typing into this), and the transient
   gesture chrome (drop-line, divider). */
.yarnnn-pointed {
  outline: 1px solid rgba(60,58,54,0.5) !important; outline-offset: 2px;
}
/* ADR-453 D5: slots are the interaction surface — outline + name on hover
   (the Wix section-hover). position:relative only anchors the label. */
[data-slot] { position: relative; }
[data-slot]:hover {
  outline: 1px dashed rgba(16,185,129,0.55); outline-offset: 2px;
}
[data-slot]:hover::after {
  content: attr(data-slot); position: absolute; top: -1rem; left: 0;
  font: 500 0.6rem system-ui, sans-serif; letter-spacing: 0.06em;
  text-transform: uppercase; color: rgba(16,185,129,0.9); pointer-events: none;
}
/* ADR-447 Phase 4: empty-slot "+ Add here" affordance. */
.yarnnn-add-here {
  display: block; width: 100%; margin: 0.5rem 0; padding: 0.6rem;
  border: 1px dashed rgba(120,115,107,0.45); border-radius: 6px;
  background: rgba(120,115,107,0.03); color: rgba(90,86,80,0.85);
  font: 500 0.8rem system-ui, sans-serif; cursor: pointer; text-align: center;
}
.yarnnn-add-here:hover {
  background: rgba(var(--yarnnn-chrome-accent-rgb),0.06);
  border-color: rgba(var(--yarnnn-chrome-accent-rgb),0.45);
  color: var(--yarnnn-chrome-accent);
}
`;

// ── The deck STAGE (ADR-447 D7.7 canvas-side fix) ─────────────────────────
//
// A deck slide's baked skin is `.slide { width:min(100%,62rem); aspect-ratio:16/9 }`.
// In the Studio's narrow center column that sizes the slide off the COLUMN
// width — a ~390px column yields a ~220px-tall slide whose padded, centered
// content overflows the `overflow:hidden` box and clips to visual emptiness
// (the reported "middle not displaying"). The navigator already solved this
// for thumbnails by pinning the slide to its natural 16:9 box and scaling the
// whole doc; the canvas needs the same. This block (injected ONLY in the
// canvas's `pointer` mode — the composed/export/thumbnail views keep the raw
// skin) fixes each deck slide to its natural landscape box (SLIDE_W×SLIDE_H,
// the navigator's numbers), so a slide is a STAGE that the zoom control scales
// to fit, never a box that collapses with the column. The parent auto-fits the
// initial zoom to the column width (StudioCanvas), so a deck fills the canvas
// on open without the operator touching the zoom.
const DECK_STAGE_W = 992; // 62rem — the slide's natural landscape width
const DECK_STAGE_H = Math.round((DECK_STAGE_W * 9) / 16); // 16:9 → 558

const DECK_STAGE_CSS = `
/* ADR-482 D4: the app-chrome accent, declared ONCE. It was a bare #6366f1
   literal at six independent sites across four separately-injected sheets, so
   nothing made the count auditable or a change single-edit. Declared here
   because this sheet is unconditionally concatenated ahead of the others in
   every pointer projection. This is chrome the app draws — never document
   content, which takes its color from the design system. */
:root {
  --yarnnn-chrome-accent: #6366f1;
  --yarnnn-chrome-accent-rgb: 99,102,241;
}
html[data-template="deck"] body { display: flex; flex-direction: column; align-items: center; }
html[data-template="deck"] .slide {
  width: ${DECK_STAGE_W}px !important;
  height: ${DECK_STAGE_H}px !important;
  aspect-ratio: auto !important;
  flex: 0 0 auto;
}
`;

// ADR-472 D3 — the IMAGES stage: a fixed-SIZE box whose real pixel dimensions
// ride the root as data-w/data-h, with `--stage-w`/`--stage-h` written INLINE
// on that same root at creation (`services/images/stage.py::stage_root_attrs`).
// The stage skin consumes those custom properties by inheritance, so this rule
// only needs to give the stage its layout box.
//
// ADR-485 D5: the comment here used to claim this rule MAPPED data-w → --stage-w
// as a retrofit, and exported a STAGE_DEFAULT_W constant for it. Neither was
// real — the mapping was never written and the constant had zero importers.
// Deleted rather than implemented: every live stage carries the mapping inline,
// so there is no instance in hand. If a stage ever loses its root style, that
// is the ADR that should build the retrofit, against the real case.
//
// This REPLACES ADR-471's data-aspect → --stage-aspect slug mapping, which
// could only ever enumerate wide/portrait/story because a property token's
// values must be enumerable (ADR-461). A design tool needs a continuous
// dimension, so dimensions became data and the token was deleted (ADR-472 D3).
const IMAGE_STAGE_CSS = `
html[data-template="image"] body { display: flex; flex-direction: column; align-items: center; }
html[data-template="image"] .slide { flex: 0 0 auto; }
`;

const POINTER_SCRIPT = `
(function () {
  var SEL = ${JSON.stringify(POINTABLE)};
  var PAGE_SEL = 'section.slide, [data-arrange]';
  var TEXT_KINDS = ${TEXT_KINDS_JS};
  var cur = null;

  function slideIndexOf(el) {
    var slide = el && el.closest ? el.closest('section.slide') : null;
    if (!slide) return null;
    var all = document.querySelectorAll('section.slide');
    for (var i = 0; i < all.length; i++) { if (all[i] === slide) return i; }
    return null;
  }
  // ADR-453: the page index — document order over PAGE_SEL, matching the
  // parent's arrangedPageAt so ops anchor on the same element.
  function pageIndexOf(el) {
    var page = el && el.closest ? el.closest(PAGE_SEL) : null;
    if (!page) return null;
    var all = document.querySelectorAll(PAGE_SEL);
    for (var i = 0; i < all.length; i++) { if (all[i] === page) return i; }
    return null;
  }
  function arrangeOf(el) {
    var page = el && el.closest ? el.closest('[data-arrange]') : null;
    return page ? (page.getAttribute('data-arrange') || null) : null;
  }

  document.addEventListener('click', function (e) {
    var t = e.target;
    // ADR-446 + F4: while a block is being edited, a click INSIDE that same
    // block just places the caret natively (return early). A click in a
    // DIFFERENT block must switch the caret there (Notion: click any text moves
    // the caret) — so fall through to the handler below, which enters the new
    // block. The old behavior returned on ANY click while editing, which
    // stranded the caret in the first block once single-click-to-edit landed.
    var editingId = window.__yarnnnEditingId ? window.__yarnnnEditingId() : null;
    if (editingId != null) {
      var inSameBlock = t && t.closest
        ? (t.closest('[data-block-id]') &&
           t.closest('[data-block-id]').getAttribute('data-block-id') === editingId)
        : false;
      if (inSameBlock) return; // native caret placement inside the editing block
    }
    // The "+ Add here" button owns its click (its own handler posts).
    if (t && t.closest && t.closest('.yarnnn-add-here')) return;
    // ADR-456 W2: the format bar owns its clicks (injected chrome, not content).
    if (t && t.closest && t.closest('.yarnnn-fmt')) return;
    // ADR-458: the hover gutter owns its clicks too (this listener runs in the
    // CAPTURE phase — without the ignore it would clear the selection before
    // the gutter button's own handler ever fires).
    if (t && t.closest && t.closest('.yarnnn-gutter')) return;
    // The grips own their presses (move/resize/divider — body-appended
    // chrome): a press that never became a gesture must NOT read as a margin
    // click and clear the very selection the grip belongs to.
    if (t && t.closest && (t.closest('.yarnnn-selbox')
        || t.closest('.yarnnn-coldiv'))) return;
    // ADR-456 W1: a toggle block's <summary> opens natively on the SECOND
    // click — the first click selects the block; once selected, the click
    // passes through so <details> can do its platform thing (script-free).
    var sum = t && t.closest ? t.closest('summary') : null;
    if (sum && cur && sum.closest('[data-block="toggle"]') === cur) return;
    var el = t && t.closest ? t.closest(SEL) : null;
    e.preventDefault();

    // ADR-453 D5: the click-grain ladder — block (a pointable inside one) →
    // slot (a slot's empty padding) → page (the page margin) → clear.
    var mark = null;
    var payload = null;
    if (el) {
      // ADR-443 D6: the selection UNIT is the block when one encloses the hit.
      var blk = el.closest ? el.closest('[data-block]') : null;
      mark = blk || el;
      var text = (el.getAttribute('alt') || el.textContent || '')
        .replace(/\\s+/g, ' ').trim().slice(0, 120);
      var slotEl = el.closest ? el.closest('[data-slot]') : null;
      var blkKind = blk ? (blk.getAttribute('data-block') || null) : null;
      payload = {
        type: 'yarnnn-point',
        tag: el.tagName.toLowerCase(),
        text: text,
        dataRef: el.getAttribute('data-ref') || (blk && blk.getAttribute('data-ref')) || null,
        blockId: blk ? (blk.getAttribute('data-block-id') || null) : null,
        blockKind: blkKind,
        slideIndex: slideIndexOf(el),
        pageIndex: pageIndexOf(el),
        slot: slotEl ? (slotEl.getAttribute('data-slot') || null) : null,
        arrange: arrangeOf(el),
      };
      // Single-click-to-edit (ADR audit F4): a click on a TEXT block enters
      // edit with the caret at the click point — the Notion default (click =
      // caret, no separate select step). Non-text blocks (media/structured/
      // data) stay select-only. The click must NOT be on a citation island
      // (contentEditable=false) — those select the block, never edit. We still
      // post the point payload (drives the Design tab scope) and tell the
      // parent editing began (yarnnn-edit-entered) so its state stays in sync.
      //
      // ADR-466 P10 — the mode-native exception: on a STAGED frame (a deck
      // slide / canvas artboard, the .slide class) the OBJECT grammar wins
      // the first click. PowerPoint's ladder: first click SELECTS (the
      // bounding box, move band, handles); a second click on the already-
      // selected block enters text at the caret; dblclick still enters
      // directly. Without this, click-to-caret consumed every first click and
      // the box practically never existed on the one surface built around it.
      var onIsland = t && t.closest ? t.closest('[data-ref]') : null;
      var staged = blk && blk.closest ? !!blk.closest('.slide') : false;
      // ADR-480 D1/D2 — on FLOW the root is already editable, so the caret
      // lands NATIVELY wherever the member clicked; there is no per-block
      // enter to perform and no block to wall off. We still post the point
      // payload (it drives the Design tab's block scope — the block remains
      // ADDRESSABLE, it just stops being an enclosure), then get out of the
      // browser's way. This is what buys cross-block drag-selection: no
      // handler consumes the click that starts a multi-block range.
      var flowMode = window.__yarnnnFlowMode ? window.__yarnnnFlowMode() : false;
      if (flowMode) {
        if (cur) cur.classList.remove('yarnnn-pointed');
        cur = blk || null;
        // ADR-484: the selection cue is applied to OBJECTS ONLY on flow.
        //
        // ADR-482 D2 saw a real asymmetry (right-click outlined, left-click did
        // not) and resolved it the wrong direction on prose: it made left-click
        // match right-click, when on a continuous writing surface NEITHER
        // should box a paragraph. Clicking into prose places a caret — the
        // caret IS the feedback, and a rule around the paragraph re-asserts the
        // per-block enclosure ADR-480 dissolved. FLOW_POINTER_CSS already drew
        // this line for the hover cue (object kinds only); the selection cue
        // now honours the same boundary.
        //
        // An OBJECT (figure/table/chart/gallery/divider) is still selected as a
        // unit — there is no caret to stand in for the cue, so it keeps it.
        if (cur && TEXT_KINDS.indexOf(cur.getAttribute('data-block')) === -1) {
          cur.classList.add('yarnnn-pointed');
        }
        parent.postMessage(payload, '*');
        return;
      }
      if (blk && blkKind && TEXT_KINDS.indexOf(blkKind) !== -1 && !onIsland
          && (!staged || cur === blk)
          && window.__yarnnnEnter) {
        if (cur) cur.classList.remove('yarnnn-pointed');
        cur = blk;
        parent.postMessage(payload, '*');
        var bid = blk.getAttribute('data-block-id');
        window.__yarnnnEnter(bid, e.clientX, e.clientY);
        parent.postMessage({ type: 'yarnnn-edit-entered', blockId: bid }, '*');
        return;
      }
    } else {
      var slot = t && t.closest ? t.closest('[data-slot]') : null;
      var page = t && t.closest ? t.closest(PAGE_SEL) : null;
      var hit = slot || page;
      if (hit) {
        mark = hit;
        payload = {
          type: 'yarnnn-point',
          tag: hit.tagName.toLowerCase(),
          text: '',
          dataRef: null,
          blockId: null,
          blockKind: null,
          slideIndex: slideIndexOf(hit),
          pageIndex: pageIndexOf(hit),
          slot: slot ? (slot.getAttribute('data-slot') || null) : null,
          arrange: arrangeOf(hit),
        };
      }
    }

    if (!payload) {
      if (cur) { cur.classList.remove('yarnnn-pointed'); cur = null; }
      parent.postMessage({ type: 'yarnnn-point-clear' }, '*');
      return;
    }
    if (cur) cur.classList.remove('yarnnn-pointed');
    cur = mark;
    mark.classList.add('yarnnn-pointed');
    parent.postMessage(payload, '*');
  }, true);

  // ── Right-click (ADR-462 D7) — selects, then menus ──────────────────────
  // Every reference (Figma, PowerPoint, Notion, Finder) selects on right-click:
  // the menu acts on the thing under the cursor, and requiring left-then-right
  // would be two gestures for one intent.
  //
  // The grain is the CLICK LADDER's, not a second one: walk to the enclosing
  // [data-block], else the page. The parent decides which rows that grain earns
  // (ADR-462 D3) — the runtime reports, it never curates.
  document.addEventListener('contextmenu', function (e) {
    var t = e.target;
    // Injected chrome owns its own context menu (i.e. none) — never the page's.
    if (t && t.closest && (t.closest('.yarnnn-gutter') || t.closest('.yarnnn-fmt')
        || t.closest('.yarnnn-add-here'))) return;
    // While a block is being edited, a right-click INSIDE that same block yields
    // to the browser's NATIVE menu (spellcheck suggestions, cut/copy/paste) —
    // exactly what an editor user expects mid-edit (mirrors the click handler's
    // in-edit early-return). The Studio block menu is for a SELECTED block, not
    // a live caret; stealing the native menu here would drop the caret and hide
    // spellcheck.
    var editingId = window.__yarnnnEditingId ? window.__yarnnnEditingId() : null;
    if (editingId && t && t.closest) {
      var host = t.closest('[data-block-id]');
      if (host && host.getAttribute('data-block-id') === editingId) return;
    }
    e.preventDefault();
    var el = t && t.closest ? t.closest(SEL) : null;
    var blk = el && el.closest ? el.closest('[data-block]') : null;
    var mark = blk || el;
    if (mark) {
      if (cur) cur.classList.remove('yarnnn-pointed');
      cur = mark;
      // ADR-482 D9: on FLOW, prose is never boxed — not by left-click (already
      // corrected) and not by right-click either. The left-click fix landed one
      // direction only, so right-clicking a paragraph still drew the enclosure
      // ADR-480 dissolved; the operator's third pass caught it on a document
      // whose ONLY structure is prose. An object (figure/table/chart/gallery)
      // still gets the cue in both grains: there is no caret to stand in for it.
      var flowNow = window.__yarnnnFlowMode ? window.__yarnnnFlowMode() : false;
      var markKind = mark.getAttribute ? mark.getAttribute('data-block') : null;
      if (!flowNow || TEXT_KINDS.indexOf(markKind) === -1) {
        mark.classList.add('yarnnn-pointed');
      }
    } else if (cur) {
      cur.classList.remove('yarnnn-pointed');
      cur = null;
    }
    var slotEl = el && el.closest ? el.closest('[data-slot]') : null;
    parent.postMessage({
      type: 'yarnnn-context-menu',
      x: e.clientX, y: e.clientY,
      tag: el ? el.tagName.toLowerCase() : null,
      text: mark ? (mark.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 120) : '',
      dataRef: (el && el.getAttribute('data-ref')) || (blk && blk.getAttribute('data-ref')) || null,
      blockId: blk ? (blk.getAttribute('data-block-id') || null) : null,
      blockKind: blk ? (blk.getAttribute('data-block') || null) : null,
      slideIndex: el ? slideIndexOf(el) : null,
      pageIndex: el ? pageIndexOf(el) : null,
      slot: slotEl ? (slotEl.getAttribute('data-slot') || null) : null,
      arrange: el ? arrangeOf(el) : null,
      // The frame gate (ADR-461 D4) travels WITH the payload: the runtime is
      // the only side that can see the DOM, so it answers "is this framed?"
      // rather than making the parent guess from the layout name.
      framed: mark ? !!(mark.closest && mark.closest('.slide')) : false,
      // ADR-471 D-d: z orders POSITIONED blocks — the same DOM-side answer,
      // one gate over (presence of both x/y markers is the positioned state).
      positioned: blk ? !!(blk.hasAttribute('data-x') && blk.hasAttribute('data-y')) : false,
    }, '*');
  });

  // ADR-458: the hover gutter selects THROUGH this runtime's own selection
  // state (one selection, not two) — exposed like __yarnnnEditingId.
  window.__yarnnnSelect = function (el) {
    if (!el || !el.classList) return;
    if (cur) cur.classList.remove('yarnnn-pointed');
    cur = el;
    el.classList.add('yarnnn-pointed');
  };
  // The READER half of the same one-selection rule. The resize handle follows
  // the SELECTED block (ADR-461 D4's gesture needs a subject that outlives the
  // pointer's journey to the corner), and it must read this runtime's own
  // selection rather than track its own — a second selection state is exactly
  // the cross-talk bindGesture's one-flag rule exists to prevent.
  window.__yarnnnSelected = function () { return cur; };
  // ADR-466 P9: the ONE zoom accessor. body.style.zoom rescales the document's
  // LAYOUT, not the viewport — rects and pointer clientX/Y come back in visual
  // px, while style.left/top on body-appended chrome land in the zoomed layout
  // space. Every chrome positioner divides its visual coordinates by this.
  window.__yarnnnZf = function () {
    var v = document.body && document.body.style ? document.body.style.zoom : '';
    return parseFloat(v) || 1;
  };

  // ADR-447 (2026-07-13): canvas commands — scroll to a slide (navigator
  // selection moves the center display) + zoom (a VIEW control; scales the
  // rendered document via CSS zoom, never touches the file).
  window.addEventListener('message', function (e) {
    var d = e.data;
    if (!d || typeof d !== 'object') return;
    if (d.type === 'yarnnn-scroll-to-slide') {
      var slides = document.querySelectorAll('section.slide');
      var s = slides[d.index];
      if (s && s.scrollIntoView) s.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else if (d.type === 'yarnnn-scroll-to-block' && typeof d.blockId === 'string') {
      // ADR-455: the outline navigates — scroll to a heading block by id.
      try {
        var blk = document.querySelector('[data-block-id="' +
          (window.CSS && CSS.escape ? CSS.escape(d.blockId) : d.blockId) + '"]');
        if (blk && blk.scrollIntoView) blk.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } catch (err) {}
    } else if (d.type === 'yarnnn-zoom' && typeof d.scale === 'number') {
      // zoom scales layout + scrollable area (unlike transform) — the honest
      // "make it bigger/smaller on screen" the operator asked for.
      document.body.style.zoom = String(d.scale);
    } else if (d.type === 'yarnnn-select-block' && typeof d.blockId === 'string') {
      // ADR-466 P9: the parent re-commands selection after a re-projection.
      // Every optimistic op swaps srcdoc, which resets this runtime's state —
      // without this, the bounding box vanished mid-flow on every write.
      try {
        var selTarget = document.querySelector('[data-block-id="' +
          (window.CSS && CSS.escape ? CSS.escape(d.blockId) : d.blockId) + '"]');
        if (selTarget) window.__yarnnnSelect(selTarget);
      } catch (err) {}
    } else if (d.type === 'yarnnn-restore-scroll') {
      // The parent captured the pre-reload position (the runtime reports it on
      // scroll below) and restores it after a STRUCTURAL reload so the canvas
      // doesn't jump to the top — the reloads that remain feel like nothing
      // moved. Opaque origin means the parent can't read scrollTop directly,
      // so this round-trips through the runtime, which owns the anchoring UNIT:
      //   · a DECK anchors on the slide INDEX — zoom-independent and stable
      //     under a re-arrange (a raw pixel y lands on the wrong slide once the
      //     re-fit changes the scroll metric or a slide's height changes).
      //   · a fluid document anchors on the pixel y (no slide unit to hold).
      try {
        var restored = false;
        if (typeof d.slide === 'number' && d.slide >= 0) {
          var target = document.querySelectorAll('section.slide')[d.slide];
          if (target && target.scrollIntoView) {
            target.scrollIntoView({ block: 'start' });
            restored = true;
          }
        }
        if (!restored && typeof d.y === 'number') window.scrollTo(0, d.y);
      } catch (err) {}
    }
  });

  // The nearest slide to the current scroll (deck only) — the anchoring unit the
  // parent stores and hands back on restore. Null for a fluid document.
  var currentSlideIndex = function () {
    var slides = document.querySelectorAll('section.slide');
    if (!slides.length) return null;
    var mid = (window.scrollY || 0) + (window.innerHeight || 0) / 2;
    var best = 0;
    var bestDist = Infinity;
    for (var i = 0; i < slides.length; i++) {
      var r = slides[i].getBoundingClientRect();
      var center = r.top + (window.scrollY || 0) + r.height / 2;
      var dist = Math.abs(center - mid);
      if (dist < bestDist) { bestDist = dist; best = i; }
    }
    return best;
  };

  // Report the scroll position to the parent so it can restore it across a
  // structural reload. The parent keeps only the latest value. Throttled on the
  // leading edge, and re-reported on the TRAILING edge too — so the final resting
  // position (the one that matters for restore) is never the value that got
  // dropped by the throttle window.
  var scrollReportTimer = null;
  var reportScroll = function () {
    parent.postMessage(
      { type: 'yarnnn-scroll-pos', y: window.scrollY || 0, slide: currentSlideIndex() },
      '*',
    );
  };
  window.addEventListener('scroll', function () {
    if (scrollReportTimer) return;
    reportScroll();
    scrollReportTimer = setTimeout(function () {
      scrollReportTimer = null;
      reportScroll(); // trailing: capture where the scroll actually settled
    }, 120);
  }, true);
  // ── Keyboard verbs (ADR-482 D2, relocated from GUTTER_SCRIPT) ──────────
  //
  // Injected in BOTH grains, because the menu that advertises these keys is
  // rendered in both. Guards ask __yarnnnCaretLive (a caret question), never
  // __yarnnnEditingId (a per-block-session question with no flow answer).
  function caretOwnsKeyIn(blk) {
    // ADR-482 D2: on PAGED the caret owns the key only inside the block that is
    // actually editing. On FLOW the root is editable for the whole session, so
    // "which block is editing" has no answer — the honest test is whether the
    // caret sits in this block and there is text for the key to act on.
    var flow = window.__yarnnnFlowMode ? window.__yarnnnFlowMode() : false;
    if (flow) {
      if (!(window.__yarnnnCaretLive && window.__yarnnnCaretLive())) return false;
      var s = window.getSelection();
      if (!s || !s.rangeCount) return false;
      var n = s.getRangeAt(0).startContainer;
      var el = n && n.nodeType === 1 ? n : (n ? n.parentElement : null);
      var inBlk = !!(el && el.closest && el.closest('[data-block]') === blk);
      return inBlk && (blk.textContent || '').trim() !== '';
    }
    var editing = window.__yarnnnEditingId ? window.__yarnnnEditingId() : null;
    if (editing == null) return false;
    if (blk.getAttribute('data-block-id') !== editing) return false;
    return (blk.textContent || '').trim() !== '';
  }
  function selectedBlock() {
    var sel = window.__yarnnnSelected ? window.__yarnnnSelected() : null;
    if (!sel || !sel.isConnected) return null;
    return caretOwnsKeyIn(sel) ? null : sel;
  }

  document.addEventListener('keydown', function (e) {
    var blk = selectedBlock();
    if (!blk) return;
    var t = e.target;
    if (t && t.closest && (t.closest('.yarnnn-gutter') || t.closest('.yarnnn-fmt'))) return;
    var id = blk.getAttribute('data-block-id');
    if (!id) return;
    var mod = e.metaKey || e.ctrlKey;

    // Delete / Backspace on a SELECTED block removes it. With a live caret in
    // a block that still has text, caretOwnsKeyIn() has already handed the key
    // back to the editor (merge at start, native mid-text) — so reaching here
    // means the caret has no claim on it.
    if (!mod && (e.key === 'Delete' || e.key === 'Backspace')) {
      e.preventDefault();
      parent.postMessage({ type: 'yarnnn-key-verb', verb: 'delete', blockId: id }, '*');
      return;
    }
    if (!mod) return;
    var k = (e.key || '').toLowerCase();
    if (k === 'c' || k === 'd' || k === 'v') {
      // The member may be copying TEXT they selected inside the block — that is
      // the platform's job, not ours. Only claim the key when nothing is
      // selected, so ⌘C over a highlighted phrase still copies the phrase.
      var s = window.getSelection();
      if (k === 'c' && s && !s.isCollapsed && String(s)) return;
      // Same rule for the caret itself: an empty block can be SELECTED while
      // its caret is live (the P11 overlap), and ⌘V there means "paste text
      // here", never "paste a block after this one". Text keys belong to the
      // editor whenever a caret exists at all.
      // ADR-482 D2: ask "is a caret LIVE", not "is a block editing" — the
      // latter is null on flow while the caret is live in the root, which
      // would steal text keys from a member mid-sentence on every document.
      if ((k === 'v' || k === 'c') &&
          window.__yarnnnCaretLive && window.__yarnnnCaretLive()) return;
      e.preventDefault();
      parent.postMessage({
        type: 'yarnnn-key-verb',
        verb: k === 'c' ? 'copy' : k === 'd' ? 'duplicate' : 'paste',
        blockId: id,
      }, '*');
    }
  });

})();
`;

// ── The empty-slot affordance (ADR-447 Phase 4) ──────────────────────────
//
// An arrangement declares slots (data-slot); a fresh arrangement has empty
// ones. This decorates every EMPTY slot with a "+ Add here" button so the
// member sees WHERE content goes and can put it there directly. Clicking posts
// {slideIndex, slot} to the parent, which inserts a block targeted at that
// slot (StudioSurface handles the op). Runs after the pointer runtime; the
// buttons are not [data-block] so they never confuse selection.

const ADD_HERE_SCRIPT = `
(function () {
  var PAGE_SEL = 'section.slide, [data-arrange]';
  function slideIndexOf(el) {
    var slide = el.closest ? el.closest('section.slide') : null;
    if (!slide) return null;
    var all = document.querySelectorAll('section.slide');
    for (var i = 0; i < all.length; i++) { if (all[i] === slide) return i; }
    return null;
  }
  function pageIndexOf(el) {
    var page = el.closest ? el.closest(PAGE_SEL) : null;
    if (!page) return null;
    var all = document.querySelectorAll(PAGE_SEL);
    for (var i = 0; i < all.length; i++) { if (all[i] === page) return i; }
    return null;
  }
  function decorate() {
    var slots = document.querySelectorAll('[data-slot]');
    for (var i = 0; i < slots.length; i++) {
      var slot = slots[i];
      // Empty = no block inside AND no existing affordance.
      if (slot.querySelector('[data-block]')) {
        slot.classList.remove('yarnnn-slot-open'); // filled — bounds retire
        continue;
      }
      // ADR-466 P8: an empty slot shows its dashed bounds ALWAYS on a deck
      // (the PowerPoint placeholder grammar) — the class is styling-only.
      slot.classList.add('yarnnn-slot-open');
      if (slot.querySelector('.yarnnn-add-here')) continue;
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'yarnnn-add-here';
      // "+ Add here" named the PLACE but not the ACT, so what arrived was a
      // surprise (it read as the slot defaulting to a format). The runtime
      // does not know slot ROLES — the parent does that vocabulary lookup and
      // routes media slots to a picker — so the honest label is the one that
      // promises a choice rather than a specific block.
      btn.textContent = '+ Add';
      btn.setAttribute('data-slot-name', slot.getAttribute('data-slot') || '');
      btn.addEventListener('click', function (e) {
        e.preventDefault(); e.stopPropagation();
        // ADR-453 D5: arrange + pageIndex ride along so the parent can gate
        // the add by the slot's ROLE (vocabulary lookup) and target the page.
        var page = this.closest ? this.closest('[data-arrange]') : null;
        parent.postMessage({
          type: 'yarnnn-add-here',
          slot: this.getAttribute('data-slot-name'),
          slideIndex: slideIndexOf(this),
          pageIndex: pageIndexOf(this),
          arrange: page ? (page.getAttribute('data-arrange') || null) : null,
        }, '*');
      });
      slot.appendChild(btn);
    }
  }
  decorate();
})();
`;

// ── The edit runtime (ADR-446: direct text editing) ──────────────────────
//
// The member edits BLOCK TEXT in place. The canvas renders a PROJECTION
// (citations resolved to blobs/tables, executables stripped), so an edit must
// map back to the artifact's SOURCE, never serialize the projection (ADR-446
// D2). Two rules make that safe:
//
//  1. Citation islands (D3): every `[data-ref]` inside an editable block is
//     `contentEditable=false` and carries `data-src-html` (its SOURCE
//     outerHTML, stamped BEFORE resolution mutated it). On commit the runtime
//     restores each island to `data-src-html` before reading the block's
//     inner — so the emitted `newInner` carries the citation in its
//     living-reference markup, never its resolved bytes.
//  2. The revision is the atom (D4): a keystroke-burst commits on blur OR
//     idle-2s, whichever first; the parent debounces further via the CAS door.
//
// The parent (StudioCanvas) commands edit mode: postMessage
// {type:'yarnnn-edit-enter', blockId} enters, {type:'yarnnn-edit-exit'} exits.
// On commit the runtime posts {type:'yarnnn-edit', blockId, newInner}.

const EDIT_CSS = `
[data-block][contenteditable="true"] {
  outline: 2px solid var(--yarnnn-chrome-accent) !important; outline-offset: 3px;
  background: rgba(var(--yarnnn-chrome-accent-rgb),0.04);
}
[data-block][contenteditable="true"] [data-ref] {
  outline: 1px dashed rgba(var(--yarnnn-chrome-accent-rgb),0.5); cursor: default;
}
/* ADR-456 W2: the inline format bar — injected chrome, body-appended (never
   inside a block, so it can never leak into a commit). */
.yarnnn-fmt {
  position: absolute; z-index: 9999; display: inline-flex; align-items: center;
  gap: 2px; background: #1f2937; border-radius: 6px; padding: 3px 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.yarnnn-fmt button {
  all: unset; cursor: pointer; color: #e5e7eb;
  font: 600 12px/1 system-ui, sans-serif; padding: 4px 7px; border-radius: 4px;
}
.yarnnn-fmt button:hover { background: rgba(255,255,255,0.15); }
.yarnnn-fmt input {
  font: 12px system-ui, sans-serif; border: 0; border-radius: 4px;
  padding: 4px 6px; width: 220px; outline: none;
}
/* ADR-458: the hover gutter — + and ⋮⋮ beside the hovered block (injected
   chrome, body-appended; the pointer runtime ignores its clicks). */
.yarnnn-gutter {
  position: absolute; z-index: 9998; display: flex; align-items: center;
}
.yarnnn-gutter button {
  all: unset; cursor: pointer; color: #9ca3af;
  font: 600 14px/1 system-ui, sans-serif; padding: 2px 4px; border-radius: 4px;
}
.yarnnn-gutter button:hover { background: rgba(0,0,0,0.08); color: #4b5563; }
.yarnnn-gutter .yg-handle { cursor: grab; font-size: 12px; letter-spacing: -3px; }
/* F1: the ⋮⋮ drag — the grabbed block dims, a drop-line follows the cursor
   between blocks (Notion's blue indicator). Body-appended chrome, never in a
   block, so it can't leak into a commit. */
.yarnnn-gutter .yg-handle:active { cursor: grabbing; }
/* The column divider (ADR-461 D3) — a snap handle on the gap between two
   columns. Body-appended chrome like the gutter, so it can never leak into a
   commit. It drags through the ratio token's STOPS, never free pixels. */
.yarnnn-coldiv {
  position: absolute; display: none; width: 9px; margin-left: -4px;
  cursor: col-resize; z-index: 2147483646;
}
.yarnnn-coldiv::before {
  content: ''; position: absolute; inset: 0 4px; border-radius: 2px;
  background: transparent; transition: background 0.1s;
}
.yarnnn-coldiv:hover::before, .yarnnn-coldiv:active::before { background: var(--yarnnn-chrome-accent); }
/* The resize handle (ADR-461 D4) — the corner grip on a MEASURABLE block (one
   inside a frame: a slide, or a media block's own box). Body-appended chrome,
   never in a block, so it can't leak into a commit. Its ABSENCE on an
   unframed block is the D4 boundary made visible. */
/* The bounding box (ADR-466 P8, conventional carve P10) — the object chrome:
   a SELECTED framed block wears a solid box in the PowerPoint grammar. The
   INTERIOR is transparent to the pointer (pointer-events: none) so clicks
   fall through to the content — the box never fights the editor. What IS
   interactive: the BORDER BAND (four thin strips riding the edges — the
   conventional near-the-border move zone, cursor: move) and EIGHT handles
   (four corners + four edge midpoints, each with its directional cursor).
   Body-appended chrome, never serialized; hidden while editing. Its ABSENCE
   on an unframed block is the ADR-461 boundary made visible. */
.yarnnn-selbox {
  position: absolute; display: none; z-index: 2147483645;
  border: 1.5px solid var(--yarnnn-chrome-accent); border-radius: 1px;
  background: transparent; box-sizing: border-box;
  pointer-events: none;
}
.yarnnn-selmove { position: absolute; pointer-events: auto; cursor: move; z-index: 1; }
.yarnnn-selmove-n { left: 6px; right: 6px; top: -5px; height: 9px; }
.yarnnn-selmove-s { left: 6px; right: 6px; bottom: -5px; height: 9px; }
.yarnnn-selmove-w { top: 6px; bottom: 6px; left: -5px; width: 9px; }
.yarnnn-selmove-e { top: 6px; bottom: 6px; right: -5px; width: 9px; }
/* A block that cannot be positioned (a media block in a flowing document)
   keeps the band for selection-stability, but it is honest about inertness. */
.yarnnn-selbox-static .yarnnn-selmove { cursor: default; }
/* P11 — the PowerPoint edit cue: while the caret is live INSIDE the block,
   the box (and its handles) PERSISTS; the border goes dashed to say "text
   mode". Hiding the box during editing was the P8 rule from the era when the
   box trapped clicks — the pointer-transparent interior retired its cause. */
.yarnnn-selbox-editing { border-style: dashed; }
.yarnnn-selh {
  position: absolute; width: 10px; height: 10px;
  border: 1.5px solid var(--yarnnn-chrome-accent); background: #fff; border-radius: 50%;
  box-shadow: 0 1px 2px rgba(0,0,0,0.2);
  pointer-events: auto; z-index: 2;
}
.yarnnn-selh-nw { left: -6px; top: -6px; cursor: nwse-resize; }
.yarnnn-selh-ne { right: -6px; top: -6px; cursor: nesw-resize; }
.yarnnn-selh-sw { left: -6px; bottom: -6px; cursor: nesw-resize; }
.yarnnn-selh-se { right: -6px; bottom: -6px; cursor: nwse-resize; }
.yarnnn-selh-n { left: 50%; margin-left: -5px; top: -6px; cursor: ns-resize; }
.yarnnn-selh-s { left: 50%; margin-left: -5px; bottom: -6px; cursor: ns-resize; }
.yarnnn-selh-w { top: 50%; margin-top: -5px; left: -6px; cursor: ew-resize; }
.yarnnn-selh-e { top: 50%; margin-top: -5px; right: -6px; cursor: ew-resize; }
/* PowerPoint's placeholder grammar (ADR-466 P8): an EMPTY slot on a deck
   slide shows its dashed bounds ALWAYS, not only on hover — the member sees
   where content goes before they reach for it. The add-here runtime stamps
   the class when it decorates an empty slot. */
.slide [data-slot].yarnnn-slot-open {
  outline: 1.5px dashed rgba(120,115,107,0.45); outline-offset: 2px;
  min-height: 2.5rem;
}
/* The frame indicator (ADR-462 D8, made persistent by ADR-466 P10) — the
   named rectangle a measure is a percent OF. It rides the SELECTION (name
   alone — "side" / "slide" / "column"), and a live gesture overlays its
   numbers ("side · 62% × 40%"): the member always sees what they are moving
   or resizing against, not only mid-drag. It borrows the slot label's own
   grammar (the green uppercase tag already on the canvas) rather than
   inventing a second vocabulary for the same idea. */
.yarnnn-frame {
  position: absolute; display: none; pointer-events: none; z-index: 2147483645;
  outline: 1px dashed rgba(16,185,129,0.7); outline-offset: 0;
  background: rgba(16,185,129,0.04); border-radius: 2px;
}
.yarnnn-frame::after {
  content: attr(data-label); position: absolute; top: -1.05rem; left: 0;
  font: 600 0.6rem system-ui, sans-serif; letter-spacing: 0.06em;
  text-transform: uppercase; color: rgba(16,185,129,0.95); white-space: nowrap;
}
.yarnnn-dragging { opacity: 0.4; }
.yarnnn-dropline {
  position: absolute; z-index: 9997; height: 2px; background: var(--yarnnn-chrome-accent);
  border-radius: 2px; pointer-events: none; display: none;
  box-shadow: 0 0 0 1px rgba(var(--yarnnn-chrome-accent-rgb),0.3);
}
`;

const EDIT_SCRIPT = `
(function () {
  var TEXT_KINDS = ${TEXT_KINDS_JS};
  var editingId = null;      // the block currently in edit mode
  var editingEl = null;
  var idleTimer = null;

  // ── ADR-480: the editing GRAIN is per-mode ────────────────────────────
  // The axiom: attribution binds to the FILE, addressing to sub-file
  // STRUCTURE, editing to neither — it binds to what the MEDIUM is.
  //
  //   paged (deck/page/canvas) — the block is an ENCLOSURE. One block
  //     editable at a time; the runtime owns the caret because the medium
  //     is a frame of objects. Everything below is unchanged there.
  //   flow (document/article) — the block is an ANNOTATION. contenteditable
  //     sits on the FLOW ROOT: one continuous writing surface, so the
  //     BROWSER supplies cross-block selection, Cmd-A, multi-paragraph
  //     copy, Cmd-F and native undo instead of a simulation of them.
  //
  // The mode is stamped by the parent (which reads it from the served
  // layout registry) — the runtime never learns a layout SLUG, so a new
  // layout declares its mode once in the kernel (ADR-222).
  var FLOW_MODE = document.documentElement.getAttribute('data-yarnnn-mode') === 'flow';
  // The flow root is the scaffold's own container. Resolved once, by shape
  // and not by slug: the outermost element holding annotated blocks.
  var FLOW_ROOT_SEL = 'main, article';
  function flowRoot() {
    return FLOW_MODE ? document.querySelector(FLOW_ROOT_SEL) : null;
  }
  window.__yarnnnFlowMode = function () { return FLOW_MODE; };

  // Restore every citation island in the block to its SOURCE form, then read
  // the block's inner — the source-mapped emit (D2/D3).
  function readSourceInner(el) {
    if (!el || !el.cloneNode) return '';
    var clone = el.cloneNode(true);
    // ADR-484: strip RUNTIME CHROME before serializing. The yarnnn-pointed
    // class is a transient selection cue the pointer runtime paints on the live
    // DOM; it has no business in the artifact. Because every commit reads the
    // DOM as it stands, whichever block was selected at commit time carried the
    // class into the SAVED file — verified in prod on three artifacts, one of
    // them a real operator document whose h2 shipped the class outright. That
    // is worse than a live-session artifact: it renders the outline for every
    // future reader, and it is attributed as the member's own authored content.
    //
    // Done HERE because this is the ONE serializer both commit paths use (the
    // flow root and the per-block edit), so chrome cannot leak from either.
    var painted = clone.querySelectorAll('.yarnnn-pointed');
    for (var p = 0; p < painted.length; p++) {
      painted[p].classList.remove('yarnnn-pointed');
      // Drop the attribute entirely when it was the only class — an empty
      // class="" is noise in an attributed revision diff.
      if (!painted[p].getAttribute('class')) painted[p].removeAttribute('class');
    }
    var refs = clone.querySelectorAll('[data-src-html]');
    for (var i = 0; i < refs.length; i++) {
      var r = refs[i];
      var src = r.getAttribute('data-src-html');
      if (src == null) continue;
      var holder = document.createElement('div');
      holder.innerHTML = decodeURIComponent(src);
      var srcEl = holder.firstElementChild;
      if (srcEl && r.parentNode) r.parentNode.replaceChild(srcEl, r);
    }
    return clone.innerHTML;
  }

  function commit() {
    if (!editingEl || editingId == null) return;
    var inner = readSourceInner(editingEl);
    parent.postMessage({ type: 'yarnnn-edit', blockId: editingId, newInner: inner }, '*');
  }

  // notify=true only on a member-initiated blur — the surface then clears its
  // editingBlockId so it doesn't re-enter this block on the post-commit reload.
  // Internal exits (re-enter of another block, or the parent's explicit
  // edit-exit command) pass notify=false: the parent already owns that state.
  //
  // silent=true detaches WITHOUT emitting the block's commit. Required by the
  // split/merge paths: they mutate the DOM first, so a commit read here would
  // describe a HALF of the result (the truncated before-half on a split; the
  // about-to-be-removed block on a merge) while the op message that follows
  // carries the WHOLE result. Both land through the write door anchored on the
  // same head, so the stale half either clobbers the op or spuriously 409s it.
  // The op message is the single source of truth for these transitions.
  function exit(notify, silent) {
    if (idleTimer) { clearTimeout(idleTimer); idleTimer = null; }
    var el = editingEl;
    editingEl = null; editingId = null; // clear FIRST so any re-entry is a no-op
    hideFmt();
    if (el && el.__yarnnnBlur) { el.removeEventListener('blur', el.__yarnnnBlur); el.__yarnnnBlur = null; }
    if (el && el.__yarnnnInput) { el.removeEventListener('input', el.__yarnnnInput); el.__yarnnnInput = null; }
    if (el && el.__yarnnnPaste) { el.removeEventListener('paste', el.__yarnnnPaste); el.__yarnnnPaste = null; }
    if (el && el.querySelectorAll) {
      if (!silent) {
        var innerNow = readSourceInner(el);
        if (innerNow) parent.postMessage({ type: 'yarnnn-edit', blockId: el.getAttribute('data-block-id'), newInner: innerNow }, '*');
      }
      el.removeAttribute('contenteditable');
      var refs = el.querySelectorAll('[data-ref]');
      for (var i = 0; i < refs.length; i++) refs[i].removeAttribute('contenteditable');
    }
    if (notify) parent.postMessage({ type: 'yarnnn-edit-exited' }, '*');
  }

  // caretX/caretY (optional): place the caret at that viewport point after
  // focusing — the single-click-to-edit gesture (ADR audit F4). Absent (the
  // dblclick / parent-command path) → the browser's default focus caret.
  function enter(blockId, caretX, caretY) {
    // Idempotent: if this block is already being edited, do nothing. This
    // breaks the re-entrancy where a local dblclick enters, tells the parent,
    // and the parent echoes back 'yarnnn-edit-enter' for the SAME block —
    // which would otherwise re-enter mid-flight and null-out state.
    if (editingId === blockId && editingEl) return;
    exit(false);
    var el = null;
    try {
      el = document.querySelector('[data-block-id="' + (window.CSS && CSS.escape ? CSS.escape(blockId) : blockId) + '"]');
    } catch (err) { el = null; }
    if (!el) return;
    editingEl = el; editingId = blockId;
    // Citation islands: never editable (D3).
    var refs = el.querySelectorAll('[data-ref]');
    for (var i = 0; i < refs.length; i++) refs[i].setAttribute('contenteditable', 'false');
    el.setAttribute('contenteditable', 'true');
    // Semantic tags from execCommand (b/i), normalized to strong/em at commit.
    try { document.execCommand('styleWithCSS', false, 'false'); } catch (err) {}
    el.focus();
    // Single-click-to-edit: land the caret WHERE the member clicked (not at the
    // block start/end el.focus() gives), so click-to-type feels like a real
    // editor. Guard the caret to inside the editable block (never into a
    // contentEditable=false citation island).
    if (caretX != null && caretY != null) {
      try {
        var range = null;
        if (document.caretRangeFromPoint) {
          range = document.caretRangeFromPoint(caretX, caretY);
        } else if (document.caretPositionFromPoint) {
          var pos = document.caretPositionFromPoint(caretX, caretY);
          if (pos) { range = document.createRange(); range.setStart(pos.offsetNode, pos.offset); range.collapse(true); }
        }
        if (range) {
          var node = range.startContainer;
          var host = node && node.nodeType === 1 ? node : (node ? node.parentElement : null);
          var island = host && host.closest ? host.closest('[contenteditable="false"]') : null;
          if (!island && el.contains(range.startContainer)) {
            var sel = window.getSelection();
            sel.removeAllRanges(); sel.addRange(range);
          }
        }
      } catch (err) {}
    }
    // ADR-456 W2: the blur guard replaces the once-blur — focus moving INTO
    // the format bar (the link input) must not end the edit session.
    var onBlur = function () {
      setTimeout(function () {
        var a = document.activeElement;
        if (a && a.closest && a.closest('.yarnnn-fmt')) return; // bar owns focus — stay
        if (a === el) return; // focus bounced back (a bar action refocused)
        exit(true);
      }, 0);
    };
    // Store EVERY listener ref on the element so exit() can remove all three —
    // enter()/exit() run on every single-click, arrow-traversal, split, and
    // merge, re-entering the SAME physical nodes across one document load. An
    // anonymous listener that exit() couldn't remove would stack per re-entry
    // (unbounded within a session): N idle-timers armed per keystroke, N paste
    // handlers. The blur listener was already stored + removed; these two were
    // the leak.
    var onInput = function () {
      if (idleTimer) clearTimeout(idleTimer);
      idleTimer = setTimeout(commit, 2000); // idle-2s safety commit (D4)
    };
    // Sanitize paste to plain text — no HTML injection through the clipboard.
    var onPaste = function (e) {
      e.preventDefault();
      var text = (e.clipboardData || window.clipboardData).getData('text/plain');
      if (document.queryCommandSupported && document.queryCommandSupported('insertText')) {
        document.execCommand('insertText', false, text);
      }
    };
    el.__yarnnnBlur = onBlur;
    el.__yarnnnInput = onInput;
    el.__yarnnnPaste = onPaste;
    el.addEventListener('blur', onBlur);
    el.addEventListener('input', onInput);
    el.addEventListener('paste', onPaste);
  }

  // ── ADR-480 D1: the FLOW editing session ──────────────────────────────
  // One contenteditable on the flow root, entered once on load and never
  // swapped. There is no enter/exit per block, so none of the boundary
  // machinery below (split on Enter, merge on Backspace, the empty-block
  // rule, cross-block arrow traversal) has anything to do on flow — the
  // browser does all of it, correctly, including IME, RTL and a11y.
  //
  // What the runtime still owns: source-mapping the commit (citation
  // islands restored to their living-reference form — the ADR-446 D3
  // contract, unchanged), the debounce, and the paste sanitizer.
  var flowIdle = null;

  function flowCommit() {
    var root = flowRoot();
    if (!root) return;
    parent.postMessage({
      type: 'yarnnn-flow-edit',
      selector: root.tagName.toLowerCase(),
      newInner: readSourceInner(root),
    }, '*');
  }

  function enterFlow() {
    var root = flowRoot();
    if (!root || root.getAttribute('contenteditable') === 'true') return;
    // Citation islands are never editable (ADR-446 D3) — the same rule the
    // per-block path applies, applied once at the root.
    var refs = root.querySelectorAll('[data-ref]');
    for (var i = 0; i < refs.length; i++) refs[i].setAttribute('contenteditable', 'false');
    root.setAttribute('contenteditable', 'true');
    try { document.execCommand('styleWithCSS', false, 'false'); } catch (err) {}
    root.addEventListener('input', function () {
      if (flowIdle) clearTimeout(flowIdle);
      flowIdle = setTimeout(flowCommit, 2000); // idle-2s, same cadence as D4
    });
    root.addEventListener('blur', function () {
      if (flowIdle) clearTimeout(flowIdle);
      flowCommit();
    }, true);
    // Paste stays plain-text — no HTML injection through the clipboard.
    root.addEventListener('paste', function (e) {
      e.preventDefault();
      var text = (e.clipboardData || window.clipboardData).getData('text/plain');
      if (document.queryCommandSupported && document.queryCommandSupported('insertText')) {
        document.execCommand('insertText', false, text);
      }
    });
  }

  if (FLOW_MODE) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', enterFlow);
    } else {
      enterFlow();
    }
    // A pending edit must never be lost to a re-projection or a tab close.
    window.addEventListener('beforeunload', function () {
      if (flowIdle) { clearTimeout(flowIdle); flowCommit(); }
    });
  }

  // ── ADR-456 W2: the inline format bar ─────────────────────────────────
  // Injected chrome, appended to <body> (never inside a block — commits read
  // the block's inner, so the bar can never leak into the source). Shows on a
  // non-collapsed selection inside the editing block. B/I ride execCommand
  // (native toggle; b/i normalized to strong/em at the write door), code is a
  // range wrap, link swaps the bar to a URL input (the blur guard keeps the
  // edit session alive while it has focus).
  var fmtBar = null, fmtBtns = null, fmtInput = null, savedRange = null;

  function scheduleCommit() {
    // ADR-480: route to the grain's own commit — the block's inner (paged) or
    // the flow root's region (flow). One debounce cadence either way.
    if (FLOW_MODE) {
      if (flowIdle) clearTimeout(flowIdle);
      flowIdle = setTimeout(flowCommit, 2000);
      return;
    }
    if (idleTimer) clearTimeout(idleTimer);
    idleTimer = setTimeout(commit, 2000);
  }

  function wrapSelection(tag) {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount) return;
    var r = sel.getRangeAt(0);
    if (r.collapsed) return;
    var el = document.createElement(tag);
    try { r.surroundContents(el); }
    catch (err) { el.appendChild(r.extractContents()); r.insertNode(el); }
    sel.removeAllRanges();
  }

  function hideFmt() {
    if (fmtBar) fmtBar.style.display = 'none';
    if (fmtInput) fmtInput.style.display = 'none';
    if (fmtBtns) fmtBtns.style.display = 'inline-flex';
  }

  function openLink() {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount || sel.getRangeAt(0).collapsed) return;
    savedRange = sel.getRangeAt(0).cloneRange();
    fmtBtns.style.display = 'none';
    fmtInput.style.display = 'inline-block';
    fmtInput.value = '';
    fmtInput.focus();
  }

  function closeLink() {
    fmtInput.style.display = 'none';
    fmtBtns.style.display = 'inline-flex';
    if (editingEl) editingEl.focus();
    if (savedRange) {
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(savedRange);
      savedRange = null;
    }
  }

  function applyLink() {
    var url = (fmtInput.value || '').trim();
    closeLink(); // restores the saved selection + refocuses the block
    if (!url) return;
    document.execCommand('createLink', false, url); // javascript: stripped at the write door
    scheduleCommit();
  }

  function applyFmt(op) {
    if (!editHost()) return; // ADR-480: the host is the block (paged) or the root (flow)
    if (op === 'bold') document.execCommand('bold');
    else if (op === 'italic') document.execCommand('italic');
    else if (op === 'code') wrapSelection('code');
    else if (op === 'link') { openLink(); return; }
    scheduleCommit();
  }

  function buildFmtBar() {
    if (fmtBar) return;
    fmtBar = document.createElement('div');
    fmtBar.className = 'yarnnn-fmt';
    fmtBar.style.display = 'none';
    fmtBtns = document.createElement('span');
    fmtBtns.style.display = 'inline-flex';
    fmtBtns.style.gap = '2px';
    var defs = [['B', 'bold', 'Bold'], ['I', 'italic', 'Italic'],
                ['<>', 'code', 'Code'], ['Link', 'link', 'Link']];
    for (var i = 0; i < defs.length; i++) {
      (function (d) {
        var b = document.createElement('button');
        b.type = 'button'; b.textContent = d[0]; b.title = d[2];
        if (d[1] === 'italic') b.style.fontStyle = 'italic';
        // mousedown preventDefault keeps the selection AND the block's focus.
        b.addEventListener('mousedown', function (e) { e.preventDefault(); });
        b.addEventListener('click', function (e) {
          e.preventDefault(); e.stopPropagation();
          applyFmt(d[1]);
        });
        fmtBtns.appendChild(b);
      })(defs[i]);
    }
    fmtInput = document.createElement('input');
    fmtInput.type = 'text';
    fmtInput.placeholder = 'https://… or a workspace path — Enter to apply';
    fmtInput.style.display = 'none';
    fmtInput.addEventListener('keydown', function (e) {
      e.stopPropagation();
      if (e.key === 'Enter') { e.preventDefault(); applyLink(); }
      else if (e.key === 'Escape') { e.preventDefault(); closeLink(); }
    });
    fmtBar.appendChild(fmtBtns);
    fmtBar.appendChild(fmtInput);
    document.body.appendChild(fmtBar);
  }

  // ADR-480: the EDITABLE HOST — the element the caret is currently inside.
  // On paged that is the block being edited (editingEl); on flow it is the
  // document root, which is editable for the whole session. One accessor, so
  // the format bar and the slash palette are written once and serve both
  // grains (the ADR-466 D1 shape: one grammar, N native editors).
  function editHost() {
    return FLOW_MODE ? flowRoot() : editingEl;
  }

  document.addEventListener('selectionchange', function () {
    var host = editHost();
    if (!host) { hideFmt(); return; }
    if (fmtInput && fmtInput.style.display !== 'none') return; // typing a URL
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount || sel.isCollapsed) { hideFmt(); return; }
    var r = sel.getRangeAt(0);
    var anc = r.commonAncestorContainer;
    var ancEl = anc && anc.nodeType === 1 ? anc : (anc ? anc.parentElement : null);
    if (!ancEl || !host.contains(ancEl)) { hideFmt(); return; }
    buildFmtBar();
    var rect = r.getBoundingClientRect();
    if (!rect || (rect.width === 0 && rect.height === 0)) { hideFmt(); return; }
    fmtBar.style.display = 'inline-flex';
    // Visual → layout: the bar is body-appended chrome inside the zoomed
    // document (ADR-466 P9 — see __yarnnnZf).
    var fz = window.__yarnnnZf ? window.__yarnnnZf() : 1;
    fmtBar.style.left = Math.max(4, (rect.left + window.scrollX) / fz) + 'px';
    fmtBar.style.top = Math.max(4, (rect.top + window.scrollY) / fz - 36) + 'px';
  });

  // ── ADR-456 W2: slash-insert (the Notion gesture) ─────────────────────
  // '/' ANYWHERE opens the block palette — mid-sentence, mid-word, on an empty
  // line. The character LANDS as ordinary text (we never preventDefault) and
  // the edit is NOT exited: the caret keeps typing, and what it types after the
  // '/' is the palette's live filter. That is what makes "and/or" and URLs safe
  // — the menu opens, matches nothing, and dismisses itself; the text is
  // untouched either way. On a pick, the parent deletes the '/'+filter run it
  // was told about (slashStart) and applies the block.
  //
  // The pre-2026-07-15 rule fired only in an EMPTY context and swallowed the
  // key. It stranded text mid-sentence (an operator's '...' outlived the block
  // it was typed in) and made the gesture unreachable exactly where writing
  // happens.
  var slashStart = -1; // caret offset of the '/' within its text node
  var slashNode = null; // the text node the '/' landed in

  function slashCaret() {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount || !sel.isCollapsed) return null;
    return sel.getRangeAt(0);
  }

  // Report the run typed since the '/' so the parent can filter + later delete
  // it. Returns null when the caret has left the run (→ the palette closes).
  function slashRun() {
    if (slashStart < 0 || !slashNode) return null;
    var caret = slashCaret();
    if (!caret) return null;
    // ADR-482 D10: RE-ANCHOR before giving up on node identity.
    //
    // The run was keyed on caret.startContainer !== slashNode — an identity
    // test that holds on PAGED, where the '/' is typed into a small per-block
    // contenteditable whose text node is stable. On FLOW the browser owns a
    // whole-document editable and freely splits, merges and re-creates text
    // nodes as the member types — ADR-480 D1 accepted exactly this (D3 already
    // re-establishes block ids on write for the same reason). When the caret's
    // node is no longer the OBJECT captured at '/'-time, this returned null,
    // the keyup handler called closeSlash(), the anchor was forgotten, and the
    // later take bailed at its own guard: the filter never narrowed and the
    // pick silently did nothing, with nothing thrown to log.
    //
    // The '/' is a POSITION in text, not an object identity. If the caret has
    // moved into a different node, look for the sentinel at the remembered
    // offset in the caret's OWN node and adopt it. Identity is kept where it
    // survives; where native editing broke it, the position is re-found.
    if (caret.startContainer !== slashNode) {
      var cn = caret.startContainer;
      if (!cn || cn.nodeType !== 3) return null;
      if ((cn.textContent || '').charAt(slashStart) !== '/') return null;
      slashNode = cn; // re-anchored — the run continues in the node that lives
    }
    if (caret.startOffset < slashStart + 1) return null; // caret moved before the '/'
    var text = slashNode.textContent || '';
    if (text.charAt(slashStart) !== '/') return null; // the '/' was deleted
    return text.slice(slashStart + 1, caret.startOffset);
  }

  // Hide the palette but KEEP the anchor (slashStart/slashNode). Dismissing is
  // a UI fact; the run is a DOM fact, and the two are not the same event. The
  // take (yarnnn-slash-take) re-validates the run against the live DOM anyway
  // — slashRun() already returns null when the '/' was deleted or the caret
  // walked off — so holding the anchor through a dismiss is safe, and dropping
  // it is what made a click-pick a silent no-op (see the mousedown below).
  function hideSlash() {
    if (slashStart < 0) return;
    parent.postMessage({ type: 'yarnnn-slash-close' }, '*');
  }

  // Hide AND forget. Only for the paths where the run itself is genuinely gone
  // (the '/' deleted, a space typed, the caret moved away) — never for a mere
  // pointer press, which may BE the pick.
  function closeSlash() {
    if (slashStart < 0) return;
    slashStart = -1;
    slashNode = null;
    parent.postMessage({ type: 'yarnnn-slash-close' }, '*');
  }

  document.addEventListener('keydown', function (e) {
    if (e.key !== '/' || !editHost()) return;
    if (fmtInput && document.activeElement === fmtInput) return;
    var caret = slashCaret();
    if (!caret || caret.startContainer.nodeType !== 3) return; // not in a text node
    if (caretInIsland()) return; // a citation island owns its own text
    // NO preventDefault + NO exit: the '/' lands and the caret keeps typing.
    // ADR-480: the palette anchors on the caret's OWN BLOCK, never the edit
    // host — on flow the host is the whole document, whose rect would put the
    // palette at the top of the page instead of beside the line being typed.
    // The block is still the right anchor there; it is an annotation now, not
    // an enclosure, but it is exactly the region the '/' was typed into.
    var anchorEl = editingEl;
    if (FLOW_MODE) {
      var cn = caret.startContainer;
      var ce = cn && cn.nodeType === 1 ? cn : (cn ? cn.parentElement : null);
      anchorEl = (ce && ce.closest ? ce.closest('[data-block]') : null) || flowRoot();
    }
    if (!anchorEl) return;
    var id = FLOW_MODE ? (anchorEl.getAttribute('data-block-id') || null) : editingId;
    var node = caret.startContainer;
    var at = caret.startOffset;
    var rect = anchorEl.getBoundingClientRect();
    var empty = (anchorEl.textContent || '').trim() === '';
    setTimeout(function () {
      // Post-input: the '/' now sits at offset 'at' in that text node.
      slashNode = node;
      slashStart = at;
      parent.postMessage({ type: 'yarnnn-slash-open', blockId: id, empty: empty,
        rect: { left: rect.left, top: rect.top, bottom: rect.bottom, width: rect.width } }, '*');
    }, 0);
  }, true);

  // While the palette is open the DOCUMENT still has the caret, so the palette's
  // navigation keys must be intercepted here and forwarded — the palette has no
  // input to focus (focusing one would end the edit the gesture depends on).
  // stopImmediatePropagation, not just preventDefault: the Enter-split handler
  // below is registered on the SAME element in the SAME phase, so preventDefault
  // alone would still let it run and split the block we are picking into — one
  // gesture, two ops, racing on one head.
  document.addEventListener('keydown', function (e) {
    if (slashStart < 0) return;
    if (e.key === 'Escape') {
      e.preventDefault(); e.stopImmediatePropagation();
      closeSlash();
      return;
    }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault(); e.stopImmediatePropagation();
      parent.postMessage({ type: 'yarnnn-slash-move', delta: e.key === 'ArrowDown' ? 1 : -1 }, '*');
      return;
    }
    if (e.key === 'Enter') {
      e.preventDefault(); e.stopImmediatePropagation();
      parent.postMessage({ type: 'yarnnn-slash-enter' }, '*');
      return;
    }
  }, true);

  // The filter is typed INTO the document, so the runtime drives it. Every key
  // that lands while the palette is open re-reports the run; leaving it closes.
  document.addEventListener('keyup', function () {
    if (slashStart < 0) return;
    var run = slashRun();
    if (run === null) { closeSlash(); return; }
    // A run that grows a word with a space in it is prose, not a filter.
    if (run.indexOf(' ') >= 0) { closeSlash(); return; }
    parent.postMessage({ type: 'yarnnn-slash-filter', filter: run }, '*');
  }, true);

  // A click anywhere in the CONTENT dismisses. The palette lives in the parent
  // document, whose mousedown listener never hears this frame — without this
  // the menu only closed by clicking the thin chrome around the canvas.
  //
  // HIDE, never close: this fires on EVERY pointer press in the frame, in the
  // capture phase — including the press that IS a palette pick. Forgetting the
  // anchor here nulled slashStart before the pick's take arrived, so the take
  // guard bailed and the block silently never landed (the keyboard path worked,
  // because a keydown fires no mousedown — the tell). The run stays; the take
  // re-validates it against the live DOM.
  document.addEventListener('mousedown', function () {
    hideSlash();
    // The parent's chrome (the toolbar's Media/New-slide panels) listens on the
    // PARENT document, which never hears a press inside this frame. Bridge it:
    // clicking the artifact is the most natural "click outside" for those
    // panels, and without this they stayed open over the canvas.
    parent.postMessage({ type: 'yarnnn-canvas-press' }, '*');
  }, true);

  // ── ENTER makes a new block (ADR audit F2 — "writing is adding") ───────
  // The core Notion reflex: press Enter, get a fresh block below, keep typing.
  // Studio had NO Enter handler, so Enter fell to native contentEditable and
  // inserted a <br> INSIDE the block — every new block needed a mouse trip.
  //
  // Scope for THIS commit: Enter at the END of a block's text appends a new
  // empty prose block after it and moves the caret in. Enter MID-block is a
  // split (its own commit, with optimistic in-frame update) — until then a
  // mid-block Enter falls through to native (a soft break), never losing text.
  // Shift+Enter is always a native soft line break (never a new block). Inside
  // a list/checklist, native Enter already makes a new <li> — leave it.
  function caretAtBlockEnd() {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount || !sel.isCollapsed) return false;
    // Range from the caret to the end of the block: empty ⇒ caret is at the end.
    var probe = document.createRange();
    try {
      probe.setStart(sel.anchorNode, sel.anchorOffset);
      probe.setEndAfter(editingEl.lastChild || editingEl);
    } catch (err) { return false; }
    return probe.toString().replace(/\\s+$/, '') === '';
  }
  function inListBlock() {
    return !!(editingEl && editingEl.closest &&
      (editingEl.closest('[data-block="checklist"]') ||
       editingEl.matches('ul,ol') || editingEl.querySelector('ul,ol')));
  }
  // F6 — the caret is inside a citation island (contentEditable=false): a split
  // or merge across it is refused (a data-ref can't be halved). Fall to native.
  function caretInIsland() {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount) return false;
    var n = sel.anchorNode;
    var el = n && n.nodeType === 1 ? n : (n ? n.parentElement : null);
    return !!(el && el.closest && el.closest('[contenteditable="false"]'));
  }
  function caretAtBlockStart() {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount || !sel.isCollapsed) return false;
    var probe = document.createRange();
    try {
      probe.setStart(editingEl, 0);
      probe.setEnd(sel.anchorNode, sel.anchorOffset);
    } catch (err) { return false; }
    return probe.toString().replace(/^\\s+/, '') === '';
  }
  // Partition the editing block at the caret into BEFORE / AFTER source-inner
  // (citation islands restored via readSourceInner). Returns null if the caret
  // sits in an island (refuse the split). Two clones are truncated by the caret
  // range, then read source-mapped — the same proven path as a plain edit.
  function splitHalves() {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount || !sel.isCollapsed) return null;
    if (caretInIsland()) return null;
    var caret = sel.getRangeAt(0);
    var beforeClone = editingEl.cloneNode(true);
    var afterClone = editingEl.cloneNode(true);
    // Map the caret into each clone by walking the same node path.
    function rangeInClone(clone, toEnd) {
      var r = document.createRange();
      // Locate the caret node inside the clone by index path from editingEl.
      var path = [];
      var node = caret.startContainer;
      while (node && node !== editingEl) {
        var p = node.parentNode;
        if (!p) break;
        path.unshift(Array.prototype.indexOf.call(p.childNodes, node));
        node = p;
      }
      var target = clone;
      for (var i = 0; i < path.length; i++) target = target.childNodes[path[i]];
      if (!target) return null;
      if (toEnd) { r.setStart(target, caret.startOffset); r.setEndAfter(clone.lastChild || clone); }
      else { r.setStart(clone, 0); r.setEnd(target, caret.startOffset); }
      return r;
    }
    var rBefore = rangeInClone(beforeClone, false);
    var rAfter = rangeInClone(afterClone, true);
    if (!rBefore || !rAfter) return null;
    // Delete the OTHER half from each clone.
    var delAfter = document.createRange();
    delAfter.setStart(rBefore.endContainer, rBefore.endOffset);
    delAfter.setEndAfter(beforeClone.lastChild || beforeClone);
    delAfter.deleteContents();
    var delBefore = document.createRange();
    delBefore.setStart(afterClone, 0);
    delBefore.setEnd(rAfter.startContainer, rAfter.startOffset);
    delBefore.deleteContents();
    return { before: readSourceInner(beforeClone), after: readSourceInner(afterClone) };
  }
  // A fresh block id checked against the CURRENT DOM (has every live id) — same
  // shape as artifactOps.freshBlockId. Math.random is fine in the browser
  // runtime; the source op re-checks uniqueness against the full document.
  function freshId() {
    for (var i = 0; i < 50; i++) {
      var id = 'b' + Math.random().toString(36).slice(2, 6);
      if (!document.querySelector('[data-block-id="' + id + '"]')) return id;
    }
    return 'b' + Math.random().toString(36).slice(2, 8);
  }
  document.addEventListener('keydown', function (e) {
    if (FLOW_MODE) return; // ADR-480 D4 — the browser splits on flow
    if (e.key !== 'Enter' || e.shiftKey || !editingEl) return;
    if (fmtInput && document.activeElement === fmtInput) return; // link input owns Enter
    if (inListBlock()) return; // native <li> creation is the right behavior
    var id = editingId;
    if (caretAtBlockEnd()) {
      // At the END → append a fresh empty block after (F2, the common case).
      e.preventDefault();
      exit(true);
      parent.postMessage({ type: 'yarnnn-enter-block', afterBlockId: id }, '*');
      return;
    }
    // MID-BLOCK → SPLIT (F6). Optimistic: mutate the DOM in-frame FIRST (the
    // caret lands in the new block instantly), then land the revision in the
    // background WITHOUT a reload — no stutter. A caret inside a citation island
    // refuses (splitHalves → null) and falls to native.
    var halves = splitHalves();
    if (!halves) return; // in-island / uncomputable → native newline
    e.preventDefault();
    var newId = freshId();
    // ── Optimistic in-frame mutation ──
    // Truncate the editing block to the BEFORE half, insert a tail block with
    // the AFTER half, move the caret to its start, and re-enter it. A heading's
    // tail becomes prose (matches splitBlock's source op).
    var kind = editingEl.getAttribute('data-block') || 'prose';
    var tail;
    if (kind === 'heading' || /^h[1-6]$/i.test(editingEl.tagName)) {
      tail = document.createElement('p'); tail.setAttribute('data-block', 'prose');
    } else {
      tail = editingEl.cloneNode(false);
      tail.removeAttribute('data-ref');
    }
    tail.setAttribute('data-block-id', newId);
    // The optimistic DOM uses the source-inner halves (re-projected on next load
    // if needed; citations in the tail are rare and resolve on reload).
    editingEl.innerHTML = halves.before;
    tail.innerHTML = halves.after;
    editingEl.insertAdjacentElement('afterend', tail);
    // silent: the DOM is already truncated to the BEFORE half, so a commit here
    // would post an edit that DROPS the after-half — racing the split message
    // below (both anchored on the same head). The split op carries both halves.
    exit(false, true);
    enter(newId);
    try {
      var r = document.createRange();
      r.selectNodeContents(tail); r.collapse(true);
      var sel2 = window.getSelection(); sel2.removeAllRanges(); sel2.addRange(r);
    } catch (err) {}
    parent.postMessage({ type: 'yarnnn-edit-entered', blockId: newId }, '*');
    // ── Background revision (no reload) ──
    parent.postMessage({ type: 'yarnnn-split-block', blockId: id, newId: newId,
      beforeInner: halves.before, afterInner: halves.after }, '*');
  }, true);

  // ── Backspace at block START → MERGE into the previous text block (F6) ──
  // Optimistic: concatenate this block's inner onto the previous text block's,
  // place the caret at the join, remove this block — then land the revision in
  // the background (no reload). Refuses across a citation island.
  document.addEventListener('keydown', function (e) {
    if (FLOW_MODE) return; // ADR-480 D4 — the browser merges (and empties) on flow
    if (e.key !== 'Backspace' || !editingEl) return;
    if (fmtInput && document.activeElement === fmtInput) return;
    if (!caretAtBlockStart() || caretInIsland()) return; // mid-text → native delete

    // ── EMPTY block → REMOVE it (the missing rule) ──────────────────────
    // Backspace at the start of an EMPTY block is a delete, not a merge:
    // there is nothing to carry, so the merge path's requirement of a
    // previous TEXT block does not apply. Without this the block survived
    // its own emptying — first block in the document, or any block whose
    // predecessor is a figure/table/divider, left an empty frame behind
    // and native Backspace had nothing to bite on. contenteditable has no
    // concept of the block; only the runtime can close it.
    //
    // The caret lands at the end of the previous block of ANY kind when
    // that block can hold one; a non-text predecessor (figure, divider)
    // takes the SELECTION instead — the member is still located, and the
    // object grammar is the honest place to be on a non-text block.
    if ((editingEl.textContent || '').trim() === '' && !editingEl.querySelector('[data-ref], img')) {
      var all = document.querySelectorAll('[data-block]');
      var here = -1;
      for (var n = 0; n < all.length; n++) { if (all[n] === editingEl) { here = n; break; } }
      if (here <= 0) return; // sole/first block → native (nothing to fall back to)
      var back = all[here - 1];
      var backId = back.getAttribute('data-block-id');
      var backKind = back.getAttribute('data-block');
      var goneId = editingId;
      e.preventDefault();
      // silent: this block is about to be removed — a commit here would
      // re-assert it and race the delete on the same head (the one-gesture
      // two-ops trap the merge path documents above).
      exit(false, true);
      if (backKind && TEXT_KINDS.indexOf(backKind) !== -1 && backId) {
        enter(backId);
        try {
          var selE = window.getSelection();
          var rE = document.createRange();
          rE.selectNodeContents(back);
          rE.collapse(false); // caret at END of the previous block
          selE.removeAllRanges(); selE.addRange(rE);
        } catch (err) {}
        parent.postMessage({ type: 'yarnnn-edit-entered', blockId: backId }, '*');
      } else if (window.__yarnnnSelect) {
        window.__yarnnnSelect(back);
      }
      // The verb the menu and the keyboard already share (ADR-462 D10) —
      // one body, a third entrance. Never a second delete implementation.
      parent.postMessage({ type: 'yarnnn-key-verb', verb: 'delete', blockId: goneId }, '*');
      return;
    }

    var prev = adjacentTextBlock('up');
    if (!prev) return; // no previous text block → native (nothing to merge into)
    e.preventDefault();
    var thisId = editingId;
    var prevId = prev.getAttribute('data-block-id');
    // The merged inner = prev's source inner + this block's source inner. The
    // caret lands at the JOIN (end of prev's original content).
    var prevInner = readSourceInner(prev);
    var thisInner = readSourceInner(editingEl);
    var joinLen = (prev.textContent || '').length;
    // ── Optimistic in-frame ──
    // silent: this block is about to be REMOVED. A commit here would post an
    // edit re-asserting it, racing the merge message below (same head anchor).
    // The merge op carries the joined inner + the removal.
    exit(false, true);
    prev.innerHTML = prevInner + thisInner;
    editingEl && editingEl.remove && editingEl.remove();
    enter(prevId);
    // caret at the join: walk to the joinLen-th character in prev.
    try {
      var sel3 = window.getSelection();
      var walk = document.createTreeWalker(prev, NodeFilter.SHOW_TEXT, null);
      var acc = 0, node2 = null, off = 0;
      while (walk.nextNode()) {
        var tn = walk.currentNode;
        if (acc + tn.length >= joinLen) { node2 = tn; off = joinLen - acc; break; }
        acc += tn.length;
      }
      var r3 = document.createRange();
      if (node2) r3.setStart(node2, off); else { r3.selectNodeContents(prev); r3.collapse(false); }
      r3.collapse(true);
      sel3.removeAllRanges(); sel3.addRange(r3);
    } catch (err) {}
    parent.postMessage({ type: 'yarnnn-edit-entered', blockId: prevId }, '*');
    // ── Background revision (no reload) ──
    parent.postMessage({ type: 'yarnnn-merge-block', blockId: thisId, prevBlockId: prevId,
      mergedInner: prevInner + thisInner }, '*');
  }, true);

  // ── Cross-block ARROW traversal (ADR audit F6) ────────────────────────
  // ArrowUp on the first visual line / ArrowDown on the last visual line exits
  // this block and enters the adjacent TEXT block, placing the caret at the end
  // (up) or start (down) — the document behaves as one continuous flow. Pure
  // in-iframe caret motion (no write door). Mid-block arrows fall through to
  // native line movement.
  function caretRect() {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount) return null;
    var r = sel.getRangeAt(0).getClientRects()[0];
    if (r) return r;
    // A collapsed caret at a boundary can yield no rect — probe a zero-range.
    try {
      var rng = sel.getRangeAt(0).cloneRange();
      rng.collapse(true);
      var rects = rng.getClientRects();
      return rects[0] || editingEl.getBoundingClientRect();
    } catch (err) { return editingEl ? editingEl.getBoundingClientRect() : null; }
  }
  function adjacentTextBlock(dir) {
    if (!editingEl) return null;
    var all = document.querySelectorAll('[data-block]');
    var idx = -1;
    for (var i = 0; i < all.length; i++) { if (all[i] === editingEl) { idx = i; break; } }
    if (idx === -1) return null;
    var step = dir === 'up' ? -1 : 1;
    for (var j = idx + step; j >= 0 && j < all.length; j += step) {
      var k = all[j].getAttribute('data-block');
      if (k && TEXT_KINDS.indexOf(k) !== -1) return all[j];
    }
    return null;
  }
  document.addEventListener('keydown', function (e) {
    if (FLOW_MODE) return; // ADR-480 D4 — the caret already traverses natively on flow
    if ((e.key !== 'ArrowUp' && e.key !== 'ArrowDown') || !editingEl || e.shiftKey) return;
    if (fmtInput && document.activeElement === fmtInput) return;
    var sel = window.getSelection();
    if (!sel || !sel.isCollapsed) return; // a selection: leave native
    var cr = caretRect();
    if (!cr) return;
    var br = editingEl.getBoundingClientRect();
    var LINE = 6; // tolerance (px) for "on the first/last visual line"
    if (e.key === 'ArrowUp' && cr.top - br.top <= LINE) {
      var prev = adjacentTextBlock('up');
      if (!prev) return;
      e.preventDefault();
      var pid = prev.getAttribute('data-block-id');
      exit(false); // commit silently (parent keeps editingBlockId in sync below)
      enter(pid);
      // caret to END of the previous block
      try {
        var r1 = document.createRange();
        r1.selectNodeContents(prev); r1.collapse(false);
        sel.removeAllRanges(); sel.addRange(r1);
      } catch (err) {}
      parent.postMessage({ type: 'yarnnn-edit-entered', blockId: pid }, '*');
    } else if (e.key === 'ArrowDown' && br.bottom - cr.bottom <= LINE) {
      var next = adjacentTextBlock('down');
      if (!next) return;
      e.preventDefault();
      var nid = next.getAttribute('data-block-id');
      exit(false);
      enter(nid);
      // caret to START of the next block
      try {
        var r2 = document.createRange();
        r2.selectNodeContents(next); r2.collapse(true);
        sel.removeAllRanges(); sel.addRange(r2);
      } catch (err) {}
      parent.postMessage({ type: 'yarnnn-edit-entered', blockId: nid }, '*');
    }
  }, true);

  // DOUBLE-CLICK is now a redundant fallback: since single-click enters TEXT
  // blocks at the caret (ADR audit F4, pointer runtime), a double-click on one
  // just re-enters idempotently (a no-op) and the native double-click word-
  // selects — the expected "double-click selects a word" of every editor. We
  // keep it only so a block whose kind the pointer's TEXT_KINDS set doesn't
  // cover still has a way in — but guard it to blocks that actually hold text
  // (never make a pure media/citation block contentEditable).
  document.addEventListener('dblclick', function (e) {
    var t = e.target;
    var blk = t && t.closest ? t.closest('[data-block]') : null;
    if (!blk) return;
    var id = blk.getAttribute('data-block-id');
    if (!id) return;
    // Skip a block with no editable text of its own (e.g. figure/gallery whose
    // only content is a citation island) — entering would orphan the caret.
    var hasText = (blk.textContent || '').replace(/\\s+/g, '').length > 0;
    var onlyRef = blk.querySelector('[data-ref]') && !hasText;
    if (onlyRef) return;
    e.preventDefault();
    enter(id);
    parent.postMessage({ type: 'yarnnn-edit-entered', blockId: id }, '*');
  }, true);

  // Esc lifts the caret back to BLOCK-SELECT (ADR audit F4): single-click now
  // enters edit directly, so Esc is the deliberate move UP to whole-block ops
  // (the Notion model — caret is the default, block-select is the escape). It
  // commits the edit, exits, and asks the parent to select the block (which
  // re-outlines it via the pointer runtime + drives the Design tab scope).
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape' || !editingEl) return;
    if (fmtInput && fmtInput.style.display !== 'none') return; // Esc closes the link input first
    var el = editingEl;
    var id = editingId;
    e.preventDefault();
    exit(true); // commit + tell the parent editing ended
    if (window.__yarnnnSelect) window.__yarnnnSelect(el);
    var slotEl = el.closest ? el.closest('[data-slot]') : null;
    var pageEl = el.closest ? el.closest('[data-arrange]') : null;
    parent.postMessage({ type: 'yarnnn-point',
      tag: el.tagName.toLowerCase(),
      text: (el.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 120),
      dataRef: el.getAttribute('data-ref') || null,
      blockId: id,
      blockKind: el.getAttribute('data-block') || null,
      slideIndex: null, pageIndex: null,
      slot: slotEl ? (slotEl.getAttribute('data-slot') || null) : null,
      arrange: pageEl ? (pageEl.getAttribute('data-arrange') || null) : null }, '*');
  }, true);

  window.addEventListener('message', function (e) {
    var d = e.data;
    if (!d || typeof d !== 'object') return;
    if (d.type === 'yarnnn-edit-enter' && typeof d.blockId === 'string') enter(d.blockId);
    else if (d.type === 'yarnnn-edit-exit') exit(false);
    else if (d.type === 'yarnnn-slash-take') {
      // A pick landed. Delete the '/'+filter run the member typed so the text
      // the block keeps never contains the gesture, then hand the parent BOTH
      // halves around the caret — it applies one op from them.
      //
      // Why the runtime computes this and not the parent: the run is a live-DOM
      // fact (which text node, which offset) that the source HTML cannot name.
      // We exit SILENT — the parent's op carries the whole result, and a commit
      // of our own would race it on the same head (the one-gesture-two-ops trap).
      //
      // ADR-482 D1: the guard reads the edit HOST, not the per-block session.
      // editingEl is assigned only by enter(), and ADR-480 D1 stopped calling
      // enter() on flow — so this bailed unconditionally on every document, and
      // ADR-481 D2 had already removed the gutter '+' that was masking it. The
      // palette opened, filtered, and did nothing. editHost() is the ADR-480
      // seam built for exactly this: the flow root on flow, editingEl on paged.
      if (slashStart < 0 || !slashNode || !editHost()) return;
      var text = slashNode.textContent || '';
      var end = slashStart + 1 + (typeof d.filterLen === 'number' ? d.filterLen : 0);
      slashNode.textContent = text.slice(0, slashStart) + text.slice(end);
      // Put the caret where the '/' was: the split point.
      try {
        var r = document.createRange();
        r.setStart(slashNode, slashStart); r.collapse(true);
        var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
      } catch (err) {}
      var halves = splitHalves(); // null inside an island → parent falls back
      // ADR-482 D1: resolve the target from the CARET, mirroring the open path
      // (:1396-1405). editingId is null on flow for the same reason editingEl
      // is, so reading it sent the parent a null blockId and its op had nothing
      // to land after. On paged the session variable is still the truth.
      var id = editingId;
      if (FLOW_MODE) {
        var tn = slashNode.nodeType === 1 ? slashNode : slashNode.parentElement;
        var tblk = tn && tn.closest ? tn.closest('[data-block]') : null;
        id = tblk ? (tblk.getAttribute('data-block-id') || null) : null;
      }
      slashStart = -1;
      slashNode = null;
      // Silent — the parent's op is the sole writer (the one-gesture-two-ops
      // trap). On flow there is no per-block session to leave; calling exit()
      // there would be a no-op that reads as though one were open.
      if (!FLOW_MODE) exit(false, true);
      parent.postMessage({ type: 'yarnnn-slash-taken', blockId: id,
        beforeInner: halves ? halves.before : null,
        afterInner: halves ? halves.after : null }, '*');
    }
  });

  // Expose to the pointer runtime so it can suppress its click-to-select while
  // a block is being edited (the caret must land, not a new selection).
  window.__yarnnnEditingId = function () { return editingId; };
  // ADR-482 D2: "is a text caret LIVE right now?" — the question the keyboard
  // verbs actually need, and the one editingId cannot answer on flow (it is
  // null there by ADR-480 D1, while the caret is very much live in the root).
  // Callers that guard TEXT keys must ask this, not __yarnnnEditingId, or ⌘C /
  // ⌘V / ⌘Z would be stolen from a member mid-sentence on every document.
  window.__yarnnnCaretLive = function () {
    if (!FLOW_MODE) return editingId != null;
    var root = flowRoot();
    if (!root) return false;
    var s = window.getSelection();
    if (!s || !s.rangeCount) return false;
    var n = s.getRangeAt(0).startContainer;
    var el = n && n.nodeType === 1 ? n : (n ? n.parentElement : null);
    return !!(el && root.contains(el));
  };
  // Expose enter-at-point so the pointer runtime can turn a SINGLE click on a
  // text block into caret placement (ADR audit F4 — click-to-type, no dblclick).
  window.__yarnnnEnter = function (blockId, x, y) { enter(blockId, x, y); };
})();
`;

// ── The hover gutter (ADR-458) ────────────────────────────────────────────
//
// The layer Notion surfaces on hover: + (open the block palette here) and ⋮⋮
// (select the block + open the Design tab — the verbs' one home) beside the
// hovered block, NO selection needed. Injected chrome, body-appended (never
// inside a block — commits can't see it). Desktop-pointer only; hides for the
// block being edited (the format bar owns that space). The ⋮⋮ handle DRAGS the
// block (F1 — pointer-events reorder with a drop-line, all in-frame; a click
// without a drag still selects + opens the Design tab).

const GUTTER_SCRIPT = `
(function () {
  if (!window.matchMedia || !window.matchMedia('(hover: hover)').matches) return;
  var PAGE_SEL = 'section.slide, [data-arrange]';
  var bar = null, plusBtn = null, curBlock = null, hideTimer = null;

  // ADR-466 P9: every piece of body-appended chrome here (gutter, dropline,
  // divider, frame label, bounding box) positions from getBoundingClientRect,
  // which reports VISUAL px — but its own style.left/top land in the zoomed
  // LAYOUT space (body.style.zoom = deck fit-scale × member zoom). Divide, or
  // the box draws at the wrong scale and drifts off the block it claims to
  // bound (the operator's screenshot: a box spanning past the slide's edge).
  function zf() { return window.__yarnnnZf ? window.__yarnnnZf() : 1; }

  function slideIndexOf(el) {
    var slide = el.closest ? el.closest('section.slide') : null;
    if (!slide) return null;
    var all = document.querySelectorAll('section.slide');
    for (var i = 0; i < all.length; i++) { if (all[i] === slide) return i; }
    return null;
  }
  function pageIndexOf(el) {
    var page = el.closest ? el.closest(PAGE_SEL) : null;
    if (!page) return null;
    var all = document.querySelectorAll(PAGE_SEL);
    for (var i = 0; i < all.length; i++) { if (all[i] === page) return i; }
    return null;
  }

  function build() {
    if (bar) return;
    bar = document.createElement('div');
    bar.className = 'yarnnn-gutter';
    bar.style.display = 'none';
    plusBtn = document.createElement('button');
    plusBtn.type = 'button'; plusBtn.textContent = '+'; plusBtn.title = 'Add a block';
    plusBtn.addEventListener('click', function (e) {
      e.preventDefault(); e.stopPropagation();
      if (!curBlock) return;
      // The SAME palette the slash trigger opens (ADR-456 W2) — one palette,
      // two entrances; the parent's routing (convert-on-empty / insert-after)
      // is unchanged.
      var rect = curBlock.getBoundingClientRect();
      parent.postMessage({ type: 'yarnnn-slash-open',
        blockId: curBlock.getAttribute('data-block-id'),
        empty: (curBlock.textContent || '').trim() === '',
        rect: { left: rect.left, top: rect.top, bottom: rect.bottom, width: rect.width } }, '*');
    });
    var handle = document.createElement('button');
    handle.type = 'button'; handle.className = 'yg-handle';
    handle.textContent = '\\u22EE\\u22EE'; handle.title = 'Drag to move · click for options';
    // CLICK (no gesture past threshold) → select + open the Design tab. Any
    // bindGesture that passed its threshold sets gestureSuppressClick; a click
    // that WAS a gesture is suppressed here so a drop never also opens the
    // Design tab. Consumed on read — the flag never outlives the click it
    // belongs to (it used to stay true until the NEXT click, which is exactly
    // the leak a second gesture source would have tripped over).
    handle.addEventListener('click', function (e) {
      e.preventDefault(); e.stopPropagation();
      if (gestureSuppressClick) { gestureSuppressClick = false; return; }
      if (!curBlock) return;
      // Select in-frame through the pointer runtime's OWN selection state
      // (one selection, not two), then tell the parent to select AND open
      // the Design tab (design: true) — the verbs' one home.
      if (window.__yarnnnSelect) window.__yarnnnSelect(curBlock);
      var slotEl = curBlock.closest ? curBlock.closest('[data-slot]') : null;
      var pageEl = curBlock.closest ? curBlock.closest('[data-arrange]') : null;
      parent.postMessage({ type: 'yarnnn-point',
        tag: curBlock.tagName.toLowerCase(),
        text: (curBlock.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 120),
        dataRef: curBlock.getAttribute('data-ref') || null,
        blockId: curBlock.getAttribute('data-block-id') || null,
        blockKind: curBlock.getAttribute('data-block') || null,
        slideIndex: slideIndexOf(curBlock),
        pageIndex: pageIndexOf(curBlock),
        slot: slotEl ? (slotEl.getAttribute('data-slot') || null) : null,
        arrange: pageEl ? (pageEl.getAttribute('data-arrange') || null) : null,
        design: true }, '*');
    });
    bindDrag(handle);
    bar.appendChild(plusBtn);
    bar.appendChild(handle);
    document.body.appendChild(bar);
  }

  // ── F1: the ⋮⋮ pointer-drag (real block reorder, all in-frame) ─────────
  // Grab the handle, the block dims + a drop-line follows the cursor between
  // its SAME-PARENT sibling blocks (v1 — cross-slot is the follow-on), release
  // posts ONE yarnnn-reorder {blockId, beforeBlockId} → the parent lands one
  // revision. Pointer Events (not HTML5 DnD — brittle under sandbox); geometry
  // stays in-frame so the body.style.zoom transform never desyncs the coords.
  var dropline = null;
  // The ONE click-suppression authority (ADR-461 D2). Every gesture bound via
  // bindGesture sets this the moment it passes its threshold; the click handler
  // consumes it. One flag, one setter (bindGesture), one consumer — so a second
  // gesture source cannot cross-talk with the first, which is what a per-gesture
  // flag would have produced.
  var gestureSuppressClick = false;
  function ensureDropline() {
    if (dropline) return dropline;
    dropline = document.createElement('div');
    dropline.className = 'yarnnn-dropline';
    document.body.appendChild(dropline);
    return dropline;
  }
  // The same-parent sibling blocks, in document order (drop candidates).
  function siblingBlocksOf(block) {
    var out = [];
    var p = block.parentElement;
    if (!p) return out;
    var kids = p.children;
    for (var i = 0; i < kids.length; i++) {
      if (kids[i].hasAttribute && kids[i].hasAttribute('data-block')) out.push(kids[i]);
    }
    return out;
  }
  /** bindGesture — the ONE pointer-gesture primitive (ADR-461 D2).
   *
   *  D2 says gestures compose existing ops rather than becoming a second write
   *  path. That was aspirational: the drag was bound to one handle, read a
   *  module-global the gutter owns, and hard-coded the Y axis and reorder
   *  semantics. A second gesture (resize) built beside it would have been a
   *  second gesture SYSTEM, and the two would have shared one click-suppression flag
   *  — a global that stays true after a drop and resets on the next click, so
   *  cross-talk would read as "the UI sometimes eats a click".
   *
   *  What is genuinely shared: pointer capture, the arm/threshold state machine
   *  (a press under the threshold is still a CLICK, never a gesture), in-frame
   *  edge auto-scroll, and the click-suppression handshake. What is not: the
   *  axis, the hit-test, the feedback, the message. Those are the caller's.
   *
   *  opts: { axis: 'y'|'xy', threshold, onStart(el,e), onMove(el,e,d), onEnd(el,moved) }
   *  The move delta carries {dx, dy} from the press origin. Returns nothing; binds listeners.
   */
  function bindGesture(handle, subject, opts) {
    var el = null, startX = 0, startY = 0, armed = false, moved = false;
    var threshold = opts.threshold == null ? 5 : opts.threshold;
    var axis = opts.axis || 'y';

    handle.addEventListener('pointerdown', function (e) {
      if (e.button !== 0) return;
      var s = subject();
      if (!s) return;
      el = s; startX = e.clientX; startY = e.clientY; armed = true; moved = false;
      try { handle.setPointerCapture(e.pointerId); } catch (err) {}
      if (opts.onStart) opts.onStart(el, e);
    });

    handle.addEventListener('pointermove', function (e) {
      if (!armed || !el) return;
      var dx = e.clientX - startX, dy = e.clientY - startY;
      if (!moved) {
        // Below the threshold this is still a CLICK, not a gesture. The axis
        // decides what "movement" even means — a resize that only moves in X
        // must not be judged by Y.
        var travel = axis === 'xy' ? Math.max(Math.abs(dx), Math.abs(dy)) : Math.abs(dy);
        if (travel < threshold) return;
        moved = true;
        // The gesture has begun — suppress the click this press would fire.
        gestureSuppressClick = true;
      }
      // Edge auto-scroll (in-frame — the iframe scrolls, never the parent).
      var vh = window.innerHeight;
      if (e.clientY < 48) window.scrollBy(0, -12);
      else if (e.clientY > vh - 48) window.scrollBy(0, 12);
      if (opts.onMove) opts.onMove(el, e, { dx: dx, dy: dy });
    });

    function end(e) {
      if (!el) return;
      try { handle.releasePointerCapture(e.pointerId); } catch (err) {}
      if (opts.onEnd) opts.onEnd(el, moved);
      el = null; armed = false; moved = false;
    }
    handle.addEventListener('pointerup', end);
    handle.addEventListener('pointercancel', end);
  }

  /** The reorder gesture — the FIRST caller of bindGesture, and its proof.
   *  What remains here is only what is genuinely the drag's own: the Y-axis
   *  sibling hit-test, the drop-line, and the reorder message. Pointer capture,
   *  the arm/threshold machine, edge-scroll and click-suppression all moved to
   *  the primitive (ADR-461 D2 — "gestures over existing ops", now true rather
   *  than aspirational). Behaviour is unchanged; that is the point. */
  function bindDrag(handle) {
    var beforeId = null;      // the block id to drop before (null = end)

    bindGesture(handle, function () { return curBlock; }, {
      axis: 'y',
      onStart: function () { beforeId = null; },
      onMove: function (dragging, e) {
        if (!dragging.classList.contains('yarnnn-dragging')) {
          dragging.classList.add('yarnnn-dragging');
          ensureDropline();
        }
        // The same-parent sibling the cursor is nearest to, and whether the
        // drop lands ABOVE or BELOW it → the drop-line position + beforeId.
        var sibs = siblingBlocksOf(dragging);
        var placed = false;
        for (var i = 0; i < sibs.length; i++) {
          var s = sibs[i];
          if (s === dragging) continue;
          var r = s.getBoundingClientRect();
          var mid = r.top + r.height / 2;
          if (e.clientY < mid) {
            var dz = zf();
            dropline.style.display = 'block';
            dropline.style.left = ((r.left + window.scrollX) / dz) + 'px';
            dropline.style.width = (r.width / dz) + 'px';
            dropline.style.top = ((r.top + window.scrollY) / dz - 1) + 'px';
            beforeId = s.getAttribute('data-block-id');
            placed = true;
            break;
          }
        }
        if (!placed) {
          // Past every sibling → drop at the END (beforeId null); line under
          // the last sibling that isn't the dragged block.
          var last = null;
          for (var j = sibs.length - 1; j >= 0; j--) { if (sibs[j] !== dragging) { last = sibs[j]; break; } }
          if (last) {
            var lr = last.getBoundingClientRect();
            var lz = zf();
            dropline.style.display = 'block';
            dropline.style.left = ((lr.left + window.scrollX) / lz) + 'px';
            dropline.style.width = (lr.width / lz) + 'px';
            dropline.style.top = ((lr.bottom + window.scrollY) / lz + 1) + 'px';
          }
          beforeId = null;
        }
      },
      onEnd: function (dragging, moved) {
        dragging.classList.remove('yarnnn-dragging');
        if (dropline) dropline.style.display = 'none';
        if (moved) {
          var id = dragging.getAttribute('data-block-id');
          // Post the reorder — the parent computes moveBlockTo and lands ONE
          // revision. A no-op drop (onto itself / already in place) is filtered
          // parent-side (moveBlockTo returns null).
          if (id && beforeId !== id) {
            parent.postMessage({ type: 'yarnnn-reorder', blockId: id, beforeBlockId: beforeId }, '*');
          }
        }
        beforeId = null;
      },
    });
  }

  // F5: position the gutter beside the block, tracking the pointer VERTICALLY so
  // it follows the mouse down a tall block (Notion) instead of pinning to the
  // block top. pointerY (viewport) centers the bar on the cursor, clamped to
  // the block's own top/bottom so it never floats past the block's edges.
  function showFor(block, pointerY) {
    build();
    curBlock = block;
    var rect = block.getBoundingClientRect();
    bar.style.display = 'flex';
    // The bar's own offsetWidth/Height are already LAYOUT px; the rect and
    // pointerY are visual. Convert the rect into layout space first, then do
    // all the math in one coordinate system (ADR-466 P9).
    var z = zf();
    var w = bar.offsetWidth || 42;
    var h = bar.offsetHeight || 22;
    var left = (rect.left + window.scrollX) / z;
    var top = (rect.top + window.scrollY) / z;
    var bottom = (rect.bottom + window.scrollY) / z;
    bar.style.left = Math.max(2, left - w - 4) + 'px';
    var topV;
    if (pointerY != null) {
      // center on the cursor, clamped inside [top, bottom - h]
      var py = (pointerY + window.scrollY) / z;
      topV = Math.min(Math.max(py - h / 2, top), bottom - h);
    } else {
      topV = top + 1;
    }
    bar.style.top = topV + 'px';
  }
  function hide() {
    if (bar) bar.style.display = 'none';
    curBlock = null;
  }

  // ── The ROW BAND (2026-07-15) ────────────────────────────────────────────
  // Resolve the pointer to a row by GEOMETRY, not by hit-testing e.target.
  //
  // The old rule was e.target.closest('[data-block]') — the gutter appeared
  // only while the pointer was literally inside a block's text box. But the bar
  // DRAWS in the left margin (rect.left - w - 4), which is OUTSIDE that box: to
  // reach the +, you had to leave the region that summoned it, and a 150ms
  // timer began hiding it. The affordance lived outside the area that kept it
  // alive, with dead space between. Hence "sometimes it's there, sometimes it
  // isn't" — it depended on pixel-exact containment.
  //
  // Notion owns the whole ROW: a horizontal band spanning the content column,
  // top-to-bottom of the block, INCLUDING the left lane where the handles sit.
  // Hover anywhere in the band and the row is yours; travelling to the + never
  // leaves it. That is what this does — find the block whose vertical extent
  // contains the pointer (nearest, if between blocks), and claim it as long as
  // the pointer is within the band's horizontal reach (the content column plus
  // the gutter lane to its left).
  var BAND_LEFT_REACH = 64;  // px left of the block box — the gutter lane
  var BAND_RIGHT_REACH = 24; // px right — a little forgiveness, no dead edge

  function rowAt(x, y) {
    var blocks = document.querySelectorAll('[data-block]');
    var best = null, bestDist = Infinity;
    for (var i = 0; i < blocks.length; i++) {
      var b = blocks[i];
      // A ROW is a thing in FLOW. A block inside a frame (a slide, a media
      // box) is placed, not stacked — it has no row above or below to be
      // inserted between, and its gesture is the corner handle, not the
      // gutter. One gate (measurableFrame) decides both affordances, so the
      // two can never both appear on the same block: framed → handles,
      // flowing → gutter. ADR-461 D4's "boundary made visible", applied to
      // the gutter as well as to the handle it was already applied to.
      if (isMeasurable(b)) continue;
      // Skip a block nested inside another annotated block: the ROW is the
      // outermost unit (a checklist's li is not its own row).
      if (b.parentElement && b.parentElement.closest && b.parentElement.closest('[data-block]')) continue;
      var r = b.getBoundingClientRect();
      if (r.height === 0) continue;
      if (x < r.left - BAND_LEFT_REACH || x > r.right + BAND_RIGHT_REACH) continue;
      // Inside the block's vertical extent → this row, unambiguously.
      if (y >= r.top && y <= r.bottom) return b;
      // Otherwise remember the nearest, so the gaps BETWEEN blocks still
      // resolve to a row (no flicker crossing a margin).
      var d = y < r.top ? r.top - y : y - r.bottom;
      if (d < bestDist) { bestDist = d; best = b; }
    }
    // Only claim a near-miss if it is genuinely close — past that, the pointer
    // is in open space (below the last block, in a page margin) and no row owns
    // it. 24px ≈ one line's leading.
    return bestDist <= 24 ? best : null;
  }

  document.addEventListener('mousemove', function (e) {
    var t = e.target;
    if (t && t.closest && t.closest('.yarnnn-gutter')) {
      if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
      return;
    }
    var blk = rowAt(e.clientX, e.clientY);
    if (blk) {
      if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
      var editingId = window.__yarnnnEditingId ? window.__yarnnnEditingId() : null;
      if (editingId != null && blk.getAttribute('data-block-id') === editingId) { hide(); return; }
      // F5: reposition on EVERY move within the row so the gutter tracks the
      // pointer vertically (Notion) instead of pinning to the block top.
      showFor(blk, e.clientY);
      return;
    }
    // A short grace delay bridges the gap between the block and the gutter
    // (F5: 150ms, down from 300 — the old lag read as sluggishness on exit).
    if (!hideTimer) hideTimer = setTimeout(function () { hideTimer = null; hide(); }, 150);
  });
  // Rects go stale on scroll — re-anchor to the block top (no pointer during
  // scroll), or hide if the block left the DOM.
  document.addEventListener('scroll', function () {
    if (curBlock && curBlock.isConnected) showFor(curBlock, null);
    else hide();
  }, true);

  // ── The column divider (ADR-461 D3) — snap-handle resize ────────────────
  // ADR-453 D7 named this exactly: "column-divider ... handles that step
  // through token stops (2-1 -> 1-1 -> 1-2), NEVER free pixels". So the drag
  // does not write a width — it picks which STOP the ratio token names, and the
  // kernel's existing [data-ratio] rules do the rest. Nothing continuous enters
  // the artifact; this is why D3 needs no amendment to the token model.
  //
  // The SECOND bindGesture caller, and the reason the primitive was extracted:
  // this is X-axis with no drop target and no sibling list, sharing only what
  // is genuinely common (capture, threshold, click-suppression).
  //
  // 1-1 is the ABSENCE of the token (.col { flex: 1 } is the default), so the
  // middle stop is written by REMOVING the attribute — the pad/valign/fit
  // convention, not a third value.
  var divider = null;
  var dividerCols = null;

  function ensureDivider() {
    if (divider) return divider;
    divider = document.createElement('div');
    divider.className = 'yarnnn-coldiv';
    document.body.appendChild(divider);
    bindGesture(divider, function () { return dividerCols; }, {
      axis: 'xy',
      onMove: function (cols, e) {
        // Which stop is the cursor nearest? The gap centre is 1-1; left of it
        // weights the right column, right of it weights the left.
        var r = cols.getBoundingClientRect();
        var frac = (e.clientX - r.left) / (r.width || 1);
        var stop = frac < 0.42 ? '1-2' : frac > 0.58 ? '2-1' : null;
        // Preview live, in-frame only — the commit happens on release.
        var page = cols.closest('[data-arrange]');
        if (!page) return;
        if (stop) page.setAttribute('data-ratio', stop);
        else page.removeAttribute('data-ratio');
      },
      onEnd: function (cols, moved) {
        if (!moved) return;
        var page = cols.closest('[data-arrange]');
        if (!page) return;
        // Post the STOP, not a width. The parent lands it through the one door
        // as an attributed revision (setToken / clearToken) — the gesture
        // composes an existing op, it is not a second write path (ADR-461 D2).
        parent.postMessage({
          type: 'yarnnn-ratio',
          pageIndex: pageIndexOf(page),
          value: page.getAttribute('data-ratio'),
        }, '*');
      },
    });
    return divider;
  }

  function showDivider(cols) {
    ensureDivider();
    dividerCols = cols;
    var r = cols.getBoundingClientRect();
    // The gap between the two columns — the divider sits on it.
    var kids = cols.querySelectorAll(':scope > .col');
    if (kids.length !== 2) { hideDivider(); return; }
    var a = kids[0].getBoundingClientRect();
    var z = zf();
    divider.style.display = 'block';
    divider.style.left = ((a.right + window.scrollX) / z) + 'px';
    divider.style.top = ((r.top + window.scrollY) / z) + 'px';
    divider.style.height = (r.height / z) + 'px';
  }
  function hideDivider() {
    if (divider) divider.style.display = 'none';
    dividerCols = null;
  }

  document.addEventListener('pointermove', function (e) {
    // Only a 2-column region gets a divider, and only when the pointer is in
    // it. A slide is exempt from the ratio token today (it applies to
    // page-multicol), so this follows the token's own scope rather than
    // inventing a second one.
    var t = e.target;
    var cols = t && t.closest ? t.closest('.cols') : null;
    if (cols && cols.querySelectorAll(':scope > .col').length === 2) showDivider(cols);
    else if (dividerCols && !divider.contains(t)) hideDivider();
  });

  // ── Resize handles (ADR-461 D4) — the measure gesture ───────────────────
  // bindGesture's THIRD caller. A measured block gets corner/edge handles; the
  // drag reports a PERCENTAGE OF ITS FRAME, never a pixel — which is what makes
  // the value bounded rather than free. The parent clamps to the kernel's own
  // declared min/max and lands setMeasure through the one door.
  //
  // MEASURABLE only where a frame bounds it (ADR-461 D4): a block on a slide
  // (the 16:9 stage) or a media block (its intrinsic ratio is its frame). A
  // block in a document/article/page reflows and has no frame — it gets no
  // handles, which is the boundary made visible rather than merely documented.
  var MEASURE_MEDIA = { figure: 1, chart: 1, gallery: 1 };
  var selBlock = null; // the block the bounding box is anchored on

  /** The frame a block's measure is a PERCENT OF — the nearest thing that
   *  actually bounds its box, which is not always the slide.
   *
   *  This asks a different question than "is this measurable at all?" (the
   *  ADR-461 D4 gate). That one is a yes/no about responsive obligation; this
   *  one is "which rectangle?" — and reusing the gate's answer for it was the
   *  bug: closest('.slide') returns the slide for a block nested three deep
   *  in '.cols > .col[data-slot]', so the runtime wrote a percent of the SLIDE
   *  while the member dragged a box laid out inside a HALF-WIDTH COLUMN. The
   *  number and the rectangle referred to different things.
   *
   *  The .col rule (flex: 1, studio.py) is what genuinely bounds a block in a
   *  column, so the column is the frame. The slide is the frame only for a
   *  block the slide itself lays out. Nearest-first, always.  */
  /** IS this block measurable? — the ADR-461 D4 gate. A yes/no about
   *  RESPONSIVE OBLIGATION: a slide has a fixed 16:9 stage, a media block has
   *  its intrinsic ratio; a document/article/page block has only a viewport to
   *  guess at. This is what decides handles-vs-gutter, and it must keep asking
   *  about the SLIDE (a column inside a document reflows just as its page
   *  does — being a column does not create a frame). */
  function isMeasurable(block) {
    if (!block) return false;
    // ADR-466 P9 grain gate: only a BLOCK is measurable. Selection can also
    // land on a slot or a page (the pointer ladder's coarser grains) and both
    // pass closest('.slide') — which put the bounding box on a SLOT and sent
    // geometry ops with no data-block-id (the red "Could not apply that here").
    // A slot keeps its own affordances (persistent dashed bound, add-here);
    // the object chrome is the block's alone.
    if (!block.hasAttribute || !block.hasAttribute('data-block')) return false;
    var kind = block.getAttribute('data-block');
    if (kind && MEASURE_MEDIA[kind]) return true;
    return !!(block.closest && block.closest('.slide'));
  }

  /** WHICH rectangle is the measure a percent of? — a different question, and
   *  conflating it with the gate above was the bug. 'closest('.slide')'
   *  answers "is there a frame" correctly and "which frame" wrongly: for a
   *  block nested in '.cols > .col[data-slot]', it returned the SLIDE, so the
   *  runtime wrote a percent of the slide while the member dragged a box laid
   *  out inside a HALF-WIDTH COLUMN — the number and the rectangle meant
   *  different things.
   *
   *  '.col { flex: 1 }' (studio.py) is what actually bounds a block in a
   *  column, so the column is the frame. The slide is the frame only for a
   *  block it lays out directly. Nearest-first, always. */
  function measurableFrame(block) {
    if (!isMeasurable(block)) return null;
    var kind = block.getAttribute('data-block');
    if (kind && MEASURE_MEDIA[kind]) return block.parentElement;
    var col = block.closest ? block.closest('.col, [data-slot]') : null;
    if (col && col !== block) return col;
    return block.closest ? block.closest('.slide') : null;
  }

  /** The SERVED bounds (ADR-485 D3), with the permissive pre-485 fallback.
   *  window.__yarnnnMeasureBounds is written by the projection immediately
   *  above this script from vocabulary.measures. The runtime clamps the PREVIEW,
   *  which is the number the member sees and the box they release on; the op
   *  clamps again at the write (the two-clamp rule is unchanged). Before this,
   *  the preview floored BOTH axes at a hardcoded 1 while the kernel serves
   *  w.min = 10 — so a 3% width previewed at 3% and landed at 10%. */
  var MEASURE_BOUNDS = (window.__yarnnnMeasureBounds) || {};
  function measureBound(key, edge, fallback) {
    var b = MEASURE_BOUNDS[key];
    return b && typeof b[edge] === 'number' ? b[edge] : fallback;
  }
  var MEASURE_MIN = { w: measureBound('w', 'min', 1), h: measureBound('h', 'min', 1) };
  var MEASURE_MAX = { w: measureBound('w', 'max', 100), h: measureBound('h', 'max', 100) };
  /** Clamp a committed value to the served bound for its key. The COMMIT
   *  clamps too (not just the preview) so the receipt the parent builds from
   *  this message states what actually landed — a revision message reading
   *  "width 3%" over an artifact holding 10% is a receipt that misstates the
   *  substrate, which is worse than the visual snap it accompanies. */
  function clampMeasure(key, v) {
    return Math.max(measureBound(key, 'min', 0), Math.min(measureBound(key, 'max', 100), v));
  }

  /** WHICH RECTANGLE is the percent a percent OF? (ADR-485 D1)
   *
   *  measurableFrame answers "which ELEMENT bounds this block". That is not the
   *  whole question, because one element carries three rectangles and the CSS
   *  box model uses a DIFFERENT one per axis-class:
   *
   *    width:% / height:%  on a child        -> the frame's CONTENT box
   *    left:% / top:%      on an abs child   -> the frame's PADDING box
   *
   *  getBoundingClientRect() returns neither — it returns the BORDER box. That
   *  was the bug: the commit divided by the border box while CSS multiplied by
   *  the content box, so on a slide carrying padding 3.5rem/4rem every drag
   *  committed ~87% of what the member drew, and each correction lost the same
   *  fraction again (100 -> 87 -> 76 -> 66 -> 57, measured in Chrome).
   *
   *  Returned in the SAME visual-pixel space as getBoundingClientRect(), so the
   *  percent math stays zoom-invariant (visual/visual) exactly as before —
   *  getComputedStyle padding is layout px, so it is scaled by zf() to match
   *  the rect it is being subtracted from. One helper, four callers (resize
   *  preview + commit, move preview + commit): the preview and the commit can
   *  no longer disagree, which is what made the gesture unconvergeable. */
  function frameRects(frame) {
    var r = frame.getBoundingClientRect();
    var cs = getComputedStyle(frame);
    var z = zf() || 1;
    var pl = (parseFloat(cs.paddingLeft) || 0) * z;
    var pr = (parseFloat(cs.paddingRight) || 0) * z;
    var pt = (parseFloat(cs.paddingTop) || 0) * z;
    var pb = (parseFloat(cs.paddingBottom) || 0) * z;
    var bl = (parseFloat(cs.borderLeftWidth) || 0) * z;
    var br_ = (parseFloat(cs.borderRightWidth) || 0) * z;
    var bt = (parseFloat(cs.borderTopWidth) || 0) * z;
    var bb = (parseFloat(cs.borderBottomWidth) || 0) * z;
    return {
      // What width:%/height:% resolve against.
      contentW: Math.max(1, r.width - bl - br_ - pl - pr),
      contentH: Math.max(1, r.height - bt - bb - pt - pb),
      // What left:%/top:% resolve against, and the origin they measure FROM
      // (the padding edge = the border edge inset by the border width).
      padW: Math.max(1, r.width - bl - br_),
      padH: Math.max(1, r.height - bt - bb),
      padLeft: r.left + bl,
      padTop: r.top + bt,
      rect: r,
    };
  }

  // (The lone corner grip + ⠿ move grip were replaced by the bounding box
  //  below — ADR-466 P8. Same gestures, same messages' semantics, one honest
  //  object chrome.)

  /** Name the frame, while the member is choosing a percent of it (D8).
   *
   *  The label prefers the frame's OWN name — '[data-slot="side"]' is already
   *  shown on the canvas as SIDE, so a resize inside it reads "SIDE · 60%"
   *  using the vocabulary the member has already met. An unnamed column falls
   *  back to COLUMN, and the slide itself to SLIDE: never a class name, never
   *  a selector — the label is operator words (ADR-443 D3). */
  var frameEl = null;
  function frameLabel(frame) {
    var slot = frame.getAttribute && frame.getAttribute('data-slot');
    if (slot) return slot;
    if (frame.classList && frame.classList.contains('col')) return 'column';
    if (frame.classList && frame.classList.contains('slide')) return 'slide';
    return 'frame';
  }
  function showFrame(frame, txt) {
    if (!frameEl) {
      frameEl = document.createElement('div');
      frameEl.className = 'yarnnn-frame';
      document.body.appendChild(frameEl);
    }
    var r = frame.getBoundingClientRect();
    var z = zf();
    // txt null = at-rest context (the frame's NAME alone rides the selection);
    // a live gesture appends its numbers — "side · 62% × 40%".
    frameEl.setAttribute('data-label', txt ? frameLabel(frame) + ' · ' + txt : frameLabel(frame));
    frameEl.style.display = 'block';
    frameEl.style.left = ((r.left + window.scrollX) / z) + 'px';
    frameEl.style.top = ((r.top + window.scrollY) / z) + 'px';
    frameEl.style.width = (r.width / z) + 'px';
    frameEl.style.height = (r.height / z) + 'px';
  }
  function hideFrame() {
    if (frameEl) frameEl.style.display = 'none';
  }

  // ── The bounding box (ADR-466 P8) — the object chrome, made honest ──────
  // The PowerPoint/Fabric grammar: a SELECTED framed block wears a solid box
  // you can GRAB — drag anywhere on it to move (deck only: position needs the
  // fixed stage), pull a corner handle to resize, double-click straight
  // through into text editing. Replaces the lone corner grip + ⠿ move grip
  // (document furniture where an object was expected). Body-appended chrome,
  // never serialized; hidden while editing. Commits stay percents of the
  // frame (structural clamp here; the parent clamps from the SERVED bound;
  // the op clamps again at the write — the two-clamp rule, unchanged).
  var box = null;
  var grabDX = 0, grabDY = 0;

  function positionable(block) {
    return !!(block && block.closest && block.closest('.slide'));
  }

  function previewContext(block) {
    // A pre-v10-kernel artifact has no positioning context yet (the retrofit
    // lands with the commit) — give the PREVIEW one, in-frame only.
    var frame = measurableFrame(block);
    if (frame && getComputedStyle(frame).position === 'static') {
      frame.style.position = 'relative';
    }
    return frame;
  }

  function moveMove(block, e) {
    var frame = measurableFrame(block);
    if (!frame) return;
    var f = frameRects(frame);
    var br = block.getBoundingClientRect();
    // Frame-aware clamp (ADR-466 P9): the block's TRAILING edge is bounded
    // too — x may reach only (100 − width%), so a wide block can never be
    // dragged past the frame it is a percent of. Percent math itself is
    // zoom-invariant (visual/visual), so no zf() here.
    //
    // ADR-485 D1: the two percentages in that clamp must be percentages of the
    // SAME rectangle. They were not — x was a percent of the border box and
    // width a percent of the content box, so (100 - wPct) compared unlike
    // units and the trailing edge was wrong by the padding fraction. x/y are
    // percents of the PADDING box (what left:%/top: % resolve against); the
    // block's own extent is a percent of the CONTENT box (what width:% does).
    // Express the extent in the position's own space before subtracting.
    var wPct = (br.width / f.padW) * 100;
    var hPct = (br.height / f.padH) * 100;
    var xMax = Math.max(0, 100 - wPct);
    var yMax = Math.max(0, 100 - hPct);
    var xPct = Math.max(0, Math.min(xMax, ((e.clientX - grabDX - f.padLeft) / f.padW) * 100));
    var yPct = Math.max(0, Math.min(yMax, ((e.clientY - grabDY - f.padTop) / f.padH) * 100));
    block.style.position = 'absolute';
    block.style.left = xPct + '%';
    block.style.top = yPct + '%';
    block.style.margin = '0';
    showBox(block);
    showFrame(frame, 'x ' + Math.round(xPct) + '% · y ' + Math.round(yPct) + '%');
  }

  function moveEnd(block, moved) {
    if (!moved) { syncFrameContext(); return; }
    var id = block.getAttribute('data-block-id');
    var frame = measurableFrame(block);
    if (!id || !frame) { syncFrameContext(); return; }
    var br = block.getBoundingClientRect();
    // ADR-485 D1: the SAME rectangle the preview used (the padding box, which
    // is what left:%/top:% resolve against) — preview and commit can no longer
    // disagree. Clamp BEFORE rounding, matching moveMove, so a drop the preview
    // allowed cannot round one percent past the frame's trailing edge.
    var f = frameRects(frame);
    var wPct = (br.width / f.padW) * 100;
    var hPct = (br.height / f.padH) * 100;
    var xRaw = Math.max(0, Math.min(Math.max(0, 100 - wPct), ((br.left - f.padLeft) / f.padW) * 100));
    var yRaw = Math.max(0, Math.min(Math.max(0, 100 - hPct), ((br.top - f.padTop) / f.padH) * 100));
    parent.postMessage({
      type: 'yarnnn-geometry',
      blockId: id,
      x: Math.round(xRaw),
      y: Math.round(yRaw),
    }, '*');
    syncFrameContext();
  }

  // Which axes a handle drives (P10 — the conventional 8-handle grammar):
  // edge midpoints are single-axis (e/w = width, n/s = height), corners are
  // both. A 'w' or 'n' handle on a POSITIONED block anchors the OPPOSITE
  // edge — origin and size change together, one geometry revision.
  function sideAxes(side) {
    return {
      west: side.indexOf('w') >= 0,
      east: side.indexOf('e') >= 0,
      north: side.indexOf('n') >= 0,
      south: side.indexOf('s') >= 0,
    };
  }

  function isPositioned(block) {
    return positionable(block) && block.hasAttribute('data-x');
  }

  function resizeMove(block, e, side) {
    var frame = measurableFrame(block);
    if (!frame) return;
    var br = block.getBoundingClientRect();
    // ADR-485 D1 — the two rectangles, named. A resize writes BOTH classes of
    // property on a west/north handle (a width AND a left), and they resolve
    // against DIFFERENT boxes: width:% against the content box, left:% against
    // the padding box. Using one rect for both is what made the drag lose the
    // padding fraction on every release.
    var f = frameRects(frame);
    var ax = sideAxes(side);
    var positioned = isPositioned(block);
    var label = [];
    // ── Horizontal (width; west anchors the right edge when positioned) ──
    if (ax.west || ax.east) {
      var pct, maxPct;
      if (ax.west && positioned) {
        var right = br.right;
        var newLeft = Math.max(f.padLeft, Math.min(e.clientX, right - 8));
        pct = ((right - newLeft) / f.contentW) * 100;
        maxPct = ((right - f.padLeft) / f.contentW) * 100;
        block.style.left = Math.max(0, Math.min(100,
          ((newLeft - f.padLeft) / f.padW) * 100)) + '%';
      } else {
        pct = ((e.clientX - br.left) / f.contentW) * 100;
        // A positioned block's width is bounded by the room to its right —
        // (100 − x%); a flow block by the frame itself (100%).
        maxPct = positioned
          ? 100 - ((br.left - f.padLeft) / f.contentW) * 100
          : 100;
      }
      pct = Math.max(MEASURE_MIN.w, Math.min(Math.max(MEASURE_MIN.w, Math.min(MEASURE_MAX.w, maxPct)), pct));
      block.style.width = pct + '%';
      label.push(Math.round(pct) + '%');
    }
    // ── Vertical (height; north anchors the bottom edge when positioned) ──
    if (ax.north || ax.south) {
      var hpct, hMax;
      if (ax.north && positioned) {
        var bottom = br.bottom;
        var newTop = Math.max(f.padTop, Math.min(e.clientY, bottom - 8));
        hpct = ((bottom - newTop) / f.contentH) * 100;
        hMax = ((bottom - f.padTop) / f.contentH) * 100;
        block.style.top = Math.max(0, Math.min(100,
          ((newTop - f.padTop) / f.padH) * 100)) + '%';
      } else if (ax.north) {
        hpct = ((br.bottom - e.clientY) / f.contentH) * 100;
        hMax = 100;
      } else {
        hpct = ((e.clientY - br.top) / f.contentH) * 100;
        hMax = positioned
          ? 100 - ((br.top - f.padTop) / f.contentH) * 100
          : 100;
      }
      hpct = Math.max(MEASURE_MIN.h, Math.min(Math.max(MEASURE_MIN.h, Math.min(MEASURE_MAX.h, hMax)), hpct));
      block.style.height = hpct + '%';
      label.push(Math.round(hpct) + '%');
    }
    showBox(block);
    // Name what the percent is OF, while it is being chosen (D8) —
    // "62% × 40%" for a corner, one number for an edge handle.
    showFrame(frame, label.join(' × '));
  }

  function resizeEnd(block, moved, side) {
    if (!moved) { syncFrameContext(); return; }
    var id = block.getAttribute('data-block-id');
    var frame = measurableFrame(block);
    if (!id || !frame) { syncFrameContext(); return; }
    var br = block.getBoundingClientRect();
    // ADR-485 D1 — THE defect this ADR exists for. This divided by the frame's
    // BORDER box while the kernel's width: var(--yw) multiplies by its
    // CONTENT box, so a member who dragged to the true edge committed
    // 864/992 = 87%, the block re-rendered 112px narrower, and every attempt
    // to correct it lost the same 13% again (100 -> 87 -> 76 -> 66 -> 57).
    // Measured in Chrome; corroborated by the live corpus, where six authored
    // widths existed and none exceeded 78%.
    //
    // Each axis-class now divides by the box its OWN property resolves against,
    // and by the SAME numbers resizeMove previewed with.
    var f = frameRects(frame);
    var ax = sideAxes(side);
    var positioned = isPositioned(block);
    var msg = { type: 'yarnnn-geometry', blockId: id };
    if (ax.west || ax.east) {
      msg.w = Math.round(clampMeasure('w', (br.width / f.contentW) * 100));
      if (ax.west && positioned) {
        msg.x = Math.round(clampMeasure('x', ((br.left - f.padLeft) / f.padW) * 100));
      }
    }
    if (ax.north || ax.south) {
      msg.h = Math.round(clampMeasure('h', (br.height / f.contentH) * 100));
      if (ax.north && positioned) {
        msg.y = Math.round(clampMeasure('y', ((br.top - f.padTop) / f.padH) * 100));
      }
    }
    parent.postMessage(msg, '*');
    syncFrameContext();
  }

  function ensureBox() {
    if (box) return box;
    box = document.createElement('div');
    box.className = 'yarnnn-selbox';
    box.style.display = 'none';
    document.body.appendChild(box);
    // The INTERIOR is pointer-transparent (CSS) — clicks fall through to the
    // content, so the editor never fights the chrome. MOVE lives on the four
    // BORDER BAND strips (the conventional near-the-border zone, cursor:
    // move). The subject gate makes the band inert where position has no
    // frame to be bounded by (a media block in a flowing document).
    ['n', 'e', 's', 'w'].forEach(function (edge) {
      var strip = document.createElement('div');
      strip.className = 'yarnnn-selmove yarnnn-selmove-' + edge;
      box.appendChild(strip);
      bindGesture(strip, function () { return selBlock && positionable(selBlock) ? selBlock : null; }, {
        axis: 'xy',
        onStart: function (block, e) {
          var br = block.getBoundingClientRect();
          grabDX = e.clientX - br.left;
          grabDY = e.clientY - br.top;
          previewContext(block);
        },
        onMove: moveMove,
        onEnd: moveEnd,
      });
    });
    // EIGHT handles (P10): four corners resize both axes, four edge midpoints
    // one axis each — the directional cursors are the affordance.
    ['nw', 'ne', 'sw', 'se', 'n', 's', 'e', 'w'].forEach(function (side) {
      var h = document.createElement('div');
      h.className = 'yarnnn-selh yarnnn-selh-' + side;
      box.appendChild(h);
      bindGesture(h, function () { return selBlock; }, {
        axis: 'xy',
        onStart: function (block) { previewContext(block); },
        onMove: function (block, ev) { resizeMove(block, ev, side); },
        onEnd: function (block, moved) { resizeEnd(block, moved, side); },
      });
    });
    return box;
  }

  function showBox(block) {
    ensureBox();
    selBlock = block;
    var r = block.getBoundingClientRect();
    var z = zf();
    box.style.display = 'block';
    box.style.left = ((r.left + window.scrollX) / z - 1) + 'px';
    box.style.top = ((r.top + window.scrollY) / z - 1) + 'px';
    box.style.width = (r.width / z + 2) + 'px';
    box.style.height = (r.height / z + 2) + 'px';
    // The band is honest about inertness: no move cursor where no move exists.
    box.className = positionable(block)
      ? 'yarnnn-selbox'
      : 'yarnnn-selbox yarnnn-selbox-static';
  }
  function hideBox() {
    if (box) box.style.display = 'none';
    selBlock = null;
    hideFrame();
  }

  /** P10: the frame reference is visible WHENEVER the box is — not only
   *  mid-gesture. "What am I resizing against" was answered only during the
   *  drag (D8's live numbers); at rest the member saw one rectangle and had
   *  to infer the second. Now the named green outline rests with the
   *  selection, and the gesture handlers overlay the live numbers on it. */
  function syncFrameContext() {
    if (!selBlock || !selBlock.isConnected) { hideFrame(); return; }
    var frame = measurableFrame(selBlock);
    if (frame) showFrame(frame, null);
    else hideFrame();
  }

  // The handle follows the SELECTION, not the pointer.
  //
  // It was bound to hover, which cannot work: the handle draws at the block's
  // bottom-right corner, so travelling to grab it moves the pointer out of the
  // block that summoned it — the affordance disappeared exactly as it was
  // reached for. (The gutter had the identical bug and was fixed the same way,
  // by owning a band rather than a box; a placed block has no band, so it owns
  // its SELECTION instead.) Claude Design's inspector shows handles on the
  // selected object for the same reason: a grip must outlive the journey to it.
  //
  // Selection is read from the pointer runtime's own state — one selection, not
  // two. Re-anchor on every relevant transition; the rect goes stale otherwise.
  // ── The selected block's keyboard (ADR-462 D10) ─────────────────────────
  //
  // The menu shipped ⌘C / ⌘V / ⌘D / ⌫ as row hints and NOTHING listened. Seven
  // keydown handlers existed in this runtime and every one guards on
  // a live editingEl — they all serve the EDITING caret (slash, Enter-split,
  // Backspace-merge, arrows, Esc). The SELECTED state, which Esc deliberately
  // lifts you into, had no keyboard at all. So the hints were decoration.
  //
  // This is the missing half, and it is the same shape as every other gesture:
  // the runtime hears the key and posts an existing verb — no new op, no second
  // write path (D1). The parent is unreachable by keyboard here anyway: the
  // canvas is a sandboxed iframe, so keys land in THIS document or nowhere.
  //
  // Guards, in order: never when a caret is live (editing owns its own keys),
  // never inside injected chrome, and never when the member is selecting text.
  //
  // ── The guard's seam, re-cut (P11 fallout) ──────────────────────────
  // This asked "is anything editing?" and refused if so. That was correct
  // while SELECTED and EDITING were mutually exclusive — but P10/P11 made
  // the box PERSIST through editing (border dashed, all eight handles
  // live), and the staged click ladder enters text on a block that is
  // still selected. So a block routinely looks selected — box drawn,
  // handles up — while editingId is non-null, and every verb key silently
  // did nothing. Delete worked only after an Esc nothing advertised.
  //
  // The honest question is not "is anything editing" but "does the CARET
  // own this key right now". It owns it when the caret is live in THIS
  // block and there is text for the key to act on. On an empty block the
  // caret has nothing to bite (the Backspace-empty rule above handles it);
  // on a DIFFERENT block, the selection is the member's real subject.
  // ADR-482 D2: the keyboard VERBS (⌘C/⌘V/⌘D/⌫) moved to the pointer runtime.
  // They lived here only by historical accident, and GUTTER_SCRIPT is not
  // injected on flow (ADR-481 D2) — so on every document the right-click menu
  // advertised shortcut hints for keys that did nothing. An affordance's
  // injection site must follow its LIFETIME, not the script it was first
  // written into. The gutter keeps what is genuinely gutter: '+', ⋮⋮, selbox.

  // ── Undo / Redo (⌘Z / ⌘⇧Z) ───────────────────────────────────────────────
  //
  // Unlike the verb keys above, undo is NOT scoped to a selected block — it
  // reverses the LAST edit whether or not anything is selected, so it gets its
  // own top-level listener instead of extending the selected-block handler
  // (which returns early on no selection). The parent owns the snapshot stack
  // (one HTML string per whole op); the runtime only hears the key and asks.
  //
  // The one guard is the same as ⌘C/⌘V above: when a text caret is LIVE, undo
  // belongs to the platform — the browser's native contentEditable stack
  // rewinds the member's typing, keystroke by keystroke, better than we could.
  // Our stack takes over the moment the caret leaves (edits commit on blur as
  // whole ops). So: caret live → let it through; no caret → claim it.
  document.addEventListener('keydown', function (e) {
    if (!(e.metaKey || e.ctrlKey)) return;
    if ((e.key || '').toLowerCase() !== 'z') return;
    // A live caret owns its own undo — don't steal the native text stack.
    if (window.__yarnnnEditingId && window.__yarnnnEditingId() != null) return;
    var t = e.target;
    // Injected chrome (gutter/format bar) is never an undo subject.
    if (t && t.closest && (t.closest('.yarnnn-gutter') || t.closest('.yarnnn-fmt'))) return;
    e.preventDefault();
    parent.postMessage({ type: e.shiftKey ? 'yarnnn-redo' : 'yarnnn-undo' }, '*');
  });

  function syncBox() {
    // P11 (operator read of P10 — the PowerPoint convention): the box
    // PERSISTS through text editing. The handles stay reachable while the
    // caret is live — the interior is pointer-transparent, so the chrome no
    // longer fights the editor — and the border goes DASHED as the text-mode
    // cue. ("Hidden while editing" was the P8 rule from the click-trapping
    // box; it outlived its cause and starved the object grammar exactly
    // where the member was looking at the object.)
    var editing = window.__yarnnnEditingId ? window.__yarnnnEditingId() : null;
    var sel = window.__yarnnnSelected ? window.__yarnnnSelected() : null;
    var target = sel && sel.isConnected ? sel : null;
    if (!target && editing != null) {
      // Click-to-caret can enter edit without routing through the pointer's
      // selection — the editing block still owns its box.
      try {
        target = document.querySelector('[data-block-id="' +
          (window.CSS && CSS.escape ? CSS.escape(editing) : editing) + '"]');
      } catch (err) { target = null; }
    }
    if (target && target.isConnected && isMeasurable(target)) {
      showBox(target);
      if (editing != null) box.className += ' yarnnn-selbox-editing';
      syncFrameContext();
    } else hideBox();
  }
  // A click lands selection in the pointer runtime's capture-phase listener;
  // this runs after it (bubble), so the selection is already the new block.
  // A click ON the grip is the grip's own (a press that never passed the
  // gesture threshold) — it must not re-anchor the thing being grabbed.
  document.addEventListener('click', function (e) {
    if (box && box.contains(e.target)) return;
    syncBox();
  });
  document.addEventListener('scroll', syncBox, true);
  window.addEventListener('resize', syncBox);
  // Typing reflows the block — with the box now persisting through editing
  // (P11), keep it hugging the live text instead of going stale mid-word.
  document.addEventListener('input', function () { setTimeout(syncBox, 0); }, true);
  // The parent may select (navigator, Design tab) without a click in-frame.
  window.addEventListener('message', function (e) {
    var d = e.data;
    if (d && typeof d === 'object' && typeof d.type === 'string' &&
        d.type.indexOf('yarnnn-') === 0) setTimeout(syncBox, 0);
  });
})();
`;

/** Remove every artifact-authored executable: script/iframe/object/embed
 *  elements + inline on* handlers + javascript: URLs. The posture forbids
 *  them; this enforces the rule mechanically before allow-scripts renders. */
function stripExecutable(doc: Document): void {
  doc.querySelectorAll('script, iframe, object, embed').forEach((el) => el.remove());
  doc.querySelectorAll('*').forEach((el) => {
    for (const attr of Array.from(el.attributes)) {
      const name = attr.name.toLowerCase();
      if (name.startsWith('on')) el.removeAttribute(attr.name);
      else if (
        (name === 'href' || name === 'src') &&
        attr.value.trim().toLowerCase().startsWith('javascript:')
      ) {
        el.removeAttribute(attr.name);
      }
    }
  });
}

/** Resolve every `data-ref` citation in the artifact's HTML; returns the
 *  projected document string ready for the canvas iframe's srcDoc.
 *  `pointer: true` (the Studio canvas) additionally strips all artifact-
 *  authored executables and injects the pointer runtime; `edit: true`
 *  (ADR-446) also stamps citation islands with their SOURCE outerHTML and
 *  injects the edit runtime so blocks become editable in place. */
export async function resolveArtifactHtml(
  html: string,
  artifactPath: string,
  opts?: {
    pointer?: boolean;
    edit?: boolean;
    mode?: 'flow' | 'paged';
    /** ADR-485 D3 — the SERVED measure bounds (`vocabulary.measures`), keyed by
     *  measure key. The in-gesture clamp used to hardcode `1` for both axes
     *  while the kernel serves `w.min = 10` and `h.min = 1`, so a width dragged
     *  to 3% previewed at 3% and landed at 10% — wider than the box the member
     *  released on. The runtime must never invent a bound (ADR-461 D4: the
     *  kernel names it, nothing downstream re-derives it), so the parent passes
     *  what the registry served. Omitted → the gesture falls back to the
     *  permissive [1,100] it always used, which is the pre-ADR-485 behaviour. */
    measureBounds?: Record<string, { min: number; max: number }>;
  },
): Promise<string> {
  if (!html) return html;
  if (!opts?.pointer && !html.includes('data-ref')) return html;
  const doc = new DOMParser().parseFromString(html, 'text/html');
  // ADR-480: stamp the layout's MODE for the runtime. The parent reads it from
  // the served layout registry, so the runtime never learns a layout SLUG — a
  // new layout declares its mode once in the kernel (ADR-222: the kernel names
  // the category, never the instance). Projection-time chrome, never
  // serialized: this attribute rides the projected document only, and the
  // write path reads the artifact's SOURCE, so it can never reach substrate.
  if (opts?.pointer && opts?.mode) {
    doc.documentElement?.setAttribute('data-yarnnn-mode', opts.mode);
  }
  const cited = Array.from(doc.querySelectorAll('[data-ref]'));
  // ADR-446 D3: stamp each citation's SOURCE outerHTML BEFORE resolution
  // mutates it — by render time its content is resolved and the source form
  // is otherwise unrecoverable. On edit-commit the runtime restores islands
  // from data-src-html so a text edit never bakes a reference.
  if (opts?.edit) {
    cited.forEach((el) => {
      // NEVER a style element (ADR-462 D13). The stamp exists so an edited
      // block's citation ISLANDS restore to their source form; a marked skin
      // is not an island and is never inside an edited block. Stamping it
      // would URI-encode the whole composed skin (5.7KB on the live YARNNN
      // system) into an attribute — and worse, hand the restore path a
      // snapshot containing signed blob URLs to write back to source.
      if (el.tagName === 'STYLE') return;
      el.setAttribute('data-src-html', encodeURIComponent(el.outerHTML));
    });
  }
  await Promise.all(cited.map((el) => resolveOne(el, artifactPath)));
  // ── ADR-481 D5: flatten legacy arrangements on FLOW, at projection ──────
  // Existing flow artifacts carry the old scaffold's `<section data-arrange>`
  // wrapping a `<div data-slot>` — which renders as a dead vertical void
  // (the operator's screenshot). We do NOT migrate the substrate: rewriting
  // live content to fix a chrome problem would manufacture revisions nobody
  // authored (ADR-209). Instead the projection unwraps them, lifting children
  // in document order. The SOURCE is untouched; because ADR-480's flow writes
  // serialize what the member edited, a legacy artifact flattens PERMANENTLY
  // on its next edit — migration by use, attributed to whoever actually typed.
  //
  // This re-parents, never rewrites: blocks, ids, citations and data-ref pins
  // all survive. Paged projections are untouched (a slide IS its arrangement).
  if (opts?.mode === 'flow') {
    doc.querySelectorAll('[data-arrange]').forEach((section) => {
      const parent = section.parentNode;
      if (!parent) return;
      // Slots are pure containers on flow — lift their children too, so a
      // `<section data-arrange><div data-slot>…</div></section>` collapses in
      // one pass rather than leaving an orphaned slot div behind.
      section.querySelectorAll('[data-slot]').forEach((slot) => {
        while (slot.firstChild) slot.parentNode?.insertBefore(slot.firstChild, slot);
        slot.remove();
      });
      while (section.firstChild) parent.insertBefore(section.firstChild, section);
      section.remove();
    });
  }
  if (opts?.pointer) {
    stripExecutable(doc);
    const style = doc.createElement('style');
    // DECK_STAGE_CSS self-gates on html[data-template="deck"] — harmless on
    // document/article, load-bearing on decks (fixes the narrow-column collapse).
    // ADR-481 D3: POINTER_CSS's block-hover outline is PAGED-only — on a
    // continuous writing surface the caret and the I-beam already say where a
    // click lands, and boxing prose as the pointer travels re-asserts the
    // enclosure ADR-480 dissolved. FLOW_POINTER_CSS keeps what still means
    // something there: the neutral selection outline for non-text OBJECTS
    // (figure/table/chart/gallery are still selectable, right-clickable,
    // addressable) plus the D2 empty-state hint.
    //
    // ADR-482 D3: the mode gates the GRAIN; the chrome WAITS for the mode.
    // `mode` is undefined until the vocabulary fetch answers, and every
    // `!== 'flow'` test below read that undefined as PAGED — so a flow
    // document's first frames projected the paged gutter, hover cue and edit
    // outline, then re-projected once the registry landed. That flash is the
    // indigo box the operator photographed on a document. The safe direction
    // is the one that shows LESS chrome (StudioSurface.tsx:571-573): until the
    // mode is KNOWN, mode-specific chrome is withheld rather than guessed.
    const paged = opts?.mode === 'paged';
    const flow = opts?.mode === 'flow';
    style.textContent =
      DECK_STAGE_CSS +
      IMAGE_STAGE_CSS +
      (flow ? FLOW_POINTER_CSS : paged ? POINTER_CSS : '') +
      // ADR-482 D4: the 2px indigo EDIT outline says "this object is live" —
      // true when one block at a time is editable, meaningless on a continuous
      // surface where contenteditable lands on main/article and the selector
      // cannot match. Paged-only, so the intent is legible not accidental.
      (opts?.edit && paged ? EDIT_CSS : '');
    doc.head?.appendChild(style);
    if (opts?.edit) {
      // The edit runtime is injected FIRST so window.__yarnnnEditingId is
      // defined before the pointer runtime checks it (script order = DOM order).
      const editScript = doc.createElement('script');
      editScript.textContent = EDIT_SCRIPT;
      doc.body?.appendChild(editScript);
    }
    const script = doc.createElement('script');
    // ADR-485 D3: the SERVED measure bounds reach the runtime as data, ahead of
    // the runtime that clamps with them. The kernel names the bound; the
    // gesture applies it; nothing in between re-derives it.
    script.textContent =
      `window.__yarnnnMeasureBounds = ${JSON.stringify(opts?.measureBounds ?? null)};\n` +
      POINTER_SCRIPT;
    doc.body?.appendChild(script);
    // ADR-447 Phase 4: empty-slot "+ Add here" (last — decorates the settled
    // DOM; its buttons are not [data-block], so pointer selection ignores them).
    // ADR-481 D1: PAGED only — flow layouts serve no arrangements, so there is
    // no slot to decorate (and the legacy flatten above removed any left over).
    // ADR-482 D3: `paged`, not `!== 'flow'` — an unresolved mode gets nothing.
    if (paged) {
      const addHere = doc.createElement('script');
      addHere.textContent = ADD_HERE_SCRIPT;
      doc.body?.appendChild(addHere);
    }
    if (opts?.edit && paged) {
      // ADR-458: the hover gutter (after the pointer — it uses the pointer's
      // __yarnnnSelect + the edit runtime's __yarnnnEditingId).
      //
      // ADR-481 D2: NOT on flow. The gutter answers "insert HERE" — meaningful
      // when blocks were enclosures with gaps between them, meaningless once
      // the caret IS the insertion point (ADR-480). An affordance that points
      // at a place answers a question a continuous surface never asks. Insert
      // on flow is `/` at the caret and right-click — both already built, both
      // better suited. This is a removal, not a replacement.
      const gutter = doc.createElement('script');
      gutter.textContent = GUTTER_SCRIPT;
      doc.body?.appendChild(gutter);
    }
  }
  const doctype = '<!doctype html>\n';
  return doctype + (doc.documentElement?.outerHTML ?? html);
}

/** The Web Viewer's projection hook (ADR-441 D3). Resolves citations when the
 *  content carries any, holding the frame empty until the projection lands so
 *  a broken-citation flash never paints; non-citing HTML short-circuits (the
 *  caller renders it verbatim). Falls back to the raw content on a projection
 *  failure — safe, because the Web Viewer's iframe is fully sandboxed
 *  (`sandbox=""`, no scripts), unlike the Studio canvas's pointer mode. */
export function useArtifactProjection(file: WorkspaceFile): {
  needsProjection: boolean;
  projected: string | null;
} {
  const content = file.content ?? '';
  const needsProjection = content.includes('data-ref');
  const [projected, setProjected] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    setProjected(null);
    if (!needsProjection) return;
    resolveArtifactHtml(content, file.path)
      .then((html) => !cancelled && setProjected(html))
      .catch(() => !cancelled && setProjected(content));
    return () => {
      cancelled = true;
    };
  }, [content, file.path, needsProjection]);
  return { needsProjection, projected };
}
