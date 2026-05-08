'use client';

/**
 * InteractiveModal — the single style for all interactive stream entries.
 *
 * ADR-258 D: proposals, documents, and any actionable item in the chat
 * stream use one modal shape. The stream entry is a compact chip; clicking
 * opens this centered modal with full detail + action affordances.
 *
 * Two modes:
 *   proposal — full proposal detail + approve/reject (wraps ProposalCard content)
 *   file     — workspace file content (wraps WorkspaceFileView)
 *
 * Built on a simple dialog pattern — no external dialog library.
 * Modal closes on Escape, on backdrop click, or on explicit close.
 */

import { useEffect, useCallback } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface InteractiveModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  /** Optional one-line subtitle below the title */
  subtitle?: string;
  children: React.ReactNode;
  /** Width class — defaults to max-w-md (proposal), can pass max-w-lg for files */
  widthClass?: string;
}

export function InteractiveModal({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  widthClass = 'max-w-md',
}: InteractiveModalProps) {
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose();
  }, [onClose]);

  useEffect(() => {
    if (!isOpen) return;
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Modal panel */}
      <div
        className={cn(
          'relative z-10 w-full mx-4 rounded-xl border border-border bg-background shadow-lg',
          widthClass,
        )}
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border/60">
          <div className="min-w-0 flex-1">
            <h2 className="text-sm font-semibold truncate">{title}</h2>
            {subtitle && (
              <p className="text-[11px] text-muted-foreground mt-0.5 truncate">{subtitle}</p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="ml-3 shrink-0 p-1 text-muted-foreground/50 hover:text-foreground rounded-md hover:bg-muted/50 transition-colors"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {/* Body */}
        <div className="px-4 py-4 max-h-[70vh] overflow-y-auto">
          {children}
        </div>
      </div>
    </div>
  );
}
