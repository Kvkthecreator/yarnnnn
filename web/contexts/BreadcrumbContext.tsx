'use client';

/**
 * BreadcrumbContext — Global breadcrumb state for the header bar.
 *
 * Pages set breadcrumb segments via `setBreadcrumb()`. The header reads them.
 * Each segment has a label and optional onClick handler (for navigation).
 *
 * Examples:
 *   Home page:           [] (empty — just "yarnnn")
 *   Agents overview:     [] (empty — toggle bar shows "Agents")
 *   Agent selected:      [{ label: "Competitive Intelligence" }]
 *   Agent browsing file: [{ label: "Competitive Intelligence", onClick }, { label: "cursor" }]
 *   Context / domain:    [{ label: "Competitors", onClick }, { label: "cursor" }]
 */

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

export interface BreadcrumbSegment {
  label: string;
  onClick?: () => void;
}

interface BreadcrumbContextValue {
  segments: BreadcrumbSegment[];
  setBreadcrumb: (segments: BreadcrumbSegment[]) => void;
  clearBreadcrumb: () => void;
}

const BreadcrumbCtx = createContext<BreadcrumbContextValue>({
  segments: [],
  setBreadcrumb: () => {},
  clearBreadcrumb: () => {},
});

export function BreadcrumbProvider({ children }: { children: ReactNode }) {
  const [segments, setSegments] = useState<BreadcrumbSegment[]>([]);

  const setBreadcrumb = useCallback((segs: BreadcrumbSegment[]) => {
    setSegments(segs);
  }, []);

  const clearBreadcrumb = useCallback(() => {
    setSegments([]);
  }, []);

  return (
    <BreadcrumbCtx.Provider value={{ segments, setBreadcrumb, clearBreadcrumb }}>
      {children}
    </BreadcrumbCtx.Provider>
  );
}

export function useBreadcrumb() {
  return useContext(BreadcrumbCtx);
}
