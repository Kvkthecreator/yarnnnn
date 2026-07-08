// Cockpit nav per ADR-205 Phase 4 F1 (feed-first landing) + ADR-214 (four-tab
// consolidation, 2026-04-23) + ADR-259 (feed surface rename, 2026-05-08) +
// ADR-297 D17 (Desktop as load-bearing layer, 2026-05-22).
// See docs/adr/ADR-214-agents-page-consolidation.md, ADR-198-surface-archetypes,
// ADR-259-feed-surface, and ADR-297 §D17 for the surface + boot frame.
//
// HOME_ROUTE = /desktop (ADR-297 §D17). Pre-D17 this was /feed — a relic from
// the pre-D11 single-page world where every operator was force-redirected to
// the Feed surface on login. D17 ratifies the YARNNN Agent OS boot model:
// login boots to the Desktop layer. Last-session windows restore from the
// open-surfaces registry (D13). Empty registry → empty Desktop with context-
// aware welcome copy. Per-slug routes (/feed, /recurrence, etc.) survive as
// deep-link transports.
//
// Launcher primary tiles (ADR-412): Home | Chat | Channels | Files | Agents.
// /schedule was a top-level tab (ADR-243) that has been folded into /work as
// the "Schedule" inner tab. /schedule now redirects to /work.
// /review deleted; Freddie's panes live in Workspace Settings → System Agent
// (ADR-412 D5 — the /agents roster is Altitude-3 only).
// /chat is a REAL surface again (ADR-412 D3 — the Chat workbench reclaimed
// the slug; the prior /chat → notifications redirect stub retired).
//
// =============================================================================
// Redirect Stub Policy (ADR-236 Item 5, 2026-04-29)
// =============================================================================
//
// Redirect stubs preserve bookmark/deep-link continuity when a route is
// retired or renamed. The policy:
//
//   1. A redirect stub is added when an ADR retires a route that may have
//      been bookmarked or shared. The target is the current canonical route.
//   2. ADR-308 (2026-06-01): a redirect stub is PURE SERVER TRANSPORT — a
//      server component calling `redirect(...)` from `next/navigation`,
//      fired before any layout mounts. It MUST NOT be a `'use client'`
//      component that redirects in `useEffect` — that paints one orphaned
//      frame inside the OS shell (no Desktop, dead dock) before
//      redirecting, the bimodality seam ADR-308 closed. Query params are
//      preserved via the server `searchParams` prop (e.g. /orchestrator →
//      HOME_ROUTE preserves OAuth callback params).
//   3. Each stub's docblock names the originating ADR and the rationale.
//   4. Stubs are reviewed at each frontend coherence pass (ADR-236 and its
//      successors) and removed when (a) the originating ADR has been
//      Implemented for at least one major release cycle AND (b) no inbound
//      external links to the route are known. Until both hold, the stub
//      stays.
//
// Active stubs (verified 2026-07-07):
//   (/chat is NO LONGER a stub — ADR-412 D3 reclaimed it for the Chat surface.)
//   /orchestrator  → /notifications?notifications.pane=understand (ADR-163, ADR-205 F1 → narrative home)
//   /feed          → /notifications?notifications.pane=understand (the /feed alias was always the NARRATIVE; lands at its real home)
//   /team          → /agents                           (ADR-214 — reverses ADR-201)
//   /overview      → /recurrence                       (ADR-205 F2; ADR-297 dissolved /work → Cadence; renamed → Recurrence 2026-06-03)
//   /cadence       → /recurrence                       (2026-06-03 — surface rename; substrate already spoke "recurrence")
//   /workfloor     → /notifications?notifications.pane=understand (ADR-163 → narrative home)
//   /memory        → /files?path=...IDENTITY.md        (ADR-215 R3)
//   (/context is NO LONGER a stub — ADR-370 reclaimed it as the boundary composition surface; the prior /context → /files stub is deleted.)
//   /system        → /settings                         (system tab removed 2026-05-02)
//   /operation     → /mandate                          (ADR-297 — atomic surface; routes.ts doc corrected 2026-05-30)
//   /backend       → /recurrence?recurrence.pane=activity         (ADR-265 rename; ADR-340 D8 fold to Runs lens)
//   /activity      → /recurrence?recurrence.pane=activity         (ADR-340 D8 — Machinery consolidation, Runs lens)
//
// =============================================================================
// ADR-297 §D17 (2026-05-22): HOME_ROUTE flips /feed → /desktop. The
// authenticated Desktop layer is the canonical landing route; per-slug
// routes (FEED_ROUTE, /recurrence, /mandate, etc.) survive as deep-link
// transports for direct surface mounting.
export const HOME_ROUTE = "/desktop";
export const HOME_LABEL = "Desktop";
export const DESKTOP_ROUTE = "/desktop";
// ADR-415 (2026-07-08): CONTEXT_ROUTE deleted. It pointed at /channels (the
// dissolved Channels surface) and had zero consumers; /channels + /context are
// now next.config.js redirect stubs → /home.
// FEED_ROUTE stays "/feed" as the redirect-stub URL. The /feed alias was always
// the NARRATIVE; after the 2026-07-02 ACTIVITY re-scope it forwards to the
// narrative's real home — /notifications?notifications.pane=understand (see
// next.config.js redirects()). Next.js carries the query string through, so
// deep-link params survive.
export const FEED_ROUTE = "/feed";
// ADR-297: /work dissolved — recurrence list + task detail folded into
// the Recurrence surface (renamed from Cadence 2026-06-03). WORK_ROUTE
// repointed to /recurrence so the surviving deep-links (`?task=`)
// resolve to the live surface. Both consumers (AgentContentView task
// links, /overview redirect stub) heal via this single repoint.
export const WORK_ROUTE = "/recurrence";
export const AGENTS_ROUTE = "/agents"; // ADR-214 — canonical (reverses ADR-201 /team rename).
// Files surface — slug `files`, route `/files`. Legacy `/context` is a
// redirect stub (2026-06-01). The substrate path `/workspace/context/…`
// is unrelated — it's the filesystem namespace, not a route URL.
export const FILES_ROUTE = "/files";
// WORKSPACE_CONFIG_ROUTE ("/workspace") deleted 2026-05-30 — ADR-297
// dissolved the /workspace container into atomic surfaces (mandate,
// autonomy, principles, etc.); the constant had zero consumers.
// ADR-340 D8 (2026-06-18): Activity folded to pane-grade under Recurrence —
// the Runs lens. /activity survives as an ADR-308 redirect stub; this constant
// repoints to the canonical live destination so any future consumer mounts the
// Runs lens directly. (Zero consumers at repoint time.)
export const ACTIVITY_ROUTE = "/recurrence?recurrence.pane=activity"; // Execution ledger (execution_events) — Runs lens of the Recurrence window.
export const CONNECTORS_ROUTE = "/connectors"; // Platform connections — Slack, Notion, GitHub, Lemon Squeezy, Alpaca.
// FREDDIE_ROUTE deleted 2026-07-07 — zero consumers, and ADR-412 D5 moved
// Freddie's panes off the /agents roster into Workspace Settings → System
// Agent (a stale ?agent=freddie deep-link falls through to roster list mode).

export function isHomeRoute(pathname: string): boolean {
  return pathname === HOME_ROUTE || pathname.startsWith(`${HOME_ROUTE}/`);
}
