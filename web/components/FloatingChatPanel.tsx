'use client';

/**
 * ADR-020: Deliverable-Centric Chat
 *
 * Floating chat panel that appears as a drawer on the right side.
 * Contextual to the current page - adapts based on what the user is viewing.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import {
  X,
  Send,
  Loader2,
  MessageSquare,
  Minus,
  Maximize2,
  Sparkles,
} from 'lucide-react';
import { useFloatingChat, PageContextType } from '@/contexts/FloatingChatContext';
import { useChat, type ChatMessage } from '@/hooks/useChat';
import { useSurface } from '@/contexts/SurfaceContext';
import { useWorkStatus } from '@/contexts/WorkStatusContext';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { ToolResultCard } from '@/components/chat/ToolResultCard';
import type { SurfaceType, SurfaceData } from '@/types/surfaces';

// Get context-specific greeting
function getContextGreeting(type: PageContextType, deliverableTitle?: string): string {
  switch (type) {
    case 'deliverable-detail':
      return deliverableTitle
        ? `I'm here to help with your "${deliverableTitle}" deliverable. Ask me to refine it, explain sections, or make changes.`
        : "I'm here to help with this deliverable. What would you like to improve?";
    case 'deliverable-review':
      return deliverableTitle
        ? `Reviewing "${deliverableTitle}". I can help you edit, rephrase, or understand any part of this draft.`
        : "I can help you review and refine this draft. What needs attention?";
    case 'deliverables-dashboard':
      return "I can help you manage your deliverables. Ask me to create new ones, check status, or make changes.";
    case 'project':
      return "What would you like to work on in this project?";
    default:
      return "Hi! I'm your Thinking Partner. How can I help?";
  }
}

// Get quick actions based on context
function getQuickActions(type: PageContextType): { label: string; prompt: string }[] {
  switch (type) {
    case 'deliverable-detail':
    case 'deliverable-review':
      return [
        { label: 'Make it shorter', prompt: 'Make this more concise - cut it down to the key points' },
        { label: 'More detail', prompt: 'Add more detail and specifics to this' },
        { label: 'Change tone', prompt: 'Make the tone more professional/formal' },
        { label: 'Regenerate', prompt: 'Please regenerate this with improvements' },
      ];
    case 'deliverables-dashboard':
      return [
        { label: 'Create new', prompt: "I'd like to create a new recurring deliverable" },
        { label: 'Show all', prompt: 'Show me all my deliverables and their status' },
        { label: 'What\'s due', prompt: 'What deliverables are coming up soon?' },
      ];
    default:
      return [
        { label: 'Create deliverable', prompt: 'Help me set up a new recurring deliverable' },
        { label: 'My deliverables', prompt: 'Show me my deliverables' },
      ];
  }
}

export function FloatingChatPanel() {
  const { state, close, minimize, restore, clearPendingPrompt } = useFloatingChat();
  const { isOpen, isMinimized, pageContext, pendingPrompt } = state;
  const router = useRouter();

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const hasAutoContextRef = useRef(false);

  // ADR-013: Surface control for TP-triggered UI actions
  const { openSurface } = useSurface();

  // ADR-016: Work status tracking
  const { startWork, completeWork, failWork } = useWorkStatus();
  const pendingWorkRef = useRef<Map<string, { agentType: string; task: string }>>(new Map());

  // Build project ID from context
  const projectId = pageContext.projectId || pageContext.deliverable?.project_id || undefined;

  // Handle UI actions from TP
  const handleUIAction = useCallback(
    (action: { type: string; surface?: string; data?: Record<string, unknown> }) => {
      if (action.type === 'OPEN_SURFACE' && action.surface) {
        openSurface(action.surface as SurfaceType, action.data as SurfaceData);
      }
    },
    [openSurface]
  );

  // Handle tool use for work status
  const handleToolUse = useCallback(
    (toolEvent: { id: string; name: string; input: Record<string, unknown> }) => {
      if (toolEvent.name === 'create_work') {
        const input = toolEvent.input as { agent_type?: string; task?: string };
        pendingWorkRef.current.set(toolEvent.id, {
          agentType: input.agent_type || 'unknown',
          task: input.task || 'Working...',
        });
        startWork(input.agent_type || 'unknown', input.task || 'Working...', toolEvent.id);
      }
    },
    [startWork]
  );

  // Handle tool results
  const handleToolResult = useCallback(
    (resultEvent: { tool_use_id: string; name: string; result: Record<string, unknown> }) => {
      if (resultEvent.name === 'create_work') {
        const result = resultEvent.result as {
          success?: boolean;
          work?: { id?: string };
          output?: { title?: string };
          error?: string;
        };
        const pendingWork = pendingWorkRef.current.get(resultEvent.tool_use_id);
        if (pendingWork) {
          if (result.success) {
            completeWork(
              pendingWork.agentType,
              result.work?.id || resultEvent.tool_use_id,
              result.output?.title
            );
          } else {
            failWork(result.error || 'Work failed', resultEvent.tool_use_id);
          }
          pendingWorkRef.current.delete(resultEvent.tool_use_id);
        }
      }
    },
    [completeWork, failWork]
  );

  const { messages, isLoading, error, sendMessage, clearMessages } = useChat({
    projectId,
    includeContext: true,
    onToolUse: handleToolUse,
    onToolResult: handleToolResult,
    onUIAction: handleUIAction,
  });

  // Track previous deliverable to detect context changes
  const prevDeliverableIdRef = useRef<string | undefined>(pageContext.deliverableId);

  // Clear messages when switching to a different deliverable
  useEffect(() => {
    const prevId = prevDeliverableIdRef.current;
    const currentId = pageContext.deliverableId;

    // If we had a deliverable and now have a different one, clear the chat
    // This prevents mixing context from different deliverables
    if (prevId && currentId && prevId !== currentId) {
      clearMessages();
    }

    // Reset auto-context flag when deliverable changes
    if (currentId) {
      hasAutoContextRef.current = false;
    }

    prevDeliverableIdRef.current = currentId;
  }, [pageContext.deliverableId, clearMessages]);

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen && !isMinimized && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen, isMinimized]);

  // Handle pending prompt - auto-send when chat opens with a prompt
  useEffect(() => {
    if (isOpen && !isMinimized && pendingPrompt && !isLoading) {
      // Small delay to ensure chat is ready
      const timer = setTimeout(() => {
        sendMessage(pendingPrompt);
        clearPendingPrompt();
      }, 150);
      return () => clearTimeout(timer);
    }
  }, [isOpen, isMinimized, pendingPrompt, isLoading, sendMessage, clearPendingPrompt]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    let message = input;
    setInput('');

    // Add context to first message if viewing a deliverable
    if (
      messages.length === 0 &&
      !hasAutoContextRef.current &&
      pageContext.deliverable &&
      pageContext.currentVersion
    ) {
      const contentPreview =
        (pageContext.currentVersion.draft_content ||
          pageContext.currentVersion.final_content ||
          '').slice(0, 500);

      message = `I'm looking at my "${pageContext.deliverable.title}" deliverable (${
        pageContext.deliverable.deliverable_type?.replace('_', ' ') || 'custom'
      }). The current draft starts with:

---
${contentPreview}${contentPreview.length >= 500 ? '...' : ''}
---

${message}`;
      hasAutoContextRef.current = true;
    }

    await sendMessage(message);
  };

  const handleQuickAction = (prompt: string) => {
    setInput(prompt);
    inputRef.current?.focus();
  };

  // Don't render if not open
  if (!isOpen) return null;

  // Minimized state - just show a small pill
  if (isMinimized) {
    return (
      <button
        onClick={restore}
        className="fixed bottom-4 right-4 z-50 flex items-center gap-2 px-4 py-2.5 bg-primary text-primary-foreground rounded-full shadow-lg hover:bg-primary/90 active:scale-95 transition-all"
      >
        <MessageSquare className="w-4 h-4" />
        <span className="text-sm font-medium hidden sm:inline">Chat</span>
        {messages.length > 0 && (
          <span className="ml-1 w-5 h-5 bg-white/20 rounded-full text-xs flex items-center justify-center">
            {messages.length}
          </span>
        )}
      </button>
    );
  }

  const contextGreeting = getContextGreeting(
    pageContext.type,
    pageContext.deliverable?.title
  );
  const quickActions = getQuickActions(pageContext.type);

  return (
    <>
      {/* Backdrop - clickable on mobile to close */}
      <div
        className="fixed inset-0 bg-black/20 md:bg-black/10 z-40 md:pointer-events-none"
        onClick={close}
        aria-hidden="true"
      />

      {/* Chat Panel - Full screen on mobile, side drawer on desktop */}
      <div
        className={cn(
          // Mobile: bottom sheet style, full width
          'fixed inset-x-0 bottom-0 h-[85vh] rounded-t-2xl',
          // Desktop: side drawer, right-aligned
          'md:inset-x-auto md:right-0 md:top-0 md:h-full md:w-full md:max-w-md md:rounded-none',
          // Common styles
          'bg-background border-t md:border-t-0 md:border-l border-border shadow-xl z-50',
          'transform transition-transform duration-200 ease-out',
          'flex flex-col'
        )}
      >
        {/* Header */}
        <div className="h-14 border-b border-border flex items-center justify-between px-4 shrink-0">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary" />
            <span className="font-medium text-sm">Thinking Partner</span>
            {pageContext.type !== 'global' && (
              <span className="text-xs text-muted-foreground px-2 py-0.5 bg-muted rounded">
                {pageContext.type === 'deliverable-detail' && pageContext.deliverable?.title}
                {pageContext.type === 'deliverable-review' && 'Reviewing'}
                {pageContext.type === 'deliverables-dashboard' && 'Dashboard'}
                {pageContext.type === 'project' && pageContext.projectName}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={minimize}
              className="p-1.5 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted"
              title="Minimize"
            >
              <Minus className="w-4 h-4" />
            </button>
            <button
              onClick={close}
              className="p-1.5 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted"
              title="Close (Esc)"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4">
          {messages.length === 0 ? (
            <div className="text-center py-8">
              <MessageSquare className="w-10 h-10 mx-auto mb-3 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground mb-4 max-w-xs mx-auto">
                {contextGreeting}
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
                        'px-3 py-2 rounded-2xl max-w-[85%] text-sm',
                        message.role === 'user'
                          ? 'bg-primary text-primary-foreground rounded-br-md'
                          : 'bg-muted rounded-bl-md'
                      )}
                    >
                      <p className="whitespace-pre-wrap">{message.content}</p>
                    </div>
                  </div>

                  {/* ADR-020: Inline tool result cards */}
                  {message.role === 'assistant' && message.toolResults && message.toolResults.length > 0 && (
                    <div className="space-y-2 pl-2">
                      {message.toolResults.map((result, resultIndex) => (
                        <ToolResultCard
                          key={resultIndex}
                          result={result}
                          onNavigate={(path) => {
                            router.push(path);
                            close();
                          }}
                        />
                      ))}
                    </div>
                  )}
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
        <div className="border-t border-border bg-background p-4 shrink-0">
          <form onSubmit={handleSubmit}>
            <div className="flex items-center gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask anything..."
                disabled={isLoading}
                className="flex-1 px-4 py-2.5 border border-border rounded-full bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary disabled:opacity-50"
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
