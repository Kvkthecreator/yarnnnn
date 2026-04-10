'use client';

/**
 * OnboardingModal — First-run identity capture (ADR-165 v8).
 *
 * Separate modal from the Overview dashboard (`WorkspaceStateView`). Opened
 * exclusively by TP via the `<!-- onboarding -->` marker on the first turn
 * when `workspace_state.identity == "empty"`. No manual trigger, no plus-menu
 * entry, no soft gate — this modal has one lifecycle: cold start → capture →
 * done.
 *
 * The body is the existing `ContextSetup` component (unchanged). On submit,
 * the modal closes and the composed message is forwarded to TP via
 * `sendMessage`, which triggers inference (UpdateContext + ManageDomains).
 */

import { useEffect } from 'react';
import { X } from 'lucide-react';
import { ContextSetup } from './ContextSetup';

interface OnboardingModalProps {
  open: boolean;
  onClose: () => void;
  /** Called with the composed message when user submits. */
  onSubmit: (message: string) => void;
}

export function OnboardingModal({ open, onClose, onSubmit }: OnboardingModalProps) {
  // Esc closes the modal. Body scroll lock while open.
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
      aria-label="Tell me about yourself"
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
                Getting started
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded p-1 text-muted-foreground/40 hover:bg-muted hover:text-muted-foreground"
              aria-label="Close onboarding"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </header>

          {/* Body — ContextSetup unchanged, embedded mode */}
          <div className="max-h-[60vh] overflow-y-auto p-3">
            <ContextSetup onSubmit={onSubmit} embedded />
          </div>

          {/* Footer — explicit escape hatch so the user never feels stuck */}
          <footer className="border-t border-border px-4 py-2.5 flex items-center justify-between">
            <p className="text-[11px] text-muted-foreground/50">
              You can always add this later via Context.
            </p>
            <button
              type="button"
              onClick={onClose}
              className="text-[11px] text-muted-foreground hover:text-foreground transition-colors"
            >
              Skip for now
            </button>
          </footer>
        </div>
      </section>
    </div>
  );
}
