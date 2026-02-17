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

// A segment is either text or a tool indicator (Claude Code style)
export interface MessageSegment {
  type: "text" | "tool";
  content?: string; // For text segments
  toolName?: string; // For tool segments
  success?: boolean; // For tool segments (undefined = still running)
  error?: string; // For failed tools
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  // Tool results associated with this message (for inline cards) - legacy
  toolResults?: ToolResultData[];
  // New: Interleaved segments for Claude Code-style display
  segments?: MessageSegment[];
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
  includeContext?: boolean;
  onToolUse?: (tool: ToolUseEvent) => void; // Called when TP uses a tool
  onToolResult?: (result: ToolResultEvent) => void; // Called with tool result
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
 * - Sessions are reused daily (one session per day)
 * - Messages are persisted to session_messages table
 * - History is loaded from server on mount
 *
 * ADR-007: Tool use with streaming.
 * - TP can use tools (list_deliverables, create_deliverable, etc.)
 * - Tool events are streamed inline with text
 *
 * ADR-034: Project concept removed - all chat is user-scoped.
 */
export function useChat({
  includeContext = true,
  onToolUse,
  onToolResult,
  onUIAction,
}: UseChatOptions = {}): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toolsUsed, setToolsUsed] = useState<string[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);
  const historyLoadedRef = useRef(false);

  // Load chat history on mount
  useEffect(() => {
    if (historyLoadedRef.current) return;
    historyLoadedRef.current = true;

    const loadHistory = async () => {
      setIsLoadingHistory(true);

      try {
        const supabase = createClient();
        const {
          data: { session },
        } = await supabase.auth.getSession();

        if (!session?.access_token) return;

        const response = await fetch(
          `${API_BASE_URL}/api/chat/history?limit=1`,
          {
            headers: {
              Authorization: `Bearer ${session.access_token}`,
            },
          }
        );

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
      }
    };

    loadHistory();
  }, []);

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

        // Note: No longer sending history - server manages session history
        const response = await fetch(`${API_BASE_URL}/api/chat`, {
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

        // Claude Code-style segments: interleave text and tool status
        const segments: MessageSegment[] = [];
        let currentTextSegment = ""; // Text accumulated since last tool
        let pendingToolName: string | null = null; // Tool currently executing

        // Add empty assistant message that we'll update
        setMessages((prev) => [...prev, { role: "assistant", content: "", toolResults: [], segments: [] }]);

        // Helper to update the message with current state
        const updateMessage = () => {
          // Build segments array with current text at the end
          const displaySegments: MessageSegment[] = [...segments];

          // Add pending tool if one is running
          if (pendingToolName) {
            displaySegments.push({ type: "tool", toolName: pendingToolName, success: undefined });
          }

          // Add current text segment if non-empty
          if (currentTextSegment.trim()) {
            displaySegments.push({ type: "text", content: currentTextSegment });
          }

          setMessages((prev) => {
            const newMessages = [...prev];
            newMessages[newMessages.length - 1] = {
              role: "assistant",
              content: assistantContent, // Keep full content for compatibility
              toolResults: [...currentToolResults],
              segments: displaySegments,
            };
            return newMessages;
          });
        };

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
                  currentTextSegment += data.content;
                  updateMessage();
                }

                // Handle tool use event (ADR-007)
                if (data.tool_use) {
                  const toolEvent = data.tool_use as ToolUseEvent;
                  currentToolsUsed.push(toolEvent.name);
                  setToolsUsed([...currentToolsUsed]);
                  onToolUse?.(toolEvent);

                  // Finalize current text segment before tool
                  if (currentTextSegment.trim()) {
                    segments.push({ type: "text", content: currentTextSegment });
                    currentTextSegment = "";
                  }

                  // Mark tool as pending (running)
                  pendingToolName = toolEvent.name;
                  updateMessage();
                }

                // Handle tool result event (ADR-007)
                if (data.tool_result) {
                  const resultEvent = data.tool_result as ToolResultEvent;
                  console.log("[useChat] tool_result received:", resultEvent.name, resultEvent.result);
                  onToolResult?.(resultEvent);

                  // ADR-020: Collect tool results for inline display
                  const result = resultEvent.result as { success?: boolean; ui_action?: TPUIAction; error?: string; message?: string };
                  currentToolResults.push({
                    toolName: resultEvent.name,
                    success: result?.success ?? true,
                    data: resultEvent.result,
                  });

                  // Finalize the tool segment with result
                  const errorMsg = !result?.success ? (result?.error || result?.message || "failed") : undefined;
                  segments.push({
                    type: "tool",
                    toolName: resultEvent.name,
                    success: result?.success ?? true,
                    error: typeof errorMsg === 'string' ? errorMsg : undefined,
                  });
                  pendingToolName = null;

                  updateMessage();

                  // ADR-013: Check for UI action in tool result
                  if (result?.ui_action) {
                    console.log("[useChat] ui_action found:", result.ui_action);
                    onUIAction?.(result.ui_action);
                  }
                }

                if (data.done) {
                  // Stream complete - finalize any remaining text
                  if (currentTextSegment.trim()) {
                    segments.push({ type: "text", content: currentTextSegment });
                    currentTextSegment = "";
                  }
                  updateMessage();

                  if (data.tools_used?.length > 0) {
                    setToolsUsed(data.tools_used);
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
    [includeContext, onToolUse, onToolResult, onUIAction]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
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
