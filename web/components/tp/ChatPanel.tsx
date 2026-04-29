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
  Repeat,
  ChevronDown,
  CornerDownRight,
  Zap,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useDesk } from '@/contexts/DeskContext';
import { useFileAttachments } from '@/hooks/useFileAttachments';
import { cn } from '@/lib/utils';
import { CommandPicker } from '@/components/tp/CommandPicker';
import { PlusMenu, type PlusMenuAction } from '@/components/tp/PlusMenu';
import { MessageBlocks } from '@/components/tp/InlineToolCall';
import { ToolResultList } from '@/components/tp/ToolResultCard';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import {
  InlineActionCard,
  type ActionCardConfig,
} from '@/components/tp/InlineActionCard';
import { ReviewerCard } from '@/components/tp/ReviewerCard';
import { stripSnapshotMeta, stripOnboardingMeta } from '@/lib/snapshot-meta';
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
          <div className="flex items-end gap-1.5 border border-border bg-background rounded-xl focus-within:ring-2 focus-within:ring-primary/50">
            <input ref={fileInputRef} type="file" accept="image/*,.pdf,.docx,.txt,.md" multiple onChange={handleFileSelect} className="hidden" />
            <PlusMenu actions={allPlusMenuActions} disabled={isLoading} />
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
              className="flex-1 py-2.5 pr-1 text-sm bg-transparent resize-none focus:outline-none disabled:opacity-50 max-h-[150px]"
            />
            <button type="submit" disabled={isLoading || (!input.trim() && attachments.length === 0)} className="shrink-0 p-2.5 text-primary disabled:text-muted-foreground disabled:opacity-50 transition-colors"><Send className="w-4 h-4" /></button>
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

function NarrativeMessage({
  msg,
  isLoading,
  onMakeRecurring,
}: {
  msg: TPMessage;
  isLoading: boolean;
  onMakeRecurring?: (messageContent: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const weight = msg.narrative?.weight ?? 'material'; // legacy default
  const isInlineAction = !msg.narrative?.taskSlug;
  const showMakeRecurring =
    weight === 'material' &&
    msg.role === 'user' &&
    isInlineAction &&
    !!onMakeRecurring &&
    !!msg.content?.trim();

  // ───── Material: full card (legacy rendering preserved) ─────
  if (weight === 'material') {
    // ADR-212: reviewer verdicts render as full-width cards, not chat bubbles.
    if (msg.role === 'reviewer') {
      return (
        <div className="max-w-[92%]">
          <ReviewerCard data={msg.reviewer ?? {}} content={msg.content} />
        </div>
      );
    }
    // ADR-219 / ADR-205 F1 attribution chip:
    //   - taskSlug set + role !== 'user' → "from {slug}", linked to /work?task={slug}
    //   - taskSlug unset + role === 'assistant' + addressed pulse + invocationId → "ran inline"
    //   This makes the difference between recurrence-fired and chat-fired
    //   invocations visible at the rendering layer per ADR-219 Axiom 9.
    const recurrenceSlug = msg.narrative?.taskSlug;
    const showRecurrenceChip = !!recurrenceSlug && msg.role !== 'user';
    const showInlineFireHint =
      !recurrenceSlug &&
      msg.role === 'assistant' &&
      msg.narrative?.pulse === 'addressed' &&
      !!msg.narrative?.invocationId;

    return (
      <div className={cn('text-[13px] rounded-2xl px-3 py-2 max-w-[92%]', msg.role === 'user' ? 'bg-primary/10 ml-auto rounded-br-md' : 'bg-muted rounded-bl-md')}>
        <span className={cn("text-[9px] font-medium text-muted-foreground/50 tracking-wider block mb-1", msg.role === 'user' ? 'uppercase' : 'font-brand text-[10px]')}>
          {msg.role === 'user' ? 'You' : msg.role === 'agent' ? (msg.authorAgentSlug ?? 'agent') : msg.role === 'external' ? 'external' : msg.role === 'system' ? 'system' : 'yarnnn'}
        </span>
        {showRecurrenceChip && (
          <a
            href={`/work?task=${encodeURIComponent(recurrenceSlug!)}`}
            className="inline-flex items-center gap-1 text-[10px] font-medium text-muted-foreground/60 hover:text-foreground hover:bg-foreground/5 px-1.5 py-0.5 -mx-0.5 -mt-0.5 mb-1 rounded transition-colors"
            title={`From recurrence: ${recurrenceSlug}`}
          >
            <CornerDownRight className="w-2.5 h-2.5" />
            <span className="font-mono">{recurrenceSlug}</span>
          </a>
        )}
        {showInlineFireHint && (
          <span
            className="inline-flex items-center gap-1 text-[10px] font-medium text-primary/60 px-1.5 py-0.5 -mx-0.5 -mt-0.5 mb-1 rounded"
            title="Inline action — fired immediately on ask"
          >
            <Zap className="w-2.5 h-2.5" />
            <span>ran inline</span>
          </span>
        )}
        {msg.blocks && msg.blocks.length > 0 ? (
          <MessageBlocks blocks={msg.blocks} />
        ) : msg.role === 'assistant' && !msg.content && isLoading ? (
          <div className="flex items-center gap-1.5 text-muted-foreground text-xs"><Loader2 className="w-3 h-3 animate-spin" />Thinking...</div>
        ) : (
          <>
            {msg.role === 'assistant' ? (
              <MarkdownRenderer content={stripOnboardingMeta(stripSnapshotMeta(msg.content))} compact />
            ) : (
              <p className="whitespace-pre-wrap">{msg.content}</p>
            )}
            {msg.toolResults && msg.toolResults.length > 0 && <ToolResultList results={msg.toolResults} compact />}
          </>
        )}
        {showMakeRecurring && (
          <div className="mt-1.5 -mb-0.5">
            <button
              type="button"
              onClick={() => onMakeRecurring!(msg.content)}
              className="inline-flex items-center gap-1 text-[10px] font-medium text-primary/70 hover:text-primary hover:bg-primary/5 px-1.5 py-0.5 rounded transition-colors"
              title="Turn this inline ask into a recurrence"
            >
              <Repeat className="w-2.5 h-2.5" />
              Make this recurring
            </button>
          </div>
        )}
      </div>
    );
  }

  // ───── Routine: collapsed line, expandable to full ─────
  if (weight === 'routine') {
    const summary = msg.narrative?.summary
      ?? (msg.content?.split('\n', 1)[0]?.slice(0, 160) ?? '(no summary)');
    return (
      <div className="max-w-[92%]">
        <div className="text-[12px] flex items-center gap-2 py-1">
          <button
            type="button"
            onClick={() => setExpanded(v => !v)}
            className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors text-left flex-1 min-w-0"
          >
            <ChevronDown
              className={cn(
                'w-3 h-3 shrink-0 transition-transform',
                expanded && 'rotate-180',
              )}
            />
            <span className="text-[9px] font-medium uppercase tracking-wider text-muted-foreground/60">
              {msg.role}
            </span>
            <span className="truncate">{summary}</span>
          </button>
          <span className="text-[10px] text-muted-foreground/40 shrink-0 tabular-nums">
            {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
        {expanded && msg.content && (
          <div className="ml-5 mt-0.5 mb-1 text-[12px] text-muted-foreground bg-muted/30 rounded px-2.5 py-1.5">
            {msg.role === 'assistant' ? (
              <MarkdownRenderer content={stripOnboardingMeta(stripSnapshotMeta(msg.content))} compact />
            ) : (
              <p className="whitespace-pre-wrap">{msg.content}</p>
            )}
          </div>
        )}
      </div>
    );
  }

  // ───── Housekeeping: dim one-liner ─────
  // The narrative_digest system_card (rendered via the material path
  // when its containing message has weight=material) is the curated
  // surface for housekeeping clusters. Individual housekeeping rows
  // still render here in case the digest hasn't run yet, but they're
  // visually de-emphasized.
  const summary = msg.narrative?.summary
    ?? (msg.content?.split('\n', 1)[0]?.slice(0, 160) ?? '');
  return (
    <div className="text-[11px] flex items-center gap-2 max-w-[92%] py-0.5 opacity-50 hover:opacity-90 transition-opacity">
      <span className="text-[9px] font-medium uppercase tracking-wider text-muted-foreground/50">
        {msg.role}
      </span>
      <span className="text-muted-foreground truncate flex-1">{summary}</span>
      <span className="text-[10px] text-muted-foreground/40 shrink-0 tabular-nums">
        {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </span>
    </div>
  );
}
