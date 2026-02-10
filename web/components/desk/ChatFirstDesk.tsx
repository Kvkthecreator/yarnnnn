'use client';

/**
 * ADR-037: Chat-First Surface Architecture
 *
 * Chat-first desk layout - TP is the primary interface
 *
 * Layout:
 * - Mobile: TP full screen
 * - Desktop: TP takes 60%+ of screen, surfaces as needed
 *
 * This inverts the traditional desk layout where surfaces were primary
 * and TP was a side drawer.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import {
  MessageCircle,
  CheckCircle2,
  Circle,
  Loader2,
  Send,
  ChevronRight,
  X,
  Paperclip,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useDesk } from '@/contexts/DeskContext';
import { Todo, TPImageAttachment } from '@/types/desk';
import { cn } from '@/lib/utils';
import { getTPStateIndicators } from '@/lib/tp-chips';
import { SkillPicker } from '@/components/tp/SkillPicker';
import { SurfaceRouter } from './SurfaceRouter';

export function ChatFirstDesk() {
  const {
    todos,
    messages,
    activeSkill,
    sendMessage,
    isLoading,
    status,
    pendingClarification,
    respondToClarification,
  } = useTP();
  const { surface } = useDesk();

  const [input, setInput] = useState('');
  const [attachments, setAttachments] = useState<File[]>([]);
  const [attachmentPreviews, setAttachmentPreviews] = useState<string[]>([]);
  const [skillPickerOpen, setSkillPickerOpen] = useState(false);
  const [surfacePanelOpen, setSurfacePanelOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status]);

  // Focus textarea on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  // Auto-resize textarea
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

  // Detect skill picker trigger
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

    // Convert attachments to base64 TPImageAttachment format
    const images: TPImageAttachment[] = [];
    for (const file of attachments) {
      const base64 = await fileToBase64(file);
      const mediaType = file.type as TPImageAttachment['mediaType'];
      // Only include supported image types
      if (['image/jpeg', 'image/png', 'image/gif', 'image/webp'].includes(mediaType)) {
        images.push({ data: base64, mediaType });
      }
    }

    sendMessage(input, { surface, images: images.length > 0 ? images : undefined });
    setInput('');
    setAttachments([]);
    setAttachmentPreviews([]);
  };

  // Helper to convert File to base64 string (without data URL prefix)
  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        // Remove "data:image/xxx;base64," prefix
        const base64 = result.split(',')[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  };

  const handleSkillSelect = (command: string) => {
    setInput(command + ' ');
    setSkillPickerOpen(false);
    textareaRef.current?.focus();
  };

  // File attachment handling
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const imageFiles = files.filter((f) => f.type.startsWith('image/'));

    if (imageFiles.length === 0) return;

    // Create previews for images
    imageFiles.forEach((file) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        setAttachmentPreviews((prev) => [...prev, e.target?.result as string]);
      };
      reader.readAsDataURL(file);
    });

    setAttachments((prev) => [...prev, ...imageFiles]);

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeAttachment = (index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
    setAttachmentPreviews((prev) => prev.filter((_, i) => i !== index));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  const handleOptionClick = (option: string) => {
    respondToClarification(option);
  };

  // Get surface label for panel header
  const indicators = getTPStateIndicators(surface);
  const surfaceLabel = indicators.surface.label;

  const formatSkillName = (skill: string) => {
    return skill
      .split('-')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const getTitle = () => {
    if (activeSkill) return formatSkillName(activeSkill);
    return 'Thinking Partner';
  };

  // Check if there's a non-idle surface to show
  const hasActiveSurface = surface.type !== 'idle';

  return (
    <div className="h-full flex justify-center">
      {/* Main Chat Area - Primary, centered with max-width like ChatGPT/Claude */}
      <div className="flex-1 flex flex-col bg-background min-w-0 max-w-3xl">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
          <div className="flex items-center gap-2">
            <MessageCircle className="w-5 h-5 text-primary" />
            <span className="font-medium">{getTitle()}</span>
            {isLoading && <Loader2 className="w-4 h-4 animate-spin text-primary" />}
          </div>

          {/* Surface toggle - only show if there's an active surface */}
          {hasActiveSurface && (
            <button
              onClick={() => setSurfacePanelOpen(!surfacePanelOpen)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md bg-muted hover:bg-muted/80 transition-colors"
            >
              <span className="truncate max-w-[120px]">{surfaceLabel}</span>
              <ChevronRight className={cn(
                'w-4 h-4 transition-transform',
                surfacePanelOpen && 'rotate-90'
              )} />
            </button>
          )}
        </div>

        {/* Todos (when active) */}
        {todos.length > 0 && (
          <div className="px-4 py-3 border-b border-border bg-muted/20 shrink-0">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-muted-foreground">Progress</span>
              <span className="text-xs text-muted-foreground">
                {todos.filter((t) => t.status === 'completed').length}/{todos.length}
              </span>
            </div>
            <div className="space-y-1.5 max-h-28 overflow-y-auto">
              {todos.map((todo, i) => (
                <TodoItem key={i} todo={todo} />
              ))}
            </div>
          </div>
        )}

        {/* Messages - Primary content area */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {messages.length === 0 && !isLoading && (
            <div className="text-center py-12">
              <MessageCircle className="w-12 h-12 text-muted-foreground/20 mx-auto mb-3" />
              <h2 className="text-lg font-medium mb-2">Welcome to yarnnn</h2>
              <p className="text-sm text-muted-foreground max-w-md mx-auto mb-4">
                I&apos;m your Thinking Partner. Tell me what recurring work you need help with,
                or type <code className="bg-muted px-1.5 py-0.5 rounded text-xs">/</code> to see available skills.
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                <button
                  onClick={() => setInput('/create ')}
                  className="px-3 py-1.5 text-sm rounded-full bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
                >
                  Create a deliverable
                </button>
                <button
                  onClick={() => setInput('What can you help me with?')}
                  className="px-3 py-1.5 text-sm rounded-full bg-muted hover:bg-muted/80 transition-colors"
                >
                  What can you do?
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
                {msg.role === 'user' ? 'You' : 'TP'}
              </span>
              {/* Display attached images */}
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
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          ))}

          {/* Status indicators */}
          {status.type === 'thinking' && (
            <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Thinking...</span>
            </div>
          )}
          {status.type === 'tool' && (
            <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>{status.toolName}...</span>
            </div>
          )}
          {status.type === 'streaming' && (
            <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Typing...</span>
            </div>
          )}

          {/* Clarification options */}
          {status.type === 'clarify' && pendingClarification?.options && (
            <div className="space-y-2 bg-muted rounded-lg p-3 max-w-2xl">
              <p className="text-sm">{pendingClarification.question}</p>
              <div className="flex flex-wrap gap-2">
                {pendingClarification.options.map((option, i) => (
                  <button
                    key={i}
                    onClick={() => handleOptionClick(option)}
                    className="px-3 py-1.5 text-sm rounded-full bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input - Claude Code IDE style */}
        <div className="p-4 border-t border-border shrink-0">
          <div className="relative max-w-2xl mx-auto">
            <SkillPicker
              query={skillQuery ?? ''}
              onSelect={handleSkillSelect}
              onClose={() => setSkillPickerOpen(false)}
              isOpen={skillPickerOpen}
            />
            <form onSubmit={handleSubmit}>
              {/* Attachment previews */}
              {attachmentPreviews.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-2 p-2 rounded-t-lg border border-b-0 border-border bg-muted/30">
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

              {/* Input container */}
              <div
                className={cn(
                  'flex items-end gap-2 border border-border bg-background transition-colors',
                  attachmentPreviews.length > 0 ? 'rounded-b-lg border-t-0' : 'rounded-lg',
                  'focus-within:ring-2 focus-within:ring-primary/50'
                )}
              >
                {/* Attachment button */}
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

                {/* Textarea */}
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={isLoading}
                  placeholder={
                    status.type === 'clarify'
                      ? 'Type your answer...'
                      : 'Ask anything or type / for skills...'
                  }
                  rows={1}
                  className="flex-1 py-3 pr-2 text-sm bg-transparent resize-none focus:outline-none disabled:opacity-50 max-h-[200px]"
                />

                {/* Send button */}
                <button
                  type="submit"
                  disabled={isLoading || (!input.trim() && attachments.length === 0)}
                  className="shrink-0 p-3 text-primary hover:text-primary/80 disabled:text-muted-foreground disabled:opacity-50 transition-colors"
                  aria-label="Send"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>

              {/* Hint text */}
              <p className="mt-1.5 text-[10px] text-muted-foreground/60 text-center">
                Press Enter to send, Shift+Enter for new line
              </p>
            </form>
          </div>
        </div>
      </div>

      {/* Surface Panel - Secondary, slides in when needed */}
      {hasActiveSurface && (
        <div
          className={cn(
            'hidden md:block border-l border-border bg-background transition-all duration-300',
            surfacePanelOpen ? 'w-[480px]' : 'w-0 overflow-hidden'
          )}
        >
          {surfacePanelOpen && (
            <div className="h-full flex flex-col">
              <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                <span className="font-medium text-sm truncate">{surfaceLabel}</span>
                <button
                  onClick={() => setSurfacePanelOpen(false)}
                  className="p-1.5 hover:bg-muted rounded-md transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="flex-1 overflow-hidden">
                <SurfaceRouter surface={surface} />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function TodoItem({ todo }: { todo: Todo }) {
  return (
    <div className="flex items-center gap-2">
      {todo.status === 'completed' ? (
        <CheckCircle2 className="w-3.5 h-3.5 text-green-600 shrink-0" />
      ) : todo.status === 'in_progress' ? (
        <Loader2 className="w-3.5 h-3.5 text-primary animate-spin shrink-0" />
      ) : (
        <Circle className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
      )}
      <span
        className={cn(
          'text-xs',
          todo.status === 'completed' && 'text-muted-foreground line-through',
          todo.status === 'in_progress' && 'text-foreground font-medium'
        )}
      >
        {todo.status === 'in_progress' ? todo.activeForm || todo.content : todo.content}
      </span>
    </div>
  );
}
