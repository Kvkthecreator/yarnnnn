'use client';

/**
 * ContentViewer — Main panel explorer view
 *
 * Renders folder contents in a details-style listing and previews files using
 * type-aware viewers (markdown, HTML, image, PDF, data, text).
 */

import { useEffect, useMemo, useState } from 'react';
import { Folder, Loader2, Trash2, FileQuestion } from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { EditInChatButton } from '@/components/shared/EditInChatButton';
import { FileIcon } from '@/components/workspace/FileIcon';
import { FileTile } from '@/components/workspace/FileTile';
import { FileListHeader, FileListRow } from '@/components/workspace/FileListView';
// 2026-07-09 — the file BODY (the kind-switch + blob previews) lifted out to
// `FileBody`, the one shared viewer. ContentViewer keeps the DOCUMENT CHROME
// (header, verbs, folder listing) and mounts the body; the chat surface's
// ArtifactCard mounts the same body inside a bounded card. Singular
// Implementation — a new file type is a rule in `lib/file-types` plus a branch
// in FileBody, never a branch in a mount.
import { FileBody, FileActions } from '@/components/workspace/FileBody';
import { useFileLoad } from '@/components/workspace/useFileLoad';
// ADR-236 Files page rework (2026-04-30): SubstrateEditor deleted. Direct
// inline editing of substrate files is removed per the original assessment
// ("not notion-like, streamline back to edit via Chat"). Every file now
// shows the EditInChatButton; substrate writes flow through chat (which
// invokes WriteFile(scope='workspace') per ADR-235).
// ADR-329 (amended) + ADR-388 follow-up: the full revision chain (with its
// revert affordance) moved out of the file body into the Get-Info modal — it
// was double-mounted; the modal is its single home. The file header still
// shows the head-revision author glance.
// ADR-309: the type→viewer association layer. Lifted out of this file's
// private getFileKind into the shared kernel-default table so every mount
// dispatches through one layer.
import { describeViewerApplication } from '@/lib/file-types';
import { cn } from '@/lib/utils';
import { formatAuthorLabel, authorAccent } from '@/lib/workspace/attribution';
import { operatorCanOrganize } from '@/lib/workspace/ownership';
import { useFileContextMenu, type FileVerbs } from '@/components/workspace/FileContextMenu';
import { useFeedback } from '@/contexts/FeedbackContext';
import type { WorkspaceTreeNode, WorkspaceFile } from '@/types';

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
  const { openMenu, menu, Kebab } = useFileContextMenu(verbs);
  const rowContext = (child: WorkspaceTreeNode) => (e: React.MouseEvent) => {
    if (verbs) {
      openMenu({ path: child.path, name: child.name, isFile: child.type === 'file' }, e);
    } else if (onGetInfo) {
      e.preventDefault();
      onGetInfo(child);
    }
  };
  // Touch parity (2026-07-12): a folder-listing row has the same verbs the
  // right-click menu offers; on a coarse pointer the kebab exposes them. Only
  // wired when `verbs` are present (the organize mount), matching rowContext.
  const rowKebab = (child: WorkspaceTreeNode) =>
    verbs ? <Kebab target={{ path: child.path, name: child.name, isFile: child.type === 'file' }} /> : undefined;
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
          → Get Info (D5); each row shows who last wrote it (D3).
          Finder-parity (2026-07-09): the icon view renders the SHARED <FileTile>
          — the same roomy tile + preview zone + radius the Recents grid uses, so
          a folder's files look identical whether reached via Recents or by
          browsing in. Tree nodes carry no blob, so file tiles show the format
          glyph (no thumbnail material here) with attribution as the subtext. */}
      {viewMode === 'icon' ? (
        <div className="grid grid-cols-2 gap-3 p-3 sm:grid-cols-3 lg:grid-cols-5">
          {children.map((child) => (
            <FileTile
              key={child.path}
              path={child.path}
              kind={child.type === 'folder' ? 'folder' : 'file'}
              onClick={() => onNavigate(child)}
              onContextMenu={rowContext(child)}
              actions={rowKebab(child)}
              subtext={
                <span className="inline-flex items-center gap-1">
                  <span className={cn('h-1.5 w-1.5 rounded-full', authorAccent((child as any).authored_by))} />
                  {formatAuthorLabel((child as any).authored_by)}
                </span>
              }
            />
          ))}
        </div>
      ) : (
        // Finder-parity (2026-07-09): the SHARED <FileListRow> details list —
        // same header + column model + row height as the Recents list view
        // (Name · Where · Author · When). A folder's rows all live in the same
        // folder, so the Where column stays empty; the file summary shows as the
        // name subtitle instead.
        <div className="overflow-hidden rounded-lg border border-border/60 mx-2 my-2">
          <FileListHeader />
          <div className="divide-y divide-border/40">
            {children.map((child) => (
              <FileListRow
                key={child.path}
                name={child.name}
                kind={child.type === 'folder' ? 'folder' : 'file'}
                subtitle={child.summary || undefined}
                when={formatTimestamp(child.updated_at)}
                author={
                  <span className="inline-flex items-center gap-1.5">
                    <span className={cn('h-1.5 w-1.5 rounded-full shrink-0', authorAccent((child as any).authored_by))} />
                    <span className="truncate">{formatAuthorLabel((child as any).authored_by)}</span>
                  </span>
                }
                onClick={() => onNavigate(child)}
                onContextMenu={rowContext(child)}
                actions={rowKebab(child)}
              />
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
  const { confirm, runAction } = useFeedback();
  const [deleting, setDeleting] = useState(false);
  // ADR-436 §6: the shared file-load hook (was a hand-written getFile + revision
  // state machine). `withRevision` fetches the ADR-209 Phase-4 head author in
  // parallel (surfaced on the header); a 404 is an honest `notFound` state (a
  // stale deep-link / synthetic node), distinct from a real load `error`.
  const { file, loading, notFound, error, headRevision } = useFileLoad(path, {
    withRevision: true,
  });

  // ADR-329/ADR-400 'delete' verb — trash-semantics (the backend archives via
  // lifecycle; ADR-209-retained, reversible; restorable from Trash). Operator-
  // owned only; the button is gated below on isOperatorDeletable (the shared
  // ownership topology), and the backend enforces the same scope (403 otherwise).
  const handleDelete = async () => {
    if (deleting) return;
    const ok = await confirm({
      title: 'Move to Trash?',
      body: 'It leaves your active workspace but stays recoverable — you can restore it from Trash any time.',
      confirmLabel: 'Move to Trash',
      danger: true,
    });
    if (!ok) return;
    setDeleting(true);
    try {
      await runAction(() => api.documents.delete(path), {
        pending: 'Moving to Trash…',
        success: 'Moved to Trash',
        error: (e) => (e instanceof APIError ? (e.data as { detail?: string })?.detail || 'Delete failed' : 'Delete failed'),
      });
      onDeleted?.();
    } catch {
      // error toast already surfaced by runAction
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

      <div className="p-4">
        {/* The one shared viewer (2026-07-09). The kind-switch + blob previews
            live in FileBody, which the chat surface's ArtifactCard mounts too.

            ADR-388 follow-up: the revision chain (ADR-209 provenance) moved
            OUT of the file body — it was double-mounted (here inline AND in the
            Get-Info modal). Singular home: Get Info (right-click or the header
            button). The file body shows content; "who wrote it" + the full
            history live one click away. */}
        <FileBody file={file} />
      </div>
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
