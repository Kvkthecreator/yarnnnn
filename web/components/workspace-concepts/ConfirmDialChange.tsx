'use client';

/**
 * ConfirmDialChange — confirm modal for high-stakes radio-dial mutations.
 *
 * Used by AutonomyCard (level) + PaceCard (kind) full variants. Per the
 * 2026-05-24 design polish (see docs/design/WORKSPACE-COMPONENTS.md §2 +
 * §6): both dials are single-click commits whose impact is capital
 * (autonomy) or cost (pace). Surfacing the consequence + requiring an
 * explicit Confirm prevents accidental flips while preserving Direct-
 * mutation semantics (no chat round-trip).
 *
 * Modal copy is the consumer's responsibility — `consequence` is the
 * one-line summary surfaced to the operator. Consumers know their dial
 * better than this generic component does.
 *
 * Built on InteractiveModal for visual consistency with the rest of the
 * feed-surface modal family.
 */

import { useState } from 'react';
import { Loader2, AlertTriangle } from 'lucide-react';
import { InteractiveModal } from '@/components/tp/InteractiveModal';
import { cn } from '@/lib/utils';

interface ConfirmDialChangeProps {
  open: boolean;
  /** Short label for the dial — e.g. "autonomy" or "pace". Lowercase. */
  dialName: string;
  /** Current level label — e.g. "Manual" or "Daily". */
  fromLabel: string;
  /** Proposed level label — e.g. "Autonomous" or "Continuous". */
  toLabel: string;
  /** One-line consequence surfaced inside the modal body. */
  consequence: string;
  onCancel: () => void;
  /** Async because consumers run a workspace-write here. */
  onConfirm: () => Promise<void>;
}

export function ConfirmDialChange({
  open,
  dialName,
  fromLabel,
  toLabel,
  consequence,
  onCancel,
  onConfirm,
}: ConfirmDialChangeProps) {
  const [submitting, setSubmitting] = useState(false);

  const handleConfirm = async () => {
    if (submitting) return;
    setSubmitting(true);
    try {
      await onConfirm();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <InteractiveModal
      isOpen={open}
      onClose={() => {
        if (submitting) return;
        onCancel();
      }}
      title={`Switch ${dialName} to ${toLabel}?`}
      subtitle={`Currently ${fromLabel}`}
    >
      <div className="px-4 py-4 space-y-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
          <p className="text-sm text-foreground/90 leading-relaxed">
            {consequence}
          </p>
        </div>

        <div className="flex items-center justify-end gap-2 pt-2 border-t border-border/40">
          <button
            type="button"
            onClick={onCancel}
            disabled={submitting}
            className={cn(
              'rounded-md border border-border/60 px-3 py-1.5 text-sm font-medium',
              'text-foreground/80 hover:bg-muted/40 transition-colors',
              'disabled:opacity-40 disabled:cursor-not-allowed',
            )}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void handleConfirm()}
            disabled={submitting}
            className={cn(
              'rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground',
              'hover:opacity-90 transition-opacity',
              'disabled:opacity-50 disabled:cursor-wait',
              'inline-flex items-center gap-1.5',
            )}
          >
            {submitting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Confirm
          </button>
        </div>
      </div>
    </InteractiveModal>
  );
}
