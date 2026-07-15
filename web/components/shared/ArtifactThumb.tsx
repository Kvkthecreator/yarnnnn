'use client';

/**
 * ArtifactThumb — a real render of an artifact, scaled down (the ADR-447
 * navigator technique): sandboxed srcDoc iframe, display-only.
 *
 * Shared home (2026-07-15, the seam-contract pass). First consumer is chat's
 * citation tile (`ArtifactCard`); `StudioSurface`'s local `ArtifactThumb`
 * (which self-fetches) should fold into this when the Studio lane's tree is
 * quiet — one thumb, N mounts. This one is purely presentational: the mount
 * hands it the document it already loaded.
 */

import { FileText } from 'lucide-react';
import { cn } from '@/lib/utils';

export function ArtifactThumb({
  doc,
  className,
}: {
  /** The artifact's HTML source; null/undefined renders the placeholder. */
  doc?: string | null;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'relative aspect-[16/10] overflow-hidden rounded-md border border-border bg-muted/30',
        className,
      )}
    >
      {doc ? (
        <iframe
          sandbox=""
          srcDoc={doc}
          tabIndex={-1}
          aria-hidden
          title=""
          className="pointer-events-none absolute left-0 top-0 h-[400%] w-[400%] origin-top-left scale-[0.25] border-0 bg-white"
        />
      ) : (
        <div className="flex h-full items-center justify-center">
          <FileText className="h-5 w-5 text-muted-foreground/40" />
        </div>
      )}
    </div>
  );
}
