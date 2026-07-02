'use client';

/**
 * PropertiesModal — the Windows-Explorer "Properties" dialog for a workspace
 * file or folder (ADR-388 D5, renamed from "Get Info" per ADR-400).
 *
 * Opened by right-click → "Properties" on any file/folder row or tile. Wraps
 * NodeDetailsPanel — which renders the flat Properties block (Kind · Location ·
 * Ownership · Modified · Contributors) + the ADR-209 revision history for files,
 * and the recent-changes aggregate for folders. Ownership (ADR-400 two-principal)
 * + the interop attribution ("ChatGPT via MCP wrote v2") are first-class here.
 *
 * "Properties" (Explorer) over "Get Info" (macOS): more universally readable,
 * consistent with the GitHub+Copilot Files direction (ADR-400).
 *
 * Reuses the standard modal shell (backdrop + Escape + centered card) — there
 * is no shared Dialog primitive in the codebase, so this matches the
 * SetupConfirmModal pattern.
 */

import { useEffect } from 'react';
import { X } from 'lucide-react';
import { NodeDetailsPanel } from '@/components/workspace/NodeDetailsPanel';
import type { WorkspaceTreeNode } from '@/types';

interface PropertiesModalProps {
  node: WorkspaceTreeNode | null;
  onClose: () => void;
  onSelectPath?: (path: string) => void;
  onRevert?: () => void;
}

export function PropertiesModal({ node, onClose, onSelectPath, onRevert }: PropertiesModalProps) {
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
            Properties — {node.name}
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
