'use client';

/**
 * WorkspaceTree — Left panel file explorer
 *
 * Recursive tree component that mirrors workspace_files paths.
 * Click folder → expand/collapse. Click file → notify parent to open in main panel.
 */

import { useEffect, useState } from 'react';
import { ChevronRight, ChevronDown, Folder, Bot, ListChecks, Settings, Upload, Boxes } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { WorkspaceTreeNode } from '@/types';
import { FileIcon } from '@/components/workspace/FileIcon';
import { FileContextMenu, type FileMenuTarget } from '@/components/workspace/FileContextMenu';

interface WorkspaceTreeProps {
  nodes: WorkspaceTreeNode[];
  selectedPath?: string;
  onSelect: (node: WorkspaceTreeNode) => void;
  /**
   * Right-click "Properties" → open the node Details panel (ADR-400).
   */
  onGetInfo?: (node: WorkspaceTreeNode) => void;
  /**
   * ADR-400 operator verbs — the human reorganizes their workspace. The menu is
   * OPTIMISTIC (Amendment 1): it offers the verb; the parent's handler + the
   * backend decide + surface an honest error on the rare carve. No defensive
   * greying.
   */
  onRename?: (node: WorkspaceTreeNode) => void;
  onMove?: (node: WorkspaceTreeNode) => void;
  onDelete?: (node: WorkspaceTreeNode) => void;
}

interface ContextMenuState {
  target: FileMenuTarget;
  node: WorkspaceTreeNode;
  x: number;
  y: number;
}

export function WorkspaceTree({ nodes, selectedPath, onSelect, onGetInfo, onRename, onMove, onDelete }: WorkspaceTreeProps) {
  const [menu, setMenu] = useState<ContextMenuState | null>(null);

  const hasMenu = !!(onGetInfo || onRename || onMove || onDelete);
  const openMenu = hasMenu
    ? (node: WorkspaceTreeNode, e: React.MouseEvent) => {
        e.preventDefault();
        setMenu({
          target: { path: node.path, name: node.name, isFile: node.type === 'file' },
          node, x: e.clientX, y: e.clientY,
        });
      }
    : undefined;

  return (
    <div className="text-sm">
      {nodes.map((node) => (
        <TreeItem
          key={node.path}
          node={node}
          depth={0}
          selectedPath={selectedPath}
          onSelect={onSelect}
          onContextMenu={openMenu}
        />
      ))}

      {menu && (
        <FileContextMenu
          target={menu.target}
          x={menu.x}
          y={menu.y}
          onClose={() => setMenu(null)}
          onOpen={() => onSelect(menu.node)}
          onProperties={onGetInfo ? () => onGetInfo(menu.node) : undefined}
          onRename={onRename ? () => onRename(menu.node) : undefined}
          onMove={onMove ? () => onMove(menu.node) : undefined}
          onDelete={onDelete ? () => onDelete(menu.node) : undefined}
        />
      )}
    </div>
  );
}

interface TreeItemProps {
  node: WorkspaceTreeNode;
  depth: number;
  selectedPath?: string;
  onSelect: (node: WorkspaceTreeNode) => void;
  onContextMenu?: (node: WorkspaceTreeNode, e: React.MouseEvent) => void;
}

// A `_`-prefixed file is machine-config / accumulated system state (per the
// File Format Discipline: _autonomy.yaml, _principles.yaml, _tracker.md,
// _account.yaml, …). ADR-320 correction (2026-06-10): these are no longer
// HIDDEN — the tree must be able to follow a deep-link or Get-Info into them
// (Home/cockpit link straight to _account.yaml etc.). They render
// de-emphasized so the operator can tell system-state from authored prose at
// a glance, without the tree lying about what exists.
function isSystemFile(node: WorkspaceTreeNode): boolean {
  if (node.type !== 'file') return false;
  const filename = node.path.split('/').pop() || '';
  return filename.startsWith('_');
}

function TreeItem({ node, depth, selectedPath, onSelect, onContextMenu }: TreeItemProps) {
  const [expanded, setExpanded] = useState(depth < 1); // Auto-expand first level
  const isFolder = node.type === 'folder';
  const isSelected = selectedPath === node.path;
  const isSystem = isSystemFile(node);

  useEffect(() => {
    if (isFolder && selectedPath && nodeContainsPath(node, selectedPath)) {
      setExpanded(true);
    }
  }, [isFolder, node, selectedPath]);

  const handleClick = () => {
    if (isFolder) {
      setExpanded(!expanded);
    }
    onSelect(node);
  };

  // Icon based on path/type
  const icon = isFolder ? (
    expanded ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" /> : <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
  ) : null;

  const fileIcon = getFileIcon(node);

  return (
    <div>
      <button
        onClick={handleClick}
        onContextMenu={onContextMenu ? (e) => onContextMenu(node, e) : undefined}
        className={cn(
          "w-full flex items-center gap-1.5 py-1 px-2 rounded-sm text-left hover:bg-accent/50 transition-colors",
          isSelected && "bg-primary/10 text-primary font-medium",
          // ADR-320 correction: machine-config files render de-emphasized
          // (dimmer text) rather than hidden — present but visibly secondary.
          isSystem && !isSelected && "text-muted-foreground/55",
        )}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {isFolder && icon}
        {!isFolder && <span className="w-3.5" />}
        {fileIcon}
        <span className="truncate flex-1">{node.name}</span>
        {/* System-file tag — disambiguates machine-config from authored prose
            at a glance (the de-emphasis + tag carry the distinction the old
            hide-rule used to carry by omission). */}
        {isSystem && (
          <span className="shrink-0 text-[9px] uppercase tracking-wide text-muted-foreground/40 ml-1">
            sys
          </span>
        )}
        {/* ADR-388 follow-up: author dots removed from the tree. An unlabeled
            color dot is a riddle — "who wrote it" now lives where it's a full
            legible label (the file header + the Get-Info modal), not a color
            the operator must decode. The tree is for navigation. */}
      </button>
      {isFolder && expanded && node.children && (
        <div>
          {node.children.map((child) => (
            <TreeItem
              key={child.path}
              node={child}
              depth={depth + 1}
              selectedPath={selectedPath}
              onSelect={onSelect}
              onContextMenu={onContextMenu}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function nodeContainsPath(node: WorkspaceTreeNode, targetPath: string): boolean {
  if (node.path === targetPath) return true;
  for (const child of node.children || []) {
    if (nodeContainsPath(child, targetPath)) return true;
  }
  return false;
}

function getFileIcon(node: WorkspaceTreeNode) {
  const path = node.path.toLowerCase();

  if (node.type === 'folder') {
    // Top-level group nodes (virtual /explorer/* paths + real ADR-320 roots).
    if (path === '/explorer/settings') return <Settings className="w-3.5 h-3.5 text-slate-500" />;
    if (path === '/explorer/context') return <Boxes className="w-3.5 h-3.5 text-sky-600" />;
    if (path === '/explorer/outputs') return <ListChecks className="w-3.5 h-3.5 text-orange-500" />;
    if (path === '/explorer/uploads' || path === '/workspace/uploads') return <Upload className="w-3.5 h-3.5 text-emerald-600" />;
    if (path === '/workspace/persona') return <Bot className="w-3.5 h-3.5 text-rose-500" />;
    if (path === '/workspace/system') return <Settings className="w-3.5 h-3.5 text-zinc-500" />;
    if (path === '/workspace/agents') return <Bot className="w-3.5 h-3.5 text-purple-500" />;
    // Substrate folder children (ADR-320 topology).
    if (path.includes('/agents/')) return <Bot className="w-3.5 h-3.5 text-purple-500" />;
    if (path.includes('/operation/reports/')) return <ListChecks className="w-3.5 h-3.5 text-orange-500" />;
    if (path.startsWith('/workspace/operation/')) return <Folder className="w-3.5 h-3.5 text-blue-500" />;
    return <Folder className="w-3.5 h-3.5 text-muted-foreground" />;
  }

  return <FileIcon filename={node.name} size="sm" />;
}
