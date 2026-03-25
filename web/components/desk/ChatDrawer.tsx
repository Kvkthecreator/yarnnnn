'use client';

/**
 * ChatDrawer — ADR-139 v2: Chat as intervention tool
 *
 * Slides from right edge, overlays the right panel.
 * Triggered by FAB button (bottom-right) or ⌘K.
 * Scoped to surface: global TP on workfloor, task-scoped TP on task page.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  MessageCircle,
  X,
  Send,
  Loader2,
  Upload,
  Search,
  Globe,
  RefreshCw,
  Bookmark,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useDesk } from '@/contexts/DeskContext';
import { useFileAttachments } from '@/hooks/useFileAttachments';
import { cn } from '@/lib/utils';
import { CommandPicker } from '@/components/tp/CommandPicker';
import { PlusMenu, type PlusMenuAction } from '@/components/tp/PlusMenu';
import { MessageBlocks } from '@/components/tp/InlineToolCall';
import { ToolResultList } from '@/components/tp/ToolResultCard';
import ReactMarkdown from 'react-markdown';
import type { DeskSurface } from '@/types/desk';

interface ChatDrawerProps {
  /** Surface context to send with messages */
  surfaceOverride?: DeskSurface;
  /** Controlled open state (parent can open the drawer) */
  isOpen?: boolean;
  /** Callback when open state changes */
  onOpenChange?: (open: boolean) => void;
}

export function ChatDrawer({ surfaceOverride, isOpen: controlledOpen, onOpenChange }: ChatDrawerProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const open = controlledOpen ?? internalOpen;
  const setOpen = (v: boolean) => { setInternalOpen(v); onOpenChange?.(v); };
  const {
    messages,
    sendMessage,
    isLoading,
    status,
    pendingClarification,
    respondToClarification,
    tokenUsage,
  } = useTP();
  const { surface } = useDesk();

  const [input, setInput] = useState('');
  const [commandPickerOpen, setCommandPickerOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const {
    attachments,
    attachmentPreviews,
    error: fileError,
    handleFileSelect,
    handlePaste,
    removeAttachment,
    clearAttachments,
    getImagesForAPI,
    fileInputRef,
  } = useFileAttachments();

  // ⌘K shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setOpen(!open);
      }
      if (e.key === 'Escape' && open) {
        setOpen(false);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open]);

  // Auto-scroll
  useEffect(() => {
    if (open) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, status, open]);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setTimeout(() => textareaRef.current?.focus(), 150);
    }
  }, [open]);

  // Auto-resize textarea
  const adjustHeight = useCallback(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = 'auto';
      ta.style.height = `${Math.min(ta.scrollHeight, 120)}px`;
    }
  }, []);

  useEffect(() => { adjustHeight(); }, [input, adjustHeight]);

  // Command picker
  const commandQuery = input.startsWith('/') ? input.slice(1).split(' ')[0] : null;
  useEffect(() => {
    setCommandPickerOpen(commandQuery !== null && !input.includes(' '));
  }, [commandQuery, input]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!input.trim() && attachments.length === 0) || isLoading) return;
    const images = await getImagesForAPI();
    sendMessage(input, {
      surface: surfaceOverride || surface,
      images: images.length > 0 ? images : undefined,
    });
    setInput('');
    clearAttachments();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  const plusMenuActions: PlusMenuAction[] = [
    { id: 'upload-file', label: 'Upload file', icon: Upload, verb: 'attach', onSelect: () => fileInputRef.current?.click() },
    { id: 'search-platforms', label: 'Search platforms', icon: Search, verb: 'prompt', onSelect: () => { setInput('Search across my connected platforms for '); textareaRef.current?.focus(); } },
    { id: 'web-search', label: 'Web search', icon: Globe, verb: 'prompt', onSelect: () => { setInput('Search the web for '); textareaRef.current?.focus(); } },
    { id: 'refresh-sync', label: 'Refresh platforms', icon: RefreshCw, verb: 'prompt', onSelect: () => { setInput('Refresh my platform data'); textareaRef.current?.focus(); } },
    { id: 'save-memory', label: 'Save to memory', icon: Bookmark, verb: 'prompt', onSelect: () => { setInput('Remember that '); textareaRef.current?.focus(); } },
  ];

  return (
    <>
      {/* FAB trigger */}
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          'fixed bottom-6 right-6 z-40 w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-all',
          open
            ? 'bg-muted text-muted-foreground hover:bg-muted/80'
            : 'bg-primary text-primary-foreground hover:bg-primary/90 hover:scale-105'
        )}
        title={open ? 'Close chat (Esc)' : 'Open chat (⌘K)'}
      >
        {open ? <X className="w-5 h-5" /> : <MessageCircle className="w-5 h-5" />}
      </button>

      {/* Backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/10 lg:bg-transparent"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Drawer */}
      <div
        className={cn(
          'fixed top-0 right-0 bottom-0 z-50 w-full sm:w-[420px] bg-background border-l border-border shadow-xl flex flex-col',
          'transition-transform duration-300 ease-out',
          open ? 'translate-x-0' : 'translate-x-full'
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
          <span className="text-sm font-medium">Chat</span>
          <div className="flex items-center gap-2">
            {tokenUsage && (
              <span className="text-[10px] font-mono text-muted-foreground/50">
                {tokenUsage.totalTokens >= 1000 ? `${(tokenUsage.totalTokens / 1000).toFixed(1)}k` : tokenUsage.totalTokens} tokens
              </span>
            )}
            <button onClick={() => setOpen(false)} className="p-1 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
          {messages.length === 0 && !isLoading && (
            <div className="text-center py-8">
              <MessageCircle className="w-6 h-6 text-muted-foreground/20 mx-auto mb-2" />
              <p className="text-xs text-muted-foreground">Ask anything or type / for commands</p>
            </div>
          )}

          {messages.map(msg => (
            <div
              key={msg.id}
              className={cn(
                'text-sm rounded-2xl px-3 py-2.5 max-w-[90%]',
                msg.role === 'user'
                  ? 'bg-primary/10 ml-auto rounded-br-md'
                  : 'bg-muted rounded-bl-md'
              )}
            >
              <span className={cn(
                "text-[9px] font-medium text-muted-foreground/60 tracking-wider block mb-1",
                msg.role === 'user' ? 'uppercase' : 'font-brand text-[10px]'
              )}>
                {msg.role === 'user' ? 'You' : 'yarnnn'}
              </span>
              {msg.blocks && msg.blocks.length > 0 ? (
                <MessageBlocks blocks={msg.blocks} />
              ) : msg.role === 'assistant' && !msg.content && isLoading ? (
                <div className="flex items-center gap-1.5 text-muted-foreground text-xs">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Thinking...
                </div>
              ) : (
                <>
                  {msg.role === 'assistant' ? (
                    <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-0.5 text-[13px]">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <p className="whitespace-pre-wrap text-[13px]">{msg.content}</p>
                  )}
                  {msg.toolResults && msg.toolResults.length > 0 && (
                    <ToolResultList results={msg.toolResults} compact />
                  )}
                </>
              )}
            </div>
          ))}

          {status.type === 'thinking' && messages[messages.length - 1]?.role === 'user' && (
            <div className="flex items-center gap-1.5 text-muted-foreground text-xs">
              <Loader2 className="w-3 h-3 animate-spin" />
              Thinking...
            </div>
          )}

          {status.type === 'clarify' && pendingClarification && (
            <div className="space-y-2 bg-muted/50 rounded-lg p-3 border border-border">
              <p className="text-xs font-medium">{pendingClarification.question}</p>
              {pendingClarification.options?.length ? (
                <div className="flex flex-wrap gap-1.5">
                  {pendingClarification.options.map((opt, i) => (
                    <button key={i} onClick={() => respondToClarification(opt)} className="px-3 py-1.5 text-xs rounded-lg border border-primary/30 bg-primary/5 text-primary hover:bg-primary/15 font-medium">
                      {opt}
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-[10px] text-muted-foreground">Type your response below</p>
              )}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="px-3 pb-3 pt-1 shrink-0 border-t border-border">
          <div className="relative">
            <CommandPicker
              query={commandQuery ?? ''}
              onSelect={(cmd) => { setInput(cmd + ' '); setCommandPickerOpen(false); textareaRef.current?.focus(); }}
              onClose={() => setCommandPickerOpen(false)}
              isOpen={commandPickerOpen}
            />
          </div>

          {attachmentPreviews.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2 p-1.5 rounded-lg border border-border bg-muted/30">
              {attachmentPreviews.map((preview, i) => (
                <div key={i} className="relative group">
                  <img src={preview} alt="" className="h-12 w-12 object-cover rounded border border-border" />
                  <button onClick={() => removeAttachment(i)} className="absolute -top-1 -right-1 w-4 h-4 bg-background border border-border rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 text-[8px]">
                    <X className="w-2.5 h-2.5" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="flex items-end gap-1.5 border border-border bg-background rounded-xl focus-within:ring-2 focus-within:ring-primary/50">
              <input ref={fileInputRef} type="file" accept="image/*,.pdf,.docx,.txt,.md" multiple onChange={handleFileSelect} className="hidden" />
              <PlusMenu actions={plusMenuActions} disabled={isLoading} />
              <textarea
                ref={textareaRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                onPaste={handlePaste}
                disabled={isLoading}
                enterKeyHint="send"
                placeholder="Ask anything or type / ..."
                rows={1}
                className="flex-1 py-2.5 pr-1 text-sm bg-transparent resize-none focus:outline-none disabled:opacity-50 max-h-[120px]"
              />
              <button type="submit" disabled={isLoading || (!input.trim() && attachments.length === 0)} className="shrink-0 p-2.5 text-primary disabled:text-muted-foreground disabled:opacity-50 transition-colors">
                <Send className="w-4 h-4" />
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
