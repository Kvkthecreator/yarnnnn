/**
 * resolveArtifactHtml — the Studio's reference projection pass (ADR-440 D5).
 *
 * A Studio artifact cites workspace objects by REFERENCE (`data-ref` = the
 * living path, `data-ref-rev` = the last-resolved pin), never by copy. This
 * pass runs before the canvas renders: it walks the artifact's HTML, resolves
 * every citation against the commons, and rewrites the element so a fully
 * sandboxed iframe (no scripts, no network reach into the API) can display it.
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

import { api } from '@/lib/api/client';

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

// ── The pointer runtime (ADR-440 v1.1 — pointing) ─────────────────────────
//
// Injected into the projected document so the member can POINT at an element
// (deixis, never editing): a click selects the nearest pointable element,
// outlines it, and posts {type:'yarnnn-point', tag, text, dataRef} to the
// parent (StudioCanvas listens). Runs under sandbox="allow-scripts" with an
// OPAQUE origin — no same-origin access, no credentials, no top-navigation.
// The projection pass strips every artifact-authored script and inline
// handler first (D5's no-script rule, enforced mechanically), so this is the
// ONLY code that executes in the canvas.

const POINTABLE =
  'h1,h2,h3,h4,p,li,img,figure,figcaption,table,blockquote,pre,[data-ref]';

const POINTER_CSS = `
${POINTABLE.split(',').map((s) => `${s}:hover`).join(',')} {
  outline: 1px dashed rgba(99,102,241,0.45); outline-offset: 2px; cursor: pointer;
}
.yarnnn-pointed { outline: 2px solid #6366f1 !important; outline-offset: 2px; }
`;

const POINTER_SCRIPT = `
(function () {
  var SEL = ${JSON.stringify(POINTABLE)};
  var cur = null;
  document.addEventListener('click', function (e) {
    var t = e.target;
    var el = t && t.closest ? t.closest(SEL) : null;
    e.preventDefault();
    if (!el) {
      if (cur) { cur.classList.remove('yarnnn-pointed'); cur = null; }
      parent.postMessage({ type: 'yarnnn-point-clear' }, '*');
      return;
    }
    if (cur) cur.classList.remove('yarnnn-pointed');
    cur = el;
    el.classList.add('yarnnn-pointed');
    var text = (el.getAttribute('alt') || el.textContent || '')
      .replace(/\\s+/g, ' ').trim().slice(0, 120);
    parent.postMessage({
      type: 'yarnnn-point',
      tag: el.tagName.toLowerCase(),
      text: text,
      dataRef: el.getAttribute('data-ref') || null,
    }, '*');
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
 *  authored executables and injects the pointer runtime. */
export async function resolveArtifactHtml(
  html: string,
  artifactPath: string,
  opts?: { pointer?: boolean },
): Promise<string> {
  if (!html) return html;
  if (!opts?.pointer && !html.includes('data-ref')) return html;
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const cited = Array.from(doc.querySelectorAll('[data-ref]'));
  await Promise.all(cited.map((el) => resolveOne(el, artifactPath)));
  if (opts?.pointer) {
    stripExecutable(doc);
    const style = doc.createElement('style');
    style.textContent = POINTER_CSS;
    doc.head?.appendChild(style);
    const script = doc.createElement('script');
    script.textContent = POINTER_SCRIPT;
    doc.body?.appendChild(script);
  }
  const doctype = '<!doctype html>\n';
  return doctype + (doc.documentElement?.outerHTML ?? html);
}
