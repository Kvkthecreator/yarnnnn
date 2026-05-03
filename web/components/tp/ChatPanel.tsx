'use client';

/**
 * ChatPanel — Shared YARNNN chat component (ADR-189, ADR-190).
 *
 * Used by both the Tasks surface and Context explorer.
 * Handles message display, input, file attachments, command picker,
 * clarification UI, action cards, and token usage.
 *
 * ADR-190: the /chat surface passes `emptyState={<ChatEmptyState />}` to
 * render a deterministic welcome + chips when messages.length === 0.
 * File drop + URL paste affordances will migrate here in a later commit.
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  Loader2,
  X,
  MessageCircle,
  Send,
  Paperclip,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useDesk } from '@/contexts/DeskContext';
import { useFileAttachments } from '@/hooks/useFileAttachments';
import { useAutonomy } from '@/lib/content-shapes/autonomy';
import { cn } from '@/lib/utils';
import { CommandPicker } from '@/components/tp/CommandPicker';
import { PlusMenu, type PlusMenuAction } from '@/components/tp/PlusMenu';
import {
  InlineActionCard,
  type ActionCardConfig,
} from '@/components/tp/InlineActionCard';
import { MessageRow } from '@/components/tp/MessageRow';
import type { TPMessage } from '@/types/desk';

/**
 * ADR-219 Commit 5: query-param-driven filters on /chat.
 * Each filter narrows messages.map render. Empty / null filters render
 * the full narrative. Filter parsing is the parent's responsibility
 * (chat/page reads the URL); ChatPanel just consumes.
 */
export interface NarrativeFilter {
  /** Restrict to entries with `metadata.weight` in this set. */
  weights?: Set<'material' | 'routine' | 'housekeeping'>;
  /** Restrict to entries with `role` in this set. */
  identities?: Set<string>;
  /** Restrict to entries with `metadata.task_slug` equal to this slug. */
  taskSlug?: string | null;
}

export interface ChatPanelProps {
  /** Surface override — when set, used instead of DeskContext surface */
  surfaceOverride?: any;
  /** Prefill the input from a parent surface without auto-sending */
  draftSeed?: { id: string; text: string } | null;
  /** Plus menu actions for the input bar */
  plusMenuActions: PlusMenuAction[];
  /** Action card pushed from parent (e.g., panel header buttons) */
  pendingActionConfig?: ActionCardConfig | null;
  /** Input placeholder text */
  placeholder?: string;
  /**
   * Empty state content — rendered when no messages. Used by:
   *   - The /chat surface (ADR-190): passes a render function that receives
   *     helpers (e.g., requestUpload) so the ChatEmptyState chips can trigger
   *     composer affordances (file picker) directly.
   *   - Other surfaces (work, agents, context via ThreePanelLayout): pass a
   *     plain ReactNode with contextual "select something" guidance.
   *
   * The render-function form exposes ChatPanel's internal helpers (file
   * picker ref, future URL input focus, etc.) to the empty-state children
   * without leaking ChatPanel internals through props.
   */
  emptyState?:
    | React.ReactNode
    | ((helpers: ChatEmptyStateHelpers) => React.ReactNode);
  /** Whether to show the command picker (/ commands) */
  showCommandPicker?: boolean;
  /** Whether to render a divider above the input */
  showInputDivider?: boolean;
  /**
   * ADR-219 Commit 5: optional filter applied before render. /chat
   * passes a parsed-from-URL filter; other surfaces (where filters
   * make less sense) leave it null.
   */
  narrativeFilter?: NarrativeFilter | null;
  /**
   * ADR-219 Commit 5 D6: callback invoked when the operator clicks
   * "Make this recurring" on a material inline-action user message.
   * Parent typically opens RecurrenceSetupModal pre-filled with the message
   * text. When undefined, the affordance is hidden.
   */
  onMakeRecurring?: (messageContent: string) => void;
}

/**
 * Helpers exposed to emptyState render functions (ADR-190).
 * Add new helpers here as rich-input affordances grow (URL capture, etc.).
 */
export interface ChatEmptyStateHelpers {
  /** Opens the OS file picker for the composer's hidden file input. */
  requestUpload: () => void;
}

export function ChatPanel({
  surfaceOverride,
  draftSeed,
  plusMenuActions,
  pendingActionConfig,
  placeholder = 'Type, drop a file, or paste a link...',
  emptyState,
  showCommandPicker = true,
  showInputDivider = true,
  narrativeFilter = null,
  onMakeRecurring,
}: ChatPanelProps) {
  const {
    messages,
    sendMessage,
    isLoading,
    status,
    pendingClarification,
    respondToClarification,
  } = useTP();
  const { surface: deskSurface } = useDesk();
  const surface = surfaceOverride || deskSurface;

  const [input, setInput] = useState('');
  const [commandPickerOpen, setCommandPickerOpen] = useState(false);
  const [actionCard, setActionCard] = useState<ActionCardConfig | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // ADR-238 + inline switcher: surface autonomy posture above the composer.
  // Always visible (not just non-manual) so the operator knows their current
  // delegation level and can switch with one click. setLevel writes directly
  // to AUTONOMY.md via PATCH /api/workspace/file — zero LLM.
  const { effectiveLevel, summary: autonomySummary, setLevel: setAutonomyLevel } = useAutonomy();
  const [autonomyPopoverOpen, setAutonomyPopoverOpen] = useState(false);
  const autonomyChipRef = useRef<HTMLButtonElement>(null);

  // Accept action card from parent
  useEffect(() => {
    if (pendingActionConfig) {
      setActionCard(pendingActionConfig);
    }
  }, [pendingActionConfig]);

  // Parent surfaces can seed the input without sending immediately.
  useEffect(() => {
    if (!draftSeed?.text) return;
    setInput(draftSeed.text);
    setActionCard(null);
    requestAnimationFrame(() => textareaRef.current?.focus());
  }, [draftSeed?.id, draftSeed?.text]);

  const handleActionSelect = (message: string) => {
    if (message.endsWith(' ')) {
      setInput(message);
      setActionCard(null);
      textareaRef.current?.focus();
    } else {
      sendMessage(message, { surface });
      setActionCard(null);
    }
  };

  const {
    attachments,
    attachmentPreviews,
    error: fileError,
    uploadedDocs,
    handleFileSelect,
    handlePaste,
    removeAttachment,
    clearAttachments,
    getImagesForAPI,
    fileInputRef,
  } = useFileAttachments();

  useEffect(() => {
    if (messages.length === 0 && status.type === 'idle') return;

    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status]);

  const adjustHeight = useCallback(() => {
    const ta = textareaRef.current;
    if (ta) { ta.style.height = 'auto'; ta.style.height = `${Math.min(ta.scrollHeight, 150)}px`; }
  }, []);
  useEffect(() => { adjustHeight(); }, [input, adjustHeight]);

  // Built-in attach action — owned by ChatPanel because it references fileInputRef.
  // Prepended to whatever plusMenuActions the page provides.
  const allPlusMenuActions: PlusMenuAction[] = useMemo(() => [
    {
      id: 'attach-file',
      label: 'Attach a file',
      icon: Paperclip,
      verb: 'attach' as const,
      onSelect: () => fileInputRef.current?.click(),
    },
    ...plusMenuActions,
  ], [plusMenuActions, fileInputRef]);

  // Command picker (/ prefix)
  const commandQuery = input.startsWith('/') ? input.slice(1).split(' ')[0] : null;
  useEffect(() => { setCommandPickerOpen(showCommandPicker && commandQuery !== null && !input.includes(' ')); }, [showCommandPicker, commandQuery, input]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!input.trim() && attachments.length === 0) || isLoading) return;
    const images = await getImagesForAPI();
    sendMessage(input, { surface, images: images.length > 0 ? images : undefined });
    setInput('');
    clearAttachments();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e as unknown as React.FormEvent); }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2.5">
        {messages.length === 0 && !isLoading && emptyState && (
          <div className="py-4 px-2">
            {typeof emptyState === 'function'
              ? emptyState({
                  requestUpload: () => fileInputRef.current?.click(),
                })
              : emptyState}
          </div>
        )}

        {messages
          .filter(msg => narrativeFilterMatches(msg, narrativeFilter))
          .map(msg => (
            <NarrativeMessage
              key={msg.id}
              msg={msg}
              isLoading={isLoading}
              onMakeRecurring={onMakeRecurring}
            />
          ))}

        {status.type === 'thinking' && messages[messages.length - 1]?.role === 'user' && (
          <div className="flex items-center gap-1.5 text-muted-foreground text-xs"><Loader2 className="w-3 h-3 animate-spin" />Thinking...</div>
        )}

        {status.type === 'clarify' && pendingClarification && (
          <div className="space-y-2 bg-muted/50 rounded-lg p-3 border border-border">
            <p className="text-xs font-medium">{pendingClarification.question}</p>
            {pendingClarification.options?.length ? (
              <div className="flex flex-wrap gap-1.5">
                {pendingClarification.options.map((opt, i) => (
                  <button key={i} onClick={() => respondToClarification(opt)} className="px-2.5 py-1 text-[11px] rounded-lg border border-primary/30 bg-primary/5 text-primary hover:bg-primary/15 font-medium">{opt}</button>
                ))}
              </div>
            ) : <p className="text-[10px] text-muted-foreground">Type your response below</p>}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className={cn(
        'relative px-3 pb-3 pt-1 shrink-0',
        showInputDivider && 'border-t border-border'
      )}>
        {showCommandPicker && (
          <CommandPicker query={commandQuery ?? ''} onSelect={(cmd) => { setInput(cmd + ' '); setCommandPickerOpen(false); textareaRef.current?.focus(); }} onClose={() => setCommandPickerOpen(false)} isOpen={commandPickerOpen} />
        )}

        {fileError && (
          <div className="mb-2 p-2 rounded-lg border border-destructive/30 bg-destructive/5 text-xs text-destructive">
            {fileError}
          </div>
        )}

        {uploadedDocs.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2 p-1.5 rounded-lg border border-border bg-muted/30">
            {uploadedDocs.map((doc, i) => (
              <div key={i} className="flex items-center gap-1.5 text-xs px-2 py-1 rounded bg-background border border-border">
                <span className="truncate max-w-[120px]">{doc.name}</span>
                <span className={doc.status === 'done' ? 'text-green-600' : doc.status === 'error' ? 'text-destructive' : 'text-muted-foreground'}>
                  {doc.status === 'uploading' ? '...' : doc.status === 'done' ? '✓' : '✗'}
                </span>
              </div>
            ))}
          </div>
        )}

        {attachmentPreviews.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2 p-1.5 rounded-lg border border-border bg-muted/30">
            {attachmentPreviews.map((preview, i) => (
              <div key={i} className="relative group">
                <img src={preview} alt="" className="h-10 w-10 object-cover rounded border border-border" />
                <button onClick={() => removeAttachment(i)} className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-background border border-border rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100"><X className="w-2 h-2" /></button>
              </div>
            ))}
          </div>
        )}

        {actionCard && (
          <div className="mb-2">
            <InlineActionCard
              config={actionCard}
              onSelect={handleActionSelect}
              onDismiss={() => setActionCard(null)}
            />
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="border border-border bg-background rounded-xl focus-within:ring-2 focus-within:ring-primary/50">
            <input ref={fileInputRef} type="file" accept="image/*,.pdf,.docx,.txt,.md" multiple onChange={handleFileSelect} className="hidden" />

            {/* Textarea row */}
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              disabled={isLoading}
              enterKeyHint="send"
              placeholder={placeholder}
              rows={1}
              className="w-full px-3 pt-2.5 pb-1 text-sm bg-transparent resize-none focus:outline-none disabled:opacity-50 max-h-[150px]"
            />

            {/* Bottom toolbar row — mirrors Claude Code: + / [mode chip] … [send] */}
            <div className="flex items-center gap-1 px-1.5 pb-1.5">
              <PlusMenu actions={allPlusMenuActions} disabled={isLoading} />

              {/* Autonomy mode chip — inline switcher, zero LLM write */}
              <div className="relative">
                <button
                  ref={autonomyChipRef}
                  type="button"
                  onClick={() => setAutonomyPopoverOpen(o => !o)}
                  className={cn(
                    'inline-flex items-center gap-1 px-2 py-1 text-[11px] font-medium rounded-md transition-colors',
                    effectiveLevel && effectiveLevel !== 'manual'
                      ? 'bg-primary/10 text-primary hover:bg-primary/20'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                  )}
                  title={effectiveLevel ? `${autonomySummary} — click to change` : 'Set autonomy level'}
                >
                  {effectiveLevel
                    ? effectiveLevel === 'manual' ? 'Manual'
                      : effectiveLevel === 'bounded_autonomous' ? 'Bounded'
                      : 'Full auto'
                    : 'Autonomy'}
                  <svg width="8" height="8" viewBox="0 0 8 8" fill="none" className="opacity-50 shrink-0">
                    <path d="M1 2.5L4 5.5L7 2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
                  </svg>
                </button>

                {autonomyPopoverOpen && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setAutonomyPopoverOpen(false)} />
                    <div className="absolute bottom-full mb-1.5 left-0 z-50 min-w-[210px] rounded-lg border border-border bg-background shadow-lg py-1">
                      {([
                        { level: 'manual' as const, label: 'Manual', desc: 'Every proposal requires your approval' },
                        { level: 'bounded_autonomous' as const, label: 'Bounded', desc: 'Auto-approve within $2K ceiling' },
                        { level: 'autonomous' as const, label: 'Full auto', desc: 'Reviewer approves and executes' },
                      ] as const).map(({ level, label, desc }) => (
                        <button
                          key={level}
                          type="button"
                          className={cn(
                            'w-full text-left px-3 py-1.5 hover:bg-muted/60 transition-colors',
                            effectiveLevel === level && 'bg-muted/40',
                          )}
                          onClick={async () => {
                            setAutonomyPopoverOpen(false);
                            await setAutonomyLevel(level);
                          }}
                        >
                          <span className="block text-[11px] font-medium">{label}</span>
                          <span className="block text-[10px] text-muted-foreground">{desc}</span>
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>

              <div className="flex-1" />
              <button
                type="submit"
                disabled={isLoading || (!input.trim() && attachments.length === 0)}
                className="shrink-0 p-1.5 text-primary disabled:text-muted-foreground disabled:opacity-50 transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}


// =============================================================================
// ADR-219 Commit 5 — weight-driven message rendering
// =============================================================================
//
// Three render shapes per ADR-219 D5:
//   - material:    full card (existing user/assistant/reviewer bubble)
//   - routine:     collapsed line (Identity icon + summary + timestamp + expand)
//   - housekeeping: hidden by default — rolled into the daily digest emitted
//                   by services/back_office/narrative_digest.py (Commit 3).
//                   We render housekeeping rows with a dim collapsed line so
//                   the operator can scroll past them without noise; the
//                   digest card (system_card='narrative_digest') is the
//                   curated headline.
//
// The legacy bubble path (reviewer special-case + user/yarnnn bubbles) is
// preserved as the material rendering. Routine and housekeeping are new
// compact rows. There is one dispatch — singular implementation per
// discipline rule 1; the legacy "no envelope" path is treated as material
// so historical messages predating Commit 2 don't disappear.

function narrativeFilterMatches(
  msg: TPMessage,
  filter: NarrativeFilter | null,
): boolean {
  if (!filter) return true;
  if (filter.weights && filter.weights.size > 0) {
    const w = msg.narrative?.weight ?? 'material'; // legacy → material
    if (!filter.weights.has(w as 'material' | 'routine' | 'housekeeping')) {
      return false;
    }
  }
  if (filter.identities && filter.identities.size > 0) {
    if (!filter.identities.has(msg.role)) return false;
  }
  if (filter.taskSlug !== undefined && filter.taskSlug !== null) {
    if ((msg.narrative?.taskSlug ?? '') !== filter.taskSlug) return false;
  }
  return true;
}

/**
 * NarrativeMessage — thin wrapper over the ADR-237 row grammar.
 *
 * Pre-ADR-237 this function held ~150 LOC of inline weight + role
 * switching. The body has been lifted to:
 *
 *   - MessageRow.tsx — weight gating + cross-cutting concerns
 *     (authorship attribution chip, Make Recurring affordance)
 *   - MessageDispatch.tsx — role-shape rendering for material weight
 *
 * This shell exists only because the surrounding map() in ChatPanel
 * passes a single message + isLoading + onMakeRecurring; the row API
 * accepts the same triple.
 */
function NarrativeMessage({
  msg,
  isLoading,
  onMakeRecurring,
}: {
  msg: TPMessage;
  isLoading: boolean;
  onMakeRecurring?: (messageContent: string) => void;
}) {
  return <MessageRow msg={msg} isLoading={isLoading} onMakeRecurring={onMakeRecurring} />;
}
