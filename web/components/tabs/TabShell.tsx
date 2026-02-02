'use client';

/**
 * ADR-022: Tab-Based Supervision Architecture
 *
 * TabShell - the main layout wrapper for the tab-based UI.
 * Combines: Header, TabBar, Content Area, PersistentTP
 */

import { ReactNode } from 'react';
import { TabBar } from './TabBar';
import { PersistentTP } from './PersistentTP';
import { useTabs } from '@/contexts/TabContext';

interface TabShellProps {
  header?: ReactNode;
  children: ReactNode;
}

export function TabShell({ header, children }: TabShellProps) {
  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header (logo, user menu, etc.) */}
      {header && (
        <div className="shrink-0">
          {header}
        </div>
      )}

      {/* Tab bar */}
      <div className="shrink-0">
        <TabBar />
      </div>

      {/* Content area - renders active tab */}
      <div className="flex-1 overflow-hidden">
        {children}
      </div>

      {/* Persistent TP layer */}
      <div className="shrink-0">
        <PersistentTP />
      </div>
    </div>
  );
}
