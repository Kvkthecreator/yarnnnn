'use client';

/**
 * ToggleBar - top-level pill navigation
 *
 * ADR-180 Work/Context Surface Split: Four segments: Chat | Work | Context | Agents
 * Each answers exactly one question:
 *   - Chat: "What should I do? What's happening?"
 *   - Work: "Is my work configured, healthy, and running?" (operational)
 *   - Context: "What does my workspace know? What has it produced?" (knowledge)
 *   - Agents: "Who's on my team?" (roster reference)
 *
 * Nav order reflects user navigation frequency (ADR-180):
 *   Chat → Work → Context → Agents
 * Agents is last: under ADR-176 agents serve work, not the other way around.
 * Context precedes Agents: outputs and knowledge are consulted more often than the roster.
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { MessageCircle, Briefcase, Users, FolderOpen } from 'lucide-react';
import { cn } from '@/lib/utils';

const SEGMENTS = [
  { id: 'chat', label: 'Chat', icon: MessageCircle, href: '/chat' },
  { id: 'work', label: 'Work', icon: Briefcase, href: '/work' },
  { id: 'context', label: 'Context', icon: FolderOpen, href: '/context' },
  { id: 'agents', label: 'Agents', icon: Users, href: '/agents' },
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
