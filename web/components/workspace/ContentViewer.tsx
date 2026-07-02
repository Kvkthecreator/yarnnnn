'use client';

/**
 * ContentViewer — Main panel explorer view
 *
 * Renders folder contents in a details-style listing and previews files using
 * type-aware viewers (markdown, HTML, image, PDF, data, text).
 */

import { useEffect, useMemo, useState } from 'react';
import { Download, ExternalLink, FileText, Folder, Loader2, Trash2, FileQuestion } from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { EditInChatButton } from '@/components/shared/EditInChatButton';
import { FileIcon } from '@/components/workspace/FileIcon';
// ADR-236 Files page rework (2026-04-30): SubstrateEditor deleted. Direct
// inline editing of substrate files is removed per the original assessment
// ("not notion-like, streamline back to edit via Chat"). Every file now
// shows the EditInChatButton; substrate writes flow through chat (which
// invokes WriteFile(scope='workspace') per ADR-235).
// ADR-329 (amended) + ADR-388 follow-up: the full revision chain (with its
// revert affordance) moved out of the file body into the Get-Info modal — it
// was double-mounted; the modal is its single home. The file header still
// shows the head-revision author glance.
import { InferenceContentView } from '@/components/context/InferenceContentView';
// ADR-309: the type→application association layer (Applications register).
// Lifted out of this file's private getFileKind into the shared kernel-
// default table so every Application dispatches through one layer.
import {
  resolveViewerApplication,
  describeViewerApplication,
} from '@/lib/file-types';
import { cn } from '@/lib/utils';
import { formatAuthorLabel, authorAccent } from '@/lib/workspace/attribution';
import { parseUploadFrontmatter, uploadSourceCaption } from '@/lib/workspace/upload-frontmatter';
import { operatorCanOrganize } from '@/lib/workspace/ownership';
import { useFileContextMenu, type FileVerbs } from '@/components/workspace/FileContextMenu';
import type { WorkspaceTreeNode, WorkspaceFile } from '@/types';

// ADR-162 Sub-phase D / ADR-215: IDENTITY and BRAND files carry an
// `<!-- inference-meta: ... -->` comment injected by `_append_inference_meta()`
// on the backend. When rendered on Files, we surface that provenance (source
// caption + gap banner) above the markdown body via InferenceContentView.
const IDENTITY_PATH = '/workspace/persona/IDENTITY.md';
const BRAND_PATH = '/workspace/operation/BRAND.md';

/**
 * Resolve a file's content_url to a directly-renderable URL (ADR-395).
 *
 * A raw upload's content_url is a relative `/api/documents/blob?storage_path=…`
 * reference that requires AUTH to resolve — a browser `<img>/<iframe>` src can't
 * send the Bearer header, so we resolve the signed URL here via an authenticated
 * fetch and hand the DIRECT (Supabase) signed URL to the element. Absolute URLs
 * (output-gateway S3/render outputs) pass through unchanged — no fetch. Returns
 * {url, loading, error}; url is '' until resolved.
 */
function useSignedBlobUrl(contentUrl: string | null | undefined): { url: string; loading: boolean; error: boolean } {
  const [state, setState] = useState<{ url: string; loading: boolean; error: boolean }>(
    { url: '', loading: false, error: false }
  );
  useEffect(() => {
    if (!contentUrl) { setState({ url: '', loading: false, error: false }); return; }
    // Absolute URL (output gateway) — render directly, no auth resolve needed.
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

function inferenceTarget(path: string): 'identity' | 'brand' | null {
  if (path === IDENTITY_PATH) return 'identity';
  if (path === BRAND_PATH) return 'brand';
  return null;
}

interface ContentViewerProps {
  selectedNode: WorkspaceTreeNode | null;
  onNavigate: (node: WorkspaceTreeNode) => void;
  showHeader?: boolean;
  /**
   * ADR-215 R1 + ADR-236 Files page rework (2026-04-30): seed the chat
   * rail for any file edit. Substrate files no longer render an inline
   * editor — every file routes through chat for mutations.
   */
  onOpenChatDraft?: (prompt: string) => void;
  /**
   * ADR-329: 'delete' is an operator verb (trash-semantics, uploads only).
   * Called after a successful archive so the surface clears selection +
   * refreshes the tree.
   */
  onDeleted?: () => void;
  /** ADR-388 D4: the Files-surface view mode (icon grid / details list). */
  viewMode?: 'icon' | 'list';
  /** ADR-388 D5: right-click "Properties" on a folder-listing row. */
  onGetInfo?: (node: WorkspaceTreeNode) => void;
  /**
   * ADR-400 Amendment 1: the operator's file verbs → right-click menu on the
   * folder-listing rows (the main-panel right-click). When present it supersedes
   * onGetInfo (the menu carries Properties). Optimistic — the handler + backend
   * decide.
   */
  verbs?: FileVerbs;
}

export function ContentViewer({
  selectedNode,
  onNavigate,
  showHeader = true,
  onOpenChatDraft,
  onDeleted,
  viewMode = 'list',
  onGetInfo,
  verbs,
}: ContentViewerProps) {
  if (!selectedNode) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        Select a file or folder from the explorer
      </div>
    );
  }

  if (selectedNode.type === 'folder') {
    return (
      <DirectoryView
        node={selectedNode}
        onNavigate={onNavigate}
        showHeader={showHeader}
        onOpenChatDraft={onOpenChatDraft}
        viewMode={viewMode}
        onGetInfo={onGetInfo}
        verbs={verbs}
      />
    );
  }

  return (
    <FileView
      path={selectedNode.path}
      showHeader={showHeader}
      onOpenChatDraft={onOpenChatDraft}
      onDeleted={onDeleted}
    />
  );
}

function DirectoryView({
  node,
  onNavigate,
  showHeader,
  onOpenChatDraft,
  viewMode = 'list',
  onGetInfo,
  verbs,
}: {
  node: WorkspaceTreeNode;
  onNavigate: (node: WorkspaceTreeNode) => void;
  showHeader: boolean;
  onOpenChatDraft?: (prompt: string) => void;
  viewMode?: 'icon' | 'list';
  onGetInfo?: (node: WorkspaceTreeNode) => void;
  verbs?: FileVerbs;
}) {
  // ADR-400: right-click a folder-listing row → the shared file context menu.
  // Falls back to onGetInfo-only when verbs aren't wired (Home/other mounts).
  const { openMenu, menu } = useFileContextMenu(verbs);
  const rowContext = (child: WorkspaceTreeNode) => (e: React.MouseEvent) => {
    if (verbs) {
      openMenu({ path: child.path, name: child.name, isFile: child.type === 'file' }, e);
    } else if (onGetInfo) {
      e.preventDefault();
      onGetInfo(child);
    }
  };
  // For synthetic nodes (entity subfolders with no pre-populated children),
  // fetch children on demand via the tree API.
  const [fetchedChildren, setFetchedChildren] = useState<WorkspaceTreeNode[] | null>(null);
  const [fetchLoading, setFetchLoading] = useState(false);

  const hasPreloadedChildren = (node.children?.length ?? 0) > 0;

  useEffect(() => {
    if (hasPreloadedChildren) return; // already have children from tree
    // Only fetch for real workspace paths (not virtual /explorer/ paths)
    if (!node.path.startsWith('/workspace/') && !node.path.startsWith('/tasks/')) return;
    setFetchLoading(true);
    api.workspace.getTree(node.path)
      .then((data) => setFetchedChildren(Array.isArray(data) ? data as WorkspaceTreeNode[] : []))
      .catch(() => setFetchedChildren([]))
      .finally(() => setFetchLoading(false));
  }, [node.path, hasPreloadedChildren]);

  const children = useMemo(
    () =>
      [...(hasPreloadedChildren ? (node.children || []) : (fetchedChildren || []))].sort((a, b) => {
        const aRank = a.type === 'folder' ? 0 : 1;
        const bRank = b.type === 'folder' ? 0 : 1;
        return aRank - bRank || a.name.localeCompare(b.name);
      }),
    [node.children, fetchedChildren, hasPreloadedChildren]
  );

  if (fetchLoading) {
    return (
      <div className="flex items-center justify-center py-10">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (children.length === 0) {
    return (
      <div className="p-8 text-center text-muted-foreground text-sm">
        <Folder className="w-10 h-10 mx-auto mb-3 opacity-40" />
        <p className="font-medium">Empty folder</p>
        <p className="text-xs mt-1">{node.path}</p>
      </div>
    );
  }

  return (
    <>
    <div className="h-full overflow-auto">
      {showHeader && (
        <div className="border-b border-border bg-muted/20 px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-medium">{node.name}</h2>
              <p className="text-xs text-muted-foreground">{children.length} items</p>
            </div>
            {onOpenChatDraft && (
              <EditInChatButton
                prompt={(() => {
                  const folderName = node.name || node.path.split('/').filter(Boolean).pop() || 'this folder';
                  return `About the ${folderName} context: `;
                })()}
                onOpenChatDraft={onOpenChatDraft}
              />
            )}
          </div>
        </div>
      )}

      {/* ADR-388 D4: honor the surface-wide view mode. Right-click any row/tile
          → Get Info (D5); each row shows who last wrote it (D3). */}
      {viewMode === 'icon' ? (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(140px,1fr))] gap-2 p-3">
          {children.map((child) => (
            <button
              key={child.path}
              onClick={() => onNavigate(child)}
              onContextMenu={rowContext(child)}
              className="flex flex-col items-center gap-1.5 rounded-lg border border-transparent p-3 text-center hover:border-border hover:bg-muted/40 transition-colors"
            >
              {child.type === 'folder' ? (
                <Folder className="h-8 w-8 text-sky-600" />
              ) : (
                <FileIcon filename={child.name} size="lg" />
              )}
              <span className="w-full truncate text-xs font-medium">{child.name}</span>
              <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
                <span className={cn('h-1.5 w-1.5 rounded-full', authorAccent((child as any).authored_by))} />
                {formatAuthorLabel((child as any).authored_by)}
              </span>
            </button>
          ))}
        </div>
      ) : (
        <div className="px-2 py-2">
          <div className="grid grid-cols-[minmax(0,1fr)_140px_120px] gap-3 px-3 py-2 text-[11px] uppercase tracking-wide text-muted-foreground border-b border-border/60">
            <span>Name</span>
            <span>Author</span>
            <span>Modified</span>
          </div>
          <div className="divide-y divide-border/50">
            {children.map((child) => (
              <button
                key={child.path}
                onClick={() => onNavigate(child)}
                onContextMenu={rowContext(child)}
                className="grid w-full grid-cols-[minmax(0,1fr)_140px_120px] gap-3 px-3 py-3 text-left hover:bg-muted/40 transition-colors"
              >
                <div className="flex items-center gap-2 min-w-0">
                  {child.type === 'folder' ? (
                    <Folder className="w-4 h-4 text-sky-600 shrink-0" />
                  ) : (
                    <FileIcon filename={child.name} size="md" />
                  )}
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{child.name}</p>
                    {child.summary && (
                      <p className="text-xs text-muted-foreground truncate">{child.summary}</p>
                    )}
                  </div>
                </div>
                {/* ADR-388 D3: who last wrote this — the attribution the folder
                    listing showed NONE of before. */}
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground self-center">
                  <span className={cn('h-1.5 w-1.5 rounded-full shrink-0', authorAccent((child as any).authored_by))} />
                  <span className="truncate">{formatAuthorLabel((child as any).authored_by)}</span>
                </div>
                <div className="text-xs text-muted-foreground self-center">
                  {formatTimestamp(child.updated_at)}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
    {menu}
    </>
  );
}

// ADR-388 D3: the file-header author line uses the ONE shared attribution
// formatter (was a local formatHeadAuthor duplicate). The MCP-host form
// "ChatGPT (via MCP)" now shows on the file header too.
const formatHeadAuthor = formatAuthorLabel;

interface HeadRevision {
  authored_by: string;
  created_at: string;
}

// ADR-400 Amendment 1: the file-header Trash button shows for anything the
// operator can organize (the shared mirror of the backend gate). Optimistic:
// the backend is authoritative; the button just doesn't offer a verb that will
// always 403 (system/ + machine-config).
const isOperatorDeletable = operatorCanOrganize;

function FileView({
  path,
  showHeader,
  onOpenChatDraft,
  onDeleted,
}: {
  path: string;
  showHeader: boolean;
  onOpenChatDraft?: (prompt: string) => void;
  onDeleted?: () => void;
}) {
  const [file, setFile] = useState<WorkspaceFile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // ADR-388 follow-up: a 404 here means the file doesn't exist at this path
  // (e.g. a stale deep-link, or a synthetic node fabricated for a typed path
  // that was never written). That's an honest "no longer here" empty state,
  // NOT a red "API Error" — distinguished from a real load failure.
  const [notFound, setNotFound] = useState(false);
  const [reloadKey] = useState(0);
  const [deleting, setDeleting] = useState(false);
  // ADR-236 Cluster B: head-revision authorship surfaced on the file
  // header. Reads /api/workspace/revisions?limit=1 — the existing
  // ADR-209 Phase 4 endpoint. No new backend.
  const [headRevision, setHeadRevision] = useState<HeadRevision | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setNotFound(false);
    setHeadRevision(null);
    api.workspace
      .getFile(path)
      .then((data) => setFile(data))
      .catch((err) => {
        // 404 → honest "no longer at this path" state, not a red error.
        if (err instanceof APIError && err.status === 404) {
          setNotFound(true);
        } else {
          setError(err?.message || 'Failed to load file');
        }
      })
      .finally(() => setLoading(false));
    // Fire revision lookup in parallel — non-blocking on file render.
    api.workspace
      .listRevisions({ path }, 1)
      .then((res) => {
        const head = res.revisions[0];
        if (head) {
          setHeadRevision({ authored_by: head.authored_by, created_at: head.created_at });
        }
      })
      .catch(() => {
        // Non-fatal — head-author display is informational; absence
        // just falls back to the existing updated_at timestamp.
      });
  }, [path, reloadKey]);

  // ADR-329/ADR-400 'delete' verb — trash-semantics (the backend archives via
  // lifecycle; ADR-209-retained, reversible; restorable from Trash). Operator-
  // owned only; the button is gated below on isOperatorDeletable (the shared
  // ownership topology), and the backend enforces the same scope (403 otherwise).
  const handleDelete = async () => {
    if (deleting) return;
    if (!window.confirm('Move this file to trash? It leaves your active workspace but can be recovered.')) return;
    setDeleting(true);
    try {
      await api.documents.delete(path);
      onDeleted?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    } finally {
      setDeleting(false);
    }
  };

  const isDeletable = isOperatorDeletable(path);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // ADR-388 follow-up: 404 = the file isn't at this path (stale deep-link /
  // synthetic node for a never-written path). Honest empty state, not an error.
  if (notFound) {
    return (
      <div className="p-8 text-center text-muted-foreground text-sm">
        <FileQuestion className="mx-auto mb-3 h-10 w-10 opacity-40" />
        <p className="font-medium text-foreground/80">This file isn’t here</p>
        <p className="mt-1 text-xs max-w-sm mx-auto">
          Nothing exists at <span className="font-mono">{path}</span>. It may have
          been moved or never written — pick a file from the explorer.
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-center text-red-500 text-sm">
        <p>Error loading file</p>
        <p className="text-xs mt-1">{error}</p>
      </div>
    );
  }

  // ADR-236 Files page rework: direct inline edit removed. All files
  // route to chat for edits via the EditInChatButton. Empty files still
  // render the empty-state (no inline editor to scaffold first content
  // anymore — operator chats with YARNNN to author).
  if (!file || (!file.content && !file.content_url)) {
    return (
      <div className="p-6 text-center text-muted-foreground text-sm">
        <p>Empty file</p>
        <p className="text-xs mt-1">{path}</p>
        <p className="text-xs mt-2 text-muted-foreground/70">
          Chat with YARNNN to author content for this file.
        </p>
      </div>
    );
  }

  const filename = file.path.split('/').pop() || file.path;
  const kind = resolveViewerApplication(file.path, file.content_type);

  return (
    <div className="h-full overflow-auto">
      {showHeader ? (
        <div className="border-b border-border bg-muted/20 px-4 py-3">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex items-center gap-2 min-w-0">
                <FileIcon filename={filename} size="md" />
                <h2 className="text-lg font-medium truncate">{filename}</h2>
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                {/* ADR-400 Amendment 1: the binary "Yours / Managed by Freddie"
                    ownership chip was removed. Under the corrected model almost
                    everything is the operator's to organize, so the binary
                    misled (a governance prose file is "yours" to move but
                    agent-authored). Who-authored lives in "Last edited by" +
                    the Properties Contributors row; content-edit-through-chat is
                    the universal rule, not a per-file badge. */}
                <span>{describeViewerApplication(file.path, file.content_type)}</span>
                {file.updated_at && <span>{formatTimestamp(file.updated_at, true)}</span>}
                {file.content_type && <span>{file.content_type}</span>}
                {/* ADR-236 Cluster B: surface head-revision authorship.
                    Tells the operator who last touched this file —
                    "Last edited by YARNNN" / "Last edited by Reviewer" /
                    "Last edited by You" etc. Substrate observability via
                    ADR-209 authored_by; falls back silently on read error. */}
                {headRevision && (() => {
                  const label = formatHeadAuthor(headRevision.authored_by);
                  return label ? (
                    <span title={`authored_by: ${headRevision.authored_by}`}>
                      Last edited by {label}
                    </span>
                  ) : null;
                })()}
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {/* ADR-236 Files page rework (2026-04-30): every file gets the
                  EditInChatButton — direct inline edit (SubstrateEditor)
                  removed per the assessment. Chat is the canonical
                  mutation surface; substrate writes flow through chat's
                  WriteFile primitive (ADR-235). */}
              {onOpenChatDraft && (
                <EditInChatButton
                  prompt={(() => {
                    const relPath = path.replace('/workspace/', '').replace('/tasks/', 'tasks/');
                    return `About this file (${relPath}): `;
                  })()}
                  onOpenChatDraft={onOpenChatDraft}
                />
              )}
              {file.content_url && (
                <FileActions contentUrl={file.content_url} />
              )}
              {/* ADR-329: 'delete' is an operator verb, uploads-only
                  (ADR-320 topology). Trash-semantics — the file is archived
                  (ADR-209-retained, recoverable), not erased. */}
              {isDeletable && (
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  title="Move to trash (recoverable)"
                  className="inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-destructive/10 hover:text-destructive hover:border-destructive/40 transition-colors disabled:opacity-50"
                >
                  {deleting ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Trash2 className="w-3.5 h-3.5" />
                  )}
                  Move to Trash
                </button>
              )}
            </div>
          </div>
        </div>
      ) : file.content_url ? (
        <div className="flex justify-end px-4 pt-4">
          <FileActions contentUrl={file.content_url} />
        </div>
      ) : null}

      <div className="p-4 space-y-4">
        {kind === 'markdown' && file.content && (() => {
          const target = inferenceTarget(file.path);
          if (target) {
            // ADR-162 Sub-phase D: IDENTITY/BRAND carry inference-meta comments
            // surfaced as a source caption + gap banner above the body.
            return <InferenceContentView content={file.content} target={target} />;
          }
          // 2026-07-01: an uploaded document's extracted-text `.md` carries a
          // `---…---` YAML header (documents.py) that would otherwise render as
          // raw body text. Strip it before rendering; surface the original
          // filename + type as a clean Source caption. General strip (harmless
          // on prose files, which have no leading frontmatter); caption is
          // upload-scoped. Orthogonal to ADR-395, which retires the header.
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
            className="w-full min-h-[720px] rounded-xl border border-border bg-white"
          />
        )}

        {kind === 'image' && (
          <div className="rounded-xl border border-border bg-muted/10 p-4">
            {file.content_url ? (
              <ImagePreview contentUrl={file.content_url} alt={filename} />
            ) : (
              <div
                className="mx-auto max-w-full [&_svg]:h-auto [&_svg]:max-w-full"
                dangerouslySetInnerHTML={{ __html: file.content || '' }}
              />
            )}
          </div>
        )}

        {kind === 'pdf' && file.content_url && (
          <PdfPreview contentUrl={file.content_url} title={filename} />
        )}

        {kind === 'csv' && file.content && <CsvPreview content={file.content} />}

        {kind === 'text' && (
          <pre className="overflow-auto rounded-xl border border-border bg-muted/20 p-4 text-sm whitespace-pre-wrap">
            {file.content || ''}
          </pre>
        )}

        {kind === 'download' && file.content_url && (
          <div className="rounded-xl border border-dashed border-border bg-muted/10 p-6 text-center">
            <FileText className="w-8 h-8 mx-auto mb-3 text-muted-foreground" />
            <p className="text-sm font-medium">Preview not available inline</p>
            <p className="text-xs text-muted-foreground mt-1">
              Open or download this file to inspect it in a native viewer.
            </p>
          </div>
        )}

        {/* ADR-388 follow-up: the revision chain (ADR-209 provenance) moved
            OUT of the file body — it was double-mounted (here inline AND in the
            Get-Info modal). Singular home: Get Info (right-click or the header
            button). The file body shows content; "who wrote it" + the full
            history live one click away in Get Info, where the attribution
            summary heads the chain. (ADR-329 D1's "provenance first-class"
            intent is preserved — it's first-class in Get Info, not duplicated
            below every file.) */}
      </div>
    </div>
  );
}

// ADR-395 image preview — resolves the authed signed URL then renders the
// direct image (a browser <img> src can't carry the Bearer header).
function ImagePreview({ contentUrl, alt }: { contentUrl: string; alt: string }) {
  const { url, loading, error } = useSignedBlobUrl(contentUrl);
  if (loading) return <BlobLoading label="Loading image…" />;
  if (error || !url) return <BlobError />;
  return <img src={url} alt={alt} className="max-w-full h-auto mx-auto rounded-lg" />;
}

// ADR-395 PDF preview — same signed-URL resolution, rendered in an iframe.
function PdfPreview({ contentUrl, title }: { contentUrl: string; title: string }) {
  const { url, loading, error } = useSignedBlobUrl(contentUrl);
  if (loading) return <BlobLoading label="Loading PDF…" />;
  if (error || !url) return <BlobError />;
  return (
    <iframe
      title={title}
      src={url}
      className="w-full min-h-[800px] rounded-xl border border-border bg-white"
    />
  );
}

function BlobLoading({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center gap-2 rounded-xl border border-border bg-muted/10 py-16 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />
      {label}
    </div>
  );
}

function BlobError() {
  return (
    <div className="rounded-xl border border-dashed border-border bg-muted/10 p-6 text-center text-sm text-muted-foreground">
      <FileQuestion className="mx-auto mb-2 h-6 w-6 text-muted-foreground/50" />
      Couldn’t load this file. Try Download to open it in a native viewer.
    </div>
  );
}

function FileActions({ contentUrl }: { contentUrl: string }) {
  // ADR-395: a raw upload's content_url needs an authed resolve to a signed URL
  // (a download-anchor can't send the Bearer header either). Resolve once, then
  // the Open/Download anchors point at the direct signed URL.
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

function CsvPreview({ content }: { content: string }) {
  const rows = content
    .trim()
    .split('\n')
    .slice(0, 21)
    .map((line) => line.split(',').map((cell) => cell.trim()));

  if (rows.length === 0) {
    return null;
  }

  const [header, ...body] = rows;

  return (
    <div className="overflow-auto rounded-xl border border-border">
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
      {content.trim().split('\n').length > 21 && (
        <div className="border-t border-border bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
          Preview truncated to first 20 rows
        </div>
      )}
    </div>
  );
}

function describeNodeKind(node: WorkspaceTreeNode): string {
  if (node.type === 'folder') {
    return 'Folder';
  }
  // ADR-309: dispatch through the shared type→application association.
  return describeViewerApplication(node.path);
}

function formatTimestamp(value?: string, detailed = false): string {
  if (!value) {
    return '—';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  if (detailed) {
    return date.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  }

  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}
