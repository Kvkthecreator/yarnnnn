import { Suspense } from 'react';
import type { Metadata } from "next";
import { createClient } from '@/lib/supabase/server';
import AuthenticatedLayout from '@/components/shell/AuthenticatedLayout';

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
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <Suspense fallback={<LayoutFallback />}>
      <AuthenticatedLayout userEmail={user?.email ?? undefined}>
        {children}
      </AuthenticatedLayout>
    </Suspense>
  );
}

function LayoutFallback() {
  return (
    <div className="h-screen flex items-center justify-center bg-background">
      <div className="text-center">
        <h1 className="text-xl font-brand mb-2">yarnnn</h1>
        <p className="text-muted-foreground text-sm">Loading...</p>
      </div>
    </div>
  );
}
