'use client';

/**
 * ChatComposerSurface — ADR-297 D11 chrome surface (region: bottom-fixed,
 * archetype: input).
 *
 * The universal write path. Mounted by the ShellCompositor in the
 * bottom-fixed region — visible on every authenticated surface so the
 * operator can ping YARNNN from any view without navigating to /feed.
 *
 * Scope discipline (Phase C, safer shape):
 *   - Universal-only state. Reads NarrativeContext (workspace-global
 *     sendMessage + loop status) and DeskContext (current surface for
 *     `sendMessage({ surface })`). No per-surface props.
 *   - The per-surface rich affordances (draftSeed, pendingActionConfig,
 *     emptyState render prop, plusMenuActions, surfaceOverride,
 *     contextLabel, narrativeFilter) stay on ConversationPanel, which
 *     atomic surfaces continue to mount via
 *     ThreePanelLayout.conversation today. Phase C.2 (follow-on)
 *     migrates the right-panel ConversationPanel into a publish/
 *     subscribe model around this shell composer.
 *   - Messages are not rendered here — that's the timeline surface
 *     (/feed FeedTimeline + per-surface ConversationPanel right
 *     panels). This surface is purely the WRITE affordance.
 *
 * Mobile shape (ADR-297 D9, accepted compromise):
 *   - Bottom strip at all viewports. Composer is collapsed (single-row,
 *     no preview chips) at mobile widths; CSS-only responsive shape.
 *   - The full-screen-on-summon shape proposed in ADR-297 D11 is
 *     deferred until operator-observed mobile pain surfaces.
 *
 * The compositor mounts this surface unconditionally (default_visibility
 * = always). Surfaces that don't want it visible (e.g. a future
 * focus-mode reader view) would set an operator-override; today there
 * is no such case so we don't build the affordance.
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { Loader2, Paperclip, Send, Square, X } from 'lucide-react';
import { useNarrative } from '@/contexts/NarrativeContext';
import { useDesk } from '@/contexts/DeskContext';
import { useFileAttachments } from '@/hooks/useFileAttachments';
import { PlusMenu, type PlusMenuAction } from '@/components/tp/PlusMenu';
import { CommandPicker } from '@/components/tp/CommandPicker';
import { useShellChrome } from '../ShellChromeContext';
import { cn } from '@/lib/utils';

const PLACEHOLDER = 'Ask YARNNN — type, drop a file, or paste a link...';

export function ChatComposerSurface() {
  const {
    sendMessage,
    isLoading,
    loopActive,
    stopActiveLoop,
  } = useNarrative();
  const { surface } = useDesk();
  const { composerSuppressed } = useShellChrome();

  const [input, setInput] = useState('');
  const [commandPickerOpen, setCommandPickerOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const {
    attachments,
    attachmentPreviews,
    error: fileError,
    docAttachments,
    handleFileSelect,
    handlePaste,
    removeAttachment,
    clearAttachments,
    getImagesForAPI,
    getDocAttachmentsForAPI,
    getDocxTextBlocks,
    fileInputRef,
  } = useFileAttachments();

  const adjustHeight = useCallback(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = 'auto';
      ta.style.height = `${Math.min(ta.scrollHeight, 150)}px`;
    }
  }, []);
  useEffect(() => {
    adjustHeight();
  }, [input, adjustHeight]);

  // Built-in attach action; shell composer keeps the same affordance as
  // the per-surface ConversationPanel uses.
  const plusMenuActions: PlusMenuAction[] = useMemo(
    () => [
      {
        id: 'attach-file',
        label: 'Attach a file',
        icon: Paperclip,
        verb: 'attach' as const,
        onSelect: () => fileInputRef.current?.click(),
      },
    ],
    [fileInputRef]
  );

  // Command picker (/ prefix) — same shape as ConversationPanel.
  const commandQuery = input.startsWith('/') ? input.slice(1).split(' ')[0] : null;
  useEffect(() => {
    setCommandPickerOpen(commandQuery !== null && !input.includes(' '));
  }, [commandQuery, input]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const hasInput = input.trim().length > 0;
    const hasImages = attachments.length > 0;
    const hasDocs = docAttachments.filter((d) => d.status === 'done').length > 0;
    if ((!hasInput && !hasImages && !hasDocs) || isLoading) return;

    const images = await getImagesForAPI();
    const fileAttachments = getDocAttachmentsForAPI();
    const docxBlocks = getDocxTextBlocks();
    const messageContent =
      docxBlocks.length > 0
        ? input +
          '\n\n' +
          docxBlocks
            .map((b) => `[Document: ${b.filename}]\n${b.content}`)
            .join('\n\n')
        : input;

    sendMessage(messageContent, {
      surface,
      images: images.length > 0 ? images : undefined,
      fileAttachments: fileAttachments.length > 0 ? fileAttachments : undefined,
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

  // ADR-297 D11 Phase C safer-shape: surfaces that mount their own
  // composer (ThreePanelLayout.conversation today) suppress the shell
  // composer to prevent the double-composer UX. Suppression releases
  // when those surfaces unmount.
  if (composerSuppressed) return null;

  return (
    // Outer wrapper sits at the bottom of the shell's flex column.
    // `shrink-0` keeps it out of the flex-1 main region's flow. The
    // inner `border-t` carries the composer visual; the trailing
    // `h-16` spacer reserves room below for the Dock (Dock floats
    // at `fixed inset-x-0 bottom-3 z-40`, ~52px tall + 12px gap).
    <div className="shrink-0 bg-background">
      <div className={cn(
        'border-t border-border bg-background px-3 pt-2 pb-2 sm:px-4'
      )}>
        <div className="mx-auto max-w-3xl">
        {commandPickerOpen && (
          <CommandPicker
            query={commandQuery ?? ''}
            onSelect={(cmd) => {
              setInput(cmd + ' ');
              setCommandPickerOpen(false);
              textareaRef.current?.focus();
            }}
            onClose={() => setCommandPickerOpen(false)}
            isOpen={commandPickerOpen}
          />
        )}

        {fileError && (
          <div className="mb-2 p-2 rounded-lg border border-destructive/30 bg-destructive/5 text-xs text-destructive">
            {fileError}
          </div>
        )}

        {docAttachments.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2 p-1.5 rounded-lg border border-border bg-muted/30">
            {docAttachments.map((doc, i) => (
              <div
                key={i}
                className="flex items-center gap-1.5 text-xs px-2 py-1 rounded bg-background border border-border"
              >
                <span className="truncate max-w-[120px]">{doc.filename}</span>
                <span
                  className={
                    doc.status === 'done'
                      ? 'text-green-600'
                      : doc.status === 'error'
                      ? 'text-destructive'
                      : 'text-muted-foreground'
                  }
                >
                  {doc.status === 'uploading'
                    ? '...'
                    : doc.status === 'done'
                    ? '✓'
                    : '✗'}
                </span>
              </div>
            ))}
          </div>
        )}

        {attachmentPreviews.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2 p-1.5 rounded-lg border border-border bg-muted/30">
            {attachmentPreviews.map((preview, i) => (
              <div key={i} className="relative group">
                <img
                  src={preview}
                  alt=""
                  className="h-10 w-10 object-cover rounded border border-border"
                />
                <button
                  type="button"
                  onClick={() => removeAttachment(i)}
                  className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-background border border-border rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100"
                >
                  <X className="w-2 h-2" />
                </button>
              </div>
            ))}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="border border-border bg-background rounded-xl focus-within:ring-2 focus-within:ring-primary/50">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*,.pdf,.docx,.txt,.md"
              multiple
              onChange={handleFileSelect}
              className="hidden"
            />

            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              disabled={isLoading}
              enterKeyHint="send"
              placeholder={PLACEHOLDER}
              rows={1}
              className="w-full px-3 pt-2.5 pb-1 text-sm bg-transparent resize-none focus:outline-none disabled:opacity-50 max-h-[150px]"
            />

            <div className="flex items-center gap-1 px-1.5 pb-1.5">
              <PlusMenu actions={plusMenuActions} disabled={isLoading} />
              <div className="flex-1" />
              {loopActive ? (
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    void stopActiveLoop();
                  }}
                  aria-label="Stop in-flight Loop"
                  title="Stop the Reviewer's in-flight Loop"
                  className="shrink-0 p-1.5 rounded text-foreground hover:bg-muted transition-colors"
                >
                  <Square className="w-4 h-4 fill-current" />
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={
                    !input.trim() &&
                    attachments.length === 0 &&
                    docAttachments.filter((d) => d.status === 'done').length === 0
                  }
                  className="shrink-0 p-1.5 text-primary disabled:text-muted-foreground disabled:opacity-50 transition-colors"
                  aria-label="Send message"
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </button>
              )}
            </div>
          </div>
        </form>
        </div>
      </div>
      {/* Dock breathing room — Dock floats at `fixed bottom-3` (~64px
          tall including gap). Without this spacer the Dock overlays
          the composer's send/attach controls. The spacer also carries
          the iOS safe-area inset. */}
      <div
        className="h-16"
        style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
        aria-hidden
      />
    </div>
  );
}
