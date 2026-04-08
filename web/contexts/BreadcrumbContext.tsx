'use client';

/**
 * BreadcrumbContext — Global breadcrumb state for the header bar.
 *
 * Pages set breadcrumb segments via `setBreadcrumb()`. The header reads them.
 * Prefer href for route-backed navigation. Use onClick only for local UI
 * state that is not URL-addressable.
 *
 * Examples:
 *   Home page:           [] (empty — just "yarnnn")
 *   Agents overview:     [] (empty — toggle bar shows "Agents")
 *   Agent selected:      [{ label: "Agents", href: "/agents" }, { label: "Competitive Intelligence", href: "/agents?agent=..." }]
 *   Context / domain:    [{ label: "Context", href: "/context" }, { label: "Competitors", href: "/context?path=..." }]
 */

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

export interface BreadcrumbSegment {
  label: string;
  href?: string;
  onClick?: () => void;
  kind?: 'surface' | 'entity' | 'task' | 'agent' | 'context' | 'output' | 'artifact';
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
