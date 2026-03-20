'use client';

/**
 * ADR-037: Chat-First Surface Architecture
 *
 * Navigation model (simplified 2026-03-19):
 * Primary:   Dashboard | Orchestrator | Projects
 * Secondary: Context | Activity | Settings
 *
 * Agents hidden from nav (ADR-122: all agents belong to projects).
 * Agent pages still accessible via direct URL and project cross-links.
 * Context = platform connections + uploaded files (was "Sources").
 */

import { useEffect, useState, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { Command, ChevronDown, Settings, Briefcase, Activity, Layers, LayoutDashboard } from 'lucide-react';
import { DeskProvider, useDesk } from '@/contexts/DeskContext';
import { TPProvider, useTP } from '@/contexts/TPContext';
import type { DeskSurface } from '@/types/desk';
import { UserMenu } from './UserMenu';
import { cn } from '@/lib/utils';
import { SetupConfirmModal } from '@/components/modals/SetupConfirmModal';
import { HOME_LABEL, HOME_ROUTE, isHomeRoute, ORCHESTRATOR_ROUTE, ORCHESTRATOR_LABEL, isOrchestratorRoute, PROJECTS_ROUTE, PROJECTS_LABEL } from '@/lib/routes';

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
      <AuthenticatedLayoutInner userEmail={userEmail}>
        {children}
      </AuthenticatedLayoutInner>
    </DeskProvider>
  );
}

// =============================================================================
// Navigation Types
// =============================================================================

interface RouteItem {
  id: string;
  label: string;
  icon: typeof Command;
  path: string;
}

// Primary: Dashboard (home) + Orchestrator + Projects
const ORCHESTRATOR_NAV: RouteItem = { id: 'orchestrator', label: ORCHESTRATOR_LABEL, icon: Command, path: ORCHESTRATOR_ROUTE };
const PROJECTS_ROUTE_NAV: RouteItem = { id: 'projects', label: PROJECTS_LABEL, icon: Briefcase, path: PROJECTS_ROUTE };

// Secondary: Context + Activity + Settings
// Context = platform connections + uploaded files (was "Sources")
// Agents hidden from nav — accessible via project cross-links and direct URL
const SECONDARY_PAGES: RouteItem[] = [
  { id: 'context', label: 'Context', icon: Layers, path: '/context' },
  { id: 'activity', label: 'Activity', icon: Activity, path: '/activity' },
  { id: 'settings', label: 'Settings', icon: Settings, path: '/settings' },
];

// Agents route kept for pathname matching (still accessible, just not in nav)
const AGENTS_ROUTE: RouteItem = { id: 'agents', label: 'Agents', icon: Briefcase, path: '/agents' };

// All primary routes for pathname matching
const PRIMARY_ROUTES = [ORCHESTRATOR_NAV, PROJECTS_ROUTE_NAV];

// Get route info from pathname
function getRouteFromPathname(pathname: string): RouteItem | null {
  for (const route of PRIMARY_ROUTES) {
    if (pathname === route.path || pathname.startsWith(route.path + '/')) {
      return route;
    }
  }
  for (const route of SECONDARY_PAGES) {
    if (pathname === route.path || pathname.startsWith(route.path + '/')) {
      return route;
    }
  }
  // Agents: hidden from nav but still accessible via direct URL / cross-links
  if (pathname === AGENTS_ROUTE.path || pathname.startsWith(AGENTS_ROUTE.path + '/')) {
    return AGENTS_ROUTE;
  }
  // Legacy routes still accessible but not in nav (memory, system)
  if (pathname.startsWith('/memory')) return { id: 'settings', label: 'Settings', icon: Settings, path: '/settings' };
  if (pathname.startsWith('/system')) return { id: 'settings', label: 'Settings', icon: Settings, path: '/settings' };
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
  const [dropdownOpen, setDropdownOpen] = useState(false);

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
        case 'agent-list':
          router.push('/agents');
          return;
        case 'agent-detail':
          router.push(`/agents/${newSurface.agentId}`);
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
      // If not on orchestrator, navigate there first (surfaces live on the chat page)
      if (!isOrchestratorRoute(window.location.pathname)) {
        router.push(ORCHESTRATOR_ROUTE);
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

  // Navigate to home (dashboard)
  const navigateToHome = useCallback(() => {
    if (!isOnHome) {
      router.push(HOME_ROUTE);
    }
  }, [isOnHome, router]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = () => setDropdownOpen(false);
    if (dropdownOpen) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [dropdownOpen]);

  // Get current display info based on context
  const getCurrentDisplay = () => {
    if (currentRoute) {
      return {
        icon: currentRoute.icon,
        label: currentRoute.label,
      };
    }
    // On home route = Dashboard
    return {
      icon: LayoutDashboard,
      label: HOME_LABEL,
    };
  };

  const display = getCurrentDisplay();
  const CurrentIcon = display.icon;

  return (
    <TPProvider onSurfaceChange={handleSurfaceChange}>
      <div className="flex flex-col h-screen bg-background">
        {/* Top Bar - Single unified bar */}
        <header className="h-14 border-b border-border bg-background flex items-center justify-between px-4 shrink-0">
          {/* Left: Logo - always navigates home */}
          <div className="flex items-center gap-4">
            <button
              onClick={navigateToHome}
              className="text-xl font-brand hover:opacity-80 transition-opacity"
            >
              yarnnn
            </button>
          </div>

          {/* Center: Current context with dropdown to navigate */}
          <div className="relative">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setDropdownOpen(!dropdownOpen);
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md bg-primary/10 text-primary font-medium"
            >
              <CurrentIcon className="w-4 h-4" />
              <span>{display.label}</span>
              <ChevronDown className={cn(
                'w-3 h-3 opacity-50 transition-transform',
                dropdownOpen && 'rotate-180'
              )} />
            </button>

            {/* Dropdown: Navigation options */}
            {dropdownOpen && (
              <div className="absolute top-full left-1/2 -translate-x-1/2 mt-1 w-48 bg-background border border-border rounded-md shadow-lg py-1 z-50">
                {/* Primary: Dashboard + Orchestrator + Projects */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (!isOnHome) {
                      router.push(HOME_ROUTE);
                    }
                    setDropdownOpen(false);
                  }}
                  className={cn(
                    'w-full px-3 py-2 text-sm text-left hover:bg-muted transition-colors flex items-center gap-2',
                    isOnHome && 'bg-primary/5 text-primary'
                  )}
                >
                  <LayoutDashboard className="w-4 h-4" />
                  {HOME_LABEL}
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setDropdownOpen(false);
                    router.push(ORCHESTRATOR_ROUTE);
                  }}
                  className={cn(
                    'w-full px-3 py-2 text-sm text-left hover:bg-muted transition-colors flex items-center gap-2',
                    isOrchestratorRoute(pathname) && 'bg-primary/5 text-primary'
                  )}
                >
                  <Command className="w-4 h-4" />
                  {ORCHESTRATOR_LABEL}
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    router.push(PROJECTS_ROUTE_NAV.path);
                    setDropdownOpen(false);
                  }}
                  className={cn(
                    'w-full px-3 py-2 text-sm text-left hover:bg-muted transition-colors flex items-center gap-2',
                    currentRoute?.id === PROJECTS_ROUTE_NAV.id && 'bg-primary/5 text-primary'
                  )}
                >
                  <Briefcase className="w-4 h-4" />
                  {PROJECTS_ROUTE_NAV.label}
                </button>

                {/* Divider — secondary pages below */}
                <div className="border-t border-border my-1" />

                {/* Secondary pages */}
                {SECONDARY_PAGES.map((route) => {
                  const Icon = route.icon;
                  const isActive = currentRoute?.id === route.id;
                  return (
                    <button
                      key={route.id}
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(route.path);
                        setDropdownOpen(false);
                      }}
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
            )}
          </div>

          {/* Right: User menu only */}
          <UserMenu email={userEmail} />
        </header>

        {/* Main content */}
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
