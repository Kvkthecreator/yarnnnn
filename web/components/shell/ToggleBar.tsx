'use client';

/**
 * ToggleBar — Claude Desktop-style pill toggle for top-level navigation
 *
 * Three segments: Tasks | Context | Activity
 * Each segment is a Next.js Link (route-based navigation).
 * Active segment determined by pathname prefix matching.
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ListChecks, FolderOpen, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';

const SEGMENTS = [
  { id: 'tasks', label: 'Tasks', icon: ListChecks, href: '/tasks' },
  { id: 'context', label: 'Context', icon: FolderOpen, href: '/context' },
  { id: 'activity', label: 'Activity', icon: Activity, href: '/activity' },
] as const;

export function ToggleBar() {
  const pathname = usePathname();

  const activeId = SEGMENTS.find(s =>
    pathname === s.href || pathname.startsWith(s.href + '/')
  )?.id ?? 'tasks';

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
