'use client';

/**
 * Drawer panel components for the Deliverable Workspace page.
 *
 * Extracted from deliverables/[id]/page.tsx for maintainability.
 * Includes: MemoryPanel, InstructionsPanel, SessionsPanel
 */

import {
  Loader2,
  CheckCircle2,
  Target,
} from 'lucide-react';
import { format } from 'date-fns';
import type { Deliverable, DeliverableSession } from '@/types';

// =============================================================================
// MemoryPanel
// =============================================================================

export function MemoryPanel({ deliverable }: { deliverable: Deliverable }) {
  const memory = deliverable.deliverable_memory;
  const observations = memory?.observations || [];
  const goal = memory?.goal;

  if (observations.length === 0 && !goal) {
    return (
      <div className="p-4 text-center">
        <p className="text-sm text-muted-foreground py-4">
          No observations yet. The agent accumulates knowledge as it processes content for this deliverable.
        </p>
      </div>
    );
  }

  return (
    <div className="p-3 space-y-2.5">
      {goal && (
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
          <div className="flex items-center gap-1.5 mb-1">
            <Target className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
            <span className="text-xs font-medium text-blue-700 dark:text-blue-400">Goal</span>
          </div>
          <p className="text-sm">{goal.description}</p>
          <p className="text-xs text-muted-foreground mt-1">Status: {goal.status}</p>
          {goal.milestones && goal.milestones.length > 0 && (
            <ul className="mt-1.5 space-y-1">
              {goal.milestones.map((m, i) => (
                <li key={i} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span className="w-1 h-1 rounded-full bg-muted-foreground/40 shrink-0" />
                  {m}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {observations.map((obs, i) => (
        <div key={i} className="p-2.5 bg-muted/30 border border-border rounded-md">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
            <span>{obs.date}</span>
            {obs.source && (
              <>
                <span className="text-border">&middot;</span>
                <span>{obs.source}</span>
              </>
            )}
          </div>
          <p className="text-sm">{obs.note}</p>
        </div>
      ))}
    </div>
  );
}

// =============================================================================
// InstructionsPanel
// =============================================================================

export function InstructionsPanel({
  instructions,
  onChange,
  onBlur,
  saving,
  saved,
}: {
  instructions: string;
  onChange: (v: string) => void;
  onBlur: () => void;
  saving: boolean;
  saved: boolean;
}) {
  return (
    <div className="p-3">
      <textarea
        value={instructions}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        placeholder={
          'Add instructions for how the agent should approach this deliverable. Examples:\n\n' +
          'Use formal tone for this board report.\n' +
          'Always include an executive summary section.\n' +
          'Focus on trend analysis rather than raw numbers.\n' +
          'The audience is the executive team.'
        }
        className="w-full min-h-[160px] px-3 py-2 text-sm font-mono bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary/20 resize-y placeholder:text-muted-foreground/60"
      />
      <div className="flex items-center justify-end mt-1.5 h-5">
        {saving && (
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <Loader2 className="w-3 h-3 animate-spin" /> Saving...
          </span>
        )}
        {saved && !saving && (
          <span className="text-xs text-green-600 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Saved
          </span>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// SessionsPanel
// =============================================================================

export function SessionsPanel({ sessions }: { sessions: DeliverableSession[] }) {
  if (sessions.length === 0) {
    return (
      <div className="p-4 text-center">
        <p className="text-sm text-muted-foreground py-4">
          No scoped conversations yet. Chat with this deliverable open to build session history.
        </p>
      </div>
    );
  }

  return (
    <div className="p-3 space-y-2">
      {sessions.map((session) => (
        <div key={session.id} className="p-2.5 bg-muted/30 border border-border rounded-md">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-muted-foreground">
              {format(new Date(session.created_at), 'MMM d, h:mm a')}
            </span>
            <span className="text-xs text-muted-foreground">
              {session.message_count} message{session.message_count !== 1 ? 's' : ''}
            </span>
          </div>
          {session.summary ? (
            <p className="text-sm line-clamp-2">{session.summary}</p>
          ) : (
            <p className="text-sm text-muted-foreground italic">No summary</p>
          )}
        </div>
      ))}
    </div>
  );
}
