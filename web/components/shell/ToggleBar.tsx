'use client';

/**
 * ToggleBar — top-level pill navigation (cockpit nav per ADR-205 F1+F2).
 *
 * Current segments: Chat | Work | Files | Team | Review
 *   - Chat: "Tell YARNNN what you want." (authoring surface, HOME — ADR-205 F1)
 *   - Work: "Let me check the work." (task list with briefing strip + detail — ADR-205 F2)
 *   - Files (nav label) / Context (route): "What does my workspace know?"
 *   - Team: "Let me check on my agents." (agents-as-identity surface — ADR-201)
 *   - Review: "Who decided what, why?" (Reviewer identity + principles + decisions — ADR-200)
 *
 * ADR-205 F1 (2026-04-22): Chat returns as the first nav tab — a brand-new workspace
 * has zero authored agents and zero authored tasks, so the first meaningful action
 * must be conversational.
 *
 * ADR-205 F2 (2026-04-22): Overview's Briefing panes (NeedsMe queue, Since-last-look,
 * snapshot tiles, IntelligenceCard) moved into /work list-mode as a BriefingStrip.
 * /overview is a redirect stub for old bookmarks.
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { MessageSquare, Briefcase, Users, FolderOpen, ShieldCheck } from 'lucide-react';
import { cn } from '@/lib/utils';

const SEGMENTS = [
  { id: 'chat', label: 'Chat', icon: MessageSquare, href: '/chat' },
  { id: 'work', label: 'Work', icon: Briefcase, href: '/work' },
  { id: 'context', label: 'Files', icon: FolderOpen, href: '/context' },
  { id: 'team', label: 'Team', icon: Users, href: '/team' },
  { id: 'review', label: 'Review', icon: ShieldCheck, href: '/review' },
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
