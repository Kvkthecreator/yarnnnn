/**
 * ADR-022: Chat-First Tab Architecture
 *
 * Tab types for IDE-like experience:
 * - Chat tab is always present (home)
 * - Output tabs open when viewing agents, runs, etc.
 * - Each tab type has its own full-page view
 */

// Tab types - each represents a different "file type" or view
export type TabType = 'chat' | 'agent' | 'run' | 'document';

// Unified tab interface
export interface Tab {
  id: string;
  type: TabType;
  title: string;
  // For output tabs, the resource ID
  resourceId?: string;
  // Additional context data
  data?: Record<string, unknown>;
  // Tab state
  isDirty?: boolean; // Has unsaved changes
  isClosable: boolean; // Can be closed (chat tab cannot)
}

// Tab state for context
export interface TabState {
  tabs: Tab[];
  activeTabId: string;
}

// Tab actions
export type TabAction =
  | { type: 'OPEN_TAB'; payload: Tab }
  | { type: 'CLOSE_TAB'; payload: { tabId: string } }
  | { type: 'SET_ACTIVE'; payload: { tabId: string } }
  | { type: 'UPDATE_TAB'; payload: { tabId: string; updates: Partial<Tab> } }
  | { type: 'REORDER_TABS'; payload: { tabIds: string[] } };

// Helper to create tabs
export function createChatTab(): Tab {
  return {
    id: 'chat',
    type: 'chat',
    title: 'Chat',
    isClosable: false,
  };
}

export function createAgentTab(id: string, title: string): Tab {
  return {
    id: `agent-${id}`,
    type: 'agent',
    title,
    resourceId: id,
    isClosable: true,
  };
}

export function createRunTab(
  agentId: string,
  runId: string,
  title: string
): Tab {
  return {
    id: `run-${runId}`,
    type: 'run',
    title,
    resourceId: runId,
    data: { agentId, runId },
    isClosable: true,
  };
}

export function createDocumentTab(id: string, title: string): Tab {
  return {
    id: `document-${id}`,
    type: 'document',
    title,
    resourceId: id,
    isClosable: true,
  };
}
