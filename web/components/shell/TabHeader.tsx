'use client';

/**
 * ADR-022: Tab-Based Supervision Architecture
 *
 * Simplified header for tab-based UI.
 * Just logo, work status, and user menu - navigation is handled by tabs.
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { createClient } from '@/lib/supabase/client';
import { UserMenu } from './UserMenu';
import { WorkStatus } from './WorkStatus';

export function TabHeader() {
  const [userEmail, setUserEmail] = useState<string | undefined>();

  useEffect(() => {
    const supabase = createClient();

    const getUser = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      setUserEmail(user?.email ?? undefined);
    };

    getUser();
  }, []);

  return (
    <header className="h-12 border-b border-border bg-background flex items-center justify-between px-4 shrink-0">
      {/* Left: Logo + Work Status */}
      <div className="flex items-center gap-4">
        <Link href="/" className="text-lg font-brand hover:opacity-80 transition-opacity">
          yarnnn
        </Link>
        <WorkStatus />
      </div>

      {/* Right: User Menu */}
      <UserMenu email={userEmail} />
    </header>
  );
}
