import { LOCALE_COOKIE, LOCALE_COOKIE_MAX_AGE, type Locale } from "@/i18n/config";

/** The device's explicit choice (ADR-660 D2). Written only by the switcher — never by a guess. */
export function writeLocaleCookie(locale: Locale) {
  document.cookie = `${LOCALE_COOKIE}=${locale}; path=/; max-age=${LOCALE_COOKIE_MAX_AGE}; samesite=lax`;
}

export function readLocaleCookie(): string | null {
  const hit = document.cookie.split("; ").find((pair) => pair.startsWith(`${LOCALE_COOKIE}=`));
  return hit ? decodeURIComponent(hit.slice(LOCALE_COOKIE.length + 1)) : null;
}
