"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Globe } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { LOCALES, LOCALE_ENDONYMS, LOCALE_METADATA_KEY, isLocale, type Locale } from "@/i18n/config";
import { writeLocaleCookie } from "./locale-cookie";

/**
 * ADR-660 D2 — the one control that changes a language. It writes the device
 * cookie always, and the account when there is one: signed out (the sign-in
 * page) the cookie is all there is, and the first signed-in render adopts it.
 *
 * The account is written BEFORE the refresh. The resolver ranks the account
 * above the cookie, so refreshing first would re-render in the old language.
 */
export function LanguageSwitcher({
  variant = "field",
  className = "",
}: {
  /** `field` — a labelled row for Settings. `inline` — a bare control for the sign-in page. */
  variant?: "field" | "inline";
  className?: string;
}) {
  const t = useTranslations("language");
  const active = useLocale();
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [failed, setFailed] = useState(false);

  async function choose(next: Locale) {
    if (next === active) return;
    setFailed(false);
    writeLocaleCookie(next);
    const supabase = createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (user) {
      const { error } = await supabase.auth.updateUser({ data: { [LOCALE_METADATA_KEY]: next } });
      if (error) {
        // The account still says the old language and outranks the cookie, so a
        // refresh would change nothing. Say so instead of looking like it worked.
        writeLocaleCookie(isLocale(active) ? active : next);
        setFailed(true);
        return;
      }
    }
    startTransition(() => router.refresh());
  }

  const select = (
    <select
      aria-label={t("label")}
      value={active}
      disabled={pending}
      onChange={(event) => {
        if (isLocale(event.target.value)) void choose(event.target.value);
      }}
      className={
        variant === "inline"
          ? "bg-transparent text-sm text-[#1a1a1a]/70 hover:text-[#1a1a1a] focus:outline-none cursor-pointer"
          : "h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-60"
      }
    >
      {LOCALES.map((locale) => (
        // Endonyms are not translated: a reader finds their language written in it.
        <option key={locale} value={locale}>
          {LOCALE_ENDONYMS[locale]}
        </option>
      ))}
    </select>
  );

  if (variant === "inline") {
    return (
      <label className={`inline-flex items-center gap-1.5 ${className}`}>
        <Globe className="w-3.5 h-3.5 text-[#1a1a1a]/50" aria-hidden />
        {select}
      </label>
    );
  }

  return (
    <div className={className}>
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-medium">{t("label")}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{t("help")}</p>
        </div>
        {select}
      </div>
      {failed && <p className="text-xs text-destructive mt-2">{t("saveFailed")}</p>}
    </div>
  );
}
