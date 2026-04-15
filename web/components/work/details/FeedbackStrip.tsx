'use client';

/**
 * FeedbackStrip — ADR-181 Phase 4a.
 *
 * Thin feedback bar below KindMiddle in WorkDetail. Three affordances per
 * output_kind, all prompt relays to TP chat (no new primitives, no CRUD).
 *
 * Only rendered when the task has at least one run (last_run_at is set).
 * system_maintenance tasks: no strip (TP-owned, no user feedback loop).
 */

import { ThumbsUp, AlertCircle, MessageSquare } from 'lucide-react';
import type { Task } from '@/types';

interface FeedbackStripProps {
  task: Task;
  onOpenChat: (prompt: string) => void;
}

// Per-output_kind button configs
interface StripButton {
  label: string;
  icon: typeof ThumbsUp;
  prompt: string;
  variant: 'primary' | 'secondary' | 'edit';
}

function getButtons(task: Task): StripButton[] {
  const title = task.title || task.slug;
  const kind = task.output_kind ?? 'produces_deliverable';
  const isDaily = task.essential === true;

  switch (kind) {
    case 'produces_deliverable': {
      const buttons: StripButton[] = [];
      // Daily update: no "looks good" (ambient, not evaluated per FEEDBACK-LOOP.md)
      if (!isDaily) {
        buttons.push({
          label: 'Looks good',
          icon: ThumbsUp,
          prompt: `This output from "${title}" looks good. Note it for future runs.`,
          variant: 'primary',
        });
      }
      buttons.push({
        label: "Something's off",
        icon: AlertCircle,
        prompt: `I want to change something about the "${title}" output: `,
        variant: 'secondary',
      });
      buttons.push({
        label: 'Edit in TP',
        icon: MessageSquare,
        prompt: `Edit the latest "${title}" output: `,
        variant: 'edit',
      });
      return buttons;
    }

    case 'accumulates_context':
      return [
        {
          label: 'Looks comprehensive',
          icon: ThumbsUp,
          prompt: `The "${title}" context looks comprehensive. Keep it up.`,
          variant: 'primary',
        },
        {
          label: 'Missing something',
          icon: AlertCircle,
          prompt: `The "${title}" context is missing: `,
          variant: 'secondary',
        },
        {
          label: 'Edit in TP',
          icon: MessageSquare,
          prompt: `Adjust what "${title}" tracks: `,
          variant: 'edit',
        },
      ];

    case 'external_action':
      return [
        {
          label: 'Delivery was right',
          icon: ThumbsUp,
          prompt: `The "${title}" delivery looked right.`,
          variant: 'primary',
        },
        {
          label: "Adjust what's sent",
          icon: AlertCircle,
          prompt: `Change what "${title}" sends: `,
          variant: 'secondary',
        },
        {
          label: 'Edit in TP',
          icon: MessageSquare,
          prompt: `Edit "${title}" settings: `,
          variant: 'edit',
        },
      ];

    case 'system_maintenance':
    default:
      return []; // No feedback strip for system tasks
  }
}

const VARIANT_STYLES: Record<string, string> = {
  primary:
    'text-primary/70 hover:text-primary hover:bg-primary/5 border-primary/20',
  secondary:
    'text-muted-foreground hover:text-foreground hover:bg-muted/60 border-border',
  edit:
    'text-muted-foreground hover:text-foreground hover:bg-muted/60 border-border',
};

export function FeedbackStrip({ task, onOpenChat }: FeedbackStripProps) {
  // Only show when task has produced output
  if (!task.last_run_at) return null;

  const buttons = getButtons(task);
  if (buttons.length === 0) return null;

  return (
    <div className="px-6 py-3 border-t border-border/30 flex items-center gap-2 flex-wrap">
      <span className="text-[10px] font-medium text-muted-foreground/40 uppercase tracking-wider mr-1">
        Feedback
      </span>
      {buttons.map((btn) => (
        <button
          key={btn.label}
          onClick={() => onOpenChat(btn.prompt)}
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] rounded-md border transition-colors ${VARIANT_STYLES[btn.variant] ?? VARIANT_STYLES.secondary}`}
        >
          <btn.icon className="w-3 h-3" />
          {btn.label}
        </button>
      ))}
    </div>
  );
}
