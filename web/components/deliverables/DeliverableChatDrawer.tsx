'use client';

/**
 * ADR-018: Deliverable Chat Drawer
 *
 * Slide-out drawer for chatting with TP about a specific deliverable.
 * Allows users to refine content, ask questions, and request changes
 * without leaving the deliverable view.
 */

import { useState, useEffect, useRef } from 'react';
import { X, Send, Loader2, MessageSquare, Sparkles } from 'lucide-react';
import { useChat } from '@/hooks/useChat';
import { cn } from '@/lib/utils';
import type { Deliverable, DeliverableVersion } from '@/types';

interface DeliverableChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  deliverable: Deliverable;
  currentVersion?: DeliverableVersion | null;
  onRefreshDeliverable?: () => void;
}

export function DeliverableChatDrawer({
  isOpen,
  onClose,
  deliverable,
  currentVersion,
  onRefreshDeliverable,
}: DeliverableChatDrawerProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const hasAutoSentRef = useRef(false);

  // Use the deliverable's project_id for context
  const { messages, isLoading, error, sendMessage } = useChat({
    projectId: deliverable.project_id || undefined,
    includeContext: true,
    onToolResult: (result) => {
      // If TP ran the deliverable, refresh the view
      if (result.name === 'run_deliverable' && result.result?.success) {
        onRefreshDeliverable?.();
      }
    },
  });

  // Focus input when drawer opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Send initial context message when drawer first opens with content
  useEffect(() => {
    if (isOpen && currentVersion && !hasAutoSentRef.current && messages.length === 0) {
      // Don't auto-send - let user initiate
      hasAutoSentRef.current = true;
    }
  }, [isOpen, currentVersion, messages.length]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const message = input;
    setInput('');

    // Build context-aware message
    // First message includes deliverable context
    let contextMessage = message;
    if (messages.length === 0 && currentVersion) {
      const contentPreview = (currentVersion.draft_content || currentVersion.final_content || '').slice(0, 500);
      contextMessage = `I'm looking at my "${deliverable.title}" deliverable (${deliverable.deliverable_type?.replace('_', ' ')}). The current draft starts with:\n\n---\n${contentPreview}${contentPreview.length >= 500 ? '...' : ''}\n---\n\n${message}`;
    }

    await sendMessage(contextMessage);
  };

  // Quick action buttons
  const quickActions = [
    { label: 'Make it shorter', prompt: 'Make this more concise - cut it down to the key points' },
    { label: 'More detail', prompt: 'Add more detail and specifics to this' },
    { label: 'Change tone', prompt: 'Make the tone more professional/formal' },
    { label: 'Regenerate', prompt: 'Please regenerate this deliverable with improvements based on our conversation' },
  ];

  const handleQuickAction = (prompt: string) => {
    setInput(prompt);
    inputRef.current?.focus();
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className={cn(
        "fixed right-0 top-0 h-full w-full max-w-md bg-background border-l border-border shadow-xl z-50",
        "transform transition-transform duration-200 ease-out",
        isOpen ? "translate-x-0" : "translate-x-full"
      )}>
        {/* Header */}
        <div className="h-14 border-b border-border flex items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary" />
            <span className="font-medium text-sm">Refine with AI</span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 h-[calc(100%-8rem)]">
          {messages.length === 0 ? (
            <div className="text-center py-8">
              <MessageSquare className="w-10 h-10 mx-auto mb-3 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground mb-4">
                Ask me to refine your "{deliverable.title}" deliverable
              </p>

              {/* Quick actions */}
              <div className="flex flex-wrap gap-2 justify-center">
                {quickActions.map((action) => (
                  <button
                    key={action.label}
                    onClick={() => handleQuickAction(action.prompt)}
                    className="px-3 py-1.5 text-xs border border-border rounded-full hover:bg-muted transition-colors"
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={cn(
                    "flex",
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  )}
                >
                  <div
                    className={cn(
                      "px-3 py-2 rounded-2xl max-w-[85%] text-sm",
                      message.role === 'user'
                        ? "bg-primary text-primary-foreground rounded-br-md"
                        : "bg-muted rounded-bl-md"
                    )}
                  >
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="flex justify-start">
                  <div className="px-3 py-2 bg-muted rounded-2xl rounded-bl-md">
                    <Loader2 className="w-4 h-4 animate-spin" />
                  </div>
                </div>
              )}

              {error && (
                <div className="px-3 py-2 bg-destructive/10 text-destructive rounded-lg text-sm">
                  {error}
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="absolute bottom-0 left-0 right-0 border-t border-border bg-background p-4">
          <form onSubmit={handleSubmit}>
            <div className="flex items-center gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask for changes..."
                disabled={isLoading}
                className="flex-1 px-4 py-2 border border-border rounded-full bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={isLoading || !input.trim()}
                className="p-2.5 bg-primary text-primary-foreground rounded-full disabled:opacity-50 transition-colors"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
