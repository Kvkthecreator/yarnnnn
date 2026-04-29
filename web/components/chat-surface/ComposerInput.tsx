'use client';

/**
 * ComposerInput — Shared input primitive for intent capture modals.
 *
 * Implements the unified-composer layout:
 *   ┌─────────────────────────────────────────┐
 *   │ [attached links]                        │
 *   │ [attached files]                        │
 *   │ ─────────────────────────────────────── │  ← divider (only when attachments present)
 *   │ textarea (primary input, autoFocus)     │
 *   │ ─────────────────────────────────────── │
 *   │ Link  File                              │  ← toolbar
 *   └─────────────────────────────────────────┘
 *
 * Data handling is identical across all callers:
 *   links + files + text → caller composes a message string → TP primitive
 *
 * Consumer (as of ADR-231 / 2026-04-29):
 *   RecurrenceSetup — recurrence creation (all surfaces). Composed message
 *                     targets UpdateContext(target='recurrence', action='create').
 *
 * Historical: ContextSetup (onboarding form) was the second consumer; it
 * was retired by ADR-215 Phase 5 as onboarding became conversational
 * (ADR-190) and identity/brand became substrate-editable on Files (ADR-215
 * R3, Phase 2). The shared primitive survives on the RecurrenceSetup path.
 *
 * When to extract vs keep separate:
 *   Two consumers sharing identical data shape and layout → extract (done).
 *   If a third consumer appears → it should compose this too.
 *   If one consumer needs a fundamentally different layout → fork, don't
 *   contort the shared primitive.
 *
 * Governed by ADR-178 (Task Creation Routes) and ADR-144 (Inference-First
 * Shared Context). See docs/design/COMPOSER-INPUT-PATTERN.md for the
 * canonical pattern doc.
 */

import React, { useState, useRef, useCallback, useEffect } from 'react';
import { X, Link2, Upload, FileText, Loader2, Plus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';

// ---------------------------------------------------------------------------
// Types (exported so callers can reference them)
// ---------------------------------------------------------------------------

export interface UploadedDoc {
  name: string;
  status: 'uploading' | 'done' | 'error';
}

export interface ComposerValue {
  notes: string;
  links: string[];
  uploadedDocs: UploadedDoc[];
}

export interface ComposerInputProps {
  /** Current text value */
  notes: string;
  onNotesChange: (v: string) => void;

  /** Current links */
  links: string[];
  onLinksChange: (links: string[]) => void;

  /** Current uploaded docs */
  uploadedDocs: UploadedDoc[];
  onUploadedDocsChange: React.Dispatch<React.SetStateAction<UploadedDoc[]>>;

  /** Textarea placeholder */
  placeholder?: string;

  /** Textarea row count (default 4) */
  rows?: number;

  /** Auto-focus the textarea on mount (default true) */
  autoFocus?: boolean;

  /** Placeholder for the link input field */
  linkPlaceholder?: string;

  /** Extra className on the outer container */
  className?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function normalizeUrl(raw: string): string {
  return raw.startsWith('http') ? raw : 'https://' + raw;
}

function isValidUrl(url: string): boolean {
  try { new URL(url); return true; } catch { return false; }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ComposerInput({
  notes,
  onNotesChange,
  links,
  onLinksChange,
  uploadedDocs,
  onUploadedDocsChange,
  placeholder = 'Describe your intent...',
  rows = 4,
  autoFocus = true,
  linkPlaceholder = 'Paste a URL and press Enter...',
  className,
}: ComposerInputProps) {
  const [linkInput, setLinkInput] = useState('');
  const [linkError, setLinkError] = useState<string | null>(null);
  const [showLinkInput, setShowLinkInput] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Reset link input when showLinkInput closes
  useEffect(() => {
    if (!showLinkInput) { setLinkInput(''); setLinkError(null); }
  }, [showLinkInput]);

  // ── Link handlers ─────────────────────────────────────────────────────────

  const addLink = useCallback(() => {
    const raw = linkInput.trim();
    if (!raw) return;
    const url = normalizeUrl(raw);
    if (!isValidUrl(url)) {
      setLinkError('Enter a valid URL');
      setTimeout(() => setLinkError(null), 3000);
      return;
    }
    if (links.includes(url)) {
      setLinkError('Already added');
      setTimeout(() => setLinkError(null), 3000);
      return;
    }
    onLinksChange([...links, url]);
    setShowLinkInput(false);
  }, [linkInput, links, onLinksChange]);

  const removeLink = useCallback((i: number) => {
    onLinksChange(links.filter((_, idx) => idx !== i));
  }, [links, onLinksChange]);

  // ── File handlers ─────────────────────────────────────────────────────────

  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    for (const file of files) {
      const maxSize = file.type.startsWith('image/') ? 5 * 1024 * 1024 : 20 * 1024 * 1024;
      if (file.size > maxSize) continue;

      const name = file.name;
      onUploadedDocsChange(prev => [...prev, { name, status: 'uploading' as const }]);

      try {
        await api.documents.upload(file);
        onUploadedDocsChange(prev =>
          prev.map(d => d.name === name && d.status === 'uploading' ? { ...d, status: 'done' as const } : d)
        );
      } catch {
        onUploadedDocsChange(prev =>
          prev.map(d => d.name === name && d.status === 'uploading' ? { ...d, status: 'error' as const } : d)
        );
      }
    }
    e.target.value = '';
  }, [onUploadedDocsChange]);

  const removeDoc = useCallback((i: number) => {
    onUploadedDocsChange(prev => prev.filter((_, idx) => idx !== i));
  }, [onUploadedDocsChange]);

  const hasAttachments = links.length > 0 || uploadedDocs.length > 0;

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className={cn(
      'rounded-lg border border-border/60 bg-muted/10 focus-within:border-border focus-within:ring-1 focus-within:ring-primary/30 transition-all',
      className
    )}>
      {/* Attached links */}
      {links.length > 0 && (
        <div className="px-3 pt-2.5 space-y-1">
          {links.map((link, i) => (
            <div key={i} className="flex items-center gap-2 group">
              <Link2 className="w-3 h-3 text-muted-foreground/40 shrink-0" />
              <span className="text-[11px] text-foreground/60 truncate flex-1 font-mono">{link}</span>
              <button
                onClick={() => removeLink(i)}
                className="p-0.5 text-muted-foreground/30 hover:text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Attached files */}
      {uploadedDocs.length > 0 && (
        <div className={cn('px-3 space-y-1', links.length > 0 ? 'pt-1' : 'pt-2.5')}>
          {uploadedDocs.map((doc, i) => (
            <div key={i} className="flex items-center gap-2 group">
              <FileText className="w-3 h-3 text-muted-foreground/40 shrink-0" />
              <span className="text-[11px] truncate flex-1 text-foreground/60">{doc.name}</span>
              <span className={cn('text-[10px] shrink-0',
                doc.status === 'done' ? 'text-green-600'
                  : doc.status === 'error' ? 'text-destructive'
                  : 'text-muted-foreground'
              )}>
                {doc.status === 'uploading'
                  ? <Loader2 className="w-3 h-3 animate-spin inline" />
                  : doc.status === 'done' ? '✓' : 'failed'}
              </span>
              <button
                onClick={() => removeDoc(i)}
                className="p-0.5 text-muted-foreground/30 hover:text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Divider between attachments and textarea */}
      {hasAttachments && <div className="mx-3 mt-2 border-t border-border/40" />}

      {/* Textarea — primary input */}
      <textarea
        value={notes}
        onChange={e => onNotesChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        // eslint-disable-next-line jsx-a11y/no-autofocus
        autoFocus={autoFocus}
        className="w-full text-sm bg-transparent px-3 py-2.5 focus:outline-none resize-none placeholder:text-muted-foreground/30"
      />

      {/* Inline link input */}
      {showLinkInput && (
        <div className="px-3 pb-2">
          <div className="flex items-center gap-1.5 border-t border-border/40 pt-2">
            <Link2 className="w-3 h-3 text-muted-foreground/40 shrink-0" />
            <input
              type="text"
              value={linkInput}
              onChange={e => { setLinkInput(e.target.value); setLinkError(null); }}
              onKeyDown={e => {
                if (e.key === 'Enter') { e.preventDefault(); addLink(); }
                if (e.key === 'Escape') setShowLinkInput(false);
              }}
              placeholder={linkPlaceholder}
              // eslint-disable-next-line jsx-a11y/no-autofocus
              autoFocus
              className="flex-1 text-[11px] bg-transparent focus:outline-none placeholder:text-muted-foreground/30"
            />
            <button
              onClick={addLink}
              disabled={!linkInput.trim()}
              className="p-1 text-muted-foreground hover:text-primary disabled:opacity-30 transition-colors shrink-0"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setShowLinkInput(false)}
              className="p-1 text-muted-foreground/40 hover:text-muted-foreground transition-colors shrink-0"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          {linkError && <p className="text-[10px] text-destructive mt-1 pl-5">{linkError}</p>}
        </div>
      )}

      {/* Toolbar */}
      {!showLinkInput && (
        <div className="flex items-center gap-0.5 px-2 pb-2 border-t border-border/30 mt-1 pt-1.5">
          <button
            onClick={() => setShowLinkInput(true)}
            className="flex items-center gap-1.5 text-[11px] text-muted-foreground/50 hover:text-muted-foreground transition-colors px-1.5 py-1 rounded hover:bg-muted/60"
          >
            <Link2 className="w-3 h-3" />
            Link
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt,.md"
            multiple
            onChange={handleFileSelect}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-1.5 text-[11px] text-muted-foreground/50 hover:text-muted-foreground transition-colors px-1.5 py-1 rounded hover:bg-muted/60"
          >
            <Upload className="w-3 h-3" />
            File
          </button>
        </div>
      )}
    </div>
  );
}
