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
  type: 'OPEN_SURFACE';
  surface: string;
  data: Record<string, unknown>;
}

export interface Chip {
  label: string;
  prompt: string;
}

// =============================================================================
// Desk State
// =============================================================================

export interface DeskState {
  surface: DeskSurface;
  attention: AttentionItem[];
  isLoading: boolean;
  error: string | null;
}

export type DeskAction =
  | { type: 'SET_SURFACE'; surface: DeskSurface }
  | { type: 'SET_ATTENTION'; items: AttentionItem[] }
  | { type: 'ADD_ATTENTION'; item: AttentionItem }
  | { type: 'REMOVE_ATTENTION'; versionId: string }
  | { type: 'CLEAR_SURFACE' }
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
}

export type TPAction =
  | { type: 'ADD_MESSAGE'; message: TPMessage }
  | { type: 'SET_MESSAGES'; messages: TPMessage[] }
  | { type: 'CLEAR_MESSAGES' }
  | { type: 'SET_LOADING'; isLoading: boolean }
  | { type: 'SET_ERROR'; error: string | null };

// =============================================================================
// Domain Browser
// =============================================================================

export interface BrowserData {
  deliverables: BrowserDeliverable[];
  recentWork: BrowserWork[];
  userMemoryCount: number;
  deliverableContexts: BrowserDeliverableContext[];
  recentDocuments: BrowserDocument[];
}

export interface BrowserDeliverable {
  id: string;
  title: string;
  status: 'active' | 'paused' | 'archived';
  scheduleDescription: string;
  nextRunAt?: string;
}

export interface BrowserWork {
  id: string;
  title: string;
  status: string;
  agentType: string;
  completedAt?: string;
}

export interface BrowserDeliverableContext {
  deliverableId: string;
  deliverableTitle: string;
  memoryCount: number;
}

export interface BrowserDocument {
  id: string;
  filename: string;
  uploadedAt: string;
}

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
  }

  return { type: 'idle' };
}
