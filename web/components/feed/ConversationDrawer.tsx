/**
 * ConversationDrawer — slide-over Conversation surface on /feed (ADR-289).
 *
 * The Feed surface (FeedTimeline) is the operations timeline; engaging
 * a conversation opens this drawer over the timeline. The drawer hosts
 * a ConversationPanel scoped to `pulse='addressed'` exchanges so the
 * operator sees a clean chat-shaped view of the dialogue without the
 * autonomous-wake noise that lives in the timeline.
 *
 * Layout (per ADR-289 design lock-in):
 *   - Desktop: slide-over from the right, dims the timeline behind.
 *     Default width 380px, resizable via drag-handle (matches the
 *     right-panel ConversationPanel pattern on /work, /agents, etc).
 *   - Mobile (<640px): full-screen takeover, no timeline visible.
 *     Same component, breakpoint-conditional chrome.
 *
 * Autonomous wakes that fire while the drawer is open emit narrative
 * rows into session_messages as usual; the FeedTimeline behind picks
 * them up via the realtime subscription. The drawer itself does not
 * surface autonomous activity — that's the noise problem ADR-289
 * structurally solves. Operator sees the new wakes when they close the
 * drawer and return to the full timeline view.
 */

'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { X } from 'lucide-react';
import { useReviewerPersona } from '@/lib/reviewer-persona';
import { ConversationPanel } from '@/components/tp/ConversationPanel';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';
import { cn } from '@/lib/utils';

const DRAWER_WIDTH_KEY = 'yarnnn:conversation-drawer-width';
const DRAWER_MIN = 320;
const DRAWER_MAX = 720;
const DRAWER_DEFAULT = 420;

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

function loadStoredWidth(): number {
  if (typeof window === 'undefined') return DRAWER_DEFAULT;
  const raw = window.localStorage.getItem(DRAWER_WIDTH_KEY);
  if (!raw) return DRAWER_DEFAULT;
  const n = parseInt(raw, 10);
  if (Number.isNaN(n)) return DRAWER_DEFAULT;
  return Math.max(DRAWER_MIN, Math.min(DRAWER_MAX, n));
}

export interface ConversationDrawerProps {
  /** Open state. The drawer is controlled by its parent. */
  open: boolean;
  /** Close handler — fired by the X button and Escape key. */
  onClose: () => void;
  /** Plus-menu actions passed through to the ConversationPanel composer. */
  plusMenuActions: PlusMenuAction[];
  /** Make-recurring callback wired through to the ConversationPanel
   *  for inline graduation of addressed exchanges to recurrences. */
  onMakeRecurring?: (messageContent: string) => void;
}

export function ConversationDrawer({
  open,
  onClose,
  plusMenuActions,
  onMakeRecurring,
}: ConversationDrawerProps) {
  const isMobile = useIsMobile();
  const personaName = useReviewerPersona();
  const [width, setWidth] = useState(DRAWER_DEFAULT);
  const dragging = useRef(false);

  // Hydrate width from localStorage on mount.
  useEffect(() => {
    setWidth(loadStoredWidth());
  }, []);

  // Escape-to-close.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  // Drag-to-resize (desktop only). Drag left edge of drawer to widen.
  const onMouseDown = useCallback((e: React.MouseEvent) => {
    if (isMobile) return;
    e.preventDefault();
    dragging.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, [isMobile]);

  useEffect(() => {
    if (isMobile) return;
    const onMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      const next = Math.max(DRAWER_MIN, Math.min(DRAWER_MAX, window.innerWidth - e.clientX));
      setWidth(next);
    };
    const onUp = () => {
      if (!dragging.current) return;
      dragging.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      window.localStorage.setItem(DRAWER_WIDTH_KEY, String(width));
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    return () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
  }, [width, isMobile]);

  if (!open) return null;

  // Backdrop dims the FeedTimeline behind (desktop) or covers it (mobile).
  return (
    <>
      <div
        className={cn(
          'fixed inset-0 z-40 bg-foreground/10 backdrop-blur-[1px]',
          isMobile && 'bg-background',
        )}
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        className={cn(
          'fixed top-0 right-0 bottom-0 z-50 flex bg-background border-l border-border shadow-2xl',
          isMobile && 'left-0 border-l-0',
        )}
        style={isMobile ? undefined : { width }}
        role="dialog"
        aria-label={`Conversation with ${personaName ?? 'Reviewer'}`}
      >
        {/* Drag handle (desktop only) */}
        {!isMobile && (
          <div
            onMouseDown={onMouseDown}
            className="w-1 shrink-0 cursor-col-resize bg-transparent hover:bg-primary/20 active:bg-primary/30 transition-colors"
            title="Drag to resize"
          />
        )}

        <div className="flex-1 min-w-0 flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2.5 border-b border-border bg-background shrink-0">
            <div className="flex items-center gap-2">
              <img src="/assets/logos/circleonly_yarnnn_1.svg" alt="" className="w-5 h-5" />
              <div className="flex flex-col">
                <span className="text-sm font-medium">{personaName ?? 'Reviewer'}</span>
                <span className="text-[10px] text-muted-foreground/60 -mt-0.5">
                  Conversation
                </span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted transition-colors"
              aria-label="Close conversation"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Conversation body — ConversationPanel scoped to pulse='addressed'. */}
          <div className="flex-1 min-h-0">
            <ConversationPanel
              surfaceOverride={{ type: 'chat' }}
              plusMenuActions={plusMenuActions}
              placeholder={`Reply to ${personaName ?? 'Reviewer'}…`}
              showCommandPicker={true}
              showInputDivider={true}
              onMakeRecurring={onMakeRecurring}
            />
          </div>
        </div>
      </div>
    </>
  );
}
