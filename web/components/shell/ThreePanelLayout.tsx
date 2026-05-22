'use client';

/**
 * ThreePanelLayout — shared shell used by /agents /context /cadence.
 *
 * SURFACE-ARCHITECTURE.md v9 (ADR-167): leftPanel is optional. Pages
 * that use list/detail collapse (Work, Agents) omit the left panel —
 * the center surface owns the full width. Pages that legitimately need
 * a tree nav (/context) still pass a leftPanel.
 *
 * D16 (2026-05-22, ADR-297): the prior `conversation` prop + right-
 * panel ConversationPanel mount + FAB + useSuppressShellComposer
 * machinery are ALL DELETED. The universal chat affordance moved to
 * the shell via ChatDrawerSurface (FAB at viewport bottom-center +
 * slide-over drawer). ThreePanelLayout shrinks to its load-bearing
 * minimum: an optional left panel + the center children area.
 *
 * Structure (with leftPanel):
 *   Left panel (resizable) | Center content
 *
 * Structure (without leftPanel):
 *   Center content (full width)
 *
 * Resize: the left panel has a drag handle that persists width to
 * localStorage. IDE-style — grab the vertical edge to widen/narrow.
 */

import { useState, useEffect, useCallback, useRef, type ReactNode } from 'react';
import { X } from 'lucide-react';

/** Returns true when viewport width < 640px (Tailwind sm breakpoint). */
function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 639px)');
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);
  return isMobile;
}

const LEFT_WIDTH_KEY = 'yarnnn:left-panel-width';
const LEFT_MIN = 200;
const LEFT_MAX = 560;

function loadStoredWidth(key: string, fallback: number, min: number, max: number): number {
  if (typeof window === 'undefined') return fallback;
  const raw = window.localStorage.getItem(key);
  if (!raw) return fallback;
  const n = parseInt(raw, 10);
  if (Number.isNaN(n)) return fallback;
  return Math.max(min, Math.min(max, n));
}

export interface ThreePanelLayoutProps {
  /**
   * Left panel content and configuration. OPTIONAL (ADR-167).
   * Omit for list/detail surfaces — the center surface owns the
   * full width.
   */
  leftPanel?: {
    content: ReactNode;
    /** Header title shown above the panel */
    title: string;
    /** Optional subtitle below the title */
    subtitle?: string;
    /** Panel width in px (default: 280) */
    width?: number;
    /** Icon component shown when collapsed */
    collapsedIcon: ReactNode;
    /** Tooltip for collapsed icon button */
    collapsedTitle?: string;
  };

  /** Center panel content */
  children: ReactNode;
}

export function ThreePanelLayout({ leftPanel, children }: ThreePanelLayoutProps) {
  const isMobile = useIsMobile();
  const [panelOpen, setPanelOpen] = useState(true);

  // Left-panel width — hydrated from localStorage on mount.
  const [leftWidth, setLeftWidth] = useState(leftPanel?.width ?? 280);

  useEffect(() => {
    setLeftWidth(loadStoredWidth(LEFT_WIDTH_KEY, leftPanel?.width ?? 280, LEFT_MIN, LEFT_MAX));
    // Read once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Drag-to-resize for left panel.
  const leftDragging = useRef(false);
  const onLeftMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    leftDragging.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!leftDragging.current) return;
      const next = Math.max(LEFT_MIN, Math.min(LEFT_MAX, e.clientX));
      setLeftWidth(next);
    };
    const onUp = () => {
      if (!leftDragging.current) return;
      leftDragging.current = false;
      try {
        window.localStorage.setItem(LEFT_WIDTH_KEY, String(leftWidth));
      } catch {}
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [leftWidth]);

  return (
    <div className="flex h-full overflow-hidden">
      {/* ── Left Panel (ADR-167: optional, hidden on mobile) ── */}
      {leftPanel && !isMobile && (
        panelOpen ? (
          <>
            <div
              className="shrink-0 border-r border-border flex flex-col bg-background"
              style={{ width: leftWidth }}
            >
              <div className="flex items-center justify-between px-3 py-2 border-b border-border shrink-0">
                <div>
                  <p className="text-sm font-medium text-foreground">{leftPanel.title}</p>
                  {leftPanel.subtitle && (
                    <p className="text-[11px] text-muted-foreground">{leftPanel.subtitle}</p>
                  )}
                </div>
                <button
                  onClick={() => setPanelOpen(false)}
                  className="p-1 text-muted-foreground/40 hover:text-muted-foreground rounded"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
              {leftPanel.content}
            </div>
            {/* Resize handle */}
            <div
              onMouseDown={onLeftMouseDown}
              className="w-1 shrink-0 cursor-col-resize bg-transparent hover:bg-primary/20 active:bg-primary/30 transition-colors"
              title="Drag to resize"
            />
          </>
        ) : (
          <div className="w-10 shrink-0 border-r border-border flex flex-col items-center py-2 gap-2 bg-background">
            <button
              onClick={() => setPanelOpen(true)}
              className="p-2 rounded-md text-muted-foreground/50 hover:text-foreground hover:bg-muted transition-colors"
              title={leftPanel.collapsedTitle ?? leftPanel.title}
            >
              {leftPanel.collapsedIcon}
            </button>
          </div>
        )
      )}

      {/* ── Center Content ── */}
      <div className="flex-1 min-w-0 min-h-0 flex flex-col overflow-y-auto bg-background">
        {children}
      </div>
    </div>
  );
}
