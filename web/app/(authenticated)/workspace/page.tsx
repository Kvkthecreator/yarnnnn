'use client';

/**
 * Workspace Explorer — Three-panel layout
 *
 * Left: File tree (WorkspaceTree)
 * Main: Content viewer (DirectoryView, FileViewer)
 * Right: Scoped chat (TP with navigation context)
 *
 * The filesystem IS the navigation. URL query param `path` tracks selection.
 */

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2, PanelLeftClose, PanelLeft, MessageCircle, X } from 'lucide-react';
import { api } from '@/lib/api/client';
import { WorkspaceTree } from '@/components/workspace/WorkspaceTree';
import { ContentViewer } from '@/components/workspace/ContentViewer';
// TP chat integration will be added when chat component is wired into right panel
import { cn } from '@/lib/utils';
import type { WorkspaceTreeNode } from '@/types';

export default function WorkspacePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedPath = searchParams.get('path') || '';

  const [trees, setTrees] = useState<{ workspace: WorkspaceTreeNode[]; agents: WorkspaceTreeNode[]; tasks: WorkspaceTreeNode[] }>({
    workspace: [],
    agents: [],
    tasks: [],
  });
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<WorkspaceTreeNode | null>(null);
  const [leftPanelOpen, setLeftPanelOpen] = useState(true);
  const [rightPanelOpen, setRightPanelOpen] = useState(true);

  // Load all three root trees
  useEffect(() => {
    async function loadTrees() {
      setLoading(true);
      try {
        const [workspace, agents, tasks] = await Promise.all([
          api.workspace.getTree('/workspace'),
          api.workspace.getTree('/agents'),
          api.workspace.getTree('/tasks'),
        ]);
        setTrees({ workspace, agents, tasks });
      } catch (err) {
        console.error('Failed to load workspace tree:', err);
      } finally {
        setLoading(false);
      }
    }
    loadTrees();
  }, []);

  // Handle node selection — update URL and selected node
  const handleSelect = useCallback((node: WorkspaceTreeNode) => {
    setSelectedNode(node);
    const params = new URLSearchParams(searchParams.toString());
    params.set('path', node.path);
    router.replace(`/workspace?${params.toString()}`, { scroll: false });
  }, [router, searchParams]);

  // Handle navigation from content viewer (e.g., clicking a folder item)
  const handleNavigate = useCallback((node: WorkspaceTreeNode) => {
    handleSelect(node);
  }, [handleSelect]);

  // Navigation context for TP chat — passed when sending messages
  // The chat component (when integrated) will use this as surface_context
  const navigationContext = selectedNode ? {
    type: 'workspace-explorer' as const,
    path: selectedNode.path,
    navigation_type: selectedNode.type,
    domain: extractDomain(selectedNode.path) || undefined,
    entity: extractEntity(selectedNode.path) || undefined,
    taskSlug: extractTaskSlug(selectedNode.path) || undefined,
    agentSlug: extractAgentSlug(selectedNode.path) || undefined,
  } : null;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Left Panel — File Explorer */}
      {leftPanelOpen && (
        <div className="w-64 border-r border-border flex flex-col shrink-0">
          <div className="flex items-center justify-between px-3 py-2 border-b border-border">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Explorer</span>
            <button onClick={() => setLeftPanelOpen(false)} className="text-muted-foreground hover:text-foreground">
              <PanelLeftClose className="w-4 h-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto py-1">
            {/* Workspace root */}
            <div className="px-2 py-1">
              <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Workspace</span>
            </div>
            <WorkspaceTree nodes={trees.workspace} selectedPath={selectedPath} onSelect={handleSelect} />

            {/* Agents root */}
            <div className="px-2 py-1 mt-2">
              <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Agents</span>
            </div>
            <WorkspaceTree nodes={trees.agents} selectedPath={selectedPath} onSelect={handleSelect} />

            {/* Tasks root */}
            <div className="px-2 py-1 mt-2">
              <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Tasks</span>
            </div>
            <WorkspaceTree nodes={trees.tasks} selectedPath={selectedPath} onSelect={handleSelect} />
          </div>
        </div>
      )}

      {/* Toggle left panel when collapsed */}
      {!leftPanelOpen && (
        <button
          onClick={() => setLeftPanelOpen(true)}
          className="absolute left-2 top-14 z-10 p-1.5 bg-background border border-border rounded-md hover:bg-accent"
        >
          <PanelLeft className="w-4 h-4" />
        </button>
      )}

      {/* Main Panel — Content Viewer */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {/* Breadcrumb */}
        <div className="px-4 py-2 border-b border-border text-xs text-muted-foreground">
          {selectedNode ? selectedNode.path : '/'}
        </div>
        <div className="flex-1 overflow-auto">
          <ContentViewer selectedNode={selectedNode} onNavigate={handleNavigate} />
        </div>
      </div>

      {/* Right Panel — Chat */}
      {rightPanelOpen && (
        <div className="w-96 border-l border-border flex flex-col shrink-0">
          <div className="flex items-center justify-between px-3 py-2 border-b border-border">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Chat</span>
            <button onClick={() => setRightPanelOpen(false)} className="text-muted-foreground hover:text-foreground">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="flex-1 overflow-hidden">
            {/* TP Chat component — reuse existing chat infrastructure */}
            <div className="flex items-center justify-center h-full text-muted-foreground text-xs">
              Chat panel — integrate existing TP chat component
            </div>
          </div>
        </div>
      )}

      {/* Toggle right panel when collapsed */}
      {!rightPanelOpen && (
        <button
          onClick={() => setRightPanelOpen(true)}
          className="absolute right-2 top-14 z-10 p-1.5 bg-background border border-border rounded-md hover:bg-accent"
        >
          <MessageCircle className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

// =============================================================================
// Path parsing helpers
// =============================================================================

function extractDomain(path: string): string | null {
  const match = path.match(/\/workspace\/context\/([^/]+)/);
  return match ? match[1] : null;
}

function extractEntity(path: string): string | null {
  const match = path.match(/\/workspace\/context\/[^/]+\/([^/]+)\//);
  return match ? match[1] : null;
}

function extractTaskSlug(path: string): string | null {
  const match = path.match(/\/tasks\/([^/]+)/);
  return match ? match[1] : null;
}

function extractAgentSlug(path: string): string | null {
  const match = path.match(/\/agents\/([^/]+)/);
  return match ? match[1] : null;
}
