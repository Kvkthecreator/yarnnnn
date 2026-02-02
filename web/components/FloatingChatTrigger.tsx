'use client';

/**
 * ADR-020: Deliverable-Centric Chat
 *
 * Floating button to open the chat panel.
 * Shows in bottom-right corner when chat is closed.
 */

import { MessageSquare, Sparkles } from 'lucide-react';
import { useFloatingChat } from '@/contexts/FloatingChatContext';
import { cn } from '@/lib/utils';

interface FloatingChatTriggerProps {
  className?: string;
}

export function FloatingChatTrigger({ className }: FloatingChatTriggerProps) {
  const { state, open } = useFloatingChat();

  // Don't show if chat is already open
  if (state.isOpen) return null;

  return (
    <button
      onClick={open}
      className={cn(
        // Mobile: centered at bottom, larger touch target
        'fixed bottom-4 right-4 z-40',
        'md:bottom-6 md:right-6',
        'flex items-center justify-center',
        // Larger on mobile for easier tapping
        'w-14 h-14 md:w-14 md:h-14 rounded-full',
        'bg-primary text-primary-foreground',
        'shadow-lg hover:shadow-xl',
        'active:scale-95 md:hover:scale-105 transition-all duration-200',
        'group',
        className
      )}
      title="Open chat (⌘K)"
    >
      <Sparkles className="w-6 h-6 md:group-hover:hidden" />
      <MessageSquare className="w-6 h-6 hidden md:group-hover:block" />
    </button>
  );
}
