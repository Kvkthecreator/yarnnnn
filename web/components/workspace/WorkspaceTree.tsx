'use client';

/**
 * WorkspaceTree — Left panel file explorer
 *
 * Recursive tree component that mirrors workspace_files paths.
 * Click folder → expand/collapse. Click file → notify parent to open in main panel.
 */

import { useState } from 'react';
import { ChevronRight, ChevronDown, Folder, FileText, Bot, ListChecks } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { WorkspaceTreeNode } from '@/types';

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
          isSelected && "bg-accent text-accent-foreground",
        )}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {isFolder && icon}
        {!isFolder && <span className="w-3.5" />}
        {fileIcon}
        <span className="truncate flex-1">{node.name}</span>
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

function getFileIcon(node: WorkspaceTreeNode) {
  const path = node.path.toLowerCase();

  if (node.type === 'folder') {
    if (path.includes('/agents/')) return <Bot className="w-3.5 h-3.5 text-purple-500" />;
    if (path.includes('/tasks/')) return <ListChecks className="w-3.5 h-3.5 text-orange-500" />;
    if (path.includes('/context/')) return <Folder className="w-3.5 h-3.5 text-blue-500" />;
    if (path.includes('/outputs/')) return <Folder className="w-3.5 h-3.5 text-green-500" />;
    return <Folder className="w-3.5 h-3.5 text-muted-foreground" />;
  }

  return <FileText className="w-3.5 h-3.5 text-muted-foreground" />;
}
