/**
 * File-tree root icons — resolves the lucide icon NAME the backend supplies for
 * each workspace root (`WORKSPACE_ROOTS[*].icon` in api/services/workspace_paths.py,
 * ADR-388 D1) to a rendered glyph (ADR-422 D3).
 *
 * This is a DIFFERENT namespace from surface-icons.tsx (which maps kernel
 * *surface* icon_keys from kernel_surfaces.py). Keeping them separate avoids
 * cross-contaminating two registries that happen to share a few names — the
 * kernel names the glyph, the FE maps it, per registry.
 *
 * Before ADR-422, buildRootNodes DROPPED root.icon and WorkspaceTree hardcoded
 * root glyphs by path string — so constitution/governance/contract/inbound fell
 * to a generic folder. This registry lets the backend own the glyph. An UNKNOWN
 * icon name falls back to the generic folder, so a re-founding root the FE has
 * never heard of still renders (ADR-388 §6 forward-compat).
 */

import type { LucideIcon } from 'lucide-react';
import {
  ArrowDownToLine,
  Bot,
  Brain,
  FileClock,
  FileCog,
  FileSignature,
  Folder,
  FolderCog,
  ScrollText,
  Settings,
  Shield,
  Upload,
  Users,
} from 'lucide-react';

// Mirrors the `icon` keys assigned in api/services/workspace_paths.py::WORKSPACE_ROOTS.
const ROOT_ICON_REGISTRY: Record<string, LucideIcon> = {
  'scroll-text': ScrollText, // constitution
  shield: Shield, // governance
  'file-signature': FileSignature, // contract
  brain: Brain, // persona
  'folder-cog': FolderCog, // operation
  settings: Settings, // system
  users: Users, // agents
  'arrow-down-to-line': ArrowDownToLine, // inbound / Intake
  upload: Upload, // uploads
  'file-clock': FileClock, // working
  // ADR-457 P3 display fold: a loose machine FILE at the workspace root
  // (_captures.yaml, _workspace_guide.md, …) is emitted by the Files page with
  // `icon_name: 'file-cog'`. It had no row here, so it resolved to the generic
  // FOLDER glyph — a file drawn as a folder, in the one disclosure where the
  // distinction matters. Registered 2026-09-04 (ADR-641).
  'file-cog': FileCog,
  bot: Bot, // (compat — legacy path-string glyph for agent-ish roots)
  folder: Folder, // generic
};

/**
 * Resolve a backend root icon name to a lucide component. Unknown names → the
 * generic folder glyph (forward-compatible with re-founding roots).
 */
export function resolveRootIcon(iconName: string | null | undefined): LucideIcon {
  if (!iconName) return Folder;
  return ROOT_ICON_REGISTRY[iconName] ?? Folder;
}

/**
 * The root ACCENT — a hue per workspace root, ADR-641.
 *
 * WHY THIS EXISTS. Before ADR-641 the tree had the colour exactly backwards:
 * the CANONICAL backend-named roots (`node.icon_name`, ADR-422 D3) rendered
 * `text-muted-foreground`, while the DEPRECATED path-string guesses beneath
 * them carried a full hue ladder (sky/orange/emerald/rose/purple/blue). So a
 * root got its correct glyph and lost its colour, and the only colourful rows
 * in the spine were the ones resolved by the fallback the registry exists to
 * replace. Moving the hues up here is what lets that ladder be DELETED.
 *
 * Keyed by ICON NAME rather than by root slug. Unlike a surface `icon_key`
 * (shared: `bell` dresses two surfaces), a root's icon is 1:1 with its root —
 * `WORKSPACE_ROOTS` gives each of the eleven a distinct glyph — so the icon
 * name IS the identity here, and a second key would be ceremony.
 *
 * Hues follow the roots' own `group` (workspace_paths.py), because that is
 * the distinction a member reads down the spine:
 *   work    → the member's own material (teal, matching `authorAccent`)
 *   arrival → what came from outside (amber, matching the `mcp` accent)
 *   system  → kernel residue, deliberately quiet
 * An unmapped icon degrades to the neutral tone, so a re-founding root
 * (ADR-388 §6) renders exactly as it does today.
 */
const ROOT_ACCENTS: Record<string, string> = {
  // group: work — Documents. The member's own authored substrate, and the row
  // they are here for. Teal matches `authorAccent`'s `member`.
  'folder-cog': 'text-teal-600',
  // group: arrival — Downloads. What ARRIVED rather than what was authored.
  //
  // NOT amber, though `authorAccent` gives an external (mcp) WRITE that hue:
  // amber is reserved in the shell chrome for ATTENTION (the AttentionCenter
  // rows), and a Downloads folder is not a thing that wants you — it is a
  // resting place. An arrival root wearing the alert colour would make every
  // workspace look like it had unread work. Cyan keeps it distinct from the
  // teal of authored work while staying quiet, and matches `authorAccent`'s
  // `platform` (things from outside).
  'arrow-down-to-line': 'text-cyan-600',
  upload: 'text-cyan-600',

  // group: system — DELIBERATELY UNCOLOURED, all of it.
  //
  // The first cut of this table gave each system root its own hue
  // (constitution sky, persona violet, agents violet, governance indigo…) and
  // the rendered spine was a rainbow: eleven saturated rows in a column, where
  // colour distinguished nothing because everything had it. Worse, the two
  // roots left neutral read as BROKEN rather than quiet — the odd ones out in
  // a coloured list.
  //
  // These roots live behind the collapsed "System files" disclosure. They are
  // kernel residue the member opens rarely and on purpose. Leaving them at the
  // neutral tone is what MAKES the two live zones above legible: Documents and
  // Downloads are the only colour in the spine, which is exactly the
  // distinction `WORKSPACE_ROOTS.group` draws.
  //
  // They are listed rather than omitted so `ROOT_ACCENTS` and
  // `ROOT_ICON_REGISTRY` cover the same keys — the gate asserts that, so a new
  // root cannot land with a glyph and no considered answer about its hue.
  shield: 'text-muted-foreground',
  'scroll-text': 'text-muted-foreground',
  'file-signature': 'text-muted-foreground',
  brain: 'text-muted-foreground',
  users: 'text-muted-foreground',
  settings: 'text-muted-foreground',
  'file-clock': 'text-muted-foreground',
  'file-cog': 'text-muted-foreground',
  bot: 'text-muted-foreground',
  folder: 'text-muted-foreground',
};

/**
 * The Tailwind text-color class for a backend-named root's glyph. An unknown
 * icon name → the neutral tone (forward-compatible with re-founding roots,
 * exactly as `resolveRootIcon` is).
 */
export function resolveRootAccent(iconName: string | null | undefined): string {
  if (!iconName) return 'text-muted-foreground';
  return ROOT_ACCENTS[iconName] ?? 'text-muted-foreground';
}
