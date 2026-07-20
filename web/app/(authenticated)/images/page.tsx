'use client';

/**
 * /images — the IMAGES surface route (ADR-472).
 *
 * The SECOND authoring app. Carved out of Studio, where it had shipped as a
 * fifth layout ("canvas", ADR-471) and read to the operator as a document type
 * rather than the app its name promised.
 *
 * It mounts the same authoring machinery as Studio — one implementation, two
 * consumers (ADR-472 D2) — parameterized by `IMAGES_APP`: its own surface slug
 * (so `images.file` is its param namespace, never `studio.file`), its own
 * template set (stages, not documents), and dimensions-first creation (D3).
 *
 * What makes it a different APP rather than a skin: its artifact is a rendered
 * raster. The composition is the SOURCE; the image is an attributed DERIVATION
 * of it (D4) — a relationship Studio's model does not have.
 */

import { StudioSurface, IMAGES_APP } from '@/components/studio/StudioSurface';

export default function ImagesPage() {
  return <StudioSurface app={IMAGES_APP} />;
}
