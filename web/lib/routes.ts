// Cockpit nav per ADR-205 Phase 4 F1 (chat-first landing) + ADR-214 (four-tab
// consolidation, 2026-04-23).
// See docs/adr/ADR-214-agents-page-consolidation.md
// and docs/adr/ADR-198-surface-archetypes.md for surface archetypes.
//
// HOME_ROUTE = /chat. A brand-new workspace has no authored agents and no
// authored tasks — the user's first meaningful action is conversational.
// Landing on /chat re-aligns with ADR-189's authored-team moat.
//
// Current nav: Chat | Work | Agents | Files
// /schedule was a top-level tab (ADR-243) that has been folded into /work as
// the "Schedule" inner tab. /schedule now redirects to /work.
// /review deleted; Reviewer lives at /agents?agent=reviewer.
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
// Active stubs (verified 2026-05-04):
//   /orchestrator  → /chat                             (ADR-163, ADR-205 F1)
//   /team          → /agents                           (ADR-214 — reverses ADR-201)
//   /overview      → /work                             (ADR-205 F2, ADR-225 Phase 3)
//   /workfloor     → /chat                             (ADR-163)
//   /memory        → /context?path=...IDENTITY.md      (ADR-215 R3)
//   /system        → /settings                         (system tab removed 2026-05-02)
//   /schedule      → /work                             (ADR-243 folded into Work tabs)
//   /operation     → /workspace                         (renamed before launch)
//
// =============================================================================
export const HOME_ROUTE = "/chat";
export const HOME_LABEL = "Chat";
export const CHAT_ROUTE = "/chat";
export const WORK_ROUTE = "/work";
export const AGENTS_ROUTE = "/agents"; // ADR-214 — canonical (reverses ADR-201 /team rename).
export const CONTEXT_ROUTE = "/context";
export const WORKSPACE_CONFIG_ROUTE = "/workspace"; // Workspace-level config (mandate, autonomy, principles, programs).
export const BACKEND_ROUTE = "/backend";             // Per-job execution log (execution_events, ADR-250).
export const CONNECTORS_ROUTE = "/connectors"; // Platform connections — Slack, Notion, GitHub, Lemon Squeezy, Alpaca.
// ADR-241: deep-link to TP detail. /agents (no param) redirects here.
// Slug is "yarnnn" — derived from title "YARNNN" (ADR-247 display_name change).
export const THINKING_PARTNER_ROUTE = "/agents?agent=yarnnn";

export function isHomeRoute(pathname: string): boolean {
  return pathname === HOME_ROUTE || pathname.startsWith(`${HOME_ROUTE}/`);
}
