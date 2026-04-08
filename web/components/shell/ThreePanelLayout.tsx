'use client';

/**
 * ThreePanelLayout — Shared shell used by all authenticated surfaces.
 *
 * SURFACE-ARCHITECTURE.md v9 (ADR-167): leftPanel is now optional. Pages that
 * use the list/detail collapse pattern (Work, Agents) omit the left panel —
 * the center surface owns the full width and the breadcrumb (b033513) drives
 * navigation. Pages that legitimately need a tree nav (/context) still pass
 * a leftPanel.
 *
 * Structure (with leftPanel):
 *   Left panel | Center content | Right chat (FAB-overlay, default closed)
 *
 * Structure (without leftPanel):
 *   Center content (full width) | Right chat (FAB-overlay, default closed)
 */

import { useState, type ReactNode } from 'react';
import { X } from 'lucide-react';
import { ChatPanel, type ChatPanelProps } from '@/components/tp/ChatPanel';

export interface ThreePanelLayoutProps {
  /**
   * Left panel content and configuration. OPTIONAL (ADR-167).
   * Omit for list/detail surfaces — the center surface owns the full width.
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

  /** Chat panel configuration. Omit to disable chat entirely (e.g., Activity page). */
  chat?: {
    /** Surface override for TP context */
    surfaceOverride?: ChatPanelProps['surfaceOverride'];
    /** Plus menu actions */
    plusMenuActions: ChatPanelProps['plusMenuActions'];
    /** Placeholder text for chat input */
    placeholder?: string;
    /** Empty state content */
    emptyState?: ReactNode;
    /** Whether to show command picker */
    showCommandPicker?: boolean;
    /** Context subtitle shown next to "TP" in chat header */
    contextLabel?: string;
    /** Initial open state (default: false — FAB only) */
    defaultOpen?: boolean;
    /** Chat panel width in px (default: 380) */
    width?: number;
  };
}

export function ThreePanelLayout({
  leftPanel,
  children,
  chat,
}: ThreePanelLayoutProps) {
  const [panelOpen, setPanelOpen] = useState(true);
  const [chatOpen, setChatOpen] = useState(chat?.defaultOpen ?? false);
  const leftWidth = leftPanel?.width ?? 280;
  const chatWidth = chat?.width ?? 380;

  return (
    <div className="flex h-full overflow-hidden">
      {/* ── Left Panel (ADR-167: optional) ── */}
      {leftPanel && (
        panelOpen ? (
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
      <div className="flex-1 min-w-0 flex flex-col bg-background">
        {children}
      </div>

      {/* ── Right: Chat Panel or FAB ── */}
      {chat && chatOpen && (
        <div
          className="shrink-0 border-l border-border flex flex-col bg-background overflow-hidden"
          style={{ width: chatWidth }}
        >
          <div className="flex items-center justify-between px-3 py-2.5 border-b border-border bg-background z-10 shrink-0">
            <div className="flex items-center gap-2">
              <img src="/assets/logos/circleonly_yarnnn_1.svg" alt="" className="w-5 h-5" />
              <span className="text-xs font-medium">TP</span>
              {chat.contextLabel && (
                <span className="text-[10px] text-muted-foreground/50 truncate max-w-[160px]">
                  · {chat.contextLabel}
                </span>
              )}
            </div>
            <button
              onClick={() => setChatOpen(false)}
              className="p-1.5 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="flex-1 min-h-0">
            <ChatPanel
              surfaceOverride={chat.surfaceOverride}
              plusMenuActions={chat.plusMenuActions}
              placeholder={chat.placeholder}
              emptyState={chat.emptyState}
              showCommandPicker={chat.showCommandPicker}
            />
          </div>
        </div>
      )}

      {chat && !chatOpen && (
        <button
          onClick={() => setChatOpen(true)}
          className="fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full shadow-lg hover:shadow-xl hover:scale-110 transition-all flex items-center justify-center group"
          title="Chat with TP"
        >
          <img
            src="/assets/logos/circleonly_yarnnn_1.svg"
            alt="yarnnn"
            className="w-12 h-12 transition-transform duration-500 group-hover:rotate-180"
          />
        </button>
      )}
    </div>
  );
}
