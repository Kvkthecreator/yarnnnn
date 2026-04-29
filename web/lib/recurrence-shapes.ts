/**
 * Frontend recurrence-shape utilities (ADR-231 Phase 3.10 hygiene rename).
 *
 * Post-cutover, the recurrence's `surface_type` lives in the declaration
 * YAML's `surface_type:` field (read at compose time). The frontend reads
 * what the API surfaces — no client-side `type_key` → surface inference.
 * The legacy `resolveTaskSurface` and `TASK_SURFACE_MAP` were registry-
 * driven helpers; the registry is dissolved per ADR-207 P4b + ADR-231 D5.
 *
 * What survives in this module: domain-key → workspace-path resolution.
 * That's a directory naming convention (key ≠ dir name in some cases),
 * still relevant for natural-home substrate path construction in the UI.
 */

const DOMAIN_KEY_TO_WORKSPACE_PATH: Record<string, string> = {
  'competitors':      '/workspace/context/competitors',
  'market':           '/workspace/context/market',
  'relationships':    '/workspace/context/relationships',
  'projects':         '/workspace/context/projects',
  'content_research': '/workspace/context/content',
  'signals':          '/workspace/context/signals',
  'slack':            '/workspace/context/slack',
  'notion':           '/workspace/context/notion',
  'github':           '/workspace/context/github',
};

export function resolveDomainWorkspacePath(domainKey: string): string {
  return DOMAIN_KEY_TO_WORKSPACE_PATH[domainKey] ?? `/workspace/context/${domainKey}`;
}

export type SurfaceType = 'report' | 'deck' | 'digest' | 'dashboard';

/** Human-readable label for a surface type */
export const SURFACE_TYPE_LABELS: Record<SurfaceType, string> = {
  report: 'Report',
  deck: 'Deck',
  digest: 'Digest',
  dashboard: 'Dashboard',
};

/**
 * Coerce a raw surface_type string from the API (declaration YAML) into the
 * typed SurfaceType union. Returns null when the value is missing/invalid;
 * caller falls back to default rendering (typically 'report').
 */
export function coerceSurfaceType(
  surface: string | null | undefined,
): SurfaceType | null {
  if (
    surface === 'report' ||
    surface === 'deck' ||
    surface === 'digest' ||
    surface === 'dashboard'
  ) {
    return surface;
  }
  return null;
}
