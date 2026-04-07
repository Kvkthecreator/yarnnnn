'use client';

/**
 * ToggleBar — Claude Desktop-style pill toggle for top-level navigation
 *
 * ADR-163 Surface Restructure: Four segments: Chat | Work | Agents | Context
 * Each answers exactly one question:
 *   - Chat: "What should I do? What's happening?"
 *   - Work: "What is my workforce doing?"
 *   - Agents: "Who's on my team?"
 *   - Context: "What does my workspace know?"
 *
 * Previous nav (v7.2) was Home | Agents | Context | Activity, with "Home"
 * pointing at /chat. The v8 restructure renames Home to Chat (its true
 * identity), elevates Work to first-class, absorbs Activity into per-surface
 * contexts, and shrinks Agents to a roster-plus-identity view.
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
              'flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium transition-all',
              isActive
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <Icon className="w-3.5 h-3.5" />
            <span>{segment.label}</span>
          </Link>
        );
      })}
    </div>
  );
}
