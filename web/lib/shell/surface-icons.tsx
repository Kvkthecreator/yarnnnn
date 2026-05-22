/**
 * Surface icons — ADR-297.
 *
 * Maps the `icon_key` string from kernel_surfaces.py to a lucide-react
 * icon component. The string indirection keeps the backend declaration
 * pure (no React imports); the frontend resolves to a concrete component.
 *
 * If a surface declares an unknown icon_key, the resolver returns the
 * Box icon as a safe fallback so the launcher still renders.
 */

import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  ActivitySquare,
  Box,
  Clock,
  FolderOpen,
  Inbox,
  Link2,
  MessageCircle,
  Package,
  Palette,
  Scale,
  ScrollText,
  Settings,
  ShieldCheck,
  Target,
  UserCircle,
  Users,
} from 'lucide-react';

const ICON_REGISTRY: Record<string, LucideIcon> = {
  activity: Activity,
  clock: Clock,
  folder: FolderOpen,
  inbox: Inbox,
  // ADR-297 D19.5.2 (2026-05-22): layout-dashboard DELETED. Was only
  // mapped to Cockpit; swapped to square-activity to disambiguate
  // from Launcher's layout-grid glyph (both rendered as 4-square
  // shape at 16px). Singular Implementation — no orphan mappings.
  // ADR-297 D19.4 (2026-05-22): link-2 + settings registered for the
  // Connectors + Settings surfaces, promoted from pages to atomic
  // kernel surfaces (windowed inside the workspace, not page-shaped).
  'link-2': Link2,
  'message-circle': MessageCircle,
  package: Package,
  palette: Palette,
  scale: Scale,
  // ADR-297 D18.2 (2026-05-22): scroll-text registered for the Feed
  // surface, disambiguating it from the universal ChatDrawer FAB
  // (which is hardcoded MessageCircle in Desktop.tsx).
  'scroll-text': ScrollText,
  settings: Settings,
  'shield-check': ShieldCheck,
  // ADR-297 D19.5.2 (2026-05-22): Cockpit icon. Box-with-pulse-line
  // glyph (macOS Activity Monitor shape); distinct from layout-grid.
  // ActivitySquare is the older lucide name for the same glyph shipped
  // as SquareActivity in newer versions — pinned to ActivitySquare per
  // installed lucide-react version.
  'square-activity': ActivitySquare,
  target: Target,
  'user-circle': UserCircle,
  users: Users,
};

export function resolveSurfaceIcon(iconKey: string): LucideIcon {
  return ICON_REGISTRY[iconKey] ?? Box;
}
