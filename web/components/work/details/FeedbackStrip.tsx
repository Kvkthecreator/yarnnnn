'use client';

/**
 * FeedbackStrip — ADR-181 Phase 4a, simplified Phase I (post-merge sweep
 * 2026-05-10).
 *
 * Thin feedback bar below MiddleResolver in WorkDetail. Single "Ask TP"
 * button that opens a chat prompt scoped to the recurrence. Kept minimal
 * — operators express feedback in conversation, not through evaluative
 * buttons.
 *
 * Rendered when the recurrence has at least one run (last_run_at is set).
 * Per ADR-261 D1's "one execution shape" principle: the prompt itself is
 * universal — no per-output_kind branching. The Reviewer reads context
 * (the recurrence's prompt + recent runs + operator's question) and
 * decides how to help.
 */

import { MessageSquare } from 'lucide-react';
import type { Recurrence } from '@/types';

interface FeedbackStripProps {
  task: Recurrence;
  onOpenChat: (prompt: string) => void;
}

export function FeedbackStrip({ task, onOpenChat }: FeedbackStripProps) {
  if (!task.last_run_at) return null;

  const title = task.title || task.slug;
  const prompt = `I want to make changes to "${title}": `;

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
