"use client";

import { useState, useCallback, useRef } from "react";
import { createClient } from "@/lib/supabase/client";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface UseChatOptions {
  projectId: string;
  includeContext?: boolean;
}

interface UseChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
}

export function useChat({
  projectId,
  includeContext = true,
}: UseChatOptions): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return;

      // Add user message immediately
      const userMessage: ChatMessage = { role: "user", content };
      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      setError(null);

      // Cancel any existing request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      try {
        // Get auth token
        const supabase = createClient();
        const {
          data: { session },
        } = await supabase.auth.getSession();

        if (!session?.access_token) {
          throw new Error("Not authenticated");
        }

        // Build request with history (excluding the message we just added)
        const history = messages.map((m) => ({
          role: m.role,
          content: m.content,
        }));

        const response = await fetch(
          `${API_BASE_URL}/api/projects/${projectId}/chat`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${session.access_token}`,
            },
            body: JSON.stringify({
              content,
              include_context: includeContext,
              history,
            }),
            signal: abortControllerRef.current.signal,
          }
        );

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(
            errorData.detail || `Request failed: ${response.status}`
          );
        }

        // Handle SSE stream
        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error("No response body");
        }

        const decoder = new TextDecoder();
        let assistantContent = "";

        // Add empty assistant message that we'll update
        setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n");

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.slice(6));

                if (data.error) {
                  throw new Error(data.error);
                }

                if (data.content) {
                  assistantContent += data.content;
                  // Update the last message (assistant)
                  setMessages((prev) => {
                    const newMessages = [...prev];
                    newMessages[newMessages.length - 1] = {
                      role: "assistant",
                      content: assistantContent,
                    };
                    return newMessages;
                  });
                }

                if (data.done) {
                  // Stream complete
                  break;
                }
              } catch (parseError) {
                // Ignore parse errors for incomplete chunks
                console.debug("Parse error:", parseError);
              }
            }
          }
        }
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          // Request was cancelled, ignore
          return;
        }

        const errorMessage =
          err instanceof Error ? err.message : "An error occurred";
        setError(errorMessage);

        // Remove the empty assistant message if there was an error
        setMessages((prev) => {
          const lastMessage = prev[prev.length - 1];
          if (lastMessage?.role === "assistant" && !lastMessage.content) {
            return prev.slice(0, -1);
          }
          return prev;
        });
      } finally {
        setIsLoading(false);
        abortControllerRef.current = null;
      }
    },
    [projectId, includeContext, messages]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
  };
}
