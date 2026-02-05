'use client';

/**
 * ADR-025: Claude Code Agentic Alignment
 * TPWorkPanel - Displays todo progress + chat during multi-step work
 *
 * This panel appears alongside surfaces when TP is performing multi-step
 * workflows (e.g., creating a deliverable via /board-update skill).
 * Shows real-time todo progress and allows continued conversation.
 *
 * Mobile: Displays as a bottom sheet overlay
 * Desktop: Displays as a side panel (360px)
 */

import { useState, useRef, useEffect } from 'react';
import { X, CheckCircle2, Circle, Loader2, Send, ChevronDown, ChevronUp } from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { Todo } from '@/types/desk';
import { cn } from '@/lib/utils';

interface TPWorkPanelProps {
  onCollapse: () => void;
  /** Mobile mode: render as bottom sheet overlay */
  mobile?: boolean;
}

export function TPWorkPanel({ onCollapse, mobile = false }: TPWorkPanelProps) {
  const { todos, messages, activeSkill, sendMessage, isLoading, status } = useTP();
  const [input, setInput] = useState('');
  const [mobileExpanded, setMobileExpanded] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage(input);
    setInput('');
  };

  // Get recent messages (last 10)
  const recentMessages = messages.slice(-10);

  // Format skill name for display
  const formatSkillName = (skill: string) => {
    return skill
      .split('-')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Mobile: Bottom sheet with expandable content
  if (mobile) {
    return (
      <>
        {/* Backdrop when expanded */}
        {mobileExpanded && (
          <div
            className="fixed inset-0 z-40 bg-black/20"
            onClick={() => setMobileExpanded(false)}
          />
        )}

        {/* Bottom sheet */}
        <div
          className={cn(
            'fixed inset-x-0 bottom-0 z-50',
            'bg-background border-t border-border rounded-t-2xl shadow-xl',
            'transition-all duration-300 ease-out',
            mobileExpanded ? 'max-h-[70vh]' : 'max-h-20'
          )}
        >
          {/* Handle + Header */}
          <button
            onClick={() => setMobileExpanded(!mobileExpanded)}
            className="w-full flex flex-col items-center"
          >
            {/* Drag handle */}
            <div className="w-10 h-1 rounded-full bg-muted-foreground/30 mt-2" />

            {/* Header row */}
            <div className="w-full flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-2">
                {isLoading && <Loader2 className="w-4 h-4 animate-spin text-primary" />}
                <span className="text-sm font-medium">
                  {activeSkill ? formatSkillName(activeSkill) : 'Working...'}
                </span>
                {todos.length > 0 && (
                  <span className="text-xs text-muted-foreground">
                    ({todos.filter((t) => t.status === 'completed').length}/{todos.length})
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {mobileExpanded ? (
                  <ChevronDown className="w-4 h-4 text-muted-foreground" />
                ) : (
                  <ChevronUp className="w-4 h-4 text-muted-foreground" />
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onCollapse();
                  }}
                  className="p-1 hover:bg-muted rounded transition-colors"
                  aria-label="Close panel"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
          </button>

          {/* Expandable content */}
          {mobileExpanded && (
            <div className="flex flex-col h-[calc(70vh-60px)] overflow-hidden">
              {/* Todos */}
              {todos.length > 0 && (
                <div className="px-4 py-3 border-t border-border bg-muted/30 shrink-0">
                  <div className="space-y-1.5 max-h-32 overflow-y-auto">
                    {todos.map((todo, i) => (
                      <TodoItem key={i} todo={todo} />
                    ))}
                  </div>
                </div>
              )}

              {/* Chat messages */}
              <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
                {recentMessages.length === 0 && !isLoading && (
                  <div className="text-sm text-muted-foreground text-center py-4">
                    No messages yet
                  </div>
                )}
                {recentMessages.map((msg) => (
                  <div
                    key={msg.id}
                    className={cn(
                      'text-sm',
                      msg.role === 'user' ? 'text-muted-foreground' : 'text-foreground'
                    )}
                  >
                    <span className="font-medium text-xs uppercase tracking-wide">
                      {msg.role === 'user' ? 'You' : 'TP'}
                    </span>
                    <p className="mt-0.5 whitespace-pre-wrap">{msg.content}</p>
                  </div>
                ))}

                {/* Status indicator */}
                {status.type === 'thinking' && (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    <span className="text-xs">Thinking...</span>
                  </div>
                )}
                {status.type === 'tool' && (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    <span className="text-xs">{status.toolName}...</span>
                  </div>
                )}
                {status.type === 'streaming' && (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    <span className="text-xs">Typing...</span>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <form onSubmit={handleSubmit} className="p-3 border-t border-border shrink-0">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    disabled={isLoading}
                    placeholder={isLoading ? 'Waiting...' : 'Type a response...'}
                    className="flex-1 px-3 py-2 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
                  />
                  <button
                    type="submit"
                    disabled={isLoading || !input.trim()}
                    className="px-3 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    aria-label="Send message"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      </>
    );
  }

  // Desktop: Side panel
  return (
    <div className="flex flex-col h-full bg-background border-l border-border">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2">
          {isLoading && <Loader2 className="w-4 h-4 animate-spin text-primary" />}
          <span className="text-sm font-medium">
            {activeSkill ? formatSkillName(activeSkill) : 'Working...'}
          </span>
        </div>
        <button
          onClick={onCollapse}
          className="p-1 hover:bg-muted rounded transition-colors"
          aria-label="Collapse panel"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Todos */}
      {todos.length > 0 && (
        <div className="px-4 py-3 border-b border-border bg-muted/30">
          <div className="text-xs font-medium text-muted-foreground mb-2">Progress</div>
          <div className="space-y-1.5">
            {todos.map((todo, i) => (
              <TodoItem key={i} todo={todo} />
            ))}
          </div>
        </div>
      )}

      {/* Chat messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {recentMessages.length === 0 && !isLoading && (
          <div className="text-sm text-muted-foreground text-center py-4">
            No messages yet
          </div>
        )}
        {recentMessages.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              'text-sm',
              msg.role === 'user' ? 'text-muted-foreground' : 'text-foreground'
            )}
          >
            <span className="font-medium text-xs uppercase tracking-wide">
              {msg.role === 'user' ? 'You' : 'TP'}
            </span>
            <p className="mt-0.5 whitespace-pre-wrap">{msg.content}</p>
          </div>
        ))}

        {/* Status indicator */}
        {status.type === 'thinking' && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span className="text-xs">Thinking...</span>
          </div>
        )}
        {status.type === 'tool' && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span className="text-xs">{status.toolName}...</span>
          </div>
        )}
        {status.type === 'streaming' && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span className="text-xs">Typing...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-border">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
            placeholder={isLoading ? 'Waiting...' : 'Type a response...'}
            className="flex-1 px-3 py-2 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-3 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label="Send message"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
}

function TodoItem({ todo }: { todo: Todo }) {
  return (
    <div className="flex items-center gap-2">
      {todo.status === 'completed' ? (
        <CheckCircle2 className="w-4 h-4 text-green-600 shrink-0" />
      ) : todo.status === 'in_progress' ? (
        <Loader2 className="w-4 h-4 text-primary animate-spin shrink-0" />
      ) : (
        <Circle className="w-4 h-4 text-muted-foreground shrink-0" />
      )}
      <span
        className={cn(
          'text-sm',
          todo.status === 'completed' && 'text-muted-foreground line-through',
          todo.status === 'in_progress' && 'text-foreground font-medium'
        )}
      >
        {todo.status === 'in_progress' ? todo.activeForm || todo.content : todo.content}
      </span>
    </div>
  );
}
