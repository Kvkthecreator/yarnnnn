'use client';

/**
 * /blogger — the Blogger surface route (ADR-627: the publish medium's desk).
 *
 * Thin wrapper — the surface component owns everything; the window manager
 * owns the frame (window = surface, ADR-436). Studio-parameterized, the Docs
 * shape: `StudioSurface app={BLOGGER_APP}` (the component keeps its internal
 * Studio name per ADR-599 D6).
 */

import { BLOGGER_APP, StudioSurface } from '@/components/authoring/StudioSurface';

export default function BloggerPage() {
  return <StudioSurface app={BLOGGER_APP} />;
}
