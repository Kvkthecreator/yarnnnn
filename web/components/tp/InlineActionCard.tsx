'use client';

/**
 * InlineActionCard — Pre-LLM structured options rendered in chat area.
 *
 * Appears instantly when user clicks a PlusMenu action or panel button.
 * No LLM call — purely frontend. User picks an option or types specifics,
 * which composes a specific message sent to TP.
 *
 * Pattern: button click → card appears → user picks → message sent → TP acts
 */

import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ActionCardOption {
  label: string;
  /** Message sent to TP when this option is selected */
  message: string;
}

export interface ActionCardConfig {
  /** Card title — what action is being configured */
  title: string;
  /** Brief context shown below title */
  description?: string;
  /** Structured options the user can pick */
  options: ActionCardOption[];
  /** Placeholder for free-text input as alternative to options */
  inputPlaceholder?: string;
}

interface InlineActionCardProps {
  config: ActionCardConfig;
  onSelect: (message: string) => void;
  onDismiss: () => void;
}

export function InlineActionCard({ config, onSelect, onDismiss }: InlineActionCardProps) {
  return (
    <div className="space-y-2 bg-muted/50 rounded-lg p-3 border border-border animate-in fade-in slide-in-from-bottom-2 duration-150">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium">{config.title}</p>
          {config.description && (
            <p className="text-[10px] text-muted-foreground/60 mt-0.5">{config.description}</p>
          )}
        </div>
        <button
          onClick={onDismiss}
          className="p-0.5 text-muted-foreground/30 hover:text-muted-foreground rounded"
        >
          <X className="w-3 h-3" />
        </button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {config.options.map((opt, i) => (
          <button
            key={i}
            onClick={() => onSelect(opt.message)}
            className="px-2.5 py-1 text-[11px] rounded-lg border border-primary/30 bg-primary/5 text-primary hover:bg-primary/15 font-medium transition-colors"
          >
            {opt.label}
          </button>
        ))}
      </div>
      {config.inputPlaceholder && (
        <p className="text-[9px] text-muted-foreground/40 pt-0.5">
          Or type specifics in the input below
        </p>
      )}
    </div>
  );
}

// =============================================================================
// Pre-defined action card configs
// =============================================================================

/** Recurrence detail: "Run this" action */
export const RUN_TASK_CARD: ActionCardConfig = {
  title: 'Run this recurrence',
  options: [
    { label: 'Run now', message: 'Run this now' },
    { label: 'Run with special focus', message: 'Run this with focus on ' },
  ],
};

/** Recurrence detail: "Adjust this" action */
export const ADJUST_TASK_CARD: ActionCardConfig = {
  title: 'Adjust this recurrence',
  description: 'What would you like to change?',
  options: [
    { label: 'Focus area', message: 'Change the focus of this recurrence to ' },
    { label: 'Success criteria', message: 'Update the success criteria for this recurrence' },
    { label: 'Schedule', message: 'Change the schedule for this recurrence' },
    { label: 'Delivery', message: 'Change the delivery for this recurrence' },
  ],
  inputPlaceholder: 'Or describe the adjustment',
};

/** Recurrence detail: "Research for this" action */
export const RESEARCH_TASK_CARD: ActionCardConfig = {
  title: 'Web research',
  description: 'What should I look into?',
  options: [
    { label: 'Latest trends', message: 'Research latest trends relevant to this recurrence' },
    { label: 'Competitor activity', message: 'Research competitor activity for this recurrence' },
    { label: 'Industry news', message: 'Research recent industry news for this recurrence' },
  ],
  inputPlaceholder: 'Or describe what to research',
};

/** Recurrence detail: "Give feedback" on latest output */
export const FEEDBACK_TASK_CARD: ActionCardConfig = {
  title: 'Feedback on output',
  description: 'How was the latest output?',
  options: [
    { label: 'Good — keep this direction', message: 'The latest output was good, keep this direction' },
    { label: 'Needs more depth', message: 'The latest output needs more depth on ' },
    { label: 'Wrong focus', message: 'The latest output focused on the wrong things — it should focus on ' },
    { label: 'Too long / too short', message: 'The latest output was too ' },
    { label: 'Update criteria based on this', message: 'Based on the latest output, update the success criteria to ' },
  ],
  inputPlaceholder: 'Or describe what to improve',
};
