// ADR-139: Workfloor + Task Surface Architecture
export const HOME_ROUTE = "/workfloor";
export const HOME_LABEL = "Workfloor";

export function isHomeRoute(pathname: string): boolean {
  return pathname === HOME_ROUTE || pathname.startsWith(`${HOME_ROUTE}/`);
}

export const ONBOARDING_ROUTE = "/onboarding";
