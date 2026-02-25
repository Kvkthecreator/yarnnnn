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
  // Deliverables
  | { type: 'deliverable-create'; initialPlatform?: 'slack' | 'gmail' | 'notion' | 'calendar' }
  | { type: 'deliverable-review'; deliverableId: string; versionId: string }
  | { type: 'deliverable-detail'; deliverableId: string }
  | { type: 'deliverable-list'; status?: 'active' | 'paused' | 'archived' }
  // Work
  | { type: 'work-output'; workId: string; outputId?: string }
  | { type: 'work-list'; filter?: 'active' | 'completed' | 'all' }
  // Context (ADR-034: user's accumulated knowledge, scoped by emergent domains)
  | { type: 'context-browser'; scope: 'user' | 'deliverable'; scopeId?: string }
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
  type: 'deliverable-staged';
  deliverableId: string;
  versionId: string;
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
  | { type: 'REMOVE_ATTENTION'; versionId: string }
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
  /** ADR-025: Active skill name (e.g., "board-update") */
  activeSkill: string | null;
  /** ADR-025: Whether work panel is expanded */
  workPanelExpanded: boolean;
}

export type TPAction =
  | { type: 'ADD_MESSAGE'; message: TPMessage }
  | { type: 'SET_MESSAGES'; messages: TPMessage[] }
  | { type: 'CLEAR_MESSAGES' }
  // ADR-042: Update streaming message blocks in real-time
  | { type: 'UPDATE_STREAMING_MESSAGE'; blocks: MessageBlock[]; content?: string }
  | { type: 'SET_LOADING'; isLoading: boolean }
  | { type: 'SET_ERROR'; error: string | null }
  // ADR-025: Todo tracking actions
  | { type: 'SET_TODOS'; todos: Todo[] }
  | { type: 'SET_ACTIVE_SKILL'; skill: string | null }
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
    // Deliverables
    case 'deliverable-create':
      return {
        type: 'deliverable-create',
        initialPlatform: data.platform as 'slack' | 'gmail' | 'notion' | 'calendar' | undefined,
      };
    case 'deliverable':
      return { type: 'deliverable-detail', deliverableId: data.deliverableId as string };
    case 'deliverable-review':
      return {
        type: 'deliverable-review',
        deliverableId: data.deliverableId as string,
        versionId: data.versionId as string,
      };
    case 'deliverable-list':
      return {
        type: 'deliverable-list',
        status: data.status as 'active' | 'paused' | 'archived' | undefined,
      };

    // Work
    case 'output':
    case 'work-output':
      return {
        type: 'work-output',
        workId: data.workId as string,
        outputId: data.outputId as string | undefined,
      };
    case 'work-list':
      return { type: 'work-list' };

    // Context (ADR-034)
    case 'context':
    case 'memory':
      return {
        type: 'context-browser',
        scope: (data.scope as 'user' | 'deliverable') || 'user',
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
    case 'deliverable-create':
      if (surface.initialPlatform) params.set('platform', surface.initialPlatform);
      break;
    case 'deliverable-review':
      params.set('did', surface.deliverableId);
      params.set('vid', surface.versionId);
      break;
    case 'deliverable-detail':
      params.set('did', surface.deliverableId);
      break;
    case 'deliverable-list':
      if (surface.status) params.set('status', surface.status);
      break;
    case 'work-output':
      params.set('wid', surface.workId);
      if (surface.outputId) params.set('oid', surface.outputId);
      break;
    case 'work-list':
      if (surface.filter) params.set('filter', surface.filter);
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
    case 'deliverable-create': {
      const platform = params.get('platform');
      return {
        type: 'deliverable-create',
        initialPlatform: platform as 'slack' | 'gmail' | 'notion' | 'calendar' | undefined,
      };
    }
    case 'deliverable-review': {
      const did = params.get('did');
      const vid = params.get('vid');
      if (did && vid) return { type: 'deliverable-review', deliverableId: did, versionId: vid };
      break;
    }
    case 'deliverable-detail': {
      const did = params.get('did');
      if (did) return { type: 'deliverable-detail', deliverableId: did };
      break;
    }
    case 'deliverable-list':
      return { type: 'deliverable-list', status: (params.get('status') as 'active' | 'paused' | 'archived') || undefined };
    case 'work-output': {
      const wid = params.get('wid');
      if (wid) return { type: 'work-output', workId: wid, outputId: params.get('oid') || undefined };
      break;
    }
    case 'work-list':
      return { type: 'work-list', filter: (params.get('filter') as 'active' | 'completed' | 'all') || undefined };
    case 'context-browser':
      return {
        type: 'context-browser',
        scope: (params.get('scope') as 'user' | 'deliverable') || 'user',
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
