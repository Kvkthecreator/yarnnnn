'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * HandoffBanner - Shows TP's message when navigating to a new surface
 *
 * This provides continuity between conversation and surface view.
 * Auto-dismisses after a few seconds or on user interaction.
 */

import { useEffect, useState } from 'react';
import { X, MessageCircle } from 'lucide-react';
import { useDesk } from '@/contexts/DeskContext';
import { cn } from '@/lib/utils';

export function HandoffBanner() {
  const { handoffMessage, clearHandoff } = useDesk();
  const [visible, setVisible] = useState(false);

  // Show banner when handoff message appears
  useEffect(() => {
    if (handoffMessage) {
      setVisible(true);

      // Auto-dismiss after 8 seconds
      const timer = setTimeout(() => {
        setVisible(false);
        // Clear after fade-out animation
        setTimeout(clearHandoff, 300);
      }, 8000);

      return () => clearTimeout(timer);
    } else {
      setVisible(false);
    }
  }, [handoffMessage, clearHandoff]);

  const handleDismiss = () => {
    setVisible(false);
    setTimeout(clearHandoff, 300);
  };

  if (!handoffMessage) return null;

  return (
    <div
      className={cn(
        'mx-auto max-w-4xl px-6 pt-4 transition-all duration-300',
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-2'
      )}
    >
      <div className="flex items-start gap-3 p-3 rounded-lg bg-primary/5 border border-primary/20">
        <MessageCircle className="w-4 h-4 mt-0.5 text-primary shrink-0" />
        <p className="flex-1 text-sm text-foreground">{handoffMessage}</p>
        <button
          onClick={handleDismiss}
          className="p-1 rounded hover:bg-primary/10 text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Dismiss"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
