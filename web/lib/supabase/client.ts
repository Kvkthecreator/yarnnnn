import { createClientComponentClient } from "@supabase/auth-helpers-nextjs";
import { createClient as createSupabaseClient, type SupabaseClient } from "@supabase/supabase-js";
import { isNativeShell } from "@/lib/shell/external-navigation";

/**
 * The browser Supabase client — one function, two storage backends
 * (ADR-661 §4.1a, §8 step 4).
 *
 * ON THE WEB, unchanged: `createClientComponentClient` persists the session as
 * a cookie, which is what `middleware.ts` reads and ROTATES server-side on
 * every request. Nothing about that changes, and this file must not make it
 * change — the web session's refresh discipline is load-bearing.
 *
 * IN THE SHELL a cookie is the wrong container. It is a browser-origin
 * concept, and the packaged app serves from a custom scheme with no origin to
 * scope one to; there is also no middleware to rotate it. So the shell uses a
 * plain supabase-js client over `localStorage` with `autoRefreshToken`, which
 * puts the refresh in the client where the shell can actually perform it.
 *
 * ⭐ **This is the one place the port is a security change rather than
 * plumbing.** The web build's session is refreshed by a server that sees every
 * request; the shell's is refreshed by the client itself. The trade is
 * deliberate and recorded in §4.1a — a shell cannot have the server half —
 * and it is contained here rather than spread across call sites.
 *
 * `AuthGate` is indifferent to which branch it got: it asks `getSession()` and
 * does not care where the answer is kept. That indifference is why the gate
 * ported unchanged, and why this seam is a two-line branch rather than a
 * rewrite.
 *
 * ⚠️ `localStorage` is the interim store. Tauri's OS keychain plugin is the
 * right home for a refresh token on a shared machine, and moving to it is a
 * change to THIS function and nothing else — which is the point of keeping the
 * decision here.
 */

type Client = SupabaseClient;

let shellClient: Client | null = null;

function createShellClient(): Client {
  // Singleton: supabase-js warns (and can double-refresh) when several clients
  // share one storage key, and `createClientComponentClient` is itself a
  // singleton on the web. The two branches must behave the same way here.
  if (shellClient) return shellClient;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) {
    // Inlined at build time. Missing means the shell was built without them,
    // and every call would fail opaquely — say so once, loudly, at the seam.
    throw new Error(
      "Shell build is missing NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY",
    );
  }

  shellClient = createSupabaseClient(url, key, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      // PKCE, explicitly — this is the whole auth architecture of a desktop
      // app and supabase-js does NOT default to it (`flowType: 'implicit'` is
      // the library default; the web's auth-helpers sets `pkce` for us, which
      // is why only the shell was affected).
      //
      // Implicit returns the session in a URL FRAGMENT (`#access_token=…`).
      // A fragment is never sent anywhere — not to a server, and not through
      // a custom-scheme deep link — so the app was handed a callback carrying
      // nothing usable and stayed signed out. That is the "sign in, land back
      // on a logged-out page" loop.
      //
      // PKCE returns a `?code=` in the QUERY STRING, which survives the round
      // trip through the browser and the `yarnnn://` hand-off, and which
      // `app/auth/callback` exchanges for a session. It is also the
      // conventional flow for a native app for exactly this reason (RFC 8252):
      // no client secret, and the verifier never leaves the device.

      flowType: "pkce",
      // The callback arrives on a deep link the host hands to the app, not as
      // a browser navigation, so the client cannot spot it in `location`.
      // `app/auth/callback` calls `exchangeCodeForSession` explicitly instead.
      detectSessionInUrl: false,
      storageKey: "yarnnn-shell-auth",
    },
  });
  return shellClient;
}

export function createClient(): Client {
  return isNativeShell()
    ? createShellClient()
    : (createClientComponentClient() as unknown as Client);
}
