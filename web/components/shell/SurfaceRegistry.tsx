'use client';

/**
 * SurfaceRegistry — ADR-297 axiom (2026-05-21).
 *
 * Maps each KernelSurfaceSlug to its React component. The single-page
 * shell viewport reads this registry to mount whichever surface is
 * currently active in DeskState.
 *
 * Per the axiom: surface = viewport panel, not URL destination. A
 * surface is a mountable React component bound to substrate; the
 * registry is the runtime resolver from slug → component.
 *
 * Each entry imports the existing per-slug page component (the same
 * file that previously rendered at `/{slug}` as a Next.js route). The
 * page wrappers themselves now exist primarily as deep-link
 * redirectors that bounce to `/?surface=atomic&slug={slug}`; the real
 * render happens here in the viewport.
 */

import type { ComponentType } from 'react';
import type { KernelSurfaceSlug } from '@/types/desk';

import FeedPage from '@/app/(authenticated)/feed/page';
import HomePage from '@/app/(authenticated)/home/page';
import RecurrencePage from '@/app/(authenticated)/recurrence/page';
// ADR-327: /pace retired from the surface registry — it is now a route-level
// redirect stub (app/(authenticated)/pace/page.tsx → /budget) handled by Next
// file routing, not a mounted kernel surface.
import MandatePage from '@/app/(authenticated)/mandate/page';
import PrinciplesPage from '@/app/(authenticated)/principles/page';
import IdentityPage from '@/app/(authenticated)/identity/page';
import QueuePage from '@/app/(authenticated)/queue/page';
import ActivityPage from '@/app/(authenticated)/activity/page';
import AgentsPage from '@/app/(authenticated)/agents/page';
import FilesPage from '@/app/(authenticated)/files/page';
// ADR-331 D1: the guided first-boot Sequence surface. Built as a page +
// SetupSequence renderer but never registered as a kernel surface until the
// ADR-338 surface audit — the launcher's "Setup" link was a dead no-op
// because isKernelSurfaceSlug('setup') was false.
import SetupPage from '@/app/(authenticated)/setup/page';
// ADR-297 D19.4 (2026-05-22) — Settings + Connectors promoted from
// legacy pages to atomic kernel surfaces. Reverses D19.7.
// ADR-340 P2 (2026-06-12) — System Settings becomes the ONE os-config
// window: budget / autonomy / program / connectors / sources are
// PANE-GRADE (registry `pane_of: "settings"`) and render as sidebar
// panes inside SettingsPage. They have NO window component — their
// slugs resolve to `undefined` here, the window manager resolves
// foregroundSurface(pane-slug) → settings + ?pane=, and their old
// routes are ADR-308 redirect stubs.
import SettingsPage from '@/app/(authenticated)/settings/page';

export const KERNEL_SURFACE_REGISTRY: Partial<Record<KernelSurfaceSlug, ComponentType>> = {
  feed: FeedPage,
  home: HomePage,
  recurrence: RecurrencePage,
  // ADR-309 (2026-06-01): `brand` slug DELETED. Brand is not a standalone
  // surface — the Identity surface (IdentityBrandCard) co-renders it.
  // /brand is a server redirect → /identity (ADR-308).
  mandate: MandatePage,
  principles: PrinciplesPage,
  identity: IdentityPage,
  queue: QueuePage,
  activity: ActivityPage,
  agents: AgentsPage,
  files: FilesPage,
  setup: SetupPage,  // ADR-331 D1 — guided first-boot Sequence
  settings: SettingsPage,  // ADR-340 P2 — System Settings, the one os-config door
};

export function resolveSurfaceComponent(slug: KernelSurfaceSlug): ComponentType | undefined {
  return KERNEL_SURFACE_REGISTRY[slug];
}
