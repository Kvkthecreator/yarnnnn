/**
 * ADR-023: Supervisor Desk Architecture
 * Type definitions for the desk surface system
 */

// =============================================================================
// Desk Surface Types
// =============================================================================

export type DeskSurface =
  // Deliverables domain
  | { type: 'deliverable-review'; deliverableId: string; versionId: string }
  | { type: 'deliverable-detail'; deliverableId: string }
  | { type: 'deliverable-list'; status?: 'active' | 'paused' | 'archived' }
  // Work domain
  | { type: 'work-output'; workId: string; outputId?: string }
  | { type: 'work-list'; filter?: 'active' | 'completed' | 'all' }
  // Context domain
  | { type: 'context-browser'; scope: 'user' | 'deliverable' | 'project'; scopeId?: string }
  | { type: 'context-editor'; memoryId: string }
  // Documents domain
  | { type: 'document-viewer'; documentId: string }
  | { type: 'document-list'; projectId?: string }
  // Projects domain
  | { type: 'project-detail'; projectId: string }
  | { type: 'project-list' }
  // Platforms domain (ADR-033 Phase 4)
  | { type: 'platform-list' }
  | { type: 'platform-detail'; platform: 'slack' | 'notion' | 'gmail' | 'google' }
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

export interface TPMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolResults?: TPToolResult[];
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

/** Selected project context for TP routing (ADR-024) */
export interface SelectedProject {
  id: string;
  name: string;
}

export interface DeskState {
  surface: DeskSurface;
  attention: AttentionItem[];
  isLoading: boolean;
  error: string | null;
  /** Message from TP shown briefly at top of surface after navigation */
  handoffMessage: string | null;
  /** Currently selected project for context routing (ADR-024) */
  selectedProject: SelectedProject | null;
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
  | { type: 'SET_ERROR'; error: string | null }
  | { type: 'SET_SELECTED_PROJECT'; project: SelectedProject | null };

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

    // Context
    case 'context':
    case 'memory':
      return {
        type: 'context-browser',
        scope: (data.scope as 'user' | 'deliverable' | 'project') || 'user',
        scopeId: data.scopeId as string | undefined,
      };
    case 'memory-edit':
      return { type: 'context-editor', memoryId: data.memoryId as string };

    // Documents
    case 'document':
      return { type: 'document-viewer', documentId: data.documentId as string };
    case 'document-list':
      return { type: 'document-list', projectId: data.projectId as string | undefined };

    // Projects
    case 'project':
      return { type: 'project-detail', projectId: data.projectId as string };
    case 'project-list':
      return { type: 'project-list' };

    // Platforms (ADR-033 Phase 4)
    case 'platforms':
    case 'platform-list':
      return { type: 'platform-list' };
    case 'platform':
    case 'platform-detail':
      return {
        type: 'platform-detail',
        platform: data.platform as 'slack' | 'notion' | 'gmail' | 'google',
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
    case 'document-list':
      if (surface.projectId) params.set('pid', surface.projectId);
      break;
    case 'project-detail':
      params.set('pid', surface.projectId);
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
        scope: (params.get('scope') as 'user' | 'deliverable' | 'project') || 'user',
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
      return { type: 'document-list', projectId: params.get('pid') || undefined };
    case 'project-detail': {
      const pid = params.get('pid');
      if (pid) return { type: 'project-detail', projectId: pid };
      break;
    }
    case 'project-list':
      return { type: 'project-list' };
    case 'platform-list':
      return { type: 'platform-list' };
    case 'platform-detail': {
      const platform = params.get('platform');
      if (platform && ['slack', 'notion', 'gmail', 'google'].includes(platform)) {
        return { type: 'platform-detail', platform: platform as 'slack' | 'notion' | 'gmail' | 'google' };
      }
      break;
    }
  }

  return { type: 'idle' };
}
