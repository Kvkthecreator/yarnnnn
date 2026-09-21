/**
 * Marketing locale — the `/ko` prefix, and the ONE place a marketing path is
 * written for a language.
 *
 * ## Why marketing prefixes and the app does not
 *
 * ADR-660 D1 ruled the authenticated app carries no locale in its URLs: a path
 * there is an address members share with each other across languages, and
 * `/ko/files` would hand an English reader a Korean shell. The same ruling
 * names the other half — *"URL-prefixed locales are the convention for INDEXED
 * pages"* — and the marketing site is the indexed half. So this module exists
 * for marketing only; nothing under `(authenticated)` imports it.
 *
 * ## Why a prefix rather than the cookie the app uses
 *
 * The app resolves a locale by reading a cookie (`i18n/resolve.ts`). A cookie
 * read makes a route dynamic, and every marketing route is statically
 * prerendered — measured on the build's route table, which ADR-660 guarded
 * across four passes. A locale in the PATH is knowable at build time, so both
 * languages prerender and the static guarantee survives. It is also the only
 * shape that is separately indexable (its own `hreflang` alternate) and
 * shareable (a Korean link opens Korean for whoever receives it).
 *
 * ## The asymmetry, deliberate
 *
 * English is UNPREFIXED. `/pricing` is the English canonical and does not move,
 * so no live URL changes, no redirect chain is introduced, and existing search
 * rankings are untouched. Korean lives at `/ko/pricing`. `localePath` encodes
 * exactly that rule, once.
 */

import { DEFAULT_LOCALE, type Locale } from "@/i18n/config";

/** The prefix a locale's marketing pages live under. English has none. */
export function localePrefix(locale: Locale): string {
  return locale === DEFAULT_LOCALE ? "" : `/${locale}`;
}

/**
 * A marketing path, written for `locale`.
 *
 * `localePath('/pricing', 'en')` → `/pricing`
 * `localePath('/pricing', 'ko')` → `/ko/pricing`
 * `localePath('/', 'ko')`        → `/ko`
 *
 * ⭐ It REFUSES to prefix a path that is not on the roster, rather than
 * trusting the caller to check. The first version trusted the caller, and two
 * hero CTAs called it directly on `/pricing` and `/how-it-works` — producing
 * 404s on the Korean page that the header and footer (which did check) did
 * not. One guard at the one function is the difference between a rule and a
 * rule everyone has to remember.
 */
export function localePath(path: string, locale: Locale): string {
  const prefix = localePrefix(locale);
  if (!prefix || !isTranslatedPath(path)) return path;
  return path === "/" ? prefix : `${prefix}${path}`;
}

/**
 * The marketing paths that exist in every locale — phase 1 of the Korean
 * marketing pass.
 *
 * This roster is the single source of truth for three things that would
 * otherwise drift apart: which paths `localePath` may prefix, which pages the
 * sitemap emits an alternate for, and which get `hreflang` metadata. A page
 * translated without being added here is invisible to search; a path added here
 * without a `/ko` route is a 404 in the sitemap. The gate checks both
 * directions.
 *
 * Deliberately NOT here, each for a reason recorded in
 * `docs/analysis/korean-marketing-site-2026-09-21.md` §5:
 *   · `/blog` + 113 posts — translating a post is a content project, not a
 *     string swap, and a machine-drafted post would be published prose.
 *   · `/privacy`, `/terms` — legal text; a mistranslated clause is a
 *     liability, so these want a professional translation or nothing.
 *   · `/invest`, `/developers` — those audiences read English.
 */
export const TRANSLATED_PATHS = [
  "/",
  "/faq",
] as const;

/**
 * ⚠️ THIS ROSTER MUST NOT RUN AHEAD OF THE ROUTES.
 *
 * A path listed here is prefixed by every link that passes through
 * `isTranslatedPath`, so listing `/pricing` before `app/ko/pricing/page.tsx`
 * exists turns the Korean page's own nav into three 404s — reachable in one
 * click from the header, the footer and the hero. Driven and confirmed before
 * this comment was written.
 *
 * Add a path here in the SAME commit that adds its `/ko` route, never earlier.
 * `api/test_adr660_the_interface_speaks_korean.py` holds the pair.
 */

export type TranslatedPath = (typeof TRANSLATED_PATHS)[number];

export function isTranslatedPath(path: string): path is TranslatedPath {
  return (TRANSLATED_PATHS as readonly string[]).includes(path);
}
