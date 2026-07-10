'use client';

/**
 * The viewer apps — ADR-436.
 *
 * FileBody's monolithic 9-branch switch split into named, frame-agnostic
 * RENDERER apps. Each app owns one or more file types and draws their content;
 * it does NOT own its frame (header/chrome/bounds) — the MOUNT owns that. This
 * is the macOS model: Preview.app renders; the window server frames.
 *
 * The contract every app honors (ADR-436 §5):
 *   - signature `(props: ViewerAppProps) => JSX.Element | null`
 *   - renders content only; NEVER edits (mutation → chat, ADR-236)
 *   - `compact` is a display hint (trims intrinsic heights), not a fork
 *   - blob-backed apps route through `useSignedBlobUrl` + degrade to BlobMissing
 *
 * Apps are registered in `web/lib/file-types::APPS` and dispatched by
 * `FileBody`. A new file type is a new app + a rule in `resolveApps` — never a
 * branch inside a mount.
 */

import { FileText } from 'lucide-react';
import type { WorkspaceFile } from '@/types';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { InferenceContentView } from '@/components/context/InferenceContentView';
import { parseUploadFrontmatter, uploadSourceCaption } from '@/lib/workspace/upload-frontmatter';
import { TILE_PREVIEW_GROUND } from '@/components/workspace/FileTile';
import { cn } from '@/lib/utils';
import { useSignedBlobUrl, BlobLoading, BlobError, BlobMissing } from './blob';

/** The frame-agnostic viewer-app contract (ADR-436 §2). */
export interface ViewerAppProps {
  file: WorkspaceFile;
  /** Trim intrinsic heights for an inline card mount. Display hint, not a fork. */
  compact?: boolean;
}

export type ViewerApp = (props: ViewerAppProps) => JSX.Element | null;

// ADR-162 Sub-phase D / ADR-215: IDENTITY carries an `<!-- inference-meta: … -->`
// comment injected by `_append_inference_meta()`. This is the TIER-1 path-exact
// association routed through the table (ADR-436 §4) — the Markdown app owns it,
// not an inline `if` in the dispatcher. ADR-432 D1c: BRAND_PATH removed.
const IDENTITY_PATH = '/workspace/persona/IDENTITY.md';

export function isIdentityPath(path: string): boolean {
  return path === IDENTITY_PATH;
}

// ---------------------------------------------------------------------------
// 1. Text Viewer — the L1 raw view (text, yaml, json, unknown-textual)
// ---------------------------------------------------------------------------
export const TextViewer: ViewerApp = ({ file }) => (
  <pre className="overflow-auto rounded-lg border border-border bg-muted/20 p-4 text-sm whitespace-pre-wrap">
    {file.content || ''}
  </pre>
);

// ---------------------------------------------------------------------------
// 2. Markdown Viewer — prose; owns the IDENTITY tier-1 case + upload-frontmatter
// ---------------------------------------------------------------------------
export const MarkdownViewer: ViewerApp = ({ file }) => {
  if (!file.content) return null;
  if (isIdentityPath(file.path)) {
    return <InferenceContentView content={file.content} target="identity" />;
  }
  // 2026-07-01: an uploaded document's extracted-text `.md` carries a `---…---`
  // YAML header (documents.py) that would otherwise render as raw body text.
  // Strip it; surface the original filename as a caption.
  const { fields, body, hasFrontmatter } = parseUploadFrontmatter(file.content);
  const sourceCaption = hasFrontmatter ? uploadSourceCaption(fields) : null;
  return (
    <>
      {sourceCaption && (
        <div className="mb-3 flex items-center gap-1.5 text-xs text-muted-foreground">
          <FileText className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate" title={sourceCaption}>
            Extracted from {sourceCaption}
          </span>
        </div>
      )}
      <div className="prose prose-sm max-w-none dark:prose-invert">
        <MarkdownRenderer content={body} />
      </div>
    </>
  );
};

// ---------------------------------------------------------------------------
// 3. Web Viewer — sandboxed iframe for composed/agent HTML
// ---------------------------------------------------------------------------
export const WebViewer: ViewerApp = ({ file, compact }) => {
  const filename = file.path.split('/').pop() || file.path;
  return (
    <iframe
      title={filename}
      srcDoc={file.content || ''}
      sandbox=""
      className={cn(
        'w-full rounded-lg border border-border bg-white',
        compact ? 'min-h-[280px]' : 'min-h-[720px]',
      )}
    />
  );
};

// ---------------------------------------------------------------------------
// 4. Image Viewer — blob-backed, with the inline-SVG (text-column) fallback
// ---------------------------------------------------------------------------
export const ImageViewer: ViewerApp = ({ file }) => {
  const filename = file.path.split('/').pop() || file.path;
  // Finder-parity (2026-07-09): frame identically to the Recents card — one
  // radius (rounded-lg) + the ONE tile ground (TILE_PREVIEW_GROUND).
  return (
    <div className={cn('rounded-lg border border-border p-4', TILE_PREVIEW_GROUND)}>
      {file.content_url ? (
        <ImageBlob contentUrl={file.content_url} alt={filename} />
      ) : (
        // Inline SVG lives in the text column, not the blob.
        <div
          className="mx-auto max-w-full [&_svg]:h-auto [&_svg]:max-w-full"
          dangerouslySetInnerHTML={{ __html: file.content || '' }}
        />
      )}
    </div>
  );
};

function ImageBlob({ contentUrl, alt }: { contentUrl: string; alt: string }) {
  const { url, loading, error } = useSignedBlobUrl(contentUrl);
  if (loading) return <BlobLoading label="Loading image…" />;
  if (error || !url) return <BlobError />;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={url} alt={alt} className="max-w-full h-auto mx-auto rounded-lg" />;
}

// ---------------------------------------------------------------------------
// 5. Media Player — video + audio; owns BlobMissing until ADR-427 Phase 2
// ---------------------------------------------------------------------------
export const MediaPlayer: ViewerApp = ({ file }) => {
  const isAudio = /\.(mp3|wav|ogg|m4a|flac|aac)$/i.test(file.path)
    || (file.content_type || '').startsWith('audio/');
  if (!file.content_url) return <BlobMissing kind={isAudio ? 'audio' : 'video'} />;
  return isAudio
    ? <AudioBlob contentUrl={file.content_url} />
    : <VideoBlob contentUrl={file.content_url} />;
};

function VideoBlob({ contentUrl }: { contentUrl: string }) {
  const { url, loading, error } = useSignedBlobUrl(contentUrl);
  if (loading) return <BlobLoading label="Loading video…" />;
  if (error || !url) return <BlobError />;
  return (
    <video
      src={url}
      controls
      preload="metadata"
      className="w-full max-h-[70vh] rounded-lg border border-border bg-black"
    />
  );
}

function AudioBlob({ contentUrl }: { contentUrl: string }) {
  const { url, loading, error } = useSignedBlobUrl(contentUrl);
  if (loading) return <BlobLoading label="Loading audio…" />;
  if (error || !url) return <BlobError />;
  return (
    <div className="rounded-lg border border-border bg-muted/10 p-4">
      <audio src={url} controls className="w-full" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// 6. PDF Viewer — blob-backed iframe
// ---------------------------------------------------------------------------
export const PdfViewer: ViewerApp = ({ file, compact }) => {
  const filename = file.path.split('/').pop() || file.path;
  if (!file.content_url) return <BlobMissing kind="PDF" />;
  return <PdfBlob contentUrl={file.content_url} title={filename} compact={compact} />;
};

function PdfBlob({ contentUrl, title, compact }: { contentUrl: string; title: string; compact?: boolean }) {
  const { url, loading, error } = useSignedBlobUrl(contentUrl);
  if (loading) return <BlobLoading label="Loading PDF…" />;
  if (error || !url) return <BlobError />;
  return (
    <iframe
      title={title}
      src={url}
      className={cn(
        'w-full rounded-lg border border-border bg-white',
        compact ? 'min-h-[320px]' : 'min-h-[800px]',
      )}
    />
  );
}

// ---------------------------------------------------------------------------
// 7. Table Viewer — CSV preview
// ---------------------------------------------------------------------------
export const TableViewer: ViewerApp = ({ file, compact }) => {
  if (!file.content) return null;
  const limit = compact ? 6 : 21;
  const lines = file.content.trim().split('\n');
  const rows = lines.slice(0, limit).map((line) => line.split(',').map((cell) => cell.trim()));
  if (rows.length === 0) return null;
  const [header, ...body] = rows;

  return (
    <div className="overflow-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead className="bg-muted/30">
          <tr>
            {header.map((cell, idx) => (
              <th key={idx} className="px-3 py-2 text-left font-medium border-b border-border">
                {cell}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {body.map((row, rowIdx) => (
            <tr key={rowIdx} className="border-b border-border/50 last:border-b-0">
              {row.map((cell, cellIdx) => (
                <td key={cellIdx} className="px-3 py-2 text-muted-foreground">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {lines.length > limit && (
        <div className="border-t border-border bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
          Preview truncated to first {limit - 1} rows
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Download Terminal — not an app; the resolver's binary terminal (ADR-436 §1).
// Where a future Open-With / redirect-launch (App(principal)) will surface.
// ---------------------------------------------------------------------------
export const DownloadTerminal: ViewerApp = ({ file }) => (
  <div className="rounded-lg border border-dashed border-border bg-muted/10 p-6 text-center">
    <FileText className="w-8 h-8 mx-auto mb-3 text-muted-foreground" />
    <p className="text-sm font-medium">Preview not available inline</p>
    <p className="text-xs text-muted-foreground mt-1">
      {file.content_url
        ? 'Open or download this file to inspect it in a native viewer.'
        : 'This file has no bytes to show yet.'}
    </p>
  </div>
);
