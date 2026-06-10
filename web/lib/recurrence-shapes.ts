/**
 * Frontend recurrence-shape utilities (ADR-231 Phase 3.10 hygiene rename).
 *
 * Post-cutover, the recurrence's `surface_type` lives in the declaration
 * YAML's `surface_type:` field (read at compose time). The frontend reads
 * what the API surfaces — no client-side `type_key` → surface inference.
 * The legacy `resolveTaskSurface` and `TASK_SURFACE_MAP` were registry-
 * driven helpers; the registry is dissolved per ADR-207 P4b + ADR-231 D5.
 *
 * ADR-320 (2026-06-10): the `resolveDomainWorkspacePath` helper + its
 * `DOMAIN_KEY_TO_WORKSPACE_PATH` map were DELETED — they hardcoded the
 * dissolved `/workspace/context/{domain}` root (now `operation/{domain}`)
 * and had zero callers. Domain→path resolution is server-side now (the
 * directory registry + nav route emit `operation/` paths). Singular
 * Implementation: dead legacy-path code removed rather than repointed.
 */

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
