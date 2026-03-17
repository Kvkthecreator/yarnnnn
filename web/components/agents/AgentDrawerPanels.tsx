'use client';

/**
 * Drawer panel components for the Agent Workspace page.
 *
 * Extracted from agents/[id]/page.tsx for maintainability.
 * Includes: MemoryPanel, InstructionsPanel, SessionsPanel
 *
 * InstructionsPanel is a read-only reference view (ADR-105):
 * - Behavior Directives (agent_instructions) — read-only display
 * - Audience (recipient_context) — read-only summary
 * - Prompt Preview (client-side composition of what the agent sees)
 * - "Edit in chat" affordance to direct users to the chat surface
 *
 * Instruction editing flows through chat (TP uses Edit primitive).
 * See docs/design/SURFACE-ACTION-MAPPING.md for the design principle.
 */

import { useState } from 'react';
import {
  Target,
  ChevronDown,
  Eye,
  MessageSquare,
  Lightbulb,
  Shield,
} from 'lucide-react';
import { format } from 'date-fns';
import ReactMarkdown from 'react-markdown';
import { cn } from '@/lib/utils';
import type {
  Agent,
  AgentSession,
  RecipientContext,
  AgentMemory,
} from '@/types';

// =============================================================================
// MemoryPanel
// =============================================================================

export function MemoryPanel({ agent }: { agent: Agent }) {
  const memory = agent.agent_memory;
  const observations = memory?.observations || [];
  const reviewLog = memory?.review_log || [];
  const goal = memory?.goal;
  const preferences = memory?.preferences;
  const supervisorNotes = memory?.supervisor_notes;

  if (observations.length === 0 && reviewLog.length === 0 && !goal && !preferences && !supervisorNotes) {
    return (
      <div className="p-4 text-center">
        <p className="text-sm text-muted-foreground py-4">
          No memory yet. The agent accumulates knowledge as it runs and receives feedback.
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
      {preferences && (
        <div className="p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-md">
          <div className="flex items-center gap-1.5 mb-1.5">
            <Lightbulb className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
            <span className="text-xs font-medium text-emerald-700 dark:text-emerald-400">Learned Preferences</span>
          </div>
          <div className="text-sm prose prose-sm dark:prose-invert max-w-none prose-p:my-1 prose-headings:text-xs prose-headings:font-medium prose-headings:mt-2 prose-headings:mb-0.5 prose-ul:my-0.5 prose-li:my-0">
            <ReactMarkdown>{preferences}</ReactMarkdown>
          </div>
        </div>
      )}
      {supervisorNotes && (
        <div className="p-3 bg-violet-50 dark:bg-violet-900/20 border border-violet-200 dark:border-violet-800 rounded-md">
          <div className="flex items-center gap-1.5 mb-1.5">
            <Shield className="w-3.5 h-3.5 text-violet-600 dark:text-violet-400" />
            <span className="text-xs font-medium text-violet-700 dark:text-violet-400">Supervisor Notes</span>
          </div>
          <div className="text-sm prose prose-sm dark:prose-invert max-w-none prose-p:my-1 prose-headings:text-xs prose-headings:font-medium prose-headings:mt-2 prose-headings:mb-0.5 prose-ul:my-0.5 prose-li:my-0">
            <ReactMarkdown>{supervisorNotes}</ReactMarkdown>
          </div>
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
  memory?: AgentMemory,
): string {
  const parts: string[] = [];

  // System prompt: instructions section
  if (instructions.trim()) {
    parts.push('## Agent Instructions');
    parts.push('The user has set these behavioral directives for this agent:');
    parts.push(instructions.trim());
  }

  // System prompt: learned preferences (ADR-117 — high salience injection)
  if (memory?.preferences) {
    parts.push('');
    parts.push('## Learned Preferences (from user edit history)');
    parts.push(memory.preferences);
    parts.push('');
    parts.push('Follow these preferences closely — they reflect what the user has consistently edited in past outputs.');
  }

  // System prompt: memory section (read-only, from agent_memory)
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
    if (memory.supervisor_notes) {
      memParts.push('**Supervisor coaching:**');
      memParts.push(memory.supervisor_notes);
    }
    if (memParts.length) {
      parts.push('');
      parts.push('## Agent Memory');
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

  return parts.join('\n');
}

// =============================================================================
// InstructionsPanel — Read-only reference view (ADR-105)
//
// Directives flow through chat (TP uses Edit primitive to persist).
// This panel shows current state for reference + "Edit in chat" affordance.
// =============================================================================

export function InstructionsPanel({
  agent,
  onEditInChat,
}: {
  agent: Agent;
  onEditInChat?: () => void;
}) {
  const instructions = agent.agent_instructions || '';
  const recipient = agent.recipient_context || {};
  const memory = agent.agent_memory;
  const [previewOpen, setPreviewOpen] = useState(false);

  const hasAnyContent = !!(
    instructions.trim() ||
    recipient.name ||
    recipient.role
  );

  const preview = composePromptPreview(instructions, recipient, memory);

  const hasAudience = !!(recipient.name || recipient.role || recipient.notes);

  return (
    <div className="p-3 space-y-4">
      {/* Edit in chat affordance */}
      {onEditInChat && (
        <button
          type="button"
          onClick={onEditInChat}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-medium text-primary border border-primary/30 rounded-md hover:bg-primary/5 transition-colors"
        >
          <MessageSquare className="w-3.5 h-3.5" />
          Edit in chat
        </button>
      )}

      {/* Section A: Behavior Directives (read-only) */}
      <div>
        <label className="block text-xs font-medium mb-1">Behavior</label>
        {instructions.trim() ? (
          <div className="px-3 py-2 text-sm font-mono bg-muted/30 border border-border rounded-md whitespace-pre-wrap">
            {instructions}
          </div>
        ) : (
          <p className="px-3 py-2 text-sm text-muted-foreground italic border border-border rounded-md bg-muted/10">
            No instructions set — tell the agent in chat what this agent should focus on.
          </p>
        )}
      </div>

      {/* Section B: Audience (read-only) */}
      {hasAudience && (
        <div>
          <label className="block text-xs font-medium mb-1">Audience</label>
          <div className="px-3 py-2 border border-border rounded-md bg-muted/30 space-y-1">
            {(recipient.name || recipient.role) && (
              <p className="text-sm">
                {recipient.name || '(unnamed)'}
                {recipient.role && <span className="text-muted-foreground"> — {recipient.role}</span>}
              </p>
            )}
            {recipient.priorities && recipient.priorities.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Priorities: {recipient.priorities.join(', ')}
              </p>
            )}
            {recipient.notes && (
              <p className="text-xs text-muted-foreground">{recipient.notes}</p>
            )}
          </div>
        </div>
      )}

      {/* Section C: Prompt Preview */}
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
            {hasAnyContent || memory ? (
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
    </div>
  );
}

// =============================================================================
// SessionsPanel
// =============================================================================

export function SessionsPanel({ sessions }: { sessions: AgentSession[] }) {
  if (sessions.length === 0) {
    return (
      <div className="p-4 text-center">
        <p className="text-sm text-muted-foreground py-4">
          Send a message to start a session.
        </p>
      </div>
    );
  }

  const today = new Date().toDateString();

  return (
    <div className="p-3 space-y-2">
      {sessions.map((session) => {
        const isToday = new Date(session.created_at).toDateString() === today;
        return (
          <div key={session.id} className={cn(
            'p-2.5 border rounded-md',
            isToday ? 'bg-primary/5 border-primary/20' : 'bg-muted/30 border-border'
          )}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-muted-foreground flex items-center gap-1.5">
                {isToday && <span className="text-[10px] font-medium text-primary">Current</span>}
                {format(new Date(session.created_at), 'MMM d, h:mm a')}
              </span>
              <span className="text-xs text-muted-foreground">
                {session.message_count} message{session.message_count !== 1 ? 's' : ''}
              </span>
            </div>
            {session.summary ? (
              <p className="text-sm line-clamp-2">{session.summary}</p>
            ) : isToday ? (
              <p className="text-sm text-muted-foreground italic">In progress</p>
            ) : (
              <p className="text-sm text-muted-foreground italic">No summary</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
