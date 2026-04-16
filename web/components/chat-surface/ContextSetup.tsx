'use client';

/**
 * ContextSetup — Identity capture for the onboarding modal (ADR-144).
 *
 * Layout priority: files (highest signal) → links → notes (lowest friction).
 * Files are a visible drop zone, not a hidden toolbar button — a pitch deck
 * or LinkedIn PDF gives TP more to work with than a typed sentence.
 *
 * On submit, the composed message is forwarded to TP which calls
 * UpdateContext + ManageDomains — no clarifying rounds.
 *
 * Sole consumer: OnboardingModal (embedded mode).
 */

import { useState, useCallback, useRef } from 'react';
import { X, ArrowRight, Loader2, Link2, Upload, FileText, Plus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import type { UploadedDoc } from './ComposerInput';

interface ContextSetupProps {
  /** Called with the composed message when user submits */
  onSubmit: (message: string) => void;
  /** Called when user dismisses without submitting */
  onDismiss?: () => void;
  /** Compact mode (smaller padding) */
  compact?: boolean;
  /** Embedded mode — parent provides the outer frame */
  embedded?: boolean;
}

export function ContextSetup({
  onSubmit,
  onDismiss,
  compact = false,
  embedded = false,
}: ContextSetupProps) {
  const [notes, setNotes] = useState('');
  const [links, setLinks] = useState<string[]>([]);
  const [linkInput, setLinkInput] = useState('');
  const [linkError, setLinkError] = useState<string | null>(null);
  const [uploadedDocs, setUploadedDocs] = useState<UploadedDoc[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isUploading = uploadedDocs.some(d => d.status === 'uploading');
  const canSubmit =
    (notes.trim().length > 0 || links.length > 0 || uploadedDocs.some(d => d.status === 'done')) &&
    !isUploading &&
    !submitting;

  // ── File handlers ─────────────────────────────────────────────────────────

  const uploadFiles = useCallback(async (files: File[]) => {
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
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length) uploadFiles(files);
    e.target.value = '';
  }, [uploadFiles]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length) uploadFiles(files);
  }, [uploadFiles]);

  // ── Link handlers ─────────────────────────────────────────────────────────

  const addLink = useCallback(() => {
    const raw = linkInput.trim();
    if (!raw) return;
    const url = raw.startsWith('http') ? raw : 'https://' + raw;
    try { new URL(url); } catch {
      setLinkError('Enter a valid URL');
      setTimeout(() => setLinkError(null), 3000);
      return;
    }
    if (links.includes(url)) {
      setLinkError('Already added');
      setTimeout(() => setLinkError(null), 3000);
      return;
    }
    setLinks(prev => [...prev, url]);
    setLinkInput('');
    setLinkError(null);
  }, [linkInput, links]);

  // ── Submit ────────────────────────────────────────────────────────────────

  const handleSubmit = useCallback(() => {
    if (!canSubmit) return;
    setSubmitting(true);

    const parts: string[] = [];

    // Notes first — user's own words are highest fidelity
    if (notes.trim()) parts.push(notes.trim());

    // Links — explicit fetch instruction so TP knows to read them
    if (links.length > 0) {
      parts.push(
        `\nPlease read these links about me and my work:\n${links.map(l => `- ${l}`).join('\n')}\nFetch each URL and use the content to update my identity and brand.`
      );
    }

    // Files — listed for TP awareness (already in workspace after upload)
    const doneDocs = uploadedDocs.filter(d => d.status === 'done');
    if (doneDocs.length > 0) {
      parts.push(`\nI've uploaded these files for reference:\n${doneDocs.map(d => `- ${d.name}`).join('\n')}`);
    }

    onSubmit(parts.join('\n'));
  }, [canSubmit, notes, links, uploadedDocs, onSubmit]);

  return (
    <div className={cn(
      'bg-background animate-in fade-in slide-in-from-bottom-3 duration-200',
      !embedded && 'rounded-xl border border-border shadow-sm',
      compact ? 'p-3' : 'p-4'
    )}>
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <p className={cn('font-medium', compact ? 'text-xs' : 'text-base')}>
            Tell me about yourself and your work
          </p>
          <p className={cn('text-muted-foreground mt-1', compact ? 'text-[11px]' : 'text-sm')}>
            Share anything — I&apos;ll figure out where it goes.
          </p>
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="p-1 text-muted-foreground/40 hover:text-muted-foreground rounded-md hover:bg-muted transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* ── 1. File drop zone (hero) ────────────────────────────────────── */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.txt,.md,.csv"
        multiple
        onChange={handleFileSelect}
        className="hidden"
      />
      <div
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={cn(
          'rounded-lg border-2 border-dashed cursor-pointer transition-all mb-3',
          'flex flex-col items-center justify-center text-center',
          uploadedDocs.length > 0 ? 'px-3 py-2.5' : 'px-4 py-5',
          dragOver
            ? 'border-primary/60 bg-primary/5'
            : 'border-border/50 hover:border-border hover:bg-muted/30'
        )}
      >
        {uploadedDocs.length === 0 ? (
          <>
            <Upload className="w-5 h-5 text-muted-foreground/40 mb-2" />
            <p className="text-sm font-medium text-foreground/70">
              Drop files here or click to upload
            </p>
            <p className="text-[11px] text-muted-foreground/50 mt-1">
              Pitch decks, brand guides, LinkedIn exports — anything that describes you or your work
            </p>
          </>
        ) : (
          <div className="w-full space-y-1.5">
            {uploadedDocs.map((doc, i) => (
              <div key={i} className="flex items-center gap-2 group">
                <FileText className="w-3.5 h-3.5 text-muted-foreground/40 shrink-0" />
                <span className="text-sm truncate flex-1 text-foreground/70">{doc.name}</span>
                <span className={cn('text-[11px] shrink-0',
                  doc.status === 'done' ? 'text-green-600'
                    : doc.status === 'error' ? 'text-destructive'
                    : 'text-muted-foreground'
                )}>
                  {doc.status === 'uploading'
                    ? <Loader2 className="w-3 h-3 animate-spin inline" />
                    : doc.status === 'done' ? 'Uploaded' : 'Failed'}
                </span>
                <button
                  onClick={(e) => { e.stopPropagation(); setUploadedDocs(prev => prev.filter((_, idx) => idx !== i)); }}
                  className="p-0.5 text-muted-foreground/30 hover:text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
            <p className="text-[11px] text-muted-foreground/40 text-center pt-1">
              Click or drop to add more
            </p>
          </div>
        )}
      </div>

      {/* ── 2. Links input (always visible) ─────────────────────────────── */}
      <div className="mb-3">
        <div className="flex items-center gap-1.5 rounded-lg border border-border/50 px-3 py-2 focus-within:border-border focus-within:ring-1 focus-within:ring-primary/30 transition-all">
          <Link2 className="w-3.5 h-3.5 text-muted-foreground/40 shrink-0" />
          <input
            type="text"
            value={linkInput}
            onChange={e => { setLinkInput(e.target.value); setLinkError(null); }}
            onKeyDown={e => {
              if (e.key === 'Enter') { e.preventDefault(); addLink(); }
            }}
            placeholder="linkedin.com/in/you, yourcompany.com"
            className="flex-1 text-sm bg-transparent focus:outline-none placeholder:text-muted-foreground/30"
          />
          {linkInput.trim() && (
            <button
              onClick={addLink}
              className="p-0.5 text-muted-foreground hover:text-primary transition-colors shrink-0"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
        {linkError && <p className="text-[10px] text-destructive mt-1 pl-5">{linkError}</p>}
        {links.length > 0 && (
          <div className="mt-1.5 space-y-1 pl-1">
            {links.map((link, i) => (
              <div key={i} className="flex items-center gap-2 group">
                <Link2 className="w-3 h-3 text-muted-foreground/40 shrink-0" />
                <span className="text-[11px] text-foreground/60 truncate flex-1 font-mono">{link}</span>
                <button
                  onClick={() => setLinks(prev => prev.filter((_, idx) => idx !== i))}
                  className="p-0.5 text-muted-foreground/30 hover:text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── 3. Notes textarea (supplementary) ───────────────────────────── */}
      <textarea
        value={notes}
        onChange={e => setNotes(e.target.value)}
        placeholder="Anything else — your role, what you're working on, what you need..."
        rows={compact ? 2 : 3}
        className="w-full text-sm bg-transparent rounded-lg border border-border/50 px-3 py-2.5 focus:outline-none focus:border-border focus:ring-1 focus:ring-primary/30 resize-none placeholder:text-muted-foreground/30 mb-3 transition-all"
      />

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!canSubmit}
        className={cn(
          'w-full flex items-center justify-center gap-2 rounded-lg font-medium transition-colors',
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
        ) : (
          <>Get started <ArrowRight className="w-4 h-4" /></>
        )}
      </button>
    </div>
  );
}
