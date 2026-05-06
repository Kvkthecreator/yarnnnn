'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * ADR-025: Claude Code Agentic Alignment - Todo tracking
 * YARNNN context - manages conversation state
 */

import React, { createContext, useContext, useReducer, useCallback, useRef, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { TPState, TPAction, TPMessage, TPToolResult, TPImageAttachment, TPNotification, mapToolActionToSurface, DeskSurface, Todo, MessageBlock, SystemCardType } from '@/types/desk';
import { SetupConfirmData } from '@/components/modals/SetupConfirmModal';
import { api } from '@/lib/api/client';
import { postChatWithFallback } from '@/lib/api/chatTransport';
import { getToolDisplayMessage } from '@/lib/utils';

// =============================================================================
// Initial State
// =============================================================================

const initialState: TPState = {
  messages: [],
  isLoading: false,
  error: null,
  // ADR-025: Todo tracking state
  todos: [],
  activeCommand: null,
  workPanelExpanded: false,
  // ADR-155: Notification queue for tool side effects
  pendingNotifications: [],
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
    // ADR-124: Also propagate author attribution fields
    case 'UPDATE_STREAMING_MESSAGE': {
      const messages = [...state.messages];
      const lastIdx = messages.length - 1;
      if (lastIdx >= 0 && messages[lastIdx].role === 'assistant') {
        messages[lastIdx] = {
          ...messages[lastIdx],
          blocks: action.blocks,
          content: action.content ?? messages[lastIdx].content,
          ...(action.authorAgentId && { authorAgentId: action.authorAgentId }),
          ...(action.authorAgentSlug && { authorAgentSlug: action.authorAgentSlug }),
          ...(action.authorRole && { authorRole: action.authorRole }),
          ...(action.authorName && { authorName: action.authorName }),
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

    case 'SET_ACTIVE_COMMAND':
      return { ...state, activeCommand: action.command };

    case 'SET_WORK_PANEL_EXPANDED':
      return { ...state, workPanelExpanded: action.expanded };

    case 'CLEAR_WORK_STATE':
      return { ...state, todos: [], activeCommand: null, workPanelExpanded: false };

    // ADR-155: Notification channel
    case 'ADD_NOTIFICATION':
      return { ...state, pendingNotifications: [...state.pendingNotifications, action.notification] };
    case 'FLUSH_NOTIFICATIONS':
      return { ...state, pendingNotifications: [] };

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
  activeCommand: string | null;
  workPanelExpanded: boolean;
  setWorkPanelExpanded: (expanded: boolean) => void;

  // ADR-155: Notification channel
  pendingNotifications: TPNotification[];
  flushNotifications: () => void;

  // Actions
  sendMessage: (
    content: string,
    context?: { surface?: DeskSurface; images?: TPImageAttachment[]; targetAgentId?: string }
  ) => Promise<TPToolResult[] | null>;
  clearMessages: () => void;
  clearClarification: () => void;
  respondToClarification: (answer: string) => void;
  closeSetupConfirmModal: () => void;
  onSurfaceChange?: (surface: DeskSurface, handoffMessage?: string) => void;
  /** ADR-087 Phase 3 / ADR-138: Load history scoped to agent, task, or global */
  loadScopedHistory: (agentId?: string, taskSlug?: string) => Promise<void>;
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
  const router = useRouter();
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
  // Status timeout safety - reset to idle if stuck in loading state.
  // Tool executions can be legitimately long (agent generation, web search),
  // so use a longer timeout than thinking/streaming.
  // ---------------------------------------------------------------------------
  useEffect(() => {
    // Clear any existing timeout
    if (statusTimeoutRef.current) {
      clearTimeout(statusTimeoutRef.current);
      statusTimeoutRef.current = null;
    }

    // Don't timeout clarify since that's waiting for user input.
    let timeoutMs: number | null = null;
    if (status.type === 'thinking' || status.type === 'streaming') {
      timeoutMs = 30000;
    } else if (status.type === 'tool') {
      timeoutMs = 120000;
    }

    if (timeoutMs !== null) {
      statusTimeoutRef.current = setTimeout(() => {
        console.warn('[TPContext] Status timeout - resetting stuck state:', status.type);
        setStatus({ type: 'idle' });
        dispatch({ type: 'SET_LOADING', isLoading: false });
      }, timeoutMs);
    }

    return () => {
      if (statusTimeoutRef.current) {
        clearTimeout(statusTimeoutRef.current);
      }
    };
  }, [status]);

  // ---------------------------------------------------------------------------
  // Load chat history — Unified session model (one conversation per workspace)
  // ---------------------------------------------------------------------------
  // No scope switching. One global session. Surface context sent per message.
  // Messages persist across page navigations — no clearing.

  const loadScopedHistory = useCallback(async (_agentId?: string, _taskSlug?: string) => {
    // Unified session: always load global history. Agent/task params ignored —
    // surface context is sent per message, not per session.
    if (historyLoadedRef.current) return;
    historyLoadedRef.current = true;

    try {
      const result = await api.chat.globalHistory(1);

      if (result.sessions && result.sessions.length > 0) {
        const session = result.sessions[0];
        if (session.messages && session.messages.length > 0) {
          const messages: TPMessage[] = session.messages.map((m) => {
            // ADR-042: Reconstruct blocks AND tool results from metadata.tool_history
            let toolResults: TPToolResult[] | undefined;
            let blocks: MessageBlock[] | undefined;

            if (m.metadata?.tool_history) {
              const toolItems = m.metadata.tool_history.filter(
                (item) => item.type === 'tool_call' && item.name
              );

              toolResults = toolItems.map((item) => ({
                toolName: item.name!,
                success: true,
                data: {
                  message: item.result_summary || 'Action completed',
                },
              }));

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

            const messageBlocks: MessageBlock[] = [];
            // ADR-179: System event cards — persisted session_messages rows with metadata.system_card.
            // Render as SystemCard component instead of prose; TP reads content field as history.
            // ADR-219 Commit 5: the narrative_digest card needs the message
            // body (bullet list of housekeeping summaries) for expand-to-list,
            // so we pass content alongside metadata in the card data.
            if (m.metadata?.system_card) {
              messageBlocks.push({
                type: 'system_card',
                card_type: m.metadata.system_card as SystemCardType,
                data: { ...(m.metadata as Record<string, unknown>), _body: m.content },
              });
            } else if (m.content) {
              messageBlocks.push({ type: 'text', content: m.content });
            }
            if (blocks && blocks.length > 0) {
              messageBlocks.push(...blocks);
            }

            // ADR-212: reviewer verdict metadata (role === 'reviewer')
            const reviewerMeta =
              m.role === 'reviewer' && m.metadata
                ? {
                    proposalId: m.metadata.proposal_id,
                    verdict: m.metadata.verdict,
                    occupant: m.metadata.occupant,
                    actionType: m.metadata.action_type,
                    taskSlug: m.metadata.task_slug,
                  }
                : undefined;

            // ADR-219 Commit 2: narrative envelope — present on every
            // post-Commit-2 row; older rows surface with only the
            // fields that were set when they were written.
            const narrative = m.metadata
              ? {
                  ...(m.metadata.summary && { summary: m.metadata.summary }),
                  ...(m.metadata.pulse && { pulse: m.metadata.pulse }),
                  ...(m.metadata.weight && { weight: m.metadata.weight }),
                  ...(m.metadata.task_slug && { taskSlug: m.metadata.task_slug }),
                  ...(m.metadata.invocation_id && { invocationId: m.metadata.invocation_id }),
                }
              : undefined;
            const narrativeHasAny =
              narrative && Object.keys(narrative).length > 0;

            return {
              id: m.id,
              role: m.role as TPMessage['role'],
              content: m.content,
              timestamp: new Date(m.created_at),
              toolResults: toolResults?.length ? toolResults : undefined,
              blocks: messageBlocks.length > 0 ? messageBlocks : undefined,
              // ADR-124: Reconstruct author attribution from stored metadata
              ...(m.metadata?.author_agent_id && { authorAgentId: m.metadata.author_agent_id }),
              ...(m.metadata?.author_agent_slug && { authorAgentSlug: m.metadata.author_agent_slug }),
              ...(m.metadata?.author_role && { authorRole: m.metadata.author_role }),
              ...(reviewerMeta && { reviewer: reviewerMeta }),
              ...(narrativeHasAny && { narrative }),
            };
          });
          dispatch({ type: 'SET_MESSAGES', messages });
        } else {
          // Session exists but no messages — clear
          dispatch({ type: 'CLEAR_MESSAGES' });
        }
      } else {
        // No session for this scope — clear messages
        dispatch({ type: 'CLEAR_MESSAGES' });
      }
    } catch (err) {
      console.warn('[TPContext] Failed to load chat history:', err);
    }
  }, []);

  // Load global history on mount — unified session, loaded once
  useEffect(() => {
    loadScopedHistory();
  }, [loadScopedHistory]);

  // ---------------------------------------------------------------------------
  // Send message to TP
  // ---------------------------------------------------------------------------
  const sendMessage = useCallback(
    async (
      content: string,
      context?: { surface?: DeskSurface; images?: TPImageAttachment[]; targetAgentId?: string }
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

      // Add user message (with images for local display).
      // ADR-219 envelope: operator messages are addressed-pulsed material
      // by default policy (mirrors api/services/narrative.py). Stamping
      // here keeps optimistic-UI rows consistent with what the backend
      // persists, so weight-driven rendering doesn't flicker on history
      // reload.
      const userMessage: TPMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content,
        images: context?.images,
        timestamp: new Date(),
        narrative: { pulse: 'addressed', weight: 'material', summary: content.split('\n', 1)[0].slice(0, 160) },
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

        // ADR-124: Add target agent ID for meeting room @-mentions
        if (context?.targetAgentId) {
          body.target_agent_id = context.targetAgentId;
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
        const response = await postChatWithFallback({
          body: JSON.stringify(body),
          token,
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          // Parse error detail from backend (e.g. daily token budget exceeded)
          let errorDetail = `Chat request failed: ${response.status}`;
          try {
            const errorData = await response.json();
            if (errorData?.detail?.message) {
              errorDetail = errorData.detail.message;
            } else if (typeof errorData?.detail === 'string') {
              errorDetail = errorData.detail;
            }
          } catch {
            // Response wasn't JSON, use generic message
          }
          throw new Error(errorDetail);
        }

        // Handle streaming response
        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('No response body');
        }

        // ADR-042: Add empty assistant message immediately for streaming blocks.
        // ADR-219: stamp envelope so weight-driven rendering applies
        // immediately; backend will record final weight (material when a
        // tool call fired, else routine) on the persisted row, but for
        // streaming-time display we treat the in-flight reply as material
        // so it renders as a full card during typing.
        const assistantMessageId = crypto.randomUUID();
        const initialAssistantMessage: TPMessage = {
          id: assistantMessageId,
          role: 'assistant',
          content: '',
          blocks: [],
          timestamp: new Date(),
          narrative: { pulse: 'addressed', weight: 'material' },
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
        // ADR-124: Author attribution from stream_start event
        let streamAuthor: { agentId?: string; agentSlug?: string; role?: string; name?: string } | null = null;

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

              // API sends: {stream_start}, {content}, {tool_use}, {tool_result}, {done}, {error}
              if (event.stream_start) {
                // ADR-124: Author attribution from backend — update the pending assistant message
                streamAuthor = {
                  agentId: event.author_agent_id,
                  agentSlug: event.author_agent_slug,
                  role: event.author_role,
                  name: event.author_name,
                };
                // Update the already-added assistant message with author info
                dispatch({
                  type: 'UPDATE_STREAMING_MESSAGE',
                  blocks: [...blocks],
                  content: assistantContent,
                  authorAgentId: event.author_agent_id,
                  authorAgentSlug: event.author_agent_slug,
                  authorRole: event.author_role,
                  authorName: event.author_name,
                });
              } else if (event.content) {
                assistantContent += event.content;
                // Update or add text block
                // Key fix: only update the LAST text block if it's the most recent block
                // If a tool_call block is more recent, create a NEW text block
                const lastBlock = blocks[blocks.length - 1];
                if (lastBlock?.type === 'text') {
                  // Continue appending to existing text block
                  lastBlock.content += event.content;
                } else {
                  // After a tool_call, start a fresh text block
                  blocks.push({ type: 'text', content: event.content });
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
                      // Add text block for response - always create new block after tool
                      // This ensures tool results don't get mixed with subsequent text
                      blocks.push({ type: 'text', content: message });
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
                    setStatus({ type: 'complete', message: 'Agent created' });
                  } else if (action.type === 'NAVIGATE') {
                    // ADR-144: Navigation links shown inline on tool call result.
                    // No auto-redirect — user clicks the "View →" link when ready.
                    // Auto-redirect was removed because bulk tool calls (e.g., creating
                    // 5 tasks in one turn) would redirect on the first result, losing
                    // the remaining tool calls and TP's response text.
                  } else if (action.type === 'UPDATE_TODOS') {
                    const todos = (action.data?.todos as Todo[]) || [];
                    dispatch({ type: 'SET_TODOS', todos });
                    if (todos.length > 0) {
                      dispatch({ type: 'SET_WORK_PANEL_EXPANDED', expanded: true });
                    }
                  }
                }

                // ADR-155: Notification-worthy tool results → inline card + FAB badge
                const toolName = event.tool_result.name;
                const resultData = toolResult;
                let notifTitle = '';
                let notifDesc = '';

                // ADR-235 D1.a: InferWorkspace produces identity + brand + entities
                // + work_intent in one Sonnet call; result carries `scaffolded` at
                // top level (entities-by-domain) plus `entity_count`.
                if (toolName === 'InferWorkspace' && resultData.scaffolded) {
                  const scaffolded = resultData.scaffolded as Record<string, unknown>;
                  const domains = Object.keys(scaffolded).filter(
                    (k) => Array.isArray(scaffolded[k])
                  );
                  const total = domains.reduce(
                    (sum: number, k: string) => sum + ((scaffolded[k] as unknown[])?.length ?? 0),
                    0
                  );
                  notifTitle = 'Workspace scaffolded';
                  notifDesc = `${total} entities across ${domains.length} domains`;
                } else if (toolName === 'ManageRecurrence' && resultData.success) {
                  // ADR-235 D1.c: lifecycle actions (create/update/pause/resume/archive).
                  const mrAction = resultData.action as string;
                  if (mrAction === 'create') {
                    notifTitle = 'Recurrence created';
                    notifDesc = (resultData.message as string) || (resultData.slug as string) || '';
                  } else if (mrAction === 'archive') {
                    notifTitle = 'Recurrence archived';
                    notifDesc = (resultData.message as string) || '';
                  }
                }

                if (notifTitle) {
                  // Inline card in chat stream (persists in history)
                  blocks.push({ type: 'notification', title: notifTitle, description: notifDesc, toolName });
                  updateStreamingMessage();
                  // FAB badge (for when chat is closed)
                  dispatch({
                    type: 'ADD_NOTIFICATION',
                    notification: { id: crypto.randomUUID(), toolName, title: notifTitle, description: notifDesc, timestamp: new Date() },
                  });
                }
              } else if (event.usage) {
                // Track token usage from API
                setTokenUsage({
                  inputTokens: event.usage.input_tokens,
                  outputTokens: event.usage.output_tokens,
                  totalTokens: event.usage.total_tokens,
                });
              } else if (event.balance_exhausted) {
                throw new Error('__balance_exhausted__');
              } else if (event.error) {
                throw new Error(event.error);
              }
            } catch (parseErr) {
              if (parseErr instanceof Error && parseErr.message.startsWith('__')) {
                throw parseErr;
              }
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
        // ADR-124: Preserve author attribution in final message update
        dispatch({
          type: 'UPDATE_STREAMING_MESSAGE',
          blocks: [...blocks],
          content: finalContent,
          ...(streamAuthor?.agentId && { authorAgentId: streamAuthor.agentId }),
          ...(streamAuthor?.agentSlug && { authorAgentSlug: streamAuthor.agentSlug }),
          ...(streamAuthor?.role && { authorRole: streamAuthor.role }),
          ...(streamAuthor?.name && { authorName: streamAuthor.name }),
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

        const rawMessage = err instanceof Error ? err.message : 'Failed to send message';
        const isBalanceExhausted = rawMessage === '__balance_exhausted__';
        const errorMessage = isBalanceExhausted ? 'Balance exhausted' : rawMessage;
        dispatch({ type: 'SET_ERROR', error: errorMessage });
        setStatus({ type: 'idle' });

        const errorContent = isBalanceExhausted
          ? 'Your account balance is exhausted. [Top up your balance](https://yarnnn.com/settings?tab=billing) to continue.'
          : `Sorry, I encountered an error: ${errorMessage}`;

        const errorAssistantMessage: TPMessage = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: errorContent,
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

  // ADR-155: Flush notifications when chat is opened
  const flushNotifications = useCallback(() => {
    dispatch({ type: 'FLUSH_NOTIFICATIONS' });
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
    activeCommand: state.activeCommand,
    workPanelExpanded: state.workPanelExpanded,
    setWorkPanelExpanded,
    // ADR-155: Notification channel
    pendingNotifications: state.pendingNotifications,
    flushNotifications,
    // Actions
    sendMessage,
    clearMessages,
    clearClarification,
    respondToClarification,
    closeSetupConfirmModal,
    onSurfaceChange,
    loadScopedHistory,
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
