'use client';

/**
 * ImagePreviewModal — a local image at full size (2026-09-18).
 *
 * The sibling of `FileOpenModal`, and deliberately a separate mount for one
 * reason: that one opens a file by its WORKSPACE PATH, through `useFileLoad`.
 * A composer attachment has no path yet — it is bytes in the browser, often
 * still uploading — so there is nothing for that mount to load. This one takes
 * a URL that already resolves (an object URL over the local file) and shows it.
 *
 * It is not a second viewer. It renders one `<img>` and nothing else: no type
 * dispatch, no `FileBody`, no Open-in-Files handoff. Once an attachment has
 * landed in the workspace, `FileOpenModal` remains the way to open it — this
 * only covers the window before that, where the member's question is simply
 * "is this the right screenshot?".
 *
 * Uses the EXISTING overlay pattern (backdrop + Escape + centered card), so
 * the window-manager invariant (window = surface, ADR-297 D15) is untouched.
 */

import { useEffect } from 'react';
import { X } from 'lucide-react';

interface ImagePreviewModalProps {
  /** An already-resolvable URL (object URL or remote), or null when closed. */
  url: string | null;
  /** Shown in the header and used as the alt text. */
  name?: string;
  onClose: () => void;
}

export function ImagePreviewModal({ url, name, onClose }: ImagePreviewModalProps) {
  useEffect(() => {
    if (!url) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [url, onClose]);

  if (!url) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <div className="relative flex max-h-full max-w-5xl flex-col overflow-hidden rounded-lg border border-border bg-background shadow-xl">
        <div className="flex items-center gap-2 border-b border-border px-3 py-2">
          <span className="min-w-0 flex-1 truncate text-sm font-medium">{name}</span>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label="Close preview"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="min-h-0 overflow-auto bg-muted/20 p-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={url}
            alt={name || ''}
            className="mx-auto block max-h-[75vh] w-auto max-w-full object-contain"
          />
        </div>
      </div>
    </div>
  );
}
