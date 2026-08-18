/**
 * resolveAccessToken — the JWT a Realtime socket must carry (ADR-575 D7).
 *
 * ## Why this is not just `getSession()`
 *
 * Realtime re-checks RLS per subscriber using the token the **socket** holds,
 * not the one the REST calls hold. Without it the socket connects with the anon
 * apikey, `auth.uid()` is NULL inside the policy, and every row is dropped while
 * the channel still reports `"Subscribed to PostgreSQL"` with the correct
 * filter — subscribed, filtered, and silent.
 *
 * `createClientComponentClient()` (legacy `@supabase/auth-helpers-nextjs`)
 * persists the session as a **chunked, JSON-array cookie**, and its
 * `getSession()` did not yield a token on the deployed surface — measured, with
 * the resulting `phx_join` carrying no `access_token` and delivering nothing.
 *
 * So this tries the supported path first and falls back to reading the cookie
 * the same client wrote. The fallback is deliberate and narrow: it is the
 * client's OWN storage, in the client's OWN format, read for the one value the
 * socket needs.
 *
 * ## The shape, measured rather than assumed
 *
 * `sb-<ref>-auth-token` decodes to a JSON **array** whose first element is the
 * access token (subsequent elements are the refresh token and session
 * metadata). Verified in production: `arr.length === 5`, `arr[0]` is a
 * three-segment JWT of ~1.4KB. Confirmed end-to-end by joining a raw socket
 * with `access_token: arr[0]` and receiving a real `postgres_changes` INSERT
 * frame for a peer write — the same write that produced nothing without it.
 */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type SupabaseLike = { auth: { getSession: () => Promise<any> } };

/** A three-segment JWT, cheaply. */
function looksLikeJwt(v: unknown): v is string {
  return typeof v === 'string' && v.split('.').length === 3 && v.length > 40;
}

/**
 * Read the access token from the auth cookie this client wrote. Returns null on
 * any shape it does not recognize — a socket without a token degrades to
 * "receives nothing", never to a thrown render.
 */
function tokenFromCookie(): string | null {
  if (typeof document === 'undefined') return null;
  const hit = document.cookie
    .split(';')
    .map((c) => c.trim())
    .find((c) => /^sb-.*-auth-token=/.test(c));
  if (!hit) return null;
  try {
    const raw = decodeURIComponent(hit.slice(hit.indexOf('=') + 1));
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && looksLikeJwt(parsed[0])) return parsed[0];
    // Some versions store the session object directly.
    if (parsed && looksLikeJwt(parsed.access_token)) return parsed.access_token;
  } catch {
    /* unrecognized shape — fall through to null */
  }
  return null;
}

/** The token for `realtime.setAuth`, or null if the member has no session. */
export async function resolveAccessToken(client: SupabaseLike): Promise<string | null> {
  try {
    const { data } = await client.auth.getSession();
    const token = data?.session?.access_token;
    if (looksLikeJwt(token)) return token;
  } catch {
    /* fall through to the cookie */
  }
  return tokenFromCookie();
}
