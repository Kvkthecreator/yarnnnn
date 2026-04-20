// Cockpit nav per ADR-198 v2 (Overview / Team / Work / Context / Review)
// + ambient YARNNN rail. See docs/adr/ADR-198-surface-archetypes.md.
//
// HOME_ROUTE = /overview per ADR-199. /chat is the expanded form of the
// ambient YARNNN rail (available via ThreePanelLayout on every surface),
// reachable by direct URL or rail-expand — not a primary nav tab.
//
// Current nav (post-ADR-201): Overview | Work | Context | Team | Review
// Legacy /agents redirects to /team per ADR-201 migration bridge.
export const HOME_ROUTE = "/overview";
export const HOME_LABEL = "Overview";
export const OVERVIEW_ROUTE = "/overview";
export const CHAT_ROUTE = "/chat";
export const WORK_ROUTE = "/work";
export const TEAM_ROUTE = "/team"; // Renamed from AGENTS_ROUTE by ADR-201.
export const CONTEXT_ROUTE = "/context";
export const REVIEW_ROUTE = "/review";

export function isHomeRoute(pathname: string): boolean {
  return pathname === HOME_ROUTE || pathname.startsWith(`${HOME_ROUTE}/`);
}
