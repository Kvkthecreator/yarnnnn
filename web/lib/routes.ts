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
// aware welcome copy. Per-slug routes (/feed, /cadence, etc.) survive as
// deep-link transports.
//
// Current nav: Feed | Work | Agents | Files
// /schedule was a top-level tab (ADR-243) that has been folded into /work as
// the "Schedule" inner tab. /schedule now redirects to /work.
// /review deleted; Reviewer lives at /agents?agent=reviewer.
// /chat redirects to /feed (ADR-259 vocabulary migration; preserves bookmarks).
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
//   2. The stub is a thin client component that calls `router.replace(...)`
//      (or `redirect(...)` from `next/navigation` for server pages). It
//      preserves query params when the target is a query-bearing route
//      (e.g. /orchestrator → /chat preserves OAuth callback params).
//   3. Each stub's docblock names the originating ADR and the rationale.
//   4. Stubs are reviewed at each frontend coherence pass (ADR-236 and its
//      successors) and removed when (a) the originating ADR has been
//      Implemented for at least one major release cycle AND (b) no inbound
//      external links to the route are known. Until both hold, the stub
//      stays.
//
// Active stubs (verified 2026-05-11):
//   /chat          → /feed                             (ADR-259 — surface rename)
//   /orchestrator  → /feed                             (ADR-163, ADR-205 F1)
//   /team          → /agents                           (ADR-214 — reverses ADR-201)
//   /overview      → /cadence                          (ADR-205 F2; ADR-297 dissolved /work → Cadence)
//   /workfloor     → /feed                             (ADR-163)
//   /memory        → /context?path=...IDENTITY.md      (ADR-215 R3)
//   /system        → /settings                         (system tab removed 2026-05-02)
//   /operation     → /mandate                          (ADR-297 — atomic surface; routes.ts doc corrected 2026-05-30)
//   /backend       → /activity                         (ADR-265 — operator-readable rename)
//
// =============================================================================
// ADR-297 §D17 (2026-05-22): HOME_ROUTE flips /feed → /desktop. The
// authenticated Desktop layer is the canonical landing route; per-slug
// routes (FEED_ROUTE, /cadence, /mandate, etc.) survive as deep-link
// transports for direct surface mounting.
export const HOME_ROUTE = "/desktop";
export const HOME_LABEL = "Desktop";
export const DESKTOP_ROUTE = "/desktop";
export const FEED_ROUTE = "/feed";
// ADR-297: /work dissolved — recurrence list + task detail folded into
// the Cadence surface. WORK_ROUTE repointed to /cadence so the surviving
// deep-links (`?task=`) resolve to the live surface. Both consumers
// (AgentContentView task links, /overview redirect stub) heal via this
// single repoint.
export const WORK_ROUTE = "/cadence";
export const AGENTS_ROUTE = "/agents"; // ADR-214 — canonical (reverses ADR-201 /team rename).
export const CONTEXT_ROUTE = "/context";
// WORKSPACE_CONFIG_ROUTE ("/workspace") deleted 2026-05-30 — ADR-297
// dissolved the /workspace container into atomic surfaces (mandate,
// autonomy, principles, etc.); the constant had zero consumers.
export const ACTIVITY_ROUTE = "/activity";           // Workspace-wide activity ledger (execution_events, ADR-250 + ADR-265).
export const CONNECTORS_ROUTE = "/connectors"; // Platform connections — Slack, Notion, GitHub, Lemon Squeezy, Alpaca.
// ADR-272: System Agent dissolved as a cockpit entity (ADR-251 reversed).
// Only Reviewer remains as a systemic detail surface. Legacy URLs
// (?agent=system / ?agent=yarnnn / ?agent=thinking-partner) 404-clean.
export const REVIEWER_ROUTE = "/agents?agent=reviewer";

export function isHomeRoute(pathname: string): boolean {
  return pathname === HOME_ROUTE || pathname.startsWith(`${HOME_ROUTE}/`);
}
