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

async function resolveOne(el: Element, artifactPath: string): Promise<void> {
  // The MARKED style elements (data-skin / data-kernel, ADR-449/453) carry
  // data-ref as an EDGE citation (trace/dependents) — their CSS is already
  // composed in place. Resolving "into" them would replace the skin's CSS
  // with the manifest's text (ADR-456 W3 fix — never touch a style element).
  if (el.tagName === 'STYLE') return;
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

const POINTER_CSS = `
${POINTABLE.split(',').map((s) => `${s}:hover`).join(',')} {
  outline: 1px dashed rgba(99,102,241,0.45); outline-offset: 2px; cursor: pointer;
}
.yarnnn-pointed { outline: 2px solid #6366f1 !important; outline-offset: 2px; }
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
  border: 1px dashed rgba(99,102,241,0.5); border-radius: 6px;
  background: rgba(99,102,241,0.04); color: #6366f1;
  font: 500 0.8rem system-ui, sans-serif; cursor: pointer; text-align: center;
}
.yarnnn-add-here:hover { background: rgba(99,102,241,0.1); }
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
html[data-template="deck"] body { display: flex; flex-direction: column; align-items: center; }
html[data-template="deck"] .slide {
  width: ${DECK_STAGE_W}px !important;
  height: ${DECK_STAGE_H}px !important;
  aspect-ratio: auto !important;
  flex: 0 0 auto;
}
`;

// The TEXT-editable block kinds (ADR-456 W2's Turn-into set): a single click on
// one of these enters edit-at-caret (F4); media/data/structured kinds
// (figure/gallery/table/metrics/chart) stay select-only. Kept in sync with the
// StudioDesignTab TURN_INTO_KINDS + the heading anchor kind.
const TEXT_KINDS_JS = JSON.stringify(['prose', 'callout', 'quote', 'checklist', 'toggle', 'heading']);

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
      var onIsland = t && t.closest ? t.closest('[data-ref]') : null;
      if (blk && blkKind && TEXT_KINDS.indexOf(blkKind) !== -1 && !onIsland
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

  // ADR-458: the hover gutter selects THROUGH this runtime's own selection
  // state (one selection, not two) — exposed like __yarnnnEditingId.
  window.__yarnnnSelect = function (el) {
    if (!el || !el.classList) return;
    if (cur) cur.classList.remove('yarnnn-pointed');
    cur = el;
    el.classList.add('yarnnn-pointed');
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
    } else if (d.type === 'yarnnn-restore-scroll' && typeof d.y === 'number') {
      // The parent captured the pre-reload scroll (the runtime reports it on
      // scroll below) and restores it after a STRUCTURAL reload so the canvas
      // doesn't jump to the top — the reloads that remain feel like nothing
      // moved. Opaque origin means the parent can't read scrollTop directly,
      // so this round-trips through the runtime.
      try { window.scrollTo(0, d.y); } catch (err) {}
    }
  });

  // Report the scroll position to the parent (throttled) so it can restore it
  // across a structural reload. The parent keeps only the latest value.
  var scrollReportTimer = null;
  window.addEventListener('scroll', function () {
    if (scrollReportTimer) return;
    scrollReportTimer = setTimeout(function () {
      scrollReportTimer = null;
      parent.postMessage({ type: 'yarnnn-scroll-pos', y: window.scrollY || 0 }, '*');
    }, 120);
  }, true);
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
      if (slot.querySelector('[data-block]')) continue;
      if (slot.querySelector('.yarnnn-add-here')) continue;
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'yarnnn-add-here';
      btn.textContent = '+ Add here';
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
  outline: 2px solid #6366f1 !important; outline-offset: 3px;
  background: rgba(99,102,241,0.04);
}
[data-block][contenteditable="true"] [data-ref] {
  outline: 1px dashed rgba(99,102,241,0.5); cursor: default;
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
.yarnnn-dragging { opacity: 0.4; }
.yarnnn-dropline {
  position: absolute; z-index: 9997; height: 2px; background: #6366f1;
  border-radius: 2px; pointer-events: none; display: none;
  box-shadow: 0 0 0 1px rgba(99,102,241,0.3);
}
`;

const EDIT_SCRIPT = `
(function () {
  var TEXT_KINDS = ${TEXT_KINDS_JS};
  var editingId = null;      // the block currently in edit mode
  var editingEl = null;
  var idleTimer = null;

  // Restore every citation island in the block to its SOURCE form, then read
  // the block's inner — the source-mapped emit (D2/D3).
  function readSourceInner(el) {
    if (!el || !el.cloneNode) return '';
    var clone = el.cloneNode(true);
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
    el.__yarnnnBlur = onBlur;
    el.addEventListener('blur', onBlur);
    el.addEventListener('input', function () {
      if (idleTimer) clearTimeout(idleTimer);
      idleTimer = setTimeout(commit, 2000); // idle-2s safety commit (D4)
    });
    // Sanitize paste to plain text — no HTML injection through the clipboard.
    el.addEventListener('paste', function (e) {
      e.preventDefault();
      var text = (e.clipboardData || window.clipboardData).getData('text/plain');
      if (document.queryCommandSupported && document.queryCommandSupported('insertText')) {
        document.execCommand('insertText', false, text);
      }
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
    if (!editingEl) return;
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

  document.addEventListener('selectionchange', function () {
    if (!editingEl) { hideFmt(); return; }
    if (fmtInput && fmtInput.style.display !== 'none') return; // typing a URL
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount || sel.isCollapsed) { hideFmt(); return; }
    var r = sel.getRangeAt(0);
    var anc = r.commonAncestorContainer;
    var ancEl = anc && anc.nodeType === 1 ? anc : (anc ? anc.parentElement : null);
    if (!ancEl || !editingEl.contains(ancEl)) { hideFmt(); return; }
    buildFmtBar();
    var rect = r.getBoundingClientRect();
    if (!rect || (rect.width === 0 && rect.height === 0)) { hideFmt(); return; }
    fmtBar.style.display = 'inline-flex';
    fmtBar.style.left = Math.max(4, rect.left + window.scrollX) + 'px';
    fmtBar.style.top = Math.max(4, rect.top + window.scrollY - 36) + 'px';
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
    if (!caret || caret.startContainer !== slashNode) return null;
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
    if (e.key !== '/' || !editingEl) return;
    if (fmtInput && document.activeElement === fmtInput) return;
    var caret = slashCaret();
    if (!caret || caret.startContainer.nodeType !== 3) return; // not in a text node
    if (caretInIsland()) return; // a citation island owns its own text
    // NO preventDefault + NO exit: the '/' lands and the caret keeps typing.
    var id = editingId;
    var node = caret.startContainer;
    var at = caret.startOffset;
    var rect = editingEl.getBoundingClientRect();
    var empty = (editingEl.textContent || '').trim() === '';
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
    if (e.key !== 'Backspace' || !editingEl) return;
    if (fmtInput && document.activeElement === fmtInput) return;
    if (!caretAtBlockStart() || caretInIsland()) return; // mid-text → native delete
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
      if (slashStart < 0 || !slashNode || !editingEl) return;
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
      var id = editingId;
      slashStart = -1;
      slashNode = null;
      exit(false, true); // silent — the parent's op is the sole writer
      parent.postMessage({ type: 'yarnnn-slash-taken', blockId: id,
        beforeInner: halves ? halves.before : null,
        afterInner: halves ? halves.after : null }, '*');
    }
  });

  // Expose to the pointer runtime so it can suppress its click-to-select while
  // a block is being edited (the caret must land, not a new selection).
  window.__yarnnnEditingId = function () { return editingId; };
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
            dropline.style.display = 'block';
            dropline.style.left = (r.left + window.scrollX) + 'px';
            dropline.style.width = r.width + 'px';
            dropline.style.top = (r.top + window.scrollY - 1) + 'px';
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
            dropline.style.display = 'block';
            dropline.style.left = (lr.left + window.scrollX) + 'px';
            dropline.style.width = lr.width + 'px';
            dropline.style.top = (lr.bottom + window.scrollY + 1) + 'px';
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
    var w = bar.offsetWidth || 42;
    var h = bar.offsetHeight || 22;
    bar.style.left = Math.max(2, rect.left + window.scrollX - w - 4) + 'px';
    var topV;
    if (pointerY != null) {
      // center on the cursor, clamped inside [rect.top, rect.bottom - h]
      topV = Math.min(Math.max(pointerY - h / 2, rect.top), rect.bottom - h);
    } else {
      topV = rect.top + 1;
    }
    bar.style.top = (topV + window.scrollY) + 'px';
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
  opts?: { pointer?: boolean; edit?: boolean },
): Promise<string> {
  if (!html) return html;
  if (!opts?.pointer && !html.includes('data-ref')) return html;
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const cited = Array.from(doc.querySelectorAll('[data-ref]'));
  // ADR-446 D3: stamp each citation's SOURCE outerHTML BEFORE resolution
  // mutates it — by render time its content is resolved and the source form
  // is otherwise unrecoverable. On edit-commit the runtime restores islands
  // from data-src-html so a text edit never bakes a reference.
  if (opts?.edit) {
    cited.forEach((el) => el.setAttribute('data-src-html', encodeURIComponent(el.outerHTML)));
  }
  await Promise.all(cited.map((el) => resolveOne(el, artifactPath)));
  if (opts?.pointer) {
    stripExecutable(doc);
    const style = doc.createElement('style');
    // DECK_STAGE_CSS self-gates on html[data-template="deck"] — harmless on
    // document/article, load-bearing on decks (fixes the narrow-column collapse).
    style.textContent = DECK_STAGE_CSS + POINTER_CSS + (opts?.edit ? EDIT_CSS : '');
    doc.head?.appendChild(style);
    if (opts?.edit) {
      // The edit runtime is injected FIRST so window.__yarnnnEditingId is
      // defined before the pointer runtime checks it (script order = DOM order).
      const editScript = doc.createElement('script');
      editScript.textContent = EDIT_SCRIPT;
      doc.body?.appendChild(editScript);
    }
    const script = doc.createElement('script');
    script.textContent = POINTER_SCRIPT;
    doc.body?.appendChild(script);
    // ADR-447 Phase 4: empty-slot "+ Add here" (last — decorates the settled
    // DOM; its buttons are not [data-block], so pointer selection ignores them).
    const addHere = doc.createElement('script');
    addHere.textContent = ADD_HERE_SCRIPT;
    doc.body?.appendChild(addHere);
    if (opts?.edit) {
      // ADR-458: the hover gutter (after the pointer — it uses the pointer's
      // __yarnnnSelect + the edit runtime's __yarnnnEditingId).
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
