'use client';

/**
 * ContextSetup — Unified onboarding + context update surface.
 *
 * Replaces the 3 cold-start chips + IDENTITY_SETUP_CARD + BRAND_SETUP_CARD.
 * A self-contained component with URL inputs, file uploads, and free-text.
 * When submitted, composes a single message to TP with all inputs.
 *
 * Used in two contexts:
 * - Cold start empty state (replaces chips)
 * - Plus menu "Update my info" (replaces "Update identity" action card)
 */

import { useState, useRef, useCallback } from 'react';
import { X, Link2, Upload, FileText, Loader2, Plus, ArrowRight, ListChecks, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';

interface UploadedDoc {
  name: string;
  status: 'uploading' | 'done' | 'error';
}

interface ContextSetupProps {
  /** Called with the composed message when user submits */
  onSubmit: (message: string) => void;
  /** Called when user dismisses without submitting */
  onDismiss?: () => void;
  /** Show skip chips at the bottom (cold start only) */
  showSkipOptions?: boolean;
  /** Called when user clicks a skip option */
  onSkipAction?: (message: string) => void;
  /** Compact mode (for plus menu, smaller padding) */
  compact?: boolean;
}

export function ContextSetup({
  onSubmit,
  onDismiss,
  showSkipOptions = false,
  onSkipAction,
  compact = false,
}: ContextSetupProps) {
  // --- Links ---
  const [links, setLinks] = useState<string[]>([]);
  const [linkInput, setLinkInput] = useState('');
  const [linkError, setLinkError] = useState<string | null>(null);

  // --- Files ---
  const [uploadedDocs, setUploadedDocs] = useState<UploadedDoc[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- Notes ---
  const [notes, setNotes] = useState('');

  // --- State ---
  const [submitting, setSubmitting] = useState(false);

  const hasContent = links.length > 0 || uploadedDocs.some(d => d.status === 'done') || notes.trim().length > 0;
  const isUploading = uploadedDocs.some(d => d.status === 'uploading');

  // --- Link handlers ---
  const addLink = useCallback(() => {
    const url = linkInput.trim();
    if (!url) return;

    // Basic URL validation
    try {
      if (!url.startsWith('http://') && !url.startsWith('https://')) {
        new URL('https://' + url);
      } else {
        new URL(url);
      }
    } catch {
      setLinkError('Enter a valid URL');
      setTimeout(() => setLinkError(null), 3000);
      return;
    }

    const normalized = url.startsWith('http') ? url : 'https://' + url;
    if (links.includes(normalized)) {
      setLinkError('Already added');
      setTimeout(() => setLinkError(null), 3000);
      return;
    }

    setLinks(prev => [...prev, normalized]);
    setLinkInput('');
    setLinkError(null);
  }, [linkInput, links]);

  const removeLink = useCallback((index: number) => {
    setLinks(prev => prev.filter((_, i) => i !== index));
  }, []);

  const handleLinkKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') { e.preventDefault(); addLink(); }
  }, [addLink]);

  // --- File handlers ---
  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    for (const file of files) {
      const maxSize = file.type.startsWith('image/') ? 5 * 1024 * 1024 : 20 * 1024 * 1024;
      if (file.size > maxSize) continue;

      const docEntry: UploadedDoc = { name: file.name, status: 'uploading' };
      setUploadedDocs(prev => [...prev, docEntry]);

      try {
        await api.documents.upload(file);
        setUploadedDocs(prev =>
          prev.map(d => d.name === file.name && d.status === 'uploading' ? { ...d, status: 'done' } : d)
        );
      } catch {
        setUploadedDocs(prev =>
          prev.map(d => d.name === file.name && d.status === 'uploading' ? { ...d, status: 'error' } : d)
        );
      }
    }

    // Reset input so same file can be selected again
    e.target.value = '';
  }, []);

  const removeDoc = useCallback((index: number) => {
    setUploadedDocs(prev => prev.filter((_, i) => i !== index));
  }, []);

  // --- Submit ---
  const handleSubmit = useCallback(() => {
    if (!hasContent || isUploading) return;
    setSubmitting(true);

    const parts: string[] = [];

    // Notes first (most important context)
    if (notes.trim()) {
      parts.push(notes.trim());
    }

    // Links
    if (links.length > 0) {
      parts.push(`\nHere are some links about me and my work:\n${links.map(l => `- ${l}`).join('\n')}`);
    }

    // Uploaded files
    const doneDocs = uploadedDocs.filter(d => d.status === 'done');
    if (doneDocs.length > 0) {
      parts.push(`\nI've uploaded these files for reference:\n${doneDocs.map(d => `- ${d.name}`).join('\n')}`);
    }

    const message = parts.join('\n');
    onSubmit(message);
  }, [hasContent, isUploading, notes, links, uploadedDocs, onSubmit]);

  return (
    <div className={cn(
      'rounded-xl border border-border bg-background shadow-sm animate-in fade-in slide-in-from-bottom-3 duration-200',
      compact ? 'p-3' : 'p-4'
    )}>
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className={cn('font-medium', compact ? 'text-xs' : 'text-sm')}>
            Tell me about yourself and your work
          </p>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            Share anything — I'll figure out where it goes.
          </p>
        </div>
        {onDismiss && (
          <button onClick={onDismiss} className="p-1 text-muted-foreground/40 hover:text-muted-foreground rounded-md hover:bg-muted transition-colors">
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      <div className="space-y-3">
        {/* Links section */}
        <div>
          <label className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-1 mb-1.5">
            <Link2 className="w-3 h-3" />
            Links
          </label>
          {links.map((link, i) => (
            <div key={i} className="flex items-center gap-2 mb-1 group">
              <span className="text-[11px] text-foreground/80 truncate flex-1 font-mono bg-muted/50 px-2 py-1 rounded">
                {link}
              </span>
              <button onClick={() => removeLink(i)} className="p-0.5 text-muted-foreground/30 hover:text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}
          <div className="flex items-center gap-1.5">
            <input
              type="text"
              value={linkInput}
              onChange={e => { setLinkInput(e.target.value); setLinkError(null); }}
              onKeyDown={handleLinkKeyDown}
              placeholder="linkedin.com/in/..., yourcompany.com"
              className={cn(
                'flex-1 text-[11px] bg-muted/30 border rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary/50 placeholder:text-muted-foreground/30',
                linkError ? 'border-destructive/50' : 'border-border/50'
              )}
            />
            <button
              onClick={addLink}
              disabled={!linkInput.trim()}
              className="p-1.5 text-muted-foreground hover:text-primary disabled:opacity-30 transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          </div>
          {linkError && <p className="text-[10px] text-destructive mt-0.5">{linkError}</p>}
        </div>

        {/* Files section */}
        <div>
          <label className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-1 mb-1.5">
            <FileText className="w-3 h-3" />
            Files
          </label>
          {uploadedDocs.map((doc, i) => (
            <div key={i} className="flex items-center gap-2 mb-1 group">
              <span className="text-[11px] truncate flex-1">{doc.name}</span>
              <span className={cn('text-[10px]',
                doc.status === 'done' ? 'text-green-600' : doc.status === 'error' ? 'text-destructive' : 'text-muted-foreground'
              )}>
                {doc.status === 'uploading' ? <Loader2 className="w-3 h-3 animate-spin inline" /> : doc.status === 'done' ? '✓' : 'failed'}
              </span>
              <button onClick={() => removeDoc(i)} className="p-0.5 text-muted-foreground/30 hover:text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}
          <input ref={fileInputRef} type="file" accept=".pdf,.docx,.txt,.md" multiple onChange={handleFileSelect} className="hidden" />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-1.5 text-[11px] text-muted-foreground hover:text-foreground px-2 py-1.5 rounded border border-dashed border-border/50 hover:border-border w-full transition-colors"
          >
            <Upload className="w-3 h-3" />
            Upload files (PDF, DOCX, TXT, MD)
          </button>
        </div>

        {/* Notes section */}
        <div>
          <label className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-1 mb-1.5">
            <Sparkles className="w-3 h-3" />
            Notes
          </label>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="I'm a founder building... / I work in... / My team does..."
            rows={3}
            className="w-full text-[12px] bg-muted/30 border border-border/50 rounded px-2.5 py-2 focus:outline-none focus:ring-1 focus:ring-primary/50 resize-y placeholder:text-muted-foreground/30"
          />
        </div>
      </div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!hasContent || isUploading || submitting}
        className={cn(
          'w-full mt-3 flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-medium transition-colors',
          hasContent && !isUploading && !submitting
            ? 'bg-primary text-primary-foreground hover:bg-primary/90'
            : 'bg-muted text-muted-foreground cursor-not-allowed'
        )}
      >
        {submitting ? (
          <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Setting up...</>
        ) : isUploading ? (
          <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Uploading...</>
        ) : (
          <>Get started <ArrowRight className="w-3.5 h-3.5" /></>
        )}
      </button>

      {/* Skip options (cold start only) */}
      {showSkipOptions && onSkipAction && (
        <div className="mt-3 pt-3 border-t border-border/30">
          <p className="text-[10px] text-muted-foreground/50 mb-1.5">Already set up?</p>
          <div className="flex gap-1.5">
            <button
              onClick={() => onSkipAction('What can you track for me?')}
              className="flex-1 text-[10px] px-2 py-1.5 rounded border border-border/40 text-muted-foreground hover:text-foreground hover:border-border transition-colors"
            >
              What can you track?
            </button>
            <button
              onClick={() => onSkipAction('I want to create a task')}
              className="flex-1 flex items-center justify-center gap-1 text-[10px] px-2 py-1.5 rounded border border-border/40 text-muted-foreground hover:text-foreground hover:border-border transition-colors"
            >
              <ListChecks className="w-3 h-3" /> Create a task
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
