'use client';

/**
 * Persistent sidebar for all /context routes.
 * Self-contained: fetches platform summary data, derives active state from pathname/searchParams.
 */

import { useState, useEffect } from 'react';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import {
  User,
  Palette,
  BookOpen,
  Database,
  FileText,
  Plus,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import type { PlatformSummary } from '@/components/ui/PlatformCard';

const ALL_PLATFORMS = ['slack', 'gmail', 'notion', 'calendar'] as const;
type PlatformKey = typeof ALL_PLATFORMS[number];

const PLATFORM_CONFIG: Record<PlatformKey, { label: string }> = {
  slack: { label: 'Slack' },
  gmail: { label: 'Email' },
  notion: { label: 'Notion' },
  calendar: { label: 'Calendar' },
};

export function ContextSidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [platforms, setPlatforms] = useState<PlatformSummary[]>([]);

  useEffect(() => {
    api.integrations.getSummary().then((r) => setPlatforms(r.platforms || [])).catch(() => {});
  }, []);

  // Build per-platform status
  const platformStatus: Record<string, PlatformSummary | undefined> = {};
  for (const p of platforms) {
    const key = p.provider === 'google' ? 'calendar' : p.provider;
    platformStatus[key] = p;
  }

  // Derive active state from URL
  const isOnContextRoot = pathname === '/context';
  const platformMatch = pathname.match(/^\/context\/(.+)$/);
  const activePlatform = platformMatch ? platformMatch[1] : null;
  const activeSection = searchParams.get('section') || 'profile';
  const isPlatformsSection = activeSection === 'platforms' || activeSection.startsWith('platform_') || !!activePlatform;

  const knowledgeItems = [
    { label: 'Profile', icon: <User className="w-4 h-4" />, section: 'profile' },
    { label: 'Styles', icon: <Palette className="w-4 h-4" />, section: 'styles' },
    { label: 'Entries', icon: <BookOpen className="w-4 h-4" />, section: 'entries' },
  ];

  return (
    <nav className="w-48 flex-shrink-0 border-r border-border bg-muted/50 flex flex-col h-full">
      <div className="p-4 space-y-1 flex-1 overflow-y-auto">
        {/* KNOWLEDGE group */}
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-3 pt-2 pb-2">
          Knowledge
        </div>
        {knowledgeItems.map((item) => {
          const isActive = isOnContextRoot && !isPlatformsSection && activeSection === item.section;
          return (
            <button
              key={item.section}
              onClick={() => router.push(`/context?section=${item.section}`)}
              className={cn(
                "w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors text-left",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              {item.icon}
              {item.label}
            </button>
          );
        })}

        {/* FILESYSTEM group */}
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-3 pt-4 pb-2">
          Filesystem
        </div>

        {/* Platforms parent */}
        <button
          onClick={() => router.push('/context?section=platforms')}
          className={cn(
            "w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors",
            isPlatformsSection
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          <span className="flex items-center gap-2">
            <Database className="w-4 h-4" />
            Platforms
          </span>
        </button>

        {/* Per-platform sub-items */}
        <div className="ml-3 space-y-0.5">
          {ALL_PLATFORMS.map((platformKey) => {
            const config = PLATFORM_CONFIG[platformKey];
            const summary = platformStatus[platformKey];
            const isConnected = summary?.status === 'connected';
            const isActive = activePlatform === platformKey ||
              (platformKey === 'calendar' && activePlatform === 'google');

            return (
              <button
                key={platformKey}
                onClick={() => router.push(`/context/${platformKey}`)}
                className={cn(
                  "w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-xs transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : isConnected
                      ? "text-foreground hover:bg-muted"
                      : "text-muted-foreground/60 hover:bg-muted hover:text-muted-foreground"
                )}
              >
                <span className="flex items-center gap-2">
                  <span className={cn(
                    "w-1.5 h-1.5 rounded-full shrink-0",
                    isConnected ? "bg-green-500" : "bg-muted-foreground/30"
                  )} />
                  {config.label}
                </span>
                {isConnected && summary && summary.resource_count > 0 && (
                  <span className="text-muted-foreground">{summary.resource_count}</span>
                )}
              </button>
            );
          })}
        </div>

        {/* Documents */}
        <button
          onClick={() => router.push('/context?section=documents')}
          className={cn(
            "w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors mt-1",
            isOnContextRoot && activeSection === 'documents'
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          <FileText className="w-4 h-4" />
          Documents
        </button>
      </div>

      {/* Actions */}
      <div className="p-4 border-t border-border">
        <button
          onClick={() => router.push('/context?section=entries')}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Knowledge
        </button>
      </div>
    </nav>
  );
}
