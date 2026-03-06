'use client';

/**
 * Scoped chat area for the Deliverable Workspace page.
 *
 * Extracted from deliverables/[id]/page.tsx for maintainability.
 * Reuses TP context, scoped to a specific deliverable.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Loader2,
  MessageSquare,
  Send,
  Paperclip,
  Upload,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useTP } from '@/contexts/TPContext';
import { useFileAttachments } from '@/hooks/useFileAttachments';
import { SkillPicker } from '@/components/tp/SkillPicker';
import { MessageBlocks } from '@/components/tp/InlineToolCall';
import { ToolResultList } from '@/components/tp/ToolResultCard';
import { InlineVersionCard } from './DeliverableVersionDisplay';
import type { Deliverable, DeliverableVersion } from '@/types';

export function DeliverableChatArea({
  deliverableId,
  deliverableTitle,
  versions,
  selectedIdx,
  onSelectIdx,
  deliverable,
  onRunNow,
  running,
}: {
  deliverableId: string;
  deliverableTitle: string;
  versions: DeliverableVersion[];
  selectedIdx: number;
  onSelectIdx: (idx: number) => void;
  deliverable: Deliverable;
  onRunNow: () => void;
  running: boolean;
}) {
  const {
    messages,
    sendMessage,
    isLoading,
    status,
    pendingClarification,
    respondToClarification,
    tokenUsage,
  } = useTP();

  const [input, setInput] = useState('');
  const [skillPickerOpen, setSkillPickerOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const {
    attachments,
    attachmentPreviews,
    isDragging,
    error: fileError,
    dropZoneProps,
    handleFileSelect,
    handlePaste,
    removeAttachment,
    clearAttachments,
    getImagesForAPI,
    fileInputRef,
  } = useFileAttachments();

  const surface = { type: 'deliverable-detail' as const, deliverableId };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status]);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, []);

  useEffect(() => {
    adjustTextareaHeight();
  }, [input, adjustTextareaHeight]);

  const skillQuery = input.startsWith('/') ? input.slice(1).split(' ')[0] : null;
  useEffect(() => {
    if (skillQuery !== null && !input.includes(' ')) {
      setSkillPickerOpen(true);
    } else {
      setSkillPickerOpen(false);
    }
  }, [skillQuery, input]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!input.trim() && attachments.length === 0) || isLoading) return;

    const images = await getImagesForAPI();
    sendMessage(input, { surface, images: images.length > 0 ? images : undefined });
    setInput('');
    clearAttachments();
  };

  const handleSkillSelect = (command: string) => {
    setInput(command + ' ');
    setSkillPickerOpen(false);
    textareaRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  return (
    <div className="relative flex flex-col flex-1 min-h-0" {...dropZoneProps}>
      {/* Drop zone overlay */}
      {isDragging && (
        <div className="absolute inset-0 z-50 bg-primary/5 backdrop-blur-[1px] flex items-center justify-center">
          <div className="border-2 border-dashed border-primary/40 rounded-xl p-8 flex flex-col items-center gap-2">
            <Upload className="w-8 h-8 text-primary/60" />
            <span className="text-sm font-medium text-primary/80">Drop images here</span>
          </div>
        </div>
      )}

      {/* File error toast */}
      {fileError && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 px-3 py-1.5 rounded-lg bg-destructive text-destructive-foreground text-xs font-medium shadow-lg animate-in fade-in slide-in-from-top-2 duration-200">
          {fileError}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {/* Inline version card — full chat width */}
        {versions.length > 0 && (
          <InlineVersionCard
            versions={versions}
            selectedIdx={selectedIdx}
            onSelectIdx={onSelectIdx}
            deliverable={deliverable}
            onRunNow={onRunNow}
            running={running}
          />
        )}

        <div className="max-w-3xl mx-auto w-full space-y-4">
          {messages.length === 0 && !isLoading && (
            <div className="text-center py-8">
              <MessageSquare className="w-10 h-10 text-muted-foreground/20 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground max-w-xs mx-auto mb-4">
                You&apos;re talking to <span className="font-medium text-foreground">{deliverableTitle}</span>.
                Ask me to generate, refine, or review.
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                <button
                  onClick={() => setInput('Generate a new version')}
                  className="px-3 py-1.5 text-sm rounded-full bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
                >
                  Generate a new version
                </button>
                <button
                  onClick={() => setInput('What sources are you using?')}
                  className="px-3 py-1.5 text-sm rounded-full bg-muted hover:bg-muted/80 transition-colors"
                >
                  What sources are you using?
                </button>
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                'text-sm rounded-lg p-3 max-w-2xl',
                msg.role === 'user' ? 'bg-primary/10 ml-auto' : 'bg-muted'
              )}
            >
              <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide block mb-1">
                {msg.role === 'user' ? 'You' : deliverableTitle}
              </span>
              {msg.images && msg.images.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-2">
                  {msg.images.map((img, i) => (
                    <img
                      key={i}
                      src={`data:${img.mediaType};base64,${img.data}`}
                      alt={`Attachment ${i + 1}`}
                      className="max-w-[200px] max-h-[150px] object-contain rounded border border-border"
                    />
                  ))}
                </div>
              )}
              {msg.blocks && msg.blocks.length > 0 ? (
                <MessageBlocks blocks={msg.blocks} />
              ) : msg.role === 'assistant' && !msg.content && isLoading ? (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Thinking...</span>
                </div>
              ) : (
                <>
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  {msg.toolResults && msg.toolResults.length > 0 && (
                    <ToolResultList results={msg.toolResults} compact />
                  )}
                </>
              )}
            </div>
          ))}

          {status.type === 'thinking' && messages[messages.length - 1]?.role === 'user' && (
            <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Thinking...</span>
            </div>
          )}

          {status.type === 'clarify' && pendingClarification && (
            <div className="space-y-3 bg-muted/50 rounded-lg p-4 max-w-2xl border border-border">
              <p className="text-sm font-medium">{pendingClarification.question}</p>
              {pendingClarification.options && pendingClarification.options.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {pendingClarification.options.map((option, i) => (
                    <button
                      key={i}
                      onClick={() => respondToClarification(option)}
                      className="px-4 py-2 text-sm rounded-lg border border-primary/30 bg-primary/5 text-primary hover:bg-primary/15 hover:border-primary/50 transition-all font-medium shadow-sm"
                    >
                      {option}
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">Type your response below</p>
              )}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="px-4 pb-4 pt-2 shrink-0">
        <div className="relative max-w-2xl mx-auto">
          <SkillPicker
            query={skillQuery ?? ''}
            onSelect={handleSkillSelect}
            onClose={() => setSkillPickerOpen(false)}
            isOpen={skillPickerOpen}
          />
          <form onSubmit={handleSubmit}>
            {attachmentPreviews.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-2 p-2 rounded-t-xl border border-b-0 border-border bg-muted/30">
                {attachmentPreviews.map((preview, index) => (
                  <div key={index} className="relative group">
                    <img
                      src={preview}
                      alt={`Attachment ${index + 1}`}
                      className="h-16 w-16 object-cover rounded-md border border-border"
                    />
                    <button
                      type="button"
                      onClick={() => removeAttachment(index)}
                      className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-background border border-border rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-destructive hover:text-destructive-foreground"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <div
              className={cn(
                'flex items-end gap-2 border border-border bg-background shadow-sm transition-colors',
                attachmentPreviews.length > 0 ? 'rounded-b-xl border-t-0' : 'rounded-xl',
                'focus-within:ring-2 focus-within:ring-primary/50 focus-within:shadow-md'
              )}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                multiple
                onChange={handleFileSelect}
                className="hidden"
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isLoading}
                className="shrink-0 p-3 text-muted-foreground hover:text-foreground disabled:opacity-50 transition-colors"
                title="Attach images"
              >
                <Paperclip className="w-5 h-5" />
              </button>
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                onPaste={handlePaste}
                disabled={isLoading}
                placeholder={
                  status.type === 'clarify'
                    ? 'Type your answer...'
                    : `Ask ${deliverableTitle} anything or type / for skills...`
                }
                rows={1}
                className="flex-1 py-3 pr-2 text-sm bg-transparent resize-none focus:outline-none disabled:opacity-50 max-h-[200px]"
              />
              <button
                type="submit"
                disabled={isLoading || (!input.trim() && attachments.length === 0)}
                className="shrink-0 p-3 text-primary hover:text-primary/80 disabled:text-muted-foreground disabled:opacity-50 transition-colors"
                aria-label="Send"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
            <div className="mt-1.5 flex items-center justify-between text-[10px] text-muted-foreground/60">
              <span>Enter to send, Shift+Enter for new line</span>
              {tokenUsage && (
                <span className="font-mono tabular-nums">
                  {tokenUsage.totalTokens >= 1000
                    ? `${(tokenUsage.totalTokens / 1000).toFixed(1)}k`
                    : tokenUsage.totalTokens} tokens
                </span>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
