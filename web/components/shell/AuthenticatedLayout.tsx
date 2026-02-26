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
 * - Chat (home) | Deliverables (Work) | Memory | Context | Activity | Settings
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
import { MessageCircle, ChevronDown, Settings, Calendar, Activity, Layers, Brain, Zap } from 'lucide-react';
import { DeskProvider, useDesk } from '@/contexts/DeskContext';
import { TPProvider, useTP } from '@/contexts/TPContext';
import type { DeskSurface } from '@/types/desk';
import { UserMenu } from './UserMenu';
import { cn } from '@/lib/utils';
import { SetupConfirmModal } from '@/components/modals/SetupConfirmModal';

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

// ADR-037: Chat-First Navigation
// - Chat is home (dashboard with idle surface)
// - All other items are routes (actual pages, not surfaces)
// - Surfaces are invoked from chat, not from nav

interface RouteItem {
  id: string;
  label: string;
  icon: typeof MessageCircle;
  path: string;
}

// ADR-063: Four-Layer Model Navigation + ADR-072: System (Operations)
// Chat | Deliverables (Work) | Memory | Context | Activity | System | Settings
const ROUTE_PAGES: RouteItem[] = [
  { id: 'deliverables', label: 'Deliverables', icon: Calendar, path: '/deliverables' },
  { id: 'memory', label: 'Memory', icon: Brain, path: '/memory' },
  { id: 'context', label: 'Context', icon: Layers, path: '/context' },
  { id: 'activity', label: 'Activity', icon: Activity, path: '/activity' },
  { id: 'system', label: 'System', icon: Zap, path: '/system' },
  { id: 'settings', label: 'Settings', icon: Settings, path: '/settings' },
];


// Get route info from pathname
function getRouteFromPathname(pathname: string): RouteItem | null {
  // Check if on a route page
  for (const route of ROUTE_PAGES) {
    if (pathname === route.path || pathname.startsWith(route.path + '/')) {
      return route;
    }
  }
  return null;
}

// Check if pathname is the dashboard (surfaces live here)
function isDashboardRoute(pathname: string): boolean {
  return pathname === '/dashboard' || pathname.startsWith('/dashboard/');
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
  const isOnDashboard = isDashboardRoute(pathname);
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
      if (!isDashboardRoute(window.location.pathname)) {
        router.push('/dashboard');
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

  // Navigate to dashboard (handles both route nav and surface reset)
  const navigateToDashboard = useCallback(() => {
    if (!isOnDashboard) {
      router.push('/dashboard');
    }
    setSurface({ type: 'idle' });
  }, [isOnDashboard, router, setSurface]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = () => setDropdownOpen(false);
    if (dropdownOpen) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [dropdownOpen]);

  // ADR-037: Get current display info based on context
  const getCurrentDisplay = () => {
    if (currentRoute) {
      // On a route page (e.g., /platforms, /docs, /settings)
      return {
        icon: currentRoute.icon,
        label: currentRoute.label,
      };
    }
    // On dashboard = Chat (home)
    return {
      icon: MessageCircle,
      label: 'Chat',
    };
  };

  const display = getCurrentDisplay();
  const CurrentIcon = display.icon;

  return (
    <TPProvider onSurfaceChange={handleSurfaceChange}>
      <div className="flex flex-col h-screen bg-background">
        {/* Top Bar - Single unified bar */}
        <header className="h-14 border-b border-border bg-background flex items-center justify-between px-4 shrink-0">
          {/* Left: Logo - always navigates to dashboard */}
          <div className="flex items-center gap-4">
            <button
              onClick={navigateToDashboard}
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
              <div className="absolute top-full left-1/2 -translate-x-1/2 mt-1 w-40 bg-background border border-border rounded-md shadow-lg py-1 z-50">
                {/* ADR-037: Chat (home) - always first */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (!isOnDashboard) {
                      router.push('/dashboard');
                    }
                    setSurface({ type: 'idle' });
                    setDropdownOpen(false);
                  }}
                  className={cn(
                    'w-full px-3 py-2 text-sm text-left hover:bg-muted transition-colors flex items-center gap-2',
                    isOnDashboard && 'bg-primary/5 text-primary'
                  )}
                >
                  <MessageCircle className="w-4 h-4" />
                  Chat
                </button>

                {/* Divider */}
                <div className="border-t border-border my-1" />

                {/* Route pages - all navigation items are routes now */}
                {ROUTE_PAGES.map((route) => {
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
