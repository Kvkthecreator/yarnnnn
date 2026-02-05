'use client';

/**
 * ADR-025 Addendum: Conversation as First-Class Surface
 *
 * Full-screen deliberation surface for extended TP conversations.
 * Used when:
 * - A skill is invoked (e.g., /board-update)
 * - Multi-turn clarification is needed
 * - User explicitly requests a chat session
 *
 * Unlike the side panel (TPWorkPanel), this gives conversation
 * full attention as befitting deliberation.
 */

import { useState, useRef, useEffect } from 'react';
import {
  ArrowLeft,
  CheckCircle2,
  Circle,
  Loader2,
  Send,
  MessageSquare,
  FileText,
  FolderKanban,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useDesk } from '@/contexts/DeskContext';
import { Todo } from '@/types/desk';
import { cn } from '@/lib/utils';

interface ConversationSurfaceProps {
  context?: {
    deliverableId?: string;
    projectId?: string;
    skillName?: string;
  };
}

export function ConversationSurface({ context }: ConversationSurfaceProps) {
  const { todos, messages, activeSkill, sendMessage, isLoading, status } = useTP();
  const { setSurface } = useDesk();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage(input);
    setInput('');
  };

  const handleBack = () => {
    // Return to idle surface
    setSurface({ type: 'idle' });
  };

  // Format skill name for display
  const formatSkillName = (skill: string) => {
    return skill
      .split('-')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Determine conversation title
  const getTitle = () => {
    if (activeSkill) return formatSkillName(activeSkill);
    if (context?.skillName) return formatSkillName(context.skillName);
    return 'Conversation';
  };

  // Context badge
  const ContextBadge = () => {
    if (context?.deliverableId) {
      return (
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground bg-muted px-2 py-1 rounded">
          <FileText className="w-3 h-3" />
          Deliverable
        </span>
      );
    }
    if (context?.projectId) {
      return (
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground bg-muted px-2 py-1 rounded">
          <FolderKanban className="w-3 h-3" />
          Project
        </span>
      );
    }
    return null;
  };

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={handleBack}
            className="p-2 hover:bg-muted rounded-lg transition-colors"
            aria-label="Back to desk"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-primary" />
            <span className="font-medium">{getTitle()}</span>
            {isLoading && <Loader2 className="w-4 h-4 animate-spin text-primary" />}
          </div>
        </div>
        <ContextBadge />
      </div>

      {/* Main content area */}
      <div className="flex-1 overflow-hidden flex flex-col lg:flex-row">
        {/* Messages panel */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Todo progress (when active) */}
          {todos.length > 0 && (
            <div className="px-4 py-3 border-b border-border bg-muted/30 shrink-0">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-muted-foreground">Progress</span>
                <span className="text-xs text-muted-foreground">
                  {todos.filter((t) => t.status === 'completed').length}/{todos.length}
                </span>
              </div>
              <div className="space-y-1.5 max-h-32 overflow-y-auto">
                {todos.map((todo, i) => (
                  <TodoItem key={i} todo={todo} />
                ))}
              </div>
            </div>
          )}

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-4">
            <div className="max-w-2xl mx-auto space-y-4">
              {messages.length === 0 && !isLoading && (
                <div className="text-center py-12">
                  <MessageSquare className="w-12 h-12 text-muted-foreground/30 mx-auto mb-3" />
                  <p className="text-muted-foreground">
                    {activeSkill
                      ? `Starting ${formatSkillName(activeSkill)}...`
                      : 'Start a conversation'}
                  </p>
                </div>
              )}

              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={cn(
                    'rounded-lg p-3',
                    msg.role === 'user'
                      ? 'bg-primary text-primary-foreground ml-8'
                      : 'bg-muted mr-8'
                  )}
                >
                  <span className="text-xs font-medium opacity-70 uppercase tracking-wide block mb-1">
                    {msg.role === 'user' ? 'You' : 'TP'}
                  </span>
                  <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                </div>
              ))}

              {/* Status indicator */}
              {status.type === 'thinking' && (
                <div className="flex items-center gap-2 text-muted-foreground bg-muted rounded-lg p-3 mr-8">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">Thinking...</span>
                </div>
              )}
              {status.type === 'tool' && (
                <div className="flex items-center gap-2 text-muted-foreground bg-muted rounded-lg p-3 mr-8">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">{status.toolName}...</span>
                </div>
              )}
              {status.type === 'streaming' && (
                <div className="flex items-center gap-2 text-muted-foreground bg-muted rounded-lg p-3 mr-8">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">Typing...</span>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input */}
          <form onSubmit={handleSubmit} className="p-4 border-t border-border shrink-0">
            <div className="max-w-2xl mx-auto flex gap-3">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={isLoading}
                placeholder={isLoading ? 'Waiting for response...' : 'Type your message...'}
                className="flex-1 px-4 py-3 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary disabled:opacity-50 transition-all"
              />
              <button
                type="submit"
                disabled={isLoading || !input.trim()}
                className="px-4 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                aria-label="Send message"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </form>
        </div>
      </div>
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
