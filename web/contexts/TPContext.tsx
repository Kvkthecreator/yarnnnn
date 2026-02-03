'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * TP (Thinking Partner) context - manages conversation state
 */

import React, { createContext, useContext, useReducer, useCallback, useRef, ReactNode } from 'react';
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

interface TPContextValue {
  state: TPState;
  messages: TPMessage[];
  isLoading: boolean;
  error: string | null;

  // Actions
  sendMessage: (
    content: string,
    context?: { surface?: DeskSurface; projectId?: string }
  ) => Promise<TPToolResult[] | null>;
  clearMessages: () => void;
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

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const data = line.slice(6);
            if (data === '[DONE]') continue;

            try {
              const event = JSON.parse(data);

              // API sends: {content}, {tool_use}, {tool_result}, {done}, {error}
              if (event.content) {
                assistantContent += event.content;
              } else if (event.tool_result) {
                const result: TPToolResult = {
                  toolName: event.tool_result.name,
                  success: event.tool_result.success ?? true,
                  data: event.tool_result,
                  uiAction: event.tool_result.ui_action,
                };
                toolResults.push(result);

                // If tool has ui_action, trigger surface change
                if (result.uiAction && onSurfaceChange) {
                  const newSurface = mapToolActionToSurface(result.uiAction);
                  if (newSurface) {
                    onSurfaceChange(newSurface);
                  }
                }
              } else if (event.error) {
                throw new Error(event.error);
              }
              // event.done and event.tool_use are informational, no action needed
            } catch (parseErr) {
              // Ignore parse errors for partial chunks, but rethrow real errors
              if (parseErr instanceof Error && parseErr.message !== 'Unexpected end of JSON input') {
                throw parseErr;
              }
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

        return toolResults.length > 0 ? toolResults : null;
      } catch (err) {
        if ((err as Error).name === 'AbortError') {
          // Request was cancelled
          dispatch({ type: 'SET_LOADING', isLoading: false });
          return null;
        }

        const errorMessage = err instanceof Error ? err.message : 'Failed to send message';
        dispatch({ type: 'SET_ERROR', error: errorMessage });

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
  // Context value
  // ---------------------------------------------------------------------------
  const value: TPContextValue = {
    state,
    messages: state.messages,
    isLoading: state.isLoading,
    error: state.error,
    sendMessage,
    clearMessages,
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
