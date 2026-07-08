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

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  Loader2,
  Info,
  History,
  LayoutGrid,
  List as ListIcon,
  Trash2,
} from 'lucide-react';
import { SettingsPaneShell } from '@/components/settings/SettingsPaneShell';
import { useNarrative } from '@/contexts/NarrativeContext';
import { useSurfaceParam } from '@/lib/shell/useSurfacePreferences';
import { useWindowCrumb } from '@/contexts/BreadcrumbContext';
import type { DeskSurface } from '@/types/desk';
import { api, APIError } from '@/lib/api/client';
import { operatorCanOrganize, organizeBlockedReason } from '@/lib/workspace/ownership';
import { useFeedback } from '@/contexts/FeedbackContext';
import { MoveToFolderModal } from '@/components/workspace/MoveToFolderModal';
import { RenameModal } from '@/components/workspace/RenameModal';
import { cn } from '@/lib/utils';
import { formatAuthorLabel } from '@/lib/workspace/attribution';
import { WorkspaceTree } from '@/components/workspace/WorkspaceTree';
import { RecentRevisions } from '@/components/workspace/RecentRevisions';
import { TrashView } from '@/components/workspace/TrashView';
import { UploadButton } from '@/components/workspace/UploadButton';
import { ContentViewer } from '@/components/workspace/ContentViewer';
import { PropertiesModal } from '@/components/workspace/PropertiesModal';
import { useFilesViewMode } from '@/lib/workspace/useFilesViewMode';
import { SurfaceIdentityHeader } from '@/components/shell/SurfaceIdentityHeader';
import { DeliverableMiddle } from '@/components/work/details/DeliverableMiddle';

type TreeNode = import('@/types').WorkspaceTreeNode;

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
      icon_name: root.icon, // ADR-422 D3: kernel-named glyph (was dropped before)
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
  // ADR-400 polish (2026-07-03): the universal action-feedback layer replaces
  // window.alert/confirm/prompt for the operator's file verbs. See
  // docs/design/ACTION-FEEDBACK.md.
  const { confirm, runAction } = useFeedback();

  // ADR-358 D6 (2026-06-25): read this window's OWN deep-link params under
  // the `files.` namespace (`?files.domain=`, `?files.path=`) so they never
  // collide with another open window on the shared /desktop URL. These are
  // mount-time SEED transports (a shared link / cross-surface jump); the
  // surface drives its live selection through internal `selectedPath` state
  // and deliberately does NOT write back to the URL (see the click handlers).
  const fp = useSurfaceParam('files');
  const domainParam = fp.get('domain');
  const pathParam = fp.get('path');

  // 2026-07-01 (operator-observed KVK): these params are COLD-LOAD SEEDS, but
  // the surface never CLEARED them after seeding. So a stale `?files.path=` (a
  // dead deep-link from a prior session) kept re-applying to `selectedPath` on
  // every 30s tree refresh / window-focus refetch — snapping the operator's
  // "Uploads" click back to the ghost file and leaving the explorer with no
  // highlighted node (the ghost path has no matching tree node). Fix: capture
  // the seed ONCE on first render, then drain the params from the URL after the
  // first load. The live selection is `selectedPath` state; the URL is not the
  // source of truth once mounted. `seedConsumedRef` guards the one-shot re-sync.
  const seedRef = useRef<{ path: string | null; domain: string | null }>({
    path: pathParam,
    domain: domainParam,
  });
  const seedConsumedRef = useRef(false);

  const [treeNodes, setTreeNodes] = useState<TreeNode[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  // ADR-400 D4: the Trash nav item toggles the center pane to the Trash view.
  const [showTrash, setShowTrash] = useState(false);
  // ADR-400 Q2 / polish: the "Move to…" folder-picker modal target (a file to
  // relocate). Replaces the old window.prompt('a /workspace/… path') — the
  // operator picks a destination folder in a tree, never types a raw path.
  const [moveTarget, setMoveTarget] = useState<{ path: string; name: string } | null>(null);
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

  // 2026-06-30 unification: the explorer mounts the shared SettingsPaneShell.
  // The shell owns the responsive contract (wide two-pane / narrow drill-in)
  // and the resizable nav width (persisted). Files' bespoke split-pane/resize/
  // icon-rail-collapse plumbing is deleted — Singular Implementation.
  //
  // Narrow drill: a tree click drills INTO the viewer (activateBodyRef); the OS
  // locator's "back" drills OUT to the tree (drillOutRef). The shell hands both
  // fns back via its onActivateRef / onDrillOutRef. The back affordance itself
  // is the OS's single GlobalLocatorStrip (fed by the useWindowCrumb below) —
  // the shell renders no parallel back row.
  const activateBodyRef = useRef<() => void>(() => {});
  const drillOutRef = useRef<() => void>(() => {});
  const registerActivate = useCallback((fn: () => void) => {
    activateBodyRef.current = fn;
  }, []);
  const registerDrillOut = useCallback((fn: () => void) => {
    drillOutRef.current = fn;
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

      // Cold-load seed — consumed ONCE on the first load (seedRef captured on
      // first render), then the params are drained from the URL so subsequent
      // refetches never re-apply a stale path. After consumption, `selectedPath`
      // state is the sole source of truth. seedConsumedRef flips true after the
      // first load whether or not a seed existed — it marks "mount seeding done"
      // so the cross-surface effect can take over for post-mount jumps.
      const seed = seedRef.current;
      const firstLoad = !seedConsumedRef.current;
      if (firstLoad) {
        seedConsumedRef.current = true;
        if (seed.path || seed.domain) {
          // Drain the seed params from the URL (they've done their one job).
          fp.set({ path: null, domain: null });

          // ?files.path= — always honour it; syntheticNodeForPath handles paths
          // not present in the virtual tree (e.g. entity subfolders).
          if (seed.path) {
            setSelectedPath(seed.path);
            return;
          }
          // ?files.domain= — select the domain folder under the operation root
          // (ADR-388 D1: domains nest under the literal operation/ root).
          if (seed.domain) {
            const domainPath = `/workspace/operation/${seed.domain}`;
            if (resolveNodeByPath(root, domainPath)) {
              setSelectedPath(domainPath);
              return;
            }
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
    // fp.set is stable (from useSurfaceParam); seedRef/seedConsumedRef are refs.
    // Deps intentionally empty — loadExplorer must not re-identify on param
    // changes (that would retrigger the mount effect's interval wiring).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // selectedNode: prefer tree-resolved node (has children populated), fall back to
  // synthetic node for direct workspace paths that aren't in the virtual tree
  // (e.g. entity subfolders navigated from TrackingEntityGrid).
  const selectedNode = selectedPath
    ? (resolveNodeByPath(virtualRoot, selectedPath) ?? syntheticNodeForPath(selectedPath))
    : null;

  // D19 (2026-05-22): workspace-wide setBreadcrumb removed. The full
  // path-trail lives inside the surface body via SurfaceIdentityHeader.
  // Per-window locator (2026-06-25): the OS GlobalLocatorStrip shows
  // "Files › {leaf}" (the selected node's name) so each open window states its
  // own position. This is the SINGLE back affordance — the shell renders no
  // parallel row. Leaf `onClick` = "back to the listing": clear the selection
  // AND (on narrow) drill out of the viewer to the tree.
  // List mode (nothing selected) registers [] — flat "Files" title.
  useWindowCrumb(
    'files',
    selectedNode
      ? [{
          label: selectedNode.name,
          kind: 'context',
          onClick: () => { setSelectedPath(null); drillOutRef.current(); },
        }]
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

  // Cross-surface re-seed: a live-mounted Files window can receive a NEW
  // deep-link param without remounting (e.g. Work → Files entity-to-entity via
  // navigateToSurface). When a fresh non-empty param appears, apply it to the
  // selection, then DRAIN it — same one-shot discipline as the mount seed, so
  // it can never re-clobber on a later tree refresh. Keyed on the param VALUE
  // (not on `treeNodes`), so tree-identity churn never retriggers it. The
  // MOUNT-time param is owned by the seed path in loadExplorer; this effect
  // waits for the seed to be consumed so it only handles POST-mount jumps.
  useEffect(() => {
    if (!seedConsumedRef.current) return; // mount param belongs to the seed
    if (!pathParam && !domainParam) return;
    // Ignore a value equal to the initial mount seed. fp.set drains the URL via
    // history.replaceState, which does NOT re-fire useSearchParams — so the
    // stale mount value can linger in this closure. Only a REAL post-mount
    // navigation (router push, which does re-render) brings a value != the
    // seed. This is the belt to the seedConsumedRef braces: even a stray
    // re-render can't re-apply the ghost path.
    if (pathParam === seedRef.current.path && domainParam === seedRef.current.domain) return;
    if (pathParam) {
      setSelectedPath(pathParam);
    } else if (domainParam) {
      // ADR-388 D1: domains nest under the literal operation/ root.
      setSelectedPath(`/workspace/operation/${domainParam}`);
    }
    fp.set({ path: null, domain: null });
    // fp.set stable; keyed on the param values so a new jump re-fires but a
    // tree refetch does not. eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathParam, domainParam]);

  // ADR-297 D19.2: in-surface selection is component state, NOT a URL write.
  // The Files surface runs as a window on the Desktop (pathname `/desktop`);
  // writing `/files?path=…` on every click flipped pathname → /files, which
  // tripped AuthenticatedLayout's pathname→foreground effect + SurfaceViewport's
  // pathnameSlug resolution, disrupting the launcher/topbar (operator-observed
  // KVK 2026-06-12). `?path=` survives only as a COLD-LOAD deep-link (read on
  // entry to seed selectedPath) — it is never written from intra-surface clicks.
  const handleExplorerSelect = useCallback((node: TreeNode) => {
    setShowTrash(false);
    setSelectedPath(node.path);
    activateBodyRef.current(); // narrow: drill into the viewer
  }, []);

  // Path-based select — a path string, not a TreeNode. The file may not be in
  // the visible tree (e.g. a folder-Details revision row deep-links into a
  // `_`-prefixed file hidden from the explorer); syntheticNodeForPath resolves
  // the viewer. Selecting via a folder-Details row also drops Details back to
  // the (newly-selected) node's own scope.
  const handleExplorerSelect_byPath = useCallback((path: string) => {
    setShowTrash(false);
    setSelectedPath(path);
    activateBodyRef.current(); // narrow: drill into the viewer
  }, []);

  // ADR-329 (amended): right-click "Get Info" on a tree node → select it (so
  // Details scopes to it) and open the Details panel.
  const handleGetInfo = useCallback((node: TreeNode) => {
    setSelectedPath(node.path);
    setDetailsOpen(true);
  }, []);

  // ADR-400 Amendment 1 operator verbs — the human reorganizes their whole
  // workspace (all of it except system/ + machine-config). The backend is
  // authoritative; the FE is OPTIMISTIC — it offers the verb, pre-empts the
  // obvious carve with a nice message, and surfaces the backend's honest 403 on
  // the rest (the Windows-Explorer model). No defensive greying.
  //
  // The handlers take a minimal {path, name} so every surface — tree, RecentsView
  // grid, ContentViewer folder listing — shares one implementation.
  //
  // ADR-400 polish (2026-07-03): no more window.alert/confirm/prompt. Feedback
  // comes through the universal action layer (useFeedback): a styled confirm
  // for the carve + the trash gate, a runAction pending→outcome toast for the
  // API call. Move + Rename use a folder-picker / rename modal (no raw-path
  // typing). See docs/design/ACTION-FEEDBACK.md.

  // Pre-empt the obvious carve (system/ + machine-config) with a plain,
  // macOS-style modal before we even call the backend. Returns true if blocked.
  const carveGuard = useCallback(async (path: string): Promise<boolean> => {
    if (operatorCanOrganize(path)) return false;
    const { title, body } = organizeBlockedReason(path);
    await confirm({ title, body, confirmLabel: 'OK', cancelLabel: '' });
    return true;
  }, [confirm]);

  // Rename — opens the RenameModal (single field, no prompt). The modal's
  // onSubmit calls this with the chosen new leaf name.
  const [renameTarget, setRenameTarget] = useState<{ path: string; name: string } | null>(null);
  const openRename = useCallback(async (t: { path: string; name: string }) => {
    if (await carveGuard(t.path)) return;
    setRenameTarget(t);
  }, [carveGuard]);

  const commitRename = useCallback(async (t: { path: string; name: string }, nextLeaf: string) => {
    const parent = t.path.slice(0, t.path.lastIndexOf('/'));
    const newPath = `${parent}/${nextLeaf}`;
    if (newPath === t.path) return;
    try {
      const r = await runAction(() => api.documents.move(t.path, newPath), {
        pending: 'Renaming…',
        success: 'Renamed',
        error: (e) => (e instanceof APIError ? (e.data as { detail?: string })?.detail || 'Rename failed' : 'Rename failed'),
      });
      await loadExplorer();
      if (r?.path) setSelectedPath(r.path);
    } catch { /* error toast already surfaced; stop (don't refresh on failure) */ }
  }, [runAction, loadExplorer]);

  // Move — opens the MoveToFolderModal (folder-picker tree, no raw-path typing).
  const openMove = useCallback(async (t: { path: string; name: string }) => {
    if (await carveGuard(t.path)) return;
    setMoveTarget(t);
  }, [carveGuard]);

  const commitMove = useCallback(async (fromPath: string, destFolder: string) => {
    const leaf = fromPath.slice(fromPath.lastIndexOf('/') + 1);
    const newPath = destFolder.endsWith('/') ? `${destFolder}${leaf}` : `${destFolder}/${leaf}`;
    if (newPath === fromPath) return;
    try {
      const r = await runAction(() => api.documents.move(fromPath, newPath), {
        pending: 'Moving…',
        success: 'Moved',
        error: (e) => (e instanceof APIError ? (e.data as { detail?: string })?.detail || 'Move failed' : 'Move failed'),
      });
      await loadExplorer();
      if (r?.path) setSelectedPath(r.path);
    } catch { /* error toast already surfaced; stop */ }
  }, [runAction, loadExplorer]);

  const handleTreeDelete = useCallback(async (t: { path: string; name: string }) => {
    if (await carveGuard(t.path)) return;
    const ok = await confirm({
      title: `Move “${t.name}” to Trash?`,
      body: 'It stays recoverable — you can restore it from Trash any time.',
      confirmLabel: 'Move to Trash',
      danger: true,
    });
    if (!ok) return;
    try {
      await runAction(() => api.documents.delete(t.path), {
        pending: 'Moving to Trash…',
        success: 'Moved to Trash',
        error: (e) => (e instanceof APIError ? (e.data as { detail?: string })?.detail || 'Delete failed' : 'Delete failed'),
      });
      await loadExplorer();
      setSelectedPath((prev) => (prev === t.path ? null : prev));
    } catch { /* error toast already surfaced; stop */ }
  }, [carveGuard, confirm, runAction, loadExplorer]);

  // ADR-400: the operator's file verbs as one bundle, threaded to every file
  // surface (tree + RecentsView grid + ContentViewer folder listing) so the
  // right-click menu works on the MAIN PANEL, not only the left tree. Properties
  // + Open are the reads; rename/move/delete the organize verbs.
  const fileVerbs = useMemo(() => ({
    onOpen: (t: { path: string }) => handleExplorerSelect_byPath(t.path),
    onProperties: (t: { path: string }) => { setShowTrash(false); setSelectedPath(t.path); setDetailsOpen(true); },
    onRename: openRename,
    onMove: openMove,
    onDelete: handleTreeDelete,
  }), [handleExplorerSelect_byPath, openRename, openMove, handleTreeDelete]);

  // Upload success (2026-07-01): after files land in the Intake raw lane
  // (inbound/uploads/{principal}/{slug}.{ext}, ADR-395), refresh the tree AND
  // take the operator to the new file — select the uploaded workspace path. The
  // tree auto-expands the Intake root (WorkspaceTree's nodeContainsPath effect)
  // and highlights the new node; the viewer opens it. The operator SEES the
  // result of the add, instead of the modal closing silently onto an unchanged-
  // looking tree. reload → then select so the fresh node exists when it resolves.
  const handleUploaded = useCallback(async (workspacePath: string) => {
    await loadExplorer();
    setSelectedPath(workspacePath);
    activateBodyRef.current(); // narrow: drill into the viewer
  }, [loadExplorer]);

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
  // The nav region the shell hosts: Explorer header (label + upload) over the
  // Recents item + tree. On narrow screens the shell drops this in full-width;
  // selecting drills into the viewer. The prior in-surface Explorer header
  // (with the manual collapse `×`) folds in here — the shell owns collapse now.
  const treePaneContent = (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border shrink-0 gap-2">
        <div className="min-w-0">
          <p className="text-sm font-medium text-foreground">Explorer</p>
          <p className="text-[11px] text-muted-foreground">Workspace context and settings</p>
        </div>
        {/* ADR-329: 'add' is an operator verb, homed on Files. On success the
            surface jumps to the new file in Uploads/ (handleUploaded). */}
        <UploadButton onUploaded={handleUploaded} />
      </div>
      <div className="flex-1 overflow-y-auto">
        {fileTreeLoading && treeNodes.length === 0 ? (
          <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Loading...
          </div>
        ) : treeNodes.length > 0 ? (
          <div className="p-2">
            <button
              onClick={() => { setShowTrash(false); setSelectedPath(null); activateBodyRef.current(); }}
              aria-current={selectedPath === null && !showTrash ? 'page' : undefined}
              className={cn(
                'w-full flex items-center gap-2 px-2 py-1.5 mb-1 rounded-md text-left text-sm transition-colors',
                selectedPath === null && !showTrash
                  ? 'bg-primary/10 text-foreground font-medium'
                  : 'text-muted-foreground hover:bg-muted/40 hover:text-foreground',
              )}
              title="Recent changes across the workspace"
            >
              <History className="w-4 h-4 shrink-0" />
              <span>Recents</span>
            </button>
            {/* ADR-400 D4: Trash — the reversible home of the delete verb. */}
            <button
              onClick={() => { setShowTrash(true); setSelectedPath(null); activateBodyRef.current(); }}
              aria-current={showTrash ? 'page' : undefined}
              className={cn(
                'w-full flex items-center gap-2 px-2 py-1.5 mb-1 rounded-md text-left text-sm transition-colors',
                showTrash
                  ? 'bg-primary/10 text-foreground font-medium'
                  : 'text-muted-foreground hover:bg-muted/40 hover:text-foreground',
              )}
              title="Deleted files — recoverable"
            >
              <Trash2 className="w-4 h-4 shrink-0" />
              <span>Trash</span>
            </button>
            <WorkspaceTree
              nodes={treeNodes}
              selectedPath={selectedPath || undefined}
              onSelect={handleExplorerSelect}
              onGetInfo={handleGetInfo}
              onRename={openRename}
              onMove={openMove}
              onDelete={handleTreeDelete}
              onMoveByDrag={commitMove}
              canOrganize={operatorCanOrganize}
            />
          </div>
        ) : (
          <div className="p-3 text-sm text-muted-foreground">Failed to load explorer</div>
        )}
      </div>
    </div>
  );

  // The viewer body — Trash view · selected node · or the Recents empty-state.
  // This is the shell's `children` (the detail pane).
  const bodyContent = showTrash ? (
    <div className="flex-1 min-h-0">
      <TrashView />
    </div>
  ) : selectedNode ? (
    <div className="flex-1 overflow-auto bg-background flex flex-col min-h-0">
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
            {/* ADR-388 D5 / ADR-400: Properties → modal. Also reachable by
                right-click on any tree/row node. */}
            <button
              onClick={() => setDetailsOpen(true)}
              title="Properties"
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground"
            >
              <Info className="w-3.5 h-3.5" />
              Properties
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
            verbs={fileVerbs}
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
    // "Recents" view — a columnar glance of recent authored changes across the
    // workspace. Selecting a row swaps to the node view.
    <div className="flex-1 min-h-0">
      <RecentRevisions onSelectPath={handleExplorerSelect_byPath} verbs={fileVerbs} />
    </div>
  );

  // 2026-06-30 unification: mount the shared SettingsPaneShell in navContent +
  // resizable mode. The shell owns the responsive contract (wide two-pane tree |
  // viewer / narrow drill-in), the resizable nav width, and the narrow collapse
  // — replacing Files' bespoke split-pane/resize/icon-rail plumbing (Singular
  // Implementation). `hasSelection` gates the narrow body (a selected node OR
  // the explicit Recents drill-in); `onActivateRef`/`onDrillOutRef` give the
  // tree + the OS locator their drill in/out hooks. The back affordance is the
  // single GlobalLocatorStrip (the useWindowCrumb above), not a shell row.
  return (
    <>
      <SettingsPaneShell
        windowSlug="files"
        navLabel="Explorer"
        navContent={treePaneContent}
        navPadded={false}
        resizable
        // Files' body is always meaningful once drilled in — a selected node,
        // or the Recents view (the deselected state). So narrow drill always
        // has something to show.
        hasSelection
        onActivateRef={registerActivate}
        onDrillOutRef={registerDrillOut}
      >
        <div className="flex-1 min-w-0 min-h-0 flex flex-col overflow-y-auto bg-background">
          {bodyContent}
        </div>
      </SettingsPaneShell>

      {/* ADR-400: Properties modal — the flat Kind/Location/Ownership/Modified/
          Contributors block + the ADR-209 revision history. Opened by the header
          button or a right-click on any tree/folder-listing node. */}
      <PropertiesModal
        node={detailsOpen ? selectedNode : null}
        onClose={() => setDetailsOpen(false)}
        onSelectPath={handleExplorerSelect_byPath}
        onRevert={loadExplorer}
      />

      {/* ADR-400 Q2 / polish: Move — the folder-picker modal (a destination
          tree, never a raw-path text field). Also the keyboard/accessibility
          path for the drag-and-drop the tree offers. */}
      <MoveToFolderModal
        target={moveTarget}
        roots={treeNodes}
        canOrganize={operatorCanOrganize}
        onClose={() => setMoveTarget(null)}
        onMove={async (destFolder) => {
          const t = moveTarget;
          setMoveTarget(null);
          if (t) await commitMove(t.path, destFolder);
        }}
      />

      {/* ADR-400 polish: Rename — a single-field modal (no window.prompt). */}
      <RenameModal
        target={renameTarget}
        onClose={() => setRenameTarget(null)}
        onSubmit={async (nextLeaf) => {
          const t = renameTarget;
          setRenameTarget(null);
          if (t) await commitRename(t, nextLeaf);
        }}
      />
    </>
  );
}
