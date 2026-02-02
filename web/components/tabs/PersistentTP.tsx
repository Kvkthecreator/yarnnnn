'use client';

/**
 * ADR-022: Tab-Based Supervision Architecture
 *
 * Persistent TP layer - always visible at bottom of screen.
 * Context-aware: knows which tab is active and provides relevant quick actions.
 *
 * Unlike floating chat, this is NOT dismissible - it's the constant interaction layer.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Loader2, Sparkles, ChevronUp, ChevronDown, X } from 'lucide-react';
import { useTabs } from '@/contexts/TabContext';
import { useChat, type ChatMessage } from '@/hooks/useChat';
import { cn } from '@/lib/utils';

interface TPResponseCard {
  type: 'success' | 'preview' | 'error' | 'action';
  title: string;
  content?: string;
  actions?: { label: string; onClick: () => void }[];
}

export function PersistentTP() {
  const { activeTab, tpContext } = useTabs();
  const [input, setInput] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { messages, isLoading, error, sendMessage, clearMessages } = useChat({
    includeContext: true,
  });

  // Get latest response for inline display
  const latestAssistantMessage = messages
    .filter(m => m.role === 'assistant')
    .pop();

  // Auto-scroll when messages change
  useEffect(() => {
    if (isExpanded && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isExpanded]);

  // Handle form submit
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    let message = input;
    setInput('');

    // Add context based on active tab
    if (activeTab && tpContext) {
      const contextPrefix = getContextPrefix(tpContext.tabType, tpContext.title, tpContext.resourceId);
      if (contextPrefix && messages.length === 0) {
        message = `${contextPrefix}\n\n${message}`;
      }
    }

    await sendMessage(message);
    setIsExpanded(true);
  };

  // Handle quick action click
  const handleQuickAction = (prompt: string) => {
    setInput(prompt);
    inputRef.current?.focus();
  };

  // Clear conversation
  const handleClear = () => {
    clearMessages();
    setIsExpanded(false);
  };

  // Get context prefix for TP
  const getContextPrefix = (tabType: string, title: string, resourceId?: string) => {
    switch (tabType) {
      case 'deliverable':
        return `[Context: I'm viewing the "${title}" deliverable${resourceId ? ` (ID: ${resourceId})` : ''}]`;
      case 'version-review':
        return `[Context: I'm reviewing a draft of "${title}"]`;
      case 'memory':
        return `[Context: I'm viewing the memory "${title}"]`;
      case 'context':
        return `[Context: I'm viewing the context item "${title}"]`;
      case 'home':
        return '[Context: I\'m on the home dashboard]';
      default:
        return null;
    }
  };

  const quickActions = tpContext?.quickActions || [];

  return (
    <div className="border-t border-border bg-background">
      {/* Expanded conversation view */}
      {isExpanded && messages.length > 0 && (
        <div className="max-h-64 overflow-y-auto border-b border-border">
          <div className="p-4 space-y-3">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={cn(
                  "text-sm",
                  msg.role === 'user' ? "text-right" : "text-left"
                )}
              >
                <div className={cn(
                  "inline-block max-w-[80%] px-3 py-2 rounded-lg",
                  msg.role === 'user'
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                )}>
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Thinking...</span>
              </div>
            )}

            {error && (
              <div className="text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-lg">
                {error}
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Clear button */}
          <div className="flex justify-end px-4 pb-2">
            <button
              onClick={handleClear}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Clear conversation
            </button>
          </div>
        </div>
      )}

      {/* Collapsed response preview (when not expanded but has response) */}
      {!isExpanded && latestAssistantMessage && (
        <button
          onClick={() => setIsExpanded(true)}
          className="w-full px-4 py-2 text-left text-sm text-muted-foreground hover:bg-muted/50 border-b border-border flex items-center gap-2"
        >
          <Sparkles className="w-4 h-4 text-primary shrink-0" />
          <span className="truncate flex-1">{latestAssistantMessage.content}</span>
          <ChevronUp className="w-4 h-4 shrink-0" />
        </button>
      )}

      {/* Main TP input area */}
      <div className="p-3">
        {/* Quick actions */}
        {quickActions.length > 0 && !isExpanded && (
          <div className="flex flex-wrap gap-2 mb-3">
            {quickActions.map((action) => (
              <button
                key={action.id}
                onClick={() => handleQuickAction(action.prompt)}
                disabled={isLoading}
                className="px-3 py-1.5 text-xs border border-border rounded-full hover:bg-muted transition-colors disabled:opacity-50"
              >
                {action.label}
              </button>
            ))}
          </div>
        )}

        {/* Input form */}
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <div className="flex-1 flex items-center gap-2 px-3 py-2 bg-muted/30 border border-border rounded-lg focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary">
            <Sparkles className="w-4 h-4 text-muted-foreground shrink-0" />
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={getPlaceholder(tpContext?.tabType)}
              disabled={isLoading}
              className="flex-1 bg-transparent text-sm focus:outline-none placeholder:text-muted-foreground/70 disabled:opacity-50"
            />
            {isExpanded && messages.length > 0 && (
              <button
                type="button"
                onClick={() => setIsExpanded(false)}
                className="p-1 text-muted-foreground hover:text-foreground"
              >
                <ChevronDown className="w-4 h-4" />
              </button>
            )}
          </div>
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className={cn(
              "p-2.5 rounded-lg transition-colors",
              input.trim()
                ? "bg-primary text-primary-foreground hover:bg-primary/90"
                : "bg-muted text-muted-foreground"
            )}
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </form>

        {/* Context indicator */}
        {activeTab && activeTab.type !== 'home' && (
          <div className="mt-2 text-xs text-muted-foreground">
            Talking about: {activeTab.title}
          </div>
        )}
      </div>
    </div>
  );
}

// Helper to get placeholder text
function getPlaceholder(tabType?: string): string {
  switch (tabType) {
    case 'home':
      return 'Ask TP anything... "Create a deliverable", "What\'s due?"';
    case 'deliverable':
      return 'Ask about this deliverable... "Run now", "Change schedule"';
    case 'version-review':
      return 'Refine this draft... "Make it shorter", "More formal"';
    case 'memory':
      return 'Ask about this memory... "Edit", "Link to deliverable"';
    default:
      return 'Ask TP anything...';
  }
}
