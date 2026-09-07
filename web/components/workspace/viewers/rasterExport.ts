/**
 * Client-side raster export (ADR-475 §13).
 *
 * The IMAGES app's artifact is a rendered raster, but the raster is not the
 * SOURCE — the layered, attributed composition is (D4). Export is therefore a
 * PROJECTION: the member's browser rasterizes the stage it is already
 * displaying and hands the PNG to the outside world (Instagram does not read
 * our ledger). The server rasterizer was removed (§13) — it only ever 503'd in
 * a container with no headless browser — so this is the whole export path.
 *
 * The moat is untouched: provenance lives in the composition (`trace` walks the
 * layered source), not in the flat PNG. A client download loses nothing the
 * moat depends on.
 *
 * TWO destinations for the same raster (2026-09-07, the §13 opt-in built):
 *   - `exportArtifactPng` — a browser download, for the outside world;
 *   - `saveArtifactPng`   — the SAME bytes POSTed back and landed beside the
 *     artboard as a `revision_kind="derivation"` citing it, so a markdown
 *     document can refer to the picture by path (`![alt](…/exports/x.png)`,
 *     ADR-572 D17). Before this the artboard's raster never entered the
 *     workspace at all, and "make an image, put it in a document" was
 *     unbuildable by construction.
 * One rasterizer feeds both; the destination is the only difference.
 *
 * Why not go through the canvas iframe: the Studio canvas is sandboxed
 * `allow-scripts` only (a deliberate security boundary — the parent cannot
 * reach its DOM). So we re-project the artifact into an OWN off-screen,
 * un-sandboxed container (the same technique `exportPrint` uses for Print/PDF)
 * and rasterize that.
 *
 * The canvas-taint problem (the reason this is a real pass, not a one-liner):
 * a cited raster binary (a generated ad hero) resolves to a cross-origin
 * Supabase signed URL (projection.resolveOne). Drawing a cross-origin image
 * onto a canvas TAINTS it, and a tainted canvas refuses `toDataURL`/`toBlob`.
 * We do not depend on the storage bucket's CORS config: we re-fetch every such
 * image as a blob (a `fetch()` carries the signed URL fine) and swap it for a
 * same-origin `data:` URI BEFORE rasterizing. SVG/CSV citations already resolve
 * to data URIs upstream, so only the binary `<img>`/`background-image` sources
 * need this pass.
 */
import { toPng } from 'html-to-image';

import { resolveArtifactHtml } from './projection';
import { readStageSize } from '@/components/authoring/stageGeometry';

/** Read the stage's real pixel dimensions off the projected document.
 *
 *  This used to read ONLY `data-w`/`data-h` (the markers an IMAGES stage root
 *  carries, ADR-472 D3) and fall back to a 1200×628 ad default. A DECK carries
 *  no such markers, so every deck raster export silently rasterized at 1200×628
 *  — the wrong aspect ratio for a 16:9 slide, and nothing reported it.
 *
 *  `readStageSize` consults the geometry the file actually carries
 *  (`--stage-w`/`--stage-h`, then the markers) and falls back per template, so
 *  a deck exports at its true stage. */
function stageDimensions(doc: Document, template?: string | null): { width: number; height: number } {
  return readStageSize(doc, template ?? doc.documentElement.getAttribute('data-template'));
}

/** Fetch a (possibly cross-origin, signed) URL and return it as a `data:` URI.
 *  A `fetch()` can reach the signed URL; the resulting data URI is same-origin
 *  to the canvas, so it never taints. Returns the original URL untouched on any
 *  failure — a missing image degrades the export, it never throws it. */
async function toDataUri(url: string): Promise<string> {
  if (!url || url.startsWith('data:')) return url;
  try {
    const res = await fetch(url, { mode: 'cors' });
    if (!res.ok) return url;
    const blob = await res.blob();
    return await new Promise<string>((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.onerror = () => resolve(url);
      reader.readAsDataURL(blob);
    });
  } catch {
    return url;
  }
}

/** Re-inline every cross-origin raster source (img `src`, CSS `background-image`)
 *  in the mounted node as a `data:` URI, so the rasterizer's canvas stays clean.
 *  Mutates the live DOM in place (it is our throwaway export container). */
async function inlineRasterSources(node: HTMLElement): Promise<void> {
  const jobs: Promise<void>[] = [];

  node.querySelectorAll('img').forEach((img) => {
    const src = img.getAttribute('src') || '';
    if (!src || src.startsWith('data:')) return;
    // crossOrigin lets the fetched-then-data-URI'd image decode without taint;
    // harmless on a data: URI, load-bearing if a source ever slips through.
    img.crossOrigin = 'anonymous';
    jobs.push(toDataUri(src).then((uri) => img.setAttribute('src', uri)));
  });

  node.querySelectorAll<HTMLElement>('*').forEach((el) => {
    const bg = el.style?.backgroundImage || '';
    const m = /url\(["']?([^"')]+)["']?\)/.exec(bg);
    const url = m?.[1];
    if (!url || url.startsWith('data:')) return;
    jobs.push(
      toDataUri(url).then((uri) => {
        el.style.backgroundImage = `url("${uri}")`;
      }),
    );
  });

  await Promise.all(jobs);
}

/** Trigger a browser download of the data URI as `<name>.png`. */
function downloadDataUri(dataUri: string, filename: string): void {
  const a = document.createElement('a');
  a.href = dataUri;
  a.download = filename.endsWith('.png') ? filename : `${filename}.png`;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

/**
 * Rasterize the artifact at `artifactPath` (its `content` HTML) to a PNG data
 * URI at the stage's real dimensions × 2 (a crisp export). The ONE rasterizer;
 * `exportArtifactPng` and `saveArtifactPng` only differ in where it goes.
 *
 * @param content       the artifact's authored HTML
 * @param artifactPath  its workspace path (for citation resolution)
 */
export async function rasterizeArtifactPng(content: string, artifactPath: string): Promise<string> {
  // Resolve citations + strip executables (no `pointer` — we want the clean
  // rendered artifact, not the edit runtime). Same call `exportPrint` makes.
  const projected = await resolveArtifactHtml(content, artifactPath, {});
  const doc = new DOMParser().parseFromString(projected, 'text/html');
  const { width, height } = stageDimensions(doc);

  // Mount the projected BODY into an off-screen, un-sandboxed container sized
  // to the stage. We carry the <head>'s styles across (the skin + kernel CSS
  // live there) so the raster matches what the canvas shows.
  const host = document.createElement('div');
  host.style.cssText =
    `position:fixed;left:-99999px;top:0;width:${width}px;height:${height}px;` +
    'overflow:hidden;background:#fff;pointer-events:none;';
  // Preserve author styles: replay every <style> from the projected head, then
  // the body content. (A <link> would be cross-origin/async; the projection
  // inlines its CSS as <style>, so this captures it all.)
  const headStyles = Array.from(doc.head?.querySelectorAll('style') ?? [])
    .map((s) => s.outerHTML)
    .join('');
  host.innerHTML = headStyles + (doc.body?.innerHTML ?? '');
  document.body.appendChild(host);

  try {
    await inlineRasterSources(host);
    // Give re-inlined images a tick to decode before the snapshot.
    await new Promise((r) => setTimeout(r, 50));
    return await toPng(host, {
      width,
      height,
      pixelRatio: 2,
      // The container already carries the stage background; make it explicit so
      // a transparent stage exports on white rather than the page behind it.
      backgroundColor: '#ffffff',
      cacheBust: true,
      // ⭐ The CLONE must not inherit the host's off-screen position. html-to-image
      // copies the node's computed style onto the clone it draws inside an SVG
      // foreignObject — including `position: fixed; left: -99999px` — so the
      // whole stage rendered 99,999px outside the canvas and every export was a
      // blank white PNG. Nobody saw it while the raster only ever left as a
      // download; the first one that LANDED in the workspace (2026-09-07) was
      // sampled: 0 non-white pixels of 291,600. These override the clone only;
      // the live host stays off-screen.
      style: { position: 'static', left: '0', top: '0' },
    });
  } finally {
    host.remove();
  }
}

/** Rasterize and hand the PNG to the browser as a download (the outside world). */
export async function exportArtifactPng(
  content: string,
  artifactPath: string,
  filename: string,
): Promise<void> {
  downloadDataUri(await rasterizeArtifactPng(content, artifactPath), filename);
}

/**
 * Rasterize and land the PNG IN the workspace, beside the artboard, as a
 * derivation of it (ADR-475 §13, built). Returns the path it landed at —
 * stable across re-exports (`{artboard folder}/exports/{artboard}.png`), so a
 * second export is a new REVISION of the same file, never a second file, and a
 * document citing it keeps resolving.
 */
export async function saveArtifactPng(content: string, artifactPath: string): Promise<string> {
  const dataUri = await rasterizeArtifactPng(content, artifactPath);
  const blob = await (await fetch(dataUri)).blob();
  const { api } = await import('@/lib/api/client');
  const res = await api.images.exportPng(blob, artifactPath);
  return res.path;
}
