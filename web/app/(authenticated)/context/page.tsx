'use client';

/**
 * Context Surface — Workspace explorer (domains, uploads, settings)
 *
 * Finder / Windows Explorer mental model:
 * - Left: hierarchical workspace tree (collapsible)
 * - Center: folder details view + type-aware file preview
 * - Right: TP chat drawer (collapsible, context-aware)
 *
 * Tasks are NOT in this explorer — they have their own surface at /tasks.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Loader2,
  X,
  MessageCircle,
  Upload,
  Globe,
  Settings2,
  ListChecks,
  FolderOpen,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useDesk } from '@/contexts/DeskContext';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { WorkspaceTree } from '@/components/workspace/WorkspaceTree';
import { ContentViewer } from '@/components/workspace/ContentViewer';
import { ChatPanel } from '@/components/tp/ChatPanel';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';

type TreeNode = import('@/types').WorkspaceTreeNode;

const EXPLORER_ROOT_PATH = '/explorer';

function asNodeArray(value: unknown): TreeNode[] {
  return Array.isArray(value) ? value as TreeNode[] : [];
}

function relabelTopLevelNodes(nodes: TreeNode[] | undefined, labelMap: Record<string, string>): TreeNode[] {
  return asNodeArray(nodes).map((node) => ({
    ...node,
    name: labelMap[node.name] || node.name,
  }));
}

function filterNodes(nodes: TreeNode[] | undefined, predicate: (node: TreeNode) => boolean): TreeNode[] {
  return asNodeArray(nodes)
    .filter(predicate)
    .map((node) => ({
      ...node,
      children: node.children ? filterNodes(node.children, predicate) : undefined,
    }));
}

function resolveNodeByPath(root: TreeNode, targetPath: string): TreeNode | null {
  if (root.path === targetPath) return root;
  for (const child of root.children || []) {
    const match = resolveNodeByPath(child, targetPath);
    if (match) return match;
  }
  return null;
}

function buildBreadcrumbs(root: TreeNode, targetPath: string): TreeNode[] {
  const trail: TreeNode[] = [];
  function walk(node: TreeNode): boolean {
    trail.push(node);
    if (node.path === targetPath) return true;
    for (const child of node.children || []) {
      if (walk(child)) return true;
    }
    trail.pop();
    return false;
  }
  walk(root);
  return trail;
}

function buildContextNodes(input: {
  domainTree?: TreeNode[];
  uploadTree?: TreeNode[];
  domainTitles: Record<string, string>;
  settings?: Array<{ name: string; filename: string; path: string; updated_at: string | null }>;
}): TreeNode[] {
  const domainChildren = relabelTopLevelNodes(
    filterNodes(input.domainTree, (node) => {
      const lower = node.path.toLowerCase();
      return !lower.endsWith('/_tracker.md') && !lower.startsWith('/workspace/context/signals');
    }),
    input.domainTitles
  );
  const uploadChildren = asNodeArray(input.uploadTree);
  const settingsFiles = Array.isArray(input.settings) ? input.settings : [];

  return [
    {
      name: 'Context',
      path: `${EXPLORER_ROOT_PATH}/context`,
      type: 'folder' as const,
      summary: domainChildren.length ? `${domainChildren.length} domains` : 'No domains yet',
      children: domainChildren,
    },
    {
      name: 'Uploads',
      path: `${EXPLORER_ROOT_PATH}/uploads`,
      type: 'folder' as const,
      summary: uploadChildren.length ? `${uploadChildren.length} items` : 'No uploads yet',
      children: uploadChildren,
    },
    {
      name: 'Settings',
      path: `${EXPLORER_ROOT_PATH}/settings`,
      type: 'folder' as const,
      summary: settingsFiles.length ? `${settingsFiles.length} files` : 'No settings files yet',
      children: settingsFiles.map((file) => ({
        name: file.filename,
        path: file.path,
        type: 'file' as const,
        updated_at: file.updated_at || undefined,
        summary: file.name,
      })),
    },
  ];
}

// =============================================================================
// Context Page
// =============================================================================

export default function ContextPage() {
  const { loadScopedHistory, sendMessage } = useTP();
  const { surface } = useDesk();

  const [treeNodes, setTreeNodes] = useState<TreeNode[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [fileTreeLoading, setFileTreeLoading] = useState(false);

  // Virtual root for resolveNodeByPath/buildBreadcrumbs (not displayed)
  const virtualRoot: TreeNode = { name: 'root', path: EXPLORER_ROOT_PATH, type: 'folder', children: treeNodes };

  const loadExplorer = useCallback(async () => {
    setFileTreeLoading(true);
    try {
      const [nav, domainTree, uploadTree] = await Promise.all([
        api.workspace.getNav(),
        api.workspace.getTree('/workspace/context'),
        api.workspace.getTree('/workspace/uploads'),
      ]);

      const navDomains = Array.isArray(nav?.domains) ? nav.domains : [];
      const domainTitles = Object.fromEntries(navDomains.map((domain: any) => [domain.key, domain.display_name]));
      const nodes = buildContextNodes({
        domainTree: asNodeArray(domainTree),
        uploadTree: asNodeArray(uploadTree),
        domainTitles,
        settings: Array.isArray(nav?.settings) ? nav.settings : [],
      });

      setTreeNodes(nodes);
      // Don't auto-select root — let user pick from tree
      setSelectedPath((prev) => {
        if (prev) {
          const root: TreeNode = { name: 'root', path: EXPLORER_ROOT_PATH, type: 'folder', children: nodes };
          if (resolveNodeByPath(root, prev)) return prev;
        }
        return null;
      });
    } catch (err) {
      console.error('Failed to load explorer:', err);
    } finally {
      setFileTreeLoading(false);
    }
  }, []);

  const selectedNode = selectedPath ? resolveNodeByPath(virtualRoot, selectedPath) : null;
  const breadcrumbs = selectedNode ? buildBreadcrumbs(virtualRoot, selectedNode.path).filter(n => n.path !== EXPLORER_ROOT_PATH) : [];

  const effectiveSurface = selectedNode
    ? {
        ...surface,
        type: 'workspace-explorer' as const,
        path: selectedNode.path,
        navigation_type: selectedNode.type,
      }
    : surface;

  const [panelOpen, setPanelOpen] = useState(true);
  const [chatOpen, setChatOpen] = useState(false);

  useEffect(() => { loadScopedHistory(); }, [loadScopedHistory]);

  useEffect(() => {
    loadExplorer();
    const interval = setInterval(loadExplorer, 30000);
    const onFocus = () => { if (document.visibilityState === 'visible') loadExplorer(); };
    document.addEventListener('visibilitychange', onFocus);
    return () => { clearInterval(interval); document.removeEventListener('visibilitychange', onFocus); };
  }, [loadExplorer]);

  const handleExplorerSelect = useCallback((node: TreeNode) => {
    setSelectedPath(node.path);
  }, []);

  const plusMenuActions: PlusMenuAction[] = [
    { id: 'create-task', label: 'Create a task', icon: ListChecks, verb: 'prompt', onSelect: () => { sendMessage('I want to create a task. What do you suggest based on my context?', { surface: effectiveSurface }); } },
    { id: 'update-info', label: 'Update my info', icon: Settings2, verb: 'prompt', onSelect: () => { setChatOpen(true); } },
    { id: 'web-search', label: 'Web search', icon: Globe, verb: 'prompt', onSelect: () => { setChatOpen(true); } },
    { id: 'upload-file', label: 'Upload file', icon: Upload, verb: 'attach', onSelect: () => { } },
  ];

  const emptyState = (
    <div className="space-y-3">
      <div className="text-center">
        <MessageCircle className="w-5 h-5 text-muted-foreground/15 mx-auto mb-1.5" />
        <p className="text-[11px] text-muted-foreground/40">Ask about your workspace</p>
      </div>
      <div className="flex flex-col gap-1.5">
        <button
          onClick={() => { sendMessage('What context do my agents have?', { surface: effectiveSurface }); }}
          className="text-left text-[11px] px-3 py-2 rounded-lg border border-border/50 text-muted-foreground hover:text-foreground hover:border-border hover:bg-muted/50 transition-colors"
        >
          What context do my agents have?
        </button>
        <button
          onClick={() => { sendMessage('Update my company information', { surface: effectiveSurface }); }}
          className="text-left text-[11px] px-3 py-2 rounded-lg border border-border/50 text-muted-foreground hover:text-foreground hover:border-border hover:bg-muted/50 transition-colors"
        >
          Update my company information
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left: Explorer panel */}
      {panelOpen ? (
        <div className="w-[280px] shrink-0 border-r border-border flex flex-col bg-background">
          <div className="flex items-center justify-between px-3 py-2 border-b border-border shrink-0">
            <div>
              <p className="text-sm font-medium text-foreground">Explorer</p>
              <p className="text-[11px] text-muted-foreground">Workspace context and settings</p>
            </div>
            <button onClick={() => setPanelOpen(false)} className="p-1 text-muted-foreground/40 hover:text-muted-foreground rounded">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {fileTreeLoading && treeNodes.length === 0 ? (
              <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Loading...
              </div>
            ) : treeNodes.length > 0 ? (
              <div className="p-2">
                <WorkspaceTree
                  nodes={treeNodes}
                  selectedPath={selectedPath || undefined}
                  onSelect={handleExplorerSelect}
                />
              </div>
            ) : (
              <div className="p-3 text-sm text-muted-foreground">Failed to load explorer</div>
            )}
          </div>
        </div>
      ) : (
        <div className="w-10 shrink-0 border-r border-border flex flex-col items-center py-2 gap-2 bg-background">
          <button
            onClick={() => setPanelOpen(true)}
            className="p-2 rounded-md text-muted-foreground/50 hover:text-foreground hover:bg-muted transition-colors"
            title="Explorer"
          >
            <FolderOpen className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Center: Content viewer */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {selectedNode ? (
          <div className="flex-1 overflow-auto bg-background flex flex-col">
            <div className="flex items-center gap-1 px-4 py-2 border-b border-border shrink-0 overflow-x-auto">
              {breadcrumbs.map((crumb, index) => (
                <div key={crumb.path} className="flex items-center gap-1 shrink-0">
                  {index > 0 && <span className="text-xs text-muted-foreground/40">/</span>}
                  <button
                    onClick={() => setSelectedPath(crumb.path)}
                    className={cn(
                      'rounded px-1.5 py-0.5 text-xs hover:bg-muted/60',
                      crumb.path === selectedNode.path ? 'text-foreground font-medium' : 'text-muted-foreground'
                    )}
                  >
                    {crumb.name}
                  </button>
                </div>
              ))}
              <span className="ml-auto shrink-0 text-[11px] text-muted-foreground">
                {selectedNode.type === 'folder'
                  ? `${selectedNode.children?.length || 0} items`
                  : selectedNode.path.split('.').pop()?.toUpperCase() || 'FILE'}
              </span>
            </div>
            <div className="flex-1 overflow-auto">
              <ContentViewer selectedNode={selectedNode} onNavigate={handleExplorerSelect} />
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-xs">
              <FolderOpen className="w-8 h-8 text-muted-foreground/15 mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">Select a file or folder from the explorer</p>
            </div>
          </div>
        )}
      </div>

      {/* Right: Chat panel or FAB */}
      {chatOpen && (
        <div className="w-[380px] shrink-0 border-l border-border flex flex-col bg-background overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2.5 border-b border-border bg-background z-10 shrink-0">
            <div className="flex items-center gap-2">
              <img src="/assets/logos/circleonly_yarnnn_1.svg" alt="" className="w-5 h-5" />
              <span className="text-xs font-medium">TP</span>
              {selectedNode && (
                <span className="text-[10px] text-muted-foreground/50 truncate max-w-[160px]">
                  · viewing {selectedNode.name}
                </span>
              )}
            </div>
            <button onClick={() => setChatOpen(false)} className="p-1.5 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="flex-1 min-h-0">
            <ChatPanel
              surfaceOverride={effectiveSurface}
              plusMenuActions={plusMenuActions}
              emptyState={emptyState}
            />
          </div>
        </div>
      )}

      {!chatOpen && (
        <button
          onClick={() => setChatOpen(true)}
          className="fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full shadow-lg hover:shadow-xl hover:scale-110 transition-all flex items-center justify-center group"
          title="Chat with TP"
        >
          <img
            src="/assets/logos/circleonly_yarnnn_1.svg"
            alt="yarnnn"
            className="w-12 h-12 transition-transform duration-500 group-hover:rotate-180"
          />
        </button>
      )}
    </div>
  );
}
