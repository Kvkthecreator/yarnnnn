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
 * moat depends on. Recording the export itself as a `revision_kind="derivation"`
 * is the opt-in follow-on named in §13; it is not built here.
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

/** Read the stage's real pixel dimensions from the projected root's markers
 *  (`data-w`/`data-h` on <html>, ADR-472 D3). Falls back to the ad default. */
function stageDimensions(doc: Document): { width: number; height: number } {
  const root = doc.documentElement;
  const w = Number(root.getAttribute('data-w'));
  const h = Number(root.getAttribute('data-h'));
  return {
    width: Number.isFinite(w) && w > 0 ? w : 1200,
    height: Number.isFinite(h) && h > 0 ? h : 628,
  };
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
 * Rasterize the artifact at `artifactPath` (its `content` HTML) to a PNG and
 * download it. Renders at the stage's real dimensions × 2 for a crisp export.
 *
 * @param content       the artifact's authored HTML
 * @param artifactPath  its workspace path (for citation resolution)
 * @param filename      the download name (without extension is fine)
 */
export async function exportArtifactPng(
  content: string,
  artifactPath: string,
  filename: string,
): Promise<void> {
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
    const dataUri = await toPng(host, {
      width,
      height,
      pixelRatio: 2,
      // The container already carries the stage background; make it explicit so
      // a transparent stage exports on white rather than the page behind it.
      backgroundColor: '#ffffff',
      cacheBust: true,
    });
    downloadDataUri(dataUri, filename);
  } finally {
    host.remove();
  }
}
