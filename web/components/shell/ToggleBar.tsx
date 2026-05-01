'use client';

/**
 * ToggleBar — top-level pill navigation (cockpit nav per ADR-205 F1 + ADR-214 + ADR-243).
 *
 * Current segments: Chat | Work | Schedule | Agents | Files
 *   - Chat: "Tell YARNNN what you want." (authoring surface, HOME — ADR-205 F1)
 *   - Work: "Let me check the work." (output-kind framing — Reports / Tracking / Actions / System)
 *   - Schedule: "What's on my schedule?" (cadence framing — Recurring / Reactive / One-time, ADR-243)
 *   - Agents: "Let me check on my agents." (systemic + domain Agents — ADR-214)
 *   - Files (nav label) / Context (route): "What does my workspace know?" (ADR-180)
 *
 * ADR-243 (2026-05-01): /schedule slotted between /work and /agents as the
 * cadence-framed sibling of /work. List-only surface; row click hands off to
 * /work?task={slug} for the canonical detail view. Calendar/timeline is
 * Phase 2 (deferred until alpha demand).
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { MessageSquare, Briefcase, CalendarClock, Users, FolderOpen } from 'lucide-react';
import { cn } from '@/lib/utils';

const SEGMENTS = [
  { id: 'chat', label: 'Chat', icon: MessageSquare, href: '/chat' },
  { id: 'work', label: 'Work', icon: Briefcase, href: '/work' },
  { id: 'schedule', label: 'Schedule', icon: CalendarClock, href: '/schedule' },
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
