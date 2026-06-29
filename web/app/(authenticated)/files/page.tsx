'use client';

/**
 * Files Surface — Workspace knowledge browser (ADR-180, v12 / ADR-206 / ADR-231 / ADR-297 D19).
 *
 * Route: /files (slug `files`). The legacy /context URL is a redirect stub.
 *
 * D19 (2026-05-22) refactor: window-shaped per the OS metaphor. The
 * page DELETES its prior outer chrome (ThreePanelLayout + PageHeader +
 * setBreadcrumb). The WindowFrame is now the chrome.
 *
 * Files is unique among atomic surfaces in that its content shape IS a
 * two-pane explorer (tree + viewer). The split-pane is the surface's
 * own internal layout, not workspace-wide chrome — the surface owns
 * the tree directly. Tree is collapsible to an icon rail; viewer takes
 * the remainder.
 *
 * Files answers: "What does my workspace know? What has it produced?"
 *
 * Four top-level sections, ordered Intent-first per ADR-206 three-layer view:
 *   Identity  — workspace identity/brand/conventions + domain _operator_profile.md
 *               + _risk.md + Reviewer principles.md. The Intent layer (ADR-206).
 *   Context   — accumulated domain knowledge (/workspace/operation/{domain}/ per ADR-320).
 *   Reports   — rendered deliverables from DELIVERABLE-shape recurrences
 *               (/workspace/operation/reports/{slug}/{date}/output.md per ADR-231 D2).
 *               Was /tasks/{slug}/outputs/latest/ pre-cutover; the substrate
 *               moved to natural-home paths in ADR-231 Phase 3.7.
 *   Uploads   — user-contributed source material (/workspace/uploads/).
 *
 * Deep-link params (COLD-LOAD ONLY, per ADR-297 D19.2):
 *   ?domain={key}  — seed selection to a context domain folder on entry
 *   ?path={path}   — seed selection to any workspace path on entry
 *
 * These params are read once on mount to seed `selectedPath` (e.g. a shared
 * link, or a cross-surface navigation via navigateToSurface('files', {path})).
 * In-surface file/folder clicks DO NOT write the URL — selection is component
 * state. Writing `/files?path=…` on every click flipped pathname away from
 * /desktop and disrupted the launcher/topbar (operator-observed KVK 2026-06-12).
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Loader2,
  FolderOpen,
  X,
  Info,
  History,
  LayoutGrid,
  List as ListIcon,
} from 'lucide-react';
import { useNarrative } from '@/contexts/NarrativeContext';
import { useSurfaceParam } from '@/lib/shell/useSurfacePreferences';
import { useWindowCrumb } from '@/contexts/BreadcrumbContext';
import type { DeskSurface } from '@/types/desk';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { formatAuthorLabel } from '@/lib/workspace/attribution';
import { WorkspaceTree } from '@/components/workspace/WorkspaceTree';
import { RecentRevisions } from '@/components/workspace/RecentRevisions';
import { UploadButton } from '@/components/workspace/UploadButton';
import { ContentViewer } from '@/components/workspace/ContentViewer';
import { GetInfoModal } from '@/components/workspace/GetInfoModal';
import { useFilesViewMode } from '@/lib/workspace/useFilesViewMode';
import { SurfaceIdentityHeader } from '@/components/shell/SurfaceIdentityHeader';
import { DeliverableMiddle } from '@/components/work/details/DeliverableMiddle';

type TreeNode = import('@/types').WorkspaceTreeNode;

// Internal split-pane sizing (D19: the surface owns its own tree pane;
// ThreePanelLayout's workspace-wide left panel was deleted).
const TREE_PANE_KEY = 'yarnnn:files:tree-width';
const TREE_PANE_DEFAULT = 280;
const TREE_PANE_MIN = 200;
const TREE_PANE_MAX = 560;

function loadStoredTreeWidth(): number {
  if (typeof window === 'undefined') return TREE_PANE_DEFAULT;
  const raw = window.localStorage.getItem(TREE_PANE_KEY);
  if (!raw) return TREE_PANE_DEFAULT;
  const n = parseInt(raw, 10);
  if (Number.isNaN(n)) return TREE_PANE_DEFAULT;
  return Math.max(TREE_PANE_MIN, Math.min(TREE_PANE_MAX, n));
}

const EXPLORER_ROOT_PATH = '/explorer';

function asNodeArray(value: unknown): TreeNode[] {
  return Array.isArray(value) ? value as TreeNode[] : [];
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

// Files surface group assembly — ADR-320 topology (2026-06-10 correction).
//
// The five-root substrate topology (ADR-320): the legacy /workspace/_shared,
// /workspace/context, /workspace/review, /workspace/memory roots are GONE.
// Substrate now lives at:
//   - /workspace/persona/      → the Reviewer seat (IDENTITY, principles,
//                                 judgment_log, calibration, standing_intent…)
//   - /workspace/operation/    → the work: domains ({portfolio}, {trading}…),
//                                 reports/, specs/, BRAND.md, CONVENTIONS.md
//   - /workspace/system/       → YARNNN working memory (awareness, notes, style)
//   - /workspace/constitution/ → MANDATE, PRECEDENT (surfaced via Identity)
//   - /workspace/governance/   → AUTONOMY (surfaced via Identity)
//   - /workspace/agents/       → per-agent substrate
//   - /workspace/uploads/      → operator-contributed source material
//
// SYSTEM FILES ARE VISIBLE, NOT HIDDEN (2026-06-10): the prior `_`-prefix
// hide rule made the tree dishonest — it couldn't "follow" a deep-link or
// Get-Info into the very files Home/cockpit link to (e.g. _account.yaml,
// _principles.yaml). Machine-config `_*` files now render DE-EMPHASIZED
// (TreeItem dims + tags them) rather than vanishing. The operator sees the
// whole substrate; the system/authored distinction is shown by treatment,
// not by omission. Only one path stays hidden: operation/signals (a
// high-churn temporal log, not browseable substrate).
//
// DOMAINS ARE DISK-DERIVED, NOT REGISTRY-DERIVED: a "domain" is any folder
// directly under operation/ that isn't reports/ or specs/. The kernel
// registry only knows generic domains (competitors, market…); program
// domains (portfolio, trading…) are created by work demand and would be
// invisible if we filtered by the registry. We read what's on disk and use
// the registry only for display-name enrichment.

// operation/ subfolders that are NOT context domains (they get their own
// groups or aren't browseable here). Loose operation/ files (BRAND.md,
// CONVENTIONS.md) are surfaced via the Identity group (nav.settings), not
// Context — the Context filter below keeps only folders.
const OPERATION_NON_DOMAIN = new Set(['reports', 'specs']);

// ADR-388 D1 — the FILESYSTEM-LITERAL explorer tree. One node per actual
// workspace root (from GET /workspace/roots), each lazy-loading its subtree
// (getTree). No synthetic cross-root groups, no hardcoded root list: the tree
// mirrors the real FS 1:1, so the ADR-320 governance/+constitution/ roots and
// the ADR-376 inbound/ lane show, and any future root the re-founding adds
// shows too (raw name if unmapped) — correct by construction (ADR-388 §6).
export interface WorkspaceRoot {
  name: string;
  path: string;
  display_name: string;
  semantic_class: string;
  description: string;
  icon: string;
  file_count: number;
  exists: boolean;
}

function buildRootNodes(input: {
  roots: WorkspaceRoot[];
  subtrees: Record<string, TreeNode[]>; // root name → its getTree children
  domainTitles: Record<string, string>; // operation/{folder} → registry display name
}): TreeNode[] {
  // The only path still hidden: operation/signals (temporal churn log).
  const isHidden = (node: TreeNode): boolean =>
    node.path.startsWith('/workspace/operation/signals');
  const notHidden = (node: TreeNode) => !isHidden(node);

  return input.roots.map((root) => {
    let children = filterNodes(input.subtrees[root.name], notHidden);

    // operation/ keeps its registry display-name enrichment on domain folders
    // (the only place we relabel a child) — the substrate stays literal, the
    // operator just sees "Competitors" instead of the raw folder key.
    if (root.name === 'operation') {
      children = (children ?? []).map((n) =>
        n.type === 'folder' && !OPERATION_NON_DOMAIN.has(n.name)
          ? { ...n, name: input.domainTitles[n.name] || n.name }
          : n
      );
    }

    const count = children?.length ?? 0;
    return {
      name: root.display_name, // friendly label; raw name for unmapped roots
      path: root.path, // the REAL fs path (/workspace/{name}) — clickable, resolves
      type: 'folder' as const,
      summary: root.description || (count ? `${count} items` : 'Empty'),
      children,
    } satisfies TreeNode;
  });
}

// Map ADR-209 authored_by taxonomy to operator-readable labels.
// Same mapping as ContentViewer's formatHeadAuthor (shipped Cluster B).
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

  // ADR-209 head-revision attribution: show "Last edited by {author}"
  // when authored_by is present on the node (populated by the tree
  // endpoint's workspace_file_versions FK embed).
  const authorLabel = formatAuthorLabel((node as any).authored_by);
  if (authorLabel) {
    parts.push(`Last edited by ${authorLabel}`);
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
  const { loadScopedHistory, sendMessage } = useNarrative();

  // ADR-358 D6 (2026-06-25): read this window's OWN deep-link params under
  // the `files.` namespace (`?files.domain=`, `?files.path=`) so they never
  // collide with another open window on the shared /desktop URL. These are
  // mount-time SEED transports (a shared link / cross-surface jump); the
  // surface drives its live selection through internal `selectedPath` state
  // and deliberately does NOT write back to the URL (see the click handlers).
  const fp = useSurfaceParam('files');
  const domainParam = fp.get('domain');
  const pathParam = fp.get('path');

  const [treeNodes, setTreeNodes] = useState<TreeNode[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [fileTreeLoading, setFileTreeLoading] = useState(false);
  const [phase, setPhase] = useState<'setup' | 'ready' | 'active' | null>(null);

  // ADR-329 (amended): node Details ("Get Info") — provenance as a per-node
  // property, opened on demand (header ⓘ toggle or tree right-click), not a
  // standing left-rail feed. Tied to the current selection; collapses to a
  // header section above the content.
  const [detailsOpen, setDetailsOpen] = useState(false);

  // ADR-388 D4: the Files-surface-wide view mode (icon grid / details list),
  // shared across Recents + folder listings (was Recents-only).
  const { mode: viewMode, setMode: setViewMode } = useFilesViewMode();

  // D19 split-pane state — the surface owns its own tree pane.
  const [treePaneOpen, setTreePaneOpen] = useState(true);
  const [treeWidth, setTreeWidth] = useState(TREE_PANE_DEFAULT);
  const treeDragging = useRef(false);

  useEffect(() => {
    setTreeWidth(loadStoredTreeWidth());
  }, []);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!treeDragging.current) return;
      const next = Math.max(TREE_PANE_MIN, Math.min(TREE_PANE_MAX, e.clientX));
      setTreeWidth(next);
    };
    const onUp = () => {
      if (!treeDragging.current) return;
      treeDragging.current = false;
      try {
        window.localStorage.setItem(TREE_PANE_KEY, String(treeWidth));
      } catch {}
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [treeWidth]);

  const onTreeDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    treeDragging.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  const virtualRoot: TreeNode = { name: 'root', path: EXPLORER_ROOT_PATH, type: 'folder', children: treeNodes };

  // Synthetic node for direct workspace paths that may not be in the virtual tree
  // (e.g. entity subfolder /workspace/operation/{domain}/{entity} from TrackingEntityGrid)
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
      // ADR-388 D1: derive the explorer from the ACTUAL filesystem roots
      // (GET /workspace/roots), not a hardcoded list. Then fetch each root's
      // subtree in parallel. This is the root-cause kill for the missing-
      // directories bug: governance/, constitution/, inbound/ — and any future
      // root — appear automatically. nav is still fetched for the operation/
      // domain display-name enrichment + readiness phase.
      const [nav, roots] = await Promise.all([
        api.workspace.getNav(),
        api.workspace.getRoots(),
      ]);

      const navDomains = Array.isArray(nav?.domains) ? nav.domains : [];
      // Map registry domain *folder name* → display_name. The registry keys
      // (competitors, market…) are the operation/{name} folder names, so we
      // index by the last path segment for disk-folder enrichment.
      const domainTitles = Object.fromEntries(
        navDomains.map((domain: any) => {
          const folderName = (domain.path || '').split('/').filter(Boolean).pop() || domain.key;
          return [folderName, domain.display_name];
        })
      );

      // Fetch each real root's subtree in parallel (catch-per-root so one
      // failure doesn't take down the explorer). Empty roots (file_count 0,
      // e.g. agents/uploads) still render as creatable nodes — no fetch needed.
      const subtreeEntries = await Promise.all(
        roots.map(async (r) => {
          if (!r.exists) return [r.name, []] as const;
          const tree = await api.workspace.getTree(r.path).catch(() => []);
          return [r.name, asNodeArray(tree)] as const;
        })
      );
      const subtrees: Record<string, TreeNode[]> = Object.fromEntries(subtreeEntries);

      const nodes = buildRootNodes({ roots, subtrees, domainTitles });

      setTreeNodes(nodes);
      setPhase(nav.readiness?.phase || 'active');

      const root: TreeNode = { name: 'root', path: EXPLORER_ROOT_PATH, type: 'folder', children: nodes };

      // ?path= deep-link — always honour it; syntheticNodeForPath handles paths
      // not present in the virtual tree (e.g. entity subfolders).
      if (pathParam) {
        setSelectedPath(pathParam);
        return;
      }

      // ?domain= deep-link — select the domain folder under the operation root
      // (ADR-388 D1: domains now nest under the literal operation/ root, not a
      // synthetic "Context" group). Resolve directly by its real path.
      if (domainParam) {
        const domainPath = `/workspace/operation/${domainParam}`;
        if (resolveNodeByPath(root, domainPath)) {
          setSelectedPath(domainPath);
          return;
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

  // D19 (2026-05-22): workspace-wide setBreadcrumb removed. The full
  // path-trail lives inside the surface body via SurfaceIdentityHeader.
  // Per-window locator (2026-06-25): the WindowFrame title bar shows
  // "Files › {leaf}" (the selected node's name) so each open window
  // states its own position; back crumb returns to the root listing.
  // List mode (nothing selected) registers [] — flat "Files" title.
  useWindowCrumb(
    'files',
    selectedNode
      ? [{ label: selectedNode.name, kind: 'context', onClick: () => setSelectedPath(null) }]
      : []
  );

  // ADR-297 Phase 3: surface context for chat drafts derives from this
  // surface's own identity (Files), not the deleted DeskContext. When a
  // node is selected, overlay the explorer path so the agent knows what
  // the operator is looking at.
  const effectiveSurface: DeskSurface = selectedNode
    ? { type: 'workspace-explorer', path: selectedNode.path, navigation_type: selectedNode.type }
    : { type: 'atomic', slug: 'files' };

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

  // ADR-297 D19.2: in-surface selection is component state, NOT a URL write.
  // The Files surface runs as a window on the Desktop (pathname `/desktop`);
  // writing `/files?path=…` on every click flipped pathname → /files, which
  // tripped AuthenticatedLayout's pathname→foreground effect + SurfaceViewport's
  // pathnameSlug resolution, disrupting the launcher/topbar (operator-observed
  // KVK 2026-06-12). `?path=` survives only as a COLD-LOAD deep-link (read on
  // entry to seed selectedPath) — it is never written from intra-surface clicks.
  const handleExplorerSelect = useCallback((node: TreeNode) => {
    setSelectedPath(node.path);
  }, []);

  // Path-based select — a path string, not a TreeNode. The file may not be in
  // the visible tree (e.g. a folder-Details revision row deep-links into a
  // `_`-prefixed file hidden from the explorer); syntheticNodeForPath resolves
  // the viewer. Selecting via a folder-Details row also drops Details back to
  // the (newly-selected) node's own scope.
  const handleExplorerSelect_byPath = useCallback((path: string) => {
    setSelectedPath(path);
  }, []);

  // ADR-329 (amended): right-click "Get Info" on a tree node → select it (so
  // Details scopes to it) and open the Details panel.
  const handleGetInfo = useCallback((node: TreeNode) => {
    setSelectedPath(node.path);
    setDetailsOpen(true);
  }, []);

  // D19 (2026-05-22): the prior plusMenuActions + chat empty-state
  // block were ThreePanelLayout-side affordances. Chat affordances
  // now live in the universal ChatDrawer FAB (singular summon path).

  // Tree pane content — a "Recents" sidebar nav item (ADR-329 Amendment 2)
  // above the explorer tree. Clicking it deselects the current node, which
  // returns the center pane to the Finder "Recents" view (the empty-state).
  // This is Finder's sidebar Recents item — the navigational way BACK to the
  // recency view once you've opened a file. Active (highlighted) when nothing
  // is selected. The cramped sidebar feed it replaces is deleted; the recency
  // DATA lives in the center pane where filenames are readable (Singular
  // Implementation: one recency view, reached by this nav item).
  const treePaneContent = (
    <div className="flex-1 overflow-y-auto">
      {fileTreeLoading && treeNodes.length === 0 ? (
        <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          Loading...
        </div>
      ) : treeNodes.length > 0 ? (
        <div className="p-2">
          <button
            onClick={() => setSelectedPath(null)}
            aria-current={selectedPath === null ? 'page' : undefined}
            className={cn(
              'w-full flex items-center gap-2 px-2 py-1.5 mb-1 rounded-md text-left text-sm transition-colors',
              selectedPath === null
                ? 'bg-primary/10 text-foreground font-medium'
                : 'text-muted-foreground hover:bg-muted/40 hover:text-foreground',
            )}
            title="Recent changes across the workspace"
          >
            <History className="w-4 h-4 shrink-0" />
            <span>Recents</span>
          </button>
          <WorkspaceTree
            nodes={treeNodes}
            selectedPath={selectedPath || undefined}
            onSelect={handleExplorerSelect}
            onGetInfo={handleGetInfo}
          />
        </div>
      ) : (
        <div className="p-3 text-sm text-muted-foreground">Failed to load explorer</div>
      )}
    </div>
  );

  return (
    <div className="flex h-full overflow-hidden">
      {/* In-surface tree pane (D19: surface owns its own internal layout;
          ThreePanelLayout dissolved). Collapsible to an icon rail. */}
      {treePaneOpen ? (
        <>
          <div
            className="shrink-0 border-r border-border flex flex-col bg-background"
            style={{ width: treeWidth }}
          >
            <div className="flex items-center justify-between px-3 py-2 border-b border-border shrink-0 gap-2">
              <div className="min-w-0">
                <p className="text-sm font-medium text-foreground">Explorer</p>
                <p className="text-[11px] text-muted-foreground">Workspace context and settings</p>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                {/* ADR-329: 'add' is an operator verb, homed on Files. */}
                <UploadButton onUploaded={() => loadExplorer()} />
                <button
                  onClick={() => setTreePaneOpen(false)}
                  className="p-1 text-muted-foreground/40 hover:text-muted-foreground rounded"
                  title="Collapse explorer"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
            {treePaneContent}
          </div>
          <div
            onMouseDown={onTreeDragStart}
            className="w-1 shrink-0 cursor-col-resize bg-transparent hover:bg-primary/20 active:bg-primary/30 transition-colors"
            title="Drag to resize"
          />
        </>
      ) : (
        <div className="w-10 shrink-0 border-r border-border flex flex-col items-center py-2 gap-2 bg-background">
          <button
            onClick={() => setTreePaneOpen(true)}
            className="p-2 rounded-md text-muted-foreground/50 hover:text-foreground hover:bg-muted transition-colors"
            title="Open explorer"
          >
            <FolderOpen className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Center content */}
      <div className="flex-1 min-w-0 min-h-0 flex flex-col overflow-y-auto bg-background">
        {selectedNode ? (
          <div className="flex-1 overflow-auto bg-background flex flex-col">
            <SurfaceIdentityHeader
              title={selectedNode.name}
              metadata={getNodeMetadata(selectedNode)}
              actions={
                <div className="flex items-center gap-2">
                  {/* ADR-388 D4: surface-wide view toggle (folder listings honor it). */}
                  {selectedNode.type === 'folder' && (
                    <div className="inline-flex items-center rounded-md border border-border p-0.5">
                      <button
                        onClick={() => setViewMode('icon')}
                        title="Icon view"
                        aria-pressed={viewMode === 'icon'}
                        className={cn(
                          'rounded p-1 transition-colors',
                          viewMode === 'icon' ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground',
                        )}
                      >
                        <LayoutGrid className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => setViewMode('list')}
                        title="List view"
                        aria-pressed={viewMode === 'list'}
                        className={cn(
                          'rounded p-1 transition-colors',
                          viewMode === 'list' ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground',
                        )}
                      >
                        <ListIcon className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  )}
                  {/* ADR-388 D5: Get Info → modal (was an inline collapsible panel).
                      Also reachable by right-click on any tree/row node. */}
                  <button
                    onClick={() => setDetailsOpen(true)}
                    title="Get Info"
                    className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground"
                  >
                    <Info className="w-3.5 h-3.5" />
                    Get Info
                  </button>
                </div>
              }
            />
            <div className="flex-1 overflow-auto">
              {/* DELIVERABLE recurrence substrate roots render DeliverableMiddle
                  (ADR-180 + ADR-231 D2). Path shape: /workspace/operation/reports/{slug}. */}
              {/^\/workspace\/reports\/[^/]+\/?$/.test(selectedNode.path) ? (() => {
                // path = /workspace/operation/reports/{slug}  →  slug at index 3
                const taskSlug = selectedNode.path.split('/')[3];
                return <DeliverableMiddle taskSlug={taskSlug} refreshKey={0} />;
              })() : (
                <ContentViewer
                  selectedNode={selectedNode}
                  onNavigate={handleExplorerSelect}
                  showHeader={false}
                  viewMode={viewMode}
                  onGetInfo={handleGetInfo}
                  onOpenChatDraft={(prompt) => sendMessage(prompt, { surface: effectiveSurface })}
                  onDeleted={() => {
                    // ADR-329: file archived — clear selection + refresh the
                    // tree (the archived file self-filters out server-side).
                    // D19.2: selection is component state, never a URL write.
                    setSelectedPath(null);
                    loadExplorer();
                  }}
                />
              )}
            </div>
          </div>
        ) : (
          // ADR-329 Amendment 2: the center pane's empty state IS the Finder
          // "Recents" view — a columnar glance of recent authored changes
          // across the workspace, replacing the bare "select a file"
          // placeholder. Selecting a row swaps to the node view; the
          // workspace-wide recency question lives here (center pane), the
          // per-node history question lives in Get Info/Details.
          <div className="flex-1 min-h-0">
            <RecentRevisions onSelectPath={handleExplorerSelect_byPath} />
          </div>
        )}
      </div>

      {/* ADR-388 D5: Get Info modal — path/type/when + the ADR-209 revision
          chain (who wrote each version). Opened by the header button or a
          right-click on any tree/folder-listing node. */}
      <GetInfoModal
        node={detailsOpen ? selectedNode : null}
        onClose={() => setDetailsOpen(false)}
        onSelectPath={handleExplorerSelect_byPath}
        onRevert={loadExplorer}
      />
    </div>
  );
}
