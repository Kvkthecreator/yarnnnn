// Toggle bar navigation — Chat is home (ADR-180 Work/Context Surface Split)
// Four top-level destinations: Chat | Work | Context | Agents
// Work = operational (health, schedule, config). Context = knowledge (outputs, domains, uploads).
// See docs/adr/ADR-180-work-context-surface-split.md
export const HOME_ROUTE = "/chat";
export const HOME_LABEL = "Chat";
export const CHAT_ROUTE = "/chat";
export const WORK_ROUTE = "/work";
export const AGENTS_ROUTE = "/agents";
export const CONTEXT_ROUTE = "/context";

export function isHomeRoute(pathname: string): boolean {
  return pathname === HOME_ROUTE || pathname.startsWith(`${HOME_ROUTE}/`);
}
