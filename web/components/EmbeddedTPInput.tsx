'use client';

/**
 * ADR-021: Embedded TP Input
 *
 * An embedded Thinking Partner input that appears directly on the page
 * (not as a floating panel). Used for the TP presence rule: TP must be
 * visible and interactive on every screen.
 *
 * This component shows:
 * - A text input for natural language commands
 * - Quick action chips relevant to the context
 * - Inline response area when TP responds
 */

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Sparkles, X, ChevronUp, ChevronDown } from 'lucide-react';
import { useChat } from '@/hooks/useChat';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';

interface QuickAction {
  label: string;
  prompt: string;
}

interface EmbeddedTPInputProps {
  /** Page context type for appropriate quick actions */
  context: 'dashboard' | 'detail' | 'browse';
  /** Optional deliverable context for scoped conversations */
  deliverableId?: string;
  deliverableTitle?: string;
  /** Custom quick actions (optional - defaults based on context) */
  quickActions?: QuickAction[];
  /** Callback when TP creates a new deliverable */
  onDeliverableCreated?: (id: string) => void;
  /** Callback when TP modifies something requiring refresh */
  onRefreshNeeded?: () => void;
  /** Custom placeholder text */
  placeholder?: string;
  /** Whether to show expanded response area by default */
  defaultExpanded?: boolean;
}

const DEFAULT_QUICK_ACTIONS: Record<string, QuickAction[]> = {
  dashboard: [
    { label: 'Create new', prompt: "I'd like to create a new recurring deliverable" },
    { label: "What's due", prompt: 'What deliverables are coming up soon?' },
    { label: 'Run all', prompt: 'Run all my active deliverables now' },
  ],
  detail: [
    { label: 'Run now', prompt: 'Generate a new version of this deliverable now' },
    { label: 'Edit schedule', prompt: 'Help me change the schedule for this deliverable' },
    { label: 'Show history', prompt: 'Show me the version history and quality trend' },
  ],
  browse: [
    { label: 'Search', prompt: 'Help me find a specific deliverable' },
    { label: 'Filter', prompt: 'Show me only paused deliverables' },
    { label: 'Stats', prompt: 'Give me a summary of all my deliverables' },
  ],
};

export function EmbeddedTPInput({
  context,
  deliverableId,
  deliverableTitle,
  quickActions,
  onDeliverableCreated,
  onRefreshNeeded,
  placeholder,
  defaultExpanded = false,
}: EmbeddedTPInputProps) {
  const router = useRouter();
  const [input, setInput] = useState('');
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const inputRef = useRef<HTMLInputElement>(null);
  const responseRef = useRef<HTMLDivElement>(null);

  const { messages, isLoading, error, sendMessage, clearMessages } = useChat({
    // No projectId - global context, TP can access all deliverables
    includeContext: true,
    onToolResult: (result) => {
      // Check if a deliverable was created
      const data = result.result as { success?: boolean; deliverable?: { id?: string } };
      if (result.name === 'create_deliverable' && data.success && data.deliverable?.id) {
        onDeliverableCreated?.(data.deliverable.id);
      }
      // Refresh on any successful modification
      if (data.success) {
        onRefreshNeeded?.();
      }
    },
  });

  // Get the latest assistant response
  const latestResponse = messages.filter(m => m.role === 'assistant').pop();

  // Auto-expand when we get a response
  useEffect(() => {
    if (latestResponse?.content) {
      setIsExpanded(true);
    }
  }, [latestResponse?.content]);

  // Scroll response into view when it updates
  useEffect(() => {
    if (isExpanded && responseRef.current && latestResponse?.content) {
      responseRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [isExpanded, latestResponse?.content]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    let message = input;
    setInput('');

    // Add context for detail page
    if (context === 'detail' && deliverableTitle) {
      message = `[Context: I'm viewing my "${deliverableTitle}" deliverable${deliverableId ? ` (ID: ${deliverableId})` : ''}]\n\n${message}`;
    }

    await sendMessage(message);
  };

  const handleQuickAction = (prompt: string) => {
    setInput(prompt);
    inputRef.current?.focus();
  };

  const handleDismiss = () => {
    clearMessages();
    setIsExpanded(false);
  };

  const actions = quickActions || DEFAULT_QUICK_ACTIONS[context] || [];
  const defaultPlaceholder = context === 'dashboard'
    ? 'Ask TP: "Create a new deliverable" / "Run now"'
    : context === 'detail'
    ? 'Ask TP about this deliverable...'
    : 'Ask TP anything...';

  return (
    <div className="w-full">
      {/* Response area - shown when there's a response */}
      {isExpanded && latestResponse?.content && (
        <div
          ref={responseRef}
          className="mb-3 p-4 bg-muted/50 border border-border rounded-lg"
        >
          <div className="flex items-start justify-between gap-2 mb-2">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-primary shrink-0" />
              <span className="text-xs font-medium text-muted-foreground">Thinking Partner</span>
            </div>
            <button
              onClick={handleDismiss}
              className="p-1 text-muted-foreground hover:text-foreground rounded"
              title="Dismiss"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="text-sm whitespace-pre-wrap leading-relaxed">
            {latestResponse.content}
          </div>
          {isLoading && (
            <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>Thinking...</span>
            </div>
          )}
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="mb-3 p-3 bg-destructive/10 border border-destructive/20 rounded-lg text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Input area */}
      <div className="relative">
        <form onSubmit={handleSubmit}>
          <div className="flex items-center gap-2 p-2 bg-muted/30 border border-border rounded-lg focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition-all">
            <Sparkles className="w-4 h-4 text-muted-foreground ml-2 shrink-0" />
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={placeholder || defaultPlaceholder}
              disabled={isLoading}
              className="flex-1 bg-transparent text-sm focus:outline-none placeholder:text-muted-foreground/70 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className={cn(
                "p-2 rounded-md transition-colors",
                input.trim()
                  ? "bg-primary text-primary-foreground hover:bg-primary/90"
                  : "text-muted-foreground hover:bg-muted"
              )}
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </div>
        </form>

        {/* Quick actions - shown when no active conversation */}
        {!latestResponse?.content && actions.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-2">
            {actions.map((action) => (
              <button
                key={action.label}
                onClick={() => handleQuickAction(action.prompt)}
                disabled={isLoading}
                className="px-3 py-1 text-xs border border-border rounded-full hover:bg-muted transition-colors disabled:opacity-50"
              >
                {action.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
