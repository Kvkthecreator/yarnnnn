'use client';

/**
 * RecurrenceSetupModal — Structured recurrence creation modal (ADR-178 + ADR-231).
 *
 * Wraps RecurrenceSetup in a modal shell — the singular creation modal across
 * the cockpit per ADR-215 Phase 4.
 *
 * Opened by the "Start new work" plus-menu action on any of the four cockpit
 * tabs. On submit, the composed intent message is forwarded to YARNNN via
 * sendMessage. Per ADR-231 D5, YARNNN calls
 * `UpdateContext(target='recurrence', action='create', shape=..., slug=...,
 * body={...})` in the same turn — no clarifying rounds.
 */

import { useEffect } from 'react';
import { X } from 'lucide-react';
import { RecurrenceSetup } from './RecurrenceSetup';

interface RecurrenceSetupModalProps {
  open: boolean;
  onClose: () => void;
  /** Called with the composed message when user submits. */
  onSubmit: (message: string) => void;
  /** Optional pre-filled notes (e.g. idle agent names from Heads Up). */
  initialNotes?: string;
}

export function RecurrenceSetupModal({ open, onClose, onSubmit, initialNotes }: RecurrenceSetupModalProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener('keydown', onKey);
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-foreground/40 px-4 py-[10vh] backdrop-blur-sm animate-in fade-in duration-150"
      role="dialog"
      aria-modal="true"
      aria-label="Set up new work"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <section
        className="w-full max-w-2xl animate-in fade-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="rounded-xl border border-border bg-background shadow-2xl">
          {/* Header */}
          <header className="flex items-start justify-between border-b border-border px-4 py-2.5">
            <div className="min-w-0">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
                New work
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded p-1 text-muted-foreground/40 hover:bg-muted hover:text-muted-foreground"
              aria-label="Close"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </header>

          {/* Body */}
          <div className="max-h-[70vh] overflow-y-auto p-3">
            <RecurrenceSetup onSubmit={onSubmit} embedded initialNotes={initialNotes} />
          </div>

          {/* Footer */}
          <footer className="border-t border-border px-4 py-2.5 flex items-center justify-end">
            <button
              type="button"
              onClick={onClose}
              className="text-[11px] text-muted-foreground hover:text-foreground transition-colors"
            >
              Cancel
            </button>
          </footer>
        </div>
      </section>
    </div>
  );
}
