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

/**
 * A typed folder name → the path segment it becomes. The FE mirror of
 * `api/routes/documents.py::_sanitize_folder_segment`.
 *
 * Deliberately NOT `path_slug` (`services/naming.py`, ADR-469). That rule
 * ASCII-folds and falls back to `untitled`, which is correct for an ARTIFACT
 * because the artifact carries its readable name in its own `<title>` — the
 * key is never read. A folder has no such carrier: its segment IS its name,
 * everywhere it is shown. Folding `한글 문서` to `untitled` there would erase
 * the only name the folder has. So Unicode survives here, and the two rules
 * differ ON PURPOSE.
 *
 * Keep in step with the Python; a drift only mis-previews, never mis-writes
 * (the server sanitizes regardless).
 *
 * The keep-set is BUILT AT RUNTIME rather than written as a regex literal.
 * `\p{L}\p{N}` needs the `u` flag, and a `u`-flagged LITERAL is refused by this
 * project's TypeScript target — though every browser that runs this supports it
 * fine. `new RegExp(…, 'gu')` is the same expression, checked at runtime
 * instead of compile time.
 *
 * Two hand-written approximations were tried first and BOTH were wrong: an
 * ASCII-punctuation denylist kept non-ASCII punctuation (`naïve—dash` survived
 * its em-dash), and a `À-￿` range kept emoji and dropped `½`. Caught by
 * diffing against the Python over a 17-case set — not by reading either
 * implementation. Don't re-approximate this; the property escapes ARE the rule.
 */
const DROP_FROM_SEGMENT = new RegExp('[^\\p{L}\\p{N}\\s_-]', 'gu');

export function folderSegment(name: string): string {
  return (name || '')
    .trim()
    .replace(/^\/+|\/+$/g, '')
    .trim()
    .replace(DROP_FROM_SEGMENT, '')
    .trim()
    .replace(/[\s_]+/g, '-')
    .toLowerCase();
}

interface NewFolderModalProps {
  /** true = open, false = closed. */
  open: boolean;
  onClose: () => void;
  /** Called with the folder name (validated non-empty, slash-free). */
  onSubmit: (name: string) => void | Promise<void>;
  /**
   * Display name of the folder the new one is created INSIDE (the folder-node
   * / folder-canvas scoped act). Absent = the top-level peer act. The modal
   * states the destination either way — never a silent placement.
   */
  destinationName?: string;
}

export function NewFolderModal({ open, onClose, onSubmit, destinationName }: NewFolderModalProps) {
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
  const folderKey = folderSegment(trimmed);
  // The server rewrites the typed name into a path segment, and it used to do
  // so SILENTLY — "The Acme Deal" became `the-acme-deal` and "R&D" became `rd`
  // with the member never told. Preview it, but only when it differs, so the
  // common case stays one field + Enter.
  const showsKey = !!folderKey && folderKey !== trimmed;
  const emptyKey = trimmed.length > 0 && !hasSlash && !folderKey;
  const canSubmit = trimmed.length > 0 && !hasSlash && !emptyKey;

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
            {destinationName
              ? <>It will be created inside <span className="font-medium text-foreground/80">{destinationName}</span>.</>
              : 'A folder for your work — it sits alongside Documents and Downloads.'}
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
          {!hasSlash && emptyKey && (
            <p className="mt-1.5 text-xs text-destructive">
              That name has no letters or numbers to build a folder from.
            </p>
          )}
          {!hasSlash && showsKey && (
            <p className="mt-1.5 text-xs text-muted-foreground">
              Saved as <span className="font-mono text-foreground/80">{folderKey}</span>
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
