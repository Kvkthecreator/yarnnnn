'use client';

/**
 * FeedbackStrip — ADR-181 Phase 4a.
 *
 * Thin feedback bar below MiddleResolver in WorkDetail. Single "Ask TP"
 * button that opens a chat prompt scoped to the task. Kept minimal —
 * users express feedback in conversation, not through evaluative buttons.
 *
 * Only rendered when the task has at least one run (last_run_at is set).
 * system_maintenance tasks: no strip (TP-owned, no user feedback loop).
 */

import { MessageSquare } from 'lucide-react';
import type { Recurrence } from '@/types';

interface FeedbackStripProps {
  task: Recurrence;
  onOpenChat: (prompt: string) => void;
}

function getPrompt(task: Recurrence): string | null {
  const title = task.title || task.slug;
  const kind = task.output_kind ?? 'produces_deliverable';

  switch (kind) {
    case 'produces_deliverable':
      return `I want to make changes to "${title}": `;
    case 'accumulates_context':
      return `Adjust what "${title}" tracks: `;
    case 'external_action':
      return `Change how "${title}" works: `;
    case 'system_maintenance':
    default:
      return null;
  }
}

export function FeedbackStrip({ task, onOpenChat }: FeedbackStripProps) {
  if (!task.last_run_at) return null;

  const prompt = getPrompt(task);
  if (!prompt) return null;

  return (
    <div className="px-6 py-3 border-t border-border/30 flex items-center gap-2">
      <span className="text-[10px] font-medium text-muted-foreground/40 uppercase tracking-wider mr-1">
        Feedback
      </span>
      <button
        onClick={() => onOpenChat(prompt)}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] rounded-md border transition-colors text-muted-foreground hover:text-foreground hover:bg-muted/60 border-border"
      >
        <MessageSquare className="w-3 h-3" />
        Ask TP for changes
      </button>
    </div>
  );
}
