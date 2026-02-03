'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * Simplified layout - single desk, no surface drawer
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { Home, Briefcase, Brain, FolderOpen, ChevronDown } from 'lucide-react';
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

// Domain navigation with dropdown surfaces
interface DomainNavItem {
  id: string;
  label: string;
  icon: typeof Home;
  defaultSurface: DeskSurface;
  surfaces: { label: string; surface: DeskSurface }[];
}

const DOMAIN_NAV: DomainNavItem[] = [
  {
    id: 'home',
    label: 'Home',
    icon: Home,
    defaultSurface: { type: 'idle' },
    surfaces: [
      { label: 'Dashboard', surface: { type: 'idle' } },
      { label: 'Review', surface: { type: 'idle' } }, // Will navigate to specific review when clicked from attention
    ],
  },
  {
    id: 'work',
    label: 'Work',
    icon: Briefcase,
    defaultSurface: { type: 'work-list' },
    surfaces: [
      { label: 'All Work', surface: { type: 'work-list' } },
      { label: 'Active', surface: { type: 'work-list', filter: 'active' } },
      { label: 'Completed', surface: { type: 'work-list', filter: 'completed' } },
    ],
  },
  {
    id: 'context',
    label: 'Context',
    icon: Brain,
    defaultSurface: { type: 'context-browser', scope: 'user' },
    surfaces: [
      { label: 'About Me', surface: { type: 'context-browser', scope: 'user' } },
    ],
  },
  {
    id: 'documents',
    label: 'Docs',
    icon: FolderOpen,
    defaultSurface: { type: 'document-list' },
    surfaces: [
      { label: 'All Documents', surface: { type: 'document-list' } },
    ],
  },
];

// Get current domain from surface type
function getCurrentDomain(surface: DeskSurface): string {
  switch (surface.type) {
    case 'idle':
    case 'deliverable-review':
    case 'deliverable-detail':
      return 'home';
    case 'work-output':
    case 'work-list':
      return 'work';
    case 'context-browser':
    case 'context-editor':
      return 'context';
    case 'document-viewer':
    case 'document-list':
      return 'documents';
    case 'project-detail':
    case 'project-list':
      return 'projects';
    default:
      return 'home';
  }
}

// Get surface title for display in nav
function getSurfaceTitle(surface: DeskSurface): string | null {
  switch (surface.type) {
    case 'idle':
      return 'Dashboard';
    case 'deliverable-review':
      return 'Review';
    case 'deliverable-detail':
      return 'Deliverable';
    case 'work-output':
      return 'Output';
    case 'work-list':
      if (surface.filter === 'active') return 'Active';
      if (surface.filter === 'completed') return 'Completed';
      return 'All Work';
    case 'context-browser':
      return surface.scope === 'user' ? 'About Me' : 'Context';
    case 'context-editor':
      return 'Edit Memory';
    case 'document-viewer':
      return 'Document';
    case 'document-list':
      return 'All Documents';
    case 'project-detail':
      return 'Project';
    case 'project-list':
      return 'All Projects';
    default:
      return null;
  }
}

// Inner component that can use desk context
function AuthenticatedLayoutInner({
  children,
  userEmail,
}: {
  children: React.ReactNode;
  userEmail?: string;
}) {
  const { surface, setSurface } = useDesk();
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const currentDomain = getCurrentDomain(surface);
  const surfaceTitle = getSurfaceTitle(surface);

  // Handle surface change from TP tool results
  const handleSurfaceChange = useCallback(
    (newSurface: DeskSurface) => {
      setSurface(newSurface);
    },
    [setSurface]
  );

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = () => setOpenDropdown(null);
    if (openDropdown) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [openDropdown]);

  return (
    <TPProvider onSurfaceChange={handleSurfaceChange}>
      <div className="flex flex-col h-screen bg-background">
        {/* Top Bar - Single unified bar */}
        <header className="h-14 border-b border-border bg-background flex items-center justify-between px-4 shrink-0">
          {/* Left: Logo */}
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSurface({ type: 'idle' })}
              className="text-xl font-brand hover:opacity-80 transition-opacity"
            >
              yarnnn
            </button>
          </div>

          {/* Center: Domain Navigation with dropdowns */}
          <nav className="hidden md:flex items-center gap-1">
            {DOMAIN_NAV.map((domain) => {
              const Icon = domain.icon;
              const isActive = currentDomain === domain.id;
              const isOpen = openDropdown === domain.id;

              return (
                <div key={domain.id} className="relative">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (isActive && domain.surfaces.length > 1) {
                        // Toggle dropdown if active and has multiple surfaces
                        setOpenDropdown(isOpen ? null : domain.id);
                      } else {
                        // Navigate to default surface
                        setSurface(domain.defaultSurface);
                        setOpenDropdown(null);
                      }
                    }}
                    className={cn(
                      'flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors',
                      isActive
                        ? 'bg-primary/10 text-primary font-medium'
                        : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{domain.label}</span>
                    {isActive && surfaceTitle && (
                      <>
                        <span className="text-primary/50">/</span>
                        <span className="font-normal">{surfaceTitle}</span>
                      </>
                    )}
                    {isActive && domain.surfaces.length > 1 && (
                      <ChevronDown className={cn(
                        'w-3 h-3 opacity-50 transition-transform',
                        isOpen && 'rotate-180'
                      )} />
                    )}
                  </button>

                  {/* Dropdown menu */}
                  {isOpen && domain.surfaces.length > 1 && (
                    <div className="absolute top-full left-0 mt-1 w-40 bg-background border border-border rounded-md shadow-lg py-1 z-50">
                      {domain.surfaces.map((item, idx) => (
                        <button
                          key={idx}
                          onClick={(e) => {
                            e.stopPropagation();
                            setSurface(item.surface);
                            setOpenDropdown(null);
                          }}
                          className={cn(
                            'w-full px-3 py-2 text-sm text-left hover:bg-muted transition-colors',
                            surfaceTitle === item.label && 'bg-primary/5 text-primary'
                          )}
                        >
                          {item.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </nav>

          {/* Mobile: Show current location */}
          <div className="flex md:hidden items-center gap-2 text-sm">
            {(() => {
              const domain = DOMAIN_NAV.find(d => d.id === currentDomain);
              if (!domain) return null;
              const Icon = domain.icon;
              return (
                <>
                  <Icon className="w-4 h-4" />
                  <span className="font-medium">{domain.label}</span>
                  {surfaceTitle && (
                    <>
                      <span className="text-muted-foreground">/</span>
                      <span className="text-muted-foreground">{surfaceTitle}</span>
                    </>
                  )}
                </>
              );
            })()}
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
