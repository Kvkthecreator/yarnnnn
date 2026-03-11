'use client';

/**
 * Workspace Layout — Persistent Panel Architecture
 *
 * Shared layout for all chat-first workspace pages:
 * - /dashboard (global TP — no deliverable scope)
 * - /deliverables/[id] (deliverable workspace — scoped TP)
 *
 * Layout (≥ lg):
 * - Header: identity chip + breadcrumb + controls + panel toggle
 * - Body: chat (left) | draggable divider | panel (right)
 * - Default split: 50/50. Draggable. Min 30% each side.
 *
 * Layout (< lg):
 * - Header + full-width chat
 * - Panel slides from right as overlay (480px / full-width mobile)
 *
 * Inspired by Claude Cowork's persistent right panel with resizable split.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { X, PanelRight, PanelRightClose } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface WorkspacePanelTab {
  id: string;
  label: string;
  content: React.ReactNode;
}

export interface WorkspaceIdentity {
  /** Icon element shown in the identity chip */
  icon: React.ReactNode;
  /** Primary label — "Thinking Partner" or deliverable title */
  label: string;
  /** Optional badge shown next to label — e.g. mode badge "[Rec]" */
  badge?: React.ReactNode;
}

interface WorkspaceLayoutProps {
  /** Identity chip shown in the header — differentiates global TP from deliverable workspace */
  identity: WorkspaceIdentity;
  /** Optional breadcrumb/back nav shown to the left of the identity chip */
  breadcrumb?: React.ReactNode;
  /** Optional controls shown to the right of the header (pause, settings, etc.) */
  headerControls?: React.ReactNode;
  /** The chat area — messages + input bar */
  children: React.ReactNode;
  /** Panel tabs. If empty, panel trigger is hidden. */
  panelTabs?: WorkspacePanelTab[];
  /** Default open state for the panel (default: true — panel visible by default) */
  panelDefaultOpen?: boolean;
  /** Controlled active tab (parent can drive tab selection) */
  activeTabId?: string;
  /** Callback when active tab changes */
  onActiveTabChange?: (tabId: string) => void;
}

// Panel width as percentage of container. Clamped between 25-65%.
const DEFAULT_PANEL_PCT = 50;
const MIN_PANEL_PCT = 25;
const MAX_PANEL_PCT = 65;

export function WorkspaceLayout({
  identity,
  breadcrumb,
  headerControls,
  children,
  panelTabs = [],
  panelDefaultOpen = true,
  activeTabId,
  onActiveTabChange,
}: WorkspaceLayoutProps) {
  const [panelOpen, setPanelOpen] = useState(panelDefaultOpen);
  const [internalActiveTab, setInternalActiveTab] = useState<string>(panelTabs[0]?.id ?? '');
  const [panelPct, setPanelPct] = useState(DEFAULT_PANEL_PCT);
  const [isDragging, setIsDragging] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);

  // Support controlled or uncontrolled active tab
  const activeTab = activeTabId ?? internalActiveTab;
  const setActiveTab = useCallback((tabId: string) => {
    setInternalActiveTab(tabId);
    onActiveTabChange?.(tabId);
  }, [onActiveTabChange]);

  const hasPanelTabs = panelTabs.length > 0;
  const activePanelContent = panelTabs.find((t) => t.id === activeTab)?.content;

  const closePanel = useCallback(() => setPanelOpen(false), []);

  // Close overlay panel on Escape key (only for mobile/overlay mode)
  useEffect(() => {
    if (!panelOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closePanel();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [panelOpen, closePanel]);

  // Drag-to-resize handler
  const handleDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const body = bodyRef.current;
      if (!body) return;
      const rect = body.getBoundingClientRect();
      const offsetFromRight = rect.right - e.clientX;
      const pct = (offsetFromRight / rect.width) * 100;
      setPanelPct(Math.max(MIN_PANEL_PCT, Math.min(MAX_PANEL_PCT, pct)));
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    // Prevent text selection while dragging
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'col-resize';

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };
  }, [isDragging]);

  // Shared tab bar
  const tabBar = (
    <div className="flex items-center border-b border-border shrink-0">
      <div className="flex-1 flex overflow-x-auto">
        {panelTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'px-3 py-2.5 text-xs font-medium whitespace-nowrap transition-colors border-b-2',
              activeTab === tab.id
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {/* Close button: only visible on < lg (overlay mode) */}
      <button
        onClick={closePanel}
        className="lg:hidden p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-md mx-1 shrink-0 transition-colors"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );

  return (
    <div className="h-full flex flex-col">
      {/* Header — CSS grid: left (breadcrumb) | center (identity) | right (controls) */}
      <div className="grid grid-cols-[1fr_auto_1fr] items-center px-4 py-3 border-b border-border shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          {breadcrumb}
        </div>

        {/* Center: identity chip */}
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-muted-foreground shrink-0">{identity.icon}</span>
          <span className="font-medium truncate">{identity.label}</span>
          {identity.badge && <span className="shrink-0">{identity.badge}</span>}
        </div>

        <div className="flex items-center gap-2 shrink-0 justify-end">
          {headerControls}
          {hasPanelTabs && (
            <button
              onClick={() => setPanelOpen(!panelOpen)}
              className={cn(
                'flex items-center gap-1.5 p-2 rounded-md transition-colors text-muted-foreground hover:text-foreground hover:bg-muted',
                panelOpen && 'bg-muted text-foreground'
              )}
              title={panelOpen ? 'Close panel' : 'Open panel'}
            >
              {panelOpen ? (
                <PanelRightClose className="w-4 h-4" />
              ) : (
                <PanelRight className="w-4 h-4" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Body: chat + panel */}
      <div ref={bodyRef} className="flex-1 flex min-h-0 overflow-hidden">
        {/* Chat area — takes remaining space */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {children}
        </div>

        {/* Desktop persistent panel (≥ lg): inline, percentage-based width, resizable */}
        {hasPanelTabs && panelOpen && (
          <>
            {/* Drag handle */}
            <div
              onMouseDown={handleDragStart}
              className={cn(
                'hidden lg:flex items-center justify-center w-1 cursor-col-resize hover:bg-primary/20 active:bg-primary/30 transition-colors shrink-0',
                isDragging && 'bg-primary/30'
              )}
            >
              <div className="w-px h-8 bg-border rounded-full" />
            </div>

            {/* Panel */}
            <div
              className="hidden lg:flex lg:flex-col border-l border-border bg-background shrink-0"
              style={{ width: `${panelPct}%` }}
            >
              {tabBar}
              <div className="flex-1 overflow-y-auto">
                {activePanelContent}
              </div>
            </div>
          </>
        )}

        {/* Mobile/tablet overlay panel (< lg): fixed, slides from right */}
        {hasPanelTabs && (
          <>
            {/* Backdrop — only on < lg */}
            <div
              className={cn(
                'lg:hidden fixed inset-0 z-40 bg-black/20 transition-opacity duration-300',
                panelOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
              )}
              onClick={closePanel}
            />

            {/* Overlay panel */}
            <div
              className={cn(
                'lg:hidden fixed top-0 right-0 bottom-0 z-50 flex flex-col bg-background border-l border-border shadow-xl',
                'w-full sm:w-[480px]',
                'transition-transform duration-300 ease-out',
                panelOpen ? 'translate-x-0' : 'translate-x-full'
              )}
            >
              {tabBar}
              <div className="flex-1 overflow-y-auto">
                {activePanelContent}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
