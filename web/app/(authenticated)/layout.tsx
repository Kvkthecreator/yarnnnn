import { Suspense } from 'react';
import type { Metadata } from "next";
import { getTranslations } from 'next-intl/server';
import { getRequestUser } from '@/lib/supabase/server';
import { IntlScope } from '@/components/i18n/IntlScope';
import AuthenticatedLayout from '@/components/shell/AuthenticatedLayout';
import { Wordmark } from '@/components/shared/Wordmark';
import { Working } from '@/components/shared/Working';

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
 * ADR-023: Supervisor Desk Architecture
 *
 * Layout for authenticated routes:
 * - Single desk view (one surface at a time)
 * - TP always present at bottom
 * - Domain browser as escape hatch
 *
 * Auth gating: middleware.ts (updateSession) is the SOLE gate — it refreshes
 * the session server-side and redirects unauthenticated requests to
 * /auth/login before this layout renders. We read the user here (server-side,
 * zero client round-trip) only to hand userEmail to the chrome. The shell no
 * longer blocks first paint on a redundant client-side getUser() — the
 * client retains a sign-out *listener* (live invalidation), not a gate.
 */
export default async function Layout({ children }: { children: React.ReactNode }) {
  // Request-cached and shared with the locale resolver (ADR-660 D2): one fetch.
  const user = await getRequestUser();
  // ADR-660 — the fallback's word is resolved HERE, not inside it: a Suspense
  // fallback must render synchronously, so it cannot be an async component
  // that awaits its own translations.
  const t = await getTranslations('shell');

  return (
    <IntlScope>
      <Suspense fallback={<LayoutFallback loading={t('loading')} />}>
        <AuthenticatedLayout userEmail={user?.email ?? undefined}>
          {children}
        </AuthenticatedLayout>
      </Suspense>
    </IntlScope>
  );
}

function LayoutFallback({ loading }: { loading: string }) {
  return (
    <div className="h-screen flex items-center justify-center bg-background">
      <div className="text-center">
        <h1 className="mb-2"><Wordmark className="text-xl" /></h1>
        <Working label={loading} className="text-sm" />
      </div>
    </div>
  );
}
