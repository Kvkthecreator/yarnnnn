"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { createClient } from "@/lib/supabase/client";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Tool result data for inline display
export interface ToolResultData {
  toolName: string;
  success: boolean;
  data: Record<string, unknown>;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  // Tool results associated with this message (for inline cards)
  toolResults?: ToolResultData[];
}

interface ToolUseEvent {
  id: string;
  name: string;
  input: Record<string, unknown>;
}

interface ToolResultEvent {
  tool_use_id: string;
  name: string;
  result: Record<string, unknown>;
}

// ADR-013: UI action from TP tool responses
interface TPUIAction {
  type: "OPEN_SURFACE" | "CLOSE_SURFACE";
  surface?: "output" | "context" | "schedule" | "export";
  data?: Record<string, unknown>;
}

interface UseChatOptions {
  projectId?: string; // Optional - omit for global (user-level) chat
  includeContext?: boolean;
  onToolUse?: (tool: ToolUseEvent) => void; // Called when TP uses a tool
  onToolResult?: (result: ToolResultEvent) => void; // Called with tool result
  onProjectChange?: () => void; // Called when a project is created/modified
  onUIAction?: (action: TPUIAction) => void; // ADR-013: Called when TP triggers UI action
}

interface UseChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  isLoadingHistory: boolean;
  error: string | null;
  toolsUsed: string[]; // Tools used in the current response
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
}

/**
 * Hook for chat with Thinking Partner.
 *
 * ADR-006: Session management is handled server-side.
 * - Sessions are reused daily (one session per project per day)
 * - Messages are persisted to session_messages table
 * - History is loaded from server on mount
 *
 * ADR-007: Tool use with streaming.
 * - TP can use tools (list_projects, create_project, etc.)
 * - Tool events are streamed inline with text
 * - onProjectChange callback triggers sidebar refresh
 *
 * Two modes:
 * - Project chat: Pass projectId to use project + user context
 * - Global chat: Omit projectId to use user context only
 */
export function useChat({
  projectId,
  includeContext = true,
  onToolUse,
  onToolResult,
  onProjectChange,
  onUIAction,
}: UseChatOptions = {}): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toolsUsed, setToolsUsed] = useState<string[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);
  const historyLoadedForRef = useRef<string | null>(null); // Track which projectId history was loaded for

  // Load chat history on mount or when projectId changes
  useEffect(() => {
    // Create a key to track what we've loaded history for
    const currentKey = projectId ?? 'global';

    // Skip if we already loaded history for this exact context
    if (historyLoadedForRef.current === currentKey) return;

    const loadHistory = async () => {
      setIsLoadingHistory(true);
      // Clear existing messages when switching contexts
      if (historyLoadedForRef.current !== null) {
        setMessages([]);
      }

      try {
        const supabase = createClient();
        const {
          data: { session },
        } = await supabase.auth.getSession();

        if (!session?.access_token) return;

        // Use project or global history endpoint
        const endpoint = projectId
          ? `${API_BASE_URL}/api/projects/${projectId}/chat/history?limit=1`
          : `${API_BASE_URL}/api/chat/history?limit=1`;

        const response = await fetch(endpoint, {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          // Load the most recent session's messages
          if (data.sessions?.length > 0) {
            const latestSession = data.sessions[0];
            const sessionMessages: ChatMessage[] = (latestSession.messages || [])
              .filter((m: { role: string; content: string }) =>
                m.role === "user" || m.role === "assistant"
              )
              .map((m: { role: string; content: string }) => ({
                role: m.role as "user" | "assistant",
                content: m.content,
              }));

            if (sessionMessages.length > 0) {
              setMessages(sessionMessages);
            }
          }
        }
      } catch (err) {
        console.error("Failed to load chat history:", err);
      } finally {
        setIsLoadingHistory(false);
        historyLoadedForRef.current = currentKey;
      }
    };

    loadHistory();
  }, [projectId]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return;

      // Add user message immediately (optimistic update)
      const userMessage: ChatMessage = { role: "user", content };
      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      setError(null);
      setToolsUsed([]); // Reset tools for new message

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

        // Use project endpoint or global endpoint based on projectId
        const endpoint = projectId
          ? `${API_BASE_URL}/api/projects/${projectId}/chat`
          : `${API_BASE_URL}/api/chat`;

        // Note: No longer sending history - server manages session history
        const response = await fetch(endpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session.access_token}`,
          },
          body: JSON.stringify({
            content,
            include_context: includeContext,
          }),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => null);
          let errorMessage = `Request failed: ${response.status}`;
          if (errorData?.detail) {
            if (Array.isArray(errorData.detail)) {
              errorMessage = errorData.detail
                .map((e: { msg?: string; loc?: string[] }) =>
                  e.msg || JSON.stringify(e)
                )
                .join(", ");
            } else if (typeof errorData.detail === "string") {
              errorMessage = errorData.detail;
            } else {
              errorMessage = JSON.stringify(errorData.detail);
            }
          }
          throw new Error(errorMessage);
        }

        // Handle SSE stream
        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error("No response body");
        }

        const decoder = new TextDecoder();
        let assistantContent = "";
        const currentToolsUsed: string[] = [];
        const currentToolResults: ToolResultData[] = [];
        let projectModified = false;

        // Add empty assistant message that we'll update
        setMessages((prev) => [...prev, { role: "assistant", content: "", toolResults: [] }]);

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
                      toolResults: [...currentToolResults],
                    };
                    return newMessages;
                  });
                }

                // Handle tool use event (ADR-007)
                if (data.tool_use) {
                  const toolEvent = data.tool_use as ToolUseEvent;
                  currentToolsUsed.push(toolEvent.name);
                  setToolsUsed([...currentToolsUsed]);
                  onToolUse?.(toolEvent);

                  // Track if project-modifying tools are used
                  if (["create_project", "rename_project", "update_project"].includes(toolEvent.name)) {
                    projectModified = true;
                  }
                }

                // Handle tool result event (ADR-007)
                if (data.tool_result) {
                  const resultEvent = data.tool_result as ToolResultEvent;
                  console.log("[useChat] tool_result received:", resultEvent.name, resultEvent.result);
                  onToolResult?.(resultEvent);

                  // ADR-020: Collect tool results for inline display
                  const result = resultEvent.result as { success?: boolean; ui_action?: TPUIAction };
                  currentToolResults.push({
                    toolName: resultEvent.name,
                    success: result?.success ?? true,
                    data: resultEvent.result,
                  });

                  // Update message with tool results
                  setMessages((prev) => {
                    const newMessages = [...prev];
                    newMessages[newMessages.length - 1] = {
                      role: "assistant",
                      content: assistantContent,
                      toolResults: [...currentToolResults],
                    };
                    return newMessages;
                  });

                  // ADR-013: Check for UI action in tool result
                  if (result?.ui_action) {
                    console.log("[useChat] ui_action found:", result.ui_action);
                    onUIAction?.(result.ui_action);
                  }
                }

                if (data.done) {
                  // Stream complete
                  if (data.tools_used?.length > 0) {
                    setToolsUsed(data.tools_used);
                  }
                  // Trigger sidebar refresh if project was modified
                  if (projectModified) {
                    onProjectChange?.();
                  }
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
    [projectId, includeContext, onToolUse, onToolResult, onProjectChange, onUIAction]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
    // Note: We don't reset historyLoadedForRef here - caller should
    // reload history explicitly if needed by changing projectId
  }, []);

  return {
    messages,
    isLoading,
    isLoadingHistory,
    error,
    toolsUsed,
    sendMessage,
    clearMessages,
  };
}
