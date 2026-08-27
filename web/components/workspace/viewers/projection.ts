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
import {
  labelForElement,
  labelForJS,
  STRUCTURAL_PAGE_SEL,
} from '@/components/authoring/structureLabels';
import {
  DECK_STAGE_FALLBACK_H,
  DECK_STAGE_FALLBACK_W,
} from '@/components/authoring/stageGeometry';
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
/** Split one CSV line, honouring "quoted, fields" and "" escapes.
 *
 *  A bare `split(',')` tore any field containing a comma into two cells — and a
 *  thousands-separated number ("1,240") is exactly that field, which is the one
 *  a CHART then reads as a value (ADR-538 D2). Shared by the table and chart
 *  projections so both read a row the same way. */
function splitCsvLine(line: string): string[] {
  const out: string[] = [];
  let cur = '';
  let quoted = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (quoted) {
      if (ch === '"') {
        if (line[i + 1] === '"') { cur += '"'; i++; } // "" → a literal quote
        else quoted = false;
      } else cur += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ',') { out.push(cur); cur = ''; }
    else cur += ch;
  }
  out.push(cur);
  return out.map((c) => c.trim());
}

function parseCsv(csv: string, maxRows: number): string[][] {
  return csv
    .trim()
    .split(/\r?\n/)
    .filter(Boolean)
    .slice(0, maxRows + 1)
    .map(splitCsvLine);
}

function csvToTableHtml(csv: string, maxRows = 50): string {
  const lines = parseCsv(csv, maxRows);
  if (!lines.length) return '<p>(empty table)</p>';
  const [head, ...rows] = lines;
  const th = head.map((c) => `<th>${escapeHtml(c)}</th>`).join('');
  const trs = rows
    .map((r) => `<tr>${r.map((c) => `<td>${escapeHtml(c)}</td>`).join('')}</tr>`)
    .join('');
  return `<table><thead><tr>${th}</tr></thead><tbody>${trs}</tbody></table>`;
}

/** ADR-538 D2 — a chart PROJECTED from cited data.
 *
 *  The sibling of `csvToTableHtml`, and deliberately built the same way: pure
 *  string→string, no engine, no library, no <script>. It emits static SVG +
 *  CSS, which is what survives the bare `sandbox=""` every reader-facing mount
 *  uses (ADR-538 §2 measured this).
 *
 *  Shape: first column = label, second = value. Extra columns are ignored
 *  rather than guessed at — a chart that silently picks a column is worse than
 *  one that reads the first two. A non-numeric or empty value counts as 0 so a
 *  ragged CSV degrades to a short bar, never to a crash.
 *
 *  NOT a rendering engine (the ADR-417 line): this projects the workspace's own
 *  cited substrate, exactly as the table projection has since ADR-440 D5.
 */
function csvToChartHtml(csv: string, kind: string, maxRows = 24): string {
  const lines = parseCsv(csv, maxRows);
  if (lines.length < 2) return '<p>(no chart data)</p>';
  const rows = lines.slice(1); // row 0 is the header
  const pts = rows
    .map((r) => ({ label: r[0] ?? '', value: Number((r[1] ?? '').replace(/[^0-9.\-]/g, '')) || 0 }))
    .filter((p) => p.label !== '');
  if (!pts.length) return '<p>(no chart data)</p>';
  const max = Math.max(...pts.map((p) => p.value), 0) || 1;
  const total = pts.reduce((s, p) => s + p.value, 0) || 1;
  const esc = (s: string) => escapeHtml(s);

  if (kind === 'donut') {
    // One <circle> per slice, drawn with stroke-dasharray around the ring —
    // no path math, no library. Slices accumulate an offset around 100 units.
    const R = 15.9155; // circumference ≈ 100, so a slice's dash IS its percent
    let acc = 0;
    const ring = pts
      .map((p, i) => {
        const pct = (p.value / total) * 100;
        const el =
          `<circle cx="21" cy="21" r="${R}" fill="none" stroke="var(--chart-${(i % 6) + 1}, currentColor)" ` +
          `stroke-width="6" stroke-dasharray="${pct.toFixed(2)} ${(100 - pct).toFixed(2)}" ` +
          `stroke-dashoffset="${(100 - acc + 25).toFixed(2)}" opacity="${(1 - (i % 6) * 0.13).toFixed(2)}"></circle>`;
        acc += pct;
        return el;
      })
      .join('');
    const legend = pts
      .map(
        (p, i) =>
          `<li><span class="swatch" style="opacity:${(1 - (i % 6) * 0.13).toFixed(2)}"></span>` +
          `${esc(p.label)} <b>${esc(String(p.value))}</b></li>`,
      )
      .join('');
    return (
      `<div class="yc yc-donut"><svg viewBox="0 0 42 42" role="img" aria-label="Donut chart">${ring}</svg>` +
      `<ul class="yc-legend">${legend}</ul></div>`
    );
  }

  // bar (the default) — a labelled row per point, width as a percentage.
  const bars = pts
    .map(
      (p) =>
        `<li><span class="yc-l">${esc(p.label)}</span>` +
        `<span class="yc-track"><span class="yc-bar" style="width:${((p.value / max) * 100).toFixed(1)}%"></span></span>` +
        `<span class="yc-v">${esc(String(p.value))}</span></li>`,
    )
    .join('');
  return `<div class="yc yc-bar-chart"><ul>${bars}</ul></div>`;
}

function markBroken(el: Element, ref: string): void {
  el.setAttribute('data-ref-broken', 'true');
  el.innerHTML = `<span style="display:inline-block;padding:0.4rem 0.6rem;border:1px dashed #c66;color:#a44;font-size:0.8rem;border-radius:4px;">citation broken: ${escapeHtml(ref)}</span>`;
}

const IMAGE_EXT = /\.(png|jpe?g|gif|webp|avif)$/i;

/** A binary's directly-renderable URL (ADR-427 D4 / ADR-510).
 *
 *  `GET /workspace/file` returns one of two shapes in `content_url`: the
 *  legacy stored `/api/documents/blob?storage_path=…` reference (needs an
 *  authenticated resolve to a signed URL — a browser element src can't send
 *  the Bearer header), or a MINTED absolute URL for a CAS-lane binary —
 *  already fetchable, used as-is. blobUrl() REJECTS absolute URLs by design
 *  (no storage_path param), so without this fork every CAS-lane citation
 *  silently fell to the catch and the asset never rendered. */
/** A citation's two reads, deduped for the length of one projection burst.
 *
 *  An artifact is projected by more than one consumer at a time — the canvas
 *  and the navigator rail both resolve the SAME citations, and the rail
 *  reprojects whenever the content changes. Uncached, a deck with M cited
 *  images issued 2M requests per edit, each image costing a file read plus a
 *  signed-URL round trip. The pixels are identical every time; only the
 *  request count grew.
 *
 *  Keyed by what is asked for, held briefly, and cleared on a timer rather
 *  than kept: a citation's target CAN change (a new revision of the cited
 *  file, an expiring signed URL), so this must be a burst dedup and never a
 *  session cache. The TTL is short enough that a member who replaces an image
 *  sees it on their next projection, and long enough that the two consumers
 *  of one edit share one request.
 *
 *  Failures are not cached — a transient error must not pin a broken citation
 *  for the whole window. */
const RESOLVE_TTL_MS = 3_000;
const resolveCache = new Map<string, { at: number; value: Promise<unknown> }>();

function burstDedup<T>(key: string, run: () => Promise<T>): Promise<T> {
  const now = Date.now();
  const hit = resolveCache.get(key);
  if (hit && now - hit.at < RESOLVE_TTL_MS) return hit.value as Promise<T>;
  const value = run().catch((err) => {
    resolveCache.delete(key);
    throw err;
  });
  resolveCache.set(key, { at: now, value });
  // Opportunistic sweep — the map holds one artifact's citations, not a
  // session's, so it never needs an eviction policy beyond expiry.
  if (resolveCache.size > 64) {
    resolveCache.forEach((v, k) => {
      if (now - v.at >= RESOLVE_TTL_MS) resolveCache.delete(k);
    });
  }
  return value;
}

async function servingUrl(contentUrl: string): Promise<string> {
  if (/^(https?:|data:|blob:)/i.test(contentUrl)) return contentUrl;
  const { url } = await burstDedup(`blob:${contentUrl}`, () =>
    api.documents.blobUrl(contentUrl),
  );
  return url;
}

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
          resolved.set(p, await servingUrl(file.content_url));
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

/** ADR-583 — a cited component fragment, made safe to inline: the same
 *  executable strip the full pass applies (script/iframe/object/embed, on*
 *  handlers, javascript: URLs), run over a detached carrier so the fragment's
 *  own <style> survives while nothing runnable does. */
function sanitizeFragmentHtml(html: string): string {
  const carrier = document.implementation.createHTMLDocument('');
  carrier.body.innerHTML = html;
  stripExecutable(carrier);
  return carrier.body.innerHTML;
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
    const file = await burstDedup(`file:${path}`, () => api.workspace.getFile(path));
    const isImg = el.tagName === 'IMG';

    if (isImg && path.toLowerCase().endsWith('.svg') && file.content) {
      (el as HTMLImageElement).src =
        `data:image/svg+xml;charset=utf-8,${encodeURIComponent(file.content)}`;
      return;
    }
    if (isImg && file.content_url) {
      (el as HTMLImageElement).src = await servingUrl(file.content_url);
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
        const url = await servingUrl(file.content_url);
        (el as HTMLElement).style.backgroundImage = `url("${url}")`;
      }
      return;
    }
    // ADR-583 — a cited COMPONENT: a workspace library fragment
    // (`*.component.html`), inlined whole. Reference, never copy — editing
    // the file updates every citing artifact. Executables are stripped before
    // the innerHTML (defense in depth: the canvas sandbox never runs script,
    // and the projection must not be the door either).
    if (kind === 'component') {
      if (file.content != null) {
        el.innerHTML = sanitizeFragmentHtml(file.content);
        return;
      }
      markBroken(el, ref);
      return;
    }
    // ADR-538 D2 — a chart cites its DATA. Checked BEFORE the table branch:
    // both read a .csv, and the chart declares itself by ref-kind, so a bare
    // `.csv` still falls through to a table (the unchanged default).
    if (kind === 'chart') {
      el.innerHTML = csvToChartHtml(
        file.content || '',
        el.closest('[data-chart]')?.getAttribute('data-chart') || 'bar',
      );
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
          } else if (kind === 'chart') {
            // ADR-538 D2 — the pinned fallback draws the chart too. Without
            // this branch a dangling chart citation fell to the <pre> path and
            // dumped raw CSV into the artifact.
            el.innerHTML = csvToChartHtml(
              rev.content,
              el.closest('[data-chart]')?.getAttribute('data-chart') || 'bar',
            );
          } else if (kind === 'component') {
            // ADR-583 — the pinned fallback inlines the component too (the
            // same lesson: a dangling citation must not dump raw source).
            el.innerHTML = sanitizeFragmentHtml(rev.content);
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
// ADR-525 D1: exported so the FE's tier fallback reads the SAME list the
// runtime derives from, rather than re-enumerating it (a second copy would
// drift the moment a kind is added — the re-derivation this ADR exists to end).
export const TEXT_BLOCK_KINDS = [
  'prose',
  'callout',
  'quote',
  // ADR-536 D1 — the two ordinary list kinds are TEXT: prose lives inside the
  // items, so a click enters edit-at-caret exactly as it does on a checklist
  // (already here, and structurally identical). Omitting them would make a
  // list select-only — a container the member can point at but not type in.
  'list',
  'numbered',
  'checklist',
  'toggle',
  'heading',
] as const;
const TEXT_KINDS_JS = JSON.stringify(TEXT_BLOCK_KINDS);

// ADR-539 D3 — the heading rung set, the FE's ONE static copy of the kernel's
// declaration (studio.py HEADING_RUNGS), pinned to it by the parity gate.
// React-land consumers prefer the SERVED `heading_rungs` and fall back to
// this; the runtime template and the normalize seam interpolate it directly
// because they are assembled at module scope, before any fetch exists.
export const HEADING_RUNGS = [1, 2, 3] as const;
/** The deepest spoken rung — what an out-of-rung heading clamps TO (D4). */
export const DEEPEST_RUNG = Math.max(...HEADING_RUNGS);

/** ADR-546 D1 — THE RUNG: depth on a document, one concept, two spellings.
 *
 *  A heading rung (`h1/h2/h3`) and a nesting step (a list item's depth, a prose
 *  block's step in from the measure) are the SAME statement — "this is
 *  subordinate to that" — so they share one declared set. The kernel's
 *  `FLOW_RUNGS` is the authority; this is the FE's static mirror, pinned by the
 *  ADR-539 parity gate exactly as `HEADING_RUNGS` is.
 *
 *  At the 2026-08-10 audit depth was declared THREE times (this set, the
 *  `indent` token's values, the kernel's `ul ul ul` CSS) with wildly different
 *  readership — six consumers, one, and NONE — while agreeing by luck on the
 *  number 3. One declaration is the fix; that the third had no reader at all is
 *  why Tab could author a hierarchy nothing could name (ADR-546 §1.2).
 *
 *  Paged depth is NOT this: on a slide depth is CONTAINMENT (which Area holds
 *  the block — ADR-544 D1/D2). A rung is a flow fact. */
export const FLOW_RUNGS = HEADING_RUNGS;
/** The deepest rung the medium speaks — what over-deep nesting clamps TO. */
export const DEEPEST_FLOW_RUNG = Math.max(...FLOW_RUNGS);
/** The tags OUTSIDE the rung set — what the intake seams clamp (D4). */
export const OUT_OF_RUNG_TAGS = [1, 2, 3, 4, 5, 6]
  .filter((r) => !(HEADING_RUNGS as readonly number[]).includes(r))
  .map((r) => `H${r}`);
const HEADING_ANCHOR_SEL_JS = JSON.stringify(
  HEADING_RUNGS.map((r) => `h${r}[data-block-id]`).join(', '),
);
const OUT_OF_RUNG_TAGS_JS = JSON.stringify(OUT_OF_RUNG_TAGS);
/** ADR-546 D1 — the rung set + its floor, for the runtimes (see EDIT_SCRIPT). */
const FLOW_RUNGS_JS = JSON.stringify([...FLOW_RUNGS]);
const DEEPEST_FLOW_RUNG_JS = JSON.stringify(DEEPEST_FLOW_RUNG);
const DEEPEST_RUNG_TAG_JS = JSON.stringify(`h${DEEPEST_RUNG}`);

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
body:has([contenteditable="true"]) div[data-block-id]:not([data-block]):hover { outline: none; }
body:has([contenteditable="true"]) div[data-block-id]:not([data-block]):hover::after { content: none; }
/* Selection is NEUTRAL (ADR-462 D5). A saturated outline reads as the app
   asserting itself over the member's page — PowerPoint/Keynote/Figma all draw
   selection as a thin neutral rule, and reserve colour for what is NOT your
   content. The accent survives where it means something the page cannot say
   for itself: the editing state (you are typing into this), and the transient
   gesture chrome (drop-line, divider). */
.yarnnn-pointed {
  outline: 1px solid rgba(60,58,54,0.5) !important; outline-offset: 2px;
}
/* A GROUP member (2026-07-24) wears the SAME neutral rule as the primary —
   the set reads as one selection, which is the whole point of grouping. It is
   a class, never markup: ungroup is deselection, and nothing here is ever
   serialized (ADR-484 — runtime chrome is stripped at the one serializer). */
.yarnnn-grouped {
  outline: 1px solid rgba(60,58,54,0.5) !important; outline-offset: 2px;
}
/* ADR-511 D3: structural CONTAINERS are selection subjects — a real DOM
   element (a column, a columns row, a slot-div) carrying identity but no
   vocabulary. The hover cue + name label light only when the pointer is over
   the container's OWN surface (padding/gap), not over a child block — the cue
   must agree with what the click would select (the grain rule, kept). The
   label speaks operator words via the projection's data-yarnnn-label stamp
   (structureLabels.ts — the file never says "div", the chrome never does
   either). The old slot-only chrome + its inert-marking pass are DELETED:
   what the frame names, the member can select. */
div[data-block-id]:not([data-block]) { position: relative; }
div[data-block-id]:not([data-block]):hover:not(:has([data-block]:hover)):not(:has(div[data-block-id]:not([data-block]):hover)) {
  outline: 1px dashed rgba(16,185,129,0.55); outline-offset: 2px;
}
div[data-block-id]:not([data-block]):hover:not(:has([data-block]:hover)):not(:has(div[data-block-id]:not([data-block]):hover))::after {
  content: attr(data-yarnnn-label); position: absolute; top: -1rem; left: 0;
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
// ADR-485 D6 — the box is READ, never restated. This declared its own `992`
// and pinned the slide to it with `!important`, so the canvas asserted a
// geometry the DOCUMENT already declares: a deck authored at any other stage
// size (IMAGES seeds its own W×H; ADR-472 D3 made dimensions first-class)
// rendered at 992 in the editor while `stageGeometry.readStageSize` read the
// true value for the fit math — the two disagreed by construction, which is the
// very split `stageGeometry.ts` was created to end. The navigator had already
// converged on the right shape (`PagedNavigator.tsx`): pin to the SAME var
// chain the document uses, with the shared fallback for a deck that predates
// the kernel retrofit. This is now the third reader of one constant, not the
// third copy of one number.

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
  width: var(--stage-w, ${DECK_STAGE_FALLBACK_W}px) !important;
  height: var(--stage-h, ${DECK_STAGE_FALLBACK_H}px) !important;
  aspect-ratio: auto !important;
  flex: 0 0 auto;
}
/* ADR-520 D1 — the STAGE VIEW: a deck shows ONE slide (the PowerPoint/Figma
   norm; the continuous scroll is a document idiom the staged medium never
   asked for). Pure VIEW state — a class regime the runtime toggles, never
   serialized (the zoom rule). The sequence lives in the navigator filmstrip;
   the fixed nav buttons page the stage in-canvas. */
body.yarnnn-stage section.slide:not(.yarnnn-current) { display: none !important; }
.yarnnn-stagenav {
  position: fixed; bottom: 14px; left: 50%; transform: translateX(-50%);
  display: none; align-items: center; gap: 6px; z-index: 2147483646;
  font: 500 0.72rem system-ui, sans-serif; color: #6b7280;
  background: rgba(255,255,255,0.92); border: 1px solid rgba(0,0,0,0.08);
  border-radius: 999px; padding: 3px 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}
body.yarnnn-stage .yarnnn-stagenav { display: flex; }
.yarnnn-stagenav button {
  border: 0; background: transparent; cursor: pointer; color: inherit;
  font: inherit; font-size: 0.9rem; line-height: 1; padding: 2px 6px;
  border-radius: 999px;
}
.yarnnn-stagenav button:hover { background: rgba(0,0,0,0.06); color: #111; }
.yarnnn-stagenav button:disabled { opacity: 0.35; cursor: default; }
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
  var PAGE_SEL = '${STRUCTURAL_PAGE_SEL}'; // ADR-511 Phase 2 — the one structural page selector
  // ADR-511 D3: a structural CONTAINER is a real element carrying identity
  // but no vocabulary — the selection rung between block and page.
  var CONTAINER_SEL = 'div[data-block-id]:not([data-block])';
  var TEXT_KINDS = ${TEXT_KINDS_JS};
  ${labelForJS('labelFor')}
  var cur = null;

  // ADR-525 D1 — the selection's TIER, declared by the one party that can see
  // both the DOM and the medium. Every consumer READS this; none re-derives it.
  //
  //   text      — prose on a continuous surface. The caret speaks for it, so it
  //               gets no box, no unit verbs, no geometry.
  //   object    — a figure/table/chart/divider anywhere, AND every block on a
  //               paged medium (ADR-480 D1: there the block IS an enclosure).
  //               Nothing else can speak for it, so it earns the box.
  //   structure — a container or a page: its own frame speaks for it.
  //
  // This mints NO new judgment — it is the rule the cue already applied at five
  // scattered sites (ADR-484 + ADR-521 D6), moved to the payload so the pane,
  // the menu and the keyboard cannot disagree about one block.
  function tierOf(el) {
    if (!el || !el.getAttribute) return null;
    var kind = el.getAttribute('data-block');
    if (!kind) return 'structure';
    var flow = window.__yarnnnFlowMode ? window.__yarnnnFlowMode() : false;
    return flow && TEXT_KINDS.indexOf(kind) !== -1 ? 'text' : 'object';
  }

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
  // ── ADR-546 D5 (F2): a medium never NAMES a grain its projection deletes ──
  //
  // slot (ADR-544's Area) and arrange (its Layout) are PAGED grains. Flow's
  // own projection lifts [data-arrange] and [data-area], [data-slot] out of
  // the document before the runtime ever loads (resolveArtifactHtml) — yet every
  // payload builder computed both by closest() and shipped them as null.
  //
  // Worse after ADR-544: the slot key reads data-area FIRST, so the Area
  // grain was being named in a DOCUMENT's selection payload — the exact drift
  // ADR-544 §2 exists to prevent, arriving through the one file that knows the
  // mode.
  //
  // Gated HERE, at the two derivations, rather than at the eight call sites: one
  // guard the payloads all inherit (rule 7 — move the derivation, never add a
  // ninth). On flow both answer null structurally, not incidentally.
  function isFlowDoc() {
    return document.documentElement.getAttribute('data-yarnnn-mode') === 'flow';
  }
  function arrangeOf(el) {
    if (isFlowDoc()) return null;
    var page = el && el.closest ? el.closest('[data-arrange]') : null;
    return page ? (page.getAttribute('data-arrange') || null) : null;
  }
  /** The Area an element sits in — paged only, by the same rule as arrangeOf.
   *  data-slot rides along for a deck authored before the ADR-544 heal. */
  function regionOf(el) {
    if (isFlowDoc()) return null;
    var r = el && el.closest ? el.closest('[data-area], [data-slot]') : null;
    return r ? (r.getAttribute('data-area') || r.getAttribute('data-slot') || null) : null;
  }
  // ADR-522 D4 — the nearest heading at or above this point, in document
  // order. Docs (flow) has NO section unit: headings are flat siblings with no
  // containing element and no heading-to-body nesting, so "this section" can
  // only honestly mean "from this heading to the next". We report the heading
  // BLOCK — the thing that actually exists — and never claim a container the
  // substrate cannot back. Real <section> wrappers are deferred to their own
  // ADR (ADR-522 §5).
  function headingAboveOf(el) {
    if (!el || !el.closest) return null;
    var blk = el.closest('[data-block]');
    if (!blk) return null;
    // The block itself is the heading — no walk needed.
    if (/^h[1-6]$/i.test(blk.tagName || '')) return blk;
    // ADR-539 D3 — the anchor set is BUILT from the declared rungs. This read
    // h1/h2 only until 2026-08-09, so an h3 heading (offered by the ramp,
    // shown in the outline) was invisible to the crumb and the AI focus line.
    var heads = document.querySelectorAll(${HEADING_ANCHOR_SEL_JS});
    if (!heads.length) return null;
    var best = null;
    for (var i = 0; i < heads.length; i++) {
      // DOCUMENT_POSITION_PRECEDING (2) — the heading comes before the block.
      var rel = blk.compareDocumentPosition(heads[i]);
      if (rel & 2) best = heads[i];
      else break; // past the block in document order; the last hit is nearest.
    }
    return best;
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

    // ── GROUP click (2026-07-24) — ⇧ adds to the selection ────────────────
    // Intercepted BEFORE the ladder: a modifier-click is not a navigation
    // gesture, so it must never place a caret, enter a block, or re-run the
    // grain ladder. Staged frames only (a deck slide / canvas artboard) —
    // moving a set together needs a coordinate space to move it IN, which is
    // ADR-461 D4's rule (a slide has a frame, a page has a viewport) and the
    // same reason x/y are block-staged. On flow, shift-click stays the
    // browser's range-selection and we do not touch it.
    //
    // ADR-519 D4 (2026-08-06) — ⌘ SPLIT OUT of this branch. It used to read
    // "shift || meta || ctrl", three modifiers doing one job; only ⇧ was ever
    // argued for (the comment above justifies shift alone) and ⌘ was swept in
    // incidentally, never chosen. Every reference tool separates them — ⇧ adds
    // to the selection (Figma, Keynote, PowerPoint, Illustrator, Finder,
    // universally) and ⌘ deep-selects (Figma, Illustrator, Sketch). The split
    // therefore costs no learned behaviour and imports the convention whole.
    if (e.shiftKey) {
      var gblk = el && el.closest ? el.closest('[data-block]') : null;
      var gstaged = gblk && gblk.closest ? !!gblk.closest('.slide') : false;
      // ADR-544 D5.1 — THE SET IS SIBLING-ONLY: every member shares one Area.
      // Refused at FORMATION, not merely withdrawn from afterwards. A set
      // spanning two Areas has no shared parent to align against, so
      // align/distribute would have to invent a frame — free placement
      // returning through the selection door (D3's whole point). Enforcing it
      // here means the illegal set never exists, rather than existing and
      // being described by a pane that has nothing true to say about it.
      //
      // The first ⇧-click seeds the set, so there is nothing to compare it to;
      // from the second on, the candidate must share the primary's Area.
      // data-slot rides along for a document authored before the heal.
      var gArea = gblk && gblk.closest ? gblk.closest('[data-area], [data-slot]') : null;
      var curArea = cur && cur.closest ? cur.closest('[data-area], [data-slot]') : null;
      if (cur && gblk && gArea !== curArea) {
        // Say why. A gesture that silently does nothing is the affordance
        // ADR-544 keeps finding; the parent owns the one notice (ADR-541 D4).
        parent.postMessage({ type: 'yarnnn-refused', reason: 'cross-area-set' }, '*');
        return;
      }
      if (gblk && gstaged) {
        // __yarnnnSelect now posts an empty set when it clears one (below), so
        // seeding through it can emit twice in one gesture. Harmless — the
        // authoritative set is posted immediately after — but the second
        // message is the one that must win, so keep them in this order and
        // never reorder them.
        if (!cur) { window.__yarnnnSelect(gblk); }
        else { toggleGroup(gblk); }
        parent.postMessage({
          type: 'yarnnn-group',
          blockIds: (window.__yarnnnGroup() || []).map(function (n) {
            return n.getAttribute('data-block-id');
          }).filter(Boolean),
        }, '*');
        return;
      }
    }

    // ── DEEP SELECT (ADR-519 D4) — ⌘/ctrl reaches the container ───────────
    // §2.4's gap: the ladder's container rung lives in the pointable-MISS
    // branch below, so a container fully tiled by its children has no
    // clickable "thing" and canon's "down is clicking the thing" (ADR-511 D3)
    // fails for exactly it. Breadcrumb / Esc-walk / pane path were the only
    // routes in. ⌘-click is the conventional modifier for this, and it does
    // NOT disturb the default ladder — it is a separate gesture, own branch.
    //
    // ctrl follows ⌘, never ⇧: it is the Windows/Linux stand-in for the same
    // intent, and splitting them would give one gesture two meanings by OS.
    //
    // The target is the INNERMOST container enclosing the hit — closest()
    // walks outward from the click, so its first match IS the innermost. A
    // page is not a deep-select target: the ladder already reaches it, and
    // ADR-519 D6 keeps pages out of the container grain.
    if (e.metaKey || e.ctrlKey) {
      var dcont = t && t.closest ? t.closest(CONTAINER_SEL) : null;
      if (dcont) {
        var dslot = dcont.closest ? dcont.closest('[data-area], [data-slot]') : null;
        // The SAME payload shape the miss-branch container rung emits — one
        // derivation, two entrances (the label-map precedent). A second shape
        // here is how the pane starts reading two answers for one grain.
        window.__yarnnnSelect(dcont);
        parent.postMessage({
          type: 'yarnnn-point',
          tag: dcont.tagName.toLowerCase(),
          text: '',
          dataRef: null,
          blockId: dcont.getAttribute('data-block-id') || null,
          blockKind: null,
          label: labelFor(dcont),
          slideIndex: slideIndexOf(dcont),
          pageIndex: pageIndexOf(dcont),
          slot: regionOf(dcont),
          arrange: arrangeOf(dcont),
          tier: tierOf(dcont), // structure — a container always earns its frame
        }, '*');
        return;
      }
    }

    // ADR-453 D5: the click-grain ladder — block (a pointable inside one) →
    // slot (a slot's empty padding) → page (the page margin) → clear.
    var mark = null;
    var payload = null;
    if (el) {
      // ADR-443 D6: the selection UNIT is the block when one encloses the hit.
      var blk = el.closest ? el.closest('[data-block]') : null;
      mark = blk || el;
      // ADR-609 D4 — mark the clip at SOURCE. This 120-char bound and the
      // server's 80-char one used to compound: a 90-char block arrived
      // already silently shortened, then got the honest "…" applied to the
      // ALREADY-shortened string, so the marker described the second cut and
      // hid the first. The block's real extent travels as its id (the
      // anchor); this text only has to name it, and say when it is partial.
      var rawText = (el.getAttribute('alt') || el.textContent || '')
        .replace(/\\s+/g, ' ').trim();
      var text = rawText.length > 120 ? rawText.slice(0, 120) + '…' : rawText;
      var blkKind = blk ? (blk.getAttribute('data-block') || null) : null;
      payload = {
        type: 'yarnnn-point',
        tag: el.tagName.toLowerCase(),
        text: text,
        dataRef: el.getAttribute('data-ref') || (blk && blk.getAttribute('data-ref')) || null,
        blockId: blk ? (blk.getAttribute('data-block-id') || null) : null,
        blockKind: blkKind,
        label: labelFor(blk || el),
        slideIndex: slideIndexOf(el),
        pageIndex: pageIndexOf(el),
        slot: regionOf(el),
        arrange: arrangeOf(el),
        // ADR-525 D1 — the tier travels WITH the selection, so the pane, the
        // menu and the keyboard read one answer instead of deriving three.
        tier: tierOf(blk || el),
      };
      // ADR-522 D4: the enclosing "section" on flow — the nearest heading at
      // or above this block. Null on a paged medium (a slide is the unit
      // there) and null in a document with no headings yet.
      var headEl = headingAboveOf(el);
      payload.headingId = headEl ? (headEl.getAttribute('data-block-id') || null) : null;
      payload.headingText = headEl
        ? (headEl.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 80)
        : null;
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
        // ADR-525 D2: the cue decision moved to __yarnnnSelect (the one place
        // that may draw a box). ADR-484's reasoning is unchanged and now lives
        // there: on a continuous writing surface, clicking into prose places a
        // caret and the caret IS the feedback; a rule around the paragraph
        // re-asserts the enclosure ADR-480 dissolved. An OBJECT keeps the cue —
        // nothing else can speak for it. This branch simply selects and posts.
        if (blk) window.__yarnnnSelect(blk);
        else { if (cur) cur.classList.remove('yarnnn-pointed'); cur = null; }
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
      // ADR-511 D3: the structural rung — a click on a container's own
      // surface (padding/gap, not a child block) selects the CONTAINER: a
      // real element with identity, so every id-addressed op works on it.
      // Then the page (which IS an object: tokens, duplicate, delete,
      // re-arrange), then clear. The inert-slot skip is deleted with the
      // inert pass itself — what the frame names, the member can select.
      var cont = t && t.closest ? t.closest(CONTAINER_SEL) : null;
      var page = t && t.closest ? t.closest(PAGE_SEL) : null;
      var hit = cont || page;
      if (hit) {
        mark = hit;
        var hitSlot = hit.closest ? hit.closest('[data-area], [data-slot]') : null;
        payload = {
          type: 'yarnnn-point',
          tag: hit.tagName.toLowerCase(),
          text: '',
          dataRef: null,
          blockId: cont ? (cont.getAttribute('data-block-id') || null) : null,
          blockKind: null,
          label: labelFor(hit),
          slideIndex: slideIndexOf(hit),
          pageIndex: pageIndexOf(hit),
          slot: regionOf(hit),
          arrange: arrangeOf(hit),
          tier: tierOf(hit), // ADR-525 D1 — a container/page is 'structure'.
        };
      }
    }

    if (!payload) {
      if (cur) { cur.classList.remove('yarnnn-pointed'); cur = null; }
      parent.postMessage({ type: 'yarnnn-point-clear' }, '*');
      return;
    }
    // ADR-525 D2 — through the chokepoint. This branch only ever marks a
    // container or page (structure tier, which always earns its frame), so the
    // guard is a no-op here; it routes through anyway so that ONE function owns
    // the cue and the completeness assertion can be absolute.
    window.__yarnnnSelect(mark);
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
    if (t && t.closest && (t.closest('.yarnnn-fmt')
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
    // ADR-511 D3: the structural rung mirrors the click ladder — right-click
    // on a container's own surface selects the container, then menus.
    var ctxCont = !el && t && t.closest ? t.closest(CONTAINER_SEL) : null;
    var mark = blk || el || ctxCont;
    if (mark) {
      // ADR-482 D9 (its rule, now enforced at ADR-525 D2's chokepoint): on FLOW
      // prose is never boxed — not by left-click and not by right-click. An
      // object still gets the cue in both grains: there is no caret to stand in
      // for it. The local guard is gone because __yarnnnSelect owns it.
      window.__yarnnnSelect(mark);
    } else if (cur) {
      cur.classList.remove('yarnnn-pointed');
      cur = null;
    }
    parent.postMessage({
      type: 'yarnnn-context-menu',
      x: e.clientX, y: e.clientY,
      tag: el ? el.tagName.toLowerCase() : null,
      text: mark ? (mark.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 120) : '',
      dataRef: (el && el.getAttribute('data-ref')) || (blk && blk.getAttribute('data-ref')) || null,
      blockId: blk ? (blk.getAttribute('data-block-id') || null)
        : ctxCont ? (ctxCont.getAttribute('data-block-id') || null) : null,
      blockKind: blk ? (blk.getAttribute('data-block') || null) : null,
      label: mark ? labelFor(mark) : null,
      // ADR-525 D1/D5 — the same tier the point payload carries, so the menu
      // and the pane cannot answer one block two ways.
      tier: mark ? tierOf(mark) : null,
      slideIndex: el ? slideIndexOf(el) : (ctxCont ? slideIndexOf(ctxCont) : null),
      pageIndex: el ? pageIndexOf(el) : (ctxCont ? pageIndexOf(ctxCont) : null),
      slot: regionOf(el),
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

  // ── Escape reaches the PARENT's chrome (the same bridge shape as the press) ──
  // A right-click opens the block menu in the PARENT document, but leaves focus
  // inside this frame — so the parent's own keydown listener never hears the
  // member's Escape, and the menu could only be dismissed with the mouse. Every
  // conventional context menu closes on Escape.
  //
  // Bridged rather than handled here for the same reason the canvas-press is:
  // the chrome lives in the parent, so the parent must decide what closes.
  // This runtime is injected on BOTH modes, which is what makes the fix
  // mode-independent — EDIT_SCRIPT's Escape handler (caret to block-select) is
  // gated on a live editingEl, null on flow by design (ADR-480 D1) and null on
  // paged after a plain right-click, so neither mode had a route.
  //
  // Not preventDefault'd and not stopped: this only ANNOUNCES the key. The edit
  // runtime's own Escape still lifts the caret to block-select where it applies,
  // and the palette's own handler still closes it first — a bridge, not a claim.
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    parent.postMessage({ type: 'yarnnn-canvas-escape' }, '*');
    // ── ADR-511 D3: Esc walks UP the real ancestor chain ──────────────────
    // block -> container -> ... -> page -> clear (the Figma/Framer hierarchy
    // walk; down is just clicking the thing). Generalizes the edit runtime's
    // existing Esc (caret -> block-select), which still runs first: while a
    // per-block session or a live caret owns Esc, the walk yields.
    if (window.__yarnnnEditingId && window.__yarnnnEditingId() != null) return;
    if (window.__yarnnnCaretLive && window.__yarnnnCaretLive()) return;
    if (!cur) return;
    var up = null;
    if (cur.parentElement && cur.parentElement.closest) {
      up = cur.parentElement.closest(CONTAINER_SEL);
      if (!up && !cur.matches(PAGE_SEL)) up = cur.parentElement.closest(PAGE_SEL);
    }
    if (!up) {
      if (cur) cur.classList.remove('yarnnn-pointed');
      // ADR-519 D4.1 — this branch clears to NOTHING without passing through
      // __yarnnnSelect, so it must clear the set itself or Esc-to-nothing
      // would leave the parent holding one.
      if (group.length) {
        clearGroup();
        parent.postMessage({ type: 'yarnnn-group', blockIds: [] }, '*');
      }
      cur = null;
      parent.postMessage({ type: 'yarnnn-point-clear' }, '*');
      return;
    }
    // ADR-525 D2 — through the chokepoint (this site boxed 'up' directly and so
    // inherited no guard; the Esc-walk climbs to a container/page, which earns
    // the frame, but the cue decision belongs to one function regardless).
    window.__yarnnnSelect(up);
    var upSlot = up.closest ? up.closest('[data-area], [data-slot]') : null;
    var upIsCont = up.matches ? up.matches(CONTAINER_SEL) : false;
    parent.postMessage({
      type: 'yarnnn-point',
      tag: up.tagName.toLowerCase(),
      text: '',
      dataRef: null,
      blockId: upIsCont ? (up.getAttribute('data-block-id') || null) : null,
      blockKind: null,
      label: labelFor(up),
      slideIndex: slideIndexOf(up),
      pageIndex: pageIndexOf(up),
      slot: regionOf(up),
      arrange: arrangeOf(up),
      tier: tierOf(up), // ADR-525 D1
    }, '*');
  }, true);

  // ── Undo / Redo (⌘Z / ⌘⇧Z) ───────────────────────────────────────────────
  //
  // RE-HOMED here 2026-07-31 from the paged-only OBJECT_SCRIPT, where it meant
  // ⌘Z did not exist at all on a document — no producer in the frame, and the
  // parent cannot hear a key pressed inside an opaque-origin iframe. Every
  // structural op (a slash insert, a delete, a turn-into) pushed a snapshot the
  // member had no way to pop. This runtime is injected on BOTH modes, which is
  // what makes undo mode-independent.
  //
  // Undo is NOT scoped to a selected block — it reverses the LAST op whether or
  // not anything is selected, so it is a top-level listener rather than an
  // extension of the selected-block handler (which returns early on no
  // selection). The parent owns the snapshot stack (one HTML string per whole
  // op); the runtime only hears the key and asks.
  //
  // THE GUARD IS THE CARET QUESTION, NOT THE SESSION QUESTION. When a text
  // caret is live, undo belongs to the platform — the browser's native
  // contentEditable stack rewinds typing keystroke by keystroke, better than a
  // whole-op stack can. It must ask __yarnnnCaretLive: the old code asked
  // __yarnnnEditingId, which is null on FLOW while a caret is very much live
  // (ADR-480 D1), so on flow it would have stolen ⌘Z mid-sentence and rewound
  // the member's paragraph to a structural snapshot. That is the exact trap
  // ADR-482 D2 named for the text keys, and re-homing this without switching
  // the guard would have walked straight into it.
  document.addEventListener('keydown', function (e) {
    if (!(e.metaKey || e.ctrlKey)) return;
    if ((e.key || '').toLowerCase() !== 'z') return;
    if (window.__yarnnnCaretLive && window.__yarnnnCaretLive()) return;
    var t = e.target;
    // Injected chrome (the format bar) is never an undo subject.
    if (t && t.closest && t.closest('.yarnnn-fmt')) return;
    e.preventDefault();
    parent.postMessage({ type: e.shiftKey ? 'yarnnn-redo' : 'yarnnn-undo' }, '*');
  });

  // ADR-458: the hover gutter selects THROUGH this runtime's own selection
  // state (one selection, not two) — exposed like __yarnnnEditingId.
  //
  // ADR-525 D2 — this is the ONE place in the system that may draw a selection
  // box, and it cannot draw one on prose. ADR-484 put its guard at the two
  // CLICK sites instead of here, so every other selection route inherited
  // nothing: the parent re-command (ADR-516 D5, which re-opened the defect on
  // Docs one day after it shipped for Studio), the backspace-merge, the
  // Esc-from-edit and the Esc-walk all boxed prose. A guard at the chokepoint
  // is inherited by the NEXT route for free — the failure this ADR closes.
  //
  // The block stays SELECTED on flow (ADR-480: still addressable — the pane
  // scopes to it, Typography and Turn into act on it, ADR-522's focus reads
  // it). Only the enclosure CUE is withheld, because the caret is already
  // saying where the member is.
  window.__yarnnnSelect = function (el) {
    if (!el || !el.classList) return;
    if (cur) cur.classList.remove('yarnnn-pointed');
    // ADR-519 D4.1 — the set dies here, and the PARENT must hear it. This
    // function already cleared the runtime's own group; what it did not do was
    // say so, and "yarnnn-group" is posted only from the ⇧ branch. So a plain
    // click after a set left the parent holding stale ids: the pane kept
    // reading "2 objects selected", every single-subject section stayed
    // withdrawn, and there was NO gesture that could get back — the member was
    // trapped in a set of one. Clearing at the chokepoint means every
    // selection route (click, Esc-walk, breadcrumb, parent re-command,
    // deep-select) is fixed by one line, which is the ADR-525 D2 lesson:
    // a guard at the chokepoint is inherited by the next route for free.
    if (group.length) {
      clearGroup();
      parent.postMessage({ type: 'yarnnn-group', blockIds: [] }, '*');
    }
    cur = el;
    if (tierOf(el) !== 'text') el.classList.add('yarnnn-pointed');
  };
  // ── The GROUP (2026-07-24) — a transient multi-selection, never markup ───
  // Shift/⌘-click adds a block to the selection; the set moves together and
  // ungroup is simply deselection. It rides ALONGSIDE cur rather than
  // replacing it: cur stays the primary (the block the box, handles and
  // Properties scope follow), and group is the additional members. That
  // keeps the one-selection rule intact — every existing reader of
  // __yarnnnSelected() still gets exactly one element, and only the move
  // gesture consults the group.
  var group = [];
  function clearGroup() {
    for (var i = 0; i < group.length; i++) group[i].classList.remove('yarnnn-grouped');
    group = [];
  }
  function inGroup(el) { return group.indexOf(el) >= 0; }
  function toggleGroup(el) {
    if (!el || !el.classList) return;
    if (el === cur) return; // the primary is already in the set
    var i = group.indexOf(el);
    if (i >= 0) { group.splice(i, 1); el.classList.remove('yarnnn-grouped'); }
    else { group.push(el); el.classList.add('yarnnn-grouped'); }
  }
  // The full set the move gesture acts on: the primary FIRST, then the others.
  window.__yarnnnGroup = function () { return cur ? [cur].concat(group) : group.slice(); };
  window.__yarnnnClearGroup = clearGroup;
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
  // ── ADR-520 D1: the STAGE VIEW's runtime half ─────────────────────────
  // The parent enables the mode (yarnnn-view-mode, deck only); the runtime
  // owns WHICH slide is shown — transient view state (the zoom rule), fed
  // back through yarnnn-scroll-pos's existing slide field so a srcdoc reload
  // restores the same stage. Every slide-addressed command below becomes
  // stage-aware: "scroll to" MEANS "show" when the stage is on.
  var stageNav = null;
  function stageMode() { return document.body.classList.contains('yarnnn-stage'); }
  function stageCurrent() {
    var s = document.querySelectorAll('section.slide');
    for (var i = 0; i < s.length; i++) {
      if (s[i].classList.contains('yarnnn-current')) return i;
    }
    return s.length ? 0 : -1;
  }
  function stageShow(index) {
    var s = document.querySelectorAll('section.slide');
    if (!s.length) return;
    var i = Math.max(0, Math.min(s.length - 1, index));
    for (var k = 0; k < s.length; k++) s[k].classList.toggle('yarnnn-current', k === i);
    window.scrollTo(0, 0);
    if (stageNav) {
      stageNav.querySelector('[data-dir="-1"]').disabled = i === 0;
      stageNav.querySelector('[data-dir="1"]').disabled = i === s.length - 1;
      stageNav.querySelector('.yarnnn-stagenav-count').textContent =
        (i + 1) + ' / ' + s.length;
    }
    reportScroll();
  }
  function stageShowFor(el) {
    // A cross-slide reach (breadcrumb, pane, select re-command) switches the
    // stage to the target's slide first — a hidden target is unreachable.
    if (!stageMode() || !el || !el.closest) return;
    var slide = el.closest('section.slide');
    if (!slide || slide.classList.contains('yarnnn-current')) return;
    var s = document.querySelectorAll('section.slide');
    for (var i = 0; i < s.length; i++) {
      if (s[i] === slide) { stageShow(i); return; }
    }
  }
  function ensureStageNav() {
    if (stageNav) return;
    stageNav = document.createElement('div');
    stageNav.className = 'yarnnn-stagenav';
    var prev = document.createElement('button');
    prev.type = 'button'; prev.textContent = '‹'; prev.title = 'Previous slide (PgUp)';
    prev.setAttribute('data-dir', '-1');
    var count = document.createElement('span');
    count.className = 'yarnnn-stagenav-count';
    var next = document.createElement('button');
    next.type = 'button'; next.textContent = '›'; next.title = 'Next slide (PgDn)';
    next.setAttribute('data-dir', '1');
    prev.addEventListener('click', function () { stageShow(stageCurrent() - 1); });
    next.addEventListener('click', function () { stageShow(stageCurrent() + 1); });
    stageNav.appendChild(prev); stageNav.appendChild(count); stageNav.appendChild(next);
    document.body.appendChild(stageNav);
  }
  // PgUp/PgDn page the stage (the caret never owns these keys).
  document.addEventListener('keydown', function (e) {
    if (!stageMode()) return;
    if (e.key !== 'PageUp' && e.key !== 'PageDown') return;
    e.preventDefault();
    stageShow(stageCurrent() + (e.key === 'PageUp' ? -1 : 1));
  }, true);

  window.addEventListener('message', function (e) {
    var d = e.data;
    if (!d || typeof d !== 'object') return;
    if (d.type === 'yarnnn-view-mode') {
      // ADR-520 D1 — enable/disable the stage. Idempotent; the shown slide
      // survives re-commands (restore-scroll carries the remembered index).
      if (d.stage) {
        var was = stageMode();
        document.body.classList.add('yarnnn-stage');
        ensureStageNav();
        if (!was) stageShow(Math.max(0, stageCurrent()));
      } else {
        document.body.classList.remove('yarnnn-stage');
      }
    } else if (d.type === 'yarnnn-scroll-to-slide') {
      if (stageMode()) { stageShow(d.index); return; }
      var slides = document.querySelectorAll('section.slide');
      var s = slides[d.index];
      if (s && s.scrollIntoView) s.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else if (d.type === 'yarnnn-scroll-to-block' && typeof d.blockId === 'string') {
      // ADR-455: the outline navigates — scroll to a heading block by id.
      try {
        var blk = document.querySelector('[data-block-id="' +
          (window.CSS && CSS.escape ? CSS.escape(d.blockId) : d.blockId) + '"]');
        if (blk) {
          stageShowFor(blk);
          if (blk.scrollIntoView) blk.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
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
        if (selTarget) {
          stageShowFor(selTarget);
          window.__yarnnnSelect(selTarget);
        }
      } catch (err) {}
    } else if (d.type === 'yarnnn-patch' && typeof d.blockId === 'string' &&
               typeof d.html === 'string') {
      // ADR-524 D1 — replace ONE block in place. The whole point: the document
      // is not re-parsed, so scroll, caret, selection and zoom are never
      // destroyed and need no restoring. The parent only sends this for
      // block-local ops (D2); anything structural still swaps srcdoc.
      //
      // The payload is already PROJECTED (projectBlock, D3) — citations
      // stamped + resolved, executables stripped. This runtime does not
      // sanitize; it trusts the same pass that produced the document it is
      // living in, and no other source may use this verb.
      try {
        var pTarget = document.querySelector('[data-block-id="' +
          (window.CSS && CSS.escape ? CSS.escape(d.blockId) : d.blockId) + '"]');
        if (pTarget) {
          // Never patch the block the member is editing: its DOM is the live
          // caret host, and replacing the element under an active caret drops
          // the cursor mid-word. The commit that produced this patch came FROM
          // that block anyway, so the DOM already shows the result.
          var editingNow = window.__yarnnnEditingId && window.__yarnnnEditingId();
          var caretLive = window.__yarnnnCaretLive && window.__yarnnnCaretLive();
          if (editingNow !== d.blockId && !(caretLive && pTarget.contains(
                document.activeElement))) {
            var holder = document.createElement('div');
            holder.innerHTML = d.html;
            var fresh = holder.firstElementChild;
            if (fresh) {
              var wasSelected = pTarget.classList.contains('yarnnn-pointed');
              pTarget.replaceWith(fresh);
              // Re-assert selection on the NEW element — the old one carried
              // the class and is now detached.
              if (wasSelected && window.__yarnnnSelect) window.__yarnnnSelect(fresh);
            }
          }
        }
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
          if (stageMode()) {
            // ADR-520 D1: on the stage, restoring the position IS restoring
            // the shown slide — the anchoring unit made literal.
            stageShow(d.slide);
            restored = true;
          } else {
            var target = document.querySelectorAll('section.slide')[d.slide];
            if (target && target.scrollIntoView) {
              target.scrollIntoView({ block: 'start' });
              restored = true;
            }
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
    // ADR-520 D1: on the stage the shown slide IS the position.
    if (stageMode()) { var sc = stageCurrent(); return sc >= 0 ? sc : null; }
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
  // ── Keyboard verbs (ADR-482 D2, relocated from the gutter script) ──────
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
  // ADR-521 D6: the block VERB tier is an OBJECT tier on flow.
  //
  // The audit ADR-521 §7 deferred, executed. These keys were written for the
  // enclosure grain (ADR-482 D2, eight days before ADR-480 flipped it) and they
  // ask only "is a block selected, and does the caret have a claim on it" —
  // never "is this subject prose or an object". On flow that is unsound,
  // because the click handler sets cur on EVERY block including prose (it
  // withholds only the visual cue, ADR-484), so a paragraph is a live verb
  // subject while looking like nothing is selected.
  //
  // Two windows made Delete/Backspace destroy a whole paragraph:
  //   1. an EMPTIED paragraph — caretOwnsKeyIn requires non-empty text, so
  //      clearing a paragraph and pressing Backspace again to merge up deleted
  //      the block instead of merging;
  //   2. a CROSS-BLOCK RANGE — the subject ADR-521 D2 just made first-class.
  //      startContainer sits in the FIRST block of the range, so inBlk is
  //      false for cur, and Backspace over an h1-prose-li selection deleted a
  //      whole block instead of the selected range.
  // Both commit a revision through applyOp — real loss, undo-recoverable only.
  //
  // The law (D2): text-tier affordances follow the SELECTION; structure-tier
  // affordances address the blocks it intersects. A unit verb on a prose block
  // is neither — it is the enclosure asserting itself. So on flow the verbs
  // keep exactly the subjects that still have no caret to speak for them:
  // OBJECT kinds (figure, table, chart, gallery, divider). For prose the keys
  // go back to the platform, where Backspace means "delete the selection or
  // merge" — the continuous-surface mechanic ADR-521 D1 committed to.
  //
  // Paged is untouched: there the block IS an enclosure and the unit verb is
  // the correct grain (ADR-480's per-mode axiom).
  function verbSubjectAllowed(blk) {
    var flow = window.__yarnnnFlowMode ? window.__yarnnnFlowMode() : false;
    if (!flow) return true;
    return TEXT_KINDS.indexOf(blk.getAttribute('data-block')) === -1;
  }
  function selectedBlock() {
    var sel = window.__yarnnnSelected ? window.__yarnnnSelected() : null;
    if (!sel || !sel.isConnected) return null;
    if (!verbSubjectAllowed(sel)) return null;
    return caretOwnsKeyIn(sel) ? null : sel;
  }

  // ── ADR-526 D3 — ⌥↑ / ⌥↓ move the block (STRUCTURE tier) ────────────────
  //
  // A deliberate, argued reversal, and it is narrow. What stands: ADR-521 D7's
  // "no drag handles / positional anything on flow", and ADR-525 D3's removal
  // of Move up/down from the pane and the menu. Those refusals are about
  // PRESENTATION — a drag handle asserts a box; a verb row presents the block
  // as an enclosure with a position in a list. A keyboard chord asserts
  // neither: it says "put this before the previous one", which is exactly what
  // moveBlock already does, medium-agnostically.
  //
  // The precedent is ADR-521 D4's Tab-indent, which superseded this runtime's
  // own written refusal on the reasoning that "a keyboard entrance to a
  // structural op has exactly slash's legitimacy — the key is not the op, it
  // is a door to it." Same tier, same shape, same reason.
  //
  // The subject is NOT selectedBlock(): that is the OBJECT-tier gate (ADR-521
  // D6) and it refuses prose on flow by design. A structure-tier act addresses
  // the block the caret is in — the ADR-521 D2 law, one rung over.
  function structureSubject() {
    var sel = window.__yarnnnSelected ? window.__yarnnnSelected() : null;
    if (sel && sel.isConnected) return sel;
    var s = window.getSelection();
    if (!s || !s.rangeCount) return null;
    var n = s.getRangeAt(0).startContainer;
    var el = n && n.nodeType === 1 ? n : (n ? n.parentElement : null);
    return el && el.closest ? el.closest('[data-block]') : null;
  }
  document.addEventListener('keydown', function (e) {
    if (!e.altKey || (e.key !== 'ArrowUp' && e.key !== 'ArrowDown')) return;
    if (e.metaKey || e.ctrlKey) return;
    var t = e.target;
    if (t && t.closest && t.closest('.yarnnn-fmt')) return;
    // Never steal a RANGE: a selection spanning blocks is the member's text
    // selection and ⌥↑ there is the platform's (extend/move by paragraph).
    var s = window.getSelection();
    if (s && s.rangeCount && !s.getRangeAt(0).collapsed) return;
    var subj = structureSubject();
    if (!subj) return;
    var sid = subj.getAttribute('data-block-id');
    if (!sid) return;
    e.preventDefault();
    parent.postMessage({
      type: 'yarnnn-key-verb',
      verb: e.key === 'ArrowUp' ? 'up' : 'down',
      blockId: sid,
    }, '*');
  }, true);

  document.addEventListener('keydown', function (e) {
    var blk = selectedBlock();
    if (!blk) return;
    var t = e.target;
    if (t && t.closest && t.closest('.yarnnn-fmt')) return;
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
  var PAGE_SEL = '${STRUCTURAL_PAGE_SEL}'; // ADR-511 Phase 2 — the one structural page selector
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
    // ADR-511 Phase 2 — STRUCTURAL: any empty LEAF container earns the
    // placeholder (imported HTML included), not just a [data-slot]-named one.
    // Same container predicate as the pointer runtime and normalizeStructure.
    var divs = document.querySelectorAll('div');
    var slots = [];
    for (var d = 0; d < divs.length; d++) {
      var el = divs[d];
      if (el.hasAttribute('data-block') || el.hasAttribute('data-ref')) continue;
      if (el.parentElement && el.parentElement.closest('[data-block], [data-ref]')) continue;
      slots.push(el);
    }
    for (var i = 0; i < slots.length; i++) {
      var slot = slots[i];
      // Empty = no block inside AND no child container (a leaf region).
      if (slot.querySelector('[data-block]')) {
        slot.classList.remove('yarnnn-slot-open'); // filled — bounds retire
        continue;
      }
      var isLeaf = true;
      for (var j = 0; j < slots.length; j++) {
        if (slots[j] !== slot && slot.contains(slots[j])) { isLeaf = false; break; }
      }
      if (!isLeaf) continue;
      // ADR-466 P8: an empty region shows its dashed bounds ALWAYS on a deck
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
      btn.setAttribute('data-slot-name', slot.getAttribute('data-area') || slot.getAttribute('data-slot') || '');
      // ADR-511 Phase 2 — the container's IDENTITY is the op address (the
      // load-normalize stamped it); slot/arrange ride along as legacy names
      // for the parent's registry ROLE lookup (media → the picker).
      btn.setAttribute('data-container-id', slot.getAttribute('data-block-id') || '');
      btn.addEventListener('click', function (e) {
        e.preventDefault(); e.stopPropagation();
        var page = this.closest ? this.closest('[data-arrange]') : null;
        parent.postMessage({
          type: 'yarnnn-add-here',
          slot: this.getAttribute('data-slot-name'),
          containerId: this.getAttribute('data-container-id') || null,
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

/* ADR-456 W2: the inline format bar — injected chrome, body-appended (never
   inside a block, so it can never leak into a commit). Its OWN sheet
   (2026-07-25): the runtime builds the bar on BOTH grains (projection's
   editHost() seam, "written once and serve both grains"), but the rules
   lived in EDIT_CSS, which ADR-482 D4 made paged-only — so on flow the bar
   rendered as unstyled static buttons at the end of body (position:absolute
   never applied, the inline left/top ignored). The bar's chrome is
   grain-independent; it ships whenever the edit runtime does. */
const FMT_CSS = `
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
/* all:unset above strips the UA focus ring, and the buttons stay in tab
   order — so a keyboard member could land on B/I/code/Link with no indication
   of where they were. Put a ring back explicitly. :focus-visible, so it appears
   for the keyboard and not on every mouse press (the reason the UA ring is
   itself :focus-visible on modern browsers). Same reasoning as the ADR-482 D8
   suppression, in the opposite direction: there we removed a ring the browser
   drew and we did not want; here we restore one we removed and do need. */
.yarnnn-fmt button:focus-visible {
  outline: 2px solid #e5e7eb; outline-offset: 1px; background: rgba(255,255,255,0.15);
}
.yarnnn-fmt input {
  font: 12px system-ui, sans-serif; border: 0; border-radius: 4px;
  padding: 4px 6px; width: 220px; outline: none;
}
/* The link input suppressed its outline with nothing in its place. It is the
   one field in this bar a member TYPES into, so an unfocusable-looking focused
   field is the worst case of the three. */
.yarnnn-fmt input:focus-visible {
  outline: 2px solid #60a5fa; outline-offset: 1px;
}
`;

const EDIT_CSS = `
[data-block][contenteditable="true"] {
  outline: 2px solid var(--yarnnn-chrome-accent) !important; outline-offset: 3px;
  background: rgba(var(--yarnnn-chrome-accent-rgb),0.04);
}
[data-block][contenteditable="true"] [data-ref] {
  outline: 1px dashed rgba(var(--yarnnn-chrome-accent-rgb),0.5); cursor: default;
}
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
/* ADR-511 D4 — the out-of-flow tag: a POSITIONED block says so at its corner.
   Absolute is a deliberate, visible exception; flow is the default. The
   Design tab's Position row (In flow | Positioned) is the reversal. */
.yarnnn-selbox-abs::after {
  content: 'positioned'; position: absolute; right: 0; top: -1.15rem;
  font: 500 0.6rem system-ui, sans-serif; letter-spacing: 0.06em;
  text-transform: uppercase; color: var(--yarnnn-chrome-accent);
  pointer-events: none;
}
/* ADR-516 D5 — a selected structural CONTAINER off the stage is legible: the
   box, border only. No handles, no move band — no frame, no measure, and the
   chrome must not promise gestures the grain lacks (the "honest about
   inertness" rule at the new grain). */
.yarnnn-selbox-container .yarnnn-selh,
.yarnnn-selbox-container .yarnnn-selmove { display: none; }
/* ADR-520 D2 — a STAGED container is adjustable: the eight handles live, the
   move band hidden (move stays reorder-shaped; a container never positions). */
.yarnnn-selbox-container-sizable .yarnnn-selmove { display: none; }
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
.slide [data-area].yarnnn-slot-open, .slide [data-slot].yarnnn-slot-open {
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
`;

const EDIT_SCRIPT = `
(function () {
  var TEXT_KINDS = ${TEXT_KINDS_JS};
  // ADR-546 D1 — the declared rung set reaches the runtime as DATA (the runtime
  // is a module-level template string and cannot close over module scope, so a
  // served/mirrored constant arrives interpolated — never re-typed here).
  var FLOW_RUNGS = ${FLOW_RUNGS_JS};
  var DEEPEST_FLOW_RUNG = ${DEEPEST_FLOW_RUNG_JS};
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
    // Enumerated rather than hard-coded to ONE class: yarnnn-grouped (the
    // group's cue, 2026-07-24) is the second member of this family, and the
    // ADR-484 defect was precisely that a runtime class had no single place
    // that knew it must be stripped. Any future cue belongs in this list.
    var CHROME_CLASSES = ['yarnnn-pointed', 'yarnnn-grouped'];
    for (var c = 0; c < CHROME_CLASSES.length; c++) {
      var painted = clone.querySelectorAll('.' + CHROME_CLASSES[c]);
      for (var p = 0; p < painted.length; p++) {
        painted[p].classList.remove(CHROME_CLASSES[c]);
        // Drop the attribute entirely when it was the only class — an empty
        // class="" is noise in an attributed revision diff.
        if (!painted[p].getAttribute('class')) painted[p].removeAttribute('class');
      }
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
    // ADR-480 D1 — flow has NO per-block session: the root is the editor.
    // This is the chokepoint (2026-07-25): the dblclick fallback below had no
    // flow guard, so double-clicking prose stamped contenteditable on the
    // BLOCK — a nested editable inside the editable root, wearing the UA
    // focus ring D8 only suppressed on the root (the operator's boxed
    // paragraph), and assigning editingEl state no flow path expects.
    if (FLOW_MODE) return;
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
    // ADR-521 D5: rich paste behind the allowlist — the SAME handler the flow
    // root uses (one implementation, both grains); plain-text fallback inside.
    var onPaste = richPaste;
    el.__yarnnnBlur = onBlur;
    el.__yarnnnInput = onInput;
    el.__yarnnnPaste = onPaste;
    el.addEventListener('blur', onBlur);
    el.addEventListener('input', onInput);
    el.addEventListener('paste', onPaste);
  }

  // ── ADR-560 D8: the FLOW editing session is DELETED ──────────────────
  // Flow documents edit in the parent-mounted model (FlowEditor), never in
  // this iframe: enterFlow, flowCommit, flowDead (ADR-540's fence) and the
  // whole-body yarnnn-flow-edit commit lane have no host here. This runtime
  // serves the PAGED editing grain and read-only projection.

  // ── ADR-456 W2: the inline format bar ─────────────────────────────────
  // Injected chrome, appended to <body> (never inside a block — commits read
  // the block's inner, so the bar can never leak into the source). Shows on a
  // non-collapsed selection inside the editing block. B/I ride execCommand
  // (native toggle; b/i normalized to strong/em at the write door), code is a
  // range wrap, link swaps the bar to a URL input (the blur guard keeps the
  // edit session alive while it has focus).
  var fmtBar = null, fmtBtns = null, fmtInput = null, savedRange = null;
  // ADR-527 D4 — the last range the member had inside the edit host. The pane
  // lives outside the iframe, so a pane click destroys the selection before the
  // command arrives; this is what it is restored from. Tracked on selection
  // change rather than captured on click, because the parent cannot tell the
  // runtime "I am about to steal focus".
  var lastLiveRange = null;
  // The last block-set we told the parent about, as a joined id string — so a
  // caret moving WITHIN one block does not re-post on every keystroke.
  var lastRangeKey = '';
  document.addEventListener('selectionchange', function () {
    try {
      var s = window.getSelection();
      var h = editHost();
      if (!s || !s.rangeCount || s.isCollapsed) {
        // ADR-528 — the range collapsed (a click, an arrow key). The parent's
        // range-scope must clear, or the pane keeps claiming a multi-block
        // selection the member has already dismissed.
        if (lastRangeKey) {
          lastRangeKey = '';
          parent.postMessage({ type: 'yarnnn-range', blockIds: [] }, '*');
        }
        return;
      }
      var r = s.getRangeAt(0);
      if (!h || !h.contains(r.commonAncestorContainer)) return;
      lastLiveRange = r.cloneRange();
      // ADR-528 — REPORT THE BLOCK SET. The parent's selection was written
      // only by a CLICK (yarnnn-point), so dragging across six blocks left the
      // pane describing whichever block was clicked into last: it showed
      // "HEADING · Heading 2 · Turn into" over a six-block range. Not
      // wrong-looking, which is what made it hard to see — STALE.
      //
      // The block set is formatSegments' own derivation (ADR-521 D2's
      // structure tier: the blocks a range intersects), so this reports what
      // the format ops already act on rather than deriving a second answer.
      var ids = [];
      // ADR-546 D3 — each covered block carries its RUNG, so the parent can
      // derive the span's SHAPE (a heading + what sits under it is a subtree,
      // not N peers) instead of only counting. The runtime is the only party
      // that can see the DOM, so it reports the fact; spanShapeOf in
      // selection.ts is the ONE place that interprets it (ADR-541 D2).
      var rungs = [];
      var segs = formatSegments();
      for (var i = 0; i < segs.length; i++) {
        var id = segs[i].block.getAttribute('data-block-id');
        if (id) {
          ids.push(id);
          var r = rungOf(segs[i].block);
          // The heading's own text rides along, so the parent can NAME the span
          // ("Pricing and the 6 blocks under it") without re-walking the DOM it
          // does not own. Only headings carry it; nothing else needs a name.
          if (r.heading != null) {
            r.text = (segs[i].block.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 60);
          }
          rungs.push(r);
        }
      }
      var key = ids.join(',');
      if (key === lastRangeKey) return; // same blocks — nothing to re-say
      lastRangeKey = key;
      parent.postMessage({ type: 'yarnnn-range', blockIds: ids, rungs: rungs }, '*');
    } catch (err) {}
  });

  function scheduleCommit() {
    // ADR-560 D8: one grain commits here now — the paged block's inner. Flow
    // commits are the model's (FlowEditor), not this runtime's.
    if (FLOW_MODE) return;
    if (idleTimer) clearTimeout(idleTimer);
    idleTimer = setTimeout(commit, 2000);
  }

  // ── ADR-521 D3: the format tier — per-block-intersection, deterministic ──
  // The selection law (D2): text-tier affordances follow the SELECTION
  // wherever it runs; structure-tier affordances address the BLOCKS it
  // intersects. On flow the browser owns the range (ADR-480), so a range may
  // cross blocks. A bare execCommand toggle there is browser-defined per
  // segment — an h1 is already bold, so "bold" tried to UN-bold it through
  // style spans the commit sanitizer strips: a silent revert. Segmentation
  // plus a computed intent make the op deterministic.

  function isHeadingBlock(el) {
    if (!el) return false;
    var t = el.tagName;
    if (t === 'H1' || t === 'H2' || t === 'H3' || t === 'H4' || t === 'H5' || t === 'H6') return true;
    return el.getAttribute && el.getAttribute('data-block') === 'heading';
  }

  // ── ADR-546 D2: one block's RUNG, read off the DOM ──────────────────────
  //
  // Depth on a document, in its two spellings: a heading's level, and nesting
  // steps inside a list. Reported as data; INTERPRETED only by spanShapeOf
  // (selection.ts) — the runtime never decides what a span means.
  //
  // No new identity: this reads the tree, it does not stamp it. An <li> still
  // carries no data-block-id (D2's refusal), which is exactly why the nesting
  // rung has to be DERIVED here rather than looked up.
  //
  // Clamped to the declared set (D1), so an over-deep paste reports the deepest
  // rung the medium speaks rather than a number nothing renders.
  function rungOf(blk) {
    if (!blk) return { heading: null, nesting: 0 };
    var tag = (blk.tagName || '').toUpperCase();
    var heading = /^H([0-9])$/.test(tag) ? Number(tag.slice(1)) : null;
    if (heading != null && FLOW_RUNGS.indexOf(heading) === -1) heading = DEEPEST_FLOW_RUNG;
    // Nesting: count the list ancestors ABOVE this block's own list. The block
    // IS the list (ul/ol carry data-block), so a nested <li>'s depth is how many
    // further lists sit between it and the block — but the block itself is the
    // top, so a non-nested list reports 0.
    var nesting = 0;
    var node = blk.parentElement;
    while (node && node !== document.body) {
      var t = (node.tagName || '').toUpperCase();
      if (t === 'UL' || t === 'OL') nesting++;
      if (node.hasAttribute && node.hasAttribute('data-block')) break;
      node = node.parentElement;
    }
    if (nesting > DEEPEST_FLOW_RUNG) nesting = DEEPEST_FLOW_RUNG;
    return { heading: heading, nesting: nesting };
  }

  function formatSegments() {
    var host = editHost();
    if (!host) return [];
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount) return [];
    var r = sel.getRangeAt(0);
    if (r.collapsed) return [];
    var blocks = host.querySelectorAll('[data-block]');
    var segs = [];
    for (var i = 0; i < blocks.length; i++) {
      var b = blocks[i];
      // Top-level blocks only — a nested annotated element rides its parent's
      // segment; citation islands are never format subjects (ADR-446 D3).
      if (b.parentElement && b.parentElement.closest('[data-block]')) continue;
      if (b.closest('[data-ref]')) continue;
      var touches = false;
      try { touches = r.intersectsNode(b); } catch (err) { touches = false; }
      if (!touches) continue;
      var sub = document.createRange();
      sub.selectNodeContents(b);
      // Clamp to the live range: the later start wins, the earlier end wins.
      if (sub.compareBoundaryPoints(Range.START_TO_START, r) < 0) sub.setStart(r.startContainer, r.startOffset);
      if (sub.compareBoundaryPoints(Range.END_TO_END, r) > 0) sub.setEnd(r.endContainer, r.endOffset);
      if (!sub.collapsed) segs.push({ block: b, range: sub });
    }
    if (!segs.length) {
      // A selection wholly inside ONE block — the common case, and every paged
      // case (the enclosure grain caps the range at the editing block).
      var anc = r.commonAncestorContainer;
      var ancEl = anc && anc.nodeType === 1 ? anc : (anc ? anc.parentElement : null);
      var own = ancEl && ancEl.closest ? ancEl.closest('[data-block]') : null;
      segs.push({ block: own, range: r.cloneRange() });
    }
    return segs;
  }

  function applyToggle(cmd) {
    var segs = formatSegments();
    if (!segs.length) return;
    var sel = window.getSelection();
    var saved = null;
    try { saved = sel.getRangeAt(0).cloneRange(); } catch (err) {}
    var eligible = [];
    for (var i = 0; i < segs.length; i++) {
      // A heading is already bold — "bolding" it is a no-op, never an un-bold.
      if (cmd === 'bold' && isHeadingBlock(segs[i].block)) continue;
      eligible.push(segs[i]);
    }
    if (!eligible.length) return;
    // Pass 1 — the intent: ANY eligible segment unformatted means APPLY
    // everywhere (the Word rule); only a fully-formatted selection removes.
    var intent = false;
    for (var j = 0; j < eligible.length; j++) {
      sel.removeAllRanges();
      sel.addRange(eligible[j].range);
      if (!document.queryCommandState(cmd)) { intent = true; break; }
    }
    // Pass 2 — enforce the intent; toggle only where the state differs. Never
    // a blind per-segment toggle (that is exactly the h1 un-bold trap).
    for (var k = 0; k < eligible.length; k++) {
      sel.removeAllRanges();
      sel.addRange(eligible[k].range);
      if (document.queryCommandState(cmd) !== intent) document.execCommand(cmd);
    }
    if (saved) {
      try { sel.removeAllRanges(); sel.addRange(saved); } catch (err2) {}
    }
  }

  // ── ADR-527 D2 — the PALETTE MARK (colour, without a colour) ─────────────
  //
  // Google Docs offers an arbitrary picker; ADR-449 forbids one and the pane
  // says so in its own words ("emphasis via the palette variables — never raw
  // color"). Notion's answer is a fixed set of roles, and that is the shape:
  // a span carrying a ROLE NAME, with one kernel rule per role. A design-system
  // change therefore re-themes every document that used it — the entire reason
  // for the constraint.
  //
  // Never an inline color:/background:. The value written is a role, and the
  // role set is closed (validated below), so a raw value cannot reach the DOM
  // even if the parent asks for one.
  var MARK_ROLES = ['muted', 'accent', 'fresh', 'warn', 'danger'];
  var HIGHLIGHT_ROLES = ['accent', 'fresh', 'warn', 'danger'];

  function applyMark(attr, role, allowed) {
    // Clearing (role null/empty) unwraps; setting re-marks. Both are per-block
    // segments, so a mark never crosses a block boundary — the same rule the
    // code op learned (ADR-521 D3's cross-block mangle).
    if (role && allowed.indexOf(role) === -1) return; // closed set — never raw
    var segs = formatSegments();
    if (!segs.length) return;
    var sel = window.getSelection();
    var saved = null;
    try { saved = sel.getRangeAt(0).cloneRange(); } catch (err) {}
    for (var i = 0; i < segs.length; i++) {
      sel.removeAllRanges();
      sel.addRange(segs[i].range);
      // Strip any existing mark of this attr inside the segment first, so
      // re-marking never nests spans (the accreted-wrapper trap).
      unwrapMarks(segs[i].range, attr);
      if (!role) continue; // clear-only
      try {
        var span = document.createElement('span');
        span.setAttribute(attr, role);
        span.appendChild(segs[i].range.extractContents());
        segs[i].range.insertNode(span);
      } catch (err2) {}
    }
    if (saved) {
      try { sel.removeAllRanges(); sel.addRange(saved); } catch (err3) {}
    }
  }

  /** Unwrap every [attr] span intersecting a range — children survive. */
  function unwrapMarks(range, attr) {
    var root = range.commonAncestorContainer;
    var el = root && root.nodeType === 1 ? root : (root ? root.parentElement : null);
    if (!el || !el.querySelectorAll) return;
    var hits = Array.prototype.slice.call(el.querySelectorAll('span[' + attr + ']'));
    // The ancestor chain too: a range INSIDE one mark has no descendant to find.
    var up = el.closest ? el.closest('span[' + attr + ']') : null;
    if (up) hits.push(up);
    for (var i = 0; i < hits.length; i++) {
      var s = hits[i];
      if (!range.intersectsNode || range.intersectsNode(s)) {
        while (s.firstChild) s.parentNode.insertBefore(s.firstChild, s);
        if (s.parentNode) s.parentNode.removeChild(s);
      }
    }
  }

  /** ADR-527 D1 — clear formatting. Emphasis goes; STRUCTURE stays: a heading
   *  is still a heading, a list item still a list item. Clearing arrangement is
   *  D3's job (the align/indent tokens), never this op's. */
  function applyClear() {
    var segs = formatSegments();
    if (!segs.length) return;
    var sel = window.getSelection();
    var saved = null;
    try { saved = sel.getRangeAt(0).cloneRange(); } catch (err) {}
    for (var i = 0; i < segs.length; i++) {
      sel.removeAllRanges();
      sel.addRange(segs[i].range);
      // removeFormat drops b/i/u/s reliably; it does NOT reliably drop
      // attribute-carrying spans, so the palette marks are stripped by hand.
      try { document.execCommand('removeFormat'); } catch (err2) {}
      unwrapMarks(segs[i].range, 'data-mark');
      unwrapMarks(segs[i].range, 'data-highlight');
    }
    if (saved) {
      try { sel.removeAllRanges(); sel.addRange(saved); } catch (err3) {}
    }
  }

  function segmentCoded(seg) {
    var anc = seg.range.commonAncestorContainer;
    var el = anc && anc.nodeType === 1 ? anc : (anc ? anc.parentElement : null);
    return !!(el && el.closest && el.closest('code'));
  }

  function applyCode() {
    var segs = formatSegments();
    if (!segs.length) return;
    var sel = window.getSelection();
    var allCoded = true;
    for (var i = 0; i < segs.length; i++) {
      if (!segmentCoded(segs[i])) { allCoded = false; break; }
    }
    for (var j = 0; j < segs.length; j++) {
      var seg = segs[j];
      if (allCoded) {
        var anc = seg.range.commonAncestorContainer;
        var el = anc && anc.nodeType === 1 ? anc : (anc ? anc.parentElement : null);
        var code = el && el.closest ? el.closest('code') : null;
        if (code && code.parentNode) {
          while (code.firstChild) code.parentNode.insertBefore(code.firstChild, code);
          code.parentNode.removeChild(code);
        }
      } else if (!segmentCoded(seg)) {
        var wrap = document.createElement('code');
        try { seg.range.surroundContents(wrap); }
        catch (err) {
          // A partially-selected INLINE element (half a link, half an em):
          // extract+insert is safe here because a segment never crosses a
          // block boundary — the old cross-block mangle is unreachable.
          wrap.appendChild(seg.range.extractContents());
          seg.range.insertNode(wrap);
        }
      }
    }
    sel.removeAllRanges();
  }

  // ── ADR-521 D5: the paste allowlist (gate 1 of 2) ─────────────────────
  // Gate 2 is sanitizeInner at the commit (ADR-446 D2) — script, on* handlers
  // and javascript: URLs cannot land even if this gate misses. This gate is
  // the hygiene layer: only the tags the grammar speaks survive, every
  // attribute is stripped (href survives with javascript: rejected), and
  // media is dropped — media enters as CITED figures (ADR-427/448), never as
  // anonymous pasted bytes.
  var PASTE_DROP = { SCRIPT: 1, STYLE: 1, IFRAME: 1, OBJECT: 1, EMBED: 1, LINK: 1, META: 1, TITLE: 1, HEAD: 1, FORM: 1, INPUT: 1, BUTTON: 1, SELECT: 1, TEXTAREA: 1, IMG: 1, PICTURE: 1, VIDEO: 1, AUDIO: 1, SOURCE: 1, CANVAS: 1, SVG: 1, MATH: 1, TEMPLATE: 1, NOSCRIPT: 1 };
  var PASTE_ALLOW = { P: 1, BR: 1, HR: 1, STRONG: 1, B: 1, EM: 1, I: 1, U: 1, S: 1, CODE: 1, PRE: 1, A: 1, UL: 1, OL: 1, LI: 1, H1: 1, H2: 1, H3: 1, H4: 1, H5: 1, H6: 1, BLOCKQUOTE: 1, TABLE: 1, THEAD: 1, TBODY: 1, TFOOT: 1, TR: 1, TH: 1, TD: 1, CAPTION: 1, DL: 1, DT: 1, DD: 1, FIGCAPTION: 1, SUP: 1, SUB: 1,
    // ADR-527 D2: a SPAN is allowed so a palette mark survives. It carries
    // no meaning of its own — on a FOREIGN paste every attribute is still
    // stripped, so a foreign span arrives as a bare, styleless wrapper.
    SPAN: 1 };
  // ADR-539 D4 — the out-of-rung heading tags and the rung they clamp to,
  // interpolated from the module's HEADING_RUNGS (the kernel's one declaration).
  // H4–H6 stay in PASTE_ALLOW above only so they are never UNWRAPPED before
  // the clamp in scrub() renames them.
  var OUT_OF_RUNG = ${OUT_OF_RUNG_TAGS_JS};
  var DEEPEST_RUNG_TAG = ${DEEPEST_RUNG_TAG_JS};

  // ADR-526 D4 — the substrate attributes an INTERNAL paste keeps. The ADR-521
  // D5 allowlist strips every attribute but href, which is exactly right for
  // FOREIGN html (it is a security gate) and wrong for a member cutting and
  // pasting inside their own document: reorder-by-cut-paste is the only
  // reorder flow has (projection.ts prices it as "the browser's own, priced and
  // accepted"), and it silently discarded citations and tokens on the way.
  //
  // Kept: the grammar's own vocabulary. NOT kept: style, class, event handlers,
  // or anything else — the foreign path is untouched and this list is closed.
  var PASTE_KEEP_INTERNAL = {
    'data-block': 1, 'data-ref': 1, 'data-ref-kind': 1, 'data-src-html': 1,
    'data-tone': 1, 'data-variant': 1, 'data-size': 1, 'data-align': 1,
    'data-fit': 1, 'data-height': 1,
    // ADR-527 D2 — the palette marks ride an internal paste like every
    // other grammar attribute. Without this a member who cuts and pastes
    // coloured text loses the colour, which is the ADR-526 D4 defect one
    // vocabulary later. Role names only; the set is closed at write time.
    'data-mark': 1, 'data-highlight': 1, 'data-indent': 1,
  };

  /** Is this clipboard payload OURS? The honest test is provenance by identity:
   *  the html carries a data-block-id that exists in THIS document, which no
   *  foreign source can fabricate by accident. Note data-block-id itself is
   *  never kept (ids are re-minted by normalizeStructure — a duplicate id is
   *  worse than none); it is read only as the origin signal. */
  function isInternalPaste(html) {
    var m = /data-block-id="([^"]+)"/.exec(html || '');
    if (!m) return false;
    try {
      return !!document.querySelector('[data-block-id="' +
        (window.CSS && CSS.escape ? CSS.escape(m[1]) : m[1]) + '"]');
    } catch (err) { return false; }
  }

  function sanitizePastedHtml(html, internal) {
    var doc;
    try { doc = document.implementation.createHTMLDocument(''); }
    catch (err) { return ''; }
    doc.body.innerHTML = html;
    function scrub(parent) {
      var kids = Array.prototype.slice.call(parent.children);
      for (var i = 0; i < kids.length; i++) {
        var el = kids[i];
        if (PASTE_DROP[el.tagName]) { parent.removeChild(el); continue; }
        scrub(el);
        // ADR-539 D4 — intake clamps to the declared rung set: a pasted
        // heading below the deepest spoken rung arrives AS the deepest rung
        // (h4–h6 → h3). The vocabulary speaks three rungs; admitting a fourth
        // here is how a block the pane called "Heading" was invisible to the
        // outline, the crumb, and the lane in the same instant.
        if (OUT_OF_RUNG.indexOf(el.tagName) !== -1) {
          var clampedEl = doc.createElement(DEEPEST_RUNG_TAG);
          var catts = Array.prototype.slice.call(el.attributes);
          for (var ci = 0; ci < catts.length; ci++) {
            clampedEl.setAttribute(catts[ci].name, catts[ci].value);
          }
          while (el.firstChild) clampedEl.appendChild(el.firstChild);
          parent.replaceChild(clampedEl, el);
          el = clampedEl;
        }
        if (!PASTE_ALLOW[el.tagName]) {
          // Unwrap: the wrapper dies, its (already-scrubbed) children stay.
          while (el.firstChild) parent.insertBefore(el.firstChild, el);
          parent.removeChild(el);
          continue;
        }
        var atts = Array.prototype.slice.call(el.attributes);
        for (var a = 0; a < atts.length; a++) {
          var name = atts[a].name;
          if (el.tagName === 'A' && name.toLowerCase() === 'href') {
            var v = (el.getAttribute('href') || '').trim().toLowerCase();
            if (v.indexOf('javascript:') === 0) el.removeAttribute('href');
            continue;
          }
          // ADR-526 D4: on an internal paste the grammar's own attributes ride
          // along. Every other attribute still goes, on both paths.
          if (internal && PASTE_KEEP_INTERNAL[name.toLowerCase()] === 1) continue;
          el.removeAttribute(name);
        }
      }
    }
    scrub(doc.body);
    return doc.body.innerHTML;
  }

  function richPaste(e) {
    var cb = e.clipboardData || window.clipboardData;
    if (!cb) return; // no clipboard object — let the browser default run
    e.preventDefault();
    var html = '';
    try { html = cb.getData('text/html') || ''; } catch (err) {}
    if (html) {
      var clean = sanitizePastedHtml(html, isInternalPaste(html));
      if (clean) {
        try { document.execCommand('insertHTML', false, clean); return; } catch (err2) {}
      }
    }
    var text = '';
    try { text = cb.getData('text/plain') || ''; } catch (err3) {}
    if (text && document.queryCommandSupported && document.queryCommandSupported('insertText')) {
      document.execCommand('insertText', false, text);
    }
  }

  function hideFmt() {
    if (fmtBar) fmtBar.style.display = 'none';
    if (fmtInput) fmtInput.style.display = 'none';
    if (fmtBtns) fmtBtns.style.display = 'inline-flex';
    // ADR-613 — the range grain lost its subject. The BLOCK may still be
    // selected, and showBox re-reports it; this only retracts the range.
    if (window.__yarnnnPostSelRect) window.__yarnnnPostSelRect(null, null);
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

  function applyFmt(op, value) {
    if (!editHost()) return; // ADR-480: the host is the block (paged) or the root (flow)
    if (op === 'bold') applyToggle('bold');
    else if (op === 'italic') applyToggle('italic');
    // ADR-527 D1 — underline and strikethrough are ONE ROW EACH, not new
    // mechanisms: applyToggle is command-generic and already carries the
    // per-block segmentation + the deterministic Word rule (ADR-521 D3).
    else if (op === 'underline') applyToggle('underline');
    else if (op === 'strike') applyToggle('strikeThrough');
    else if (op === 'code') applyCode();
    // ADR-527 D2 — palette roles, never a colour. A null value clears.
    else if (op === 'mark') applyMark('data-mark', value || null, MARK_ROLES);
    else if (op === 'highlight') applyMark('data-highlight', value || null, HIGHLIGHT_ROLES);
    else if (op === 'clear') applyClear();
    else if (op === 'link') { openLink(); return; }
    else return; // unknown op — never fall through to a commit
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
    // ADR-613 — the same rect, reported for the parent-side judged gesture.
    // The RANGE grain: the member has text selected inside a block, so the
    // target is the range, not the block that holds it. ancEl is passed as
    // the SUBJECT so the reported content box is the stage this text sits on
    // — the range's own rect cannot name the margin it must hang outside of.
    if (window.__yarnnnPostSelRect) window.__yarnnnPostSelRect(rect, 'range', ancEl);
  });

  // ── ADR-521 D4: ⌘B/⌘I are the bar's op behind a key ───────────────────
  // One implementation, N entrances (the ADR-511 D5 shape). Only a real
  // SELECTION is intercepted: at a collapsed caret the browser's native
  // type-ahead state is correct — there is no heterogeneous range, so the
  // trap the D3 op exists for cannot fire there.
  document.addEventListener('keydown', function (e) {
    if (!(e.metaKey || e.ctrlKey) || e.altKey || e.shiftKey) return;
    var op = null;
    if (e.key === 'b' || e.key === 'B') op = 'bold';
    else if (e.key === 'i' || e.key === 'I') op = 'italic';
    if (!op) return;
    var host = editHost();
    if (!host) return;
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount || sel.isCollapsed) return; // caret: browser-native
    var r = sel.getRangeAt(0);
    var anc = r.commonAncestorContainer;
    var ancEl = anc && anc.nodeType === 1 ? anc : (anc ? anc.parentElement : null);
    if (!ancEl || !host.contains(ancEl)) return;
    e.preventDefault();
    applyFmt(op);
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
  // Is the palette ON SCREEN right now? Distinct from the anchor above, and the
  // distinction is load-bearing. hideSlash() dismisses the palette but KEEPS
  // the anchor (a pointer press may BE the pick — see the mousedown below), so
  // after a click-away the anchor is still live while nothing is displayed.
  // The keyboard interception below must follow the VISIBLE palette, not the
  // anchor: guarding it on slashStart alone let a dismissed palette swallow
  // the member's next Enter / Arrow / Escape exactly once, with no chrome on
  // screen to explain where the keystroke went.
  var slashOpen = false;

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
    slashOpen = false; // the palette leaves the screen; the anchor stays
    parent.postMessage({ type: 'yarnnn-slash-close' }, '*');
  }

  // Hide AND forget. Only for the paths where the run itself is genuinely gone
  // (the '/' deleted, a space typed, the caret moved away) — never for a mere
  // pointer press, which may BE the pick.
  function closeSlash() {
    if (slashStart < 0) return;
    slashStart = -1;
    slashNode = null;
    slashOpen = false;
    parent.postMessage({ type: 'yarnnn-slash-close' }, '*');
  }

  // slashFromToolbar is DELETED (ADR-586 D1): the toolbar's [+ Add] opens the
  // category menu in the parent on EVERY medium now, so nothing asks the
  // runtime to type a '/'. The typed gesture below is untouched — '/' remains
  // flow's located insert. Deleted rather than left unreachable: a surviving
  // body would be a second insert path waiting to be called (the ADR-506 D1
  // one-sender reasoning that already removed its paged branch).

  // The opener, extracted (ADR-506 D1) so the typed '/' and the toolbar's
  // Insert share ONE body rather than two that drift. Call AFTER the '/' has
  // landed in the DOM; the caret arg is the pre-input caret, used only to pick
  // the anchor element (the post-input re-read below resolves the actual run).
  function openSlashAtCaret(caret) {
    if (!caret) caret = slashCaret();
    if (!caret) return;
    // ADR-480: the palette anchors on the caret's OWN BLOCK, never the edit
    // host — on flow the host is the whole document, whose rect would put the
    // palette at the top of the page instead of beside the line being typed.
    // The block is still the right anchor there; it is an annotation now, not
    // an enclosure, but it is exactly the region the '/' was typed into.
    var cn = caret.startContainer;
    var ce = cn && cn.nodeType === 1 ? cn : (cn ? cn.parentElement : null);
    var anchorEl = editingEl;
    if (FLOW_MODE) {
      anchorEl = (ce && ce.closest ? ce.closest('[data-block]') : null) || flowRoot();
    }
    if (!anchorEl) return;
    var id = FLOW_MODE ? (anchorEl.getAttribute('data-block-id') || null) : editingId;
    var rect = anchorEl.getBoundingClientRect();
    var empty = (anchorEl.textContent || '').trim() === '';
    setTimeout(function () {
      // POST-INPUT: re-read the caret now that the '/' exists in the DOM.
      // The pre-input read bailed on nodeType !== 3 — which is exactly an
      // EMPTY LINE's state at keydown (the caret sits in the element; the
      // text node doesn't exist until the character lands). The gesture's
      // canonical home ("type / on an empty line", this file's own words)
      // was the one place it never fired (2026-07-25). The sentinel's own
      // landing creates the text node; anchor on it after the fact — and,
      // per D11 below, from an element-node caret too (a native flow line).
      var c2 = slashCaret();
      if (!c2) return;
      // ADR-482 D11: resolve the '/'-bearing TEXT NODE from wherever the caret
      // settled. On flow the browser owns the whole-document editable and does
      // not guarantee the caret lands in a text node after input: pressing '/'
      // on a native div line (the block-level element Enter creates on a flow
      // root — see normalizeBlockIds) can leave the caret in the ELEMENT at an
      // offset between its children. The pre-D11 guard bailed on nodeType !== 3,
      // so '/' on exactly those lines dead-ended and the sentinel landed as
      // literal text (verified in prod: a document littered with typed slashes
      // and no palette). The '/' is a POSITION, not a node identity (the same
      // premise D10 applied to slashRun): find the text node that holds it,
      // whether the caret sits IN it or just AFTER it.
      var node = c2.startContainer;
      var at;
      if (node.nodeType === 3) {
        at = c2.startOffset - 1; // caret inside the text node, just past the '/'
      } else {
        // Element-node caret: the '/' is the last char of the text node ending
        // at this offset (the child immediately before startOffset, or its last
        // descendant text node). Walk back to it.
        var prev = c2.startOffset > 0 ? node.childNodes[c2.startOffset - 1] : null;
        while (prev && prev.nodeType === 1) prev = prev.lastChild;
        if (!prev || prev.nodeType !== 3) return;
        node = prev;
        at = (node.textContent || '').length - 1;
      }
      if (at < 0 || (node.textContent || '').charAt(at) !== '/') return;
      slashNode = node;
      slashStart = at;
      slashOpen = true;
      parent.postMessage({ type: 'yarnnn-slash-open', blockId: id, empty: empty,
        rect: { left: rect.left, top: rect.top, bottom: rect.bottom, width: rect.width } }, '*');
    }, 0);
  }

  document.addEventListener('keydown', function (e) {
    if (e.key !== '/' || !editHost()) return;
    // FLOW ONLY. The slash is the gesture of a TEXT CARET IN A LINEAR FLOW, and
    // that is a fact about the medium rather than a preference.
    //
    // ADR-505 D4 made it universal on the strength of "Figma Slides, Pitch and
    // Gamma in the deck class" — and two of those three are false. Figma Slides
    // binds '/' to CURSOR CHAT; Pitch's quick menu is Cmd+K and its docs say so
    // explicitly. Of seven slide editors surveyed only Gamma ships a block
    // insert slash, and Gamma is a card/document hybrid, not a spatial canvas.
    // Webflow and Framer both shipped a slash and both scoped it to rich-text
    // contexts ONLY, deliberately not the canvas — the same line drawn here.
    //
    // On paged, insert is the mouse's: the toolbar's Insert button (discovery)
    // and the right-click row (located), which together restored the ten kinds
    // that were mouse-unreachable while '/' was the sole block-insert route.
    //
    // This is a gate on the MEDIUM, read from the DOM at keypress time — not on
    // an async React value — so it cannot re-open the ADR-482 D3 race: FLOW_MODE
    // is stamped on the served projection before any key can reach this.
    if (!FLOW_MODE) return;
    if (fmtInput && document.activeElement === fmtInput) return;
    var caret = slashCaret();
    if (!caret) return;
    if (caretInIsland()) return; // a citation island owns its own text
    // NO preventDefault + NO exit: the '/' lands and the caret keeps typing.
    openSlashAtCaret(caret);
  }, true);

  // While the palette is open the DOCUMENT still has the caret, so the palette's
  // navigation keys must be intercepted here and forwarded — the palette has no
  // input to focus (focusing one would end the edit the gesture depends on).
  // stopImmediatePropagation, not just preventDefault: the Enter-split handler
  // below is registered on the SAME element in the SAME phase, so preventDefault
  // alone would still let it run and split the block we are picking into — one
  // gesture, two ops, racing on one head.
  document.addEventListener('keydown', function (e) {
    // VISIBILITY, not the anchor. These three keys are stolen from the document
    // only while the member can SEE the palette they steer. After a click-away
    // the anchor is deliberately still live (the press may be the pick), but the
    // palette is gone — and a member pressing Enter to break a line is writing,
    // not picking. Guarding on slashStart swallowed that keystroke once.
    if (!slashOpen) return;
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
    // Only a VISIBLE palette gets re-filtered. The anchor survives a dismiss so
    // a click-pick can still take it, but re-reporting the run would make the
    // dismissed palette pop back open on the member's next keystroke — a menu
    // that returns after you dismissed it reads as broken, not helpful.
    if (!slashOpen) return;
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
  // Partition the HOST block at the caret into BEFORE / AFTER source-inner
  // (citation islands restored via readSourceInner). Returns null if the caret
  // sits in an island (refuse the split). Two clones are truncated by the caret
  // range, then read source-mapped — the same proven path as a plain edit.
  //
  // host is a PARAMETER (2026-07-25): this read editingEl directly, which is
  // null on flow by ADR-480 D1 — so the flow slash-take (its second caller,
  // fixed by ADR-482 D1 to resolve its target from the caret) crashed on
  // cloneNode-of-null and the palette pick silently did nothing, leaving the
  // typed '/' behind. Paged passes editingEl; flow passes the caret's block.
  function splitHalves(host) {
    if (!host) return null;
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount || !sel.isCollapsed) return null;
    if (caretInIsland()) return null;
    var caret = sel.getRangeAt(0);
    var beforeClone = host.cloneNode(true);
    var afterClone = host.cloneNode(true);
    // Map the caret into each clone by walking the same node path.
    function rangeInClone(clone, toEnd) {
      var r = document.createRange();
      // Locate the caret node inside the clone by index path from the host.
      var path = [];
      var node = caret.startContainer;
      while (node && node !== host) {
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
    var halves = splitHalves(editingEl);
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
    // ADR-480 D1 (guard added 2026-07-25): on flow the root is the editor and
    // a double-click means what it means in every editor — word-select. The
    // enter() chokepoint also refuses, but bailing here keeps preventDefault
    // from eating the native selection.
    if (FLOW_MODE) return;
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
    // ADR-546 D5 (F2) — paged grains, null on flow. This runtime already knows
    // the mode, so it answers structurally rather than computing a closest()
    // against markup flow's projection lifted out before load (the pointer
    // runtime's regionOf/arrangeOf hold the same guard for the same reason).
    var slotEl = FLOW_MODE ? null : (el.closest ? el.closest('[data-area], [data-slot]') : null);
    var pageEl = FLOW_MODE ? null : (el.closest ? el.closest('[data-arrange]') : null);
    parent.postMessage({ type: 'yarnnn-point',
      tag: el.tagName.toLowerCase(),
      text: (el.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 120),
      dataRef: el.getAttribute('data-ref') || null,
      blockId: id,
      blockKind: el.getAttribute('data-block') || null,
      slideIndex: null, pageIndex: null,
      slot: slotEl ? (slotEl.getAttribute('data-area') || slotEl.getAttribute('data-slot') || null) : null,
      // ADR-525 D1 — the edit runtime is a separate script, so it derives the
      // tier from its own FLOW_MODE/TEXT_KINDS rather than reaching for the
      // pointer runtime's tierOf. Same rule, stated once per scope.
      tier: (function () {
        var k = el.getAttribute('data-block');
        if (!k) return 'structure';
        return FLOW_MODE && TEXT_KINDS.indexOf(k) !== -1 ? 'text' : 'object';
      })(),
      arrange: pageEl ? (pageEl.getAttribute('data-arrange') || null) : null }, '*');
  }, true);

  window.addEventListener('message', function (e) {
    var d = e.data;
    if (!d || typeof d !== 'object') return;
    if (d.type === 'yarnnn-edit-enter' && typeof d.blockId === 'string') enter(d.blockId);
    else if (d.type === 'yarnnn-edit-exit') exit(false);
    // ── ADR-527 D4 — the PANE drives a range op ───────────────────────────
    //
    // The pane's buttons and the inline bar's buttons are two entrances to ONE
    // applyFmt (the ADR-521 D4 shape). What the pane needs and the bar does not
    // is range PRESERVATION: clicking a pane button moves focus out of the
    // iframe entirely, so the selection is gone by the time the command
    // arrives. The bar solves this with mousedown-preventDefault; across the
    // frame boundary that is unavailable, so the runtime keeps its own last
    // live range and restores it before applying.
    //
    // Refuses when nothing was ever selected — a pane click must never format
    // a range the member cannot see.
    else if (d.type === 'yarnnn-fmt-op' && typeof d.op === 'string') {
      var host = editHost();
      if (!host) return;
      try {
        var s = window.getSelection();
        var live = s && s.rangeCount ? s.getRangeAt(0) : null;
        var usable = live && host.contains(live.commonAncestorContainer) ? live : null;
        if (!usable && lastLiveRange && host.contains(lastLiveRange.commonAncestorContainer)) {
          s.removeAllRanges();
          s.addRange(lastLiveRange);
          usable = lastLiveRange;
        }
        if (!usable) return; // no range to act on — do nothing, silently
        applyFmt(d.op, typeof d.value === 'string' ? d.value : null);
      } catch (err) {}
    }
    // ADR-506 D1 — the toolbar's Insert, routed into the ONE gesture.
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
      // ADR-482 D1: resolve the target from the CARET, mirroring the open path.
      // editingId is null on flow for the same reason editingEl is, so reading
      // it sent the parent a null blockId and its op had nothing to land
      // after. On paged the session variable is still the truth. The resolved
      // block is ALSO the split host (2026-07-25): splitHalves cloned
      // editingEl unconditionally, so every flow pick crashed on
      // cloneNode-of-null — the console's splitHalves TypeError.
      var id = editingId;
      var host = editingEl;
      if (FLOW_MODE) {
        var tn = slashNode.nodeType === 1 ? slashNode : slashNode.parentElement;
        var tblk = tn && tn.closest ? tn.closest('[data-block]') : null;
        id = tblk ? (tblk.getAttribute('data-block-id') || null) : null;
        host = tblk;
      }
      var halves = splitHalves(host); // null host/island → parent falls back
      slashStart = -1;
      slashNode = null;
      slashOpen = false; // the pick consumed the palette; stop stealing keys
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

// ── The object grammar (`paged` only) ─────────────────────────────────────
//
// The direct-manipulation layer for a framed medium: the bounding box with its
// eight handles, the border-band move, group resize, the column divider, and
// the selected block's keyboard. Injected chrome, body-appended (never inside a
// block — commits can't see it). Desktop-pointer only.
//
// ADR-505 D4: THE HOVER GUTTER IS DELETED (all modes). It was ADR-458's Notion
// layer — a `+` and a `⋮⋮` handle beside the hovered block — and ADR-481 D2 had
// already removed it on `flow` (the caret IS the insertion point, so an
// affordance pointing at a place answers a question a continuous surface never
// asks). What remained was a third insert route on `paged` behind `/` and the
// gallery, and web-page editors do not have one. Deleted with it: the `⋮⋮`
// drag-to-reorder (F1) and its drop-line — on `document` reorder is now cut and
// paste in continuous prose (the browser's own, priced and accepted), on
// `deck`/`web` it is the menu's Move up/down. `bindGesture` SURVIVES: it was
// always the shared pointer primitive (ADR-461 D2) and the resize/divider/box
// gestures are its other callers.
//
// The script was named GUTTER_SCRIPT while holding all of the above; the name
// described its first 90 lines and hid the other thousand. Renamed to what it
// is, so a future reader deleting "the gutter" cannot delete deck's object
// grammar by following a stale name.

const OBJECT_SCRIPT = `
(function () {
  if (!window.matchMedia || !window.matchMedia('(hover: hover)').matches) return;
  var PAGE_SEL = '${STRUCTURAL_PAGE_SEL}'; // ADR-511 Phase 2 — the one structural page selector

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
  // The ONE click-suppression authority (ADR-461 D2). Every gesture bound via
  // bindGesture sets this the moment it passes its threshold; the click handler
  // consumes it. One flag, one setter (bindGesture), one consumer — so a second
  // gesture source cannot cross-talk with the first, which is what a per-gesture
  // flag would have produced.
  var gestureSuppressClick = false;
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
   *  its intrinsic ratio; a document or web block has only a viewport to
   *  guess at. This is what decides whether a block gets HANDLES, and it must ask
   *  about the SLIDE (a column inside a document reflows just as its page
   *  does — being a column does not create a frame). */
  function isMeasurable(block) {
    if (!block) return false;
    // ADR-466 P9 grain gate, as amended by ADR-520 D2: a BLOCK is measurable
    // (media anywhere; anything on a stage), and a structural CONTAINER on
    // the stage is too — w/h only, the operator's "the main container is
    // unadjustable" friction. The kernel CSS (.slide [data-w]) never gated
    // on the block grammar; only this function did. A PAGE stays out (the
    // pointer ladder's coarsest grain has its own ops), and an off-stage
    // container keeps no frame, no measure (ADR-461's mode truth).
    if (!block.hasAttribute || !block.hasAttribute('data-block')) {
      return !!(block.matches &&
        block.matches('div[data-block-id]:not([data-block])') &&
        block.closest && block.closest('.slide'));
    }
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
    // ADR-511 Phase 2 — the frame is the nearest structural CONTAINER
    // (identity, no vocabulary); .col/[data-slot] kept as legacy fallbacks
    // for projections that predate the load-normalize.
    var col = block.parentElement && block.parentElement.closest
      ? block.parentElement.closest('div[data-block-id]:not([data-block]), .col, [data-area], [data-slot]')
      : null;
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
   *  no longer disagree, which is what made the gesture unconvergeable.
   *
   *  ADR-485 D7 — on a deck slide the two boxes are now the SAME rectangle:
   *  the stage carries no padding (the inset rides its children), so x and w
   *  are percents of one thing and the green frame IS the slide. The helper
   *  keeps both accessors deliberately: a column or slot frame can still be
   *  padded, and reading a computed style is what makes this self-correcting
   *  rather than a second place that hardcodes a number. */
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
      // ADR-485 D6 — the ORIGIN the content box measures FROM. A denominator
      // without its origin is half a rectangle: the east/south drags divided by
      // contentW/contentH while measuring from the BLOCK's own edge, so a block
      // inset from the content edge could never reach 100%. Named here, beside
      // the box it belongs to, so no caller re-derives it.
      contentLeft: r.left + bl + pl,
      contentTop: r.top + bt + pt,
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
  // ADR-511 D3: one label ladder (structureLabels.ts), inlined — the frame
  // name and the selection chrome speak the same operator words.
  ${labelForJS('frameLabel')}
  function showFrame(frame, txt) {
    if (!frameEl) {
      frameEl = document.createElement('div');
      frameEl.className = 'yarnnn-frame';
      document.body.appendChild(frameEl);
    }
    // ADR-485 D6 — THE OVERLAY DRAWS THE RECTANGLE THE MATH USES. This drew
    // frame.getBoundingClientRect() (the BORDER box) while every percent
    // resolves against the CONTENT box, so the green outline was larger than
    // the area a measure can address — by exactly the frame's padding. The
    // member aimed at the green edge, the clamp stopped them short of it, and
    // the affordance and the constraint were two different rectangles.
    //
    // frameRects is the one place the box model is answered (D1); this was its
    // fifth reader and the only one that bypassed it. Now the green outline IS
    // 100%: reaching it and committing 100 are the same act.
    var f = frameRects(frame);
    var z = zf();
    // txt null = at-rest context (the frame's NAME alone rides the selection);
    // a live gesture appends its numbers — "side · 62% × 40%".
    frameEl.setAttribute('data-label', txt ? frameLabel(frame) + ' · ' + txt : frameLabel(frame));
    frameEl.style.display = 'block';
    frameEl.style.left = ((f.contentLeft + window.scrollX) / z) + 'px';
    frameEl.style.top = ((f.contentTop + window.scrollY) / z) + 'px';
    frameEl.style.width = (f.contentW / z) + 'px';
    frameEl.style.height = (f.contentH / z) + 'px';
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
  // The group's members and their fixed offsets from the dragged block, held
  // for the duration of one move gesture (see the strip's onStart).
  var groupRide = [];

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
    // The riders follow at their captured offsets, in the SAME frame space and
    // clamped by the SAME rule — a group member may not leave the frame just
    // because the block being dragged is still inside it.
    for (var ri = 0; ri < groupRide.length; ri++) {
      var rd = groupRide[ri];
      var rr = rd.el.getBoundingClientRect();
      var rwPct = (rr.width / f.padW) * 100;
      var rhPct = (rr.height / f.padH) * 100;
      var rx = ((e.clientX - grabDX + rd.dx - f.padLeft) / f.padW) * 100;
      var ry = ((e.clientY - grabDY + rd.dy - f.padTop) / f.padH) * 100;
      rd.el.style.position = 'absolute';
      rd.el.style.left = Math.max(0, Math.min(Math.max(0, 100 - rwPct), rx)) + '%';
      rd.el.style.top = Math.max(0, Math.min(Math.max(0, 100 - rhPct), ry)) + '%';
      rd.el.style.margin = '0';
    }
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
    // A group drop is ONE act, so it posts ONE message carrying every member's
    // landed position — the parent folds them into a single revision. Posting
    // N geometry messages would race the optimistic write and make the history
    // read as N drags nobody performed.
    if (groupRide.length) {
      var moves = [{ blockId: id, x: Math.round(xRaw), y: Math.round(yRaw) }];
      for (var mi = 0; mi < groupRide.length; mi++) {
        var mel = groupRide[mi].el;
        var mid = mel.getAttribute('data-block-id');
        if (!mid) continue;
        var mr = mel.getBoundingClientRect();
        var mwPct = (mr.width / f.padW) * 100;
        var mhPct = (mr.height / f.padH) * 100;
        moves.push({
          blockId: mid,
          x: Math.round(Math.max(0, Math.min(Math.max(0, 100 - mwPct), ((mr.left - f.padLeft) / f.padW) * 100))),
          y: Math.round(Math.max(0, Math.min(Math.max(0, 100 - mhPct), ((mr.top - f.padTop) / f.padH) * 100))),
        });
      }
      groupRide = [];
      parent.postMessage({ type: 'yarnnn-geometry-many', moves: moves }, '*');
      syncFrameContext();
      return;
    }
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

  // ── GROUP RESIZE (2026-07-24) — the Figma model ────────────────────────
  // Figma resizes a multi-selection PROPORTIONALLY WITHIN ITS BOUNDING BOX:
  // every member's position and size scale by the same ratio relative to that
  // box, so the set's internal layout is preserved. It scales the BOX, never
  // the type — a text block gets wider, its font does not grow (that is
  // Figma's own distinction between resizing a frame and scaling it, and it is
  // the only one expressible here: the kernel has w/h measures and no scale
  // transform, so "each member's own w/h" is both the Figma behaviour and the
  // only honest one).
  //
  // Captured ONCE at gesture start, for the same reason the move's offsets
  // are: recomputing the union per frame would feed each frame's rounding
  // into the next and let the set creep.
  var groupResize = null;
  function captureGroupResize(primary) {
    var set = window.__yarnnnGroup ? window.__yarnnnGroup() : [];
    if (set.length < 2) { groupResize = null; return; }
    var members = [];
    var minL = Infinity, minT = Infinity, maxR = -Infinity, maxB = -Infinity;
    for (var i = 0; i < set.length; i++) {
      if (!positionable(set[i])) continue;
      var r = set[i].getBoundingClientRect();
      members.push({ el: set[i], r: r });
      if (r.left < minL) minL = r.left;
      if (r.top < minT) minT = r.top;
      if (r.right > maxR) maxR = r.right;
      if (r.bottom > maxB) maxB = r.bottom;
    }
    if (members.length < 2) { groupResize = null; return; }
    groupResize = {
      primary: primary,
      box: { left: minL, top: minT, width: Math.max(1, maxR - minL), height: Math.max(1, maxB - minT) },
      members: members,
    };
  }
  // Apply the primary's scale to every member, about the box's anchored corner.
  // sx/sy are the ratios the primary's own drag produced; the anchor is the
  // edge the handle did NOT move (a west drag anchors the box's right edge).
  function applyGroupResize(f, sx, sy, anchorX, anchorY) {
    if (!groupResize) return;
    var g = groupResize;
    for (var i = 0; i < g.members.length; i++) {
      var m = g.members[i];
      var nl = anchorX + (m.r.left - anchorX) * sx;
      var nt = anchorY + (m.r.top - anchorY) * sy;
      var nw = m.r.width * sx;
      var nh = m.r.height * sy;
      m.el.style.position = 'absolute';
      m.el.style.margin = '0';
      m.el.style.left = Math.max(0, Math.min(100, ((nl - f.padLeft) / f.padW) * 100)) + '%';
      m.el.style.top = Math.max(0, Math.min(100, ((nt - f.padTop) / f.padH) * 100)) + '%';
      m.el.style.width = Math.max(MEASURE_MIN.w, Math.min(MEASURE_MAX.w, (nw / f.contentW) * 100)) + '%';
      m.el.style.height = Math.max(MEASURE_MIN.h, Math.min(MEASURE_MAX.h, (nh / f.contentH) * 100)) + '%';
    }
  }

  function resizeMove(block, e, side) {
    var frame = measurableFrame(block);
    if (!frame) return;
    var br = block.getBoundingClientRect();
    // A group resize scales the whole set about the anchored corner; the
    // primary is one member of it, so its own branch below is skipped.
    if (groupResize) {
      var gf = frameRects(frame);
      var gax = sideAxes(side);
      var b = groupResize.box;
      var ancX = gax.west ? b.left + b.width : b.left;
      var ancY = gax.north ? b.top + b.height : b.top;
      var sx = 1, sy = 1;
      if (gax.west) sx = Math.max(0.05, (ancX - e.clientX) / b.width);
      else if (gax.east) sx = Math.max(0.05, (e.clientX - ancX) / b.width);
      if (gax.north) sy = Math.max(0.05, (ancY - e.clientY) / b.height);
      else if (gax.south) sy = Math.max(0.05, (e.clientY - ancY) / b.height);
      applyGroupResize(gf, sx, sy, ancX, ancY);
      showBox(block);
      showFrame(frame, Math.round(sx * 100) + '% × ' + Math.round(sy * 100) + '%');
      return;
    }
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
        // ADR-485 D6 — the EAST drag's origin. br.left is the BLOCK's edge;
        // f.contentW is the FRAME's content width. Mixing them measures a
        // width from one rectangle and divides it by another, so a block that
        // sits inset from the content-left (every flow block in a padded
        // container, and any block a .col gap offsets) can never reach 100%:
        // dragging to the frame's true right edge yields only
        // (contentRight − blockLeft)/contentW, short by exactly the inset.
        // maxPct = 100 never bound, because the value never got there — the
        // member ran out of green before running out of percent.
        //
        // The west branch above was already frame-relative; this is the same
        // arithmetic, made consistent. Measure from the CONTENT-LEFT origin so
        // the numerator and the denominator describe one rectangle.
        pct = ((e.clientX - f.contentLeft) / f.contentW) * 100;
        // A positioned block's width is bounded by the room to its right —
        // (100 − x%); a flow block by the frame itself (100%).
        maxPct = positioned
          ? 100 - ((br.left - f.contentLeft) / f.contentW) * 100
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
        // ADR-485 D6 — the SOUTH drag's origin, the width defect's twin.
        // Same rule: measure from the frame's content-top, not the block's own.
        hpct = ((e.clientY - f.contentTop) / f.contentH) * 100;
        hMax = positioned
          ? 100 - ((br.top - f.contentTop) / f.contentH) * 100
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
    if (!moved) { groupResize = null; syncFrameContext(); return; }
    var id = block.getAttribute('data-block-id');
    var frame = measurableFrame(block);
    if (!id || !frame) { groupResize = null; syncFrameContext(); return; }
    var br = block.getBoundingClientRect();
    // A group resize commits every member's LANDED rect — read back from the
    // DOM rather than recomputed from the scale, so what is written is what
    // the member saw (the clamps in applyGroupResize already ran). One
    // message, one revision, exactly as the group move does.
    if (groupResize) {
      var gf = frameRects(frame);
      var gmoves = [];
      for (var gi = 0; gi < groupResize.members.length; gi++) {
        var gel = groupResize.members[gi].el;
        var gid = gel.getAttribute('data-block-id');
        if (!gid) continue;
        var gr = gel.getBoundingClientRect();
        gmoves.push({
          blockId: gid,
          x: Math.round(clampMeasure('x', ((gr.left - gf.padLeft) / gf.padW) * 100)),
          y: Math.round(clampMeasure('y', ((gr.top - gf.padTop) / gf.padH) * 100)),
          w: Math.round(clampMeasure('w', (gr.width / gf.contentW) * 100)),
          h: Math.round(clampMeasure('h', (gr.height / gf.contentH) * 100)),
        });
      }
      groupResize = null;
      if (gmoves.length) parent.postMessage({ type: 'yarnnn-geometry-many', moves: gmoves }, '*');
      syncFrameContext();
      return;
    }
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
          // The group rides the PRIMARY's delta: capture each member's offset
          // from the dragged block once, then hold it for the whole gesture.
          // Recomputing per frame would compound rounding and let the set
          // drift apart mid-drag.
          groupRide = [];
          var set = window.__yarnnnGroup ? window.__yarnnnGroup() : [];
          for (var gi = 0; gi < set.length; gi++) {
            if (set[gi] === block || !positionable(set[gi])) continue;
            var gr = set[gi].getBoundingClientRect();
            groupRide.push({ el: set[gi], dx: gr.left - br.left, dy: gr.top - br.top });
          }
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
        onStart: function (block) { captureGroupResize(block); previewContext(block); },
        onMove: function (block, ev) { resizeMove(block, ev, side); },
        onEnd: function (block, moved) { resizeEnd(block, moved, side); },
      });
    });
    return box;
  }

  // ADR-516 D5: a structural container (identity, no vocabulary) is a
  // selection subject (ADR-511 D3) and earns the box — the static, handle-less
  // variant. Same selector the pointer runtime's rung uses.
  function isContainerEl(el) {
    return !!(el && el.matches && el.matches('div[data-block-id]:not([data-block])'));
  }

  // ADR-613 — the selection's VISUAL box, posted for the parent-side judged
  // gesture. Iframe-viewport coordinates (the clientX/Y space), so the parent
  // offsets by the iframe's page position with NO zoom multiply — the mapping
  // proven at StudioCanvas's context-menu bridge. Do NOT divide by zf() here:
  // that is only correct for body-appended chrome inside the zoomed document
  // (the format bar), and dividing would put the door at ~37% of the offset on
  // a deck.
  // The CONTENT the selection sits in — the box the door must hang OUTSIDE of.
  //
  // The parent cannot compute this. Its only handle is the iframe element,
  // which is w-full h-full and so spans the whole canvas column; a staged
  // artifact (a deck slide, an image template) is letterboxed inside it at
  // fitScale. Measuring the margin against the IFRAME therefore places the
  // door past the canvas entirely, on top of the properties pane — the defect
  // this reports its way out of. Only the runtime knows where the stage
  // actually is, so the runtime is what says so.
  //
  // Same iframe-viewport space and the same no-zoom rule as the selection rect
  // itself: the parent adds the iframe's page offset and multiplies nothing.
  // Falls back to the document element for a fluid artifact, where the content
  // genuinely does fill the frame.
  function contentBox(el) {
    var stage = el && el.closest ? el.closest('.slide, [data-stage]') : null;
    var host = stage || document.documentElement;
    return host.getBoundingClientRect();
  }

  var lastSelRectKey = '';
  function postSelectionRect(rect, grain, subject) {
    if (!rect || (rect.width === 0 && rect.height === 0)) {
      if (lastSelRectKey === '') return;
      lastSelRectKey = '';
      parent.postMessage({ type: 'yarnnn-selection-rect', rect: null }, '*');
      return;
    }
    var c = contentBox(subject);
    var key = grain + ':' + Math.round(rect.left) + ',' + Math.round(rect.top)
      + ',' + Math.round(rect.right) + ',' + Math.round(rect.bottom)
      + '|' + Math.round(c.left) + ',' + Math.round(c.right);
    if (key === lastSelRectKey) return;
    lastSelRectKey = key;
    parent.postMessage({
      type: 'yarnnn-selection-rect',
      grain: grain,
      rect: {
        left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom,
      },
      content: { left: c.left, right: c.right },
    }, '*');
  }
  window.__yarnnnPostSelRect = postSelectionRect;

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
    postSelectionRect(r, 'object', block);
    // The band is honest about inertness: no move cursor where no move exists.
    if (isContainerEl(block)) {
      // ADR-520 D2: a STAGED container is adjustable — handles live, move
      // band still hidden (move stays reorder-shaped; a container is never
      // positioned). Off the stage it keeps ADR-516 D5's static box.
      box.className = block.closest && block.closest('.slide')
        ? 'yarnnn-selbox yarnnn-selbox-container-sizable'
        : 'yarnnn-selbox yarnnn-selbox-static yarnnn-selbox-container';
      return;
    }
    box.className = positionable(block)
      ? 'yarnnn-selbox'
      : 'yarnnn-selbox yarnnn-selbox-static';
    // ADR-511 D4 — positioned state is LEGIBLE: an out-of-flow block wears a
    // corner tag, so absolute is a visible, deliberate exception (flow is the
    // default). The Design tab's Position row is the reversal affordance.
    if (block.hasAttribute('data-x') && block.hasAttribute('data-y')) {
      box.className += ' yarnnn-selbox-abs';
    }
  }
  function hideBox() {
    if (box) box.style.display = 'none';
    selBlock = null;
    hideFrame();
    // ADR-613 — no subject, no door. Clearing here (rather than only on an
    // explicit deselect) keeps the parent's gesture bound to what is actually
    // selected, including the scroll/resize paths syncBox already drives.
    postSelectionRect(null, null);
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
  // They lived here only by historical accident, and the object script is not
  // injected on flow (ADR-481 D2) — so on every document the right-click menu
  // advertised shortcut hints for keys that did nothing. An affordance's
  // injection site must follow its LIFETIME, not the script it was first
  // written into. The gutter keeps what is genuinely gutter: '+', ⋮⋮, selbox.

  // ── Undo / Redo MOVED (2026-07-31) ───────────────────────────────────────
  // It lived here, in the paged-only OBJECT_SCRIPT, so ⌘Z simply DID NOT EXIST
  // on a document: no producer, and the parent has no keyboard listener of its
  // own (the canvas is an opaque-origin frame, so the key never leaves it).
  // Meanwhile every structural op kept pushing snapshots onto a stack nobody
  // could pop. Its injection site now follows its LIFETIME — the same rule the
  // keyboard verbs above were re-homed by — so it sits in the pointer runtime,
  // which is injected on BOTH modes. See "Undo / Redo" there.

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
    // ADR-520 D1: a target on a HIDDEN slide (the stage shows one at a time)
    // has no client rect — a box around it would be a 0×0 lie at the origin.
    var visible = target && target.isConnected &&
      target.getClientRects && target.getClientRects().length > 0;
    if (visible && (isMeasurable(target) || isContainerEl(target))) {
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
    /** ADR-544 D4 — the SERVED kind→label map (`vocabulary.blocks`). The chrome
     *  says the registry's word ("Text"), never the substrate's attribute
     *  ("prose"). Same reasoning as `measureBounds` directly above: the runtime
     *  must never invent an operator-facing word, so the parent passes what the
     *  registry served. Omitted → labels degrade to the raw kind, which is the
     *  pre-544 behaviour and visibly wrong rather than silently plausible. */
    blockLabels?: Record<string, string>;
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
      section.querySelectorAll('[data-area], [data-slot]').forEach((slot) => {
        while (slot.firstChild) slot.parentNode?.insertBefore(slot.firstChild, slot);
        slot.remove();
      });
      while (section.firstChild) parent.insertBefore(section.firstChild, section);
      section.remove();
    });
  }
  // ── ADR-511 D3: stamp operator-word labels on structural containers ─────
  // The inert-slot marking pass that lived here is DELETED — it existed to
  // hide a grain that offered "the layout master as an object with none of an
  // object's affordances." Containers now HAVE affordances (selection, the
  // id-addressed ops, layout properties), so the clash it papered over —
  // chrome that named a region the member could not act on — dissolves the
  // honest direction: what the frame names, the member can select.
  //
  // This pass stamps `data-yarnnn-label` (render-side chrome only — the
  // projected doc, never the source; flow edits can't leak it because flow
  // flattens containers above, and paged edits commit per-block inners) so
  // the hover cue's CSS can speak operator words via attr(). The predicate
  // matches normalizeStructure's pass B: a div holding blocks, outside any
  // block/citation.
  if (opts?.mode === 'paged') {
    doc.querySelectorAll('div').forEach((el) => {
      if (el.hasAttribute('data-block') || el.hasAttribute('data-ref')) return;
      if (el.parentElement?.closest('[data-block], [data-ref]')) return;
      if (!el.querySelector('[data-block]') && !el.hasAttribute('data-area') && !el.hasAttribute('data-slot')) return;
      el.setAttribute('data-yarnnn-label', labelForElement(el));
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
      // The format bar's sheet rides the edit runtime on BOTH grains
      // (2026-07-25 — it was orphaned on flow when D4 scoped EDIT_CSS).
      (opts?.edit ? FMT_CSS : '') +
      // ADR-482 D4: the 2px indigo EDIT outline says "this object is live" —
      // true when one block at a time is editable, meaningless on a continuous
      // surface where contenteditable lands on main/article and the selector
      // cannot match. Paged-only, so the intent is legible not accidental.
      (opts?.edit && paged ? EDIT_CSS : '');
    doc.head?.appendChild(style);
    // ADR-544 D4 — the served labels land BEFORE any runtime that labels with
    // them. EDIT_SCRIPT is injected ahead of POINTER_SCRIPT and both inline
    // `labelForJS`, so the global cannot ride the pointer payload alone.
    const labelData = doc.createElement('script');
    labelData.textContent = `window.__yarnnnBlockLabels = ${JSON.stringify(
      opts?.blockLabels ?? null,
    )};`;
    doc.body?.appendChild(labelData);
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
      // The object grammar (after the pointer — it uses the pointer's
      // __yarnnnSelect + the edit runtime's __yarnnnEditingId).
      //
      // `paged` ONLY, and now for the ORIGINAL reason rather than the gutter's:
      // this script draws the bounding box, the handles and the divider — the
      // chrome of a medium where a block is an ENCLOSURE (ADR-480). On `flow` a
      // block is an annotation, the browser owns the caret, and there is no
      // object to box. ADR-505 D4 deleted the gutter that used to ride along
      // here; what remains is geometry, and geometry needs a frame.
      const objects = doc.createElement('script');
      objects.textContent = OBJECT_SCRIPT;
      doc.body?.appendChild(objects);
    }
  }
  const doctype = '<!doctype html>\n';
  return doctype + (doc.documentElement?.outerHTML ?? html);
}

/**
 * ADR-524 D3 — project ONE block, for the patch channel.
 *
 * The patch path exists so a one-block change stops re-parsing the whole
 * document (D1). But a patch must never be raw source: the canvas iframe is
 * `allow-scripts` on an opaque origin precisely because THIS pass is what
 * strips artifact-authored executables, and the citation contract (ADR-446 D3)
 * requires `data-src-html` to be stamped BEFORE resolution or the source form
 * is unrecoverable at commit time. So the patch payload comes from here — the
 * same transforms as the full pass, scoped to a single block — never from
 * markup assembled parent-side.
 *
 * What this deliberately does NOT do, because the live frame already has it:
 * head/style injection, runtime script injection, flow flattening (a structural
 * re-parent — not block-local, and flow edits are not patchable per D2), and
 * the paged container labelling (it stamps ancestors, not the block).
 *
 * Returns null when the block is not found or carries no id — the caller then
 * falls back to a full swap, which is always correct.
 */
export async function projectBlock(
  html: string,
  blockId: string,
  artifactPath: string,
): Promise<string | null> {
  if (!html || !blockId) return null;
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const block = doc.querySelector(`[data-block-id="${CSS.escape(blockId)}"]`);
  if (!block) return null;

  // Citation islands INSIDE this block get the same stamp-then-resolve order as
  // the full pass. The block itself can be a citation (a figure with data-ref),
  // so the scope is self-or-descendant, not just descendants.
  const cited: Element[] = [];
  if (block.hasAttribute('data-ref')) cited.push(block);
  cited.push(...Array.from(block.querySelectorAll('[data-ref]')));
  cited.forEach((el) => {
    if (el.tagName === 'STYLE') return; // never a style element (ADR-462 D13)
    el.setAttribute('data-src-html', encodeURIComponent(el.outerHTML));
  });
  await Promise.all(cited.map((el) => resolveOne(el, artifactPath)));

  // The security floor: the same strip the full pass applies, over this
  // subtree. `stripExecutable` takes a Document, so run it on a detached doc
  // holding only this block — the patch must not be able to smuggle a script
  // into a frame that runs scripts.
  const carrier = document.implementation.createHTMLDocument('');
  carrier.body.appendChild(carrier.importNode(block, true));
  stripExecutable(carrier);
  return carrier.body.firstElementChild?.outerHTML ?? null;
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
