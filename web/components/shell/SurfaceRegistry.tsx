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
import CockpitPage from '@/app/(authenticated)/cockpit/page';
import CadencePage from '@/app/(authenticated)/cadence/page';
import PacePage from '@/app/(authenticated)/pace/page';
import AutonomyPage from '@/app/(authenticated)/autonomy/page';
import MandatePage from '@/app/(authenticated)/mandate/page';
import PrinciplesPage from '@/app/(authenticated)/principles/page';
import IdentityPage from '@/app/(authenticated)/identity/page';
import ProgramPage from '@/app/(authenticated)/program/page';
import QueuePage from '@/app/(authenticated)/queue/page';
import ActivityPage from '@/app/(authenticated)/activity/page';
import AgentsPage from '@/app/(authenticated)/agents/page';
import FilesPage from '@/app/(authenticated)/files/page';
// ADR-297 D19.4 (2026-05-22) — Settings + Connectors promoted from
// legacy pages to atomic kernel surfaces. Reverses D19.7. Inside the
// authenticated workspace, every surface is a window mounted on the
// Desktop; the legacy isLegacyNonAtomicRoute branch tightens to catch
// only auth + docs + marketing.
import SettingsPage from '@/app/(authenticated)/settings/page';
import ConnectorsPage from '@/app/(authenticated)/connectors/page';

export const KERNEL_SURFACE_REGISTRY: Record<KernelSurfaceSlug, ComponentType> = {
  feed: FeedPage,
  cockpit: CockpitPage,
  cadence: CadencePage,
  pace: PacePage,
  autonomy: AutonomyPage,
  // Brand co-renders inside IdentityPage (per ADR-297 D1 — the
  // IdentityBrandCard hosts both). The Brand slug maps to the same
  // component for now; future split is operator-demand-driven.
  brand: IdentityPage,
  mandate: MandatePage,
  principles: PrinciplesPage,
  identity: IdentityPage,
  program: ProgramPage,
  queue: QueuePage,
  activity: ActivityPage,
  agents: AgentsPage,
  files: FilesPage,
  settings: SettingsPage,
  connectors: ConnectorsPage,
};

export function resolveSurfaceComponent(slug: KernelSurfaceSlug): ComponentType {
  return KERNEL_SURFACE_REGISTRY[slug];
}
