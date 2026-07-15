'use client';

/**
 * ArtifactThumb — a small, display-only preview of an artifact.
 *
 * Shared home (2026-07-15, the seam-contract pass). First consumer is chat's
 * citation tile (`ArtifactCard`); `StudioSurface`'s local `ArtifactThumb`
 * (which self-fetches) should fold into this when the Studio lane's tree is
 * quiet — one thumb, N mounts. This one is purely presentational: the mount
 * hands it the file it already loaded.
 *
 * ── THE THUMB READS THE TYPE, THE MOUNT DOES NOT (2026-07-16) ─────────────
 *
 * A thumb is not one technique. `.html` scales down a real render (the ADR-447
 * navigator trick: sandboxed srcDoc iframe); an image is its own thumbnail and
 * wants `<img>`, not an iframe around its bytes; a pdf/csv/binary has no cheap
 * client-side render at all and shows its glyph. Dispatching here — through the
 * same `resolveViewerApplication` table every other mount reads — keeps that a
 * TYPE concern, so the tile's call site stays `<ArtifactThumb file={file} />`
 * for every format and a new type never edits a mount (ADR-436 §4).
 *
 * This is a PREVIEW, never a working render: no interaction, no blob fetch, no
 * `FileBody`. The depth rule lives in the mount (ADR-443 amendment); the
 * technique lives here.
 */

import { FileIcon } from '@/components/workspace/FileIcon';
import { resolveViewerApplication } from '@/lib/file-types';
import { cn } from '@/lib/utils';
import type { WorkspaceFile } from '@/types';

/** Frame + ground shared by every thumb technique, so the tile never jumps. */
const FRAME = 'relative aspect-[16/10] overflow-hidden rounded-md border border-border bg-muted/30';

export function ArtifactThumb({
  file,
  className,
}: {
  /** The loaded file; undefined/null renders the placeholder frame. */
  file?: Pick<WorkspaceFile, 'path' | 'content' | 'content_type' | 'content_url'> | null;
  className?: string;
}) {
  if (!file) return <Placeholder className={className} />;

  const kind = resolveViewerApplication(file.path, file.content_type);

  // html — scale a real render down (the ADR-447 navigator technique).
  if (kind === 'html') {
    if (!file.content) return <Placeholder path={file.path} className={className} />;
    return (
      <div className={cn(FRAME, className)}>
        <iframe
          sandbox=""
          srcDoc={file.content}
          tabIndex={-1}
          aria-hidden
          title=""
          className="pointer-events-none absolute left-0 top-0 h-[400%] w-[400%] origin-top-left scale-[0.25] border-0 bg-white"
        />
      </div>
    );
  }

  // image — it IS its own thumbnail. Inline SVG lives in the text column;
  // raster bytes live in the blob and are addressed by `content_url`.
  if (kind === 'image') {
    if (file.content_url) {
      return (
        <div className={cn(FRAME, 'bg-white', className)}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={file.content_url}
            alt=""
            aria-hidden
            className="absolute inset-0 h-full w-full object-contain"
          />
        </div>
      );
    }
    if (file.content) {
      return (
        <div
          className={cn(
            FRAME,
            'bg-white p-2 [&_svg]:h-full [&_svg]:w-full [&_svg]:object-contain',
            className,
          )}
          aria-hidden
          dangerouslySetInnerHTML={{ __html: file.content }}
        />
      );
    }
  }

  // Everything else — pdf, csv, video, audio, text, binary: no cheap preview.
  // The glyph is honest; the tile's name + meta carry the rest.
  return <Placeholder path={file.path} className={className} />;
}

function Placeholder({ path, className }: { path?: string; className?: string }) {
  return (
    <div className={cn(FRAME, 'flex items-center justify-center', className)}>
      <FileIcon filename={path ? path.split('/').pop() || path : 'file'} size="lg" />
    </div>
  );
}
