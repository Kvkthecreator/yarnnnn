// Toggle bar navigation — Chat is home (ADR-163 Surface Restructure)
// Four top-level destinations: Chat | Work | Agents | Context
// Each answers exactly one question. See docs/adr/ADR-163-surface-restructure.md
export const HOME_ROUTE = "/chat";
export const HOME_LABEL = "Chat";
export const CHAT_ROUTE = "/chat";
export const WORK_ROUTE = "/work";
export const AGENTS_ROUTE = "/agents";
export const CONTEXT_ROUTE = "/context";

export function isHomeRoute(pathname: string): boolean {
  return pathname === HOME_ROUTE || pathname.startsWith(`${HOME_ROUTE}/`);
}
