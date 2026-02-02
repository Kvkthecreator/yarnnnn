'use client';

/**
 * ADR-022: Chat-First Architecture
 *
 * Primary chat interface - the main view for authenticated users.
 * TP lives here. All conversation happens here.
 * Drawers open from here for detailed views.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Loader2, Sparkles } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useChat } from '@/hooks/useChat';
import { useSurface } from '@/contexts/SurfaceContext';
import { cn } from '@/lib/utils';
import { ToolResultCard } from '@/components/chat/ToolResultCard';
import { api } from '@/lib/api/client';
import type { Deliverable } from '@/types';

// Quick actions shown when there are deliverables
const QUICK_ACTIONS = [
  { label: 'Review pending', prompt: 'Show me deliverables that need review' },
  { label: 'Run all', prompt: 'Run all my active deliverables now' },
  { label: 'Create new', prompt: "I'd like to create a new deliverable" },
];

// Onboarding quick starts (when no deliverables)
const ONBOARDING_PROMPTS = [
  { label: 'Weekly status report', prompt: "I need to send my manager weekly updates on what I've been working on" },
  { label: 'Monthly investor update', prompt: 'I need to send monthly updates to my investors about company progress' },
  { label: 'Meeting summary', prompt: 'I have a recurring meeting and need to produce summaries/notes after each one' },
];

interface ChatViewProps {
  initialMessage?: string; // Pre-filled message from context (e.g., "Ask TP about X")
}

export function ChatView({ initialMessage }: ChatViewProps) {
  const router = useRouter();
  const { openSurface } = useSurface();
  const [input, setInput] = useState(initialMessage || '');
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [loadingDeliverables, setLoadingDeliverables] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Load deliverables to determine quick actions
  useEffect(() => {
    async function loadDeliverables() {
      try {
        const data = await api.deliverables.list();
        setDeliverables(data);
      } catch (err) {
        console.error('Failed to load deliverables:', err);
      } finally {
        setLoadingDeliverables(false);
      }
    }
    loadDeliverables();
  }, []);

  // Handle tool results - watch for deliverable creation, opening surfaces
  const handleToolResult = useCallback(
    (resultEvent: { tool_use_id: string; name: string; result: Record<string, unknown> }) => {
      const result = resultEvent.result as {
        success?: boolean;
        deliverable?: { id?: string };
        version?: { id?: string };
      };

      // Refresh deliverables list if one was created
      if (resultEvent.name === 'create_deliverable' && result.success) {
        api.deliverables.list().then(setDeliverables).catch(console.error);
      }
    },
    []
  );

  // Handle UI actions from TP (like opening drawers)
  const handleUIAction = useCallback(
    (action: { type: string; surface?: string; data?: Record<string, unknown> }) => {
      if (action.type === 'OPEN_SURFACE') {
        if (action.surface === 'deliverable' && action.data?.deliverableId) {
          openSurface('output', { deliverableId: action.data.deliverableId as string });
        } else if (action.surface === 'review' && action.data?.versionId) {
          // Open review drawer
          openSurface('output', {
            deliverableId: action.data.deliverableId as string,
            versionId: action.data.versionId as string,
            mode: 'review',
          });
        }
      }
    },
    [openSurface]
  );

  const { messages, isLoading, error, sendMessage, clearMessages } = useChat({
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

  // Send initial message if provided
  useEffect(() => {
    if (initialMessage && messages.length === 0) {
      sendMessage(initialMessage);
      setInput('');
    }
  }, [initialMessage, messages.length, sendMessage]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const message = input;
    setInput('');
    await sendMessage(message);
  };

  const handleQuickAction = (prompt: string) => {
    setInput(prompt);
    textareaRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const hasDeliverables = deliverables.length > 0;
  const stagedCount = deliverables.filter(d => d.latest_version_status === 'staged').length;
  const quickActions = hasDeliverables ? QUICK_ACTIONS : ONBOARDING_PROMPTS;

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          // Empty state
          <div className="h-full flex flex-col items-center justify-center p-8">
            <div className="max-w-md text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary/10 mb-4">
                <Sparkles className="w-6 h-6 text-primary" />
              </div>

              {loadingDeliverables ? (
                <Loader2 className="w-6 h-6 animate-spin mx-auto text-muted-foreground" />
              ) : hasDeliverables ? (
                <>
                  <h1 className="text-xl font-semibold mb-2">
                    {stagedCount > 0
                      ? `You have ${stagedCount} ${stagedCount === 1 ? 'deliverable' : 'deliverables'} ready for review`
                      : 'All caught up!'}
                  </h1>
                  <p className="text-muted-foreground text-sm mb-6">
                    {stagedCount > 0
                      ? 'Ask me to show them, or use the quick actions below.'
                      : "Ask me anything about your deliverables, or I can create new ones."}
                  </p>
                </>
              ) : (
                <>
                  <h1 className="text-xl font-semibold mb-2">
                    What do you need to produce regularly?
                  </h1>
                  <p className="text-muted-foreground text-sm mb-6">
                    Tell me what you deliver on a recurring basis - weekly reports, monthly updates,
                    meeting summaries - and I'll set it up for you.
                  </p>
                </>
              )}

              {/* Quick action chips */}
              <div className="flex flex-wrap justify-center gap-2">
                {quickActions.map((action) => (
                  <button
                    key={action.label}
                    onClick={() => handleQuickAction(action.prompt)}
                    className="px-4 py-2 text-sm border border-border rounded-full hover:bg-muted transition-colors"
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          // Messages
          <div className="max-w-2xl mx-auto p-4 space-y-4">
            {messages.map((message, index) => (
              <div key={index} className="space-y-2">
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
        <form onSubmit={handleSubmit} className="max-w-2xl mx-auto">
          <div className="flex items-end gap-2">
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Message TP..."
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
        </form>
      </div>
    </div>
  );
}
