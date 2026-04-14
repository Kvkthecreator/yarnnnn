'use client';

/**
 * TaskSetup — Structured intent capture for task creation (ADR-178 v2).
 *
 * Single-screen design:
 *   - Route toggle chips at top (Set up recurring work | I have something specific in mind)
 *   - Prominent textarea adapts placeholder to route
 *   - Links and files co-equal alongside textarea — not collapsed behind a divider
 *   - Zero chip groups (domain/cadence/sources/format/mode/delivery all removed)
 *     TP infers these from composed message + working_memory
 *
 * Composed message is a complete intent statement TP acts on in one turn.
 * See docs/design/TASK-SETUP-FLOW.md for full spec.
 *
 * Governed by ADR-178 (Task Creation Routes).
 * Parallel to ContextSetup.tsx (same material injection pattern).
 */

import React, { useState, useRef, useCallback, useEffect } from 'react';
import { X, Link2, Upload, FileText, Loader2, Plus, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Route = 'track' | 'deliverable';

interface UploadedDoc {
  name: string;
  status: 'uploading' | 'done' | 'error';
}

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const ROUTES: { value: Route; label: string }[] = [
  { value: 'track', label: 'Set up recurring work' },
  { value: 'deliverable', label: 'I have something specific in mind' },
];

const PLACEHOLDERS: Record<Route, string> = {
  track: 'Track Cursor, Linear, Notion. Focused on pricing and product changes.',
  deliverable: 'A weekly competitive brief. 2 pages, pricing focus. Email me Monday mornings.',
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface TaskSetupProps {
  /** Called with the composed message when user submits */
  onSubmit: (message: string) => void;
  /** Called when user dismisses */
  onDismiss?: () => void;
  /** Compact mode (smaller padding) */
  compact?: boolean;
  /** Embedded mode — parent provides the outer frame */
  embedded?: boolean;
  /** Pre-fill notes (e.g. from Heads Up with idle agent names) */
  initialNotes?: string;
}

export function TaskSetup({
  onSubmit,
  onDismiss,
  compact = false,
  embedded = false,
  initialNotes = '',
}: TaskSetupProps) {
  const [route, setRoute] = useState<Route>('track');
  const [notes, setNotes] = useState(initialNotes);
  const [links, setLinks] = useState<string[]>([]);
  const [uploadedDocs, setUploadedDocs] = useState<UploadedDoc[]>([]);
  const [submitting, setSubmitting] = useState(false);

  // Link input state
  const [linkInput, setLinkInput] = useState('');
  const [linkError, setLinkError] = useState<string | null>(null);
  const [showLinkInput, setShowLinkInput] = useState(false);

  // File upload
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sync initialNotes prop (e.g. when opened from Heads Up with idle agent names)
  useEffect(() => {
    setNotes(initialNotes);
  }, [initialNotes]);

  const isUploading = uploadedDocs.some(d => d.status === 'uploading');

  // ── Link helpers ──────────────────────────────────────────────────────────

  const addLink = useCallback(() => {
    const url = linkInput.trim();
    if (!url) return;
    try {
      const normalized = url.startsWith('http') ? url : 'https://' + url;
      new URL(normalized);
      if (links.includes(normalized)) {
        setLinkError('Already added');
        setTimeout(() => setLinkError(null), 3000);
        return;
      }
      setLinks(prev => [...prev, normalized]);
      setLinkInput('');
      setLinkError(null);
      setShowLinkInput(false);
    } catch {
      setLinkError('Enter a valid URL');
      setTimeout(() => setLinkError(null), 3000);
    }
  }, [linkInput, links]);

  const removeLink = useCallback((index: number) => {
    setLinks(prev => prev.filter((_, i) => i !== index));
  }, []);

  // ── File helpers ──────────────────────────────────────────────────────────

  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    for (const file of files) {
      const maxSize = file.type.startsWith('image/') ? 5 * 1024 * 1024 : 20 * 1024 * 1024;
      if (file.size > maxSize) continue;

      const name = file.name;
      setUploadedDocs(prev => [...prev, { name, status: 'uploading' as const }]);

      try {
        await api.documents.upload(file);
        setUploadedDocs(prev =>
          prev.map(d => d.name === name && d.status === 'uploading' ? { ...d, status: 'done' as const } : d)
        );
      } catch {
        setUploadedDocs(prev =>
          prev.map(d => d.name === name && d.status === 'uploading' ? { ...d, status: 'error' as const } : d)
        );
      }
    }
    e.target.value = '';
  }, []);

  const removeDoc = useCallback((index: number) => {
    setUploadedDocs(prev => prev.filter((_, i) => i !== index));
  }, []);

  // ── Submit ────────────────────────────────────────────────────────────────

  const canSubmit =
    (notes.trim().length > 0 || links.length > 0 || uploadedDocs.some(d => d.status === 'done')) &&
    !isUploading &&
    !submitting;

  const handleSubmit = useCallback(() => {
    if (!canSubmit) return;
    setSubmitting(true);

    const doneDocs = uploadedDocs.filter(d => d.status === 'done');
    const parts: string[] = [];

    if (route === 'track') {
      parts.push(
        notes.trim()
          ? `I want to track ${notes.trim()}.`
          : 'I want to set up recurring tracking work.'
      );
      if (links.length > 0) {
        parts.push(`Please fetch these to seed entity profiles:\n${links.map(l => `- ${l}`).join('\n')}`);
      }
      if (doneDocs.length > 0) {
        parts.push(`I've uploaded context to seed this domain:\n${doneDocs.map(d => `- ${d.name}`).join('\n')}`);
      }
    } else {
      parts.push(
        notes.trim()
          ? `I want a deliverable — ${notes.trim()}`
          : 'I want to create a deliverable.'
      );
      if (links.length > 0) {
        parts.push(`Reference materials — fetch each and use to shape the output spec:\n${links.map(l => `- ${l}`).join('\n')}`);
      }
      if (doneDocs.length > 0) {
        parts.push(`I've uploaded reference materials:\n${doneDocs.map(d => `- ${d.name}`).join('\n')}`);
      }
    }

    onSubmit(parts.join('\n'));
  }, [canSubmit, route, notes, links, uploadedDocs, onSubmit]);

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className={cn(
      'bg-background animate-in fade-in slide-in-from-bottom-3 duration-200',
      !embedded && 'rounded-xl border border-border shadow-sm',
      compact ? 'p-3' : 'p-4'
    )}>
      {/* Header row with optional dismiss */}
      {onDismiss && (
        <div className="flex items-center justify-end mb-3">
          <button
            onClick={onDismiss}
            className="p-1 text-muted-foreground/40 hover:text-muted-foreground rounded-md hover:bg-muted transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Route toggle */}
      <div className="flex items-center gap-1.5 mb-4 p-1 bg-muted/40 rounded-lg">
        {ROUTES.map(r => (
          <button
            key={r.value}
            onClick={() => setRoute(r.value)}
            className={cn(
              'flex-1 py-1.5 px-2 rounded-md text-xs font-medium transition-colors',
              route === r.value
                ? 'bg-background text-foreground shadow-sm border border-border/60'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            {r.label}
          </button>
        ))}
      </div>

      {/* Unified input surface — textarea + materials in one bordered container */}
      <div className="rounded-lg border border-border/60 bg-muted/10 focus-within:border-border focus-within:ring-1 focus-within:ring-primary/30 transition-all mb-3">

        {/* Attached links */}
        {links.length > 0 && (
          <div className="px-3 pt-2.5 space-y-1">
            {links.map((link, i) => (
              <div key={i} className="flex items-center gap-2 group">
                <Link2 className="w-3 h-3 text-muted-foreground/40 shrink-0" />
                <span className="text-[11px] text-foreground/60 truncate flex-1 font-mono">
                  {link}
                </span>
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
                  doc.status === 'done' ? 'text-green-600' : doc.status === 'error' ? 'text-destructive' : 'text-muted-foreground'
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

        {/* Divider when attachments are present */}
        {(links.length > 0 || uploadedDocs.length > 0) && (
          <div className="mx-3 mt-2 border-t border-border/40" />
        )}

        {/* Textarea */}
        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          placeholder={PLACEHOLDERS[route]}
          rows={4}
          autoFocus
          className="w-full text-sm bg-transparent px-3 py-2.5 focus:outline-none resize-none placeholder:text-muted-foreground/30"
        />

        {/* Inline link input (shown when adding a link) */}
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
                  if (e.key === 'Escape') { setShowLinkInput(false); setLinkInput(''); setLinkError(null); }
                }}
                placeholder={route === 'track'
                  ? 'competitor sites, market pages, GitHub repos...'
                  : 'example reports, reference sources...'}
                autoFocus
                className={cn(
                  'flex-1 text-[11px] bg-transparent focus:outline-none placeholder:text-muted-foreground/30',
                  linkError ? 'text-destructive' : ''
                )}
              />
              <button
                onClick={addLink}
                disabled={!linkInput.trim()}
                className="p-1 text-muted-foreground hover:text-primary disabled:opacity-30 transition-colors shrink-0"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => { setShowLinkInput(false); setLinkInput(''); setLinkError(null); }}
                className="p-1 text-muted-foreground/40 hover:text-muted-foreground transition-colors shrink-0"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            {linkError && <p className="text-[10px] text-destructive mt-1 pl-5">{linkError}</p>}
          </div>
        )}

        {/* Toolbar — attach link / upload file */}
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

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!canSubmit}
        className={cn(
          'w-full mt-4 flex items-center justify-center gap-2 rounded-lg font-medium transition-colors',
          compact ? 'py-2 text-xs' : 'py-2.5 text-sm',
          canSubmit
            ? 'bg-primary text-primary-foreground hover:bg-primary/90'
            : 'bg-muted text-muted-foreground cursor-not-allowed'
        )}
      >
        {submitting ? (
          <><Loader2 className="w-4 h-4 animate-spin" /> Setting up...</>
        ) : isUploading ? (
          <><Loader2 className="w-4 h-4 animate-spin" /> Uploading...</>
        ) : route === 'track' ? (
          <>Set up tracking<ArrowRight className="w-4 h-4" /></>
        ) : (
          <>Set up deliverable<ArrowRight className="w-4 h-4" /></>
        )}
      </button>
    </div>
  );
}
