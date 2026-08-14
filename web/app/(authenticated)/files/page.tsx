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
 * Deep-link params (ARRIVAL ONLY, per ADR-297 D19.2):
 *   ?files.domain={key}  — open a context domain folder
 *   ?files.path={path}   — open any workspace path
 *
 * These are how a deep-link ARRIVES (a shared link, or a cross-surface jump via
 * navigateToSurface('files', {path})). One handler consumes them — the arrival
 * effect — which opens the path and then DRAINS the param; see "THE ONE ARRIVAL
 * DOOR". They are inbound transport only: in-surface file/folder clicks DO NOT
 * write the URL, because selection is component state. Writing `/files?path=…`
 * on every click flipped pathname away from /desktop and disrupted the
 * launcher/topbar (operator-observed KVK 2026-06-12).
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  Cable,
  Loader2,
  Info,
  History,
  Trash2,
  FolderPlus,
  Upload,
} from 'lucide-react';
import { SettingsPaneShell } from '@/components/settings/SettingsPaneShell';
import { useCoarsePointer } from '@/hooks/useCoarsePointer';
import { useNarrative } from '@/contexts/NarrativeContext';
import { useSurfaceParam, useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { useWindowCrumb } from '@/contexts/BreadcrumbContext';
import type { DeskSurface } from '@/types/desk';
import { api, APIError } from '@/lib/api/client';
import { operatorCanOrganize } from '@/lib/workspace/ownership';
import { useFeedback } from '@/contexts/FeedbackContext';
import { useFileOrganizeVerbs } from '@/hooks/useFileOrganizeVerbs';
import {
  ensureKindApps,
  extractTemplate,
  isArtifactCandidate,
  knownKind,
  rememberKind,
  resolveDeclarationApplication,
  resolveSurfaceApplication,
} from '@/lib/file-types';
import { resolveHandlers, applyDefaultOverride } from '@/lib/file-types/handlers';
import { resolveApps } from '@/lib/file-types/apps';
import { NewFolderModal } from '@/components/workspace/NewFolderModal';
import { MoveToFolderModal } from '@/components/workspace/MoveToFolderModal';
import { ShareDialog } from '@/components/workspace/ShareDialog';
import { cn } from '@/lib/utils';
import { formatAuthorLabel } from '@/lib/workspace/attribution';
import { WorkspaceTree } from '@/components/workspace/WorkspaceTree';
import { RecentRevisions } from '@/components/workspace/RecentRevisions';
import { TrashView } from '@/components/workspace/TrashView';
import { UploadModal } from '@/components/workspace/UploadButton';
import { CanvasContextMenu } from '@/components/workspace/CanvasContextMenu';
import { ContentViewer } from '@/components/workspace/ContentViewer';
import { PropertiesModal } from '@/components/workspace/PropertiesModal';
import { FilesViewToggle } from '@/components/workspace/FilesViewToggle';
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
  // ADR-423 follow-on (Files-model note, 2026-07-09): the operator zone —
  // 'work' (Documents) | 'arrival' (Downloads) | 'system' (collapsed residue).
  // The SINGULAR source is WORKSPACE_ROOTS in workspace_paths.py; the FE only
  // renders it. Absent (older API) → treated as 'work' so nothing hides.
  group?: 'work' | 'arrival' | 'system';
  description: string;
  icon: string;
  file_count: number;
  exists: boolean;
}

// ADR-423 follow-on: synthetic parent nodes for the two grouped zones — one
// "Downloads" (all arrival roots merged, since inbound/ + legacy uploads/ are
// the same "what arrived" concept) and one "System files" fold (kernel residue).
// Their paths are virtual /explorer/ handles (never fetched); children are the
// real roots' subtrees, each still clickable + deep-linkable.
const DOWNLOADS_NODE_PATH = '/explorer/downloads';
const SYSTEM_FILES_NODE_PATH = '/explorer/system-files';

function buildRootNodes(input: {
  roots: WorkspaceRoot[];
  subtrees: Record<string, TreeNode[]>; // root name → its getTree children
  domainTitles: Record<string, string>; // operation/{folder} → registry display name
}): TreeNode[] {
  // The only path still hidden: operation/signals (temporal churn log).
  const isHidden = (node: TreeNode): boolean =>
    node.path.startsWith('/workspace/operation/signals');
  const notHidden = (node: TreeNode) => !isHidden(node);

  // Turn one root into a tree node (children lazy-loaded, operation/ domains
  // relabeled). Shared by both the top-level zones and the System-files fold.
  const rootToNode = (root: WorkspaceRoot): TreeNode => {
    let children = filterNodes(input.subtrees[root.name], notHidden);
    // operation/ (now "Documents") keeps its registry display-name enrichment on
    // domain folders — the substrate stays literal, the operator sees "Competitors".
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
      icon_name: root.icon, // ADR-422 D3: kernel-named glyph
      children,
    } satisfies TreeNode;
  };

  // ADR-423 follow-on (Files-model note): partition roots by operator ZONE.
  //   work    → the home level: Documents (the system-provided authored-work
  //             home = operation/) PLUS any operator/AI-authored PEER folder
  //             (an unknown top-level root defaults to 'work' — it renders as a
  //             PEER of Documents, not inside it; the OS home-directory model,
  //             note §3b). All rendered as direct top-level nodes.
  //   arrival → Downloads: ALL arrival roots (inbound/ + legacy uploads/) merge
  //             under ONE "Downloads" node — they are the same "what arrived"
  //             concept, so two identical "Downloads" labels would confuse.
  //   system  → System files: kernel residue folded under ONE collapsed
  //             disclosure sorted last (the OS "Show system files" model).
  // `group` is the singular backend signal (WORKSPACE_ROOTS); absent → 'work'.
  const zoneOf = (r: WorkspaceRoot): 'work' | 'arrival' | 'system' => r.group ?? 'work';

  // ADR-457 P3 (2026-07-14) — loose machine FILES at the workspace root
  // (_captures.yaml, _capture_signal.yaml, _recurrences.yaml,
  // _workspace_guide.md, …) arrive from the roots API as pseudo-roots named by
  // the file. They are kernel state, not the operator's work — without this
  // they render beside Documents as top-level "folders" (the stress-test
  // wart). Fold them into the System files disclosure as FILE nodes. This is
  // the display half of the root-directories invariant; the substrate half
  // (re-homing them under system/) is P3's coherent migration, deliberately
  // deferred to the next scheduler-touching pass so the move happens once,
  // not piecemeal.
  const isLooseMachineRoot = (r: WorkspaceRoot) => r.name.startsWith('_');
  const looseFileNodes: TreeNode[] = input.roots
    .filter(isLooseMachineRoot)
    .map((r) => ({
      name: r.name,
      path: r.path, // /workspace/{name} IS the real file path for a loose root
      type: 'file' as const,
      summary: 'Workspace machine state (kernel-managed).',
      icon_name: 'file-cog',
    }));
  const realRoots = input.roots.filter((r) => !isLooseMachineRoot(r));

  const workNodes = realRoots.filter((r) => zoneOf(r) === 'work').map(rootToNode);
  const arrivalRoots = realRoots.filter((r) => zoneOf(r) === 'arrival');
  const systemRoots = realRoots.filter((r) => zoneOf(r) === 'system');

  const out: TreeNode[] = [...workNodes];

  // Merge the arrival roots under one "Downloads". If there's exactly one arrival
  // root (the common case — inbound/ only), promote it directly (no needless
  // wrapper). If more than one (inbound/ + legacy uploads/), merge their subtrees.
  if (arrivalRoots.length === 1) {
    const only = rootToNode(arrivalRoots[0]);
    out.push({ ...only, name: 'Downloads', path: arrivalRoots[0].path });
  } else if (arrivalRoots.length > 1) {
    const mergedChildren = arrivalRoots.flatMap((r) => rootToNode(r).children ?? []);
    out.push({
      name: 'Downloads',
      // Point the merged node at the canonical arrival root (inbound/) so a
      // click still lands somewhere real; legacy uploads/ files show as children.
      path: arrivalRoots.find((r) => r.name === 'inbound')?.path ?? arrivalRoots[0].path,
      type: 'folder' as const,
      summary: 'What arrived in your workspace — uploads and observations from connected apps. Kept as received.',
      icon_name: 'arrow-down-to-line',
      children: mergedChildren,
    });
  }

  // The one collapsed "System files" disclosure — virtual node, real children.
  // Loose machine files at the root (ADR-457 P3 display fold) render after the
  // system roots, as plain file rows.
  if (systemRoots.length > 0 || looseFileNodes.length > 0) {
    out.push({
      name: 'System files',
      path: SYSTEM_FILES_NODE_PATH,
      type: 'folder' as const,
      summary: 'Files the system uses to run your workspace — settings, agent homes, runtime state.',
      icon_name: 'settings',
      children: [...systemRoots.map(rootToNode), ...looseFileNodes],
    });
  }

  return out;
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
  const { runAction, toast } = useFeedback();
  // Touch parity (2026-07-12): the canvas New Folder / Add Files verbs live in a
  // right-click menu (mouse-only). On a coarse pointer we surface them as
  // buttons in the Explorer header — the Finder-parity clean look stays on
  // desktop, touch gets a reachable trigger.
  const coarse = useCoarsePointer();

  // ADR-358 D6 (2026-06-25): read this window's OWN deep-link params under
  // the `files.` namespace (`?files.domain=`, `?files.path=`) so they never
  // collide with another open window on the shared /desktop URL. These are
  // ARRIVAL transports (a shared link / cross-surface jump); the surface drives
  // its live selection through internal `selectedPath` state and deliberately
  // does NOT write back to the URL (see the click handlers).
  const fp = useSurfaceParam('files');
  // ADR-451: the Finder routes surface-owned formats to their app.
  const { navigateToSurface } = useSurfacePreferences();
  const domainParam = fp.get('domain');
  const pathParam = fp.get('path');

  const [treeNodes, setTreeNodes] = useState<TreeNode[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  // ADR-570: the Open With choice for the OPEN file — which app of the type's
  // set to mount inline (e.g. 'markdown.editor'). Selection state beside
  // selectedPath (D19.2 — never a URL write); null = the type's default app.
  const [inlineApp, setInlineApp] = useState<{ path: string; appId: string } | null>(null);
  // ADR-400 D4: the Trash nav item toggles the center pane to the Trash view.
  const [showTrash, setShowTrash] = useState(false);
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

  // Finder-parity (2026-07-09): the New Folder / Add Files verbs left the header
  // for the canvas right-click menu (Finder has no visible buttons for either).
  // `canvasMenu` = the background-menu open-state (x/y click point); `uploadOpen`
  // = the Add Files modal, summonable from the menu OR from a drag-drop onto the
  // canvas (which pre-seeds it with `droppedFiles`). One import path, no button.
  const [canvasMenu, setCanvasMenu] = useState<{ x: number; y: number } | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  // The resolved arrival destination (ADR-555 D3) — null = the intake lane.
  const [uploadDest, setUploadDest] = useState<{ path: string; label: string } | null>(null);
  // The folder-listing drop highlight (ADR-552) — the grid's own, kept apart
  // from the tree's so the two panes never fight over one highlight.
  const [listingDropTarget, setListingDropTarget] = useState<string | null>(null);

  // ── The multi-selection (ADR-553) ──────────────────────────────────────
  // A SET carried BESIDE the selection, never replacing it — ADR-519 D4.1's
  // rule, inherited: `selectedPath` stays the primary (every existing reader
  // still gets exactly one path), and this is the additional members. Only the
  // gestures that genuinely take N consult it.
  //
  // ADR-519 also shipped a PROD TRAP here once — a multi-select with no way
  // out. Withdrawal is therefore part of the feature, not a follow-up: Escape
  // clears, a background click clears, and any single-target verb clears
  // before it acts (D3).
  const [alsoSelected, setAlsoSelected] = useState<string[]>([]);
  const clearSet = useCallback(() => setAlsoSelected([]), []);
  const [moveSetOpen, setMoveSetOpen] = useState(false);
  // The full set the next N-taking verb acts on — the primary FIRST, so a
  // reader that takes `[0]` gets the same file `selectedPath` names.
  const selectionSet = useMemo(
    () => (selectedPath ? [selectedPath, ...alsoSelected.filter((p) => p !== selectedPath)] : []),
    [selectedPath, alsoSelected],
  );
  const [droppedFiles, setDroppedFiles] = useState<File[] | null>(null);
  const [canvasDragOver, setCanvasDragOver] = useState(false);

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
  // A ref mirror of the openPath funnel (defined below), so the earlier-declared
  // loadExplorer + the post-mount deep-link effect can route a `?files.path=`
  // through the ONE open door without a definition-order / stale-closure cycle.
  // Same idiom as activateBodyRef above (a late callback reached from an early
  // one). Assigned once openPath exists; a deep-link that lands before that tick
  // is impossible (openPath is defined in the same render).
  const openPathRef = useRef<(path: string) => void>(() => {});
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

      // A deep-link is NOT handled here. `loadExplorer` re-runs on a 30s timer
      // and on every window-focus refetch; the arrival effect below owns the
      // param, keyed on its VALUE, so the tree load and the open are
      // independent. See "THE ONE ARRIVAL DOOR".

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
    // Deps intentionally empty — loadExplorer must not re-identify on param
    // changes (that would retrigger the mount effect's interval wiring). The
    // deep-link is not read here at all; the arrival effect owns it.
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

  // ── THE ONE ARRIVAL DOOR ───────────────────────────────────────────────
  //
  // Every way a deep-link REACHES this surface lands here: a cold-load shared
  // link, and a cross-surface jump (`navigateToSurface('files', {path})`) from
  // Radar, Settings, or the shell. One handler, keyed on the param VALUE.
  //
  // 2026-08-13 (operator-observed KVK, Radar "open folder" → generic Recents).
  // This REPLACES a two-handler shape — a mount SEED captured on first render
  // plus this post-mount effect — which raced and lost. In canvas mode (and on
  // mobile) SurfaceViewport renders only the foregrounded surface, so a
  // backgrounded Files window is UNMOUNTED; a jump into it therefore REMOUNTS
  // rather than re-rendering. On that remount the seed captured `null` (the
  // param reaches the URL via reconcileUrl's history.replaceState, which has
  // not re-rendered useSearchParams yet), while this effect bailed on
  // `!seedConsumedRef.current` — a ref that only flips after loadExplorer's
  // network round-trip. Keyed on values that never changed again, it never
  // re-fired: param stranded in the URL, `selectedPath` null, Recents.
  //
  // The staleness the seed was defending against (a dead `?files.path=`
  // re-applying on every 30s refetch) is now handled by the two things that
  // actually address it: this effect never runs on a tree refetch (it is keyed
  // on the params, not on `treeNodes`), and the DRAIN below removes the param
  // the moment it is honoured. Belt-and-braces guards that can outvote the
  // real signal are worse than the staleness they prevent.
  useEffect(() => {
    if (!pathParam && !domainParam) return;
    // Through the ONE open door (openPathRef) — a deep-link to an artifact
    // opens its app, folders/unclaimed types fall through to inline. The path
    // need not be in the virtual tree: syntheticNodeForPath resolves the
    // viewer for entity subfolders and `_`-prefixed files.
    if (pathParam) {
      openPathRef.current(pathParam);
    } else if (domainParam) {
      // ADR-388 D1: domains nest under the literal operation/ root.
      openPathRef.current(`/workspace/operation/${domainParam}`);
    }
    // Drain — the param has done its one job. `selectedPath` is the live
    // selection from here on; the URL is not the source of truth once open.
    fp.set({ path: null, domain: null });
    // fp.set stable; keyed on the param values so a new jump re-fires but a
    // tree refetch does not. eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathParam, domainParam]);

  // ADR-297 D19.2: in-surface selection is component state, NOT a URL write.
  // The Files surface runs as a window on the Desktop (pathname `/desktop`);
  // writing `/files?path=…` on every click flipped pathname → /files, which
  // tripped AuthenticatedLayout's pathname→foreground effect + SurfaceViewport's
  // pathnameSlug resolution, disrupting the launcher/topbar (operator-observed
  // KVK 2026-06-12). `?path=` survives only as an inbound ARRIVAL param
  // (opened + drained above) — it is never written from intra-surface clicks.
  // Path-based select — a path string, not a TreeNode. The file may not be in
  // the visible tree (e.g. a folder-Details revision row deep-links into a
  // `_`-prefixed file hidden from the explorer); syntheticNodeForPath resolves
  // the viewer. Selecting via a folder-Details row also drops Details back to
  // the (newly-selected) node's own scope.
  //
  // ── openPath — THE ONE DOOR that opens a workspace path ────────────────
  //
  // 2026-07-24 (Option A cleanup). Every way a member opens a file in the Files
  // surface routes through here — the tree click, the folder-listing click, the
  // right-click Open verb, a Recents click, a cold-load / post-mount deep-link
  // (`?files.path=`), and a just-uploaded file. There is deliberately no second
  // path that calls `setSelectedPath` for a FILE: a new door consults the app
  // layer by calling this, and physically cannot bypass it (a bare
  // setSelectedPath for an artifact is the regression the gate forbids).
  //
  // Why a funnel and not per-call-site resolution: the pre-cleanup shape
  // consulted the resolver at each open site, so every entry point had to
  // REMEMBER to. The tree forgot (rendered a Studio artifact blank inline); the
  // two deep-link jumps forgot (a shared link to an artifact rendered blank).
  // Same bug three times — the signature of a missing funnel. This is the
  // Singular Implementation of "open".
  //
  // The decision inside: ADR-451 — a format claimed by a surface-owning app (a
  // Studio artifact, an Images stage) opens in its APP, like a .pptx opening
  // PowerPoint; everything unclaimed (folders, .md, images, pdf, arrivals) drops
  // to the inline viewer, the Quick Look analog. ADR-473 D2 — WHICH app owns an
  // artifact comes from its declared type (`data-template`), read from the one
  // file being opened (the tree carries no kind); a read failure falls back to
  // the default app (pre-ADR-473 behavior).
  //
  // `selectInline` is the terminal for an unclaimed path — the ONLY sanctioned
  // setSelectedPath-for-a-file site for an OPEN (nested so it can't be called
  // from outside). The one deliberate carve: Get Info / Properties
  // (handleGetInfo, fileVerbs.onProperties) also setSelectedPath a file path,
  // but their intent is to SCOPE THE DETAILS PANEL to that file's metadata, not
  // to open its body — routing those through openPath would wrongly launch the
  // app when the operator asked to inspect. Those are select-to-inspect, not
  // open; the gate's ban is on open-a-file setSelectedPath outside the funnel,
  // and it allowlists the two Details sites by name.
  const openPath = useCallback((path: string) => {
    // ADR-570: which INLINE app mounts is part of the open decision — the
    // default open clears any prior Open With choice; an override-chosen
    // inline app (the editor) arrives via `appId`.
    const selectInline = (appId?: string) => {
      setShowTrash(false);
      setSelectedPath(path);
      const defaultApp = resolveApps(path)[0];
      setInlineApp(appId && appId !== defaultApp ? { path, appId } : null);
      activateBodyRef.current(); // narrow: drill into the viewer
    };
    // ADR-486: a hub DECLARATION (operation/{topic}/_radar.yaml) is claimed by
    // the Radar app — a path-only check ahead of the artifact layer, still
    // inside the one openPath funnel (no content read; the app derives the
    // topic from the handed path).
    const declApp = resolveDeclarationApplication(path);
    if (declApp) {
      navigateToSurface(declApp.surface, { [declApp.param]: path });
      return;
    }
    // A non-artifact path (folder, image, arrival) never routes to an app —
    // isArtifactCandidate is a cheap path-only pre-check, so we don't read
    // content for the 500-row tree, only for a file that might route. The
    // ADR-570 carve: a type with MORE than one inline app (.md — viewer +
    // editor) falls through to the async branch, because the file's own
    // Opens-With override (ADR-514 D2.4) must be consulted for the choice to
    // be honest — a set-default that the open ignores is decoration.
    if (!isArtifactCandidate(path) && resolveApps(path).length <= 1) {
      selectInline();
      return;
    }
    void (async () => {
      let kind: string | null = null;
      let override: string | null = null;
      try {
        // Run-1 second finding: the kind→app MAP is as lazy as the kind — a
        // fresh session that never mounted an authoring surface consulted an
        // empty association and routed every kind to the default app. The
        // association loads WITH the content read, before any resolution.
        const [file] = await Promise.all([
          api.workspace.getFile(path),
          ensureKindApps(),
        ]);
        kind = extractTemplate(file.content ?? '');
        rememberKind(path, kind); // the menu's sync resolution reads this cache
        // ADR-514 D2.4: the file's own default binding, if the operator set one.
        override =
          (file.metadata as { launch?: { handler?: string } } | undefined)?.launch
            ?.handler ?? null;
      } catch {
        /* fall through to the registry default */
      }
      // The override re-ranks the set; a stale id falls through, so a removed
      // app can never strand the file (applyDefaultOverride).
      const chosen = applyDefaultOverride(
        resolveHandlers({ paths: [path], isFolder: false, kind }),
        override,
      )[0];
      if (chosen && chosen.open.via === 'surface') {
        navigateToSurface(chosen.open.surface, { [chosen.open.param]: path });
        return;
      }
      selectInline(chosen?.id);
    })();
  }, [navigateToSurface]);
  // ADR-514 D2.2 — the handler set for a menu target. `Open` above fires the
  // default; this is what makes the ALTERNATIVES visible. The set is derived
  // from the same two registries openPath consults, merged into one ordered
  // list (lib/file-types/handlers), so the menu and the open funnel can never
  // disagree about what can open a file.
  //
  // ADR-518 click-pass run-1 finding: openPath resolved WITH the file's kind
  // (it reads content) while this menu resolution did not — so the menu
  // showed "Studio (default)" for a document and never listed Docs. The kind
  // rides the shared PATH_KIND cache (rememberKind at every content read);
  // when the menu opens on an artifact whose kind is not yet known, a
  // fire-and-forget read fills the cache and `kindTick` re-renders the open
  // menu with the honest set. Until it lands, the kind-less order (the
  // pre-ADR-518 behavior) shows — never a wrong route, only a stale label.
  const [kindTick, setKindTick] = useState(0);
  const kindFetchInFlight = useRef<Set<string>>(new Set());
  const assocEnsured = useRef(false);
  const handlersFor = useCallback(
    (t: { path: string; isFile: boolean }) => {
      const kind = t.isFile ? knownKind(t.path) : undefined;
      if (t.isFile && isArtifactCandidate(t.path)) {
        // Run-1 second finding: load the served kind→app association the
        // first time an artifact's menu resolves in this surface — once per
        // mount (the done-guard keeps the resolved promise from ticking a
        // render loop).
        if (!assocEnsured.current) {
          assocEnsured.current = true;
          void ensureKindApps().then(() => setKindTick((n) => n + 1));
        }
        if (!kind && !kindFetchInFlight.current.has(t.path)) {
          kindFetchInFlight.current.add(t.path);
          void api.workspace
            .getFile(t.path)
            .then((f) => {
              rememberKind(t.path, extractTemplate(f.content ?? ''));
              setKindTick((n) => n + 1);
            })
            .catch(() => {
              /* kind stays unknown; the kind-less order stands */
            })
            .finally(() => kindFetchInFlight.current.delete(t.path));
        }
      }
      return resolveHandlers({ paths: [t.path], isFolder: !t.isFile, kind })
        .map((h) => ({ id: h.id, label: h.label }));
    },
    // kindTick re-arms the callback so the OPEN menu re-reads the cache.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [kindTick],
  );

  // Open the target with a NON-default handler. Surface navigation and inline
  // mount are peers here — which one a handler uses is the handler's own
  // declaration, not a branch the caller re-derives.
  const openWith = useCallback(
    (t: { path: string }, handlerId: string) => {
      const handler = resolveHandlers({
        paths: [t.path],
        isFolder: false,
        kind: knownKind(t.path), // same cache as the menu that offered the id
      }).find((h) => h.id === handlerId);
      if (!handler) return;
      if (handler.open.via === 'surface') {
        navigateToSurface(handler.open.surface, { [handler.open.param]: t.path });
        return;
      }
      setShowTrash(false);
      setSelectedPath(t.path);
      // ADR-570: an explicit Open With on an inline handler mounts THAT app
      // (the editor); choosing the type's default is the same as a plain open.
      const defaultApp = resolveApps(t.path)[0];
      setInlineApp(handlerId !== defaultApp ? { path: t.path, appId: handlerId } : null);
      activateBodyRef.current();
    },
    [navigateToSurface],
  );

  // Mirror into the ref so the earlier loadExplorer + post-mount effect route
  // deep-links through this exact funnel (see openPathRef declaration).
  openPathRef.current = openPath;

  // The tree + folder-listing hand a TreeNode; every other door hands a path.
  // Both are the SAME open verb (openPath) — the node wrapper only unwraps.
  const handleExplorerSelect = useCallback(
    (node: TreeNode, e?: { metaKey?: boolean; ctrlKey?: boolean }) => {
      // ADR-553 D1 — ⌘/Ctrl-click TOGGLES membership in the set; a plain click
      // replaces the whole selection. Finder's grammar, and the reason the
      // modifier is the ONLY way in: a member cannot enter a multi-selection by
      // accident, which is half of why ADR-519's trap was a trap.
      const additive = !!(e?.metaKey || e?.ctrlKey);
      if (!additive) {
        clearSet();
        openPath(node.path);
        return;
      }
      if (node.type === 'folder') return; // the set is files — folders have no bulk verb
      if (!selectedPath) {
        openPath(node.path);
        return;
      }
      if (node.path === selectedPath) return; // never let the primary leave the set
      setAlsoSelected((prev) =>
        prev.includes(node.path) ? prev.filter((p) => p !== node.path) : [...prev, node.path],
      );
    },
    [openPath, clearSet, selectedPath],
  );

  // ── The way OUT (ADR-553 D3) ───────────────────────────────────────────
  // ADR-519 shipped an inescapable multi-selection once; withdrawal is part of
  // this feature, not a follow-up. Escape is the universal exit.
  useEffect(() => {
    if (alsoSelected.length === 0) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') clearSet();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [alsoSelected.length, clearSet]);

  // ADR-329 (amended): right-click "Get Info" on a tree node → select it (so
  // Details scopes to it) and open the Details panel.
  const handleGetInfo = useCallback((node: TreeNode) => {
    setSelectedPath(node.path);
    setDetailsOpen(true);
  }, []);

  // ADR-400 Amendment 1 operator verbs — the human reorganizes their whole
  // workspace (all of it except system/ + machine-config). Rename / Move to… /
  // Move to Trash are the ONE shared implementation in `useFileOrganizeVerbs`
  // (extracted so Studio's surface bar offers the identical verbs, ADR-446). The
  // backend is authoritative; the FE is OPTIMISTIC — offer the verb, pre-empt the
  // obvious carve with a nice message, surface the backend's honest 403 on the
  // rest (the Windows-Explorer model). No defensive greying.
  //
  // Files supplies its OWN move-picker tree (`treeNodes`, already loaded) so the
  // hook doesn't double-fetch, and an `onAfterMutate` that refreshes the explorer
  // + re-selects the new path (or clears selection when the file was trashed).
  const { verbs: organizeVerbs, modals: organizeModals } = useFileOrganizeVerbs({
    moveRoots: treeNodes,
    onAfterMutate: (newPath, oldPath) => {
      void loadExplorer();
      // ADR-553 D3 — a single-target verb ENDS the set. Otherwise a set built
      // before a rename/move/trash outlives it and points at paths that no
      // longer exist: the stale-state half of ADR-519's trap, arriving by a
      // different door than the one the Escape hatch guards.
      clearSet();
      // Rename/Move → re-select the new path; Trash (newPath null) → clear the
      // selection only if the trashed file WAS the selected one (the original
      // `prev === t.path` behavior).
      setSelectedPath((prev) => (newPath === null ? (prev === oldPath ? null : prev) : newPath));
    },
  });
  const openRename = organizeVerbs.onRename;
  const openMove = organizeVerbs.onMove;
  const handleTreeDelete = organizeVerbs.onDelete;

  // New Folder — ADR-424 D2: create a folder. `newFolderParent` scopes the act:
  // null = a top-level PEER (peer of Documents/Downloads); a folder path =
  // create INSIDE it (the folder-node menu verb, and the canvas menu when a
  // folder's contents are on screen — the Finder folder-window-background
  // grammar). The modal collects a name and states the destination; this seeds
  // the folder's first file. The parent travels VERBATIM in its own field —
  // the backend sanitizes only the new leaf, so an existing parent segment
  // (`_adr427-probe`) is never rewritten en route.
  const [newFolderOpen, setNewFolderOpen] = useState(false);
  const [newFolderParent, setNewFolderParent] = useState<{ path: string; name: string } | null>(null);
  const openNewFolder = useCallback((parent: { path: string; name: string } | null) => {
    // Virtual /explorer/ groups aren't substrate — refuse honestly up front
    // (the same pre-empt-the-obvious-carve posture as useFileOrganizeVerbs).
    if (parent && !parent.path.startsWith('/workspace/')) {
      toast({ kind: 'error', message: 'You can’t create a folder here — this is a grouping, not a real folder.' });
      return;
    }
    setNewFolderParent(parent);
    setNewFolderOpen(true);
  }, [toast]);
  const closeNewFolder = useCallback(() => {
    setNewFolderOpen(false);
    setNewFolderParent(null);
  }, []);
  const commitNewFolder = useCallback(async (name: string) => {
    try {
      const parentRel = newFolderParent
        ? newFolderParent.path.replace(/^\/workspace\//, '')
        : null;
      const r = await runAction(() => api.documents.createFolder(name, parentRel), {
        pending: 'Creating folder…',
        success: 'Folder created',
        error: (e) => (e instanceof APIError ? (e.data as { detail?: string })?.detail || 'Could not create the folder' : 'Could not create the folder'),
      });
      closeNewFolder();
      await loadExplorer();
      // Jump to the seeded README so the new folder is visible + selected —
      // through THE ONE DOOR (openPath). The seed is markdown today (falls
      // through to inline), but routing keeps the invariant: no open-a-path
      // site outside the funnel.
      if (r?.seeded) openPath(r.seeded);
    } catch { /* error toast already surfaced; keep the modal open to retry */ }
  }, [runAction, loadExplorer, openPath, newFolderParent, closeNewFolder]);

  // Move (deliberate, modal) + drag-move (gesture) both route through the shared
  // hook — `openMove` opens the picker, `commitMove` is the drag fast-path.
  const commitMove = organizeVerbs.commitMove;

  // ADR-529 D1: share OPENS THE DIALOG — it no longer mints on click.
  //
  // This used to be a one-click mint-and-copy with NO role parameter, so every
  // use granted full workspace membership and the toast reported a decision the
  // operator was never asked to make ("anyone with it can join the workspace").
  // That over-grant is closed by construction: the dialog always asks, and it
  // is the single cockpit mint path (Studio's popover and the Properties
  // panel's list/revoke are deleted in the same commit — ADR-529 D4).
  const [shareTarget, setShareTarget] = useState<{ path: string; name: string } | null>(null);
  const handleShare = useCallback((t: { path: string; name: string }) => {
    setShareTarget({ path: t.path, name: t.name });
  }, []);

  // ADR-400: the operator's file verbs as one bundle, threaded to every file
  // surface (tree + RecentsView grid + ContentViewer folder listing) so the
  // right-click menu works on the MAIN PANEL, not only the left tree. Properties
  // + Open are the reads; rename/move/delete the organize verbs; share (ADR-437
  // D4) mints a link to the artifact. (Learn-from moved to the Studio landing
  // — ADR-452 D5: a creation act, not a file operation.)
  const fileVerbs = useMemo(() => ({
    onOpen: (t: { path: string }) => openPath(t.path),
    onProperties: (t: { path: string }) => { setShowTrash(false); setSelectedPath(t.path); setDetailsOpen(true); },
    onRename: openRename,
    onMove: openMove,
    onDelete: handleTreeDelete,
    onShare: handleShare,
    // ADR-514 D1: derive a sibling copy — the kernel names it and records the
    // derived_from edge, so trace on the copy walks back to this file.
    onDuplicate: organizeVerbs.onDuplicate,
    // ADR-514 D2.2: Open fires the default; these expose the rest.
    handlersFor,
    onOpenWith: openWith,
    // Folder-scoped create — right-click a folder (tree or listing) → a new
    // folder INSIDE it. The Explorer "New > Folder" grammar; the canvas menu
    // stays the sibling-level act.
    onNewFolder: (t: { path: string; name: string }) => openNewFolder(t),
    // ADR-569 D7 — the Files door into Keeper's desk (doors-in-context,
    // ADR-514: the gesture lives where the file does; the management does
    // not). Offered on designatable files (the v1 md/csv/json/txt scope,
    // machinery leaves excluded) and on folders (the desk asks for the leaf
    // there). Optimistic beyond that — the desk is the authority and refuses
    // loudly.
    extraItemsFor: (t: { path: string; name: string; isFile: boolean }) => {
      const leaf = t.name;
      const designatable = t.isFile
        ? /\.(md|csv|json|txt)$/i.test(leaf) && !leaf.startsWith('_') && leaf !== 'CONTRACT.md'
        : !t.path.startsWith('/workspace/system');
      if (!designatable) return [];
      return [{
        id: 'keep-current',
        label: 'Keep this current…',
        icon: <Cable className="w-3.5 h-3.5 text-muted-foreground" />,
        onClick: () => navigateToSurface('strings', { file: t.path }),
      }];
    },
  }), [openPath, openRename, openMove, handleTreeDelete, handleShare, organizeVerbs,
       handlersFor, openWith, openNewFolder, navigateToSurface]);

  // Upload success (2026-07-01): after files land in the Intake raw lane
  // (inbound/uploads/{principal}/{slug}.{ext}, ADR-395), refresh the tree AND
  // take the operator to the new file — select the uploaded workspace path. The
  // tree auto-expands the Intake root (WorkspaceTree's nodeContainsPath effect)
  // and highlights the new node; the viewer opens it. The operator SEES the
  // result of the add, instead of the modal closing silently onto an unchanged-
  // looking tree. reload → then select so the fresh node exists when it resolves.
  const handleUploaded = useCallback(async (workspacePath: string) => {
    await loadExplorer();
    // Route through THE ONE DOOR (openPath) rather than a raw setSelectedPath.
    // An uploaded file lands in the Intake raw lane (inbound/uploads/…), which
    // isArtifactCandidate excludes — so an uploaded .html falls through to inline
    // preview here, correctly. If upload destinations ever change, the resolver
    // decides; the upload path can't reintroduce the blank-inline bug.
    openPath(workspacePath);
    activateBodyRef.current(); // narrow: drill into the viewer
  }, [loadExplorer, openPath]);

  // Finder-parity canvas verbs (2026-07-09). Right-click on empty canvas → the
  // background menu (New Folder / Add Files) — the gesture Finder's muscle memory
  // reaches for. We only open the menu on a right-click of the pane BACKGROUND,
  // not of a file tile/row (those carry their own <FileContextMenu>); the row
  // handlers call stopPropagation, so a background contextmenu means empty space.
  const openCanvasMenu = useCallback((e: React.MouseEvent) => {
    // ADR-452 D5 (Finder-flat): a tile/row's own context menu claims the event
    // (preventDefault in useFileContextMenu.openMenu); the bubbled copy must
    // NOT also open the canvas menu — that was the stacked-menus defect the
    // operator observed (the canvas box covering the file menu's Open/Properties).
    if (e.defaultPrevented) return;
    e.preventDefault();
    setCanvasMenu({ x: e.clientX, y: e.clientY });
  }, []);

  // ADR-555 D3 — where an arrival lands, in order: the folder the drop
  // happened on, else the folder the canvas is showing, else Documents (the
  // caller passes null and the server defaults). The same "the background of
  // an open folder acts on that folder" rule New Folder already follows —
  // arrival was the one act on this surface that ignored where you stood.
  const uploadDestinationFor = useCallback(
    (folder?: { path: string; name: string } | null) => {
      const node =
        folder ??
        (selectedNode?.type === 'folder' && selectedNode.path.startsWith('/workspace/')
          ? { path: selectedNode.path, name: selectedNode.name }
          : null);
      if (!node) return null;
      const rel = node.path.replace(/^\/workspace\//, '').replace(/\/+$/, '');
      if (!rel) return null;
      return { path: rel, label: node.name };
    },
    [selectedNode],
  );

  const openUpload = useCallback(
    (files?: File[], folder?: { path: string; name: string } | null) => {
      setDroppedFiles(files ?? null);
      setUploadDest(uploadDestinationFor(folder));
      setUploadOpen(true);
    },
    [uploadDestinationFor],
  );

  // Drag-drop onto the canvas = Finder's primary import gesture. A real file
  // drop opens the Add Files modal pre-seeded with the dropped files. We guard on
  // dataTransfer having files (an internal node drag carries none) so dragging a
  // tree node around never trips the uploader.
  const onCanvasDragOver = useCallback((e: React.DragEvent) => {
    if (!Array.from(e.dataTransfer.types || []).includes('Files')) return;
    e.preventDefault();
    setCanvasDragOver(true);
  }, []);
  const onCanvasDragLeave = useCallback((e: React.DragEvent) => {
    // Only clear when leaving the pane itself, not when crossing a child.
    if (e.currentTarget === e.target) setCanvasDragOver(false);
  }, []);
  const onCanvasDrop = useCallback((e: React.DragEvent) => {
    const files = Array.from(e.dataTransfer.files || []);
    if (files.length === 0) return;
    e.preventDefault();
    setCanvasDragOver(false);
    openUpload(files);
  }, [openUpload]);

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
      {/* Finder-parity (2026-07-09): the sidebar has no titled panel header and
          no visible New Folder / Add Files buttons — those verbs live in the
          canvas right-click menu (openCanvasMenu) + drag-drop, like Finder. A
          quiet uppercase group label heads the source list (Finder's "Favorites"
          / "Locations" pattern), nothing more. */}
      <div className="px-3 pt-3 pb-1 shrink-0 flex items-center justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
          Explorer
        </p>
        {/* Touch parity (2026-07-12): on a coarse pointer, the canvas verbs
            (right-click-only on desktop) get reachable buttons here. */}
        {coarse && (
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => openNewFolder(null)}
              aria-label="New folder"
              className="rounded p-1 text-muted-foreground hover:bg-accent/60 hover:text-foreground"
            >
              <FolderPlus className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => openUpload()}
              aria-label="Add files"
              className="rounded p-1 text-muted-foreground hover:bg-accent/60 hover:text-foreground"
            >
              <Upload className="h-4 w-4" />
            </button>
          </div>
        )}
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
              // ADR-514 D2.6: the WHOLE bundle — the same verbs the grid and the
              // folder listing get. The tree previously took a hand-listed
              // subset, which is how Duplicate (and Share…) went missing here.
              verbs={fileVerbs}
              onMoveByDrag={commitMove}
              // ADR-555 D3 — an OS file dropped on a folder row imports THERE.
              onDropFiles={(files, folder) => openUpload(files, folder)}
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
            {/* ADR-388 D4: the ONE shared Files view toggle (folder listings honor
                it; same control + memory as the Recents toggle — Finder-parity
                2026-07-09). */}
            {selectedNode.type === 'folder' && (
              <FilesViewToggle mode={viewMode} onChange={setViewMode} />
            )}
            {/* ADR-553 D3 — the set SAYS ITSELF and shows its exit.
                ADR-519 shipped an inescapable multi-selection once; a visible
                count with a visible Clear is the difference between a state a
                member chose and a state they are stuck in. The count names the
                SET (ADR-519 D4.1: "the Identity heading names the count, never
                a stale label"). */}
            {selectionSet.length > 1 && (
              <div className="inline-flex items-center gap-1.5 rounded-md border border-primary/40 bg-primary/10 px-2.5 py-1.5 text-xs">
                <span className="font-medium text-foreground">
                  {selectionSet.length} selected
                </span>
                <button
                  onClick={() => setMoveSetOpen(true)}
                  className="rounded px-1.5 py-0.5 text-primary transition-colors hover:bg-primary/15"
                >
                  Move…
                </button>
                <button
                  onClick={clearSet}
                  title="Clear selection (Esc)"
                  className="rounded px-1.5 py-0.5 text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
                >
                  Clear
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
            // ADR-552 — the folder listing drags. ADR-400 deferred this ("grid
            // drag-drop remains a later fast-follow"); the listing is where
            // files are actually looked at, so drag lived only in the tree.
            // The SAME handlers the tree uses — one move path, one import path.
            dnd={{
              canOrganize: operatorCanOrganize,
              dropTarget: listingDropTarget,
              setDropTarget: setListingDropTarget,
              onDropPath: commitMove,
              onDropFiles: (files, folder) => openUpload(files, folder),
            }}
            onOpenChatDraft={(prompt) => sendMessage(prompt, { surface: effectiveSurface })}
            onDeleted={() => {
              // ADR-329: file archived — clear selection + refresh the
              // tree (the archived file self-filters out server-side).
              // D19.2: selection is component state, never a URL write.
              setSelectedPath(null);
              setInlineApp(null);
              loadExplorer();
            }}
            // ADR-570: the Open With choice for the open file; the mismatch
            // guard makes a stale choice inert when selection moves on.
            appId={inlineApp && inlineApp.path === selectedNode.path ? inlineApp.appId : null}
            onAppDone={() => setInlineApp(null)}
          />
        )}
      </div>
    </div>
  ) : (
    // ADR-329 Amendment 2: the center pane's empty state IS the Finder
    // "Recents" view — a columnar glance of recent authored changes across the
    // workspace. Selecting a row swaps to the node view.
    <div className="flex-1 min-h-0">
      <RecentRevisions onSelectPath={openPath} verbs={fileVerbs} />
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
        {/* Finder-parity (2026-07-09): the body IS the canvas — right-click its
            background for New Folder / Add Files, and drop files onto it to
            import. A drop highlight rings the pane while dragging files over it.
            Row/tile right-clicks stopPropagation, so these only fire on empty
            space (the Finder contract). */}
        <div
          className={cn(
            'flex-1 min-w-0 min-h-0 flex flex-col overflow-y-auto bg-background transition-shadow',
            canvasDragOver && 'ring-2 ring-inset ring-primary/50',
          )}
          onContextMenu={openCanvasMenu}
          onDragOver={onCanvasDragOver}
          onDragLeave={onCanvasDragLeave}
          onDrop={onCanvasDrop}
        >
          {bodyContent}
        </div>
      </SettingsPaneShell>

      {/* Finder-parity canvas menu — the background right-click on the center
          pane. Carries the two canvas verbs (New Folder / Add Files) that used to
          be header buttons. */}
      {canvasMenu && (
        <CanvasContextMenu
          x={canvasMenu.x}
          y={canvasMenu.y}
          onClose={() => setCanvasMenu(null)}
          // Finder folder-window grammar: the background of an open REAL folder
          // creates inside that folder. Recents / a virtual /explorer/ group /
          // an open file keep the top-level peer act (there is no honest
          // "here" to create into).
          onNewFolder={() =>
            openNewFolder(
              selectedNode?.type === 'folder' && selectedNode.path.startsWith('/workspace/')
                ? { path: selectedNode.path, name: selectedNode.name }
                : null,
            )
          }
          onAddFiles={() => openUpload()}
        />
      )}

      {/* The Add Files modal, summoned from the canvas menu or a drag-drop.
          `initialFiles` pre-seeds the batch when the operator dropped files onto
          the canvas. */}
      {uploadOpen && (
        <UploadModal
          destination={uploadDest}
          onClose={() => { setUploadOpen(false); setDroppedFiles(null); setUploadDest(null); }}
          onUploaded={handleUploaded}
          initialFiles={droppedFiles ?? undefined}
        />
      )}

      {/* ADR-400: Properties modal — the flat Kind/Location/Ownership/Modified/
          Contributors block + the ADR-209 revision history. Opened by the header
          button or a right-click on any tree/folder-listing node. */}
      <PropertiesModal
        node={detailsOpen ? selectedNode : null}
        onClose={() => setDetailsOpen(false)}
        onSelectPath={openPath}
        onRevert={loadExplorer}
      />

      {/* ADR-400 Q2 / ADR-446: the Move-picker + Rename modals — now owned by the
          shared useFileOrganizeVerbs hook (one implementation across Files +
          Studio). Files feeds the hook its own `treeNodes` for the picker. */}
      {organizeModals}

      {/* ADR-424 D2: New Folder — top-level peer, or inside the folder the act
          was scoped to (destination stated in the modal, never silent). */}
      {/* ADR-553 D2 — the SET's Move, through the SAME picker a single Move
          uses. `target` names the set honestly ("3 files") rather than
          borrowing one member's name, which would be the stale-label failure
          ADR-519 D4.1 names. */}
      <MoveToFolderModal
        target={moveSetOpen ? { path: selectionSet[0] ?? '', name: `${selectionSet.length} files` } : null}
        roots={treeNodes}
        canOrganize={operatorCanOrganize}
        onClose={() => setMoveSetOpen(false)}
        onMove={async (destFolder) => {
          const paths = selectionSet;
          setMoveSetOpen(false);
          const { moved, failed } = await organizeVerbs.commitMoveMany(paths, destFolder);
          clearSet();
          // Non-transactional by construction — say which half landed rather
          // than reporting a flat success over a partial move.
          if (failed.length) {
            toast({
              kind: 'error',
              message: moved.length
                ? `Moved ${moved.length} of ${paths.length}. ${failed.length} could not be moved.`
                : `Could not move ${failed.length} file${failed.length === 1 ? '' : 's'}.`,
            });
          } else {
            toast({
              kind: 'success',
              message: `Moved ${moved.length} file${moved.length === 1 ? '' : 's'}.`,
            });
          }
        }}
      />

      <NewFolderModal
        open={newFolderOpen}
        onClose={closeNewFolder}
        onSubmit={commitNewFolder}
        destinationName={newFolderParent?.name}
      />

      {/* ADR-529 D1: the ONE share act. Reached from every file surface through
          the FileVerbs bundle (tree, grid, listing) — and Studio mounts the
          same component, so the act is identical wherever it is invoked. */}
      <ShareDialog target={shareTarget} onClose={() => setShareTarget(null)} />

    </>
  );
}
