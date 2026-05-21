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
 *   Left panel | Center content | Right Conversation panel (resizable, default closed)
 *
 * Structure (without leftPanel):
 *   Center content (full width) | Right Conversation panel (resizable, default closed)
 *
 * Resize: both the left panel and the conversation panel have a drag
 * handle that persists width to localStorage (per panel role). IDE-style
 * — grab the vertical edge to widen/narrow.
 *
 * ADR-289 Phase 2: `chat` prop renamed to `conversation` and the inner
 * mount switched from FeedPanel to ConversationPanel (scoped to
 * `pulse='addressed'`). The localStorage width key is preserved as
 * `yarnnn:chat-panel-width` so existing operator widths survive.
 */

import { useState, useEffect, useCallback, useRef, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { X } from 'lucide-react';
import { ConversationPanel, type ConversationPanelProps } from '@/components/tp/ConversationPanel';
import { useSuppressShellComposer } from './ShellChromeContext';

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

const CHAT_WIDTH_KEY = 'yarnnn:chat-panel-width';
const LEFT_WIDTH_KEY = 'yarnnn:left-panel-width';
const CHAT_MIN = 320;
const CHAT_MAX = 720;
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

  /**
   * Conversation panel configuration (ADR-289 D10 rename from `chat`).
   * Mounts a ConversationPanel — chat-shaped exchange between operator
   * and counterpart, scoped to `pulse='addressed'`. Omit to disable.
   */
  conversation?: {
    /** Surface override for YARNNN context */
    surfaceOverride?: ConversationPanelProps['surfaceOverride'];
    /** Prefill the input from the parent surface without auto-sending */
    draftSeed?: ConversationPanelProps['draftSeed'];
    /** Plus menu actions */
    plusMenuActions: ConversationPanelProps['plusMenuActions'];
    /** Placeholder text for input */
    placeholder?: string;
    /** Empty state content */
    emptyState?: ReactNode;
    /** Whether to show command picker */
    showCommandPicker?: boolean;
    /** Context subtitle shown next to "yarnnn" in panel header */
    contextLabel?: string;
    /** Initial open state (default: false — FAB only) */
    defaultOpen?: boolean;
    /** Increment to force the conversation panel open from the parent surface */
    openSignal?: number;
    /** Conversation panel width in px (default: 380) */
    width?: number;
  };
}

/**
 * Tiny zero-render component that always calls
 * useSuppressShellComposer. Mounted by ThreePanelLayout when its
 * `conversation` prop is set, so the shell-bottom composer hides
 * while a per-surface ConversationPanel is owning the chat affordance.
 * Phase C safer-shape per ADR-297 D11.
 */
function ShellComposerSuppressor() {
  useSuppressShellComposer();
  return null;
}

export function ThreePanelLayout({
  leftPanel,
  children,
  conversation,
}: ThreePanelLayoutProps) {
  const isMobile = useIsMobile();
  const router = useRouter();
  const [panelOpen, setPanelOpen] = useState(true);
  // Start closed to avoid SSR/hydration mismatch. On desktop with defaultOpen=true,
  // we open after mount. On mobile we never open — user reaches TP via Chat nav.
  const [chatOpen, setChatOpen] = useState(false);

  useEffect(() => {
    if (isMobile) {
      // Force-close the panel if viewport shrinks to mobile (e.g. browser resize).
      setChatOpen(false);
    } else if (conversation?.defaultOpen) {
      // On desktop with defaultOpen, open once after mount.
      setChatOpen(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isMobile]);

  // Width state — hydrated from localStorage on mount to avoid SSR mismatch.
  const [leftWidth, setLeftWidth] = useState(leftPanel?.width ?? 280);
  const [chatWidth, setChatWidth] = useState(conversation?.width ?? 380);
  const previousChatOpenSignal = useRef<number | undefined>(conversation?.openSignal);

  useEffect(() => {
    setLeftWidth(loadStoredWidth(LEFT_WIDTH_KEY, leftPanel?.width ?? 280, LEFT_MIN, LEFT_MAX));
    setChatWidth(loadStoredWidth(CHAT_WIDTH_KEY, conversation?.width ?? 380, CHAT_MIN, CHAT_MAX));
    // Read once on mount — defaults are stable per page render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (conversation?.openSignal === undefined) {
      previousChatOpenSignal.current = undefined;
      return;
    }
    if (previousChatOpenSignal.current === undefined) {
      previousChatOpenSignal.current = conversation.openSignal;
      return;
    }
    if (conversation.openSignal !== previousChatOpenSignal.current) {
      previousChatOpenSignal.current = conversation.openSignal;
      setChatOpen(true);
    }
  }, [conversation?.openSignal]);

  // Drag-to-resize for left panel (drag right edge → width grows)
  const leftDragging = useRef(false);
  const onLeftMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    leftDragging.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  // Drag-to-resize for chat panel (drag left edge → width grows leftward)
  const chatDragging = useRef(false);
  const onChatMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    chatDragging.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (leftDragging.current) {
        const next = Math.max(LEFT_MIN, Math.min(LEFT_MAX, e.clientX));
        setLeftWidth(next);
      } else if (chatDragging.current) {
        const next = Math.max(CHAT_MIN, Math.min(CHAT_MAX, window.innerWidth - e.clientX));
        setChatWidth(next);
      }
    };
    const onUp = () => {
      if (leftDragging.current) {
        leftDragging.current = false;
        try { window.localStorage.setItem(LEFT_WIDTH_KEY, String(leftWidth)); } catch {}
      }
      if (chatDragging.current) {
        chatDragging.current = false;
        try { window.localStorage.setItem(CHAT_WIDTH_KEY, String(chatWidth)); } catch {}
      }
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [leftWidth, chatWidth]);

  return (
    <div className="flex h-full overflow-hidden">
      {/* ADR-297 D11 Phase C safer-shape: suppress shell-bottom composer
          while this surface owns its own ConversationPanel. */}
      {conversation && <ShellComposerSuppressor />}

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
            {/* Resize handle for left panel */}
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

      {/* ── Right: Conversation Panel (only renders on non-mobile; on mobile chatOpen stays false) ── */}
      {conversation && chatOpen && (
        <>
          {/* Resize handle for conversation panel */}
          <div
            onMouseDown={onChatMouseDown}
            className="w-1 shrink-0 cursor-col-resize bg-transparent hover:bg-primary/20 active:bg-primary/30 transition-colors"
            title="Drag to resize"
          />
          <div
            className="shrink-0 border-l border-border flex flex-col bg-background overflow-hidden"
            style={{ width: chatWidth }}
          >
            <div className="flex items-center justify-between px-3 py-2.5 border-b border-border bg-background z-10 shrink-0">
              <div className="flex items-center gap-2">
                <img src="/assets/logos/circleonly_yarnnn_1.svg" alt="" className="w-5 h-5" />
                <span className="text-sm font-brand">yarnnn</span>
                {conversation.contextLabel && (
                  <span className="text-[10px] text-muted-foreground/50 truncate max-w-[160px]">
                    · {conversation.contextLabel}
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
              <ConversationPanel
                surfaceOverride={conversation.surfaceOverride}
                draftSeed={conversation.draftSeed}
                plusMenuActions={conversation.plusMenuActions}
                placeholder={conversation.placeholder}
                emptyState={conversation.emptyState}
                showCommandPicker={conversation.showCommandPicker}
              />
            </div>
          </div>
        </>
      )}

      {/* FAB — always visible when conversation panel is closed.
          Desktop: opens the inline conversation panel.
          Mobile: navigates to /feed (panel layout doesn't work at <640px). */}
      {conversation && !chatOpen && (
        <button
          onClick={() => isMobile ? router.push('/feed') : setChatOpen(true)}
          className="fixed right-4 z-50 w-12 h-12 rounded-full shadow-lg hover:shadow-xl hover:scale-110 transition-all flex items-center justify-center group sm:right-6"
          style={{ bottom: 'max(1.5rem, env(safe-area-inset-bottom, 0px) + 0.75rem)' }}
          title="Chat with YARNNN"
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
