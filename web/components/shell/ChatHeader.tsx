'use client';

/**
 * ADR-022: Chat-First Architecture
 *
 * Header for chat-first UI. Simple: logo, work status, settings.
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Settings } from 'lucide-react';
import { createClient } from '@/lib/supabase/client';
import { UserMenu } from './UserMenu';
import { WorkStatus } from './WorkStatus';

export function ChatHeader() {
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

      {/* Right: Settings + User Menu */}
      <div className="flex items-center gap-2">
        <Link
          href="/dashboard/settings"
          className="p-2 hover:bg-muted rounded-md transition-colors"
          title="Settings"
        >
          <Settings className="w-4 h-4 text-muted-foreground" />
        </Link>
        <UserMenu email={userEmail} />
      </div>
    </header>
  );
}
