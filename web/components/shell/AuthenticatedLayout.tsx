'use client';

/**
 * AuthenticatedLayout — ADR-297 shell.
 *
 * Per ADR-297 D7, the shell carries:
 *   - Top chrome: brand mark (left), launcher button + user menu (right)
 *   - Bottom chrome: persistent Dock of operator-pinned surfaces
 *   - Center: surface content (delivered via children)
 *
 * The 4-tab nav (ADR-205 F1 / ADR-214 — Feed · Work · Agents · Files)
 * is DELETED. Navigation is summon-first via the Launcher overlay; the
 * Dock holds operator-pinned defaults (Feed by default, operator pins
 * more from the Launcher).
 *
 * Home behavior (D6): logo click navigates to the operator's last-active
 * surface (macOS-natural), not a fixed home route. First-time operators
 * land on Feed (the only default-pinned surface). The legacy HOME_ROUTE
 * constant survives but is overridden by the last-active preference
 * when set.
 */

import { useEffect, useState, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { DeskProvider, useDesk } from '@/contexts/DeskContext';
import { NarrativeProvider, useNarrative } from '@/contexts/NarrativeContext';
import { BreadcrumbProvider } from '@/contexts/BreadcrumbContext';
import type { DeskSurface } from '@/types/desk';
import { UserMenu } from './UserMenu';
import { Dock } from './Dock';
import { Launcher } from './Launcher';
import { LauncherButton } from './LauncherButton';
import { useComposition } from '@/lib/compositor/useComposition';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { SetupConfirmModal } from '@/components/modals/SetupConfirmModal';
import { HOME_ROUTE } from '@/lib/routes';

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
  const { data: composition } = useComposition();
  const { pinned, pin, unpin, recordVisit, lastActive } = useSurfacePreferences();
  const [launcherOpen, setLauncherOpen] = useState(false);

  // Build bundle title map from active_bundles for Launcher tier headers.
  const bundleTitleBySlug: Record<string, string> = {};
  composition.active_bundles.forEach((b) => {
    if (b.slug && b.title) bundleTitleBySlug[b.slug] = b.title;
  });

  // ADR-297 D6: record visits to drive last-active home behavior. Compute
  // the active surface slug by matching the current pathname against the
  // surface registry's routes (longest-prefix wins).
  useEffect(() => {
    if (!composition.surfaces || composition.surfaces.length === 0) return;
    const sorted = [...composition.surfaces].sort(
      (a, b) => b.route.length - a.route.length
    );
    const match = sorted.find(
      (s) => pathname === s.route || pathname.startsWith(s.route + '/')
    );
    if (match) recordVisit(match.slug);
  }, [pathname, composition.surfaces, recordVisit]);

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
    // ADR-297 D6: logo click navigates to operator's last-active surface
    // (macOS-natural). Resolves the slug to a route via the compositor
    // registry; falls back to HOME_ROUTE if the registry isn't loaded
    // yet or the slug is unknown.
    const surface = composition.surfaces?.find((s) => s.slug === lastActive);
    const target = surface?.route || HOME_ROUTE;
    if (pathname !== target) router.push(target);
  }, [router, pathname, composition.surfaces, lastActive]);

  return (
    <NarrativeProvider onSurfaceChange={handleSurfaceChange}>
      <div className="flex flex-col h-screen bg-background">
        {/* Top Bar — ADR-297 D7: brand mark (left) + launcher + user menu (right). */}
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

          {/* Right: Launcher + User menu */}
          <div className="flex items-center gap-1">
            <LauncherButton onClick={() => setLauncherOpen(true)} />
            <UserMenu email={userEmail} />
          </div>
        </header>

        {/* Main content. ADR-167 v2: each surface renders its own <PageHeader />
            inside the content area — there is no separate breadcrumb bar. */}
        <main className="flex-1 min-h-0 overflow-hidden">{children}</main>

        {/* ADR-297 D5: persistent dock of pinned surfaces (bottom). */}
        <Dock surfaces={composition.surfaces || []} pinned={pinned} />
      </div>

      {/* ADR-297 D4: summon-first launcher overlay. */}
      <Launcher
        open={launcherOpen}
        onClose={() => setLauncherOpen(false)}
        surfaces={composition.surfaces || []}
        pinned={pinned}
        onPin={pin}
        onUnpin={unpin}
        bundleTitleBySlug={bundleTitleBySlug}
      />

      {/* Setup Confirmation Modal - rendered inside NarrativeProvider */}
      <SetupConfirmModalWrapper />
    </NarrativeProvider>
  );
}

// Separate component to access NarrativeContext inside NarrativeProvider
function SetupConfirmModalWrapper() {
  const { setupConfirmModal, closeSetupConfirmModal } = useNarrative();

  return (
    <SetupConfirmModal
      open={setupConfirmModal.open}
      data={setupConfirmModal.data}
      onClose={closeSetupConfirmModal}
    />
  );
}
