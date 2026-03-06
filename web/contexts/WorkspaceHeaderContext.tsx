'use client';

/**
 * WorkspaceHeaderContext
 *
 * Allows workspace pages (dashboard, deliverable detail) to inject
 * header content into the AuthenticatedLayout top bar.
 * Also exposes nav dropdown toggle so workspace headers can include
 * the navigation chevron on their identity chip.
 */

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

interface WorkspaceHeaderContextValue {
  /** Current workspace header content, or null if no workspace is active */
  header: ReactNode | null;
  /** Set workspace header content (call with null to clear) */
  setHeader: (node: ReactNode | null) => void;
  /** Whether the nav dropdown is open */
  navOpen: boolean;
  /** Toggle the nav dropdown */
  toggleNav: () => void;
  /** Close the nav dropdown */
  closeNav: () => void;
}

const WorkspaceHeaderContext = createContext<WorkspaceHeaderContextValue | null>(null);

export function WorkspaceHeaderProvider({ children }: { children: ReactNode }) {
  const [header, setHeader] = useState<ReactNode | null>(null);
  const [navOpen, setNavOpen] = useState(false);
  const toggleNav = useCallback(() => setNavOpen((prev) => !prev), []);
  const closeNav = useCallback(() => setNavOpen(false), []);
  return (
    <WorkspaceHeaderContext.Provider value={{ header, setHeader, navOpen, toggleNav, closeNav }}>
      {children}
    </WorkspaceHeaderContext.Provider>
  );
}

export function useWorkspaceHeader() {
  const ctx = useContext(WorkspaceHeaderContext);
  if (!ctx) throw new Error('useWorkspaceHeader must be used within WorkspaceHeaderProvider');
  return ctx;
}
