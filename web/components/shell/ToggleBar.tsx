'use client';

/**
 * ToggleBar — top-level pill navigation (cockpit nav per ADR-205 F1 + ADR-214).
 *
 * Current segments: Chat | Work | Agents | Files
 *   - Chat: "Tell YARNNN what you want." (authoring surface, HOME — ADR-205 F1)
 *   - Work: "Let me check the work." (task list with briefing strip + detail — ADR-205 F2)
 *   - Agents: "Let me check on my agents." (systemic + domain Agents — ADR-214)
 *   - Files (nav label) / Context (route): "What does my workspace know?" (ADR-180)
 *
 * ADR-214 (2026-04-23): Four-tab consolidation. /review is deleted; Reviewer
 * lives as a systemic agent detail at /agents?agent=reviewer. /team reverses
 * back to /agents per ADR-212 vocabulary (only judgment-bearing entities are
 * Agents — production roles + integrations are Orchestration, not shown here).
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { MessageSquare, Briefcase, Users, FolderOpen } from 'lucide-react';
import { cn } from '@/lib/utils';

const SEGMENTS = [
  { id: 'chat', label: 'Chat', icon: MessageSquare, href: '/chat' },
  { id: 'work', label: 'Work', icon: Briefcase, href: '/work' },
  { id: 'agents', label: 'Agents', icon: Users, href: '/agents' },
  { id: 'context', label: 'Files', icon: FolderOpen, href: '/context' },
] as const;

export function ToggleBar() {
  const pathname = usePathname();

  const activeId = SEGMENTS.find(s =>
    pathname === s.href || pathname.startsWith(s.href + '/')
  )?.id ?? 'chat';

  return (
    <div className="flex items-center gap-0.5 rounded-full bg-muted/60 p-0.5">
      {SEGMENTS.map(segment => {
        const Icon = segment.icon;
        const isActive = segment.id === activeId;
        return (
          <Link
            key={segment.id}
            href={segment.href}
            className={cn(
              'flex items-center gap-1.5 rounded-full px-2.5 py-1 text-sm font-medium transition-colors',
              isActive
                ? 'bg-foreground text-background shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <Icon className="h-3.5 w-3.5 shrink-0" />
            {/* Hide text labels on small screens — icons only on mobile */}
            <span className="hidden sm:inline">{segment.label}</span>
          </Link>
        );
      })}
    </div>
  );
}
