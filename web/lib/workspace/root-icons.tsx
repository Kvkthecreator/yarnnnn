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
