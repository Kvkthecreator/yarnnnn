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

/** Workfloor: "Update my {target}" action */
export function contextUpdateCard(target: string): ActionCardConfig {
  return {
    title: `Update ${target}`,
    description: target === 'documents' ? undefined : `What would you like to change about your ${target}?`,
    options: target === 'documents' ? [
      { label: 'Upload a file', message: 'I want to upload a document' },
    ] : [
      { label: 'Add new details', message: `Add new details to my ${target}` },
      { label: 'Update from a URL', message: `Update my ${target} from ` },
      { label: 'Update from an uploaded doc', message: `Update my ${target} from my uploaded documents` },
      { label: 'Rewrite from scratch', message: `Rewrite my ${target}` },
    ],
    inputPlaceholder: 'Or describe the change',
  };
}

/** Workfloor: "Create a new task" action */
export const NEW_TASK_CARD: ActionCardConfig = {
  title: 'Create a new task',
  description: 'What kind of recurring work do you need?',
  options: [
    { label: 'Market research', message: 'Create a market research task' },
    { label: 'Competitive intel', message: 'Create a competitive intelligence task' },
    { label: 'Content brief', message: 'Create a content brief task' },
    { label: 'Platform digest', message: 'Create a platform digest task' },
    { label: 'Something else', message: 'Create a task for ' },
  ],
  inputPlaceholder: 'Or describe the task',
};

/** Task page: "Run this task" action */
export const RUN_TASK_CARD: ActionCardConfig = {
  title: 'Run this task',
  options: [
    { label: 'Run now', message: 'Run this task now' },
    { label: 'Run with special focus', message: 'Run this task with focus on ' },
  ],
};

/** Task page: "Adjust this task" action */
export const ADJUST_TASK_CARD: ActionCardConfig = {
  title: 'Adjust this task',
  description: 'What would you like to change?',
  options: [
    { label: 'Focus area', message: 'Change the focus of this task to ' },
    { label: 'Success criteria', message: 'Update the success criteria for this task' },
    { label: 'Schedule', message: 'Change the schedule for this task' },
    { label: 'Delivery', message: 'Change the delivery for this task' },
  ],
  inputPlaceholder: 'Or describe the adjustment',
};

/** Task page: "Research for this task" action */
export const RESEARCH_TASK_CARD: ActionCardConfig = {
  title: 'Web research',
  description: 'What should I look into?',
  options: [
    { label: 'Latest trends', message: 'Research latest trends relevant to this task' },
    { label: 'Competitor activity', message: 'Research competitor activity for this task' },
    { label: 'Industry news', message: 'Research recent industry news for this task' },
  ],
  inputPlaceholder: 'Or describe what to research',
};

/** Task page: "Give feedback" on latest output */
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
