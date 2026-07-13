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

const POINTER_SCRIPT = `
(function () {
  var SEL = ${JSON.stringify(POINTABLE)};
  var PAGE_SEL = 'section.slide, [data-arrange]';
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
    // ADR-446: while a block is being edited, clicks must place the caret, not
    // re-select — the edit runtime (if present) reports the editing block id.
    if (window.__yarnnnEditingId && window.__yarnnnEditingId() != null) return;
    var t = e.target;
    // The "+ Add here" button owns its click (its own handler posts).
    if (t && t.closest && t.closest('.yarnnn-add-here')) return;
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
      payload = {
        type: 'yarnnn-point',
        tag: el.tagName.toLowerCase(),
        text: text,
        dataRef: el.getAttribute('data-ref') || (blk && blk.getAttribute('data-ref')) || null,
        blockId: blk ? (blk.getAttribute('data-block-id') || null) : null,
        blockKind: blk ? (blk.getAttribute('data-block') || null) : null,
        slideIndex: slideIndexOf(el),
        pageIndex: pageIndexOf(el),
        slot: slotEl ? (slotEl.getAttribute('data-slot') || null) : null,
        arrange: arrangeOf(el),
      };
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
    } else if (d.type === 'yarnnn-zoom' && typeof d.scale === 'number') {
      // zoom scales layout + scrollable area (unlike transform) — the honest
      // "make it bigger/smaller on screen" the operator asked for.
      document.body.style.zoom = String(d.scale);
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
    if (el && el.querySelectorAll) {
      var innerNow = readSourceInner(el);
      if (innerNow) parent.postMessage({ type: 'yarnnn-edit', blockId: el.getAttribute('data-block-id'), newInner: innerNow }, '*');
      el.removeAttribute('contenteditable');
      var refs = el.querySelectorAll('[data-ref]');
      for (var i = 0; i < refs.length; i++) refs[i].removeAttribute('contenteditable');
    }
    if (notify) parent.postMessage({ type: 'yarnnn-edit-exited' }, '*');
  }

  function enter(blockId) {
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
    el.focus();
    el.addEventListener('blur', function () { exit(true); }, { once: true });
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

  // ADR-447 Phase 4: DOUBLE-CLICK to edit — the natural gesture (every editor
  // since 1984), replacing the toolbar chip. A dblclick on a [data-block]
  // enters edit mode HERE and tells the parent (yarnnn-edit-entered) so its
  // editingBlockId stays in sync (the parent then won't re-command on reload).
  document.addEventListener('dblclick', function (e) {
    var t = e.target;
    var blk = t && t.closest ? t.closest('[data-block]') : null;
    if (!blk) return;
    var id = blk.getAttribute('data-block-id');
    if (!id) return;
    e.preventDefault();
    enter(id);
    parent.postMessage({ type: 'yarnnn-edit-entered', blockId: id }, '*');
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
