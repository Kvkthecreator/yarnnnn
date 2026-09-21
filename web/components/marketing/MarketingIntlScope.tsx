import { NextIntlClientProvider } from "next-intl";
import { DEFAULT_LOCALE, type Locale } from "@/i18n/config";

type Messages = { [key: string]: string | Messages };

/** A fixed instant — see the provider below for why it is passed at all. */
const STATIC_NOW = new Date(0);

/** `over` laid on `base`, key by key — the same partial-catalog rule as `i18n/request.ts`. */
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
 * The marketing provider — a FIFTH scope, and the only one whose locale is an
 * argument rather than a lookup.
 *
 * ADR-660 D3's four scopes (`(authenticated)`, `auth/login`, `mcp/auth`,
 * `admin`) all resolve the locale by reading a cookie and the account, through
 * `i18n/request.ts`. That read is what makes a route dynamic, and it is exactly
 * why the provider was kept out of the root layout: every marketing route is
 * statically prerendered, and ADR-660 guarded that on the build's route table
 * four times.
 *
 * So this scope does not resolve anything. The locale comes from the ROUTE
 * (`/ko/pricing` is Korean because of where it is), is passed in, and the
 * catalog is imported directly rather than through `getMessages()` — which
 * would call the request config and reintroduce the cookie read. A page under
 * this provider therefore prerenders, in both languages, with no request state
 * consulted at all.
 *
 * The English fallback is preserved (ADR-660 D4): a missing `ko` key renders
 * English rather than throwing, so a half-translated page reads as English and
 * never as a broken one.
 *
 * ⚠️ `useTranslations` throws outside a provider. Any component rendered by a
 * marketing page that calls it must be reachable ONLY from inside this scope —
 * the same hazard ADR-660 D8 made mechanical with `SCOPELESS_BY_RULING`.
 * `LandingHeader` and `LandingFooter` are shared by untranslated marketing
 * pages too, so they take their words as PROPS and call no hook.
 */
export async function MarketingIntlScope({
  locale,
  children,
}: {
  locale: Locale;
  children: React.ReactNode;
}) {
  const base = (await import(`@/messages/${DEFAULT_LOCALE}.json`)).default as Messages;
  const messages =
    locale === DEFAULT_LOCALE
      ? base
      : layer(base, (await import(`@/messages/${locale}.json`)).default as Messages);

  return (
    <NextIntlClientProvider
      locale={locale}
      messages={messages}
      // `now` and `timeZone` are supplied EXPLICITLY, and that is what keeps
      // this page static. Left out, the provider asks the request config for
      // them, which opts the route into dynamic rendering — measured: `/`
      // fell from ○ to ƒ. Marketing renders no live times, so a fixed epoch
      // and UTC are honest; anything date-shaped here would be a bug anyway.
      now={STATIC_NOW}
      timeZone="UTC"
    >
      {children}
    </NextIntlClientProvider>
  );
}
