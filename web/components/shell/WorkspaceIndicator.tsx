'use client';

/**
 * WorkspaceIndicator — the ambient which-workspace + who's-here read
 * (ADR-412 D6, the "ambient context" clause).
 *
 * In a multi-workspace life the binding must be GLANCEABLE — before this,
 * the only place the active workspace showed was inside the UserMenu
 * switcher (ADR-407 Phase 5), so a member acting in a peer's commons had
 * no standing signal of where their acts would land. This chip names the
 * acting workspace in the top bar whenever the caller holds MORE THAN ONE
 * binding (N=1 users see nothing — the ADR-407 Phase 5 hidden-switcher
 * discipline, applied to chrome).
 *
 * The popover is a compact WHO'S-HERE read: the workspace's principal
 * roster — humans and AI principals — from the SAME cached members fetch
 * the viewer-resolution layer uses (one substrate, one fetch). This is
 * MEMBERSHIP, not presence: who can act here, never who is online (the
 * ADR-373 no-presence/no-realtime rejection stands). Depth lives at
 * Workspace Settings → Workspace Members (the mirror); this is the glance.
 *
 * SWITCHING stays in the UserMenu (Singular Implementation — one switcher);
 * the chip is read-only context.
 */

import { useRef, useState } from 'react';
import { Briefcase, Users, Bot, ArrowRight } from 'lucide-react';
import { usePopoverDismissal } from '@/lib/shell/usePopoverDismissal';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { Z_POPOVER } from '@/lib/shell/z-tiers';
import {
  useWorkspaceMembers,
  useWorkspaceMemberships,
} from '@/lib/workspace/viewer';
import { cn } from '@/lib/utils';

const HUMAN_ROLES = new Set(['owner', 'member']);

export function WorkspaceIndicator() {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const { memberships } = useWorkspaceMemberships();
  const { members, loaded: membersLoaded } = useWorkspaceMembers();
  const { navigateToSurface } = useSurfacePreferences();

  usePopoverDismissal(containerRef, isOpen, () => setIsOpen(false));

  // Glanceable only when there is something to disambiguate: one binding →
  // no chip (the N=1 world stays byte-identical).
  if (memberships.length <= 1) return null;

  const active = memberships.find((m) => m.is_active) ?? memberships[0];

  // Membership roster, humans first (owner, then members), then AI
  // principals (foreign-llm / a2a / platform / own-agent).
  const humans = members.filter((m) => HUMAN_ROLES.has(m.role));
  const others = members.filter((m) => !HUMAN_ROLES.has(m.role));

  const openMembersPane = () => {
    setIsOpen(false);
    navigateToSurface('workspace-settings', { pane: 'members' });
  };

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        className={cn(
          'flex h-8 items-center gap-1.5 rounded-md px-2 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground',
          isOpen && 'bg-muted text-foreground',
        )}
        title={`Acting in ${active.label}`}
        aria-label={`Workspace: ${active.label}`}
        aria-expanded={isOpen}
      >
        <Briefcase className="h-3.5 w-3.5 shrink-0" />
        <span className="hidden md:block max-w-[10rem] truncate">{active.label}</span>
      </button>

      {isOpen && (
        <div
          style={{ zIndex: Z_POPOVER }}
          className="absolute top-full right-0 mt-1 w-64 max-w-[calc(100vw-1rem)] rounded-lg border border-border bg-background shadow-lg overflow-hidden"
          role="dialog"
          aria-label="Workspace context"
        >
          <div className="px-3 py-2 border-b border-border bg-muted/30">
            <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
              You&apos;re acting in
            </p>
            <p className="text-sm font-medium truncate">{active.label}</p>
          </div>

          <div className="max-h-72 overflow-y-auto py-1">
            {!membersLoaded && (
              <p className="px-3 py-2 text-xs text-muted-foreground">Loading members…</p>
            )}
            {membersLoaded && humans.length > 0 && (
              <>
                <div className="px-3 pt-1.5 pb-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                  Members
                </div>
                {humans.map((m) => (
                  <div key={m.principal_id} className="flex items-center gap-2 px-3 py-1.5">
                    <Users className="h-3.5 w-3.5 text-muted-foreground/60 shrink-0" />
                    <span className="flex-1 min-w-0 text-xs text-foreground truncate">
                      {m.label || m.principal_id}
                    </span>
                  </div>
                ))}
              </>
            )}
            {membersLoaded && others.length > 0 && (
              <>
                <div className="px-3 pt-1.5 pb-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                  AI &amp; connections
                </div>
                {others.map((m) => (
                  <div key={m.principal_id} className="flex items-center gap-2 px-3 py-1.5">
                    <Bot className="h-3.5 w-3.5 text-muted-foreground/60 shrink-0" />
                    <span className="flex-1 min-w-0 text-xs text-foreground truncate">
                      {m.label || m.principal_id}
                    </span>
                  </div>
                ))}
              </>
            )}
          </div>

          <button
            type="button"
            onClick={openMembersPane}
            className="flex w-full items-center gap-1 border-t border-border px-3 py-2 text-left text-xs text-primary transition-colors hover:bg-muted"
          >
            Manage access
            <ArrowRight className="h-3 w-3" />
          </button>
        </div>
      )}
    </div>
  );
}
