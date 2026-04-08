'use client';

/**
 * ADR-037: Chat-First Surface Architecture
 *
 * Navigation model:
 * Primary:   Orchestrator
 * Secondary: Context | Activity | Settings
 *
 * Dashboard collapsed into Orchestrator (single landing page).
 * Agent pages still accessible via direct URL.
 * Context = platform connections + uploaded files (was "Sources").
 */

import { useEffect, useState, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { DeskProvider, useDesk } from '@/contexts/DeskContext';
import { TPProvider, useTP } from '@/contexts/TPContext';
import { BreadcrumbProvider } from '@/contexts/BreadcrumbContext';
import type { DeskSurface } from '@/types/desk';
import { UserMenu } from './UserMenu';
import { ToggleBar } from './ToggleBar';
// ADR-167 v2: GlobalBreadcrumb DELETED. Each surface renders <PageHeader />
// inside its own content area instead of a separate bar between header and main.
import { SetupConfirmModal } from '@/components/modals/SetupConfirmModal';
import { HOME_ROUTE, isHomeRoute } from '@/lib/routes';

interface AuthenticatedLayoutProps {
  children: React.ReactNode;
}

export default function AuthenticatedLayout({ children }: AuthenticatedLayoutProps) {
  const [userEmail, setUserEmail] = useState<string | undefined>();
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const supabase = createClient();

  useEffect(() => {
    const loginRedirect = () => {
      const next = `${window.location.pathname}${window.location.search}`;
      router.replace(`/auth/login?next=${encodeURIComponent(next)}`);
    };

    const checkAuth = async () => {
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) {
        loginRedirect();
        return;
      }

      setUserEmail(user.email ?? undefined);
      setLoading(false);
    };

    checkAuth();

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_OUT' || !session) {
        loginRedirect();
      }
    });

    return () => subscription.unsubscribe();
  }, [router, supabase.auth]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-brand mb-2">yarnnn</h1>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <BreadcrumbProvider>
      <DeskProvider>
        <AuthenticatedLayoutInner userEmail={userEmail}>
          {children}
        </AuthenticatedLayoutInner>
      </DeskProvider>
    </BreadcrumbProvider>
  );
}

// Inner component that can use desk context
function AuthenticatedLayoutInner({
  children,
  userEmail,
}: {
  children: React.ReactNode;
  userEmail?: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { setSurface, setSurfaceWithHandoff } = useDesk();

  const isOnHome = isHomeRoute(pathname);

  // Handle surface change from TP tool results
  const handleSurfaceChange = useCallback(
    (newSurface: DeskSurface, handoffMessage?: string) => {
      switch (newSurface.type) {
        case 'agent-list':
          router.push('/agents');
          return;
        case 'agent-detail':
          router.push(`/agents?agent=${newSurface.agentId}`);
          return;
        case 'document-list':
          router.push('/context');
          return;
        case 'document-viewer':
          router.push(`/docs/${newSurface.documentId}`);
          return;
        case 'platform-list':
          router.push('/context');
          return;
        case 'platform-detail':
          router.push(`/context/${newSurface.platform}`);
          return;
        case 'context-browser':
          router.push('/context');
          return;
        case 'task-detail':
          router.push(`/agents`);
          return;
      }

      // For remaining surfaces, use surface system
      if (handoffMessage) {
        setSurfaceWithHandoff(newSurface, handoffMessage);
      } else {
        setSurface(newSurface);
      }
    },
    [setSurface, setSurfaceWithHandoff, router]
  );

  const navigateToHome = useCallback(() => {
    // Logo click navigates to the appropriate home based on maturity
    if (!isOnHome) {
      router.push(HOME_ROUTE);
    }
  }, [isOnHome, router]);

  return (
    <TPProvider onSurfaceChange={handleSurfaceChange}>
      <div className="flex flex-col h-screen bg-background">
        {/* Top Bar */}
        <header className="h-14 border-b border-border bg-background flex items-center justify-between px-4 shrink-0">
          {/* Left: Logo */}
          <div className="flex items-center min-w-0">
            <button
              onClick={navigateToHome}
              className="text-xl font-brand hover:opacity-80 transition-opacity shrink-0"
            >
              yarnnn
            </button>
          </div>

          {/* Center: Toggle bar */}
          <ToggleBar />

          {/* Right: User menu */}
          <UserMenu email={userEmail} />
        </header>

        {/* Main content. ADR-167 v2: each surface renders its own <PageHeader />
            inside the content area — there is no separate breadcrumb bar. */}
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>

      {/* Setup Confirmation Modal - rendered inside TPProvider */}
      <SetupConfirmModalWrapper />
    </TPProvider>
  );
}

// Separate component to access TPContext inside TPProvider
function SetupConfirmModalWrapper() {
  const { setupConfirmModal, closeSetupConfirmModal } = useTP();

  return (
    <SetupConfirmModal
      open={setupConfirmModal.open}
      data={setupConfirmModal.data}
      onClose={closeSetupConfirmModal}
    />
  );
}
