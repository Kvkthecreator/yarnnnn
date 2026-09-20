import { getRequestConfig } from "next-intl/server";
import { DEFAULT_LOCALE } from "./config";
import { resolveLocale } from "./resolve";

type Messages = { [key: string]: string | Messages };

/** `over` laid on `base`, key by key — so a catalog can be partial. */
function layer(base: Messages, over: Messages): Messages {
  const out: Messages = { ...base };
  for (const [key, value] of Object.entries(over)) {
    const under = out[key];
    out[key] =
      typeof value === "object" && typeof under === "object" ? layer(under, value) : value;
  }
  return out;
}

/**
 * ADR-660 D4 — a missing key falls back to English rather than throwing: a
 * half-translated surface reads as English, never as a broken one. Parity is
 * the gate's job (`api/test_adr660_the_interface_speaks_korean.py`), not the
 * render's.
 */
export default getRequestConfig(async () => {
  const locale = await resolveLocale();
  const base = (await import(`../messages/${DEFAULT_LOCALE}.json`)).default as Messages;
  if (locale === DEFAULT_LOCALE) return { locale, messages: base };
  const own = (await import(`../messages/${locale}.json`)).default as Messages;
  return { locale, messages: layer(base, own) };
});
