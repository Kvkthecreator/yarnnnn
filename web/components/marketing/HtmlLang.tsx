"use client";

import { useEffect } from "react";
import type { Locale } from "@/i18n/config";

/**
 * Sets `<html lang>` for a marketing page.
 *
 * `<html>` is written once, by the root layout, and that layout must stay
 * static — reading the pathname there to pick a language would make every
 * route in the app dynamic, which is the tradeoff ADR-660 D3 declined. So the
 * attribute is corrected from inside the page, the same way `LocaleEffects`
 * does it for the authenticated scopes.
 *
 * ⚠️ This runs after hydration, so the SERVED html carries `lang="en"`. For a
 * crawler that is not the signal that matters: Google determines language from
 * the page's content and its `hreflang` alternates, both of which are correct
 * and present in the static output. What this fixes is the ASSISTIVE-TECH
 * story — a screen reader picks its voice from `lang`, and a Korean page
 * announced in an English voice is unusable.
 *
 * If the marketing site ever wants `lang` right in the served bytes, the shape
 * is a route group with its own root layout (`app/(ko)/layout.tsx`), which
 * stays static. That is a larger restructure than this pass, and it is
 * recorded here rather than done silently.
 */
export function HtmlLang({ locale }: { locale: Locale }) {
  useEffect(() => {
    const previous = document.documentElement.lang;
    document.documentElement.lang = locale;
    return () => {
      document.documentElement.lang = previous;
    };
  }, [locale]);
  return null;
}
