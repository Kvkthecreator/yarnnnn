'use client';

/**
 * RenameModal — the single-field rename dialog for the operator's Rename verb
 * (ADR-400 polish, 2026-07-03). Replaces `window.prompt('Rename … to:')` with a
 * styled, focused text field. Pre-filled with the current name, "/" rejected
 * inline (a filename can't contain a slash — that's a Move, not a rename).
 *
 * Outcome feedback (renaming… / renamed / failed) comes from the caller's
 * runAction wrapper (useFeedback) — this modal only collects the new name.
 */

import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { cn } from '@/lib/utils';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';

interface RenameModalProps {
  /** The file being renamed (null = closed). */
  target: { path: string; name: string } | null;
  onClose: () => void;
  /** Called with the new leaf name (validated non-empty, slash-free). */
  onSubmit: (nextLeaf: string) => void | Promise<void>;
}

export function RenameModal({ target, onClose, onSubmit }: RenameModalProps) {
  const [value, setValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const currentLeaf = target ? target.path.slice(target.path.lastIndexOf('/') + 1) : '';

  useEffect(() => {
    if (target) {
      setValue(currentLeaf);
      // Focus + select the name (minus extension where obvious) next tick.
      requestAnimationFrame(() => {
        const el = inputRef.current;
        if (!el) return;
        el.focus();
        const dot = currentLeaf.lastIndexOf('.');
        el.setSelectionRange(0, dot > 0 ? dot : currentLeaf.length);
      });
    }
  }, [target, currentLeaf]);

  if (!target) return null;

  const trimmed = value.trim();
  const hasSlash = trimmed.includes('/');
  const canSubmit = trimmed.length > 0 && !hasSlash && trimmed !== currentLeaf;

  const submit = () => {
    if (canSubmit) onSubmit(trimmed);
  };

  return createPortal(
    <>
      <div
        className="fixed inset-0 bg-black/50 animate-in fade-in duration-150"
        style={{ zIndex: Z_CONFIRM_BACKDROP }}
        onClick={onClose}
      />
      <div
        className="fixed inset-0 flex items-center justify-center p-4 pointer-events-none"
        style={{ zIndex: Z_CONFIRM_DIALOG }}
      >
        <div
          className="pointer-events-auto w-full max-w-sm rounded-lg border border-border bg-card p-5 shadow-xl animate-in fade-in zoom-in-95 duration-150"
          role="dialog"
          aria-modal="true"
        >
          <h3 className="text-base font-semibold text-card-foreground">Rename</h3>
          <input
            ref={inputRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') submit();
              if (e.key === 'Escape') onClose();
            }}
            className={cn(
              'mt-3 w-full rounded-md border bg-background px-3 py-2 text-sm text-foreground outline-none transition-colors',
              hasSlash ? 'border-destructive focus:border-destructive' : 'border-border focus:border-primary',
            )}
            aria-label="New name"
          />
          {hasSlash && (
            <p className="mt-1.5 text-xs text-destructive">
              A name can’t contain “/”. To move it to another folder, use “Move to…”.
            </p>
          )}
          <div className="mt-5 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-border px-3.5 py-1.5 text-sm text-foreground transition-colors hover:bg-muted/60"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={!canSubmit}
              onClick={submit}
              className={cn(
                'rounded-md px-3.5 py-1.5 text-sm font-medium transition-colors',
                canSubmit
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                  : 'cursor-not-allowed bg-muted text-muted-foreground',
              )}
            >
              Rename
            </button>
          </div>
        </div>
      </div>
    </>,
    document.body,
  );
}
