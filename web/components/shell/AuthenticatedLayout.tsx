'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * Simplified layout - single desk, no surface drawer
 */

import { useEffect, useState, useCallback } from 'react';
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

// Domain navigation - simple list, dropdown navigates between domains
interface DomainNavItem {
  id: string;
  label: string;
  icon: typeof Home;
  surface: DeskSurface;
}

const DOMAIN_NAV: DomainNavItem[] = [
  { id: 'home', label: 'Home', icon: Home, surface: { type: 'idle' } },
  { id: 'work', label: 'Work', icon: Briefcase, surface: { type: 'work-list' } },
  { id: 'context', label: 'Context', icon: Brain, surface: { type: 'context-browser', scope: 'user' } },
  { id: 'documents', label: 'Docs', icon: FolderOpen, surface: { type: 'document-list' } },
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


// Inner component that can use desk context
function AuthenticatedLayoutInner({
  children,
  userEmail,
}: {
  children: React.ReactNode;
  userEmail?: string;
}) {
  const { surface, setSurface } = useDesk();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const currentDomain = getCurrentDomain(surface);

  // Handle surface change from TP tool results
  const handleSurfaceChange = useCallback(
    (newSurface: DeskSurface) => {
      setSurface(newSurface);
    },
    [setSurface]
  );

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = () => setDropdownOpen(false);
    if (dropdownOpen) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [dropdownOpen]);

  // Get current domain info
  const currentDomainInfo = DOMAIN_NAV.find(d => d.id === currentDomain);
  const CurrentIcon = currentDomainInfo?.icon || Home;

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

          {/* Center: Current domain with dropdown to navigate */}
          <div className="relative">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setDropdownOpen(!dropdownOpen);
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md bg-primary/10 text-primary font-medium"
            >
              <CurrentIcon className="w-4 h-4" />
              <span>{currentDomainInfo?.label || 'Home'}</span>
              <ChevronDown className={cn(
                'w-3 h-3 opacity-50 transition-transform',
                dropdownOpen && 'rotate-180'
              )} />
            </button>

            {/* Dropdown: Navigate to other domains */}
            {dropdownOpen && (
              <div className="absolute top-full left-1/2 -translate-x-1/2 mt-1 w-40 bg-background border border-border rounded-md shadow-lg py-1 z-50">
                {DOMAIN_NAV.map((domain) => {
                  const Icon = domain.icon;
                  const isActive = currentDomain === domain.id;
                  return (
                    <button
                      key={domain.id}
                      onClick={(e) => {
                        e.stopPropagation();
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
