'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * TPMessages - Inline TP response messages
 */

import { X, Bot, User } from 'lucide-react';
import { TPMessage } from '@/types/desk';
import { ToolResultList } from './ToolResultCard';

interface TPMessagesProps {
  messages: TPMessage[];
  onDismiss: () => void;
}

export function TPMessages({ messages, onDismiss }: TPMessagesProps) {
  // Only show the last few messages
  const recentMessages = messages.slice(-3);

  if (recentMessages.length === 0) return null;

  return (
    <div className="px-4 pt-4 pb-2 border-b border-border bg-muted/20">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 space-y-2 max-h-40 overflow-y-auto">
          {recentMessages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-2 ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {message.role === 'assistant' && (
                <div className="shrink-0 w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center">
                  <Bot className="w-3.5 h-3.5 text-primary" />
                </div>
              )}

              <div
                className={`max-w-[80%] px-3 py-2 rounded-lg text-sm ${
                  message.role === 'user'
                    ? 'bg-primary text-primary-foreground rounded-br-sm'
                    : 'bg-muted rounded-bl-sm'
                }`}
              >
                <p className="whitespace-pre-wrap">{message.content}</p>

                {/* Inline tool results - Claude Code style */}
                {message.toolResults && message.toolResults.length > 0 && (
                  <ToolResultList results={message.toolResults} compact />
                )}
              </div>

              {message.role === 'user' && (
                <div className="shrink-0 w-6 h-6 rounded-full bg-muted flex items-center justify-center">
                  <User className="w-3.5 h-3.5 text-muted-foreground" />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Dismiss button */}
        <button
          onClick={onDismiss}
          className="shrink-0 p-1 hover:bg-muted rounded"
          aria-label="Dismiss messages"
        >
          <X className="w-4 h-4 text-muted-foreground" />
        </button>
      </div>
    </div>
  );
}
