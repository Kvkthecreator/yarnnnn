/**
 * Frontend task type utilities.
 *
 * The backend writes `**Surface:**` to TASK.md for new tasks, but older tasks
 * may not have it. This map lets the frontend derive surface_type from type_key
 * when task.surface is null.
 *
 * Keep in sync with api/services/task_types.py surface_type values.
 */

export type SurfaceType = 'report' | 'deck' | 'digest' | 'dashboard';

/** type_key → surface_type for produces_deliverable tasks */
const TASK_SURFACE_MAP: Record<string, SurfaceType> = {
  'competitive-brief': 'report',
  'market-report': 'report',
  'meeting-prep': 'report',
  'content-brief': 'report',
  'stakeholder-update': 'deck',
  'launch-material': 'deck',
  'daily-update': 'digest',
  'project-status': 'dashboard',
};

/**
 * Resolve the surface_type for a task.
 * Prefers the TASK.md-parsed value (`task.surface`) when present,
 * falls back to the registry map via `task.type_key`.
 */
export function resolveTaskSurface(
  surface: string | null | undefined,
  type_key: string | null | undefined,
): SurfaceType | null {
  if (surface && (surface === 'report' || surface === 'deck' || surface === 'digest' || surface === 'dashboard')) {
    return surface as SurfaceType;
  }
  if (type_key && TASK_SURFACE_MAP[type_key]) {
    return TASK_SURFACE_MAP[type_key];
  }
  return null;
}

/** Human-readable label for a surface type */
export const SURFACE_TYPE_LABELS: Record<SurfaceType, string> = {
  report: 'Report',
  deck: 'Deck',
  digest: 'Digest',
  dashboard: 'Dashboard',
};
