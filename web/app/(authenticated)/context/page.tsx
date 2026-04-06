'use client';

/**
 * Context Surface — Workspace explorer (domains, uploads, settings)
 *
 * SURFACE-ARCHITECTURE.md v7: The single file browser. All raw file viewing
 * happens here. Agents page links in with ?domain={key} for deep-linking.
 *
 * Uses ThreePanelLayout for shared shell.
 */

import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  Loader2,
  MessageCircle,
  Upload,
  Globe,
  Settings2,
  ListChecks,
  FolderOpen,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useDesk } from '@/contexts/DeskContext';
import { useBreadcrumb } from '@/contexts/BreadcrumbContext';
import { api } from '@/lib/api/client';
import { WorkspaceTree } from '@/components/workspace/WorkspaceTree';
import { ContentViewer } from '@/components/workspace/ContentViewer';
import { ThreePanelLayout } from '@/components/shell/ThreePanelLayout';

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
      const filename = node.path.split('/').pop() || '';
      return !filename.startsWith('_') && !node.path.startsWith('/workspace/context/signals');
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
  const searchParams = useSearchParams();
  const { loadScopedHistory, sendMessage } = useTP();
  const { surface } = useDesk();
  const { setBreadcrumb, clearBreadcrumb } = useBreadcrumb();

  const domainParam = searchParams.get('domain');

  const [treeNodes, setTreeNodes] = useState<TreeNode[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [fileTreeLoading, setFileTreeLoading] = useState(false);
  const [phase, setPhase] = useState<'setup' | 'ready' | 'active' | null>(null);
  const [domainDeepLinked, setDomainDeepLinked] = useState(false);

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
      setPhase(nav.readiness?.phase || 'active');

      // Domain deep-linking: auto-navigate to domain folder on first load
      if (domainParam && !domainDeepLinked) {
        setDomainDeepLinked(true);
        // Find the domain node in the Context folder's children
        const contextFolder = nodes.find(n => n.name === 'Context');
        if (contextFolder?.children) {
          // Match by domain key (the original folder name before relabeling)
          // The path will be like /workspace/context/{domain}
          const domainNode = contextFolder.children.find(
            n => n.path === `/workspace/context/${domainParam}` || n.path.endsWith(`/${domainParam}`)
          );
          if (domainNode) {
            setSelectedPath(domainNode.path);
            return;
          }
        }
      }

      // Preserve current selection if still valid
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
  }, [domainParam, domainDeepLinked]);

  const selectedNode = selectedPath ? resolveNodeByPath(virtualRoot, selectedPath) : null;
  const breadcrumbs = selectedNode ? buildBreadcrumbs(virtualRoot, selectedNode.path).filter(n => n.path !== EXPLORER_ROOT_PATH) : [];

  // Push breadcrumb path into global header
  useEffect(() => {
    if (breadcrumbs.length > 0) {
      const segs = breadcrumbs.slice(0, 2).map((crumb, i) => ({
        label: crumb.name,
        ...(i < breadcrumbs.length - 1 ? { onClick: () => setSelectedPath(crumb.path) } : {}),
      }));
      setBreadcrumb(segs);
    } else {
      clearBreadcrumb();
    }
  }, [selectedPath]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    return () => clearBreadcrumb();
  }, [clearBreadcrumb]);

  const effectiveSurface = selectedNode
    ? { ...surface, type: 'workspace-explorer' as const, path: selectedNode.path, navigation_type: selectedNode.type }
    : surface;

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
    { id: 'update-info', label: 'Update my info', icon: Settings2, verb: 'prompt', onSelect: () => {} },
    { id: 'web-search', label: 'Web search', icon: Globe, verb: 'prompt', onSelect: () => {} },
    { id: 'upload-file', label: 'Upload file', icon: Upload, verb: 'attach', onSelect: () => {} },
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

  // Left panel content for ThreePanelLayout
  const leftPanelContent = (
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
  );

  return (
    <ThreePanelLayout
      leftPanel={{
        title: 'Explorer',
        subtitle: 'Workspace context and settings',
        content: leftPanelContent,
        collapsedIcon: <FolderOpen className="w-4 h-4" />,
        collapsedTitle: 'Explorer',
      }}
      chat={{
        surfaceOverride: effectiveSurface,
        plusMenuActions,
        emptyState,
        contextLabel: selectedNode ? `viewing ${selectedNode.name}` : undefined,
      }}
    >
      {selectedNode ? (
        <div className="flex-1 overflow-auto bg-background flex flex-col">
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
    </ThreePanelLayout>
  );
}
