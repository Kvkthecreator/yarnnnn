'use client';

/**
 * ToggleBar — Claude Desktop-style pill toggle for top-level navigation
 *
 * SURFACE-ARCHITECTURE.md v4: Four segments: Home | Agents | Context | Activity
 * Each segment is a Next.js Link (route-based navigation).
 * Active segment determined by pathname prefix matching.
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, Users, FolderOpen, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';

const SEGMENTS = [
  { id: 'chat', label: 'Home', icon: Home, href: '/chat' },
  { id: 'agents', label: 'Agents', icon: Users, href: '/agents' },
  { id: 'context', label: 'Context', icon: FolderOpen, href: '/context' },
  { id: 'activity', label: 'Activity', icon: Activity, href: '/activity' },
] as const;

export function ToggleBar() {
  const pathname = usePathname();

  const activeId = SEGMENTS.find(s =>
    pathname === s.href || pathname.startsWith(s.href + '/')
  )?.id ?? 'agents';

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
