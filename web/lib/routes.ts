export const HOME_ROUTE = "/dashboard";
export const HOME_LABEL = "Dashboard";

export const ORCHESTRATOR_ROUTE = "/orchestrator";
export const ORCHESTRATOR_LABEL = "Orchestrator";

export function isHomeRoute(pathname: string): boolean {
  return pathname === HOME_ROUTE || pathname.startsWith(`${HOME_ROUTE}/`);
}

export function isOrchestratorRoute(pathname: string): boolean {
  return pathname === ORCHESTRATOR_ROUTE || pathname.startsWith(`${ORCHESTRATOR_ROUTE}/`);
}

export const PROJECTS_ROUTE = "/projects";
export const PROJECTS_LABEL = "Projects";
