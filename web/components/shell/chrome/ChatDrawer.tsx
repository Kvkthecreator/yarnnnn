'use client';

/**
 * ChatDrawer — ADR-297 D16 universal chat drawer body.
 *
 * The slide-over drawer summoned by the bottom-center FAB. Hosts:
 *   - Persona header (yarnnn icon + persona name + Conversation
 *     subtitle + close ×)
 *   - Scrollable addressed-conversation timeline (ConversationPanel,
 *     filtered to pulse='addressed' intrinsically)
 *   - Composer input at the bottom (inside ConversationPanel)
 *
 * Drawer width: default 400px, resizable 320–720px via left-edge
 * drag handle. Persisted per-user to localStorage. Mobile (<640px):
 * full-screen takeover.
 *
 * This component intentionally re-uses the per-`/feed` legacy
 * ConversationDrawer (web/components/feed/ConversationDrawer.tsx)
 * pattern verbatim — operators already learned the shape; D16 just
 * relocates the mount from `/feed`-only to the shell. The legacy
 * file is DELETED in the same commit; this file is its successor.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { X } from 'lucide-react';
import { ConversationPanel } from '@/components/tp/ConversationPanel';
import { useReviewerPersona } from '@/lib/reviewer-persona';
import { useViewport } from '@/lib/shell/useViewport';
import { useDesk } from '@/contexts/DeskContext';
import { cn } from '@/lib/utils';

const DRAWER_WIDTH_KEY = 'yarnnn:shell:chat-drawer-width';
const DRAWER_MIN = 320;
const DRAWER_MAX = 720;
const DRAWER_DEFAULT = 400;

function loadStoredWidth(): number {
  if (typeof window === 'undefined') return DRAWER_DEFAULT;
  const raw = window.localStorage.getItem(DRAWER_WIDTH_KEY);
  if (!raw) return DRAWER_DEFAULT;
  const n = parseInt(raw, 10);
  if (Number.isNaN(n)) return DRAWER_DEFAULT;
  return Math.max(DRAWER_MIN, Math.min(DRAWER_MAX, n));
}

interface ChatDrawerProps {
  open: boolean;
  onClose: () => void;
}

export function ChatDrawer({ open, onClose }: ChatDrawerProps) {
  const { isMobile } = useViewport();
  const personaName = useReviewerPersona();
  const { surface } = useDesk();
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
  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (isMobile) return;
      e.preventDefault();
      dragging.current = true;
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    },
    [isMobile]
  );

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
      try {
        window.localStorage.setItem(DRAWER_WIDTH_KEY, String(width));
      } catch {}
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    return () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
  }, [width, isMobile]);

  if (!open) return null;

  return (
    <>
      {/* Backdrop dims the windows behind (desktop) or fully covers
          them (mobile, where the drawer takes full-screen). */}
      <div
        className={cn(
          'fixed inset-0 z-40 bg-foreground/10 backdrop-blur-[1px]',
          isMobile && 'bg-background'
        )}
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        className={cn(
          'fixed top-0 right-0 bottom-0 z-50 flex bg-background border-l border-border shadow-2xl',
          isMobile && 'left-0 border-l-0'
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
              <img
                src="/assets/logos/circleonly_yarnnn_1.svg"
                alt=""
                className="w-5 h-5"
              />
              <div className="flex flex-col">
                <span className="text-sm font-medium">
                  {personaName ?? 'Reviewer'}
                </span>
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

          {/* Conversation body — composer + addressed timeline.
              surfaceOverride flows from DeskContext per D16 §5 so
              YARNNN knows the operator is "asking about {current
              surface}" when they summon chat from any window. */}
          <div className="flex-1 min-h-0">
            <ConversationPanel
              surfaceOverride={surface}
              plusMenuActions={[]}
              placeholder={`Ask ${personaName ?? 'YARNNN'}…`}
              showCommandPicker={true}
              showInputDivider={true}
            />
          </div>
        </div>
      </div>
    </>
  );
}
