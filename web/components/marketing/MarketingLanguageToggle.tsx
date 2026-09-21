"use client";

import Link from "next/link";
import { Globe } from "lucide-react";
import { LOCALES, LOCALE_ENDONYMS, DEFAULT_LOCALE, type Locale } from "@/i18n/config";
import { localePath } from "@/lib/marketing/locale";

/**
 * The marketing language control — a LINK to the other language, not a switch.
 *
 * `components/i18n/LanguageSwitcher.tsx` is the app's control and stays as it
 * is: signed in, a language is a property of the human (ADR-660 D2), so it
 * writes the account and the device cookie and refreshes in place. That is the
 * right shape there and the wrong one here.
 *
 * On marketing the language IS the address. `/ko/pricing` is a different page
 * from `/pricing` — separately prerendered, separately indexed, shareable as
 * itself. So switching languages is navigation, and this renders an anchor.
 * Consequences that follow, and are the point of it:
 *
 *   · no client state, no refresh, no cookie write;
 *   · a crawler FOLLOWS it, so the Korean page is discoverable from the
 *     English one by an ordinary link, not only by `hreflang`;
 *   · it cannot record a guess as a choice (ADR-660 D2) — the visitor's
 *     navigation IS the choice.
 *
 * ── Why ONE link and not a list of languages ──────────────────────────────
 * The first version rendered every locale as `English · 한국어`, the current
 * one inert. In a nav that already carries five links plus Sign In it read as
 * two more nav items, and it made the reader work out which of the two they
 * were already in. With exactly two languages the useful control is the one
 * they are NOT in: a globe and the other language's endonym, which is what
 * two-language sites converge on. The globe carries the meaning when the label
 * is in a script the reader cannot read.
 *
 * If a third language is ever added this must become a MENU — with three or
 * more, "the other one" stops being a thing. The ADR-660 gate asserts the
 * two-language assumption, so the day that roster grows this file is named
 * rather than left silently wrong.
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
  // With two locales there is exactly one "other". See the note above before
  // adding a third — this becomes a menu, not a longer sentence.
  const other = LOCALES.find((l) => l !== locale) ?? DEFAULT_LOCALE;

  const tone = inverted
    ? "border-white/15 text-white/60 hover:border-white/30 hover:text-white"
    : "border-[#1a1a1a]/15 text-[#1a1a1a]/55 hover:border-[#1a1a1a]/25 hover:text-[#1a1a1a]";

  return (
    <Link
      href={localePath(path, other)}
      hrefLang={other}
      // The visible label is the other language's own name, which a screen
      // reader set to the CURRENT language would mispronounce. Naming the
      // link explicitly keeps the control legible either way.
      aria-label={LOCALE_ENDONYMS[other]}
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm transition-colors ${tone} ${className}`}
    >
      <Globe className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      <span>{LOCALE_ENDONYMS[other]}</span>
    </Link>
  );
}
