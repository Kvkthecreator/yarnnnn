'use client';

/**
 * ADR-022: Chat-First Tab Architecture
 *
 * Context for managing IDE-like tabs:
 * - Chat tab is always present and active by default
 * - Output tabs can be opened, closed, reordered
 * - Persists tab state across navigation
 */

import { createContext, useContext, useReducer, useCallback, ReactNode } from 'react';
import type { Tab, TabState, TabAction } from '@/lib/tabs';
import {
  createChatTab,
  createDeliverableTab,
  createVersionTab,
} from '@/lib/tabs';

// Initial state: just the chat tab
const initialState: TabState = {
  tabs: [createChatTab()],
  activeTabId: 'chat',
};

function tabReducer(state: TabState, action: TabAction): TabState {
  switch (action.type) {
    case 'OPEN_TAB': {
      // Check if tab already exists
      const existingTab = state.tabs.find(t => t.id === action.payload.id);
      if (existingTab) {
        // Just activate it
        return { ...state, activeTabId: action.payload.id };
      }
      // Add new tab and activate it
      return {
        tabs: [...state.tabs, action.payload],
        activeTabId: action.payload.id,
      };
    }

    case 'CLOSE_TAB': {
      const tab = state.tabs.find(t => t.id === action.payload.tabId);
      // Can't close non-closable tabs (like chat)
      if (!tab || tab.isClosable === false) {
        return state;
      }

      const newTabs = state.tabs.filter(t => t.id !== action.payload.tabId);

      // If closing active tab, activate the previous tab or chat
      let newActiveId = state.activeTabId;
      if (state.activeTabId === action.payload.tabId) {
        const closedIndex = state.tabs.findIndex(t => t.id === action.payload.tabId);
        const prevTab = newTabs[closedIndex - 1] || newTabs[0];
        newActiveId = prevTab?.id || 'chat';
      }

      return { tabs: newTabs, activeTabId: newActiveId };
    }

    case 'SET_ACTIVE': {
      const exists = state.tabs.some(t => t.id === action.payload.tabId);
      if (!exists) return state;
      return { ...state, activeTabId: action.payload.tabId };
    }

    case 'UPDATE_TAB': {
      return {
        ...state,
        tabs: state.tabs.map(t =>
          t.id === action.payload.tabId
            ? { ...t, ...action.payload.updates }
            : t
        ),
      };
    }

    case 'REORDER_TABS': {
      // Reorder based on provided IDs (chat always first)
      const reordered = action.payload.tabIds
        .map(id => state.tabs.find(t => t.id === id))
        .filter((t): t is Tab => t !== undefined);

      // Ensure chat is first
      const chatTab = reordered.find(t => t.type === 'chat');
      const others = reordered.filter(t => t.type !== 'chat');

      return {
        ...state,
        tabs: chatTab ? [chatTab, ...others] : others,
      };
    }

    default:
      return state;
  }
}

interface TabContextValue {
  tabs: Tab[];
  activeTabId: string;
  activeTab: Tab | undefined;

  // Actions
  openDeliverableTab: (id: string, title: string) => void;
  openVersionTab: (deliverableId: string, versionId: string, title: string) => void;
  closeTab: (tabId: string) => void;
  setActiveTab: (tabId: string) => void;
  updateTab: (tabId: string, updates: Partial<Tab>) => void;
  goToChat: () => void;
}

const TabContext = createContext<TabContextValue | null>(null);

export function TabProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(tabReducer, initialState);

  const openDeliverableTab = useCallback((id: string, title: string) => {
    dispatch({
      type: 'OPEN_TAB',
      payload: createDeliverableTab(id, title),
    });
  }, []);

  const openVersionTab = useCallback(
    (deliverableId: string, versionId: string, title: string) => {
      dispatch({
        type: 'OPEN_TAB',
        payload: createVersionTab(deliverableId, versionId, title),
      });
    },
    []
  );

  const closeTab = useCallback((tabId: string) => {
    dispatch({ type: 'CLOSE_TAB', payload: { tabId } });
  }, []);

  const setActiveTab = useCallback((tabId: string) => {
    dispatch({ type: 'SET_ACTIVE', payload: { tabId } });
  }, []);

  const updateTab = useCallback((tabId: string, updates: Partial<Tab>) => {
    dispatch({ type: 'UPDATE_TAB', payload: { tabId, updates } });
  }, []);

  const goToChat = useCallback(() => {
    dispatch({ type: 'SET_ACTIVE', payload: { tabId: 'chat' } });
  }, []);

  const activeTab = state.tabs.find(t => t.id === state.activeTabId);

  return (
    <TabContext.Provider
      value={{
        tabs: state.tabs,
        activeTabId: state.activeTabId,
        activeTab,
        openDeliverableTab,
        openVersionTab,
        closeTab,
        setActiveTab,
        updateTab,
        goToChat,
      }}
    >
      {children}
    </TabContext.Provider>
  );
}

export function useTabs() {
  const context = useContext(TabContext);
  if (!context) {
    throw new Error('useTabs must be used within TabProvider');
  }
  return context;
}
