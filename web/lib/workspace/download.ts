/**
 * resolveDownload — "save this file to my computer", for every file surface.
 *
 * ONE resolver, because Download is now offered in TWO places and they must
 * not drift: the right-click menu (`FileContextMenu`) and the Properties panel
 * (`NodeDetailsPanel`). The menu had the verb and Properties did not, which is
 * its own defect — Properties is where an operator goes to ask "what IS this
 * file", and "and give me a copy" is the same question's second half. Two
 * copies of this logic would be two chances to reproduce the bug it fixes.
 *
 * WHY THIS EXISTS AT ALL (the defect, 2026-08-31). The previous resolver built
 * the download itself from `getFile()`:
 *
 *     const file = await api.workspace.getFile(path);
 *     if (file.content_url) return api.documents.blobUrl(file.content_url);
 *
 * That reads as if it covers the binary lane. It does not. A CAS-backed binary
 * (ADR-427) stores NO `content_url` on its row — the capability is minted per
 * read (D4) — so `getFile` returns an ABSOLUTE, already-signed URL, while
 * `blobUrl` resolves only the legacy `documents`-bucket `?storage_path=` form
 * and REJECTS anything else. The reject was caught, the resolver returned
 * null, and a null download means the menu entry does not render at all: every
 * one of the 39 live binaries in production silently offered no Download.
 * An affordance ABSENT rather than refused is the ADR-373 D6 incorrect-success
 * shape — nothing is wrong on screen, so the operator concludes the product
 * cannot save a file.
 *
 * The fix is not a third branch here; it is that the SERVER answers this
 * question. `GET /api/workspace/file/download` spans both lanes and — for a
 * binary — mints the url with the file's real name as a
 * `Content-Disposition: attachment`, which is what stops a save from landing
 * as a 64-hex content address with no extension. See the route for why the
 * viewing url and the saving url are deliberately different urls.
 *
 * NO FOLDER LANE, and no zip builder is coming (ADR-417 — generation is
 * rented, not owned). The bulk door already exists and is strictly better:
 * `GET /api/workspace/export` produces a real git repo WITH history and
 * attribution. A folder returns null and the affordance does not render — no
 * dead entry, no disabled-looking row.
 */

import { api } from '@/lib/api/client';

export interface ResolvedDownload {
  href: string;
  filename: string;
}

/**
 * The MIME type a TEXT file downloads as.
 *
 * A text file's bytes live in the `content` column, not the blob store, so the
 * browser is handed a Blob we construct — and a Blob with no type saves as
 * `application/octet-stream`, which the OS shows as a nameless binary even when
 * the extension is right. The type has to be stated.
 *
 * Deliberately NARROW: the extensions the substrate's text lane actually holds,
 * mirroring `_EXT_MIMES` in `api/services/content_types.py` for exactly those
 * rows. NOT a second general type registry — the backend's
 * `derive_content_type` remains the authority for every stored file, and
 * anything else falls back to `text/plain`.
 *
 * Only consulted when the server hands back a `content_type` it could not
 * improve on: the server's own derived type wins whenever it has one, since it
 * saw the file's magic bytes and this function has only the name.
 */
export function textDownloadMime(filename: string): string {
  const ext = filename.includes('.') ? filename.split('.').pop()!.toLowerCase() : '';
  switch (ext) {
    case 'md':
    case 'markdown': return 'text/markdown';
    case 'csv': return 'text/csv';
    case 'html': return 'text/html';
    case 'json': return 'application/json';
    case 'yaml':
    case 'yml': return 'application/yaml';
    default: return 'text/plain';
  }
}

/**
 * Resolve a target to a followable `{ href, filename }`, or null when there is
 * nothing to save (a folder, or an unresolvable file).
 *
 * `onObjectUrl` receives any object URL minted for the text lane so the caller
 * can revoke it on unmount. Revoking here is not possible: the href must
 * outlive this function long enough for the browser to follow it.
 *
 * THE FILENAME IS LOAD-BEARING, not cosmetic, and it travels WITH the href for
 * that reason. Both lanes need it — the anchor's `download` attribute for text,
 * and as the belt to the server's `Content-Disposition` braces for binary.
 */
export async function resolveDownload(
  target: { path: string; name: string; isFile: boolean },
  onObjectUrl?: (href: string) => void,
): Promise<ResolvedDownload | null> {
  if (!target.isFile) return null;
  try {
    const res = await api.documents.fileDownload(target.path);
    // The server's filename is authoritative — it comes off the substrate's own
    // `workspace_files.path`, so the saved name cannot drift from the file's
    // identity. Fall back to the target only if the response somehow omits it.
    const filename = res.filename || target.path.split('/').pop() || target.name;

    // BINARY: follow the attachment-dispositioned signed URL as-is.
    if (res.url) return { href: res.url, filename };

    // TEXT: the content IS the file. A null content is a genuinely empty body,
    // not a missing one — it downloads as an empty file, which is what the
    // substrate holds.
    if (res.content === null || res.content === undefined) return null;
    const type =
      res.content_type && res.content_type !== 'application/octet-stream'
        ? res.content_type
        : textDownloadMime(filename);
    const href = URL.createObjectURL(new Blob([res.content], { type }));
    onObjectUrl?.(href);
    return { href, filename };
  } catch {
    return null;
  }
}
