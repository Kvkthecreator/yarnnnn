'use client';

/**
 * Conversation-First Onboarding (ADR-020 Extension)
 *
 * Full-screen chat view for cold-start users with no deliverables.
 * Encourages pasting examples or describing needs rather than
 * filling out a structured wizard.
 *
 * The TP can create deliverables directly via the create_deliverable tool.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Send,
  Loader2,
  Sparkles,
  ClipboardList,
  FileText,
  Search,
  MessageSquare,
} from 'lucide-react';
import { useChat } from '@/hooks/useChat';
import { useFloatingChat } from '@/contexts/FloatingChatContext';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { ToolResultCard } from '@/components/chat/ToolResultCard';

interface OnboardingChatViewProps {
  onDeliverableCreated: (deliverableId: string) => void;
  onUseWizard: () => void;
}

// Quick start prompts for common deliverable types
const QUICK_STARTS = [
  {
    icon: ClipboardList,
    label: 'Weekly status report',
    prompt: 'I need to send my manager weekly updates on what I\'ve been working on',
  },
  {
    icon: FileText,
    label: 'Monthly investor update',
    prompt: 'I need to send monthly updates to my investors about company progress',
  },
  {
    icon: Search,
    label: 'Competitive brief',
    prompt: 'I want to track my competitors and get regular summaries of what they\'re doing',
  },
  {
    icon: MessageSquare,
    label: 'Meeting summary',
    prompt: 'I have a recurring meeting and need to produce summaries/notes after each one',
  },
];

export function OnboardingChatView({
  onDeliverableCreated,
  onUseWizard,
}: OnboardingChatViewProps) {
  const router = useRouter();
  const { setPageContext } = useFloatingChat();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Set page context to hide floating chat trigger (we're already in a chat)
  useEffect(() => {
    setPageContext({ type: 'onboarding-chat' });
    return () => setPageContext({ type: 'global' });
  }, [setPageContext]);

  // Handle tool results - watch for deliverable creation
  const handleToolResult = useCallback(
    (resultEvent: { tool_use_id: string; name: string; result: Record<string, unknown> }) => {
      if (resultEvent.name === 'create_deliverable') {
        const result = resultEvent.result as {
          success?: boolean;
          deliverable?: { id?: string };
        };
        if (result.success && result.deliverable?.id) {
          // Notify parent that a deliverable was created
          onDeliverableCreated(result.deliverable.id);
        }
      }
    },
    [onDeliverableCreated]
  );

  // Handle UI actions from TP (like opening deliverable detail)
  const handleUIAction = useCallback(
    (action: { type: string; surface?: string; data?: Record<string, unknown> }) => {
      if (action.type === 'OPEN_SURFACE' && action.surface === 'deliverable' && action.data?.deliverableId) {
        router.push(`/dashboard/deliverable/${action.data.deliverableId}`);
      }
    },
    [router]
  );

  const { messages, isLoading, error, sendMessage } = useChat({
    includeContext: true,
    onToolResult: handleToolResult,
    onUIAction: handleUIAction,
  });

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus textarea on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const message = input;
    setInput('');
    await sendMessage(message);
  };

  const handleQuickStart = (prompt: string) => {
    setInput(prompt);
    textareaRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Submit on Enter without shift
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 text-center py-8 px-4">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary/10 mb-4">
          <Sparkles className="w-6 h-6 text-primary" />
        </div>
        <h1 className="text-xl font-semibold mb-2">
          What do you need to produce regularly?
        </h1>
        <p className="text-muted-foreground text-sm max-w-md mx-auto">
          Paste an example, describe what you deliver, or pick a quick start below.
          I&apos;ll set it up so you get drafts on schedule.
        </p>
      </div>

      {/* Chat area */}
      <div className="flex-1 overflow-y-auto px-4">
        {messages.length === 0 ? (
          <div className="max-w-lg mx-auto">
            {/* Quick start cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
              {QUICK_STARTS.map((item) => (
                <button
                  key={item.label}
                  onClick={() => handleQuickStart(item.prompt)}
                  className="flex items-start gap-3 p-4 text-left border border-border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <item.icon className="w-5 h-5 text-muted-foreground shrink-0 mt-0.5" />
                  <span className="text-sm">{item.label}</span>
                </button>
              ))}
            </div>

            {/* Wizard fallback */}
            <div className="text-center pt-4 border-t border-border">
              <button
                onClick={onUseWizard}
                className="text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                I know exactly what I need &rarr; Use step-by-step setup
              </button>
            </div>
          </div>
        ) : (
          <div className="max-w-lg mx-auto space-y-4 pb-4">
            {messages.map((message, index) => (
              <div key={index} className="space-y-2">
                {/* Message bubble */}
                <div
                  className={cn(
                    'flex',
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  )}
                >
                  <div
                    className={cn(
                      'px-4 py-3 rounded-2xl max-w-[85%] text-sm',
                      message.role === 'user'
                        ? 'bg-primary text-primary-foreground rounded-br-md'
                        : 'bg-muted rounded-bl-md'
                    )}
                  >
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  </div>
                </div>

                {/* Tool result cards */}
                {message.role === 'assistant' &&
                  message.toolResults &&
                  message.toolResults.length > 0 && (
                    <div className="space-y-2 pl-2">
                      {message.toolResults.map((result, resultIndex) => (
                        <ToolResultCard
                          key={resultIndex}
                          result={result}
                          onNavigate={(path) => router.push(path)}
                        />
                      ))}
                    </div>
                  )}
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="px-4 py-3 bg-muted rounded-2xl rounded-bl-md">
                  <Loader2 className="w-4 h-4 animate-spin" />
                </div>
              </div>
            )}

            {error && (
              <div className="px-4 py-3 bg-destructive/10 text-destructive rounded-lg text-sm">
                {error}
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="shrink-0 border-t border-border bg-background p-4">
        <form onSubmit={handleSubmit} className="max-w-lg mx-auto">
          <div className="flex items-end gap-2">
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Describe what you need, or paste an example..."
                disabled={isLoading}
                rows={1}
                className={cn(
                  'w-full px-4 py-3 border border-border rounded-xl bg-background text-sm resize-none',
                  'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary',
                  'disabled:opacity-50 placeholder:text-muted-foreground',
                  'min-h-[48px] max-h-[200px]'
                )}
              />
            </div>
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className={cn(
                'p-3 rounded-xl transition-colors shrink-0',
                'bg-primary text-primary-foreground',
                'hover:bg-primary/90 disabled:opacity-50'
              )}
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
          <p className="text-xs text-muted-foreground mt-2 text-center">
            Press Enter to send, Shift+Enter for new line
          </p>
        </form>
      </div>
    </div>
  );
}
