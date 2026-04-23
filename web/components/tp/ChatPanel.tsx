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
import { stripWorkspaceStateMeta, stripOnboardingMeta } from '@/lib/workspace-state-meta';

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

        {messages.map(msg => {
          // ADR-212: reviewer verdicts render as full-width cards, not chat bubbles.
          if (msg.role === 'reviewer') {
            return (
              <div key={msg.id} className="max-w-[92%]">
                <ReviewerCard data={msg.reviewer ?? {}} content={msg.content} />
              </div>
            );
          }
          return (
          <div key={msg.id} className={cn('text-[13px] rounded-2xl px-3 py-2 max-w-[92%]', msg.role === 'user' ? 'bg-primary/10 ml-auto rounded-br-md' : 'bg-muted rounded-bl-md')}>
            <span className={cn("text-[9px] font-medium text-muted-foreground/50 tracking-wider block mb-1", msg.role === 'user' ? 'uppercase' : 'font-brand text-[10px]')}>
              {msg.role === 'user' ? 'You' : 'yarnnn'}
            </span>
            {msg.blocks && msg.blocks.length > 0 ? (
              <MessageBlocks blocks={msg.blocks} />
            ) : msg.role === 'assistant' && !msg.content && isLoading ? (
              <div className="flex items-center gap-1.5 text-muted-foreground text-xs"><Loader2 className="w-3 h-3 animate-spin" />Thinking...</div>
            ) : (
              <>
                {msg.role === 'assistant' ? (
                  <MarkdownRenderer content={stripOnboardingMeta(stripWorkspaceStateMeta(msg.content))} compact />
                ) : (
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                )}
                {msg.toolResults && msg.toolResults.length > 0 && <ToolResultList results={msg.toolResults} compact />}
              </>
            )}
          </div>
          );
        })}

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
