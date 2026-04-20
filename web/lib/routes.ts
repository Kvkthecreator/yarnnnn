// Cockpit nav per ADR-198 v2 + ADR-199 Overview surface.
//
// HOME_ROUTE = /overview per ADR-199. /chat is the expanded form of the
// ambient YARNNN rail (available via ThreePanelLayout on every surface),
// reachable by direct URL or rail-expand — not a primary nav tab.
//
// Current nav (ADR-199 phase): Overview | Work | Context | Agents
// After ADR-201: Overview | Team | Work | Context | Review (five destinations)
// After ADR-200 : Review destination added.
//
// See docs/adr/ADR-198-surface-archetypes.md, ADR-199-overview-surface.md.
export const HOME_ROUTE = "/overview";
export const HOME_LABEL = "Overview";
export const OVERVIEW_ROUTE = "/overview";
export const CHAT_ROUTE = "/chat";
export const WORK_ROUTE = "/work";
export const AGENTS_ROUTE = "/agents";
export const CONTEXT_ROUTE = "/context";
export const REVIEW_ROUTE = "/review"; // Destination shipping in ADR-200.

export function isHomeRoute(pathname: string): boolean {
  return pathname === HOME_ROUTE || pathname.startsWith(`${HOME_ROUTE}/`);
}
