"use client";

import Link from "next/link";
import { LOCALES, LOCALE_ENDONYMS, type Locale } from "@/i18n/config";
import { localePath } from "@/lib/marketing/locale";

/**
 * The marketing language control — a LINK between two real URLs, not a cookie
 * write.
 *
 * `components/i18n/LanguageSwitcher.tsx` is the app's control and stays as it
 * is: signed in, a language is a property of the human (ADR-660 D2), so it
 * writes the account and the device cookie and refreshes in place. That is the
 * right shape there and the wrong one here.
 *
 * On marketing the language IS the address. `/ko/pricing` is a different page
 * from `/pricing` — separately prerendered, separately indexed, and shareable
 * as itself. So switching languages is navigation, and this renders two
 * anchors. Consequences that follow from that and are the point of it:
 *
 *   · it is a server component with no state, no `useTransition`, no client JS;
 *   · a crawler follows it, so the Korean page is discoverable from the English
 *     one by an ordinary link, not only by `hreflang`;
 *   · it cannot write a cookie, so it cannot record a guess as a choice
 *     (ADR-660 D2) — the visitor's navigation IS the choice.
 *
 * Endonyms are never translated: a Korean reader looks for 한국어.
 */
export function MarketingLanguageToggle({
  locale,
  path,
  className = "",
  inverted = false,
}: {
  /** The locale this page is rendered in. */
  locale: Locale;
  /** This page's canonical (English, unprefixed) path — e.g. `/pricing`. */
  path: string;
  className?: string;
  /** On a dark hero, where the muted-foreground tokens have no contrast. */
  inverted?: boolean;
}) {
  const idle = inverted ? "text-white/50 hover:text-white" : "text-[#1a1a1a]/40 hover:text-[#1a1a1a]";
  const live = inverted ? "text-white" : "text-[#1a1a1a]";

  return (
    <div className={`flex items-center gap-2 text-sm ${className}`}>
      {LOCALES.map((option, index) => (
        <span key={option} className="flex items-center gap-2">
          {index > 0 && (
            <span aria-hidden="true" className={inverted ? "text-white/20" : "text-[#1a1a1a]/20"}>
              ·
            </span>
          )}
          {option === locale ? (
            // The current language is not a link to itself. `aria-current` is
            // how a screen reader is told which one is live, since colour alone
            // would not carry it.
            <span aria-current="true" className={live}>
              {LOCALE_ENDONYMS[option]}
            </span>
          ) : (
            <Link
              href={localePath(path, option)}
              hrefLang={option}
              className={`${idle} transition-colors`}
            >
              {LOCALE_ENDONYMS[option]}
            </Link>
          )}
        </span>
      ))}
    </div>
  );
}
