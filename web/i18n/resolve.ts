// Server-only: `next/headers` fails the build if a client component imports this.
import { cookies, headers } from "next/headers";
import { getRequestUser } from "@/lib/supabase/server";
import {
  DEFAULT_LOCALE,
  LOCALE_COOKIE,
  isLocale,
  negotiateLocale,
  type Locale,
} from "./config";
// The account step is ONE reader, shared with the client chain
// (`resolve-client.ts`, ADR-661 §8 step 2) so "what counts as the account's
// preference" cannot answer differently on the two builds.
import { accountLocaleFrom } from "./resolve-client";

/**
 * ADR-660 D2 — the ONE resolution chain. A language belongs to the human, so
 * the account outranks the device; a guess is never recorded, so it outranks
 * nothing.
 *
 *   1. the account's preference   — signed in; fresh, follows the member everywhere
 *   2. the device cookie          — what was chosen here; all a signed-out page can know
 *   3. Accept-Language            — negotiated per request, never written down
 *   4. English
 *
 * `getRequestUser` is request-cached and shared with the authenticated layout,
 * so step 1 costs no request of its own.
 */
export async function resolveLocale(): Promise<Locale> {
  const user = await getRequestUser();
  const account = accountLocaleFrom(user?.user_metadata);
  if (account) return account;

  const cookieStore = await cookies();
  const device = cookieStore.get(LOCALE_COOKIE)?.value;
  if (isLocale(device)) return device;

  const headerStore = await headers();
  return negotiateLocale(headerStore.get("accept-language")) ?? DEFAULT_LOCALE;
}

/** The account's own preference, or null — the adoption effect needs to tell "unset" from "en". */
export async function accountLocale(): Promise<Locale | null> {
  const user = await getRequestUser();
  return accountLocaleFrom(user?.user_metadata);
}
