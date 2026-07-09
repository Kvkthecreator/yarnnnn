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

import type { ComponentType } from 'react';
import type { LucideIcon } from 'lucide-react';
import { FreddieAvatar } from '@/components/freddie/FreddieAvatar';
import {
  Activity,
  ArrowLeftRight,
  Bell,
  Box,
  Clock,
  FolderKanban,
  FolderOpen,
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

// The type the resolver returns — every call site renders `<Icon className=... />`
// and nothing else, so a component taking only `className` is the honest contract.
// This is wider than LucideIcon so the Freddie mascot (a custom SVG, not a lucide
// glyph) can be a first-class surface icon. (ADR-426 amendment, 2026-07-09.)
export type SurfaceIcon = ComponentType<{ className?: string }>;

// ADR-426 amendment — the Freddie System Agent door wears Freddie's OWN mark, the
// mascot face (FreddieAvatar), the same one on the chat rail FAB + ChatDrawer +
// FreddieCard. In CHROME (launcher / dock / top-bar) it renders MONOCHROME
// (mono → currentColor silhouette) so it sits in the glyph row like the lucide
// icons and inherits the active tile's `text-background` white-on-black recolor
// (the full-color Frankie is the BRAND mark elsewhere; on the active tile it
// ignored the recolor and read as a heavy green block — 2026-07-09). Rendered
// STILL (mono implies still) — motion is the "working" signal, a static tile
// must not perpetually animate. The `freddie` icon_key resolves here.
const FreddieSurfaceIcon: SurfaceIcon = ({ className }) => (
  <FreddieAvatar mono className={className} />
);

const ICON_REGISTRY: Record<string, LucideIcon> = {
  activity: Activity,
  // ADR-370: the Context boundary surface — context flowing in + out across
  // the operation's edge. The two-way arrow reads as "the boundary / the
  // exchange", distinct from the scroll-text Feed (now the Flow lens within).
  'arrow-left-right': ArrowLeftRight,
  // ADR-349 D2: the Notifications surface IS the topbar bell at a second zoom
  // ("one name, two zooms"). It carries the SAME Bell glyph the AttentionCenter
  // renders, so the launcher tile + Dock icon + top-bar bell read as one
  // object. Singular Implementation: one canonical icon for Notifications,
  // used everywhere it surfaces (top-bar glance, Launcher tile, Dock icon).
  bell: Bell,
  clock: Clock,
  folder: FolderOpen,
  // ADR-349 D4: the Workspace Settings (operation) door — distinct from the
  // System Settings gear so the two launcher doors read apart.
  'folder-kanban': FolderKanban,
  // ADR-327: wallet glyph for the /budget surface (supersedes /pace's gauge —
  // the `gauge` key was removed ADR-349 D2 once Notifications stopped borrowing
  // it; no surface declares gauge anymore).
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

export function resolveSurfaceIcon(iconKey: string): SurfaceIcon {
  // ADR-426 amendment — the Freddie mascot is not a lucide glyph; resolve it
  // explicitly so launcher, dock, and page header all render the same face.
  if (iconKey === 'freddie') return FreddieSurfaceIcon;
  return ICON_REGISTRY[iconKey] ?? Box;
}
