import { Suspense } from 'react';
import type { Metadata } from "next";
import { ShellIntlScope } from '@/components/i18n/ShellIntlScope';
import AuthenticatedLayout from '@/components/shell/AuthenticatedLayout';
import { AuthGate } from '@/components/shell/AuthGate';
import { Wordmark } from '@/components/shared/Wordmark';
import { FallbackWait } from '@/components/shell/FallbackWait';

export const metadata: Metadata = {
  title: {
    default: "App",
    template: "%s | yarnnn",
  },
  robots: {
    index: false,
    follow: false,
    noarchive: true,
    nosnippet: true,
    noimageindex: true,
  },
};

/**
 * The authenticated layout for the SHELL build (ADR-661 §8 step 4).
 *
 * `layout.web.tsx` beside this file is the WEB build's layout and is the one
 * that changes when product behaviour changes; the `.web` suffix is a route
 * extension only the web build lists (`pageExtensions` in `next.config.js`),
 * so exactly one of the two exists in any given build. They are a PAIR and
 * must stay one: the difference between them is only where two facts come
 * from, never what the shell renders.
 *
 * The two differences, and both are forced by the absence of a request:
 *
 * 1. **No `getRequestUser()`.** The web layout reads the user server-side to
 *    hand `userEmail` to the chrome. That is a `cookies()` read, which made
 *    all 41 authenticated routes un-exportable (measured). Here no email is
 *    passed, and `ShellChromeProvider` reads it from the session the client
 *    already holds (§7n — until then this sentence described a fallback that
 *    did not exist, and the avatar read `?`).
 *
 * 2. **`ShellIntlScope`, not `IntlScope`.** Same reason: `IntlScope` awaits
 *    `getLocale()`, which runs ADR-660 D2's chain through `cookies()` and
 *    `headers()`. The shell scope runs the same chain from
 *    `resolveLocaleClient` (§8 step 2).
 *
 * Everything else — the Suspense boundary, `AuthGate`, the fallback, the
 * component tree below — is identical by construction, because it is the same
 * components in the same order.
 *
 * ⚠️ A change to the web layout's TREE belongs here too. The gate
 * (`api/test_adr661_*.py`) asserts both mount `AuthGate` and a scope, which
 * catches the drift that matters most; it cannot catch every divergence, so
 * treat the pair as one file with two heads.
 */
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <ShellIntlScope>
      <Suspense fallback={<LayoutFallback />}>
        <AuthGate fallback={<LayoutFallback />}>
          <AuthenticatedLayout>{children}</AuthenticatedLayout>
        </AuthGate>
      </Suspense>
    </ShellIntlScope>
  );
}

/**
 * The fallback's word comes from the catalog like every other (ADR-660), but
 * it cannot be resolved the way the web layout resolves it: there `t('loading')`
 * is awaited on the SERVER, and a Suspense fallback must render synchronously.
 *
 * So this is a client component that reads the hook, and it sits INSIDE
 * `ShellIntlScope` — which is what makes the hook legal here. `useTranslations`
 * throws outside a provider, and the scope is mounted above this boundary.
 */
function LayoutFallback() {
  return (
    <div className="h-screen flex items-center justify-center bg-background">
      <div className="text-center">
        <h1 className="mb-2"><Wordmark className="text-xl" /></h1>
        <FallbackWait />
      </div>
    </div>
  );
}
