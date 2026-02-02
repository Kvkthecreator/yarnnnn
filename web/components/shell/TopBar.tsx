'use client';

/**
 * ADR-014: Top Bar with Minimal Chrome
 * ADR-018: Updated for Deliverables-first experience
 *
 * Chat navigation removed - FloatingChatPanel (Cmd+K) is the primary chat interface.
 * The floating chat is always available and context-aware.
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutGrid } from 'lucide-react';
import { UserMenu } from './UserMenu';
import { WorkStatus } from './WorkStatus';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { cn } from '@/lib/utils';

interface TopBarProps {
  email?: string;
}

export function TopBar({ email }: TopBarProps) {
  const pathname = usePathname();
  const isDesktop = useMediaQuery('(min-width: 768px)');

  const isDeliverables = pathname === '/dashboard' || pathname.startsWith('/dashboard/deliverable');

  return (
    <header className="h-14 border-b border-border bg-background flex items-center justify-between px-4 shrink-0 sticky top-0 z-40">
      {/* Left section: Logo + Work Status */}
      <div className="flex items-center gap-4">
        {/* Logo - links to landing page */}
        <Link href="/" className="text-xl font-brand hover:opacity-80 transition-opacity">
          yarnnn
        </Link>

        {/* Work Status (ADR-016) */}
        <WorkStatus />
      </div>

      {/* Right section: Navigation + User */}
      <div className="flex items-center gap-2">
        {/* Navigation (desktop) */}
        {isDesktop && (
          <nav className="flex items-center gap-1 mr-2">
            <Link
              href="/dashboard"
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors",
                isDeliverables
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <LayoutGrid className="w-4 h-4" />
              <span className="hidden lg:inline">Deliverables</span>
            </Link>
          </nav>
        )}

        {/* User Menu */}
        <UserMenu email={email} />
      </div>
    </header>
  );
}
