'use client';

/**
 * Persistent sidebar for all /context routes.
 * Self-contained: fetches platform summary data, derives active state from pathname/searchParams.
 */

import { useState, useEffect } from 'react';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import {
  Database,
  FileText,
  FolderTree,
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

const KNOWLEDGE_CLASSES = [
  { key: 'digests', label: 'Digests' },
  { key: 'analyses', label: 'Analyses' },
  { key: 'briefs', label: 'Briefs' },
  { key: 'research', label: 'Research' },
  { key: 'insights', label: 'Insights' },
] as const;

export function ContextSidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [platforms, setPlatforms] = useState<PlatformSummary[]>([]);
  const [knowledgeCounts, setKnowledgeCounts] = useState<Record<string, number>>({});

  useEffect(() => {
    Promise.all([
      api.integrations.getSummary().catch(() => ({ platforms: [] })),
      api.knowledge.summary().catch(() => ({ classes: [] })),
    ]).then(([integrations, knowledge]) => {
      setPlatforms(integrations.platforms || []);
      const nextCounts: Record<string, number> = {};
      for (const item of knowledge.classes || []) {
        nextCounts[item.content_class] = item.count;
      }
      setKnowledgeCounts(nextCounts);
    }).catch(() => {});
  }, []);

  // Build per-platform status
  const platformStatus: Record<string, PlatformSummary | undefined> = {};
  for (const p of platforms) {
    platformStatus[p.provider] = p;
  }

  // Derive active state from URL
  const isOnContextRoot = pathname === '/context';
  const platformMatch = pathname.match(/^\/context\/(.+)$/);
  const activePlatform = platformMatch ? platformMatch[1] : null;
  const activeSection = searchParams.get('section') || 'knowledge';
  const activeKnowledgeClass = searchParams.get('class');
  const isPlatformsSection = activeSection === 'platforms' || activeSection.startsWith('platform_') || !!activePlatform;
  const isKnowledgeSection = isOnContextRoot && activeSection === 'knowledge';
  const totalKnowledge = Object.values(knowledgeCounts).reduce((sum, count) => sum + count, 0);

  return (
    <nav className="h-full min-h-0 border-r border-border bg-muted/50 flex flex-col">
      <div className="p-4 space-y-1 flex-1 min-h-0 overflow-y-auto">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-3 pt-4 pb-2">
          Files
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
            const isConnected = summary?.status === 'active';
            const isActive = activePlatform === platformKey;

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

        {/* Knowledge */}
        <button
          onClick={() => router.push('/context?section=knowledge')}
          className={cn(
            "w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors mt-1",
            isKnowledgeSection
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          <span className="flex items-center gap-2">
            <FolderTree className="w-4 h-4" />
            Knowledge
          </span>
          {totalKnowledge > 0 && (
            <span className="text-muted-foreground text-xs">{totalKnowledge}</span>
          )}
        </button>

        <div className="ml-3 space-y-0.5">
          <button
            onClick={() => router.push('/context?section=knowledge')}
            className={cn(
              "w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-xs transition-colors",
              isKnowledgeSection && !activeKnowledgeClass
                ? "bg-primary/10 text-primary"
                : "text-foreground hover:bg-muted"
            )}
          >
            <span className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full shrink-0 bg-muted-foreground/40" />
              All
            </span>
          </button>

          {KNOWLEDGE_CLASSES.map((item) => {
            const count = knowledgeCounts[item.key] || 0;
            const isActive = isKnowledgeSection && activeKnowledgeClass === item.key;
            return (
              <button
                key={item.key}
                onClick={() => router.push(`/context?section=knowledge&class=${item.key}`)}
                className={cn(
                  "w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-xs transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-foreground hover:bg-muted"
                )}
              >
                <span className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full shrink-0 bg-muted-foreground/40" />
                  {item.label}
                </span>
                {count > 0 && (
                  <span className="text-muted-foreground">{count}</span>
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
    </nav>
  );
}
