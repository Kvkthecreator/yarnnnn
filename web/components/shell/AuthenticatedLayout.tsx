'use client';

/**
 * ADR-037: Chat-First Surface Architecture
 * ADR-063: Four-Layer Model Navigation
 *
 * Navigation model:
 * - Home (/dashboard) = Chat-first experience (TP primary)
 * - Four-layer pages: Memory, Activity, Context, Work (Deliverables)
 * - Settings is meta (not a layer)
 *
 * Navigation structure (ADR-063 aligned):
 * - Agent (home) | Work (Deliverables) | Memory | Context | Activity | Settings
 *
 * Four-Layer Model:
 * - Memory (/memory): What YARNNN knows about you (Profile, Styles, Entries)
 * - Activity (/activity): What YARNNN has done (audit trail)
 * - Context (/context): What's in your platforms (Platforms, Documents)
 * - Work (/deliverables): What YARNNN produces (recurring outputs)
 */

import { useEffect, useState, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { Sparkles, ChevronDown, Settings, Briefcase, Activity, Layers, Brain, Zap } from 'lucide-react';
import { DeskProvider, useDesk } from '@/contexts/DeskContext';
import { TPProvider, useTP } from '@/contexts/TPContext';
import { WorkspaceHeaderProvider, useWorkspaceHeader } from '@/contexts/WorkspaceHeaderContext';
import type { DeskSurface } from '@/types/desk';
import { UserMenu } from './UserMenu';
import { cn } from '@/lib/utils';
import { SetupConfirmModal } from '@/components/modals/SetupConfirmModal';
import { HOME_LABEL, HOME_ROUTE, isHomeRoute } from '@/lib/routes';

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
    <DeskProvider>
      <WorkspaceHeaderProvider>
        <AuthenticatedLayoutInner userEmail={userEmail}>
          {children}
        </AuthenticatedLayoutInner>
      </WorkspaceHeaderProvider>
    </DeskProvider>
  );
}

// =============================================================================
// Navigation Types
// =============================================================================

// ADR-037: Chat-First Navigation
// - Chat is home (dashboard with idle surface)
// - All other items are routes (actual pages, not surfaces)
// - Surfaces are invoked from chat, not from nav

interface RouteItem {
  id: string;
  label: string;
  icon: typeof Sparkles;
  path: string;
}

// ADR-063: Four-Layer Model Navigation + ADR-072: System (Operations)
// Primary workspace: Agent + Work (creation flows through TP chat)
// Supporting pages: Memory, Context, Activity, System, Settings
const DELIVERABLES_ROUTE: RouteItem = { id: 'deliverables', label: 'Work', icon: Briefcase, path: '/deliverables' };

const ROUTE_PAGES: RouteItem[] = [
  { id: 'memory', label: 'Memory', icon: Brain, path: '/memory' },
  { id: 'context', label: 'Context', icon: Layers, path: '/context' },
  { id: 'activity', label: 'Activity', icon: Activity, path: '/activity' },
  { id: 'system', label: 'System', icon: Zap, path: '/system' },
  { id: 'settings', label: 'Settings', icon: Settings, path: '/settings' },
];


// Get route info from pathname
function getRouteFromPathname(pathname: string): RouteItem | null {
  // Check deliverables route first (primary workspace)
  if (pathname === DELIVERABLES_ROUTE.path || pathname.startsWith(DELIVERABLES_ROUTE.path + '/')) {
    return DELIVERABLES_ROUTE;
  }
  // Check supporting route pages
  for (const route of ROUTE_PAGES) {
    if (pathname === route.path || pathname.startsWith(route.path + '/')) {
      return route;
    }
  }
  return null;
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
  const { surface, setSurface, setSurfaceWithHandoff } = useDesk();
  const { header: workspaceHeader } = useWorkspaceHeader();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const toggleNav = useCallback(() => setDropdownOpen((prev) => !prev), []);
  const closeNav = useCallback(() => setDropdownOpen(false), []);

  // Determine navigation context
  const isOnHome = isHomeRoute(pathname);
  const currentRoute = getRouteFromPathname(pathname);

  // Handle surface change from TP tool results (with optional handoff message)
  // ADR-037: For migrated entities, navigate to routes instead of surfaces
  const handleSurfaceChange = useCallback(
    (newSurface: DeskSurface, handoffMessage?: string) => {
      // ADR-037: Route-first navigation for migrated entities
      // ADR-039: Route-first navigation with unified Context page
      switch (newSurface.type) {
        case 'deliverable-list':
          router.push('/deliverables');
          return;
        case 'deliverable-detail':
          router.push(`/deliverables/${newSurface.deliverableId}`);
          return;
        case 'document-list':
          // ADR-039: Documents now live in unified Context page
          router.push('/context?section=documents');
          return;
        case 'document-viewer':
          router.push(`/docs/${newSurface.documentId}`);
          return;
        case 'platform-list':
          // ADR-039: Platforms now live in unified Context page
          router.push('/context?section=platforms');
          return;
        case 'platform-detail':
          // ADR-039: Specific platform page in Context
          router.push(`/context/${newSurface.platform}`);
          return;
        case 'context-browser':
          // ADR-039: Now redirects to unified Context page
          router.push('/context');
          return;
      }

      // For remaining surfaces (work, review, create, etc.), use surface system
      // If not on dashboard, navigate there first
      if (!isHomeRoute(window.location.pathname)) {
        router.push(HOME_ROUTE);
      }
      // Use handoff version if we have a message from TP
      if (handoffMessage) {
        setSurfaceWithHandoff(newSurface, handoffMessage);
      } else {
        setSurface(newSurface);
      }
    },
    [setSurface, setSurfaceWithHandoff, router]
  );

  // Navigate to home (handles both route nav and surface reset)
  const navigateToHome = useCallback(() => {
    if (!isOnHome) {
      router.push(HOME_ROUTE);
    }
    setSurface({ type: 'idle' });
  }, [isOnHome, router, setSurface]);

  // Dropdown close is handled by the backdrop overlay below (no document listener needed)

  // ADR-037: Get current display info based on context
  const getCurrentDisplay = () => {
    if (currentRoute) {
      // On a route page (e.g., /platforms, /docs, /settings)
      return {
        icon: currentRoute.icon,
        label: currentRoute.label,
      };
    }
    // On home route = Agent
    return {
      icon: Sparkles,
      label: HOME_LABEL,
    };
  };

  const display = getCurrentDisplay();
  const CurrentIcon = display.icon;

  // Nav dropdown menu (shared between workspace and non-workspace center slots)
  // Navigate to a route and close the nav dropdown
  const navTo = useCallback((path: string) => {
    router.push(path);
    closeNav();
  }, [router, closeNav]);

  // Nav dropdown rendered as fixed overlay (outside stacking contexts)
  const navDropdownMenu = dropdownOpen && (
    <>
      {/* Invisible backdrop to close on outside click */}
      <div className="fixed inset-0 z-[100]" onClick={closeNav} />
      {/* Menu positioned below the top bar, centered */}
      <div className="fixed top-14 left-1/2 -translate-x-1/2 z-[101] w-48 bg-background border border-border rounded-md shadow-lg py-1">
        <button
          onClick={() => { navigateToHome(); closeNav(); }}
          className={cn(
            'w-full px-3 py-2 text-sm text-left hover:bg-muted transition-colors flex items-center gap-2',
            isOnHome && 'bg-primary/5 text-primary'
          )}
        >
          <Sparkles className="w-4 h-4" />
          {HOME_LABEL}
        </button>
        <button
          onClick={() => navTo(DELIVERABLES_ROUTE.path)}
          className={cn(
            'w-full px-3 py-2 text-sm text-left hover:bg-muted transition-colors flex items-center gap-2',
            currentRoute?.id === DELIVERABLES_ROUTE.id && 'bg-primary/5 text-primary'
          )}
        >
          <Briefcase className="w-4 h-4" />
          {DELIVERABLES_ROUTE.label}
        </button>

        <div className="border-t border-border my-1" />

        {ROUTE_PAGES.map((route) => {
          const Icon = route.icon;
          const isActive = currentRoute?.id === route.id;
          return (
            <button
              key={route.id}
              onClick={() => navTo(route.path)}
              className={cn(
                'w-full px-3 py-2 text-sm text-left hover:bg-muted transition-colors flex items-center gap-2',
                isActive && 'bg-primary/5 text-primary'
              )}
            >
              <Icon className="w-4 h-4" />
              {route.label}
            </button>
          );
        })}
      </div>
    </>
  );

  return (
    <TPProvider onSurfaceChange={handleSurfaceChange}>
      <div className="flex flex-col h-screen bg-background">
        {/* Top Bar - Single unified bar */}
        <header className="h-14 border-b border-border bg-background flex items-center justify-between px-4 shrink-0">
          {/* Left: Logo — plain home link */}
          <div className="flex items-center shrink-0">
            <button
              onClick={navigateToHome}
              className="hover:opacity-80 transition-opacity"
            >
              <span className="text-xl font-brand">yarnnn</span>
            </button>
          </div>

          {/* Center: workspace header or page label + nav chevron */}
          <div className="flex-1 flex items-center justify-center min-w-0 mx-4">
            {workspaceHeader ?? (
              <div className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-muted-foreground font-medium">
                <CurrentIcon className="w-4 h-4" />
                <span>{display.label}</span>
              </div>
            )}
            <button
              onClick={toggleNav}
              className="p-1 text-muted-foreground hover:text-foreground transition-colors shrink-0"
            >
              <ChevronDown className={cn(
                'w-3.5 h-3.5 transition-transform',
                dropdownOpen && 'rotate-180'
              )} />
            </button>
          </div>

          {/* Right: User menu only */}
          <div className="shrink-0">
            <UserMenu email={userEmail} />
          </div>
        </header>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>

      {/* Nav dropdown — rendered outside header to avoid stacking context issues */}
      {navDropdownMenu}

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
