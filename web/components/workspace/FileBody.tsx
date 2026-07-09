'use client';

/**
 * FileBody — THE one file renderer, mounted by every surface that opens a file.
 *
 * Extracted from `ContentViewer.FileView` (2026-07-09). The kind-switch,
 * the blob previews, and the signed-URL resolution used to live privately
 * inside the Files surface, which meant the chat surface could not show what
 * a lane had just written without re-implementing all of it.
 *
 * Two mounts today:
 *   1. the DOCUMENT CHROME — `ContentViewer` on the Files / Recents / Context
 *      surfaces: header (name, type, attribution, verbs) + this body.
 *   2. the ARTIFACT CARD — `chat-surface/ArtifactCard`: a bounded frame around
 *      this body, shown inline when a lane's WriteFile/EditFile lands.
 *
 * Singular Implementation: a new file type is a rule in
 * `lib/file-types::resolveViewerApplication` plus a branch HERE. Never a
 * branch inside a mount. If a third mount needs a different frame, it wraps
 * this component; it does not fork it.
 *
 * ADR-236: this component RENDERS. It never edits — chat is the canonical
 * mutation surface (`SubstrateEditor` was deleted). That is the Artifacts
 * model, not the Canvas model, and it is a ratified decision.
 *
 * `compact` is a DISPLAY hint, not a different renderer: it trims chrome and
 * shortens the intrinsic heights (iframes, previews) so the body sits inside
 * a scrollable card instead of a full window. Same tree, same dispatch.
 */

import { useEffect, useState } from 'react';
import { Download, ExternalLink, FileText, FileQuestion, Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { InferenceContentView } from '@/components/context/InferenceContentView';
import { resolveViewerApplication } from '@/lib/file-types';
import { parseUploadFrontmatter, uploadSourceCaption } from '@/lib/workspace/upload-frontmatter';
import { TILE_PREVIEW_GROUND } from '@/components/workspace/FileTile';
import { cn } from '@/lib/utils';
import type { WorkspaceFile } from '@/types';

// ADR-162 Sub-phase D / ADR-215: IDENTITY carries an `<!-- inference-meta: … -->`
// comment injected by `_append_inference_meta()`. This is the TIER-1 path-exact
// association (see lib/file-types header): one known path, one bespoke renderer.
// ADR-432 D1c: BRAND_PATH removed with the retired Brand concept.
const IDENTITY_PATH = '/workspace/persona/IDENTITY.md';

export function inferenceTarget(path: string): 'identity' | null {
  return path === IDENTITY_PATH ? 'identity' : null;
}

/**
 * Resolve a file's content_url to a directly-renderable URL (ADR-395).
 *
 * A raw upload's content_url is a relative `/api/documents/blob?storage_path=…`
 * reference that requires AUTH to resolve — a browser `<img>/<iframe>/<video>`
 * src can't send the Bearer header, so we resolve the signed URL here via an
 * authenticated fetch and hand the DIRECT (Supabase) signed URL to the element.
 * Absolute URLs pass through unchanged. Returns {url, loading, error}; url is
 * '' until resolved.
 *
 * ADR-427 D4 forward pointer: `content_url` is scheduled for deletion as a
 * stored column — it becomes a per-request, per-principal, TTL'd MINTED
 * capability computed from `blob_sha`. This hook is the single FE site that
 * consumes it, so the retirement lands here and nowhere else.
 */
export function useSignedBlobUrl(
  contentUrl: string | null | undefined,
): { url: string; loading: boolean; error: boolean } {
  const [state, setState] = useState<{ url: string; loading: boolean; error: boolean }>(
    { url: '', loading: false, error: false }
  );
  useEffect(() => {
    if (!contentUrl) { setState({ url: '', loading: false, error: false }); return; }
    if (/^(https?:|data:|blob:)/i.test(contentUrl)) {
      setState({ url: contentUrl, loading: false, error: false });
      return;
    }
    let cancelled = false;
    setState({ url: '', loading: true, error: false });
    api.documents
      .blobUrl(contentUrl)
      .then((r) => { if (!cancelled) setState({ url: r.url, loading: false, error: false }); })
      .catch(() => { if (!cancelled) setState({ url: '', loading: false, error: true }); });
    return () => { cancelled = true; };
  }, [contentUrl]);
  return state;
}

// ---------------------------------------------------------------------------
// The body
// ---------------------------------------------------------------------------

interface FileBodyProps {
  file: WorkspaceFile;
  /** Trim intrinsic heights + chrome for an inline card mount. */
  compact?: boolean;
  className?: string;
}

export function FileBody({ file, compact = false, className }: FileBodyProps) {
  const filename = file.path.split('/').pop() || file.path;
  const kind = resolveViewerApplication(file.path, file.content_type);

  // A binary revision's text column is empty by construction (ADR-427 §8).
  // Every blob-backed branch below therefore guards on `content_url` and
  // degrades to BlobMissing rather than painting an empty box.
  const frameHeight = compact ? 'min-h-[280px]' : 'min-h-[720px]';

  return (
    <div className={cn('space-y-4', className)}>
      {kind === 'markdown' && file.content && (() => {
        const target = inferenceTarget(file.path);
        if (target) {
          return <InferenceContentView content={file.content} target={target} />;
        }
        // 2026-07-01: an uploaded document's extracted-text `.md` carries a
        // `---…---` YAML header (documents.py) that would otherwise render as
        // raw body text. Strip it; surface the original filename as a caption.
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
      })()}

      {kind === 'html' && (
        <iframe
          title={filename}
          srcDoc={file.content || ''}
          sandbox=""
          className={cn('w-full rounded-lg border border-border bg-white', frameHeight)}
        />
      )}

      {/* Finder-parity (2026-07-09): the detail preview frames a file identically
          to its Recents card — one radius (rounded-lg) + the ONE tile ground
          (TILE_PREVIEW_GROUND). The same SVG no longer looks like two different
          files card→detail (the audit's flagged mismatch). */}
      {kind === 'image' && (
        <div className={cn('rounded-lg border border-border p-4', TILE_PREVIEW_GROUND)}>
          {file.content_url ? (
            <ImagePreview contentUrl={file.content_url} alt={filename} />
          ) : (
            // Inline SVG lives in the text column, not the blob.
            <div
              className="mx-auto max-w-full [&_svg]:h-auto [&_svg]:max-w-full"
              dangerouslySetInnerHTML={{ __html: file.content || '' }}
            />
          )}
        </div>
      )}

      {kind === 'video' && (
        file.content_url
          ? <VideoPreview contentUrl={file.content_url} />
          : <BlobMissing kind="video" />
      )}

      {kind === 'audio' && (
        file.content_url
          ? <AudioPreview contentUrl={file.content_url} />
          : <BlobMissing kind="audio" />
      )}

      {kind === 'pdf' && (
        file.content_url
          ? <PdfPreview contentUrl={file.content_url} title={filename} compact={compact} />
          : <BlobMissing kind="PDF" />
      )}

      {kind === 'csv' && file.content && <CsvPreview content={file.content} compact={compact} />}

      {kind === 'text' && (
        <pre className="overflow-auto rounded-lg border border-border bg-muted/20 p-4 text-sm whitespace-pre-wrap">
          {file.content || ''}
        </pre>
      )}

      {kind === 'download' && (
        <div className="rounded-lg border border-dashed border-border bg-muted/10 p-6 text-center">
          <FileText className="w-8 h-8 mx-auto mb-3 text-muted-foreground" />
          <p className="text-sm font-medium">Preview not available inline</p>
          <p className="text-xs text-muted-foreground mt-1">
            {file.content_url
              ? 'Open or download this file to inspect it in a native viewer.'
              : 'This file has no bytes to show yet.'}
          </p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Blob-backed previews (ADR-395 signed-URL resolution)
// ---------------------------------------------------------------------------

function ImagePreview({ contentUrl, alt }: { contentUrl: string; alt: string }) {
  const { url, loading, error } = useSignedBlobUrl(contentUrl);
  if (loading) return <BlobLoading label="Loading image…" />;
  if (error || !url) return <BlobError />;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={url} alt={alt} className="max-w-full h-auto mx-auto rounded-lg" />;
}

function VideoPreview({ contentUrl }: { contentUrl: string }) {
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

function AudioPreview({ contentUrl }: { contentUrl: string }) {
  const { url, loading, error } = useSignedBlobUrl(contentUrl);
  if (loading) return <BlobLoading label="Loading audio…" />;
  if (error || !url) return <BlobError />;
  return (
    <div className="rounded-lg border border-border bg-muted/10 p-4">
      <audio src={url} controls className="w-full" />
    </div>
  );
}

function PdfPreview({ contentUrl, title, compact }: { contentUrl: string; title: string; compact?: boolean }) {
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

function BlobLoading({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center gap-2 rounded-lg border border-border bg-muted/10 py-16 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />
      {label}
    </div>
  );
}

function BlobError() {
  return (
    <div className="rounded-lg border border-dashed border-border bg-muted/10 p-6 text-center text-sm text-muted-foreground">
      <FileQuestion className="mx-auto mb-2 h-6 w-6 text-muted-foreground/50" />
      Couldn’t load this file. Try Download to open it in a native viewer.
    </div>
  );
}

/**
 * The type resolved to a blob-backed viewer but there is no blob.
 *
 * Today this is the honest state for a versioned `.mp4`: binary is still
 * Category-3 (`content_url` sidecar) and a `write_revision` of bytes has
 * nowhere to land until ADR-427 Phase 2. Saying so is better than painting
 * an empty player — and better than the pre-2026-07-09 behavior, which
 * resolved the same file to `text` and painted its bytes.
 */
function BlobMissing({ kind }: { kind: string }) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-muted/10 p-6 text-center text-sm text-muted-foreground">
      <FileQuestion className="mx-auto mb-2 h-6 w-6 text-muted-foreground/50" />
      This {kind} has no stored bytes yet.
    </div>
  );
}

function CsvPreview({ content, compact }: { content: string; compact?: boolean }) {
  const limit = compact ? 6 : 21;
  const lines = content.trim().split('\n');
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
}

// ---------------------------------------------------------------------------
// FileActions — "open with your computer" (the degenerate Open With, ADR-329)
// ---------------------------------------------------------------------------

export function FileActions({ contentUrl }: { contentUrl: string }) {
  const { url, loading } = useSignedBlobUrl(contentUrl);
  const disabled = loading || !url;
  return (
    <div className="flex items-center gap-2 shrink-0">
      <a
        href={disabled ? undefined : url}
        target="_blank"
        rel="noreferrer"
        aria-disabled={disabled}
        className={cn(
          'inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground',
          disabled && 'pointer-events-none opacity-50'
        )}
      >
        <ExternalLink className="w-3.5 h-3.5" />
        Open
      </a>
      <a
        href={disabled ? undefined : url}
        download
        aria-disabled={disabled}
        className={cn(
          'inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground',
          disabled && 'pointer-events-none opacity-50'
        )}
      >
        <Download className="w-3.5 h-3.5" />
        Download
      </a>
    </div>
  );
}
