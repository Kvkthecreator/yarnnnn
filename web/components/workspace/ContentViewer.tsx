'use client';

/**
 * ContentViewer — Main panel content display
 *
 * Renders different views based on what's selected:
 * - Directory → file listing
 * - Markdown file → rendered markdown
 * - Task folder → task detail (redirect or inline)
 * - Agent folder → agent detail
 */

import { useEffect, useState } from 'react';
import { FileText, Folder, Clock, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import type { WorkspaceTreeNode, WorkspaceFile } from '@/types';

interface ContentViewerProps {
  selectedNode: WorkspaceTreeNode | null;
  onNavigate: (node: WorkspaceTreeNode) => void;
}

export function ContentViewer({ selectedNode, onNavigate }: ContentViewerProps) {
  if (!selectedNode) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        Select a file or folder from the explorer
      </div>
    );
  }

  if (selectedNode.type === 'folder') {
    return <DirectoryView node={selectedNode} onNavigate={onNavigate} />;
  }

  return <FileView path={selectedNode.path} />;
}

// =============================================================================
// Directory View — file listing for folders
// =============================================================================

function DirectoryView({
  node,
  onNavigate,
}: {
  node: WorkspaceTreeNode;
  onNavigate: (node: WorkspaceTreeNode) => void;
}) {
  const children = node.children || [];

  if (children.length === 0) {
    return (
      <div className="p-6 text-center text-muted-foreground text-sm">
        <Folder className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p>Empty folder</p>
        <p className="text-xs mt-1">{node.path}</p>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="mb-4">
        <h2 className="text-lg font-medium">{node.name}</h2>
        <p className="text-xs text-muted-foreground">{node.path}</p>
      </div>
      <div className="space-y-1">
        {children.map((child) => (
          <button
            key={child.path}
            onClick={() => onNavigate(child)}
            className="w-full flex items-center gap-3 py-2 px-3 rounded-md hover:bg-accent/50 transition-colors text-left"
          >
            {child.type === 'folder' ? (
              <Folder className="w-4 h-4 text-blue-500 shrink-0" />
            ) : (
              <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{child.name}</p>
              {child.summary && (
                <p className="text-xs text-muted-foreground truncate">{child.summary}</p>
              )}
            </div>
            {child.updated_at && (
              <span className="text-xs text-muted-foreground flex items-center gap-1 shrink-0">
                <Clock className="w-3 h-3" />
                {child.updated_at.slice(0, 10)}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

// =============================================================================
// File View — markdown renderer for files
// =============================================================================

function FileView({ path }: { path: string }) {
  const [file, setFile] = useState<WorkspaceFile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api.workspace
      .getFile(path)
      .then((data) => setFile(data))
      .catch((err) => setError(err.message || 'Failed to load file'))
      .finally(() => setLoading(false));
  }, [path]);

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

  if (!file || !file.content) {
    return (
      <div className="p-6 text-center text-muted-foreground text-sm">
        <p>Empty file</p>
        <p className="text-xs mt-1">{path}</p>
      </div>
    );
  }

  return (
    <div className="p-4 overflow-auto h-full">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium">{path.split('/').pop()}</h2>
          <p className="text-xs text-muted-foreground">{path}</p>
        </div>
        {file.updated_at && (
          <span className="text-xs text-muted-foreground">
            Updated {file.updated_at.slice(0, 16).replace('T', ' ')}
          </span>
        )}
      </div>
      <div className="prose prose-sm dark:prose-invert max-w-none">
        <MarkdownRenderer content={file.content} />
      </div>
    </div>
  );
}
