'use client';

/**
 * Context Surface — Workspace knowledge browser (ADR-180, v12 / ADR-206 / ADR-231).
 *
 * Context answers: "What does my workspace know? What has it produced?"
 *
 * Four top-level sections, ordered Intent-first per ADR-206 three-layer view:
 *   Identity  — workspace identity/brand/conventions + domain _operator_profile.md
 *               + _risk.md + Reviewer principles.md. The Intent layer (ADR-206).
 *   Context   — accumulated domain knowledge (/workspace/context/{domain}/).
 *   Reports   — rendered deliverables from DELIVERABLE-shape recurrences
 *               (/workspace/reports/{slug}/{date}/output.md per ADR-231 D2).
 *               Was /tasks/{slug}/outputs/latest/ pre-cutover; the substrate
 *               moved to natural-home paths in ADR-231 Phase 3.7.
 *   Uploads   — user-contributed source material (/workspace/uploads/).
 *
 * Deep-link params:
 *   ?domain={key}  — navigate to a context domain folder
 *   ?path={path}   — navigate to any workspace path (incl. /workspace/reports/{slug}/)
 */

import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import {
  Loader2,
  MessageCircle,
  Globe,
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
import { RecurrenceSetupModal } from '@/components/chat-surface/RecurrenceSetupModal';
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

// ADR-236 Round 5+ extension (2026-04-30): Files page surfaces more of
// the substrate the operator should see.
//
// HIDE RULE (only system-strict hidden):
//   - Files starting with `_` (machine-config: _recurring.yaml, _tracker.md,
//     _domain.md, _performance.md, etc.). These are operationally important
//     but accumulated by the system; their content is rendered by the
//     surfaces that need them (faces, briefings). Showing them in the
//     explorer would create operator confusion about whether they're
//     authored substrate.
//   - /workspace/context/signals — temporal signals log, not substrate.
//
// VISIBLE (operator can see + ask YARNNN about):
//   - Identity (authored shared substrate at /workspace/context/_shared/)
//   - Context (accumulated domain knowledge, hiding `_`-prefixed files)
//   - Reports (DELIVERABLE recurrences)
//   - Uploads (operator-contributed)
//   - Memory (YARNNN's working memory — awareness, notes, style)
//   - Review (Reviewer substrate — IDENTITY, principles, decisions, calibration)
//   - Agents (per-agent substrate — AGENT.md, memory/, etc.) — the operator
//     wanted to see TP's folder; this surfaces it.
function buildContextNodes(input: {
  domainTree?: TreeNode[];
  uploadTree?: TreeNode[];
  memoryTree?: TreeNode[];
  reviewTree?: TreeNode[];
  agentsTree?: TreeNode[];
  domainTitles: Record<string, string>;
  settings?: Array<{ name: string; filename: string; path: string; updated_at: string | null }>;
  outputTasks?: Array<{ slug: string; title: string; last_run_at: string | null }>;
}): TreeNode[] {
  // System-strict hide predicate: `_`-prefixed files are machine-config /
  // accumulated by the system; specific paths (signals/) are temporal logs.
  const isHidden = (node: TreeNode): boolean => {
    const filename = node.path.split('/').pop() || '';
    if (filename.startsWith('_')) return true;
    if (node.path.startsWith('/workspace/context/signals')) return true;
    return false;
  };
  const visible = (predicate: (n: TreeNode) => boolean) => (node: TreeNode) =>
    !isHidden(node) && predicate(node);

  const domainChildren = relabelTopLevelNodes(
    filterNodes(input.domainTree, visible(() => true)),
    input.domainTitles
  );
  const uploadChildren = asNodeArray(input.uploadTree);
  const memoryChildren = filterNodes(input.memoryTree, visible(() => true));
  const reviewChildren = filterNodes(input.reviewTree, visible(() => true));
  const agentsChildren = filterNodes(input.agentsTree, visible(() => true));
  const settingsFiles = Array.isArray(input.settings) ? input.settings : [];

  // Outputs: DELIVERABLE-shape recurrences (ADR-180 + ADR-231 D2).
  const outputTasks = input.outputTasks ?? [];
  const outputChildren: TreeNode[] = outputTasks.map(task => ({
    name: task.title,
    path: `/workspace/reports/${task.slug}`,
    type: 'folder' as const,
    updated_at: task.last_run_at ?? undefined,
    summary: task.last_run_at ? `Latest output` : 'No output yet',
  }));

  // ADR-206 Intent-first ordering preserved for the first four sections.
  // Memory + Review + Agents added per the operator's "most should be
  // visible" framing. Sections with zero children are omitted — the
  // operator saw "Agents: 0 items / Empty folder" which was confusing
  // because specialist filesystem substrate only materialises when an
  // agent first runs; TP has no /workspace/agents/ filesystem path at
  // all (TP is an orchestration surface, not a filesystem-substrate
  // agent per ADR-216).
  const maybe = (node: TreeNode): TreeNode | null =>
    (node.children?.length ?? 0) > 0 ? node : null;

  return [
    {
      name: 'Identity',
      path: `${EXPLORER_ROOT_PATH}/settings`,
      type: 'folder' as const,
      summary: settingsFiles.length ? `${settingsFiles.length} files` : 'Declare identity, brand, conventions',
      children: settingsFiles.map((file) => ({
        name: file.filename,
        path: file.path,
        type: 'file' as const,
        updated_at: file.updated_at || undefined,
        summary: file.name,
      })),
    },
    {
      name: 'Context',
      path: `${EXPLORER_ROOT_PATH}/context`,
      type: 'folder' as const,
      summary: domainChildren.length ? `${domainChildren.length} domains` : 'No domains yet',
      children: domainChildren,
    },
    maybe({
      name: 'Reports',
      path: `${EXPLORER_ROOT_PATH}/outputs`,
      type: 'folder' as const,
      summary: outputChildren.length ? `${outputChildren.length} reports` : 'No reports yet',
      children: outputChildren,
    }),
    maybe({
      name: 'Memory',
      path: '/workspace/memory',
      type: 'folder' as const,
      summary: `${memoryChildren.length} files`,
      children: memoryChildren,
    }),
    maybe({
      name: 'Review',
      path: '/workspace/review',
      type: 'folder' as const,
      summary: `${reviewChildren.length} files`,
      children: reviewChildren,
    }),
    maybe({
      name: 'Agents',
      path: '/workspace/agents',
      type: 'folder' as const,
      summary: `${agentsChildren.length} agents`,
      children: agentsChildren,
    }),
    maybe({
      name: 'Uploads',
      path: `${EXPLORER_ROOT_PATH}/uploads`,
      type: 'folder' as const,
      summary: `${uploadChildren.length} items`,
      children: uploadChildren,
    }),
  ].filter((n): n is TreeNode => n !== null);
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
  const [recurrenceSetupOpen, setRecurrenceSetupOpen] = useState(false);

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
      // ADR-236 Round 5+ extension: fetch memory/review/agents trees in
      // parallel. allSettled rather than all so that any single tree's
      // 404 / error doesn't take down the explorer.
      const [
        nav,
        domainTree,
        uploadTree,
        memoryTreeR,
        reviewTreeR,
        agentsTreeR,
        tasksData,
      ] = await Promise.all([
        api.workspace.getNav(),
        api.workspace.getTree('/workspace/context'),
        api.workspace.getTree('/workspace/uploads'),
        api.workspace.getTree('/workspace/memory').catch(() => []),
        api.workspace.getTree('/workspace/review').catch(() => []),
        api.workspace.getTree('/workspace/agents').catch(() => []),
        api.recurrences.list(),
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
        memoryTree: asNodeArray(memoryTreeR),
        reviewTree: asNodeArray(reviewTreeR),
        agentsTree: asNodeArray(agentsTreeR),
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

  // ADR-215 R4: the + menu is a modal launcher only. Authored-rules edits
  // (IDENTITY / BRAND / CONVENTIONS / MANDATE) are substrate per R3 — edit
  // the file directly on Files. ManageContextModal is retired.
  const plusMenuActions: PlusMenuAction[] = [
    { id: 'create-task', label: 'Start new work', icon: ListChecks, verb: 'show', onSelect: () => setRecurrenceSetupOpen(true) },
    {
      id: 'web-search',
      label: 'Web search',
      icon: Globe,
      verb: 'prompt',
      onSelect: () => sendMessage(
        'Search the web for: ',
        { surface: effectiveSurface },
      ),
    },
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
            {/* DELIVERABLE recurrence substrate roots render DeliverableMiddle
                (ADR-180 + ADR-231 D2). Path shape: /workspace/reports/{slug}. */}
            {/^\/workspace\/reports\/[^/]+\/?$/.test(selectedNode.path) ? (() => {
              // path = /workspace/reports/{slug}  →  slug at index 3
              const taskSlug = selectedNode.path.split('/')[3];
              return <DeliverableMiddle taskSlug={taskSlug} refreshKey={0} />;
            })() : (
              <ContentViewer
                selectedNode={selectedNode}
                onNavigate={handleExplorerSelect}
                showHeader={false}
                onOpenChatDraft={(prompt) => sendMessage(prompt, { surface: effectiveSurface })}
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

      <RecurrenceSetupModal
        open={recurrenceSetupOpen}
        onClose={() => setRecurrenceSetupOpen(false)}
        onSubmit={(msg) => { setRecurrenceSetupOpen(false); sendMessage(msg, { surface: effectiveSurface }); }}
      />
    </>
  );
}
