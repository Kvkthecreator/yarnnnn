/**
 * ADR-660 D2's resolution chain, resolved in the CLIENT (ADR-661 §8 step 2).
 *
 * The server chain (`i18n/resolve.ts`) reads `cookies()` and `headers()`, which
 * exist only inside a request. The packaged shell has no request, so steps 2
 * and 3 there have no source and every surface would silently fall to English —
 * a silent failure, which is the worst kind. This module is the same chain,
 * same order, from what a client can see:
 *
 *   1. the account's preference   — signed in; follows the member everywhere
 *   2. the device cookie          — what was chosen on this device
 *   3. navigator.languages        — the device's own list, never written down
 *   4. English
 *
 * It is NOT a second policy. The ORDER is ADR-660 D2 and lives in one place
 * conceptually; what differs is only where each step reads from, because the
 * two builds can see different things. The one substantive difference is step
 * 3: the server negotiates `Accept-Language` (a quality-ranked header), the
 * client reads `navigator.languages` (an ordered list, no qualities). Both
 * answer the same question — *what does this device prefer* — and
 * `negotiateLocale` is reused for it by rendering the list back into the
 * header's grammar, so one matcher serves both and a roster change cannot
 * reach one and miss the other.
 *
 * A guess is still never written down (D2): this module only READS. The cookie
 * is written by the switcher and by `LocaleEffects`' reconciliation, never here.
 */

import {
  DEFAULT_LOCALE,
  LOCALE_COOKIE,
  LOCALE_METADATA_KEY,
  isLocale,
  negotiateLocale,
  type Locale,
} from "./config";

/** The account's own preference, or null — "unset" must be distinguishable from "en". */
export function accountLocaleFrom(userMetadata: unknown): Locale | null {
  const value = (userMetadata as Record<string, unknown> | null | undefined)?.[
    LOCALE_METADATA_KEY
  ];
  return isLocale(value) ? value : null;
}

/** Step 2 — the device's explicit choice. Duplicated from `locale-cookie.ts`'s
 *  reader only in spirit: that module is the WRITE side and imports nothing
 *  else; keeping the read here lets this file stand alone in a build with no
 *  DOM at module-eval time. */
function deviceCookie(): Locale | null {
  if (typeof document === "undefined") return null;
  const hit = document.cookie
    .split("; ")
    .find((pair) => pair.startsWith(`${LOCALE_COOKIE}=`));
  if (!hit) return null;
  const value = decodeURIComponent(hit.slice(LOCALE_COOKIE.length + 1));
  return isLocale(value) ? value : null;
}

/**
 * Step 3 — the device's own language list.
 *
 * `navigator.languages` is ordered by preference and carries no q-values, so it
 * is rendered back into `Accept-Language` grammar and handed to the SAME
 * matcher the server uses. That is deliberate: `negotiateLocale` already knows
 * to match on the primary subtag (`ko-KR` → `ko`) and to respect roster order,
 * and re-implementing that here is how the two halves would drift.
 */
function deviceLanguages(): Locale | null {
  if (typeof navigator === "undefined") return null;
  const list =
    navigator.languages && navigator.languages.length
      ? navigator.languages
      : navigator.language
        ? [navigator.language]
        : [];
  if (!list.length) return null;
  // Descending q so the matcher's quality sort preserves the list's own order.
  const header = list
    .map((tag, index) => (index === 0 ? tag : `${tag};q=${(1 - index * 0.01).toFixed(2)}`))
    .join(",");
  return negotiateLocale(header);
}

/**
 * The chain. `userMetadata` is the signed-in member's `user_metadata` — the
 * caller already holds it from the session it resolved, so this costs no
 * request of its own (the same economy `resolveLocale` gets from
 * `getRequestUser`'s request cache).
 */
export function resolveLocaleClient(userMetadata?: unknown): Locale {
  return (
    accountLocaleFrom(userMetadata) ??
    deviceCookie() ??
    deviceLanguages() ??
    DEFAULT_LOCALE
  );
}
