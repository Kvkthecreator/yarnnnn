import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import { accountLocale } from "@/i18n/resolve";
import { LocaleEffects } from "./LocaleEffects";

/**
 * ADR-660 D3 — the provider is SCOPED. It mounts in the layouts whose pages a
 * member reads in their own language (`(authenticated)`, `auth/login`,
 * `mcp/auth`) and never in the root layout: resolving a locale reads a cookie,
 * and a cookie read in the root would make every marketing route dynamic.
 *
 * A component that calls `useTranslations` must render inside one of these
 * scopes — outside, it throws.
 */
export async function IntlScope({ children }: { children: React.ReactNode }) {
  const [locale, messages, account] = await Promise.all([
    getLocale(),
    getMessages(),
    accountLocale(),
  ]);
  return (
    <NextIntlClientProvider locale={locale} messages={messages}>
      <LocaleEffects locale={locale} accountLocale={account} />
      {children}
    </NextIntlClientProvider>
  );
}
