/**
 * Compositor API client — ADR-225 §1 FE side.
 *
 * Single fetcher: GET /api/programs/surfaces. Auth handled by the
 * existing api client.
 */

import { api } from '@/lib/api/client';
import type { SurfacesResponse } from './types';

export async function fetchWorkspaceSurfaces(): Promise<SurfacesResponse> {
  // Casting through unknown because the api client's inline types use
  // `Record<string, unknown>` for tabs (intentional — it's a forwarded
  // shape) while the compositor's TS types mirror the server-side
  // composition_resolver structure precisely.
  const raw = await api.programs.getSurfaces();
  return raw as unknown as SurfacesResponse;
}
