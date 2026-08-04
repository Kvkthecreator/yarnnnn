'use client';

/**
 * /docs — the DOCS surface route (ADR-518).
 *
 * The WRITING app. Carved from Studio along the mode seam ({document} vs
 * {deck, web}): the flow medium's caret-first editor gets its own door,
 * recents, and default handler, while Studio keeps the layout media.
 *
 * It mounts the same authoring machinery as Studio and IMAGES — one
 * implementation, three consumers (ADR-472 D2 via ADR-518 D2) — parameterized
 * by `DOCS_APP`: its own surface slug (so `docs.file` is its param namespace,
 * never `studio.file`) and its own template set (the `document` type, owned
 * via the served `app` declaration on the layout row, ADR-473 D2).
 *
 * What makes it a different APP rather than a filter: the act is different.
 * Docs ↔ write a document (capture, revised forever, caret-first); Studio ↔
 * lay out an artifact (staged frames and bands, mouse-first). ADR-440 D2's
 * one-surface-one-act test, re-cut per medium.
 *
 * Route history: this path was the ADR-308 redirect stub → /files (the old
 * ADR-249 upload index having dissolved into Files), and /docs/[id] was the
 * ADR-249 upload-detail page — both deleted here; Files carries that job.
 */

import { StudioSurface, DOCS_APP } from '@/components/studio/StudioSurface';

export default function DocsPage() {
  return <StudioSurface app={DOCS_APP} />;
}
