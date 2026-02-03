'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * Simplified layout - single desk, no surface drawer
 *
 * Navigation model:
 * - Routes: /dashboard (surfaces), /settings, /projects/[id]
 * - Surfaces: Query-param states within /dashboard
 * - Domain dropdown shows surfaces when on /dashboard, routes otherwise
 */

import { useEffect, useState, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { LayoutDashboard, Brain, FolderOpen, ChevronDown, Settings } from 'lucide-react';
import { DeskProvider, useDesk } from '@/contexts/DeskContext';
import { TPProvider } from '@/contexts/TPContext';
import { UserMenu } from './UserMenu';
import { DeskSurface } from '@/types/desk';
import { cn } from '@/lib/utils';

interface AuthenticatedLayoutProps {
  children: React.ReactNode;
}

export default function AuthenticatedLayout({ children }: AuthenticatedLayoutProps) {
  const [userEmail, setUserEmail] = useState<string | undefined>();
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const supabase = createClient();

  useEffect(() => {
    const checkAuth = async () => {
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) {
        router.replace('/auth/login');
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
        router.replace('/auth/login');
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

// Surface domains - navigable within /dashboard via query params
interface SurfaceDomainItem {
  id: string;
  label: string;
  icon: typeof LayoutDashboard;
  surface: DeskSurface;
}

// Route pages - separate Next.js routes outside /dashboard
interface RouteItem {
  id: string;
  label: string;
  icon: typeof LayoutDashboard;
  path: string;
}

// Surface domains available via dropdown when on /dashboard
const SURFACE_DOMAINS: SurfaceDomainItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, surface: { type: 'idle' } },
  { id: 'context', label: 'Context', icon: Brain, surface: { type: 'context-browser', scope: 'user' } },
  { id: 'documents', label: 'Docs', icon: FolderOpen, surface: { type: 'document-list' } },
];

// Route pages (non-surface pages)
const ROUTE_PAGES: RouteItem[] = [
  { id: 'settings', label: 'Settings', icon: Settings, path: '/settings' },
];

// Get current surface domain from surface type
function getCurrentSurfaceDomain(surface: DeskSurface): string {
  switch (surface.type) {
    case 'idle':
    case 'deliverable-review':
    case 'deliverable-detail':
    case 'work-output':
    case 'work-list':
    case 'project-detail':
    case 'project-list':
      return 'dashboard';
    case 'context-browser':
    case 'context-editor':
      return 'context';
    case 'document-viewer':
    case 'document-list':
      return 'documents';
    default:
      return 'dashboard';
  }
}

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
  const currentSurfaceDomain = getCurrentSurfaceDomain(surface);

  // Handle surface change from TP tool results (with optional handoff message)
  const handleSurfaceChange = useCallback(
    (newSurface: DeskSurface, handoffMessage?: string) => {
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

  // Get current display info based on context
  const getCurrentDisplay = () => {
    if (currentRoute) {
      // On a route page (e.g., /settings)
      return {
        icon: currentRoute.icon,
        label: currentRoute.label,
      };
    }
    // On dashboard - show surface domain
    const domainInfo = SURFACE_DOMAINS.find(d => d.id === currentSurfaceDomain);
    return {
      icon: domainInfo?.icon || LayoutDashboard,
      label: domainInfo?.label || 'Dashboard',
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
                {/* Surface domains (always available) */}
                {SURFACE_DOMAINS.map((domain) => {
                  const Icon = domain.icon;
                  const isActive = isOnDashboard && currentSurfaceDomain === domain.id;
                  return (
                    <button
                      key={domain.id}
                      onClick={(e) => {
                        e.stopPropagation();
                        // Navigate to dashboard if not there
                        if (!isOnDashboard) {
                          router.push('/dashboard');
                        }
                        setSurface(domain.surface);
                        setDropdownOpen(false);
                      }}
                      className={cn(
                        'w-full px-3 py-2 text-sm text-left hover:bg-muted transition-colors flex items-center gap-2',
                        isActive && 'bg-primary/5 text-primary'
                      )}
                    >
                      <Icon className="w-4 h-4" />
                      {domain.label}
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
        <main className="flex-1 overflow-hidden">{children}</main>
      </div>
    </TPProvider>
  );
}
