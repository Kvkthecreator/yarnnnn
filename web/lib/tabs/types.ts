/**
 * ADR-022: Tab-Based Supervision Architecture
 *
 * Type definitions for the tab system.
 */

// Tab content types - determines rendering and TP context
export type TabType =
  | 'home'
  | 'deliverable'
  | 'version-review'
  | 'memory'
  | 'context'
  | 'document'
  | 'profile';

// Tab state
export type TabStatus = 'idle' | 'loading' | 'error' | 'unsaved';

// Icon mapping for tab types
export const TAB_ICONS: Record<TabType, string> = {
  'home': '🏠',
  'deliverable': '📋',
  'version-review': '✏️',
  'memory': '🧠',
  'context': '📚',
  'document': '📄',
  'profile': '👤',
};

// Tab definition
export interface Tab {
  id: string;                    // Unique tab ID (e.g., 'home', 'del_123', 'mem_456')
  type: TabType;                 // Determines renderer and TP context
  title: string;                 // Display title
  resourceId?: string;           // Associated resource ID (deliverable ID, memory ID, etc.)
  status: TabStatus;             // Current tab state
  closeable: boolean;            // Whether tab can be closed (home is not closeable)
  data?: Record<string, unknown>; // Optional cached data for the tab
}

// Quick action for TP layer
export interface QuickAction {
  id: string;
  label: string;
  prompt: string;
  icon?: string;
}

// Quick actions by tab type
export const TAB_QUICK_ACTIONS: Record<TabType, QuickAction[]> = {
  'home': [
    { id: 'create', label: 'Create new', prompt: "I'd like to create a new recurring deliverable" },
    { id: 'due', label: "What's due", prompt: 'What deliverables are coming up soon?' },
    { id: 'run-all', label: 'Run all', prompt: 'Run all my active deliverables now' },
  ],
  'deliverable': [
    { id: 'run', label: 'Run now', prompt: 'Generate a new version of this deliverable now' },
    { id: 'schedule', label: 'Edit schedule', prompt: 'Help me change the schedule for this deliverable' },
    { id: 'pause', label: 'Pause', prompt: 'Pause this deliverable' },
  ],
  'version-review': [
    { id: 'shorter', label: 'Shorter', prompt: 'Make this more concise - cut it down to the key points' },
    { id: 'detail', label: 'More detail', prompt: 'Add more detail and specifics to this' },
    { id: 'formal', label: 'More formal', prompt: 'Adjust the tone to be more professional and formal' },
    { id: 'casual', label: 'More casual', prompt: 'Adjust the tone to be more casual and conversational' },
  ],
  'memory': [
    { id: 'edit', label: 'Edit', prompt: 'I want to edit this memory' },
    { id: 'delete', label: 'Delete', prompt: 'Delete this memory' },
    { id: 'link', label: 'Link', prompt: 'Link this memory to a deliverable' },
  ],
  'context': [
    { id: 'summarize', label: 'Summarize', prompt: 'Summarize this context item' },
    { id: 'extract', label: 'Extract', prompt: 'Extract key points from this' },
    { id: 'delete', label: 'Delete', prompt: 'Delete this context item' },
  ],
  'document': [
    { id: 'summarize', label: 'Summarize', prompt: 'Summarize this document' },
    { id: 'extract', label: 'Extract to memory', prompt: 'Extract key information to memory' },
    { id: 'delete', label: 'Delete', prompt: 'Delete this document' },
  ],
  'profile': [
    { id: 'preferences', label: 'Preferences', prompt: 'Help me update my preferences' },
    { id: 'export', label: 'Export data', prompt: 'Export my data' },
  ],
};

// TP context info based on active tab
export interface TPContext {
  tabType: TabType;
  tabId: string;
  resourceId?: string;
  title: string;
  quickActions: QuickAction[];
}

// Helper to create a tab
export function createTab(
  type: TabType,
  title: string,
  resourceId?: string,
  data?: Record<string, unknown>
): Tab {
  const id = resourceId ? `${type}_${resourceId}` : type;
  return {
    id,
    type,
    title,
    resourceId,
    status: 'idle',
    closeable: type !== 'home',
    data,
  };
}

// Helper to create home tab
export function createHomeTab(): Tab {
  return createTab('home', 'Home');
}

// Get TP context for a tab
export function getTPContext(tab: Tab): TPContext {
  return {
    tabType: tab.type,
    tabId: tab.id,
    resourceId: tab.resourceId,
    title: tab.title,
    quickActions: TAB_QUICK_ACTIONS[tab.type] || [],
  };
}
