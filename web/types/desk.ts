/**
 * ADR-023: Supervisor Desk Architecture
 * ADR-034: Context (emergent domains)
 *
 * Type definitions for the desk surface system
 */

// =============================================================================
// Desk Surface Types
// =============================================================================

export type DeskSurface =
  // Agents (create handled by YARNNN chat — /dashboard?create)
  | { type: 'agent-review'; agentId: string; runId: string }
  | { type: 'agent-detail'; agentId: string }
  | { type: 'agent-list'; status?: 'active' | 'paused' | 'archived' }
  // Tasks (ADR-139)
  | { type: 'task-detail'; taskSlug: string }
  // Context (ADR-034: user's accumulated knowledge, scoped by emergent domains)
  | { type: 'context-browser'; scope: 'user' | 'agent'; scopeId?: string }
  | { type: 'context-editor'; memoryId: string }
  // Documents
  | { type: 'document-viewer'; documentId: string }
  | { type: 'document-list' }
  // Platforms (ADR-033)
  | { type: 'platform-list' }
  | { type: 'platform-detail'; platform: 'slack' | 'notion' }
  // Workspace explorer (Context surface)
  | { type: 'workspace-explorer'; path: string; navigation_type?: 'file' | 'folder' }
  // Idle state
  | { type: 'idle' };

// =============================================================================
// Attention Queue
// =============================================================================

export interface AttentionItem {
  type: 'agent-staged';
  agentId: string;
  runId: string;
  title: string;
  stagedAt: string;
}

// =============================================================================
// TP (Thinking Partner)
// =============================================================================

/** Image attachment sent inline as base64 (not stored, ephemeral) */
export interface TPImageAttachment {
  /** Base64-encoded image data */
  data: string;
  /** MIME type (image/jpeg, image/png, image/gif, image/webp) */
  mediaType: 'image/jpeg' | 'image/png' | 'image/gif' | 'image/webp';
}

/**
 * ADR-042: Streaming Process Visibility
 * Message content blocks for inline tool display
 */
export type SystemCardType =
  | 'workspace_init_complete'
  | 'task_complete'
  // ADR-219 Commit 3: rolled-up housekeeping digest written by
  // back-office-narrative-digest. Frontend renders as a collapsed
  // card with expand-to-list using metadata.rolled_up_ids/counts.
  | 'narrative_digest';

/**
 * ADR-219 Commit 2: narrative envelope per session_messages row.
 * Mirrors the metadata fields that services.narrative.write_narrative_entry
 * stamps. Available on every TPMessage post-Commit-2; older rows
 * surface with only the fields that were set when they were written.
 */
export type NarrativeWeight = 'material' | 'routine' | 'housekeeping';
export type NarrativePulse = 'periodic' | 'reactive' | 'addressed' | 'heartbeat';

export interface NarrativeEnvelope {
  /** One-line headline used for collapsed (routine) rendering. */
  summary?: string;
  pulse?: NarrativePulse;
  weight?: NarrativeWeight;
  /** Task slug nameplate, when this invocation was labeled. */
  taskSlug?: string;
  /** agent_runs row id when this invocation produced one. */
  invocationId?: string;
}

export type MessageBlock =
  | { type: 'text'; content: string }
  | { type: 'thinking'; content: string }
  | { type: 'tool_call'; id: string; tool: string; input?: Record<string, unknown>; status: 'pending' | 'success' | 'failed'; result?: TPToolResult }
  | { type: 'clarify'; question: string; options?: string[] }
  | { type: 'notification'; title: string; description?: string; toolName: string }
  | { type: 'system_card'; card_type: SystemCardType; data: Record<string, unknown> };

/**
 * ADR-212 / 2026-04-23: Reviewer verdict metadata surfaced as chat messages.
 * Populated when role === 'reviewer'. Enables ReviewerCard rendering.
 */
export interface ReviewerCardData {
  proposalId?: string;
  verdict?: 'approve' | 'reject' | 'defer' | 'observation' | string;
  occupant?: string;
  actionType?: string;
  taskSlug?: string;
}

export interface TPMessage {
  id: string;
  /**
   * ADR-219 Commit 2 widened the session_messages.role enum to include
   * the full Identity taxonomy: user, assistant, system, reviewer, agent,
   * external. The frontend mirrors that union so every narrative entry
   * round-trips through TPMessage without conflation.
   */
  role: 'user' | 'assistant' | 'system' | 'reviewer' | 'agent' | 'external';
  content: string;
  /** Images attached to this message (user messages only) */
  images?: TPImageAttachment[];
  /** Legacy: tool results shown at end of message */
  toolResults?: TPToolResult[];
  /** ADR-042: Structured content blocks for inline display */
  blocks?: MessageBlock[];
  timestamp: Date;
  /** ADR-124: Author attribution for meeting room messages */
  authorAgentId?: string;
  authorAgentSlug?: string;
  authorRole?: string;
  authorName?: string;
  /** ADR-212: reviewer verdict metadata (role === 'reviewer') */
  reviewer?: ReviewerCardData;
  /** ADR-219 Commit 2: narrative envelope (weight, pulse, summary, …). */
  narrative?: NarrativeEnvelope;
}

export interface TPToolResult {
  toolName: string;
  success: boolean;
  data?: Record<string, unknown>;
  uiAction?: TPUIAction;
}

export interface TPUIAction {
  type: 'OPEN_SURFACE' | 'RESPOND' | 'CLARIFY' | 'SHOW_SETUP_CONFIRM' | 'UPDATE_TODOS' | 'NAVIGATE';
  surface?: string;
  data: Record<string, unknown>;
}

// =============================================================================
// Todo Tracking (ADR-025 Claude Code Alignment)
// =============================================================================

/** ADR-155: Notification from tool side effects */
export interface TPNotification {
  id: string;
  toolName: string;
  title: string;
  description?: string;
  timestamp: Date;
}

/** A single todo item in TP's work progress */
export interface Todo {
  /** Task description in imperative form (e.g., "Gather details") */
  content: string;
  /** Current status of the task */
  status: 'pending' | 'in_progress' | 'completed';
  /** Task description in present continuous (e.g., "Gathering details") */
  activeForm?: string;
}

// =============================================================================
// Desk State
// =============================================================================

export interface DeskState {
  surface: DeskSurface;
  attention: AttentionItem[];
  isLoading: boolean;
  error: string | null;
  /** Message from TP shown briefly at top of surface after navigation */
  handoffMessage: string | null;
}

export type DeskAction =
  | { type: 'SET_SURFACE'; surface: DeskSurface }
  | { type: 'SET_SURFACE_WITH_HANDOFF'; surface: DeskSurface; handoffMessage: string }
  | { type: 'SET_ATTENTION'; items: AttentionItem[] }
  | { type: 'ADD_ATTENTION'; item: AttentionItem }
  | { type: 'REMOVE_ATTENTION'; runId: string }
  | { type: 'CLEAR_SURFACE' }
  | { type: 'CLEAR_HANDOFF' }
  | { type: 'NEXT_ATTENTION' }
  | { type: 'SET_LOADING'; isLoading: boolean }
  | { type: 'SET_ERROR'; error: string | null };

// =============================================================================
// TP State
// =============================================================================

export interface TPState {
  messages: TPMessage[];
  isLoading: boolean;
  error: string | null;
  /** ADR-025: Current todo list for multi-step work */
  todos: Todo[];
  /** ADR-025: Active slash command name (e.g., "recap", "summary") */
  activeCommand: string | null;
  /** ADR-025: Whether work panel is expanded */
  workPanelExpanded: boolean;
  /** ADR-155: Notifications from tool side effects (queued when chat closed) */
  pendingNotifications: TPNotification[];
}

export type TPAction =
  | { type: 'ADD_MESSAGE'; message: TPMessage }
  | { type: 'SET_MESSAGES'; messages: TPMessage[] }
  | { type: 'CLEAR_MESSAGES' }
  // ADR-042: Update streaming message blocks in real-time
  // ADR-124: author fields for meeting room attribution
  | { type: 'UPDATE_STREAMING_MESSAGE'; blocks: MessageBlock[]; content?: string; authorAgentId?: string; authorAgentSlug?: string; authorRole?: string; authorName?: string }
  | { type: 'SET_LOADING'; isLoading: boolean }
  | { type: 'SET_ERROR'; error: string | null }
  // ADR-025: Todo tracking actions
  | { type: 'SET_TODOS'; todos: Todo[] }
  | { type: 'SET_ACTIVE_COMMAND'; command: string | null }
  | { type: 'SET_WORK_PANEL_EXPANDED'; expanded: boolean }
  | { type: 'CLEAR_WORK_STATE' }
  // ADR-155: Notification channel
  | { type: 'ADD_NOTIFICATION'; notification: TPNotification }
  | { type: 'FLUSH_NOTIFICATIONS' };

// =============================================================================
// Utility functions
// =============================================================================

/**
 * Map TP tool ui_action to DeskSurface
 */
export function mapToolActionToSurface(action: TPUIAction): DeskSurface | null {
  const { surface, data } = action;

  switch (surface) {
    // Agents (create handled by YARNNN chat — /dashboard?create)
    case 'agent':
      return { type: 'agent-detail', agentId: data.agentId as string };
    case 'agent-review':
      return {
        type: 'agent-review',
        agentId: data.agentId as string,
        runId: data.runId as string,
      };
    case 'agent-list':
      return {
        type: 'agent-list',
        status: data.status as 'active' | 'paused' | 'archived' | undefined,
      };

    // Tasks (ADR-139)
    case 'task':
    case 'task-detail':
      return { type: 'task-detail', taskSlug: data.taskSlug as string };

    // Context (ADR-034)
    case 'context':
    case 'memory':
      return {
        type: 'context-browser',
        scope: (data.scope as 'user' | 'agent') || 'user',
        scopeId: data.scopeId as string | undefined,
      };
    case 'memory-edit':
      return { type: 'context-editor', memoryId: data.memoryId as string };

    // Documents
    case 'document':
      return { type: 'document-viewer', documentId: data.documentId as string };
    case 'document-list':
      return { type: 'document-list' };

    // Platforms (ADR-033)
    case 'platforms':
    case 'platform-list':
      return { type: 'platform-list' };
    case 'platform':
    case 'platform-detail':
      return {
        type: 'platform-detail',
        platform: data.platform as 'slack' | 'notion',
      };

    // Dashboard/Home
    case 'dashboard':
    case 'home':
    case 'idle':
      return { type: 'idle' };

    default:
      return null;
  }
}

/**
 * Serialize surface to URL params
 */
export function surfaceToParams(surface: DeskSurface): URLSearchParams {
  const params = new URLSearchParams();
  params.set('surface', surface.type);

  switch (surface.type) {
    case 'agent-review':
      params.set('did', surface.agentId);
      params.set('vid', surface.runId);
      break;
    case 'agent-detail':
      params.set('did', surface.agentId);
      break;
    case 'agent-list':
      if (surface.status) params.set('status', surface.status);
      break;
    case 'task-detail':
      params.set('taskSlug', surface.taskSlug);
      break;
    case 'context-browser':
      params.set('scope', surface.scope);
      if (surface.scopeId) params.set('scopeId', surface.scopeId);
      break;
    case 'context-editor':
      params.set('mid', surface.memoryId);
      break;
    case 'document-viewer':
      params.set('docId', surface.documentId);
      break;
    case 'platform-detail':
      params.set('platform', surface.platform);
      break;
  }

  return params;
}

/**
 * Parse URL params to surface
 */
export function paramsToSurface(params: URLSearchParams): DeskSurface {
  const surfaceType = params.get('surface');

  switch (surfaceType) {
    case 'agent-review': {
      const did = params.get('did');
      const vid = params.get('vid');
      if (did && vid) return { type: 'agent-review', agentId: did, runId: vid };
      break;
    }
    case 'agent-detail': {
      const did = params.get('did');
      if (did) return { type: 'agent-detail', agentId: did };
      break;
    }
    case 'agent-list':
      return { type: 'agent-list', status: (params.get('status') as 'active' | 'paused' | 'archived') || undefined };
    case 'task-detail': {
      const tSlug = params.get('taskSlug');
      if (tSlug) return { type: 'task-detail', taskSlug: tSlug };
      break;
    }
    case 'context-browser':
      return {
        type: 'context-browser',
        scope: (params.get('scope') as 'user' | 'agent') || 'user',
        scopeId: params.get('scopeId') || undefined,
      };
    case 'context-editor': {
      const mid = params.get('mid');
      if (mid) return { type: 'context-editor', memoryId: mid };
      break;
    }
    case 'document-viewer': {
      const docId = params.get('docId');
      if (docId) return { type: 'document-viewer', documentId: docId };
      break;
    }
    case 'document-list':
      return { type: 'document-list' };
    case 'platform-list':
      return { type: 'platform-list' };
    case 'platform-detail': {
      const platform = params.get('platform');
      if (platform && ['slack', 'notion'].includes(platform)) {
        return { type: 'platform-detail', platform: platform as 'slack' | 'notion' };
      }
      break;
    }
  }

  return { type: 'idle' };
}
