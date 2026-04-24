'use client';

/**
 * ContentViewer — Main panel explorer view
 *
 * Renders folder contents in a details-style listing and previews files using
 * type-aware viewers (markdown, HTML, image, PDF, data, text).
 */

import { useEffect, useMemo, useState } from 'react';
import { Download, ExternalLink, FileText, Folder, Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { EditInChatButton } from '@/components/shared/EditInChatButton';
import { FileIcon } from '@/components/workspace/FileIcon';
import { SubstrateEditor, isSubstrateEditable } from '@/components/workspace/SubstrateEditor';
import { InferenceContentView } from '@/components/context/InferenceContentView';
import type { WorkspaceTreeNode, WorkspaceFile } from '@/types';

// ADR-162 Sub-phase D / ADR-215: IDENTITY and BRAND files carry an
// `<!-- inference-meta: ... -->` comment injected by `_append_inference_meta()`
// on the backend. When rendered on Files, we surface that provenance (source
// caption + gap banner) above the markdown body via InferenceContentView.
const IDENTITY_PATH = '/workspace/context/_shared/IDENTITY.md';
const BRAND_PATH = '/workspace/context/_shared/BRAND.md';
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
   * ADR-215 R1 + R3: seed the chat rail for judgment-shaped edits. Never
   * invoked for substrate files (those render SubstrateEditor instead).
   */
  onOpenChatDraft?: (prompt: string) => void;
  /** Called after a successful inline substrate edit, so the host can refresh. */
  onSubstrateSaved?: () => void;
}

export function ContentViewer({
  selectedNode,
  onNavigate,
  showHeader = true,
  onOpenChatDraft,
  onSubstrateSaved,
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
      />
    );
  }

  return (
    <FileView
      path={selectedNode.path}
      showHeader={showHeader}
      onOpenChatDraft={onOpenChatDraft}
      onSubstrateSaved={onSubstrateSaved}
    />
  );
}

function DirectoryView({
  node,
  onNavigate,
  showHeader,
  onOpenChatDraft,
}: {
  node: WorkspaceTreeNode;
  onNavigate: (node: WorkspaceTreeNode) => void;
  showHeader: boolean;
  onOpenChatDraft?: (prompt: string) => void;
}) {
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

      <div className="px-2 py-2">
        <div className="grid grid-cols-[minmax(0,1fr)_140px_120px] gap-3 px-3 py-2 text-[11px] uppercase tracking-wide text-muted-foreground border-b border-border/60">
          <span>Name</span>
          <span>Kind</span>
          <span>Modified</span>
        </div>
        <div className="divide-y divide-border/50">
          {children.map((child) => (
            <button
              key={child.path}
              onClick={() => onNavigate(child)}
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
              <div className="text-xs text-muted-foreground self-center">
                {describeNodeKind(child)}
              </div>
              <div className="text-xs text-muted-foreground self-center">
                {formatTimestamp(child.updated_at)}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function FileView({
  path,
  showHeader,
  onOpenChatDraft,
  onSubstrateSaved,
}: {
  path: string;
  showHeader: boolean;
  onOpenChatDraft?: (prompt: string) => void;
  onSubstrateSaved?: () => void;
}) {
  const [file, setFile] = useState<WorkspaceFile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api.workspace
      .getFile(path)
      .then((data) => setFile(data))
      .catch((err) => setError(err.message || 'Failed to load file'))
      .finally(() => setLoading(false));
  }, [path, reloadKey]);

  const handleSubstrateSaved = () => {
    setReloadKey((k) => k + 1);
    onSubstrateSaved?.();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
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

  // ADR-215 R3: substrate-editable files render the editor even when empty,
  // so the operator can author their first content inline.
  const substrateEditable = file ? isSubstrateEditable(file.path) : false;

  if (!file || (!file.content && !file.content_url && !substrateEditable)) {
    return (
      <div className="p-6 text-center text-muted-foreground text-sm">
        <p>Empty file</p>
        <p className="text-xs mt-1">{path}</p>
      </div>
    );
  }

  const filename = file.path.split('/').pop() || file.path;
  const kind = getFileKind(file.path, file.content_type);

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
                <span>{describeFileKind(file.path, file.content_type)}</span>
                {file.updated_at && <span>{formatTimestamp(file.updated_at, true)}</span>}
                {file.content_type && <span>{file.content_type}</span>}
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {/* ADR-215 R3: substrate files get inline edit instead of chat redirect. */}
              {!substrateEditable && onOpenChatDraft && (
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
            </div>
          </div>
        </div>
      ) : file.content_url ? (
        <div className="flex justify-end px-4 pt-4">
          <FileActions contentUrl={file.content_url} />
        </div>
      ) : null}

      <div className="p-4 space-y-4">
        {substrateEditable && (
          <SubstrateEditor
            path={file.path}
            initialContent={file.content ?? ''}
            onSaved={handleSubstrateSaved}
          />
        )}

        {kind === 'markdown' && file.content && (() => {
          const target = inferenceTarget(file.path);
          if (target) {
            // ADR-162 Sub-phase D: IDENTITY/BRAND carry inference-meta comments
            // surfaced as a source caption + gap banner above the body.
            return <InferenceContentView content={file.content} target={target} />;
          }
          return (
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <MarkdownRenderer content={file.content} />
            </div>
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
              <img src={file.content_url} alt={filename} className="max-w-full h-auto mx-auto rounded-lg" />
            ) : (
              <div
                className="mx-auto max-w-full [&_svg]:h-auto [&_svg]:max-w-full"
                dangerouslySetInnerHTML={{ __html: file.content || '' }}
              />
            )}
          </div>
        )}

        {kind === 'pdf' && file.content_url && (
          <iframe
            title={filename}
            src={file.content_url}
            className="w-full min-h-[800px] rounded-xl border border-border bg-white"
          />
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
      </div>
    </div>
  );
}

function FileActions({ contentUrl }: { contentUrl: string }) {
  return (
    <div className="flex items-center gap-2 shrink-0">
      <a
        href={contentUrl}
        target="_blank"
        rel="noreferrer"
        className="inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground"
      >
        <ExternalLink className="w-3.5 h-3.5" />
        Open
      </a>
      <a
        href={contentUrl}
        download
        className="inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground"
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
  return describeFileKind(node.path);
}

function describeFileKind(path: string, contentType?: string): string {
  const kind = getFileKind(path, contentType);
  switch (kind) {
    case 'markdown':
      return 'Markdown';
    case 'html':
      return 'HTML report';
    case 'image':
      return 'Image';
    case 'pdf':
      return 'PDF';
    case 'csv':
      return 'CSV';
    case 'download':
      return 'Binary file';
    default:
      return 'Text';
  }
}

function getFileKind(path: string, contentType?: string): 'markdown' | 'html' | 'image' | 'pdf' | 'csv' | 'text' | 'download' {
  const lowerPath = path.toLowerCase();
  const lowerType = (contentType || '').toLowerCase();

  if (lowerPath.endsWith('.md')) return 'markdown';
  if (lowerPath.endsWith('.html') || lowerType.includes('text/html')) return 'html';
  if (
    lowerPath.endsWith('.png') ||
    lowerPath.endsWith('.jpg') ||
    lowerPath.endsWith('.jpeg') ||
    lowerPath.endsWith('.gif') ||
    lowerPath.endsWith('.webp') ||
    lowerPath.endsWith('.svg') ||
    lowerType.startsWith('image/')
  ) {
    return 'image';
  }
  if (lowerPath.endsWith('.pdf') || lowerType.includes('application/pdf')) return 'pdf';
  if (lowerPath.endsWith('.csv') || lowerType.includes('text/csv')) return 'csv';
  if (
    lowerPath.endsWith('.xlsx') ||
    lowerPath.endsWith('.xls') ||
    lowerPath.endsWith('.pptx') ||
    lowerPath.endsWith('.ppt')
  ) {
    return 'download';
  }
  return 'text';
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
