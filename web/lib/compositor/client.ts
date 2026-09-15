/**
 * Compositor API client — ADR-225 §1 FE side.
 *
 * Single fetcher: GET /api/programs/surfaces. Auth handled by the
 * existing api client.
 *
 * ⭐ THE CACHE LIVES HERE, AND IT IS THE ONLY ONE (2026-09-15).
 *
 * `useComposition` has claimed since ADR-225 that it "caches the response per
 * session". It never did: every unprimed mount called this fetcher directly,
 * with no module cache and no in-flight dedupe. Driving a real logged-in
 * `/desktop` load on prod showed SEVEN identical `GET /api/programs/surfaces`
 * requests in one page load — for a response the same file describes as
 * changing "only at deploy time (bundle file changes) + when a workspace's
 * platform_connections change".
 *
 * Seven round-trips on the authenticated hot path, every navigation, for a
 * response that is the same seven times. Nothing went red: each request
 * returned 200, so the only symptom was latency and load.
 *
 * The cache belongs at the FETCHER, not in the hook: the hook runs once per
 * mount by construction, so a cache inside it can only ever dedupe within one
 * component. Here it dedupes across every caller and every mount.
 *
 * Two mechanisms, both needed:
 *   - `cached`   — a resolved response, reused for the session.
 *   - `inFlight` — the promise of a request already in the air. Without it,
 *                  seven components mounting in the SAME tick all miss the
 *                  (still-empty) cache and fire seven requests anyway. The
 *                  simultaneous-mount case is the observed one.
 *
 * `invalidateWorkspaceSurfaces()` drops both — call it when the composition
 * genuinely changes under the session (a connection added/removed), and on
 * workspace switch, so a second workspace never reads the first's surfaces.
 */

import { api } from '@/lib/api/client';
import type { SurfacesResponse } from './types';

let cached: SurfacesResponse | null = null;
let inFlight: Promise<SurfacesResponse> | null = null;

/**
 * Drop the cached composition.
 *
 * The composition is workspace-scoped, so anything that changes WHICH
 * workspace the session is bound to — or what that workspace has connected —
 * must call this, or the next read serves the previous workspace's surfaces.
 */
export function invalidateWorkspaceSurfaces(): void {
  cached = null;
  inFlight = null;
}

export async function fetchWorkspaceSurfaces(
  opts?: { force?: boolean },
): Promise<SurfacesResponse> {
  if (opts?.force) invalidateWorkspaceSurfaces();
  if (cached) return cached;
  // A request is already in the air — await THAT one rather than starting a
  // second. This is the branch the seven simultaneous mounts take.
  if (inFlight) return inFlight;

  inFlight = (async () => {
    // Casting through unknown because the api client's inline types use
    // `Record<string, unknown>` for tabs (intentional — it's a forwarded
    // shape) while the compositor's TS types mirror the server-side
    // composition_resolver structure precisely.
    const raw = await api.programs.getSurfaces();
    return raw as unknown as SurfacesResponse;
  })();

  try {
    const response = await inFlight;
    cached = response;
    return response;
  } catch (err) {
    // A failed fetch must NOT be cached — the hook's "cockpit never breaks"
    // fallback renders kernel defaults, and the next mount must be free to
    // retry rather than inheriting the failure for the whole session.
    throw err;
  } finally {
    inFlight = null;
  }
}
