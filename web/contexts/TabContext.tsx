'use client';

/**
 * ADR-022: Tab-Based Supervision Architecture
 *
 * Global tab state management.
 * Manages open tabs, active tab, and tab operations.
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Tab,
  TabType,
  TabStatus,
  TPContext,
  createTab,
  createHomeTab,
  getTPContext,
} from '@/lib/tabs';

interface TabContextValue {
  // State
  tabs: Tab[];
  activeTabId: string;
  activeTab: Tab | null;
  tpContext: TPContext | null;

  // Tab operations
  openTab: (type: TabType, title: string, resourceId?: string, data?: Record<string, unknown>) => void;
  closeTab: (tabId: string) => void;
  setActiveTab: (tabId: string) => void;
  updateTabStatus: (tabId: string, status: TabStatus) => void;
  updateTabData: (tabId: string, data: Record<string, unknown>) => void;
  reorderTabs: (fromIndex: number, toIndex: number) => void;

  // Helpers
  findTabByResource: (type: TabType, resourceId: string) => Tab | undefined;
  isTabOpen: (type: TabType, resourceId?: string) => boolean;
}

const TabContext = createContext<TabContextValue | null>(null);

const MAX_TABS = 10;

export function TabProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Initialize with home tab
  const [tabs, setTabs] = useState<Tab[]>([createHomeTab()]);
  const [activeTabId, setActiveTabId] = useState<string>('home');

  // Get active tab
  const activeTab = tabs.find(t => t.id === activeTabId) || null;

  // Get TP context for active tab
  const tpContext = activeTab ? getTPContext(activeTab) : null;

  // Sync tabs with URL on mount
  useEffect(() => {
    const tabParam = searchParams.get('tab');
    const activeParam = searchParams.get('active');

    if (tabParam) {
      // URL has tab state - restore it
      // Format: tab=del_123,mem_456&active=del_123
      // For now, just handle active tab
      if (activeParam && tabs.some(t => t.id === activeParam)) {
        setActiveTabId(activeParam);
      }
    }
  }, [searchParams]);

  // Update URL when active tab changes
  const syncUrlWithTabs = useCallback((newActiveId: string, newTabs: Tab[]) => {
    // Only sync non-home tabs to URL
    const openTabIds = newTabs
      .filter(t => t.id !== 'home')
      .map(t => t.id);

    if (openTabIds.length === 0 && newActiveId === 'home') {
      // Just home tab - clean URL
      router.replace('/dashboard', { scroll: false });
    } else {
      // Build URL with tab state
      const params = new URLSearchParams();
      if (openTabIds.length > 0) {
        params.set('tab', openTabIds.join(','));
      }
      if (newActiveId !== 'home') {
        params.set('active', newActiveId);
      }
      router.replace(`/dashboard?${params.toString()}`, { scroll: false });
    }
  }, [router]);

  // Open a tab (or focus if already open)
  const openTab = useCallback((
    type: TabType,
    title: string,
    resourceId?: string,
    data?: Record<string, unknown>
  ) => {
    const tabId = resourceId ? `${type}_${resourceId}` : type;

    setTabs(currentTabs => {
      // Check if tab already exists
      const existingTab = currentTabs.find(t => t.id === tabId);
      if (existingTab) {
        // Just activate it
        setActiveTabId(tabId);
        syncUrlWithTabs(tabId, currentTabs);
        return currentTabs;
      }

      // Check max tabs
      if (currentTabs.length >= MAX_TABS) {
        // Close oldest non-home, non-active tab
        const tabToClose = currentTabs.find(t => t.closeable && t.id !== activeTabId);
        if (tabToClose) {
          const filtered = currentTabs.filter(t => t.id !== tabToClose.id);
          const newTab = createTab(type, title, resourceId, data);
          const newTabs = [...filtered, newTab];
          setActiveTabId(tabId);
          syncUrlWithTabs(tabId, newTabs);
          return newTabs;
        }
      }

      // Add new tab
      const newTab = createTab(type, title, resourceId, data);
      const newTabs = [...currentTabs, newTab];
      setActiveTabId(tabId);
      syncUrlWithTabs(tabId, newTabs);
      return newTabs;
    });
  }, [activeTabId, syncUrlWithTabs]);

  // Close a tab
  const closeTab = useCallback((tabId: string) => {
    setTabs(currentTabs => {
      const tab = currentTabs.find(t => t.id === tabId);
      if (!tab || !tab.closeable) return currentTabs;

      const newTabs = currentTabs.filter(t => t.id !== tabId);

      // If closing active tab, switch to previous or home
      if (tabId === activeTabId) {
        const currentIndex = currentTabs.findIndex(t => t.id === tabId);
        const newActiveIndex = Math.max(0, currentIndex - 1);
        const newActiveId = newTabs[newActiveIndex]?.id || 'home';
        setActiveTabId(newActiveId);
        syncUrlWithTabs(newActiveId, newTabs);
      } else {
        syncUrlWithTabs(activeTabId, newTabs);
      }

      return newTabs;
    });
  }, [activeTabId, syncUrlWithTabs]);

  // Set active tab
  const setActiveTabFn = useCallback((tabId: string) => {
    if (tabs.some(t => t.id === tabId)) {
      setActiveTabId(tabId);
      syncUrlWithTabs(tabId, tabs);
    }
  }, [tabs, syncUrlWithTabs]);

  // Update tab status
  const updateTabStatus = useCallback((tabId: string, status: TabStatus) => {
    setTabs(currentTabs =>
      currentTabs.map(t => t.id === tabId ? { ...t, status } : t)
    );
  }, []);

  // Update tab data
  const updateTabData = useCallback((tabId: string, data: Record<string, unknown>) => {
    setTabs(currentTabs =>
      currentTabs.map(t => t.id === tabId ? { ...t, data: { ...t.data, ...data } } : t)
    );
  }, []);

  // Reorder tabs (for drag and drop)
  const reorderTabs = useCallback((fromIndex: number, toIndex: number) => {
    setTabs(currentTabs => {
      const newTabs = [...currentTabs];
      const [moved] = newTabs.splice(fromIndex, 1);
      newTabs.splice(toIndex, 0, moved);
      return newTabs;
    });
  }, []);

  // Find tab by resource
  const findTabByResource = useCallback((type: TabType, resourceId: string) => {
    const tabId = `${type}_${resourceId}`;
    return tabs.find(t => t.id === tabId);
  }, [tabs]);

  // Check if tab is open
  const isTabOpen = useCallback((type: TabType, resourceId?: string) => {
    const tabId = resourceId ? `${type}_${resourceId}` : type;
    return tabs.some(t => t.id === tabId);
  }, [tabs]);

  const value: TabContextValue = {
    tabs,
    activeTabId,
    activeTab,
    tpContext,
    openTab,
    closeTab,
    setActiveTab: setActiveTabFn,
    updateTabStatus,
    updateTabData,
    reorderTabs,
    findTabByResource,
    isTabOpen,
  };

  return (
    <TabContext.Provider value={value}>
      {children}
    </TabContext.Provider>
  );
}

export function useTabs() {
  const context = useContext(TabContext);
  if (!context) {
    throw new Error('useTabs must be used within a TabProvider');
  }
  return context;
}
