'use client';

/**
 * GetInfoModal — the macOS Get-Info / Explorer-Properties idiom for a
 * workspace file or folder (ADR-388 D5).
 *
 * Opened by right-click → "Get Info" on any file/folder row or tile (replacing
 * the old inline "Details" button). Wraps the existing NodeDetailsPanel — which
 * already renders path/type/when + the ADR-209 revision chain (who wrote each
 * version, when, with what message) for files, and the recent-revisions list
 * for folders — in a centered modal. The attribution story (the interop-wedge
 * "ChatGPT (via MCP) wrote v2") is first-class here.
 *
 * Reuses the standard modal shell (backdrop + Escape + centered card) — there
 * is no shared Dialog primitive in the codebase, so this matches the
 * SetupConfirmModal pattern.
 */

import { useEffect } from 'react';
import { X } from 'lucide-react';
import { NodeDetailsPanel } from '@/components/workspace/NodeDetailsPanel';
import type { WorkspaceTreeNode } from '@/types';

interface GetInfoModalProps {
  node: WorkspaceTreeNode | null;
  onClose: () => void;
  onSelectPath?: (path: string) => void;
  onRevert?: () => void;
}

export function GetInfoModal({ node, onClose, onSelectPath, onRevert }: GetInfoModalProps) {
  useEffect(() => {
    if (!node) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [node, onClose]);

  if (!node) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative z-10 w-full max-w-md mx-4 max-h-[80vh] overflow-y-auto rounded-lg border border-border bg-background shadow-lg">
        <div className="sticky top-0 flex items-center justify-between border-b border-border bg-background/95 px-4 py-3 backdrop-blur">
          <h2 className="truncate text-sm font-semibold">
            Get Info — {node.name}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-4">
          <NodeDetailsPanel node={node} onSelectPath={onSelectPath} onRevert={onRevert} />
        </div>
      </div>
    </div>
  );
}
