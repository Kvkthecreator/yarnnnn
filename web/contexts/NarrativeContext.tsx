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
import { useSessionMessagesRealtime } from '@/lib/realtime/use-session-messages-realtime';

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

    // Update streaming message in place. Targets by ID (action.messageId) when
    // provided, falls back to last-assistant-role scan for backward compat.
    // ADR-124: Also propagate author attribution fields
    case 'UPDATE_STREAMING_MESSAGE': {
      const messages = [...state.messages];
      const targetIdx = action.messageId
        ? messages.findIndex(m => m.id === action.messageId)
        : messages.map(m => m.role).lastIndexOf('assistant');
      if (targetIdx >= 0) {
        messages[targetIdx] = {
          ...messages[targetIdx],
          blocks: action.blocks,
          content: action.content ?? messages[targetIdx].content,
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

interface NarrativeContextValue {
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

  // Commit H (2026-05-11) — interruption surface (Mode 1):
  /** True iff a Reviewer Loop is in flight: either the operator's own
   *  sendMessage is mid-stream OR a recent autonomous wake (cron-fired)
   *  has emitted realtime activity in the last ~30s. */
  loopActive: boolean;
  /** Stop the in-flight Loop. Aborts the operator's local stream (if
   *  any) AND POSTs /api/feed/cancel so server-side cooperative
   *  cancellation kicks in for autonomous wakes. Best-effort; safe to
   *  call when no Loop is running. */
  stopActiveLoop: () => Promise<void>;

  // Actions
  sendMessage: (
    content: string,
    context?: {
      surface?: DeskSurface;
      images?: TPImageAttachment[];
      targetAgentId?: string;
      fileAttachments?: Array<{ file_id: string; filename: string; mime_type: string }>;
    }
  ) => Promise<TPToolResult[] | null>;
  clearMessages: () => void;
  clearClarification: () => void;
  respondToClarification: (answer: string) => void;
  closeSetupConfirmModal: () => void;
  onSurfaceChange?: (surface: DeskSurface, handoffMessage?: string) => void;
  /** ADR-087 Phase 3 / ADR-138: Load history scoped to agent, task, or global */
  loadScopedHistory: (agentId?: string, taskSlug?: string) => Promise<void>;
}

const NarrativeContext = createContext<NarrativeContextValue | null>(null);

// =============================================================================
// Provider
// =============================================================================

interface NarrativeProviderProps {
  children: ReactNode;
  /** Called when TP navigates to a surface. Optional handoffMessage for context continuity. */
  onSurfaceChange?: (surface: DeskSurface, handoffMessage?: string) => void;
}

export function NarrativeProvider({ children, onSurfaceChange }: NarrativeProviderProps) {
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
  // Session ID for the unified workspace conversation. Captured from
  // fetchAndSetHistory and consumed by useSessionMessagesRealtime to
  // push autonomous-write events to the operator without requiring a
  // chat-turn round-trip (FOUNDATIONS v8.4 Axiom 1 fourth sub-clause +
  // ADR-260 real-time-visible-handoffs commitment).
  const [sessionId, setSessionId] = useState<string | null>(null);
  // Realtime debounce — coalesce bursts of inserts (e.g., a Reviewer
  // wake fires 5 System Agent narrations in quick succession) into one
  // re-fetch, avoiding 5 concurrent globalHistory roundtrips.
  const realtimeRefetchTimerRef = useRef<NodeJS.Timeout | null>(null);
  // Commit H (2026-05-11): track last realtime-insert timestamp for
  // loop-active detection. Cron-fired Loops produce realtime System
  // Agent narrations without changing `status` (which only tracks
  // operator-initiated sendMessage flow). When realtime activity is
  // recent (last ~30s), we treat the Loop as in-flight and surface the
  // Stop affordance.
  const [lastRealtimeActivity, setLastRealtimeActivity] = useState<number | null>(null);

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
        console.warn('[NarrativeContext] Status timeout - resetting stuck state:', status.type);
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

  // Core history fetch — no guard. Used by loadScopedHistory (guarded)
  // and by post-ProposeAction refresh (unguarded, picks up async reviewer verdicts).
  const fetchAndSetHistory = useCallback(async () => {
    try {
      const result = await api.chat.globalHistory(1);

      if (result.sessions && result.sessions.length > 0) {
        const session = result.sessions[0];
        // Capture the session_id for realtime subscription. Stable across
        // the operator's lifetime in this workspace (unified session model).
        setSessionId(session.id);
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

            // ADR-212: reviewer verdict metadata (role === 'freddie')
            const reviewerMeta =
              m.role === 'freddie' && m.metadata
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
            // Audit-pass-2 DD-4: surface metadata.proposal_id on
            // system_agent narration entries so the FE can render an
            // inline ProposalCard chip (closes the supervisory mental-
            // thread gap on heartbeat/cron-fired ProposeAction calls).
            const narrative = m.metadata
              ? {
                  ...(m.metadata.summary && { summary: m.metadata.summary }),
                  ...(m.metadata.pulse && { pulse: m.metadata.pulse }),
                  ...(m.metadata.weight && { weight: m.metadata.weight }),
                  ...(m.metadata.task_slug && { taskSlug: m.metadata.task_slug }),
                  ...(m.metadata.invocation_id && { invocationId: m.metadata.invocation_id }),
                  // ADR-377: boundary-direction signals for the Context
                  // In/Out/Flow filtered views.
                  ...(m.metadata.written_to && { writtenTo: m.metadata.written_to }),
                  ...(m.metadata.tool && { tool: m.metadata.tool }),
                  ...(m.role === 'system_agent' && m.metadata.proposal_id && {
                    proposalId: m.metadata.proposal_id,
                  }),
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
      console.warn('[NarrativeContext] Failed to load chat history:', err);
    }
  }, []);

  const loadScopedHistory = useCallback(async (_agentId?: string, _taskSlug?: string) => {
    // Unified session: always load global history. Agent/task params ignored —
    // surface context is sent per message, not per session.
    if (historyLoadedRef.current) return;
    historyLoadedRef.current = true;
    await fetchAndSetHistory();
  }, [fetchAndSetHistory]);

  // Load global history on mount — unified session, loaded once
  useEffect(() => {
    loadScopedHistory();
  }, [loadScopedHistory]);

  // ---------------------------------------------------------------------------
  // Realtime — autonomous-write events from cron-fired Loop wakes
  // ---------------------------------------------------------------------------
  // Per FOUNDATIONS v8.4 Axiom 1 (substrate is the bus the Loop runs over):
  // when the Reviewer wakes via cron + writes substrate while the operator-
  // human is absent, the operator-in-real-time embodiment needs to SEE
  // those writes when they next attend to the cockpit. Without realtime,
  // the FE only re-fetches after sendMessage, so cron-fired narrations
  // are invisible until the operator types a chat message — silently
  // breaking ADR-260's real-time-visible-handoffs commitment.
  //
  // Implementation: on every INSERT to session_messages for our session,
  // schedule a debounced re-fetch of globalHistory. Debounce coalesces
  // bursts (e.g., a Reviewer wake fires 5 System Agent narrations within
  // ~100ms) into one re-fetch. The existing fetchAndSetHistory converter
  // is reused — Singular Implementation rule, no parallel row→TPMessage
  // logic.
  useSessionMessagesRealtime({
    sessionId,
    onInsert: () => {
      // Commit H (2026-05-11): track every realtime arrival for loop-active
      // detection. The Stop affordance surfaces when realtime activity is
      // recent (~30s), regardless of operator's own status.
      setLastRealtimeActivity(Date.now());
      // Skip realtime echoes during active sendMessage — the streaming
      // path's reducer mutations already populated optimistic UI state,
      // and a re-fetch would race against in-flight stream events.
      if (status.type !== 'idle' && status.type !== 'complete') return;
      if (realtimeRefetchTimerRef.current) {
        clearTimeout(realtimeRefetchTimerRef.current);
      }
      realtimeRefetchTimerRef.current = setTimeout(() => {
        realtimeRefetchTimerRef.current = null;
        // Fire-and-forget; failure is logged inside fetchAndSetHistory.
        void fetchAndSetHistory();
      }, 250);
    },
  });

  // Commit H (2026-05-11): loop-active derivation drives the Stop affordance.
  // Two signals:
  //   (a) operator's own sendMessage is mid-flight (status != idle/complete)
  //   (b) recent realtime arrival from an autonomous Loop wake (~30s window)
  // We re-evaluate per render; for (b) we use a 30s sliding window because
  // there's no clean "loop ended" event from the backend — a quiet pause
  // means the Loop wrapped up. The window length matches typical Reviewer
  // session duration (a few rounds × few seconds each).
  const REALTIME_ACTIVE_WINDOW_MS = 30_000;
  const operatorStreamActive = status.type !== 'idle' && status.type !== 'complete';
  const realtimeRecent =
    lastRealtimeActivity !== null &&
    Date.now() - lastRealtimeActivity < REALTIME_ACTIVE_WINDOW_MS;
  const loopActive = operatorStreamActive || realtimeRecent;

  // Tick state every 5s while a recent realtime arrival exists, so the
  // Stop affordance disappears when the window elapses without any new
  // events. Tied to lastRealtimeActivity so we only spin a timer when
  // there's something to expire.
  useEffect(() => {
    if (lastRealtimeActivity === null) return;
    const elapsed = Date.now() - lastRealtimeActivity;
    if (elapsed >= REALTIME_ACTIVE_WINDOW_MS) return;
    const timer = setTimeout(() => {
      // Force re-render by re-setting state to the same value; React
      // will see no diff but the next render's loopActive computation
      // will use the now-elapsed window.
      setLastRealtimeActivity((prev) => prev);
    }, REALTIME_ACTIVE_WINDOW_MS - elapsed + 100);
    return () => clearTimeout(timer);
  }, [lastRealtimeActivity]);

  const stopActiveLoop = useCallback(async () => {
    // (1) Abort the operator's own sendMessage stream if mid-flight.
    if (abortControllerRef.current) {
      try {
        abortControllerRef.current.abort();
      } catch {/* best-effort */}
      abortControllerRef.current = null;
    }
    // (2) POST the server-side cancel for autonomous Loop wakes (and as
    // a belt-and-suspenders signal even on operator-stream cancels).
    try {
      await api.chat.cancel();
    } catch (err) {
      console.warn('[NarrativeContext] /api/feed/cancel failed:', err);
    }
    // (3) Reset local UI state so the composer returns to send mode.
    setStatus({ type: 'idle' });
    dispatch({ type: 'SET_LOADING', isLoading: false });
    // Clear realtime-recent so the Stop affordance disappears.
    setLastRealtimeActivity(null);
  }, []);

  // ---------------------------------------------------------------------------
  // Send message to TP
  // ---------------------------------------------------------------------------
  const sendMessage = useCallback(
    async (
      content: string,
      context?: {
        surface?: DeskSurface;
        images?: TPImageAttachment[];
        targetAgentId?: string;
        fileAttachments?: Array<{ file_id: string; filename: string; mime_type: string }>;
      }
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

        // ADR-249: ephemeral file attachments via Anthropic Files API
        if (context?.fileAttachments && context.fileAttachments.length > 0) {
          body.file_attachments = context.fileAttachments;
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

        // Surface a "thinking" indicator immediately so the operator sees the
        // turn is in progress while the backend pre-loads substrate and starts
        // the loop. Cleared on first content/progress event or stream_start.
        setStatus({ type: 'thinking' });

        // Track state during streaming
        let assistantContent = '';
        const toolResults: TPToolResult[] = [];
        const blocks: MessageBlock[] = [];
        const decoder = new TextDecoder();
        let buffer = '';
        let pendingSurface: DeskSurface | null = null;
        let pendingHandoff: string | null = null;
        let clarifyWasCalled = false;
        let reviewerFired = false; // tracks whether reviewer_response SSE was received
        // Track pending tool calls by ID for updating status
        const pendingToolCalls: Map<string, number> = new Map(); // tool_use_id -> block index
        // ADR-124: Author attribution from stream_start event
        let streamAuthor: { agentId?: string; agentSlug?: string; role?: string; name?: string } | null = null;
        // Streaming placeholder ID — set when stream_start fires, null until then.
        // We only insert a placeholder once we know the System Agent will stream
        // content. Reviewer turns call loadScopedHistory() instead, so they never
        // need a client-side placeholder.
        let streamingMessageId: string | null = null;

        // Helper to update streaming message in-place by ID
        const updateStreamingMessage = () => {
          if (!streamingMessageId) return;
          dispatch({ type: 'UPDATE_STREAMING_MESSAGE', messageId: streamingMessageId, blocks: [...blocks], content: assistantContent });
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
                // ADR-124: Author attribution from backend
                streamAuthor = {
                  agentId: event.author_agent_id,
                  agentSlug: event.author_agent_slug,
                  role: event.author_role,
                  name: event.author_name,
                };
                // Insert the streaming placeholder now — only when we know the
                // System Agent will stream content. Reviewer turns never reach
                // stream_start; they call loadScopedHistory() on reviewer_response.
                streamingMessageId = crypto.randomUUID();
                const streamingPlaceholder: TPMessage = {
                  id: streamingMessageId,
                  role: 'assistant',
                  content: '',
                  blocks: [],
                  timestamp: new Date(),
                  narrative: { pulse: 'addressed', weight: 'material' },
                  ...(event.author_agent_id && { authorAgentId: event.author_agent_id }),
                  ...(event.author_agent_slug && { authorAgentSlug: event.author_agent_slug }),
                  ...(event.author_role && { authorRole: event.author_role }),
                  ...(event.author_name && { authorName: event.author_name }),
                };
                dispatch({ type: 'ADD_MESSAGE', message: streamingPlaceholder });
                setStatus({ type: 'streaming', content: '' });
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
              } else if (event.reviewer_progress) {
                const phase = event.phase;

                // ADR-351 Phase 2: the Reviewer's reasoning streams token-by-
                // token. On the first delta, insert a streaming REVIEWER bubble
                // (the stream_start analog the Reviewer path never had — see the
                // comment at the stream_start branch) and append progressively,
                // mirroring the System Agent content path above. The bubble is
                // TRANSIENT: when reviewer_response arrives, fetchAndSetHistory()
                // replaces the whole scoped history with DB truth, dropping this
                // placeholder and rendering the authoritative FreddieCard. So
                // the operator watches the reasoning build, then it settles into
                // the persisted card — no duplicate.
                if (phase === 'text_delta') {
                  const chunk: string = event.text ?? '';
                  if (!chunk) continue;
                  if (!streamingMessageId) {
                    streamingMessageId = crypto.randomUUID();
                    // role:'reviewer' is what MessageDispatch keys the
                    // reviewer-bubble on (MessageDispatch.tsx:77), matching a
                    // real Reviewer history row.
                    const reviewerPlaceholder: TPMessage = {
                      id: streamingMessageId,
                      role: 'freddie',
                      content: '',
                      blocks: [],
                      timestamp: new Date(),
                      narrative: { pulse: 'addressed', weight: 'material' },
                    };
                    dispatch({ type: 'ADD_MESSAGE', message: reviewerPlaceholder });
                  }
                  assistantContent += chunk;
                  const lastBlock = blocks[blocks.length - 1];
                  if (lastBlock?.type === 'text') {
                    lastBlock.content += chunk;
                  } else {
                    blocks.push({ type: 'text', content: chunk });
                  }
                  // The streaming BUBBLE is the surface for the reasoning text —
                  // do NOT echo it into the transient status line (that would
                  // duplicate the whole block into the 11px status row). Clear
                  // status.content so the panel's `streaming && content` guard
                  // hides the line while the bubble carries the words. This is
                  // the 'streaming' state of D3's thinking/streaming/settled.
                  if (assistantContent.length % 50 < chunk.length || chunk.includes('\n')) {
                    setStatus({ type: 'streaming', content: '' });
                    updateStreamingMessage();
                  }
                } else {
                  // ADR-351 D4: the per-tool label map ("Reviewer is reading
                  // substrate…" et al.) is DELETED. It was a frontend guess at
                  // what a primitive name meant, standing in for narration that
                  // now arrives as the persona's own streamed reasoning above.
                  // The transient tool status carries ONLY a judgment-shaped,
                  // tool-agnostic line (ADR-338 DP28 consent line — never the
                  // primitive name, never the mechanism). It is secondary to
                  // the streaming reasoning; it just signals "still working."
                  if (phase === 'tool_start') {
                    setStatus({ type: 'streaming', content: 'Reviewer is working through it…' });
                  }
                }
              } else if (event.reviewer_response) {
                // Reviewer spoke — reload history immediately so FreddieCard renders.
                // CRITICAL: use fetchAndSetHistory() (unguarded), not loadScopedHistory()
                // which has a once-per-page-load guard for initial mount. Without this,
                // every Reviewer turn after the first looked silent until hard refresh.
                reviewerFired = true;
                await fetchAndSetHistory();
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

        // Final update — only if we actually inserted a streaming placeholder.
        // ADR-124: Preserve author attribution in final message update.
        if (streamingMessageId) {
          dispatch({
            type: 'UPDATE_STREAMING_MESSAGE',
            messageId: streamingMessageId,
            blocks: [...blocks],
            content: finalContent,
            ...(streamAuthor?.agentId && { authorAgentId: streamAuthor.agentId }),
            ...(streamAuthor?.agentSlug && { authorAgentSlug: streamAuthor.agentSlug }),
            ...(streamAuthor?.role && { authorRole: streamAuthor.role }),
            ...(streamAuthor?.name && { authorName: streamAuthor.name }),
          });
        }
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

        // After stream ends: if Reviewer fired, reload history to ensure FreddieCard
        // is visible and any stale placeholder is replaced by DB truth.
        const hasProposeAction = toolResults.some(r => r.toolName === 'ProposeAction');
        if (hasProposeAction) {
          setTimeout(() => fetchAndSetHistory(), 1500);
        }
        if (reviewerFired) {
          // Same fix as in-stream handler — fetchAndSetHistory is unguarded;
          // loadScopedHistory's once-per-page-load guard would no-op here.
          await fetchAndSetHistory();
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
    [onSurfaceChange, fetchAndSetHistory]
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
  const value: NarrativeContextValue = {
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
    // Commit H (2026-05-11): interruption surface (Mode 1)
    loopActive,
    stopActiveLoop,
    // Actions
    sendMessage,
    clearMessages,
    clearClarification,
    respondToClarification,
    closeSetupConfirmModal,
    onSurfaceChange,
    loadScopedHistory,
  };

  return <NarrativeContext.Provider value={value}>{children}</NarrativeContext.Provider>;
}

// =============================================================================
// Hook
// =============================================================================

export function useNarrative(): NarrativeContextValue {
  const context = useContext(NarrativeContext);
  if (!context) {
    throw new Error('useNarrative must be used within a NarrativeProvider');
  }
  return context;
}
