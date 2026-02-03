'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * Simplified layout - single desk, no surface drawer
 */

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { Menu, Home, Briefcase, Brain, FolderOpen } from 'lucide-react';
import { DeskProvider, useDesk } from '@/contexts/DeskContext';
import { TPProvider } from '@/contexts/TPContext';
import { DomainBrowser } from '@/components/desk/DomainBrowser';
import { UserMenu } from './UserMenu';
import { DeskSurface } from '@/types/desk';
import { cn } from '@/lib/utils';

interface AuthenticatedLayoutProps {
  children: React.ReactNode;
}

export default function AuthenticatedLayout({ children }: AuthenticatedLayoutProps) {
  const [userEmail, setUserEmail] = useState<string | undefined>();
  const [loading, setLoading] = useState(true);
  const [browserOpen, setBrowserOpen] = useState(false);
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
      <AuthenticatedLayoutInner
        userEmail={userEmail}
        browserOpen={browserOpen}
        setBrowserOpen={setBrowserOpen}
      >
        {children}
      </AuthenticatedLayoutInner>
    </DeskProvider>
  );
}

// Domain navigation items - surfaces that exist
// Home (idle) shows deliverables overview, so no separate deliverables tab needed
const DOMAIN_NAV = [
  { id: 'home', label: 'Home', icon: Home, surface: { type: 'idle' } as DeskSurface },
  { id: 'work', label: 'Work', icon: Briefcase, surface: { type: 'work-list' } as DeskSurface },
  { id: 'context', label: 'Context', icon: Brain, surface: { type: 'context-browser', scope: 'user' } as DeskSurface },
  { id: 'documents', label: 'Docs', icon: FolderOpen, surface: { type: 'document-list' } as DeskSurface },
] as const;

// Get current domain from surface type
function getCurrentDomain(surface: DeskSurface): string {
  switch (surface.type) {
    case 'idle':
    case 'deliverable-review':
    case 'deliverable-detail':
      return 'home'; // Deliverables are part of home
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
  browserOpen,
  setBrowserOpen,
}: {
  children: React.ReactNode;
  userEmail?: string;
  browserOpen: boolean;
  setBrowserOpen: (open: boolean) => void;
}) {
  const { surface, setSurface } = useDesk();
  const currentDomain = getCurrentDomain(surface);

  // Handle surface change from TP tool results
  const handleSurfaceChange = useCallback(
    (newSurface: DeskSurface) => {
      setSurface(newSurface);
    },
    [setSurface]
  );

  return (
    <TPProvider onSurfaceChange={handleSurfaceChange}>
      <div className="flex flex-col h-screen bg-background">
        {/* Top Bar */}
        <header className="h-14 border-b border-border bg-background flex items-center justify-between px-4 shrink-0">
          {/* Left: Logo */}
          <div className="flex items-center gap-4">
            <span className="text-xl font-brand">yarnnn</span>
          </div>

          {/* Center: Domain Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {DOMAIN_NAV.map(({ id, label, icon: Icon, surface: navSurface }) => (
              <button
                key={id}
                onClick={() => setSurface(navSurface)}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors',
                  currentDomain === id
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                )}
              >
                <Icon className="w-4 h-4" />
                <span>{label}</span>
              </button>
            ))}
          </nav>

          {/* Right: Browse + User */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setBrowserOpen(true)}
              className="p-2 hover:bg-muted rounded-md transition-colors"
              aria-label="Browse all"
            >
              <Menu className="w-5 h-5" />
            </button>
            <UserMenu email={userEmail} />
          </div>
        </header>

        {/* Main content */}
        <main className="flex-1 overflow-hidden">{children}</main>

        {/* Domain Browser */}
        <DomainBrowser isOpen={browserOpen} onClose={() => setBrowserOpen(false)} />
      </div>
    </TPProvider>
  );
}
