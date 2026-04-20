'use client';

/**
 * ToggleBar — top-level pill navigation (cockpit nav per ADR-198 v2).
 *
 * Current segments (post-ADR-199 + ADR-200): Overview | Work | Files | Agents | Review
 *   - Overview: "What's going on? What needs me?" (HOME — ADR-199)
 *   - Work: "Let me check the work." (tasks + schedules + outputs)
 *   - Files (nav label) / Context (route): "What does my workspace know?"
 *   - Agents: "Who's on my team?" (rename to Team in ADR-201)
 *   - Review: "Who decided what, why?" (Reviewer identity + principles + decisions — ADR-200)
 *
 * YARNNN is ambient — available as a right-rail panel on every surface
 * via ThreePanelLayout. /chat is the expanded form of the rail, reachable
 * by direct URL or rail-expand — not a primary nav tab.
 *
 * Remaining phase (per ADR-198 v2):
 *   - ADR-201: Agents → Team rename + cross-linking to Work
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Briefcase, Users, FolderOpen, ShieldCheck } from 'lucide-react';
import { cn } from '@/lib/utils';

const SEGMENTS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard, href: '/overview' },
  { id: 'work', label: 'Work', icon: Briefcase, href: '/work' },
  { id: 'context', label: 'Files', icon: FolderOpen, href: '/context' },
  { id: 'agents', label: 'Agents', icon: Users, href: '/agents' },
  { id: 'review', label: 'Review', icon: ShieldCheck, href: '/review' },
] as const;

export function ToggleBar() {
  const pathname = usePathname();

  const activeId = SEGMENTS.find(s =>
    pathname === s.href || pathname.startsWith(s.href + '/')
  )?.id ?? 'overview';

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
