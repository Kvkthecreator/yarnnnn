"use client";

import { useState, useRef, useEffect, FormEvent } from "react";
import { Send, Loader2 } from "lucide-react";
import { useChat } from "@/hooks/useChat";

interface ChatProps {
  /**
   * Project ID for project-scoped chat.
   * Omit for global (user-level) chat.
   */
  projectId?: string;
  /**
   * Whether to include context in the chat.
   * For project chat: includes user + project context.
   * For global chat: includes user context only.
   */
  includeContext?: boolean;
  /**
   * Custom empty state message
   */
  emptyMessage?: string;
  /**
   * Custom height class (default: h-[calc(100vh-240px)])
   */
  heightClass?: string;
}

/**
 * Reusable chat component for Thinking Partner conversations.
 *
 * Supports two modes:
 * - Project chat: Pass projectId for project + user context
 * - Global chat: Omit projectId for user context only
 */
export function Chat({
  projectId,
  includeContext = true,
  emptyMessage,
  heightClass = "h-[calc(100vh-240px)]",
}: ChatProps) {
  const { messages, isLoading, isLoadingHistory, error, sendMessage } = useChat({
    projectId,
    includeContext,
  });
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const message = input;
    setInput("");
    await sendMessage(message);
  };

  const defaultEmptyMessage = projectId
    ? "Hi! I'm your Thinking Partner. I can help you analyze your project context and think through problems. What would you like to explore?"
    : "Hi! I'm your Thinking Partner. I'm here to help you think through ideas, explore problems, and work on anything. What's on your mind?";

  return (
    <div className={`flex flex-col ${heightClass}`}>
      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {isLoadingHistory && (
          <div className="flex justify-center py-4">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        )}

        {!isLoadingHistory && messages.length === 0 && (
          <div className="p-4 bg-muted rounded-lg max-w-[80%]">
            <p className="text-sm">{emptyMessage || defaultEmptyMessage}</p>
          </div>
        )}

        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${
              message.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`p-4 rounded-lg max-w-[80%] ${
                message.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted"
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
            </div>
          </div>
        ))}

        {isLoading && messages[messages.length - 1]?.role !== "assistant" && (
          <div className="flex justify-start">
            <div className="p-4 bg-muted rounded-lg">
              <Loader2 className="w-4 h-4 animate-spin" />
            </div>
          </div>
        )}

        {error && (
          <div className="p-4 bg-destructive/10 text-destructive rounded-lg max-w-[80%]">
            <p className="text-sm">Error: {error}</p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="border-t border-border pt-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message..."
            disabled={isLoading}
            className="flex-1 px-4 py-2 border border-border rounded-md bg-background disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md disabled:opacity-50 flex items-center gap-2"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
