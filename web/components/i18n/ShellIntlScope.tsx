'use client';

/**
 * ShellIntlScope — `IntlScope` for a build with no request (ADR-661 §8 step 4).
 *
 * `IntlScope` is an async SERVER component: it awaits `getLocale()`, which runs
 * ADR-660 D2's chain through `cookies()` and `headers()`. Under
 * `output: 'export'` there is no request, so that read makes every authenticated
 * route un-exportable — measured, it was the blocker on all 41 of them.
 *
 * This is the same scope resolved in the client, using `resolveLocaleClient`
 * (§8 step 2 — same order, same matcher, client-visible sources). It is NOT a
 * second locale policy; the policy lives in `i18n/resolve-client.ts` and both
 * halves of the product read it.
 *
 * WHAT DIFFERS, and why it is acceptable here:
 *
 * - **The catalogs are bundled, not fetched per request.** Both are imported
 *   statically (366KB of JSON), because a packaged app has no server to ask and
 *   should not need a network round-trip to know its own words. On the web the
 *   request config still loads one catalog per request; only the shell pays
 *   this cost, and it pays it once at startup.
 * - **The first frame is resolved, not guessed.** The account's preference is
 *   read from the session the client already holds, so there is no flash of
 *   English before Korean — the chain's step 1 is available before first paint,
 *   exactly as it is on the server.
 * - **`now`/`timeZone` are pinned.** `NextIntlClientProvider` asks the request
 *   config for them otherwise, which is the dependency that made a marketing
 *   route dynamic once before (ADR-660). Pinning them keeps this component
 *   free of any request concept at all.
 */

import { useEffect, useMemo, useState } from 'react';
import { NextIntlClientProvider } from 'next-intl';
import { createClient } from '@/lib/supabase/client';
import { resolveLocaleClient, accountLocaleFrom } from '@/i18n/resolve-client';
import { DEFAULT_LOCALE, type Locale } from '@/i18n/config';
import { LocaleEffects } from './LocaleEffects';
import en from '@/messages/en.json';
import ko from '@/messages/ko.json';

type Messages = { [key: string]: string | Messages };

const CATALOGS: Record<Locale, Messages> = {
  en: en as Messages,
  ko: ko as Messages,
};

/** `over` laid on `base`, key by key — the same partial-catalog rule as
 *  `i18n/request.ts`, so a missing Korean key falls back to English rather
 *  than throwing (ADR-660 D4). */
function layer(base: Messages, over: Messages): Messages {
  const out: Messages = { ...base };
  for (const [key, value] of Object.entries(over)) {
    const under = out[key];
    out[key] =
      typeof value === 'object' && value !== null && typeof under === 'object' && under !== null
        ? layer(under as Messages, value as Messages)
        : value;
  }
  return out;
}

export function ShellIntlScope({ children }: { children: React.ReactNode }) {
  // Resolved synchronously from cookie/navigator so the first frame is already
  // in the right language; the account's preference lands a tick later and
  // outranks it (step 1 of the chain).
  const [locale, setLocale] = useState<Locale>(() =>
    typeof window === 'undefined' ? DEFAULT_LOCALE : resolveLocaleClient(),
  );
  const [account, setAccount] = useState<Locale | null>(null);

  useEffect(() => {
    let active = true;
    createClient()
      .auth.getSession()
      .then(({ data: { session } }) => {
        if (!active) return;
        const metadata = session?.user?.user_metadata;
        setAccount(accountLocaleFrom(metadata));
        setLocale(resolveLocaleClient(metadata));
      });
    return () => {
      active = false;
    };
  }, []);

  const messages = useMemo(
    () =>
      locale === DEFAULT_LOCALE
        ? CATALOGS[DEFAULT_LOCALE]
        : layer(CATALOGS[DEFAULT_LOCALE], CATALOGS[locale]),
    [locale],
  );

  return (
    <NextIntlClientProvider
      locale={locale}
      messages={messages}
      timeZone="UTC"
      now={new Date(0)}
    >
      <LocaleEffects locale={locale} accountLocale={account} />
      {children}
    </NextIntlClientProvider>
  );
}
