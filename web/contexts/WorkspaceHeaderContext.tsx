'use client';

/**
 * WorkspaceHeaderContext
 *
 * Allows workspace pages (dashboard, deliverable detail) to inject
 * header content into the AuthenticatedLayout top bar.
 */

import { createContext, useContext, useState, type ReactNode } from 'react';

interface WorkspaceHeaderContextValue {
  /** Current workspace header content, or null if no workspace is active */
  header: ReactNode | null;
  /** Set workspace header content (call with null to clear) */
  setHeader: (node: ReactNode | null) => void;
}

const WorkspaceHeaderContext = createContext<WorkspaceHeaderContextValue | null>(null);

export function WorkspaceHeaderProvider({ children }: { children: ReactNode }) {
  const [header, setHeader] = useState<ReactNode | null>(null);
  return (
    <WorkspaceHeaderContext.Provider value={{ header, setHeader }}>
      {children}
    </WorkspaceHeaderContext.Provider>
  );
}

export function useWorkspaceHeader() {
  const ctx = useContext(WorkspaceHeaderContext);
  if (!ctx) throw new Error('useWorkspaceHeader must be used within WorkspaceHeaderProvider');
  return ctx;
}
