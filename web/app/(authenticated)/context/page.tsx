'use client';

/**
 * Context Surface — Workspace knowledge browser (ADR-180, v11).
 *
 * Context answers: "What does my workspace know? What has it produced?"
 *
 * Four top-level sections:
 *   Context  — accumulated domain knowledge (/workspace/context/)
 *   Reports  — rendered deliverables from produces_deliverable tasks (/tasks/{slug}/outputs/latest/) [ADR-180]
 *   Uploads  — user-contributed files (/workspace/uploads/)
 *   Settings — workspace identity/brand/conventions files
 *
 * Deep-link params:
 *   ?domain={key}  — navigate to a context domain folder
 *   ?path={path}   — navigate to any workspace path (incl. /tasks/{slug}/outputs/latest)
 */

import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
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
import { PageHeader } from '@/components/shell/PageHeader';
import { SurfaceIdentityHeader } from '@/components/shell/SurfaceIdentityHeader';
import { TaskSetupModal } from '@/components/chat-surface/TaskSetupModal';
import { DeliverableMiddle } from '@/components/work/details/DeliverableMiddle';

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
  outputTasks?: Array<{ slug: string; title: string; last_run_at: string | null }>;
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

  // Outputs: tasks that have produced deliverables (ADR-180)
  const outputTasks = input.outputTasks ?? [];
  const outputChildren: TreeNode[] = outputTasks.map(task => ({
    name: task.title,
    path: `/tasks/${task.slug}/outputs/latest`,
    type: 'folder' as const,
    updated_at: task.last_run_at ?? undefined,
    summary: task.last_run_at ? `Latest output` : 'No output yet',
  }));

  return [
    {
      name: 'Context',
      path: `${EXPLORER_ROOT_PATH}/context`,
      type: 'folder' as const,
      summary: domainChildren.length ? `${domainChildren.length} domains` : 'No domains yet',
      children: domainChildren,
    },
    {
      name: 'Reports',
      path: `${EXPLORER_ROOT_PATH}/outputs`,
      type: 'folder' as const,
      summary: outputChildren.length ? `${outputChildren.length} reports` : 'No reports yet',
      children: outputChildren,
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

function getNodeMetadata(node: TreeNode): string {
  const parts: string[] = [node.type === 'folder' ? 'Folder' : 'File'];

  if (node.type === 'folder') {
    const childCount = node.children?.length;
    if (typeof childCount === 'number') {
      parts.push(`${childCount} ${childCount === 1 ? 'item' : 'items'}`);
    } else if (node.summary) {
      parts.push(node.summary);
    }
  } else if (node.summary) {
    parts.push(node.summary);
  }

  if (node.updated_at) {
    parts.push(`Updated ${formatNodeTimestamp(node.updated_at)}`);
  }

  return parts.join(' · ');
}

function formatNodeTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

// =============================================================================
// Context Page
// =============================================================================

export default function ContextPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { loadScopedHistory, sendMessage } = useTP();
  const { surface } = useDesk();
  const { setBreadcrumb, clearBreadcrumb } = useBreadcrumb();

  const domainParam = searchParams.get('domain');
  const pathParam = searchParams.get('path');

  const [treeNodes, setTreeNodes] = useState<TreeNode[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [fileTreeLoading, setFileTreeLoading] = useState(false);
  const [phase, setPhase] = useState<'setup' | 'ready' | 'active' | null>(null);
  const [taskSetupOpen, setTaskSetupOpen] = useState(false);

  const virtualRoot: TreeNode = { name: 'root', path: EXPLORER_ROOT_PATH, type: 'folder', children: treeNodes };

  // Synthetic node for direct workspace paths that may not be in the virtual tree
  // (e.g. entity subfolder /workspace/context/{domain}/{entity} from TrackingEntityGrid)
  const syntheticNodeForPath = useCallback((path: string): TreeNode | null => {
    if (!path) return null;
    const name = path.split('/').filter(Boolean).pop() ?? path;
    // Determine type: paths without an extension are treated as folders
    const hasExtension = /\.[a-z0-9]+$/i.test(name);
    return {
      name,
      path,
      type: hasExtension ? 'file' : 'folder',
      children: [],
    };
  }, []);

  const loadExplorer = useCallback(async () => {
    setFileTreeLoading(true);
    try {
      const [nav, domainTree, uploadTree, tasksData] = await Promise.all([
        api.workspace.getNav(),
        api.workspace.getTree('/workspace/context'),
        api.workspace.getTree('/workspace/uploads'),
        api.tasks.list(),
      ]);

      const navDomains = Array.isArray(nav?.domains) ? nav.domains : [];
      const domainTitles = Object.fromEntries(navDomains.map((domain: any) => [domain.key, domain.display_name]));

      // Only show tasks that produce deliverables and have run at least once
      const allTasks = Array.isArray(tasksData) ? tasksData : [];
      const outputTasks = allTasks
        .filter((t: any) => t.output_kind === 'produces_deliverable' && t.last_run_at)
        .map((t: any) => ({ slug: t.slug, title: t.title, last_run_at: t.last_run_at }));

      const nodes = buildContextNodes({
        domainTree: asNodeArray(domainTree),
        uploadTree: asNodeArray(uploadTree),
        domainTitles,
        settings: Array.isArray(nav?.settings) ? nav.settings : [],
        outputTasks,
      });

      setTreeNodes(nodes);
      setPhase(nav.readiness?.phase || 'active');

      const root: TreeNode = { name: 'root', path: EXPLORER_ROOT_PATH, type: 'folder', children: nodes };

      // ?path= deep-link — always honour it; syntheticNodeForPath handles paths
      // not present in the virtual tree (e.g. entity subfolders).
      if (pathParam) {
        setSelectedPath(pathParam);
        return;
      }

      // ?domain= deep-link — select the domain folder
      if (domainParam) {
        const contextFolder = nodes.find(n => n.name === 'Context');
        if (contextFolder?.children) {
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
        if (prev && resolveNodeByPath(root, prev)) return prev;
        return null;
      });
    } catch (err) {
      console.error('Failed to load explorer:', err);
    } finally {
      setFileTreeLoading(false);
    }
  }, [domainParam, pathParam]);

  // selectedNode: prefer tree-resolved node (has children populated), fall back to
  // synthetic node for direct workspace paths that aren't in the virtual tree
  // (e.g. entity subfolders navigated from TrackingEntityGrid).
  const selectedNode = selectedPath
    ? (resolveNodeByPath(virtualRoot, selectedPath) ?? syntheticNodeForPath(selectedPath))
    : null;
  const breadcrumbs = selectedNode ? buildBreadcrumbs(virtualRoot, selectedNode.path).filter(n => n.path !== EXPLORER_ROOT_PATH) : [];

  // Push breadcrumb path into global header
  // Virtual top-level folder names (Context, Outputs, Uploads, Settings) are
  // explorer-only groupings — strip them; the surface root "Context" label is
  // always the first segment, showing which surface the user is on.
  useEffect(() => {
    const TOP_LEVEL_VIRTUAL = new Set(['Context', 'Outputs', 'Uploads', 'Settings']);
    if (breadcrumbs.length > 0) {
      const displayBreadcrumbs = TOP_LEVEL_VIRTUAL.has(breadcrumbs[0]?.name ?? '')
        ? breadcrumbs.slice(1)
        : breadcrumbs;
      const segs = displayBreadcrumbs.map((crumb) => ({
        label: crumb.name,
        href: `/context?path=${encodeURIComponent(crumb.path)}`,
        kind: crumb.type === 'file' ? 'context' as const : 'entity' as const,
      }));
      setBreadcrumb([
        { label: 'Context', href: '/context', kind: 'surface' },
        ...segs,
      ]);
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

  // When URL params change while tree is already loaded (user navigates
  // entity-to-entity from Work without a full remount), sync selection
  // without re-fetching the tree.
  useEffect(() => {
    if (treeNodes.length === 0) return; // wait for loadExplorer

    if (pathParam) {
      setSelectedPath(pathParam);
      return;
    }
    if (domainParam) {
      const contextFolder = treeNodes.find(n => n.name === 'Context');
      const domainNode = contextFolder?.children?.find(
        n => n.path === `/workspace/context/${domainParam}` || n.path.endsWith(`/${domainParam}`)
      );
      if (domainNode) setSelectedPath(domainNode.path);
    }
  }, [pathParam, domainParam, treeNodes]);

  const handleExplorerSelect = useCallback((node: TreeNode) => {
    setSelectedPath(node.path);
    router.replace(`/context?path=${encodeURIComponent(node.path)}`, { scroll: false });
  }, [router]);

  const plusMenuActions: PlusMenuAction[] = [
    { id: 'create-task', label: 'Start new work', icon: ListChecks, verb: 'show', onSelect: () => setTaskSetupOpen(true) },
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
    <>
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
      <PageHeader defaultLabel="Context" />
      {selectedNode ? (
        <div className="flex-1 overflow-auto bg-background flex flex-col">
          <SurfaceIdentityHeader
            title={selectedNode.name}
            metadata={getNodeMetadata(selectedNode)}
          />
          <div className="flex-1 overflow-auto">
            {/* Task output paths render DeliverableMiddle (ADR-180) */}
            {/^\/tasks\/[^/]+\/outputs/.test(selectedNode.path) ? (() => {
              const taskSlug = selectedNode.path.split('/')[2];
              return <DeliverableMiddle taskSlug={taskSlug} refreshKey={0} />;
            })() : (
              <ContentViewer
                selectedNode={selectedNode}
                onNavigate={handleExplorerSelect}
                showHeader={false}
                onEditViaChat={(prompt) => sendMessage(prompt, { surface: effectiveSurface })}
              />
            )}
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center max-w-xs">
            <FolderOpen className="w-8 h-8 text-muted-foreground/15 mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">Select a file or folder from the explorer</p>
          </div>
        </div>
      )}
    </ThreePanelLayout>

      <TaskSetupModal
        open={taskSetupOpen}
        onClose={() => setTaskSetupOpen(false)}
        onSubmit={(msg) => { setTaskSetupOpen(false); sendMessage(msg, { surface: effectiveSurface }); }}
      />
    </>
  );
}
