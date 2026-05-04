'use client';

/**
 * ToggleBar — top-level pill navigation (ADR-205 F1, ADR-214).
 *
 * Four segments: Chat | Work | Agents | Files
 *   - Chat:   authoring surface, HOME (ADR-205 F1)
 *   - Work:   output-kind list + Dashboard + Schedule + Decisions tabs inside
 *   - Agents: systemic + domain Agents (ADR-214)
 *   - Files:  workspace context browser (ADR-180)
 *
 * Schedule (ADR-243) is now a tab inside /work, not a top-level segment.
 * /schedule redirects to /work (bookmark-safety stub).
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { MessageSquare, Briefcase, Users, FolderOpen } from 'lucide-react';
import { cn } from '@/lib/utils';

const SEGMENTS = [
  { id: 'chat',    label: 'Chat',   icon: MessageSquare, href: '/chat' },
  { id: 'work',    label: 'Work',   icon: Briefcase,     href: '/work' },
  { id: 'agents',  label: 'Agents', icon: Users,         href: '/agents' },
  { id: 'context', label: 'Files',  icon: FolderOpen,    href: '/context' },
] as const;

export function ToggleBar() {
  const pathname = usePathname();

  // /schedule redirects to /work; treat it as work-active while the redirect fires
  const activeId = SEGMENTS.find(s =>
    pathname === s.href || pathname.startsWith(s.href + '/')
  )?.id ?? (pathname.startsWith('/schedule') ? 'work' : 'chat');

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
            <span className="hidden sm:inline">{segment.label}</span>
          </Link>
        );
      })}
    </div>
  );
}
