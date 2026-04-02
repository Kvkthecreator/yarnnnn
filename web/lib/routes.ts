// Toggle bar navigation — Tasks is home
export const HOME_ROUTE = "/tasks";
export const HOME_LABEL = "Tasks";
export const CONTEXT_ROUTE = "/context";

export function isHomeRoute(pathname: string): boolean {
  return pathname === HOME_ROUTE || pathname.startsWith(`${HOME_ROUTE}/`);
}
