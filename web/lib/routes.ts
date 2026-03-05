export const HOME_ROUTE = "/dashboard";
export const HOME_LABEL = "Agent";

export function isHomeRoute(pathname: string): boolean {
  return pathname === HOME_ROUTE || pathname.startsWith(`${HOME_ROUTE}/`);
}
