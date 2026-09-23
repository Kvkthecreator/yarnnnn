/**
 * "Save as .docx / .pptx / .xlsx" — the ONE client entry point (ADR-395 am.2
 * §11.11), for every file surface that offers it: the right-click menu
 * (`FileContextMenu`) and Properties (`NodeDetailsPanel`). Same discipline as
 * `resolveDownload` beside it: two surfaces, one resolver, so they cannot
 * drift into offering different formats for the same file.
 *
 * WHICH formats a file can become is the SERVER's answer, not ours. The file
 * read serves `export_as` (am.2 D16) — per FILE, because a Slides deck and a
 * blog post are both `.html` and only the deck becomes a presentation, which
 * only the file's own declared type can say. So there is no format table
 * here: an absent or failed `export_as` resolves to NO targets and the entry
 * does not render. Guessing from the extension would offer a deck export on
 * a blog post, and the server would refuse it after the click.
 *
 * The act is a NEW file beside the source, named by the kernel and citing the
 * source (`derived_from`). It never replaces a file.
 */

import { api } from '@/lib/api/client';
import type { ExportTarget } from '@/types';

/** The formats this file can be saved as — [] for a folder or when unknown. */
export async function resolveExportTargets(
  target: { path: string; isFile: boolean },
): Promise<ExportTarget[]> {
  if (!target.isFile) return [];
  try {
    const file = await api.workspace.getFile(target.path);
    return file.export_as ?? [];
  } catch {
    return [];
  }
}

/** Write the file as `to`; resolves to the NEW file's path. */
export async function exportAs(path: string, to: ExportTarget): Promise<string> {
  const res = await api.documents.exportAs(path, to);
  return res.new_path;
}
