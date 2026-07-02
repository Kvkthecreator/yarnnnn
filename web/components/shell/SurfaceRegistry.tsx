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

// ADR-385 — the Channels perception+principal surface (was `context`).
// Window-grade like Home / Notifications; its panes re-mount existing mirror
// bodies (ConnectedIntegrations → Connections, SourcesCard → Sources,
// WorkspaceMembersCard → AI Connections, FeedSurface [filtered to inbound
// crossings] → In, EmissionsView → Out). The 2026-07-02 ACTIVITY re-scope
// retired the Flow pane (the global narrative lives at Notifications → Activity,
// not on a boundary surface).
//
// ADR-385 follow-on (2026-06-30): the legacy `feed` + `context` alias slugs
// are RETIRED from this registry (full alias deletion). They produced a
// duplicate dock icon from stale persisted state; persisted dock state naming
// them is now normalized → `channels` at the surface-preferences read boundary
// (lib/shell/surface-preferences.ts), and the OLD `/feed` + `/context` URLs are
// next.config.js server redirects. So nothing foregrounds `feed`/`context`
// anymore — they need no registry entry.
import ChannelsPage from '@/app/(authenticated)/channels/page';
import HomePage from '@/app/(authenticated)/home/page';
import RecurrencePage from '@/app/(authenticated)/recurrence/page';
// ADR-327: /pace retired from the surface registry — it is now a route-level
// redirect stub (app/(authenticated)/pace/page.tsx → /budget) handled by Next
// file routing, not a mounted kernel surface.
// ADR-341 (2026-06-18) — the constitution surfaces (mandate/principles/
// identity) become PANE-GRADE under Workspace Settings (registry
// `pane_of: "workspace-settings"`): their *Card full variants render as
// Constitution panes inside WorkspaceSettingsPage. No window component —
// their slugs resolve to `undefined` here, foregroundSurface(slug) →
// workspace-settings + ?pane=, and /mandate //principles //identity are
// ADR-308 redirect stubs. Their FIRST-CLASS door stays the Home
// constitution band (ADR-312 D5) — HomeHeader consumes the cards
// directly, independent of these (now-deleted) page routes.
import QueuePage from '@/app/(authenticated)/queue/page';
// ADR-346 (2026-06-19) — the Operation composition window (Decide · Read ·
// Tune). Window-grade (no pane_of) like Home; its panes reuse mirror bodies.
import NotificationsPage from '@/app/(authenticated)/notifications/page';
// ADR-340 D8 (2026-06-18) — Machinery consolidation. Activity is PANE-GRADE
// under Recurrence (registry `pane_of: "recurrence"`): the Runs lens rendered
// inside RecurrencePage (shared ActivityLog body). No window component — the
// slug resolves to `undefined` here, foregroundSurface('activity') → recurrence
// + ?pane=activity, and /activity is an ADR-308 redirect stub.
import AgentsPage from '@/app/(authenticated)/agents/page';
import FilesPage from '@/app/(authenticated)/files/page';
// ADR-331 D1: the guided first-boot Sequence surface. Built as a page +
// SetupSequence renderer but never registered as a kernel surface until the
// ADR-338 surface audit — the launcher's "Setup" link was a dead no-op
// because isKernelSurfaceSlug('setup') was false.
import SetupPage from '@/app/(authenticated)/setup/page';
// ADR-297 D19.4 (2026-05-22) — Settings + Connectors promoted from
// legacy pages to atomic kernel surfaces. Reverses D19.7.
// ADR-347 (2026-06-19) — the two-door split (ADR-341) is reversed.
// `workspace-settings` is THE one Settings door (the operation's settings);
// budget / autonomy / expected-output / program / connectors / sources are
// PANE-GRADE (registry `pane_of: "workspace-settings"`) and render as
// sidebar panes inside it. They have NO window component — their slugs
// resolve to `undefined` here; the window manager resolves
// foregroundSurface(pane-slug) → workspace-settings + ?pane=, and their old
// routes are ADR-308 redirect stubs. The `settings` slug is now the ACCOUNT
// window the UserMenu opens (billing/usage/account), kept as a windowed page.
import SettingsPage from '@/app/(authenticated)/settings/page';
import WorkspaceSettingsPage from '@/app/(authenticated)/workspace-settings/page';  // ADR-347 — the one Settings door

export const KERNEL_SURFACE_REGISTRY: Partial<Record<KernelSurfaceSlug, ComponentType>> = {
  // ADR-385 — the Channels perception+principal surface. (The legacy `feed` +
  // `context` alias keys were deleted 2026-06-30 — full alias deletion; their
  // slugs no longer exist in the union, persisted dock state is normalized →
  // `channels`, and the old URLs are next.config redirects.)
  channels: ChannelsPage,
  home: HomePage,
  recurrence: RecurrencePage,
  // ADR-309 (2026-06-01): `brand` slug DELETED. Brand is not a standalone
  // surface — the Identity surface (IdentityBrandCard) co-renders it.
  // /brand is a server redirect → /identity (ADR-308).
  // ADR-341 (2026-06-18): mandate/principles/identity are pane-grade under
  // workspace-settings; no window component (resolve to undefined here).
  queue: QueuePage,
  notifications: NotificationsPage,  // ADR-346/349 — the operating-work composition (was 'operation')
  // ADR-340 D8 — `activity` is pane-grade under recurrence; no window component.
  agents: AgentsPage,
  files: FilesPage,
  setup: SetupPage,  // ADR-331 D1 — guided first-boot Sequence
  settings: SettingsPage,  // ADR-347 — the account window (UserMenu-reached: billing/usage/account)
  'workspace-settings': WorkspaceSettingsPage,  // ADR-347 — the ONE Settings door (the operation)
};

export function resolveSurfaceComponent(slug: KernelSurfaceSlug): ComponentType | undefined {
  return KERNEL_SURFACE_REGISTRY[slug];
}
