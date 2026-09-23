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
 *   - renders content only; NEVER edits. Editing is an app SURFACE's job
 *     (ADR-571: prose → Text, .html → Docs/Studio) or chat's (ADR-236) —
 *     both through the member write door, attributed on one chain.
 *   - `compact` is a display hint (trims intrinsic heights), not a fork
 *   - blob-backed apps route through `useSignedBlobUrl` + degrade to BlobMissing
 *
 * Apps are registered in `web/lib/file-types::APPS` and dispatched by
 * `FileBody`. A new file type is a new app + a rule in `resolveApps` — never a
 * branch inside a mount.
 */

import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { useTranslations } from 'next-intl';
import { Download, FileText } from 'lucide-react';
import { resolveDownload } from '@/lib/workspace/download';
import type { WorkspaceFile } from '@/types';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { InferenceContentView } from '@/components/context/InferenceContentView';
import { parseUploadFrontmatter, uploadSourceCaption } from '@/lib/workspace/upload-frontmatter';
import { TILE_PREVIEW_GROUND } from '@/components/workspace/FileTile';
import { cn } from '@/lib/utils';
import { resolveViewerApplication } from '@/lib/file-types';
import { useSignedBlobUrl, useBlobBytes, BlobLoading, BlobError, BlobMissing } from './blob';
import { useArtifactProjection } from './projection';
import { readWorkbook, renderDocx, slidesFromProjection, type SheetGrid } from './office';

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
  const t = useTranslations('files.viewers');
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
            {t('extractedFrom', { source: sourceCaption })}
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
  // ADR-441 D3: citations resolve in the RENDERER — every mount (ArtifactCard,
  // FileOpenModal, the Files detail) draws a citing artifact exactly as the
  // Studio canvas does. Non-citing HTML renders verbatim (the projection
  // short-circuits); a citing document holds blank until the projection lands.
  const { needsProjection, projected } = useArtifactProjection(file);
  return (
    <iframe
      title={filename}
      srcDoc={needsProjection ? projected ?? '' : file.content || ''}
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
  const t = useTranslations('files.viewers');
  const { url, loading, error } = useSignedBlobUrl(contentUrl);
  if (loading) return <BlobLoading label={t('loadingImage')} />;
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
  const t = useTranslations('files.viewers');
  const { url, loading, error } = useSignedBlobUrl(contentUrl);
  if (loading) return <BlobLoading label={t('loadingVideo')} />;
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
  const t = useTranslations('files.viewers');
  const { url, loading, error } = useSignedBlobUrl(contentUrl);
  if (loading) return <BlobLoading label={t('loadingAudio')} />;
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
  const t = useTranslations('files.viewers');
  const { url, loading, error } = useSignedBlobUrl(contentUrl);
  if (loading) return <BlobLoading label={t('loadingPdf')} />;
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
// 7. Table Viewer — CSV and .xlsx workbooks (ADR-395 am.2 D15)
// ---------------------------------------------------------------------------
//
// ONE table renderer for both tabular kinds: a CSV's text and a workbook's
// cached cell values both arrive as rows of strings and draw through
// `DataTable`. What differs is only where the rows come from.

/** Rows drawn per sheet — the parse itself is bounded to this (`sheetRows`). */
const SHEET_ROWS = { full: 500, compact: 6 } as const;
const SHEET_COLS = { full: 52, compact: 8 } as const;

function DataTable({
  head,
  body,
  firstRow,
}: {
  head: string[];
  body: string[][];
  /** Draw a row-number gutter starting here (a workbook); omit for a CSV. */
  firstRow?: number;
}) {
  const gutter = firstRow !== undefined;
  return (
    <table className="w-full text-sm">
      <thead className="bg-muted/30">
        <tr>
          {gutter && <th className="w-10 border-b border-r border-border px-2 py-2" />}
          {head.map((cell, idx) => (
            <th key={idx} className="px-3 py-2 text-left font-medium border-b border-border">
              {cell}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {body.map((row, rowIdx) => (
          <tr key={rowIdx} className="border-b border-border/50 last:border-b-0">
            {firstRow !== undefined && (
              <td className="border-r border-border bg-muted/20 px-2 py-2 text-right text-xs tabular-nums text-muted-foreground/70">
                {firstRow + rowIdx}
              </td>
            )}
            {row.map((cell, cellIdx) => (
              <td key={cellIdx} className="px-3 py-2 text-muted-foreground whitespace-pre-wrap">
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export const TableViewer: ViewerApp = ({ file, compact }) => {
  const t = useTranslations('files.viewers');
  // The app owns two kinds; which one THIS file is comes from the same
  // resolver that routed it here (served view first, ADR-395 am.2 D15).
  if (resolveViewerApplication(file.path, file.content_type, file.view) === 'spreadsheet') {
    return <WorkbookView file={file} compact={compact} />;
  }
  if (!file.content) return null;
  const limit = compact ? 6 : 21;
  const lines = file.content.trim().split('\n');
  const rows = lines.slice(0, limit).map((line) => line.split(',').map((cell) => cell.trim()));
  if (rows.length === 0) return null;
  const [header, ...body] = rows;

  return (
    <div className="overflow-auto rounded-lg border border-border">
      <DataTable head={header} body={body} />
      {lines.length > limit && (
        <div className="border-t border-border bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
          {t('previewTruncated', { count: limit - 1 })}
        </div>
      )}
    </div>
  );
};

/**
 * Parse a blob-backed file once its bytes arrive. `failed` covers every way a
 * draw can fail — no bytes, a fetch error, a parser that throws — because the
 * answer to all of them is the same: fall back to the terminal (am.2 D15).
 */
function useParsedBlob<T>(
  contentUrl: string | null | undefined,
  parse: (bytes: ArrayBuffer) => Promise<T>,
): { value: T | null; failed: boolean } {
  const { bytes, loading, error } = useBlobBytes(contentUrl);
  const parseRef = useRef(parse);
  parseRef.current = parse;
  const [out, setOut] = useState<{ value: T | null; failed: boolean }>({ value: null, failed: false });
  useEffect(() => {
    if (!bytes) {
      setOut({ value: null, failed: !loading && (error || !contentUrl) });
      return;
    }
    let cancelled = false;
    setOut({ value: null, failed: false });
    parseRef
      .current(bytes)
      .then((value) => { if (!cancelled) setOut({ value, failed: false }); })
      .catch(() => { if (!cancelled) setOut({ value: null, failed: true }); });
    return () => { cancelled = true; };
  }, [bytes, loading, error, contentUrl]);
  return out;
}

function WorkbookView({ file, compact }: ViewerAppProps) {
  const t = useTranslations('files.viewers');
  const size = compact ? 'compact' : 'full';
  const parse = useCallback(
    (bytes: ArrayBuffer) => readWorkbook(bytes, SHEET_ROWS[size], SHEET_COLS[size]),
    [size],
  );
  const { value: sheets, failed } = useParsedBlob<SheetGrid[]>(file.content_url, parse);
  const [active, setActive] = useState(0);

  if (failed || (sheets && sheets.length === 0)) return <DownloadTerminal file={file} compact={compact} />;
  if (!sheets) return <BlobLoading label={t('loadingWorkbook')} />;

  const sheet = sheets[Math.min(active, sheets.length - 1)];
  const bounded = sheet.totalRows > sheet.rows.length || sheet.totalCols > sheet.columns.length;
  const boundedNote = t('workbookBounded', {
    rows: sheet.rows.length,
    totalRows: sheet.totalRows,
    cols: sheet.columns.length,
    totalCols: sheet.totalCols,
  });
  return (
    <div className="rounded-lg border border-border">
      <OfficeBar file={file} compact={compact}>
        {sheets.length > 1 && (
          <div role="tablist" aria-label={t('sheetsLabel')} className="flex min-w-0 gap-1 overflow-x-auto">
            {sheets.map((s, i) => (
              <button
                key={i}
                type="button"
                role="tab"
                aria-selected={s === sheet}
                onClick={() => setActive(i)}
                className={cn(
                  'shrink-0 rounded-md px-2.5 py-1 text-xs',
                  s === sheet ? 'bg-background font-medium shadow-sm' : 'text-muted-foreground hover:bg-muted/50',
                )}
              >
                {s.name}
              </button>
            ))}
          </div>
        )}
      </OfficeBar>
      {sheet.rows.length === 0 ? (
        <p className="p-6 text-center text-xs text-muted-foreground">{t('sheetEmpty')}</p>
      ) : (
        <div className={cn('overflow-auto', compact ? 'max-h-[280px]' : 'max-h-[720px]')}>
          <DataTable head={sheet.columns} body={sheet.rows} firstRow={sheet.firstRow} />
        </div>
      )}
      <div className="border-t border-border bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
        {bounded ? `${boundedNote} ` : ''}
        {t('workbookCachedValues')}
      </div>
    </div>
  );
}

/**
 * The office viewers' strip: what the viewer needs to say on the left, and the
 * Download it must always keep reachable on the right — a drawn file is still
 * a file the member may want back (am.1 D13).
 */
function OfficeBar({ file, compact, children }: ViewerAppProps & { children?: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border bg-muted/20 px-2 py-1.5">
      <div className="min-w-0 flex-1">{children}</div>
      {!compact && <DownloadButton path={file.path} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 8. Document Viewer — .docx, drawn page-faithfully in a sandboxed frame
// ---------------------------------------------------------------------------
export const DocumentViewer: ViewerApp = ({ file, compact }) => {
  const t = useTranslations('files.viewers');
  const filename = file.path.split('/').pop() || file.path;
  const { value: html, failed } = useParsedBlob<string>(file.content_url, renderDocx);
  if (failed) return <DownloadTerminal file={file} compact={compact} />;
  if (html === null) return <BlobLoading label={t('loadingDocument')} />;
  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <OfficeBar file={file} compact={compact} />
      {/* Untrusted markup, isolated exactly as WebViewer isolates html:
          sandbox="" = no script, opaque origin; the document's own CSP
          forbids every fetch (see `renderDocx`). */}
      <iframe
        title={filename}
        srcDoc={html}
        sandbox=""
        className={cn('block w-full bg-white', compact ? 'h-[280px]' : 'h-[800px]')}
      />
    </div>
  );
};

// ---------------------------------------------------------------------------
// 9. Slides Viewer — .pptx, the deck's own words laid out slide by slide
// ---------------------------------------------------------------------------
// No pptx parser: the reasons are on `slidesFromProjection` and ADR-395 §11.10.
// This view needs no bytes at all — the projection rode the file read (D12).
export const SlidesViewer: ViewerApp = ({ file, compact }) => {
  const t = useTranslations('files.viewers');
  const slides = file.readable === 'read' ? slidesFromProjection(file.projection_preview) : [];
  if (slides.length === 0) return <DownloadTerminal file={file} compact={compact} />;
  const shown = compact ? slides.slice(0, 2) : slides;
  return (
    <div className="rounded-lg border border-border">
      <OfficeBar file={file} compact={compact}>
        <p className="truncate px-1 text-xs text-muted-foreground">{t('slidesTextOnly')}</p>
      </OfficeBar>
      <ol className="space-y-3 p-3">
        {shown.map((slide) => (
          <li key={slide.n} className="rounded-md border border-border bg-background p-4">
            <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground/70">
              {t('slideLabel', { n: slide.n })}
            </p>
            {slide.blocks.map((block, i) => (
              <SlideBlock key={i} block={block} lead={i === 0} />
            ))}
            {slide.notes && (
              <div className="mt-3 border-t border-border/60 pt-2 text-xs text-muted-foreground">
                <span className="font-medium">{t('speakerNotes')}</span> {slide.notes}
              </div>
            )}
          </li>
        ))}
      </ol>
      {file.projection_truncated && !compact && (
        <p className="border-t border-border bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
          {t('slidesTruncated')}
        </p>
      )}
    </div>
  );
};

/** A slide's text block — a TSV block (a table shape) draws as a table. */
function SlideBlock({ block, lead }: { block: string; lead: boolean }) {
  const lines = block.split('\n');
  if (lines.length > 1 && lines.every((l) => l.includes('\t'))) {
    const [head, ...body] = lines.map((l) => l.split('\t'));
    return (
      <div className="my-2 overflow-auto rounded border border-border">
        <DataTable head={head} body={body} />
      </div>
    );
  }
  return (
    <p className={cn('whitespace-pre-wrap', lead ? 'mb-2 text-base font-semibold' : 'mb-2 text-sm text-muted-foreground')}>
      {block}
    </p>
  );
}

// ---------------------------------------------------------------------------
// Download Terminal — not an app; the resolver's binary terminal (ADR-436 §1).
// Also every office viewer's FALLBACK (am.2 D15): a file a renderer cannot
// draw lands here, on its extracted words and its download.
// ---------------------------------------------------------------------------

/**
 * ADR-395 am.1 D13 — the one Download button, shared by the terminal and every
 * office viewer. ONE resolver, shared with the menu and Properties (ADR-427/
 * 510): it spans the text and CAS lanes and carries the substrate's own
 * filename. Rebuilding the href here is the exact bug that module exists to fix.
 */
function DownloadButton({ path }: { path: string }) {
  const t = useTranslations('files.viewers');
  const [saving, setSaving] = useState(false);
  const objectUrls = useRef<string[]>([]);
  useEffect(
    () => () => {
      objectUrls.current.forEach((u) => URL.revokeObjectURL(u));
      objectUrls.current = [];
    },
    [],
  );
  const onDownload = useCallback(async () => {
    setSaving(true);
    try {
      const resolved = await resolveDownload(
        { path, name: path.split('/').pop() || 'file', isFile: true },
        (href) => objectUrls.current.push(href),
      );
      if (!resolved) return;
      const a = document.createElement('a');
      a.href = resolved.href;
      a.download = resolved.filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } finally {
      setSaving(false);
    }
  }, [path]);
  return (
    <button
      type="button"
      onClick={onDownload}
      disabled={saving}
      className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-xs font-medium hover:bg-muted/50 disabled:opacity-60"
    >
      <Download className="h-3.5 w-3.5" />
      {saving ? t('downloading') : t('download')}
    </button>
  );
}

export const DownloadTerminal: ViewerApp = ({ file, compact }) => {
  const t = useTranslations('files.viewers');
  // ADR-395 am.1 D11 — two files land here for OPPOSITE reasons, and before
  // this line they read identically: a .sketch yarnnn genuinely cannot read,
  // and an .xlsx it reads perfectly well (am.1 D10) but cannot DRAW. "No
  // preview" is true of both and answers neither; the member's question is
  // whether their agent knows what is in the file.
  //
  // The verdict is the SERVER's (`documents.readable_state`) — undefined means
  // unknown, and an unknown says nothing rather than guessing.
  const readable = file.readable;
  const preview = readable === 'read' ? file.projection_preview : null;

  // ADR-395 am.1 D13 — the terminal SAYS "open or download this file" and,
  // before this, offered no way to do either: Download lived only in the Files
  // right-click menu and Properties, neither of them reachable from the panel
  // giving the instruction. Advice without a door.
  return (
    <div className="rounded-lg border border-dashed border-border bg-muted/10 p-6 text-center">
      <FileText className="w-8 h-8 mx-auto mb-3 text-muted-foreground" />
      <p className="text-sm font-medium">{t('noInlinePreview')}</p>
      <p className="text-xs text-muted-foreground mt-1">
        {file.content_url ? t('openExternally') : t('noBytes')}
      </p>
      {readable === 'read' && (
        <p className="mt-3 text-xs text-muted-foreground">{t('agentCanRead')}</p>
      )}
      {readable === 'unread' && (
        <p className="mt-3 text-xs text-muted-foreground">{t('agentCannotRead')}</p>
      )}

      <div className="mt-4">
        <DownloadButton path={file.path} />
      </div>

      {/* D12 — the words we already extracted. This is the honest preview of a
          format we cannot draw: no parser, no conversion service, no sandbox.
          Left-aligned because it is a document, not a caption. */}
      {preview && !compact && (
        <div className="mt-5 text-left">
          <p className="mb-2 text-xs font-medium text-muted-foreground">
            {t('extractedTextTitle')}
          </p>
          <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-md border border-border bg-background/60 p-3 text-left font-sans text-xs leading-relaxed text-muted-foreground">
            {preview}
          </pre>
          {file.projection_truncated && (
            <p className="mt-1.5 text-[11px] text-muted-foreground/70">
              {t('extractedTextTruncated')}
            </p>
          )}
        </div>
      )}
    </div>
  );
};
