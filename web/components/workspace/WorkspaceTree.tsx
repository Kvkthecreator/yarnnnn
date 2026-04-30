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

interface WorkspaceTreeProps {
  nodes: WorkspaceTreeNode[];
  selectedPath?: string;
  onSelect: (node: WorkspaceTreeNode) => void;
}

export function WorkspaceTree({ nodes, selectedPath, onSelect }: WorkspaceTreeProps) {
  return (
    <div className="text-sm">
      {nodes.map((node) => (
        <TreeItem
          key={node.path}
          node={node}
          depth={0}
          selectedPath={selectedPath}
          onSelect={onSelect}
        />
      ))}
    </div>
  );
}

interface TreeItemProps {
  node: WorkspaceTreeNode;
  depth: number;
  selectedPath?: string;
  onSelect: (node: WorkspaceTreeNode) => void;
}

function TreeItem({ node, depth, selectedPath, onSelect }: TreeItemProps) {
  const [expanded, setExpanded] = useState(depth < 1); // Auto-expand first level
  const isFolder = node.type === 'folder';
  const isSelected = selectedPath === node.path;

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
        className={cn(
          "w-full flex items-center gap-1.5 py-1 px-2 rounded-sm text-left hover:bg-accent/50 transition-colors",
          isSelected && "bg-primary/10 text-primary font-medium",
        )}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {isFolder && icon}
        {!isFolder && <span className="w-3.5" />}
        {fileIcon}
        <span className="truncate flex-1">{node.name}</span>
        {/* ADR-209: authored_by from head revision — compact right-edge
            label so the operator can see at a glance who last touched
            each file without opening it. Only shown for file nodes
            (not folders) when authored_by is populated. */}
        {!isFolder && node.authored_by && (
          <span className="shrink-0 text-[9px] text-muted-foreground/40 ml-1">
            {node.authored_by === 'operator' ? 'You'
              : node.authored_by.startsWith('yarnnn:') ? 'TP'
              : node.authored_by.startsWith('agent:') ? 'Agent'
              : node.authored_by.startsWith('specialist:') ? 'Spec.'
              : node.authored_by.startsWith('reviewer:') ? 'Rev.'
              : node.authored_by.startsWith('system:') ? 'Sys'
              : null}
          </span>
        )}
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
  const name = node.name.toLowerCase();

  if (node.type === 'folder') {
    if (path === '/explorer/tasks') return <ListChecks className="w-3.5 h-3.5 text-orange-500" />;
    if (path === '/explorer/domains') return <Boxes className="w-3.5 h-3.5 text-sky-600" />;
    if (path === '/explorer/uploads') return <Upload className="w-3.5 h-3.5 text-emerald-600" />;
    if (path === '/explorer/settings') return <Settings className="w-3.5 h-3.5 text-slate-500" />;
    if (path.includes('/agents/')) return <Bot className="w-3.5 h-3.5 text-purple-500" />;
    if (path.includes('/tasks/')) return <ListChecks className="w-3.5 h-3.5 text-orange-500" />;
    if (path.includes('/context/')) return <Folder className="w-3.5 h-3.5 text-blue-500" />;
    if (path.includes('/outputs/')) return <Folder className="w-3.5 h-3.5 text-green-500" />;
    if (name === 'uploads') return <Upload className="w-3.5 h-3.5 text-emerald-600" />;
    if (name === 'settings') return <Settings className="w-3.5 h-3.5 text-slate-500" />;
    return <Folder className="w-3.5 h-3.5 text-muted-foreground" />;
  }

  return <FileIcon filename={node.name} size="sm" />;
}
