// Toggle bar navigation — Agents is home (SURFACE-ARCHITECTURE.md v3)
export const HOME_ROUTE = "/agents";
export const HOME_LABEL = "Agents";
export const CHAT_ROUTE = "/chat";
export const CONTEXT_ROUTE = "/context";
export const ACTIVITY_ROUTE = "/activity";

export function isHomeRoute(pathname: string): boolean {
  return pathname === HOME_ROUTE || pathname.startsWith(`${HOME_ROUTE}/`);
}
