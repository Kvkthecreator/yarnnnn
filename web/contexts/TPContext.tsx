'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * ADR-025: Claude Code Agentic Alignment - Todo tracking
 * TP (Thinking Partner) context - manages conversation state
 */

import React, { createContext, useContext, useReducer, useCallback, useRef, useState, useEffect, ReactNode } from 'react';
import { createClient } from '@/lib/supabase/client';
import { TPState, TPAction, TPMessage, TPToolResult, TPImageAttachment, mapToolActionToSurface, DeskSurface, Todo, MessageBlock } from '@/types/desk';
import { SetupConfirmData } from '@/components/modals/SetupConfirmModal';
import { api } from '@/lib/api/client';
import { getToolDisplayMessage } from '@/lib/utils';

// API base URL - must match the Python backend
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// =============================================================================
// Initial State
// =============================================================================

const initialState: TPState = {
  messages: [],
  isLoading: false,
  error: null,
  // ADR-025: Todo tracking state
  todos: [],
  activeSkill: null,
  workPanelExpanded: false,
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

    // ADR-042: Update streaming message blocks in place
    case 'UPDATE_STREAMING_MESSAGE': {
      const messages = [...state.messages];
      const lastIdx = messages.length - 1;
      if (lastIdx >= 0 && messages[lastIdx].role === 'assistant') {
        messages[lastIdx] = {
          ...messages[lastIdx],
          blocks: action.blocks,
          content: action.content ?? messages[lastIdx].content,
        };
      }
      return { ...state, messages };
    }

    case 'SET_LOADING':
      return { ...state, isLoading: action.isLoading };

    case 'SET_ERROR':
      return { ...state, error: action.error, isLoading: false };

    // ADR-025: Todo tracking actions
    case 'SET_TODOS':
      return { ...state, todos: action.todos };

    case 'SET_ACTIVE_SKILL':
      return { ...state, activeSkill: action.skill };

    case 'SET_WORK_PANEL_EXPANDED':
      return { ...state, workPanelExpanded: action.expanded };

    case 'CLEAR_WORK_STATE':
      return { ...state, todos: [], activeSkill: null, workPanelExpanded: false };

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

// Token usage tracking
export interface TokenUsage {
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
}

// Status for real-time display in TPBar
// ADR-039: toolDisplayMessage provides Claude Code-style descriptive status
export type TPStatus =
  | { type: 'idle' }
  | { type: 'thinking' }  // Before first tool call
  | { type: 'tool'; toolName: string; toolDisplayMessage: string }  // Calling a tool with display message
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
  setupConfirmModal: { open: boolean; data: SetupConfirmData | null };  // Setup confirmation modal state
  tokenUsage: TokenUsage | null;  // Current turn's token usage

  // ADR-025: Todo tracking state
  todos: Todo[];
  activeSkill: string | null;
  workPanelExpanded: boolean;
  setWorkPanelExpanded: (expanded: boolean) => void;

  // Actions
  sendMessage: (
    content: string,
    context?: { surface?: DeskSurface; images?: TPImageAttachment[] }
  ) => Promise<TPToolResult[] | null>;
  clearMessages: () => void;
  clearClarification: () => void;
  respondToClarification: (answer: string) => void;
  closeSetupConfirmModal: () => void;
  onSurfaceChange?: (surface: DeskSurface, handoffMessage?: string) => void;
}

const TPContext = createContext<TPContextValue | null>(null);

// =============================================================================
// Provider
// =============================================================================

interface TPProviderProps {
  children: ReactNode;
  /** Called when TP navigates to a surface. Optional handoffMessage for context continuity. */
  onSurfaceChange?: (surface: DeskSurface, handoffMessage?: string) => void;
}

export function TPProvider({ children, onSurfaceChange }: TPProviderProps) {
  const [state, dispatch] = useReducer(tpReducer, initialState);
  const [pendingClarification, setPendingClarification] = useState<ClarificationRequest | null>(null);
  const [status, setStatus] = useState<TPStatus>({ type: 'idle' });
  const [setupConfirmModal, setSetupConfirmModal] = useState<{ open: boolean; data: SetupConfirmData | null }>({
    open: false,
    data: null,
  });
  const [tokenUsage, setTokenUsage] = useState<TokenUsage | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  // Track if we've loaded history
  const historyLoadedRef = useRef(false);
  // Timeout ref for stuck status safety
  const statusTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // ---------------------------------------------------------------------------
  // Status timeout safety - reset to idle if stuck in loading state for >30s
  // ---------------------------------------------------------------------------
  useEffect(() => {
    // Clear any existing timeout
    if (statusTimeoutRef.current) {
      clearTimeout(statusTimeoutRef.current);
      statusTimeoutRef.current = null;
    }

    // Set timeout for loading states (thinking, tool, streaming)
    // Don't timeout clarify since that's waiting for user input
    const loadingStates = ['thinking', 'tool', 'streaming'];
    if (loadingStates.includes(status.type)) {
      statusTimeoutRef.current = setTimeout(() => {
        console.warn('[TPContext] Status timeout - resetting stuck state:', status.type);
        setStatus({ type: 'idle' });
        dispatch({ type: 'SET_LOADING', isLoading: false });
      }, 30000); // 30 second safety timeout
    }

    return () => {
      if (statusTimeoutRef.current) {
        clearTimeout(statusTimeoutRef.current);
      }
    };
  }, [status.type]);

  // ---------------------------------------------------------------------------
  // Load chat history on mount
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (historyLoadedRef.current) return;
    historyLoadedRef.current = true;

    const loadHistory = async () => {
      try {
        const result = await api.chat.globalHistory(1);

        if (result.sessions && result.sessions.length > 0) {
          const session = result.sessions[0];
          if (session.messages && session.messages.length > 0) {
            const messages: TPMessage[] = session.messages.map((m) => {
              // ADR-042: Reconstruct blocks AND tool results from metadata.tool_history
              // This ensures historical messages render with Claude Code-style inline tool calls
              let toolResults: TPToolResult[] | undefined;
              let blocks: MessageBlock[] | undefined;

              if (m.metadata?.tool_history) {
                const toolItems = m.metadata.tool_history.filter(
                  (item) => item.type === 'tool_call' && item.name
                );

                // Reconstruct legacy toolResults for backwards compatibility
                toolResults = toolItems.map((item) => ({
                  toolName: item.name!,
                  success: true, // Assume success for historical
                  data: {
                    message: item.result_summary || 'Action completed',
                  },
                }));

                // ADR-042: Reconstruct blocks for Claude Code-style rendering
                // Note: Historical data only has input_summary (string), not full input object
                blocks = toolItems.map((item, idx) => ({
                  type: 'tool_call' as const,
                  id: `hist_${m.id}_${idx}`,
                  tool: item.name!,
                  input: item.input_summary ? { summary: item.input_summary } : {},
                  status: 'success' as const,
                  result: {
                    toolName: item.name!,
                    success: true,
                    data: { message: item.result_summary || 'Action completed' },
                  },
                }));
              }

              // Build blocks array: text content + tool calls
              const messageBlocks: MessageBlock[] = [];
              if (m.content) {
                messageBlocks.push({ type: 'text', content: m.content });
              }
              if (blocks && blocks.length > 0) {
                messageBlocks.push(...blocks);
              }

              return {
                id: m.id,
                role: m.role as 'user' | 'assistant',
                content: m.content,
                timestamp: new Date(m.created_at),
                toolResults: toolResults?.length ? toolResults : undefined,
                blocks: messageBlocks.length > 0 ? messageBlocks : undefined,
              };
            });
            dispatch({ type: 'SET_MESSAGES', messages });
          }
        }
      } catch (err) {
        console.warn('[TPContext] Failed to load chat history:', err);
        // Non-blocking - user can still chat
      }
    };

    loadHistory();
  }, []);

  // ---------------------------------------------------------------------------
  // Send message to TP
  // ---------------------------------------------------------------------------
  const sendMessage = useCallback(
    async (
      content: string,
      context?: { surface?: DeskSurface; images?: TPImageAttachment[] }
    ): Promise<TPToolResult[] | null> => {
      // Cancel any ongoing request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      // Clear previous workflow state - todos will be recreated if TP starts a new workflow
      // This prevents stale todos from lingering when user switches topics
      dispatch({ type: 'CLEAR_WORK_STATE' });

      // Reset token usage for new turn
      setTokenUsage(null);

      // Add user message (with images for local display)
      const userMessage: TPMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content,
        images: context?.images,
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

        // Add surface context for TP to understand what user is looking at
        if (context?.surface) {
          body.surface_context = context.surface;
        }

        // Add images as base64 (Claude API format)
        if (context?.images && context.images.length > 0) {
          body.images = context.images.map((img) => ({
            type: 'base64',
            media_type: img.mediaType,
            data: img.data,
          }));
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

        // ADR-042: Add empty assistant message immediately for streaming blocks
        const assistantMessageId = crypto.randomUUID();
        const initialAssistantMessage: TPMessage = {
          id: assistantMessageId,
          role: 'assistant',
          content: '',
          blocks: [],
          timestamp: new Date(),
        };
        dispatch({ type: 'ADD_MESSAGE', message: initialAssistantMessage });

        // Track state during streaming
        let assistantContent = '';
        const toolResults: TPToolResult[] = [];
        const blocks: MessageBlock[] = [];
        const decoder = new TextDecoder();
        let buffer = '';
        let pendingSurface: DeskSurface | null = null;
        let pendingHandoff: string | null = null;
        let clarifyWasCalled = false;
        // Track pending tool calls by ID for updating status
        const pendingToolCalls: Map<string, number> = new Map(); // tool_use_id -> block index

        // Helper to update streaming message
        const updateStreamingMessage = () => {
          dispatch({ type: 'UPDATE_STREAMING_MESSAGE', blocks: [...blocks], content: assistantContent });
        };

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const data = line.slice(6);
            if (data === '[DONE]') continue;

            try {
              const event = JSON.parse(data);

              // API sends: {content}, {tool_use}, {tool_result}, {done}, {error}
              if (event.content) {
                assistantContent += event.content;
                // Update or add text block
                const lastBlock = blocks[blocks.length - 1];
                if (lastBlock?.type === 'text') {
                  lastBlock.content = assistantContent;
                } else {
                  blocks.push({ type: 'text', content: assistantContent });
                }
                // Batch updates to reduce re-renders
                if (assistantContent.length % 50 < event.content.length || event.content.includes('\n')) {
                  setStatus({ type: 'streaming', content: assistantContent });
                  updateStreamingMessage();
                }
              } else if (event.tool_use) {
                // ADR-042: Add pending tool call block immediately
                const toolId = event.tool_use.id || `tool_${Date.now()}`;
                const toolBlock: MessageBlock = {
                  type: 'tool_call',
                  id: toolId,
                  tool: event.tool_use.name,
                  input: event.tool_use.input,
                  status: 'pending',
                };
                blocks.push(toolBlock);
                pendingToolCalls.set(toolId, blocks.length - 1);
                // ADR-039: Use descriptive tool display message (Claude Code style)
                const toolDisplayMessage = getToolDisplayMessage(
                  event.tool_use.name,
                  event.tool_use.input as Record<string, unknown>
                );
                setStatus({ type: 'tool', toolName: event.tool_use.name, toolDisplayMessage });
                updateStreamingMessage();
              } else if (event.tool_result) {
                const toolResult = event.tool_result.result || event.tool_result;
                const result: TPToolResult = {
                  toolName: event.tool_result.name,
                  success: toolResult.success ?? true,
                  data: toolResult,
                  uiAction: toolResult.ui_action,
                };
                toolResults.push(result);

                // ADR-042: Update the pending tool call block with result
                const toolId = event.tool_result.tool_use_id;
                const blockIdx = pendingToolCalls.get(toolId);
                if (blockIdx !== undefined && blocks[blockIdx]?.type === 'tool_call') {
                  const toolBlock = blocks[blockIdx] as Extract<MessageBlock, { type: 'tool_call' }>;
                  toolBlock.status = result.success ? 'success' : 'failed';
                  toolBlock.result = result;
                }
                updateStreamingMessage();

                // Handle UI actions
                if (result.uiAction) {
                  const action = result.uiAction;

                  if (action.type === 'OPEN_SURFACE' && onSurfaceChange) {
                    const newSurface = mapToolActionToSurface(action);
                    if (newSurface) pendingSurface = newSurface;
                    const navMessage = result.data?.message as string;
                    if (navMessage && !assistantContent) assistantContent = navMessage;
                    setStatus({ type: 'complete', message: navMessage });
                  } else if (action.type === 'RESPOND') {
                    const message = action.data?.message as string;
                    if (message) {
                      assistantContent = message;
                      if (pendingSurface) pendingHandoff = message;
                      // Add text block for response
                      const lastBlock = blocks[blocks.length - 1];
                      if (lastBlock?.type === 'text') {
                        lastBlock.content = message;
                      } else {
                        blocks.push({ type: 'text', content: message });
                      }
                      setStatus({ type: 'streaming', content: message });
                      updateStreamingMessage();
                    }
                  } else if (action.type === 'CLARIFY') {
                    const question = action.data?.question as string || '';
                    const options = action.data?.options as string[] | undefined;
                    clarifyWasCalled = true;
                    blocks.push({ type: 'clarify', question, options });
                    setPendingClarification({ question, options });
                    setStatus({ type: 'clarify', question, options });
                    updateStreamingMessage();
                  } else if (action.type === 'SHOW_SETUP_CONFIRM') {
                    const setupData = action.data as unknown as SetupConfirmData;
                    setSetupConfirmModal({ open: true, data: setupData });
                    setStatus({ type: 'complete', message: 'Deliverable created' });
                  } else if (action.type === 'UPDATE_TODOS') {
                    const todos = (action.data?.todos as Todo[]) || [];
                    dispatch({ type: 'SET_TODOS', todos });
                    if (todos.length > 0) {
                      dispatch({ type: 'SET_WORK_PANEL_EXPANDED', expanded: true });
                    }
                  }
                }
              } else if (event.usage) {
                // Track token usage from API
                setTokenUsage({
                  inputTokens: event.usage.input_tokens,
                  outputTokens: event.usage.output_tokens,
                  totalTokens: event.usage.total_tokens,
                });
              } else if (event.error) {
                throw new Error(event.error);
              }
            } catch (parseErr) {
              console.warn('Failed to parse SSE event:', data, parseErr);
            }
          }
        }

        // Process remaining buffer
        if (buffer.startsWith('data: ')) {
          const data = buffer.slice(6);
          if (data && data !== '[DONE]') {
            try {
              const event = JSON.parse(data);
              if (event.content) {
                assistantContent += event.content;
                const lastBlock = blocks[blocks.length - 1];
                if (lastBlock?.type === 'text') {
                  lastBlock.content = assistantContent;
                }
              }
            } catch {
              // Ignore
            }
          }
        }

        // Final update
        updateStreamingMessage();

        // Execute pending surface navigation
        if (pendingSurface && onSurfaceChange) {
          onSurfaceChange(pendingSurface, pendingHandoff || undefined);
        }

        // Finalize content if empty
        let finalContent = assistantContent;
        if (!finalContent && toolResults.length > 0) {
          const firstMessage = toolResults.find((r) => r.data?.message)?.data?.message as string;
          if (firstMessage) finalContent = firstMessage;
        }

        // Final update with toolResults for legacy compatibility
        dispatch({
          type: 'UPDATE_STREAMING_MESSAGE',
          blocks: [...blocks],
          content: finalContent,
        });
        dispatch({ type: 'SET_LOADING', isLoading: false });

        // Set complete status, then fade to idle (unless clarify is pending)
        // Use clarifyWasCalled (local) instead of pendingClarification (stale closure)
        if (!clarifyWasCalled) {
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
  // Close setup confirmation modal
  // ---------------------------------------------------------------------------
  const closeSetupConfirmModal = useCallback(() => {
    setSetupConfirmModal({ open: false, data: null });
  }, []);

  // ---------------------------------------------------------------------------
  // ADR-025: Work panel expansion control
  // ---------------------------------------------------------------------------
  const setWorkPanelExpanded = useCallback((expanded: boolean) => {
    dispatch({ type: 'SET_WORK_PANEL_EXPANDED', expanded });
  }, []);

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
    setupConfirmModal,
    tokenUsage,
    // ADR-025: Todo tracking state
    todos: state.todos,
    activeSkill: state.activeSkill,
    workPanelExpanded: state.workPanelExpanded,
    setWorkPanelExpanded,
    // Actions
    sendMessage,
    clearMessages,
    clearClarification,
    respondToClarification,
    closeSetupConfirmModal,
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
