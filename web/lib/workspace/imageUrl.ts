/**
 * resolveWorkspaceImageUrl — the ONE resolver for a markdown image whose
 * `src` is a workspace path (ADR-572 D17; ADR-590 D5).
 *
 * `![alt](marketing/assets/hero.png)` is native markdown, and the bytes are a
 * real substrate file — but a workspace path is not a URL a browser can
 * fetch, and the CAS serving URL is minted per request with a 1-hour TTL
 * (ADR-427 D4), so it cannot be baked into the file either. The `.md` keeps
 * the portable PATH; the viewer mints its own access, per read.
 *
 * ONE resolver, because the image is drawn on TWO faces that must not drift:
 * the reading face (`MarkdownRenderer`, which the thumbnail and Print/PDF use)
 * and the editing canvas (`ProseCanvas`, the surface the member types in).
 * D17 shipped this logic inside `MarkdownRenderer` alone and gated it there —
 * one day after ADR-572 D8 had demoted that renderer to thumbnail + print. The
 * canvas drew no image for three weeks under a green gate. Two copies of this
 * logic would be two chances to reproduce that.
 *
 * Resolution: `getFile` mints an ABSOLUTE signed URL for a CAS-backed binary
 * head (usable as-is); the legacy `documents`-bucket `?storage_path=` form
 * still needs the authenticated `blobUrl` exchange. `resolveDownload` in
 * `download.ts` is deliberately NOT reused: that is the SAVE lane
 * (`Content-Disposition: attachment`), and a viewing URL and a saving URL are
 * different URLs on purpose — see that file.
 *
 * The api client is imported lazily so a surface that renders no image never
 * pays for the module, and so the canvas can be mounted in a bare harness.
 */

/** Anything with a scheme (https:, data:, blob:) or protocol-relative is already fetchable. */
export function isFetchableImageSrc(src: string): boolean {
  return /^[a-z][a-z0-9+.-]*:/i.test(src) || src.startsWith('//');
}

/**
 * Resolve an image `src` to a URL an `<img>` can load. A fetchable `src` is
 * returned untouched; a workspace path is minted per call. Rejects when the
 * file is missing or has no serving URL — the caller names the path rather
 * than showing a broken glyph.
 */
export async function resolveWorkspaceImageUrl(src: string): Promise<string> {
  if (!src) throw new Error('empty image src');
  if (isFetchableImageSrc(src)) return src;
  const path = src.startsWith('/workspace/') ? src : `/workspace/${src.replace(/^\/+/, '')}`;
  const { api } = await import('@/lib/api/client');
  const f = await api.workspace.getFile(path);
  const url = (f as { content_url?: string | null }).content_url;
  if (!url) throw new Error(`no content_url for ${path}`);
  if (!/[?&]storage_path=/.test(url)) return url;
  return (await api.documents.blobUrl(url)).url;
}
