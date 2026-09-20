"use client";

import { useEffect } from "react";
import { createClient } from "@/lib/supabase/client";
import { LOCALE_METADATA_KEY, isLocale, type Locale } from "@/i18n/config";
import { readLocaleCookie, writeLocaleCookie } from "./locale-cookie";

/**
 * What a scoped provider cannot do from the server (ADR-660 D2/D3):
 *
 * - `<html lang>` lives in the root layout, which must stay static, so the
 *   attribute is set from inside the scope.
 * - Adoption: a visitor who chose a language on the sign-in page carries it as
 *   a cookie. Their first signed-in render writes it to an account that has no
 *   preference yet, so it follows them to their next device. An account that
 *   already has one is never overwritten from a cookie.
 * - The reverse: when the account HAS a preference, the device cookie is brought
 *   into line with it. Found by driving it — a member who switched to English on
 *   one device was rendered English on the other (the account outranks the
 *   cookie), but that device's cookie still said Korean, so signing out there
 *   greeted them in the language they had just left.
 */
export function LocaleEffects({
  locale,
  accountLocale,
}: {
  locale: Locale | string;
  accountLocale: Locale | null;
}) {
  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  useEffect(() => {
    if (accountLocale) {
      if (readLocaleCookie() !== accountLocale) writeLocaleCookie(accountLocale);
      return;
    }
    const device = readLocaleCookie();
    if (!isLocale(device)) return;
    const supabase = createClient();
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user || user.user_metadata?.[LOCALE_METADATA_KEY]) return;
      void supabase.auth.updateUser({ data: { [LOCALE_METADATA_KEY]: device } });
    });
  }, [accountLocale]);

  return null;
}
