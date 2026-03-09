'use client';

/**
 * Drawer panel components for the Deliverable Workspace page.
 *
 * Extracted from deliverables/[id]/page.tsx for maintainability.
 * Includes: MemoryPanel, InstructionsPanel, SessionsPanel
 *
 * InstructionsPanel consolidates instruction-related fields into a
 * structured editor with live prompt preview (ADR-087 Phase 3):
 * - Behavior Directives (deliverable_instructions)
 * - Audience (recipient_context — moved from Settings)
 * - Output Format (template_structure.format_notes — custom type only)
 * - Prompt Preview (client-side composition of what the agent sees)
 */

import { useState } from 'react';
import {
  Loader2,
  CheckCircle2,
  Target,
  ChevronDown,
  Eye,
} from 'lucide-react';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import type {
  Deliverable,
  DeliverableSession,
  RecipientContext,
  TemplateStructure,
  DeliverableMemory,
} from '@/types';

// =============================================================================
// MemoryPanel
// =============================================================================

export function MemoryPanel({ deliverable }: { deliverable: Deliverable }) {
  const memory = deliverable.deliverable_memory;
  const observations = memory?.observations || [];
  const reviewLog = memory?.review_log || [];
  const goal = memory?.goal;

  if (observations.length === 0 && reviewLog.length === 0 && !goal) {
    return (
      <div className="p-4 text-center">
        <p className="text-sm text-muted-foreground py-4">
          No observations yet. The agent accumulates knowledge as it processes content for this deliverable.
        </p>
      </div>
    );
  }

  const actionColors: Record<string, string> = {
    generate: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    observe: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    sleep: 'bg-gray-100 text-gray-600 dark:bg-gray-800/50 dark:text-gray-400',
  };

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
      {reviewLog.length > 0 && (
        <>
          <div className="flex items-center gap-1.5 pt-1">
            <span className="text-xs font-medium text-muted-foreground">Review History</span>
          </div>
          {reviewLog.slice(-5).map((entry, i) => (
            <div key={`review-${i}`} className="p-2.5 bg-muted/30 border border-border rounded-md">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
                <span>{entry.date}</span>
                <span className={cn('px-1.5 py-0.5 rounded text-[10px] font-medium', actionColors[entry.action] || actionColors.observe)}>
                  {entry.action}
                </span>
              </div>
              <p className="text-sm">{entry.note}</p>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

// =============================================================================
// Prompt Preview Helper
// =============================================================================

function composePromptPreview(
  instructions: string,
  recipient: RecipientContext,
  templateStructure: TemplateStructure | undefined,
  deliverableType: string,
  memory?: DeliverableMemory,
): string {
  const parts: string[] = [];

  // System prompt: instructions section
  if (instructions.trim()) {
    parts.push('## Deliverable Instructions');
    parts.push('The user has set these behavioral directives for this deliverable:');
    parts.push(instructions.trim());
  }

  // System prompt: memory section (read-only, from deliverable_memory)
  if (memory) {
    const memParts: string[] = [];
    if (memory.goal) {
      memParts.push(`**Goal:** ${memory.goal.description}`);
      if (memory.goal.status) memParts.push(`Goal status: ${memory.goal.status}`);
    }
    if (memory.observations?.length) {
      memParts.push('**Recent observations:**');
      memory.observations.slice(-5).forEach(obs => {
        memParts.push(`- ${obs.date}: ${obs.note}`);
      });
    }
    if (memory.review_log?.length) {
      memParts.push('**Review history:**');
      memory.review_log.slice(-3).forEach(entry => {
        memParts.push(`- ${entry.date}: ${entry.note}`);
      });
    }
    if (memParts.length) {
      parts.push('');
      parts.push('## Deliverable Memory');
      parts.push(memParts.join('\n'));
    }
  }

  // User message: recipient context
  if (recipient.name || recipient.role) {
    parts.push('');
    parts.push('---');
    parts.push('*(In the user message:)*');
    let line = `RECIPIENT: ${recipient.name || '(unnamed)'}`;
    if (recipient.role) line += ` (${recipient.role})`;
    parts.push(line);
    if (recipient.priorities?.length) {
      parts.push(`PRIORITIES: ${recipient.priorities.join(', ')}`);
    }
  }

  // Custom type: structure notes
  if (deliverableType === 'custom' && templateStructure?.format_notes) {
    parts.push('');
    parts.push('STRUCTURE NOTES:');
    parts.push(templateStructure.format_notes);
  }

  return parts.join('\n');
}

// =============================================================================
// InstructionsPanel — Structured editor with prompt preview (ADR-087 Phase 3)
// =============================================================================

export function InstructionsPanel({
  instructions,
  onInstructionsChange,
  onBlur,
  recipientContext,
  onRecipientChange,
  templateStructure,
  onTemplateChange,
  deliverableType,
  deliverableMemory,
  saving,
  saved,
}: {
  instructions: string;
  onInstructionsChange: (v: string) => void;
  onBlur: () => void;
  recipientContext: RecipientContext;
  onRecipientChange: (v: RecipientContext) => void;
  templateStructure?: TemplateStructure;
  onTemplateChange?: (v: TemplateStructure) => void;
  deliverableType: string;
  deliverableMemory?: DeliverableMemory;
  saving: boolean;
  saved: boolean;
}) {
  const [audienceOpen, setAudienceOpen] = useState(
    !!(recipientContext.name || recipientContext.role || recipientContext.notes)
  );
  const [previewOpen, setPreviewOpen] = useState(false);

  const hasAnyContent = !!(
    instructions.trim() ||
    recipientContext.name ||
    recipientContext.role ||
    (deliverableType === 'custom' && templateStructure?.format_notes)
  );

  const preview = composePromptPreview(
    instructions,
    recipientContext,
    templateStructure,
    deliverableType,
    deliverableMemory,
  );

  return (
    <div className="p-3 space-y-4">
      {/* Section A: Behavior Directives */}
      <div>
        <label className="block text-xs font-medium mb-1">Behavior</label>
        <p className="text-[10px] text-muted-foreground mb-1.5">
          How should the agent approach this deliverable?
        </p>
        <textarea
          value={instructions}
          onChange={(e) => onInstructionsChange(e.target.value)}
          onBlur={onBlur}
          placeholder={
            'Examples:\n' +
            'Use formal tone for this board report.\n' +
            'Always include an executive summary section.\n' +
            'Focus on trend analysis rather than raw numbers.\n' +
            'The audience is the executive team.'
          }
          className="w-full min-h-[120px] px-3 py-2 text-sm font-mono bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary/20 resize-y placeholder:text-muted-foreground/60"
        />
      </div>

      {/* Section B: Audience (recipient_context) */}
      <div className="border border-border rounded-md overflow-hidden">
        <button
          type="button"
          onClick={() => setAudienceOpen(!audienceOpen)}
          className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium hover:bg-muted/50 transition-colors"
        >
          <span>Audience</span>
          <ChevronDown className={cn(
            'w-3.5 h-3.5 text-muted-foreground transition-transform',
            audienceOpen && 'rotate-180'
          )} />
        </button>
        {audienceOpen && (
          <div className="px-3 pb-3 space-y-2 border-t border-border">
            <p className="text-[10px] text-muted-foreground pt-2">
              Personalizes output for your audience
            </p>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="text"
                value={recipientContext.name || ''}
                onChange={(e) => onRecipientChange({ ...recipientContext, name: e.target.value || undefined })}
                onBlur={onBlur}
                placeholder="Name"
                className="px-2 py-1.5 border border-border rounded-md text-xs focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
              <input
                type="text"
                value={recipientContext.role || ''}
                onChange={(e) => onRecipientChange({ ...recipientContext, role: e.target.value || undefined })}
                onBlur={onBlur}
                placeholder="Role"
                className="px-2 py-1.5 border border-border rounded-md text-xs focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <textarea
              value={recipientContext.notes || ''}
              onChange={(e) => onRecipientChange({ ...recipientContext, notes: e.target.value || undefined })}
              onBlur={onBlur}
              placeholder="Notes (e.g., prefers bullet points, wants metrics upfront)"
              rows={2}
              className="w-full px-2 py-1.5 border border-border rounded-md text-xs focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none"
            />
          </div>
        )}
      </div>

      {/* Section C: Output Format (custom type only) */}
      {deliverableType === 'custom' && onTemplateChange && (
        <div>
          <label className="block text-xs font-medium mb-1">Output Format</label>
          <p className="text-[10px] text-muted-foreground mb-1.5">
            Structure and formatting guidance
          </p>
          <textarea
            value={templateStructure?.format_notes || ''}
            onChange={(e) => onTemplateChange({
              ...templateStructure,
              format_notes: e.target.value || undefined,
            })}
            onBlur={onBlur}
            placeholder="e.g., Start with executive summary. Use bullet points. Max 500 words."
            rows={3}
            className="w-full px-3 py-2 text-sm font-mono bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary/20 resize-y placeholder:text-muted-foreground/60"
          />
        </div>
      )}

      {/* Section D: Prompt Preview */}
      <div className="border border-border rounded-md overflow-hidden">
        <button
          type="button"
          onClick={() => setPreviewOpen(!previewOpen)}
          className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium hover:bg-muted/50 transition-colors"
        >
          <span className="flex items-center gap-1.5">
            <Eye className="w-3 h-3 text-muted-foreground" />
            What the agent sees
          </span>
          <ChevronDown className={cn(
            'w-3.5 h-3.5 text-muted-foreground transition-transform',
            previewOpen && 'rotate-180'
          )} />
        </button>
        {previewOpen && (
          <div className="border-t border-border bg-muted/20">
            {hasAnyContent || deliverableMemory ? (
              <pre className="px-3 py-2 text-[11px] font-mono text-muted-foreground whitespace-pre-wrap overflow-x-auto max-h-[300px] overflow-y-auto">
                {preview}
              </pre>
            ) : (
              <p className="px-3 py-3 text-xs text-muted-foreground italic">
                No instructions set — the agent will use type defaults.
              </p>
            )}
          </div>
        )}
      </div>

      {/* Save indicator */}
      <div className="flex items-center justify-end h-5">
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
