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
 * write the URL, because selection is component state. Writing `/files?files.path=…`
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
import { NewFolderModal } from '@/components/workspace/NewFolderModal';
import { MoveToFolderModal } from '@/components/workspace/MoveToFolderModal';
import { ShareDialog } from '@/components/workspace/ShareDialog';
import { cn } from '@/lib/utils';
import { formatAuthorLabel } from '@/lib/workspace/attribution';
import { toWorkspacePath, relPath } from '@/lib/interop/fileHandle';
import { CopyField } from '@/components/workspace/CopyField';
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
type FileClickIntent = import('@/types').FileClickIntent;

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
//
// ADR-587 D9 — the HISTORY half of the strip: when it last changed and who
// changed it. Two facts, one clause. What this deliberately no longer says:
//
//   · "File" / "Folder" — the kind is already the glyph beside the title, the
//     extension in the name, and the `Kind` row in Properties. A word that
//     labels something three other things already say is noise.
//   · `node.summary` — the stored summary is a WRITER'S MARKER, not a
//     description. `_plain_summary` (routes/workspace.py) drops the obvious
//     machine shapes, but tags with no slash and no extension slip through
//     it — the operator hit `connector-watch:github` on a `_watch.yaml`,
//     which is a legacy tag from machinery ADR-582 has since deleted. A field
//     the operator never wrote, describing a mechanism that no longer exists,
//     is not identity.
//
// A folder keeps its item count: that is the one fact a folder's identity
// line carries that nothing else on the screen states.
function getNodeMetadata(node: TreeNode): string {
  const parts: string[] = [];

  if (node.type === 'folder') {
    const childCount = node.children?.length;
    if (typeof childCount === 'number') {
      parts.push(`${childCount} ${childCount === 1 ? 'item' : 'items'}`);
    }
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

/**
 * The header's metadata strip — ADR-587 D8.
 *
 * The FOURTH face of the D7 rule, and the one the operator is standing IN.
 * The children of a folder showed their paths (D7's grid tile + list row)
 * while the folder itself said only "Folder · 3 items · Updated…" — and the
 * breadcrumb above it reads "Files › _connectors", which DROPS the
 * `operation/` prefix. So the one object whose identity the screen is
 * devoted to was the one object the screen would not name.
 *
 * Inline variant, not boxed: this is a metadata strip under an h1, and a
 * bordered input here would out-weigh the title it describes. Same component,
 * same clipboard fallback — presentation differs, mechanism does not.
 */
function nodeMetadataNode(node: TreeNode): React.ReactNode {
  const history = getNodeMetadata(node);
  return (
    // ADR-587 D9: two lines, because they answer two questions. WHERE this
    // object is (its path — the identity D7/D8 established, and the one part
    // of this strip the operator takes AWAY with them) sits above WHEN it
    // last changed and WHO changed it. Run together on one dot-separated run
    // they read as one undifferentiated fact-list, and the copyable half is
    // the hardest to pick out of it — which is the opposite of what a copy
    // affordance is for.
    <span className="flex min-w-0 flex-col gap-0.5">
      <CopyField variant="inline" value={relPath(node.path)} label="path" />
      {history && <span className="truncate">{history}</span>}
    </span>
  );
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
  // its live view through internal `viewPath` state and deliberately
  // does NOT write back to the URL (see the click handlers).
  const fp = useSurfaceParam('files');
  // ADR-451: the Finder routes surface-owned formats to their app.
  const { navigateToSurface } = useSurfacePreferences();
  const domainParam = fp.get('domain');
  const pathParam = fp.get('path');

  const [treeNodes, setTreeNodes] = useState<TreeNode[]>([]);

  // ── THE TWO STATES: what you are LOOKING AT vs what you have PICKED ────
  //
  // 2026-08-20. Until this commit ONE piece of state (`selectedPath`) meant
  // both "the highlighted item" and "the document the center pane renders".
  // That inversion was the whole defect: because naming a file rendered its
  // body, a plain click could not be inert — and a click that always goes
  // somewhere is not a selection at all. Without selection there is no
  // multi-select, no shift-range, no bulk verb, no drag-a-group; the entire
  // file-operation vocabulary was unreachable through the surface.
  //
  //   viewPath   — WHAT THE CENTER PANE RENDERS. A folder (its listing), a
  //                file whose body was OPENED, or null (the Recents view).
  //                Only an OPEN (openPath) moves this. A selection never does.
  //   selection  — WHAT IS PICKED. A SET, first-class, in the listing's visual
  //                order. Clicking replaces it; ⌘/Ctrl-click toggles a member;
  //                shift-click takes the range from the anchor. The verbs act
  //                on it. It renders as a highlight and NOTHING ELSE.
  //
  // This DELETES the prior `selectedPath` + `alsoSelected` + `selectionSet`
  // shape (ADR-553's "a SET carried BESIDE the selection, never replacing it").
  // There is no primary any more, so there is nothing to carry a set beside.
  // ADR-553 D1 further carved ⌘-click as the ONLY way into a multi-selection,
  // reasoning that a member must not enter one by accident — but that reasoning
  // only held because a plain click was DESTRUCTIVE (it navigated the surface
  // into an app). A plain click is now inert, so plain-click-to-select is safe,
  // expected, and the way every file browser works. That carve is withdrawn.
  const [viewPath, setViewPath] = useState<string | null>(null);
  const [selection, setSelection] = useState<string[]>([]);
  // The shift-range anchor — the last item picked by a plain or ⌘ click. A
  // range is taken FROM it, and taking one does not move it (so successive
  // shift-clicks re-range from the same origin, the Finder/Explorer rule).
  const [anchorPath, setAnchorPath] = useState<string | null>(null);
  // The listing's current visual order, published by whichever pane rendered
  // it. A range is over WHAT THE MEMBER SEES — sorted, filtered, folders-first
  // — not over any underlying tree order, so the highlight always matches the
  // rectangle the gesture drew.
  const orderRef = useRef<string[]>([]);
  const publishOrder = useCallback((paths: string[]) => { orderRef.current = paths; }, []);
  const clearSelection = useCallback(() => { setSelection([]); setAnchorPath(null); }, []);

  // ADR-400 D4: the Trash nav item toggles the center pane to the Trash view.
  const [showTrash, setShowTrash] = useState(false);
  const [fileTreeLoading, setFileTreeLoading] = useState(false);
  const [phase, setPhase] = useState<'setup' | 'ready' | 'active' | null>(null);

  // ADR-329 (amended): node Details ("Get Info") — provenance as a per-node
  // property, opened on demand (header ⓘ toggle or tree right-click), not a
  // standing left-rail feed. Tied to the current selection; collapses to a
  // header section above the content.
  const [detailsOpen, setDetailsOpen] = useState(false);
  // WHICH node Properties describes. Its own state, because the selection is a
  // SET and the shown object is a FOLDER: neither one alone answers "get info
  // on this". Null = fall back to the single selected item, else the shown
  // object — so the header's Properties button still describes what you are
  // standing in when nothing is picked.
  const [propertiesPath, setPropertiesPath] = useState<string | null>(null);

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

  // The set-taking Move (ADR-553 D2) — now fed by `selection` directly.
  //
  // ADR-519 shipped a PROD TRAP here once — a multi-selection with no way out.
  // Withdrawal is part of the feature, not a follow-up: Escape clears, a
  // background click clears, and any single-target verb clears before it acts.
  const [moveSetOpen, setMoveSetOpen] = useState(false);
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

      // Preserve what's on screen if it still exists. The SELECTION is left
      // alone deliberately: a listing row is not always a tree node (a synthetic
      // entity subfolder, a lazily-unloaded branch), so pruning against the tree
      // on every 30s refetch would silently drop a legitimate pick out from
      // under a member who is lining up a bulk verb.
      setViewPath((prev) => {
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

  // viewNode — the object the center pane is SHOWING (not the one that is
  // picked). Prefer the tree-resolved node (its children are populated), fall
  // back to a synthetic node for direct workspace paths that aren't in the
  // virtual tree (e.g. entity subfolders navigated from TrackingEntityGrid).
  const viewNode = viewPath
    ? (resolveNodeByPath(virtualRoot, viewPath) ?? syntheticNodeForPath(viewPath))
    : null;

  // The node Properties describes: the explicit Get-Info target, else the one
  // selected item, else what is on screen. Three fallbacks, one direction —
  // most specific first.
  const propertiesTarget =
    propertiesPath ?? (selection.length === 1 ? selection[0] : null) ?? viewPath;
  const propertiesNode = propertiesTarget
    ? (resolveNodeByPath(virtualRoot, propertiesTarget) ?? syntheticNodeForPath(propertiesTarget))
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
    viewNode
      ? [{
          label: viewNode.name,
          kind: 'context',
          onClick: () => { setViewPath(null); clearSelection(); drillOutRef.current(); },
        }]
      : []
  );

  // ADR-297 Phase 3: surface context for chat drafts derives from this
  // surface's own identity (Files), not the deleted DeskContext. When a
  // node is selected, overlay the explorer path so the agent knows what
  // the operator is looking at.
  // A single PICKED file is the sharpest statement of "what the operator is
  // looking at" — sharper than the folder they are standing in. So one
  // selected item scopes the chat draft; otherwise the shown object does
  // (and with nothing shown, the bare surface).
  const focusNode =
    selection.length === 1
      ? (resolveNodeByPath(virtualRoot, selection[0]) ?? syntheticNodeForPath(selection[0]))
      : viewNode;
  const effectiveSurface: DeskSurface = focusNode
    ? { type: 'workspace-explorer', path: focusNode.path, navigation_type: focusNode.type }
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
  // re-fired: param stranded in the URL, `viewPath` null, Recents.
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
      // ADR-587: the arrival door is where a name from OUTSIDE enters, so it
      // is where the ADR-512 D5 grammar is applied. A deep-link may carry any
      // of the three honest spellings — the canonical `yarnnn://workspace/…`
      // handle an external AI was given, the ledger's absolute form, or a bare
      // relative path — and before this, only the absolute form resolved:
      // `openPath` matches `workspace_files.path` verbatim, so a handle or a
      // bare path fell through to an empty selection. The app emitted a name
      // it could not read back.
      //
      // A refusal (another scheme, `..`) opens nothing rather than guessing.
      const arrival = toWorkspacePath(pathParam);
      if (arrival) openPathRef.current(arrival);
    } else if (domainParam) {
      // ADR-388 D1: domains nest under the literal operation/ root.
      openPathRef.current(`/workspace/operation/${domainParam}`);
    }
    // Drain — the param has done its one job. `viewPath` is what the surface
    // shows from here on; the URL is not the source of truth once open.
    //
    // ARRIVING AT A PATH IS AN OPEN, NOT A SELECT. A deep-link is someone
    // handing you a document, so it goes through the ONE open door and lands
    // rendered — the select/open split below governs in-surface GESTURES only.
    fp.set({ path: null, domain: null });
    // fp.set stable; keyed on the param values so a new jump re-fires but a
    // tree refetch does not. eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathParam, domainParam]);

  // ADR-297 D19.2: in-surface selection is component state, NOT a URL write.
  // The Files surface runs as a window on the Desktop (pathname `/desktop`);
  // writing `/files?files.path=…` on every click flipped pathname → /files, which
  // tripped AuthenticatedLayout's pathname→foreground effect + SurfaceViewport's
  // pathnameSlug resolution, disrupting the launcher/topbar (operator-observed
  // KVK 2026-06-12). `?path=` survives only as an inbound ARRIVAL param
  // (opened + drained above) — it is never written from intra-surface clicks.
  // Path-based open — a path string, not a TreeNode. The file may not be in
  // the visible tree (e.g. a folder-Details revision row deep-links into a
  // `_`-prefixed file hidden from the explorer); syntheticNodeForPath resolves
  // the viewer.
  //
  // ── openPath — THE ONE DOOR that opens a workspace path ────────────────
  //
  // 2026-07-24 (Option A cleanup). Every way a member opens a file in the Files
  // surface routes through here — the tree double-click, the folder-listing
  // double-click, the single tap on a touch device, Enter on the selection, the
  // right-click Open verb, a Recents click, a cold-load / post-mount deep-link
  // (`?files.path=`), and a just-uploaded file. There is deliberately no second
  // path that calls `setViewPath` for a FILE: a new door consults the app layer
  // by calling this, and physically cannot bypass it (a bare setViewPath for an
  // artifact is the regression the gate forbids).
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
  // `showInline` is the terminal for an unclaimed path — the ONLY sanctioned
  // setViewPath-for-a-file site (nested so it can't be called from outside).
  //
  // Since the select/open split there is no longer any "select-to-inspect"
  // carve to allowlist: Get Info / Properties SELECT (they scope the details
  // modal) and no longer touch what the center pane renders at all. The two
  // states are now genuinely separate, so the funnel owns `setViewPath` for a
  // file outright.
  const openPath = useCallback((path: string) => {
    const showInline = (isFolder: boolean) => {
      setShowTrash(false);
      setViewPath(path);
      // Opening a FILE also PICKS it — the OS rule: whatever you just launched
      // is the highlighted item. Opening a FOLDER is NAVIGATION, so it clears:
      // you have arrived somewhere new and nothing in the new listing is
      // picked yet. Carrying the parent folder's own path into the child view
      // as "selected" would make the very first bulk verb act on the wrong
      // object.
      if (isFolder) {
        clearSelection();
      } else {
        setSelection([path]);
        setAnchorPath(path);
      }
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
    // A non-candidate path (folder, image, arrival) never routes to an app —
    // isArtifactCandidate is a cheap path-only pre-check, so we don't read
    // content for the 500-row tree, only for a file that might route. Since
    // ADR-571 it admits PROSE too (the Text app claims .md by extension), so
    // a document reaches the surface claim below without a content read.
    if (!isArtifactCandidate(path)) {
      // `isArtifactCandidate` is path-only, so a folder (no extension) is
      // exactly the non-candidate case; ask the resolver rather than re-deriving.
      showInline(!/\.[a-z0-9]+$/i.test(path.split('/').filter(Boolean).pop() ?? ''));
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
      showInline(false);
    })();
  }, [navigateToSurface, clearSelection]);
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
      // An inline-handler Open With — the same act openPath's terminal performs.
      setShowTrash(false);
      setViewPath(t.path);
      setSelection([t.path]);
      setAnchorPath(t.path);
      activateBodyRef.current();
    },
    [navigateToSurface],
  );

  // Mirror into the ref so the earlier loadExplorer + post-mount effect route
  // deep-links through this exact funnel (see openPathRef declaration).
  openPathRef.current = openPath;

  // ── TWO PANES, TWO GRAMMARS ────────────────────────────────────────────
  //
  //   LEFT TREE (WorkspaceTree)  a NAVIGATOR — the folder hierarchy you move
  //                              THROUGH. FOLDERS ONLY. One click navigates the
  //                              centre pane there and unfolds the branch. No
  //                              selection, no multi-select, no open. It cannot
  //                              open a file at all, because it holds none.
  //
  //   CENTRE PANE (ContentViewer) a FILE BROWSER — the contents of the folder
  //                              you are standing in. The grammar below.
  //
  // Explorer and Finder both show folders only in the left tree, so "does
  // clicking a file there open it?" never arises. The first cut of the split
  // (2026-08-20, morning) applied ONE grammar to both panes and the selection
  // model bled into the navigator: clicking a FILE in the tree raised the
  // floating Move…/Open/Clear chip beside Properties (operator-observed).
  //
  // ── SELECT ≠ OPEN — the CENTRE PANE's file-browser grammar ─────────────
  //
  // In every conventional OS a file browser's grid has a selection model:
  //
  //   single click            SELECT — highlight it. Nothing else happens.
  //                           A single click must be able to lead NOWHERE.
  //   ⌘/Ctrl-click            toggle one member in or out of the set
  //   shift-click             take the RANGE from the anchor, in the listing's
  //                           current visual order
  //   double click            OPEN — the one gesture that leads somewhere
  //   Enter                   OPEN the selection (double-click's keyboard peer)
  //   Escape / background     clear the selection
  //
  // Why the inert click is load-bearing and not a nicety: if every single click
  // goes somewhere, there is no selection state at all — and with no selection
  // there is no multi-select, no shift-range, no bulk verb, no drag-a-group.
  // The whole vocabulary of file operations is unreachable through the surface.
  // Selection is the NOUN the verbs act on; it has to exist before they can.
  //
  // What the pane shows while you select: THE FOLDER LISTING, unchanged. The
  // item highlights and the view does not move. Metadata for a picked file
  // lives in Properties (which the selection SCOPES rather than replaces), and
  // reading content is what OPEN is for — Files is a browser, and a .md opens
  // in Text, a .html in Studio. A bounded in-pane preview (Quick Look) is
  // deliberately NOT built here; half of one would be worse than none.
  //
  // COARSE POINTER (touch) KEEPS ITS SINGLE-TAP OPEN. The branch is on input
  // CAPABILITY (`useCoarsePointer`, `(pointer: coarse)`), never viewport width —
  // a narrow desktop window still has a mouse; a large tablet does not. Double-
  // tap is not a touch idiom: it fires unreliably, competes with double-tap-to-
  // zoom, and is undiscoverable. Every touch OS opens on a single tap, so touch
  // gets no selection grammar and no new action model — the same shape the
  // kebab (⋯) parity took.
  //
  // FOLDERS IN THE LISTING take the DOUBLE-CLICK, exactly like a file: the
  // listing is a grid of peers, and a member drawing a selection across it must
  // be able to include a folder in the rectangle without being navigated away
  // mid-gesture. (In the TREE a folder is single-click — see navigateToFolder.
  // A tree that demanded a double-click to expand a branch reads as broken.)
  //
  // THE VERBS LIVE IN THE RIGHT-CLICK MENU, not in a toolbar the selection
  // raises. That is where every OS puts them, and the shared FileContextMenu
  // already carried the whole bundle.
  //
  // THE ONE DOOR is intact: every branch below that OPENS calls `openPath`.

  // Replace the selection with exactly this path (a plain click, and the pick
  // that rides along with an open).
  const selectOne = useCallback((path: string) => {
    setSelection([path]);
    setAnchorPath(path);
  }, []);

  // ⌘/Ctrl-click — toggle one member. Removing the anchor moves it to whatever
  // is still picked, so a following shift-click ranges from something real.
  //
  // Computed from the CURRENT selection rather than inside a setState updater:
  // an updater must be pure (React may invoke it twice), and this one has to
  // move the anchor as well as the set.
  const toggleSelected = useCallback((path: string) => {
    const next = selection.includes(path)
      ? selection.filter((p) => p !== path)
      : [...selection, path];
    setSelection(next);
    setAnchorPath(next.includes(path) ? path : (next[next.length - 1] ?? null));
  }, [selection]);

  // Shift-click — the RANGE, over the listing's published visual order. With no
  // anchor (or a row the current listing doesn't contain — a tree node, a stale
  // pick) it degrades to a plain single select rather than doing nothing.
  const selectRange = useCallback((path: string) => {
    const order = orderRef.current;
    const to = order.indexOf(path);
    const from = anchorPath ? order.indexOf(anchorPath) : -1;
    if (to === -1 || from === -1) {
      selectOne(path);
      return;
    }
    const [lo, hi] = from <= to ? [from, to] : [to, from];
    // The anchor deliberately does NOT move: successive shift-clicks re-range
    // from the same origin, which is what makes a range correctable.
    setSelection(order.slice(lo, hi + 1));
  }, [anchorPath, selectOne]);

  // THE CENTRE PANE's click grammar. It belongs to the LISTING alone — the
  // tree is a navigator and has its own single-meaning gesture below.
  //
  // The first cut of the split routed both panes through this one function with
  // a `source: 'tree' | 'listing'` discriminator. That parameter was the error
  // made concrete: a function that has to be told which pane called it is two
  // functions wearing one name, and the shared half (the selection) then bled
  // into the pane that has nothing to select.
  const handleFileClick = useCallback(
    (node: TreeNode, e?: FileClickIntent) => {
      if (e?.shiftKey) {
        selectRange(node.path);
        return;
      }
      if (e?.metaKey || e?.ctrlKey) {
        toggleSelected(node.path);
        return;
      }
      // A double-click arrives as a second click event with detail >= 2 — the
      // browser's own counter. No timer of ours, so a slow double-click the
      // browser scored as two singles just selects twice, and a micro-drag
      // between the presses never becomes a spurious open.
      const isDoubleClick = (e?.detail ?? 0) >= 2;
      if (coarse || isDoubleClick) {
        openPath(node.path);
        return;
      }
      selectOne(node.path);
    },
    [openPath, coarse, selectOne, selectRange, toggleSelected],
  );
  const handleListingClick = handleFileClick;

  // THE TREE's gesture — one click, one meaning: show me this folder.
  //
  // It routes through `openPath` like every other way into a folder (THE ONE
  // DOOR), which also clears the selection: you have arrived somewhere new and
  // nothing in the new listing is picked yet. There is no file branch, because
  // there are no files in the tree — the centre pane is the only route to a
  // document, and that is the point of the two-pane split.
  const navigateToFolder = useCallback((node: TreeNode) => { openPath(node.path); }, [openPath]);

  // Enter opens the selection — the keyboard equivalent double-click does not
  // have, and therefore the accessibility answer to the split above. With a
  // multi-selection it opens the anchor (the last thing actually pointed at),
  // because "open 12 files" is not an act this surface offers.
  // A bare key, ignored while the member is typing into a field or a
  // contentEditable (inline rename, the chat composer).
  useEffect(() => {
    if (selection.length === 0) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Enter' || e.metaKey || e.ctrlKey || e.altKey) return;
      const t = e.target as HTMLElement | null;
      if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
      e.preventDefault();
      openPathRef.current(
        anchorPath && selection.includes(anchorPath) ? anchorPath : selection[0],
      );
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [selection, anchorPath]);

  // ── The way OUT ────────────────────────────────────────────────────────
  // ADR-519 shipped an inescapable multi-selection once; withdrawal is part of
  // this feature, not a follow-up. Escape is the universal exit, at ANY size —
  // a selection of one is just as much a state a member needs out of as a
  // selection of nine (the earlier shape only armed Escape past size 1).
  useEffect(() => {
    if (selection.length === 0) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') clearSelection();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [selection.length, clearSelection]);

  // ADR-329 (amended): right-click "Get Info" on a tree node → select it (so
  // Details scopes to it) and open the Details panel.
  // A pure SELECT-to-inspect: it scopes the details modal to this node and
  // moves nothing else. It deliberately does NOT touch `viewPath` — inspecting
  // a file's properties is not reading its body, and before the select/open
  // split it did both at once.
  const handleGetInfo = useCallback((node: TreeNode) => {
    selectOne(node.path);
    setPropertiesPath(node.path);
    setDetailsOpen(true);
  }, [selectOne]);

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
      // A single-target verb ENDS the set. Otherwise a set built before a
      // rename/move/trash outlives it and points at paths that no longer
      // exist: the stale-state half of ADR-519's trap, arriving by a different
      // door than the one the Escape hatch guards.
      //
      // Rename/Move → the moved file becomes the selection at its NEW path, so
      // the member can see where it went. Trash (newPath null) → nothing is
      // picked.
      if (newPath === null) clearSelection(); else selectOne(newPath);
      // What is being SHOWN only moves if the mutated file was the thing on
      // screen. Renaming a file you merely picked must not yank the listing.
      setViewPath((prev) => (prev !== oldPath ? prev : newPath));
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
  // a folder marker (ADR-588 D1). The parent travels VERBATIM in its own field —
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
      // ADR-588 D1: STAY HERE. The folder is revealed + selected in the tree,
      // Finder/Explorer grammar — no OS opens an editor on `mkdir`. The route
      // used to return a seeded README and this line opened it, which since
      // ADR-571 routes .md to the Text app meant creating a folder EJECTED the
      // operator out of Files into an editor. Both the seed and the redirect
      // are gone; `path` is the folder itself.
      if (r?.path) selectOne(r.path);
    } catch { /* error toast already surfaced; keep the modal open to retry */ }
  }, [runAction, loadExplorer, selectOne, newFolderParent, closeNewFolder]);

  // Move (deliberate, modal) + drag-move (gesture) both route through the shared
  // hook — `openMove` opens the picker, `commitMove` is the drag fast-path.
  //
  // DRAG THE GROUP. Selection is only worth having if the verbs take it, and
  // dragging is the most direct verb on this surface. When the row a member
  // picked up is part of a multi-selection, the drop moves the WHOLE set —
  // otherwise a member who selected nine files and dragged one would watch the
  // other eight stay put, which reads as the selection being decorative. A
  // dragged row that is NOT in the selection moves alone (the OS rule: dragging
  // outside the selection is its own act).
  const commitMove = useCallback(
    async (fromPath: string, destFolder: string) => {
      if (selection.length > 1 && selection.includes(fromPath)) {
        const paths = selection;
        const { moved, failed } = await organizeVerbs.commitMoveMany(paths, destFolder);
        clearSelection();
        if (failed.length) {
          toast({
            kind: 'error',
            message: moved.length
              ? `Moved ${moved.length} of ${paths.length}. ${failed.length} could not be moved.`
              : `Could not move ${failed.length} file${failed.length === 1 ? '' : 's'}.`,
          });
        } else {
          toast({ kind: 'success', message: `Moved ${moved.length} files.` });
        }
        return;
      }
      await organizeVerbs.commitMove(fromPath, destFolder);
    },
    [selection, organizeVerbs, clearSelection, toast],
  );

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
    // SELECT-to-inspect, like handleGetInfo — it scopes the modal, it does not
    // open the file. When the target is already in a multi-selection the set is
    // left intact; Properties reads one node either way.
    onProperties: (t: { path: string }) => {
      setShowTrash(false);
      setSelection((prev) => (prev.includes(t.path) ? prev : [t.path]));
      setAnchorPath(t.path);
      setPropertiesPath(t.path);
      setDetailsOpen(true);
    },
    onRename: openRename,
    // MOVE — the verb the deleted selection chip used to carry.
    //
    // It takes the SET when the right-clicked file is part of a multi-selection,
    // and the single file otherwise. That is the OS rule (right-clicking inside
    // a selection acts on the selection; right-clicking outside it acts on the
    // row) and it is the whole reason a selection is worth having: verbs that
    // ignore the set make the highlight decorative.
    //
    // Right-clicking a row that is NOT in the selection first REPLACES the
    // selection with it — otherwise the menu would name one file and the verb
    // would move nine.
    onMove: (t: { path: string; name: string }) => {
      if (selection.length > 1 && selection.includes(t.path)) {
        setMoveSetOpen(true);
        return;
      }
      openMove(t);
    },
    onDelete: handleTreeDelete,
    onShare: handleShare,
    // DOWNLOAD — save to the operator's computer (2026-08-20). It left the
    // preview header (`FileActions`) for the right-click menu, the
    // cloud-provider convention (Dropbox / Drive / OneDrive) and where the
    // operator actually looks for it.
    //
    // Only a blob-backed file resolves: a folder and a text file (whose bytes
    // ARE its content, read through the API) return null and the entry does not
    // render. The filename comes from the PATH, never from the CAS href —
    // 1069fe3's fix, carried through the move.
    downloadFor: async (t: { path: string; name: string; isFile: boolean }) => {
      if (!t.isFile) return null;
      try {
        const file = await api.workspace.getFile(t.path);
        if (!file.content_url) return null;
        const r = await api.documents.blobUrl(file.content_url);
        return { href: r.url, filename: t.path.split('/').pop() || t.name };
      } catch {
        return null;
      }
    },
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
       handlersFor, openWith, openNewFolder, navigateToSurface, selection]);

  // Upload success (2026-07-01): after files land in the Intake raw lane
  // (inbound/uploads/{principal}/{slug}.{ext}, ADR-395), refresh the tree AND
  // take the operator to the new file — select the uploaded workspace path. The
  // tree auto-expands the Intake root (WorkspaceTree's nodeContainsPath effect)
  // and highlights the new node; the viewer opens it. The operator SEES the
  // result of the add, instead of the modal closing silently onto an unchanged-
  // looking tree. reload → then select so the fresh node exists when it resolves.
  const handleUploaded = useCallback(async (workspacePath: string) => {
    await loadExplorer();
    // Route through THE ONE DOOR (openPath) rather than a raw setViewPath.
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
        (viewNode?.type === 'folder' && viewNode.path.startsWith('/workspace/')
          ? { path: viewNode.path, name: viewNode.name }
          : null);
      if (!node) return null;
      const rel = node.path.replace(/^\/workspace\//, '').replace(/\/+$/, '');
      if (!rel) return null;
      return { path: rel, label: node.name };
    },
    [viewNode],
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
              onClick={() => { setShowTrash(false); setViewPath(null); clearSelection(); activateBodyRef.current(); }}
              aria-current={viewPath === null && !showTrash ? 'page' : undefined}
              className={cn(
                'w-full flex items-center gap-2 px-2 py-1.5 mb-1 rounded-md text-left text-sm transition-colors',
                viewPath === null && !showTrash
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
              onClick={() => { setShowTrash(true); setViewPath(null); clearSelection(); activateBodyRef.current(); }}
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
            {/* The NAVIGATOR. Folders only, and it takes no selection: the
                tree moves what the centre pane is SHOWING, and the centre pane
                owns picking. See WorkspaceTree's header for the two-pane
                grammar. */}
            <WorkspaceTree
              nodes={treeNodes}
              viewPath={viewPath || undefined}
              onNavigate={navigateToFolder}
              // ADR-514 D2.6: the WHOLE bundle — the same verbs the grid and the
              // folder listing get. The tree previously took a hand-listed
              // subset, which is how Duplicate (and Share…) went missing here.
              // Every target here is a folder, so the file-only entries
              // self-suppress.
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
  ) : viewNode ? (
    <div className="flex-1 overflow-auto bg-background flex flex-col min-h-0">
      <SurfaceIdentityHeader
        title={viewNode.name}
        metadata={nodeMetadataNode(viewNode)}
        actions={
          <div className="flex items-center gap-2">
            {/* ADR-388 D4: the ONE shared Files view toggle (folder listings honor
                it; same control + memory as the Recents toggle — Finder-parity
                2026-07-09). */}
            {viewNode.type === 'folder' && (
              <FilesViewToggle mode={viewMode} onChange={setViewMode} />
            )}
            {/* NO SELECTION TOOLBAR. A selection should LOOK selected; it
                does not need a chip announcing itself beside Properties.

                The floating Move…/Open/Clear strip that stood here is DELETED
                (2026-08-20, second cut). Its verbs moved to the RIGHT-CLICK
                CONTEXT MENU on centre-pane items, which is where every OS puts
                them — and where the shared FileContextMenu already carried
                Open / Open With / Rename / Move / Duplicate / Share / Delete /
                Properties, so the strip was a second, smaller, worse copy of a
                menu the surface already had.

                The chip also appeared for a TREE click, which is how the
                operator met it: right beside Properties, from a pane that
                should never have had a selection at all.

                Withdrawal is unaffected (the ADR-519 prod-trap lesson — a
                selection you cannot leave is the actual defect). Escape clears
                at any size, and a click on the listing's empty ground clears;
                both are gated. What is gone is the ANNOUNCEMENT, not the exit. */}
            {/* ADR-388 D5 / ADR-400: Properties → modal. Also reachable by
                right-click on any tree/row node. */}
            <button
              onClick={() => { setPropertiesPath(null); setDetailsOpen(true); }}
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
        {/^\/workspace\/reports\/[^/]+\/?$/.test(viewNode.path) ? (() => {
          // path = /workspace/operation/reports/{slug}  →  slug at index 3
          const taskSlug = viewNode.path.split('/')[3];
          return <DeliverableMiddle taskSlug={taskSlug} refreshKey={0} />;
        })() : (
          <ContentViewer
            node={viewNode}
            selection={selection}
            onPublishOrder={publishOrder}
            onNavigate={handleListingClick}
            onClearSelection={clearSelection}
            onSelectRow={selectOne}
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
              setViewPath(null);
              clearSelection();
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
              viewNode?.type === 'folder' && viewNode.path.startsWith('/workspace/')
                ? { path: viewNode.path, name: viewNode.name }
                : null,
            )
          }
          onAddFiles={() => openUpload()}
          // The VISIBLE way out of a selection, now that the chip is gone. The
          // Finder background menu is where "Deselect All" lives; Escape and a
          // background click are the other two exits, and all three are gated.
          onDeselect={clearSelection}
          selectionCount={selection.length}
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
        node={detailsOpen ? propertiesNode : null}
        onClose={() => { setDetailsOpen(false); setPropertiesPath(null); }}
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
        target={moveSetOpen ? { path: selection[0] ?? '', name: `${selection.length} files` } : null}
        roots={treeNodes}
        canOrganize={operatorCanOrganize}
        onClose={() => setMoveSetOpen(false)}
        onMove={async (destFolder) => {
          const paths = selection;
          setMoveSetOpen(false);
          const { moved, failed } = await organizeVerbs.commitMoveMany(paths, destFolder);
          clearSelection();
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
