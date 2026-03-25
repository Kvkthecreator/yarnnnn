export const HOME_ROUTE = "/orchestrator";
export const HOME_LABEL = "Orchestrator";

export function isHomeRoute(pathname: string): boolean {
  return pathname === HOME_ROUTE || pathname.startsWith(`${HOME_ROUTE}/`);
}

export const ONBOARDING_ROUTE = "/onboarding";
