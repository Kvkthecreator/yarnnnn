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
  Box,
  Clock,
  FolderKanban,
  FolderOpen,
  Gauge,
  Home,
  Inbox,
  Link2,
  MessageCircle,
  Package,
  Palette,
  Rocket,
  Rss,
  Scale,
  ScrollText,
  Settings,
  ShieldCheck,
  Target,
  User,
  UserCircle,
  Users,
  Wallet,
} from 'lucide-react';

const ICON_REGISTRY: Record<string, LucideIcon> = {
  activity: Activity,
  clock: Clock,
  folder: FolderOpen,
  // ADR-349 D4: the Workspace Settings (operation) door — distinct from the
  // System Settings gear so the two launcher doors read apart.
  'folder-kanban': FolderKanban,
  // ADR-297 D20 amendment (2026-05-25): gauge registered for the
  // /pace surface. Pre-fix the Dock + Launcher rendered Box as
  // fallback because `gauge` was missing — visible inconsistency
  // between Dock icon (Box) and SystemStatusCluster icon (Activity).
  // Singular Implementation: one canonical icon per surface, used
  // everywhere it surfaces (Dock, Launcher, status cluster).
  gauge: Gauge,
  // ADR-327: wallet glyph for the /budget surface (supersedes /pace's gauge).
  wallet: Wallet,
  // 2026-06-03: home glyph for the Home surface (post ADR-312
  // cockpit→home rename). Replaces square-activity, which no longer
  // matched the surface name.
  home: Home,
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
  // ADR-331 D1: rocket glyph for the /setup guided first-boot sequence.
  rocket: Rocket,
  // ADR-338 D4.1: rss glyph for the /sources standing-watch surface.
  rss: Rss,
  scale: Scale,
  // ADR-297 D18.2 (2026-05-22): scroll-text registered for the Feed
  // surface, disambiguating it from the universal ChatDrawer FAB
  // (which is hardcoded MessageCircle in Desktop.tsx).
  'scroll-text': ScrollText,
  settings: Settings,
  'shield-check': ShieldCheck,
  target: Target,
  // ADR-347: user glyph for the account window (the `settings` slug,
  // UserMenu-reached — billing/usage/privacy, the human/principal).
  user: User,
  'user-circle': UserCircle,
  users: Users,
};

export function resolveSurfaceIcon(iconKey: string): LucideIcon {
  return ICON_REGISTRY[iconKey] ?? Box;
}
