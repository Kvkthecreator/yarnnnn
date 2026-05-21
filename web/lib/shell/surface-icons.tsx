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
  FolderOpen,
  Inbox,
  LayoutDashboard,
  MessageCircle,
  Package,
  Palette,
  Scale,
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
  'layout-dashboard': LayoutDashboard,
  'message-circle': MessageCircle,
  package: Package,
  palette: Palette,
  scale: Scale,
  'shield-check': ShieldCheck,
  target: Target,
  'user-circle': UserCircle,
  users: Users,
};

export function resolveSurfaceIcon(iconKey: string): LucideIcon {
  return ICON_REGISTRY[iconKey] ?? Box;
}
