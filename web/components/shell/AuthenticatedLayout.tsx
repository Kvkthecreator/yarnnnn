'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * Simplified layout - single desk, no surface drawer
 */

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { Menu } from 'lucide-react';
import { DeskProvider, useDesk } from '@/contexts/DeskContext';
import { TPProvider } from '@/contexts/TPContext';
import { DomainBrowser } from '@/components/desk/DomainBrowser';
import { UserMenu } from './UserMenu';
import { ModeToggle } from '@/components/mode-toggle';
import { DeskSurface } from '@/types/desk';

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
  const { setSurface } = useDesk();

  // Handle surface change from TP tool results
  const handleSurfaceChange = useCallback(
    (surface: DeskSurface) => {
      setSurface(surface);
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

          {/* Right: Browse + User */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setBrowserOpen(true)}
              className="p-2 hover:bg-muted rounded-md transition-colors"
              aria-label="Browse all"
            >
              <Menu className="w-5 h-5" />
            </button>
            <ModeToggle />
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
