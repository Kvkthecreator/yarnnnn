'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * TP (Thinking Partner) context - manages conversation state
 */

import React, { createContext, useContext, useReducer, useCallback, useRef, useState, ReactNode } from 'react';
import { createClient } from '@/lib/supabase/client';
import { TPState, TPAction, TPMessage, TPToolResult, mapToolActionToSurface, DeskSurface } from '@/types/desk';

// API base URL - must match the Python backend
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// =============================================================================
// Initial State
// =============================================================================

const initialState: TPState = {
  messages: [],
  isLoading: false,
  error: null,
};

// =============================================================================
// Reducer
// =============================================================================

function tpReducer(state: TPState, action: TPAction): TPState {
  switch (action.type) {
    case 'ADD_MESSAGE':
      return {
        ...state,
        messages: [...state.messages, action.message],
        error: null,
      };

    case 'SET_MESSAGES':
      return { ...state, messages: action.messages };

    case 'CLEAR_MESSAGES':
      return { ...state, messages: [] };

    case 'SET_LOADING':
      return { ...state, isLoading: action.isLoading };

    case 'SET_ERROR':
      return { ...state, error: action.error, isLoading: false };

    default:
      return state;
  }
}

// =============================================================================
// Context
// =============================================================================

// Clarification request from TP
export interface ClarificationRequest {
  question: string;
  options?: string[];
}

// Status for real-time display in TPBar
export type TPStatus =
  | { type: 'idle' }
  | { type: 'thinking' }  // Before first tool call
  | { type: 'tool'; toolName: string }  // Calling a tool
  | { type: 'streaming'; content: string }  // Streaming respond() content
  | { type: 'clarify'; question: string; options?: string[] }  // Waiting for user input
  | { type: 'complete'; message?: string };  // Done, optionally show brief confirmation

interface TPContextValue {
  state: TPState;
  messages: TPMessage[];
  isLoading: boolean;
  error: string | null;
  pendingClarification: ClarificationRequest | null;
  status: TPStatus;  // Real-time status for UI

  // Actions
  sendMessage: (
    content: string,
    context?: { surface?: DeskSurface; projectId?: string }
  ) => Promise<TPToolResult[] | null>;
  clearMessages: () => void;
  clearClarification: () => void;
  respondToClarification: (answer: string) => void;
  onSurfaceChange?: (surface: DeskSurface) => void;
}

const TPContext = createContext<TPContextValue | null>(null);

// =============================================================================
// Provider
// =============================================================================

interface TPProviderProps {
  children: ReactNode;
  onSurfaceChange?: (surface: DeskSurface) => void;
}

export function TPProvider({ children, onSurfaceChange }: TPProviderProps) {
  const [state, dispatch] = useReducer(tpReducer, initialState);
  const [pendingClarification, setPendingClarification] = useState<ClarificationRequest | null>(null);
  const [status, setStatus] = useState<TPStatus>({ type: 'idle' });
  const abortControllerRef = useRef<AbortController | null>(null);

  // ---------------------------------------------------------------------------
  // Send message to TP
  // ---------------------------------------------------------------------------
  const sendMessage = useCallback(
    async (
      content: string,
      context?: { surface?: DeskSurface; projectId?: string }
    ): Promise<TPToolResult[] | null> => {
      // Cancel any ongoing request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      // Add user message
      const userMessage: TPMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content,
        timestamp: new Date(),
      };
      dispatch({ type: 'ADD_MESSAGE', message: userMessage });
      dispatch({ type: 'SET_LOADING', isLoading: true });
      setStatus({ type: 'thinking' });

      try {
        // Build request body
        const body: Record<string, unknown> = {
          content: content,  // Must match ChatRequest.content in api/routes/chat.py
          include_context: true,
        };

        if (context?.projectId) {
          body.project_id = context.projectId;
        }

        // Add surface context for TP to understand what user is looking at
        if (context?.surface) {
          body.surface_context = context.surface;
        }

        // Get auth token for API request
        const supabase = createClient();
        const { data: { session } } = await supabase.auth.getSession();
        const token = session?.access_token;

        // Send to chat endpoint
        const response = await fetch(`${API_BASE_URL}/api/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(body),
          credentials: 'include',
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`Chat request failed: ${response.status}`);
        }

        // Handle streaming response
        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('No response body');
        }

        let assistantContent = '';
        const toolResults: TPToolResult[] = [];
        const decoder = new TextDecoder();
        let buffer = ''; // Buffer for incomplete lines

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          // Append new chunk to buffer
          buffer += decoder.decode(value, { stream: true });

          // Split by newlines, keeping incomplete last line in buffer
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep last (potentially incomplete) line

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const data = line.slice(6);
            if (data === '[DONE]') continue;

            try {
              const event = JSON.parse(data);

              // API sends: {content}, {tool_use}, {tool_result}, {done}, {error}
              if (event.content) {
                assistantContent += event.content;
                // Update streaming status for respond content
                setStatus({ type: 'streaming', content: assistantContent });
              } else if (event.tool_use) {
                // Tool is being called - show in status
                setStatus({ type: 'tool', toolName: event.tool_use.name });
              } else if (event.tool_result) {
                const result: TPToolResult = {
                  toolName: event.tool_result.name,
                  success: event.tool_result.success ?? true,
                  data: event.tool_result,
                  uiAction: event.tool_result.ui_action,
                };
                toolResults.push(result);

                // Handle different ui_action types
                if (result.uiAction) {
                  const action = result.uiAction;

                  if (action.type === 'OPEN_SURFACE' && onSurfaceChange) {
                    // Navigation - open a surface
                    const newSurface = mapToolActionToSurface(action);
                    if (newSurface) {
                      onSurfaceChange(newSurface);
                    }
                    // Show completion status
                    setStatus({ type: 'complete' });
                  } else if (action.type === 'RESPOND') {
                    // Conversation - the message is the response
                    const message = action.data?.message as string;
                    if (message) {
                      assistantContent = message;
                      setStatus({ type: 'streaming', content: message });
                    }
                  } else if (action.type === 'CLARIFY') {
                    // Clarification request - show in status bar
                    const question = action.data?.question as string || '';
                    const options = action.data?.options as string[] | undefined;
                    setPendingClarification({ question, options });
                    setStatus({ type: 'clarify', question, options });
                  }
                }
              } else if (event.error) {
                throw new Error(event.error);
              }
            } catch (parseErr) {
              // Log parse errors but don't crash - might be malformed server data
              console.warn('Failed to parse SSE event:', data, parseErr);
            }
          }
        }

        // Process any remaining buffer content
        if (buffer.startsWith('data: ')) {
          const data = buffer.slice(6);
          if (data && data !== '[DONE]') {
            try {
              const event = JSON.parse(data);
              if (event.content) {
                assistantContent += event.content;
              }
            } catch {
              // Ignore final incomplete chunk
            }
          }
        }

        // Add assistant message
        const assistantMessage: TPMessage = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: assistantContent,
          toolResults: toolResults.length > 0 ? toolResults : undefined,
          timestamp: new Date(),
        };
        dispatch({ type: 'ADD_MESSAGE', message: assistantMessage });
        dispatch({ type: 'SET_LOADING', isLoading: false });

        // Set complete status, then fade to idle (unless clarify is pending)
        if (!pendingClarification) {
          setStatus({ type: 'complete', message: assistantContent?.slice(0, 100) });
          // Reset to idle after a brief delay
          setTimeout(() => {
            setStatus(prev => prev.type === 'complete' ? { type: 'idle' } : prev);
          }, 3000);
        }

        return toolResults.length > 0 ? toolResults : null;
      } catch (err) {
        if ((err as Error).name === 'AbortError') {
          // Request was cancelled
          dispatch({ type: 'SET_LOADING', isLoading: false });
          setStatus({ type: 'idle' });
          return null;
        }

        const errorMessage = err instanceof Error ? err.message : 'Failed to send message';
        dispatch({ type: 'SET_ERROR', error: errorMessage });
        setStatus({ type: 'idle' });

        // Add error message
        const errorAssistantMessage: TPMessage = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `Sorry, I encountered an error: ${errorMessage}`,
          timestamp: new Date(),
        };
        dispatch({ type: 'ADD_MESSAGE', message: errorAssistantMessage });

        return null;
      }
    },
    [onSurfaceChange]
  );

  // ---------------------------------------------------------------------------
  // Clear messages
  // ---------------------------------------------------------------------------
  const clearMessages = useCallback(() => {
    dispatch({ type: 'CLEAR_MESSAGES' });
  }, []);

  // ---------------------------------------------------------------------------
  // Clear clarification
  // ---------------------------------------------------------------------------
  const clearClarification = useCallback(() => {
    setPendingClarification(null);
    setStatus({ type: 'idle' });
  }, []);

  // ---------------------------------------------------------------------------
  // Respond to clarification (send answer back to TP)
  // ---------------------------------------------------------------------------
  const respondToClarification = useCallback((answer: string) => {
    setPendingClarification(null);
    setStatus({ type: 'idle' });
    // Send the answer as a new message
    sendMessage(answer);
  }, [sendMessage]);

  // ---------------------------------------------------------------------------
  // Context value
  // ---------------------------------------------------------------------------
  const value: TPContextValue = {
    state,
    messages: state.messages,
    isLoading: state.isLoading,
    error: state.error,
    pendingClarification,
    status,
    sendMessage,
    clearMessages,
    clearClarification,
    respondToClarification,
    onSurfaceChange,
  };

  return <TPContext.Provider value={value}>{children}</TPContext.Provider>;
}

// =============================================================================
// Hook
// =============================================================================

export function useTP(): TPContextValue {
  const context = useContext(TPContext);
  if (!context) {
    throw new Error('useTP must be used within a TPProvider');
  }
  return context;
}
