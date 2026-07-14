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
`;

const EDIT_SCRIPT = `
(function () {
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
  function exit(notify) {
    if (idleTimer) { clearTimeout(idleTimer); idleTimer = null; }
    var el = editingEl;
    editingEl = null; editingId = null; // clear FIRST so any re-entry is a no-op
    hideFmt();
    if (el && el.__yarnnnBlur) { el.removeEventListener('blur', el.__yarnnnBlur); el.__yarnnnBlur = null; }
    if (el && el.querySelectorAll) {
      var innerNow = readSourceInner(el);
      if (innerNow) parent.postMessage({ type: 'yarnnn-edit', blockId: el.getAttribute('data-block-id'), newInner: innerNow }, '*');
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

  // ── ADR-456 W2: slash-insert ──────────────────────────────────────────
  // '/' in an EMPTY context (an empty block, or an empty paragraph inside
  // one) commits + exits the edit and asks the parent to open the block
  // palette anchored at the block. A literal '/' in flowing text is untouched
  // (the trigger never fires mid-sentence), so URLs and "and/or" still type.
  function slashContextEmpty() {
    if (!editingEl) return false;
    if ((editingEl.textContent || '').trim() === '') return true;
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount || !sel.isCollapsed) return false;
    var n = sel.anchorNode;
    var p = n && n.nodeType === 1 ? n : (n ? n.parentElement : null);
    while (p && p !== editingEl && !/^(P|LI|H1|H2|H3|H4|SUMMARY|DIV)$/.test(p.tagName)) {
      p = p.parentElement;
    }
    if (!p || p === editingEl) return false;
    return (p.textContent || '').trim() === '';
  }

  document.addEventListener('keydown', function (e) {
    if (e.key !== '/' || !editingEl) return;
    if (fmtInput && document.activeElement === fmtInput) return;
    if (!slashContextEmpty()) return;
    e.preventDefault();
    var id = editingId;
    var rect = editingEl.getBoundingClientRect();
    var empty = (editingEl.textContent || '').trim() === '';
    exit(true); // commits current text + tells the parent editing ended
    parent.postMessage({ type: 'yarnnn-slash-open', blockId: id, empty: empty,
      rect: { left: rect.left, top: rect.top, bottom: rect.bottom, width: rect.width } }, '*');
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
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' || e.shiftKey || !editingEl) return;
    if (fmtInput && document.activeElement === fmtInput) return; // link input owns Enter
    if (inListBlock()) return; // native <li> creation is the right behavior
    if (!caretAtBlockEnd()) return; // mid-block Enter → native (split lands in commit 6)
    e.preventDefault();
    var afterId = editingId;
    exit(true); // commit the current block + tell the parent editing ended
    // The parent inserts a fresh empty prose block after afterId (always
    // present — the editing block), then commands edit into the new one. Enter
    // therefore NEVER hits the end-of-document append path.
    parent.postMessage({ type: 'yarnnn-enter-block', afterBlockId: afterId }, '*');
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
// block being edited (the format bar owns that space). The ⋮⋮ handle is where
// in-frame block drag lands later (ADR-453 D7.4 — a named follow-on).

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
    handle.textContent = '\\u22EE\\u22EE'; handle.title = 'Block options';
    handle.addEventListener('click', function (e) {
      e.preventDefault(); e.stopPropagation();
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
    bar.appendChild(plusBtn);
    bar.appendChild(handle);
    document.body.appendChild(bar);
  }

  function showFor(block) {
    build();
    curBlock = block;
    var rect = block.getBoundingClientRect();
    bar.style.display = 'flex';
    var w = bar.offsetWidth || 42;
    bar.style.left = Math.max(2, rect.left + window.scrollX - w - 4) + 'px';
    bar.style.top = (rect.top + window.scrollY + 1) + 'px';
  }
  function hide() {
    if (bar) bar.style.display = 'none';
    curBlock = null;
  }

  document.addEventListener('mousemove', function (e) {
    var t = e.target;
    if (t && t.closest && t.closest('.yarnnn-gutter')) {
      if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
      return;
    }
    var blk = t && t.closest ? t.closest('[data-block]') : null;
    if (blk) {
      if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
      var editingId = window.__yarnnnEditingId ? window.__yarnnnEditingId() : null;
      if (editingId != null && blk.getAttribute('data-block-id') === editingId) { hide(); return; }
      if (blk !== curBlock) showFor(blk);
      return;
    }
    // A grace delay bridges the gap between the block and the gutter.
    if (!hideTimer) hideTimer = setTimeout(function () { hideTimer = null; hide(); }, 300);
  });
  // Rects go stale on scroll — re-anchor (or hide if the block left the DOM).
  document.addEventListener('scroll', function () {
    if (curBlock && curBlock.isConnected) showFor(curBlock);
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
