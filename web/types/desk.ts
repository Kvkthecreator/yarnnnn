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
  // Agents (create handled by TP chat — /dashboard?create)
  | { type: 'agent-review'; agentId: string; runId: string }
  | { type: 'agent-detail'; agentId: string }
  | { type: 'agent-list'; status?: 'active' | 'paused' | 'archived' }
  // Projects (ADR-119 P4b)
  | { type: 'project-detail'; projectSlug: string }
  // Context (ADR-034: user's accumulated knowledge, scoped by emergent domains)
  | { type: 'context-browser'; scope: 'user' | 'agent'; scopeId?: string }
  | { type: 'context-editor'; memoryId: string }
  // Documents
  | { type: 'document-viewer'; documentId: string }
  | { type: 'document-list' }
  // Platforms (ADR-033)
  | { type: 'platform-list' }
  | { type: 'platform-detail'; platform: 'slack' | 'notion' | 'gmail' | 'calendar' }
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
export type MessageBlock =
  | { type: 'text'; content: string }
  | { type: 'thinking'; content: string }
  | { type: 'tool_call'; id: string; tool: string; input?: Record<string, unknown>; status: 'pending' | 'success' | 'failed'; result?: TPToolResult }
  | { type: 'clarify'; question: string; options?: string[] };

export interface TPMessage {
  id: string;
  role: 'user' | 'assistant';
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
}

export interface TPToolResult {
  toolName: string;
  success: boolean;
  data?: Record<string, unknown>;
  uiAction?: TPUIAction;
}

export interface TPUIAction {
  type: 'OPEN_SURFACE' | 'RESPOND' | 'CLARIFY' | 'SHOW_SETUP_CONFIRM' | 'UPDATE_TODOS';
  surface?: string;
  data: Record<string, unknown>;
}

// =============================================================================
// Todo Tracking (ADR-025 Claude Code Alignment)
// =============================================================================

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
  | { type: 'CLEAR_WORK_STATE' };

// =============================================================================
// Utility functions
// =============================================================================

/**
 * Map TP tool ui_action to DeskSurface
 */
export function mapToolActionToSurface(action: TPUIAction): DeskSurface | null {
  const { surface, data } = action;

  switch (surface) {
    // Agents (create handled by TP chat — /dashboard?create)
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

    // Projects (ADR-119 P4b)
    case 'project':
    case 'project-detail':
      return { type: 'project-detail', projectSlug: data.projectSlug as string };

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
        platform: data.platform as 'slack' | 'notion' | 'gmail' | 'calendar',
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
    case 'project-detail':
      params.set('projectSlug', surface.projectSlug);
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
    case 'project-detail': {
      const pSlug = params.get('projectSlug');
      if (pSlug) return { type: 'project-detail', projectSlug: pSlug };
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
      if (platform && ['slack', 'notion', 'gmail', 'calendar'].includes(platform)) {
        return { type: 'platform-detail', platform: platform as 'slack' | 'notion' | 'gmail' | 'calendar' };
      }
      break;
    }
  }

  return { type: 'idle' };
}
