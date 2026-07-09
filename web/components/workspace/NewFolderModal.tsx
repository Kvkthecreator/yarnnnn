'use client';

/**
 * NewFolderModal — the operator's "New Folder" dialog (ADR-424 D2/D6).
 *
 * Pure-OS: the operator names a folder for their work at the top level (a peer
 * of Documents/Downloads) — you don't ask permission to `mkdir ~/projects`.
 * Folders are implicit in the substrate, so creating one seeds the folder's
 * first file (a starter README.md) via POST /documents/folder.
 *
 * Mirrors RenameModal's single-field pattern (ADR-400 polish) — one modal
 * design language, no second toast/dialog system. Outcome feedback (creating…/
 * created/failed) comes from the caller's runAction wrapper (useFeedback).
 */

import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { cn } from '@/lib/utils';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';

interface NewFolderModalProps {
  /** true = open, false = closed. */
  open: boolean;
  onClose: () => void;
  /** Called with the folder name (validated non-empty, slash-free). */
  onSubmit: (name: string) => void | Promise<void>;
}

export function NewFolderModal({ open, onClose, onSubmit }: NewFolderModalProps) {
  const [value, setValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setValue('');
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  if (!open) return null;

  const trimmed = value.trim();
  const hasSlash = trimmed.includes('/');
  const canSubmit = trimmed.length > 0 && !hasSlash;

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
          <h3 className="text-base font-semibold text-card-foreground">New folder</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            A folder for your work — it sits alongside Documents and Downloads.
          </p>
          <input
            ref={inputRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') submit();
              if (e.key === 'Escape') onClose();
            }}
            placeholder="e.g. The Acme Deal"
            className={cn(
              'mt-3 w-full rounded-md border bg-background px-3 py-2 text-sm text-foreground outline-none transition-colors',
              hasSlash ? 'border-destructive focus:border-destructive' : 'border-border focus:border-primary',
            )}
            aria-label="Folder name"
          />
          {hasSlash && (
            <p className="mt-1.5 text-xs text-destructive">
              A folder name can’t contain “/”.
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
              Create
            </button>
          </div>
        </div>
      </div>
    </>,
    document.body,
  );
}
