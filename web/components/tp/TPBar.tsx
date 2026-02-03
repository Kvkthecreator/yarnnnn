'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * TPBar - Status hub and input for Thinking Partner
 *
 * Design: Status area above input shows TP's current state
 * - Idle: Subtle placeholder
 * - Thinking: "Processing..."
 * - Tool: "Opening context..." with spinner
 * - Streaming: Real-time response text
 * - Clarify: Question with inline option buttons
 * - Complete: Brief confirmation, fades to idle
 */

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, MessageCircle, X, ChevronDown, ChevronUp } from 'lucide-react';
import { useDesk } from '@/contexts/DeskContext';
import { useTP, TPStatus } from '@/contexts/TPContext';
import { cn } from '@/lib/utils';

// Human-readable tool names - conversational tone
const TOOL_LABELS: Record<string, string> = {
  respond: 'Composing response...',
  clarify: 'Need to ask you something...',
  list_memories: 'Pulling up your memories...',
  list_projects: 'Loading your projects...',
  list_deliverables: 'Checking your deliverables...',
  list_work: 'Looking at your work...',
  get_deliverable: 'Opening that deliverable...',
  get_work: 'Fetching work details...',
  create_project: 'Setting up the project...',
  create_memory: 'Remembering this...',
  create_work: 'Kicking off the work...',
  create_deliverable: 'Creating your deliverable...',
  run_deliverable: 'Generating the deliverable...',
  update_deliverable: 'Updating deliverable...',
  update_work: 'Updating work...',
  delete_memory: 'Removing from memory...',
  rename_project: 'Renaming project...',
  update_project: 'Updating project...',
  // Default fallback handled in component
};

function getToolLabel(toolName: string): string {
  return TOOL_LABELS[toolName] || `Running ${toolName}...`;
}

export function TPBar() {
  const { surface } = useDesk();
  const {
    sendMessage,
    isLoading,
    status,
    pendingClarification,
    respondToClarification,
    clearClarification,
    messages
  } = useTP();
  const [input, setInput] = useState('');
  const [mobileExpanded, setMobileExpanded] = useState(false);
  const [historyExpanded, setHistoryExpanded] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const statusRef = useRef<HTMLDivElement>(null);

  // Handle form submit
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    handleSend(input);
  };

  // Send message
  const handleSend = async (content: string) => {
    setInput('');
    await sendMessage(content, { surface });
  };

  // Handle clarification option click
  const handleOptionClick = (option: string) => {
    respondToClarification(option);
  };

  // Focus input when expanded on mobile
  useEffect(() => {
    if (mobileExpanded) {
      inputRef.current?.focus();
    }
  }, [mobileExpanded]);

  // Render status content based on current state
  const renderStatus = (currentStatus: TPStatus) => {
    switch (currentStatus.type) {
      case 'idle':
        return null;

      case 'thinking':
        return (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">Thinking...</span>
          </div>
        );

      case 'tool':
        return (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">{getToolLabel(currentStatus.toolName)}</span>
          </div>
        );

      case 'streaming':
        return (
          <div className="text-sm text-foreground">
            {currentStatus.content}
          </div>
        );

      case 'clarify':
        return (
          <div className="space-y-2">
            <p className="text-sm text-foreground">{currentStatus.question}</p>
            {currentStatus.options && currentStatus.options.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {currentStatus.options.map((option, i) => (
                  <button
                    key={i}
                    onClick={() => handleOptionClick(option)}
                    className="px-3 py-1.5 text-sm rounded-full bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
                  >
                    {option}
                  </button>
                ))}
              </div>
            )}
          </div>
        );

      case 'complete':
        if (!currentStatus.message) return null;
        return (
          <div className="text-sm text-foreground">
            {currentStatus.message}
          </div>
        );

      default:
        return null;
    }
  };

  const hasStatus = status.type !== 'idle';
  const recentMessages = messages.slice(-3); // Show last 3 messages in history

  return (
    <>
      {/* Mobile FAB - visible only on small screens when collapsed */}
      <button
        onClick={() => setMobileExpanded(true)}
        className={cn(
          'fixed bottom-6 right-6 z-50',
          'w-14 h-14 rounded-full',
          'bg-primary text-primary-foreground',
          'shadow-lg shadow-primary/25',
          'flex items-center justify-center',
          'transition-all duration-200',
          'hover:scale-105 active:scale-95',
          'md:hidden',
          mobileExpanded ? 'scale-0 opacity-0' : 'scale-100 opacity-100'
        )}
        aria-label="Ask TP"
      >
        <MessageCircle className="w-6 h-6" />
      </button>

      {/* Main TP Bar */}
      <div
        className={cn(
          'shrink-0 bg-background',
          'transition-all duration-200',
          mobileExpanded
            ? 'fixed inset-x-0 bottom-0 z-50 bg-background md:relative'
            : 'hidden md:block'
        )}
      >
        <div className="max-w-2xl mx-auto px-4">
          {/* History toggle (when there are messages) */}
          {messages.length > 0 && !hasStatus && (
            <button
              onClick={() => setHistoryExpanded(!historyExpanded)}
              className="w-full flex items-center justify-center gap-1 py-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              {historyExpanded ? (
                <>
                  <ChevronDown className="w-3 h-3" />
                  Hide history
                </>
              ) : (
                <>
                  <ChevronUp className="w-3 h-3" />
                  {messages.length} message{messages.length !== 1 ? 's' : ''}
                </>
              )}
            </button>
          )}

          {/* Message history (collapsed by default) */}
          {historyExpanded && !hasStatus && (
            <div className="mb-2 p-3 rounded-lg bg-muted/50 max-h-48 overflow-y-auto">
              {recentMessages.map((msg, i) => (
                <div
                  key={msg.id}
                  className={cn(
                    'text-sm py-1',
                    msg.role === 'user' ? 'text-muted-foreground' : 'text-foreground'
                  )}
                >
                  <span className="font-medium">
                    {msg.role === 'user' ? 'You: ' : 'TP: '}
                  </span>
                  {msg.content.slice(0, 150)}
                  {msg.content.length > 150 && '...'}
                </div>
              ))}
            </div>
          )}

          {/* Status area - prominent when visible for user assurance */}
          {hasStatus && (
            <div
              ref={statusRef}
              className="mb-2 p-3 rounded-lg bg-muted border border-border shadow-md animate-in fade-in slide-in-from-bottom-2 duration-200"
            >
              {renderStatus(status)}
            </div>
          )}
        </div>

        {/* Input container */}
        <div className="p-4 pb-6 md:pb-4">
          <div className="max-w-2xl mx-auto">
            <form onSubmit={handleSubmit}>
              <div className="relative flex items-center gap-2">
                {/* Close button on mobile */}
                {mobileExpanded && (
                  <button
                    type="button"
                    onClick={() => setMobileExpanded(false)}
                    className="md:hidden p-2 text-muted-foreground hover:text-foreground"
                    aria-label="Close"
                  >
                    <X className="w-5 h-5" />
                  </button>
                )}

                {/* Input field */}
                <div className="flex-1 relative">
                  <input
                    ref={inputRef}
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    disabled={isLoading}
                    placeholder={
                      status.type === 'clarify'
                        ? 'Type your answer...'
                        : 'Ask anything...'
                    }
                    className={cn(
                      'w-full px-5 py-3 pr-14',
                      'border border-border rounded-full',
                      'text-sm bg-background',
                      'shadow-lg shadow-black/5',
                      'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary',
                      'disabled:opacity-50'
                    )}
                  />

                  {/* Send button */}
                  <button
                    type="submit"
                    disabled={isLoading || !input.trim()}
                    className={cn(
                      'absolute right-2 top-1/2 -translate-y-1/2',
                      'p-2.5 rounded-full',
                      'bg-primary text-primary-foreground',
                      'disabled:opacity-50',
                      'hover:bg-primary/90 transition-colors'
                    )}
                  >
                    {isLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      </div>

      {/* Mobile backdrop */}
      {mobileExpanded && (
        <div
          className="fixed inset-0 z-40 bg-black/20 md:hidden"
          onClick={() => setMobileExpanded(false)}
        />
      )}
    </>
  );
}
