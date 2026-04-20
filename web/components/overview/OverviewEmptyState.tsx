'use client';

/**
 * OverviewEmptyState — day-zero welcome for new operators (ADR-199).
 *
 * Rendered when the workspace has zero agents, zero active tasks, and
 * zero pending proposals. Matches ADR-161 heartbeat discipline: never
 * silent, always a call to action.
 *
 * Not a separate route — rendered inline by OverviewSurface when a
 * day-zero signal is detected. Cold-starts trigger the YARNNN rail with
 * a seeded prompt on click.
 */

import { Sparkles, Plug, FilePlus } from 'lucide-react';

export interface OverviewEmptyStateProps {
  onOpenChatDraft: (prompt: string) => void;
}

export function OverviewEmptyState({ onOpenChatDraft }: OverviewEmptyStateProps) {
  return (
    <div className="flex flex-1 items-center justify-center px-6 py-16">
      <div className="max-w-md text-center">
        <Sparkles className="mx-auto mb-4 h-8 w-8 text-muted-foreground/40" />
        <h2 className="text-lg font-medium text-foreground">
          Your workforce is here.
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Connect a platform or describe your work to activate it. YARNNN will
          help you build the team.
        </p>
        <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-center">
          <button
            onClick={() =>
              onOpenChatDraft(
                "Help me set up my workspace. I'll describe my work and you can suggest agents to start with.",
              )
            }
            className="inline-flex items-center gap-1.5 rounded-md bg-foreground px-3 py-1.5 text-sm font-medium text-background hover:opacity-90"
          >
            <FilePlus className="h-3.5 w-3.5" />
            Describe my work
          </button>
          <a
            href="/integrations"
            className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <Plug className="h-3.5 w-3.5" />
            Connect a platform
          </a>
        </div>
      </div>
    </div>
  );
}
