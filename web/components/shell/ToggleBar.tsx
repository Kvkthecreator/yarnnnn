'use client';

/**
 * ToggleBar - top-level pill navigation
 *
 * ADR-163 Surface Restructure: Four segments: Chat | Work | Agents | Context
 * Each answers exactly one question:
 *   - Chat: "What should I do? What's happening?"
 *   - Work: "What is my workforce doing?"
 *   - Agents: "Who's on my team?"
 *   - Context: "What does my workspace know?"
 *
 * Nav order: Chat → Work → Agents → Context.
 * Work precedes Agents: ADR-176 work-first model — work exists first, agents serve work.
 * Users navigate to tasks first; agent identity is secondary.
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { MessageCircle, Briefcase, Users, FolderOpen } from 'lucide-react';
import { cn } from '@/lib/utils';

const SEGMENTS = [
  { id: 'chat', label: 'Chat', icon: MessageCircle, href: '/chat' },
  { id: 'work', label: 'Work', icon: Briefcase, href: '/work' },
  { id: 'agents', label: 'Agents', icon: Users, href: '/agents' },
  { id: 'context', label: 'Context', icon: FolderOpen, href: '/context' },
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
