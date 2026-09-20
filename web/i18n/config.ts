/**
 * ADR-660 D1 — the language roster. Adding a language is a row here and a
 * catalog in `web/messages/`, nothing else.
 *
 * Safe to import from client and server: no `next/headers`, no catalogs.
 */

export const LOCALES = ["en", "ko"] as const;
export type Locale = (typeof LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "en";

/** The device's explicit choice (ADR-660 D2 step 2). Never written by a guess. */
export const LOCALE_COOKIE = "NEXT_LOCALE";
export const LOCALE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

/** Where the account's preference lives: `auth.users.user_metadata.locale`. */
export const LOCALE_METADATA_KEY = "locale";

/** A language is always named in itself — a Korean reader finds 한국어, not "Korean". */
export const LOCALE_ENDONYMS: Record<Locale, string> = {
  en: "English",
  ko: "한국어",
};

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (LOCALES as readonly string[]).includes(value);
}

/**
 * Pick a roster locale from an `Accept-Language` header, by quality then order.
 * Matches on the primary subtag, so `ko-KR` resolves to `ko`. Returns null when
 * nothing on the roster is acceptable — the caller owns the default.
 */
export function negotiateLocale(acceptLanguage: string | null | undefined): Locale | null {
  if (!acceptLanguage) return null;
  const ranked = acceptLanguage
    .split(",")
    .map((part, index) => {
      const [tag, ...params] = part.trim().split(";");
      const q = params.map((p) => p.trim()).find((p) => p.startsWith("q="));
      const quality = q ? Number(q.slice(2)) : 1;
      return { tag: tag.trim().toLowerCase(), quality: Number.isFinite(quality) ? quality : 0, index };
    })
    .filter((entry) => entry.tag && entry.quality > 0)
    .sort((a, b) => b.quality - a.quality || a.index - b.index);
  for (const { tag } of ranked) {
    const primary = tag.split("-")[0];
    if (isLocale(primary)) return primary;
  }
  return null;
}
