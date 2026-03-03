'use client';

/**
 * ADR-091: Workspace Layout & Navigation Architecture
 *
 * Shared layout for all chat-first workspace pages:
 * - /dashboard (global TP — no deliverable scope)
 * - /deliverables/[id] (deliverable workspace — scoped TP)
 *
 * Layout:
 * - Header: identity chip + breadcrumb + controls
 * - Left: chat area (dominant, full height)
 * - Right: collapsible panel with tabs (desktop only)
 *
 * The identity chip is the user's primary signal for "which agent am I talking to."
 * It must always be visible and never ambiguous.
 */

import { useState } from 'react';
import { X, PanelRight } from 'lucide-react';
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
  /** Right panel tabs. If empty, panel toggle is hidden. */
  panelTabs?: WorkspacePanelTab[];
  /** Default open state for the right panel */
  panelDefaultOpen?: boolean;
}

export function WorkspaceLayout({
  identity,
  breadcrumb,
  headerControls,
  children,
  panelTabs = [],
  panelDefaultOpen = false,
}: WorkspaceLayoutProps) {
  const [panelOpen, setPanelOpen] = useState(panelDefaultOpen);
  const [activeTab, setActiveTab] = useState<string>(panelTabs[0]?.id ?? '');

  const hasPanelTabs = panelTabs.length > 0;
  const activePanelContent = panelTabs.find((t) => t.id === activeTab)?.content;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          {breadcrumb && (
            <>
              {breadcrumb}
              <span className="text-border text-sm select-none">·</span>
            </>
          )}
          {/* Identity chip */}
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-muted-foreground shrink-0">{identity.icon}</span>
            <span className="font-medium truncate">{identity.label}</span>
            {identity.badge && <span className="shrink-0">{identity.badge}</span>}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {headerControls}
          {hasPanelTabs && (
            <button
              onClick={() => setPanelOpen(!panelOpen)}
              className={cn(
                'hidden md:flex items-center gap-1.5 p-2 rounded-md transition-colors text-muted-foreground hover:text-foreground hover:bg-muted',
                panelOpen && 'bg-muted text-foreground'
              )}
              title={panelOpen ? 'Close panel' : 'Open panel'}
            >
              <PanelRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Body: chat + optional right panel */}
      <div className="flex-1 flex overflow-hidden">
        {/* Chat area */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {children}
        </div>

        {/* Right panel — desktop only */}
        {hasPanelTabs && (
          <div
            className={cn(
              'hidden md:flex flex-col border-l border-border bg-background transition-all duration-200',
              panelOpen ? 'w-80' : 'w-0 overflow-hidden'
            )}
          >
            {panelOpen && (
              <>
                {/* Panel tab bar */}
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
                  <button
                    onClick={() => setPanelOpen(false)}
                    className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-md mx-1 shrink-0 transition-colors"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Panel tab content */}
                <div className="flex-1 overflow-y-auto">
                  {activePanelContent}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
