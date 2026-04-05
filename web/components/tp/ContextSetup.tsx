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
import { X, Link2, Upload, FileText, Loader2, Plus, ArrowRight, Sparkles } from 'lucide-react';
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
  /** Compact mode (for plus menu, smaller padding) */
  compact?: boolean;
}

export function ContextSetup({
  onSubmit,
  onDismiss,
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

  const hasContent = links.length > 0 || linkInput.trim().length > 0 || uploadedDocs.some(d => d.status === 'done') || notes.trim().length > 0;
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
    // Auto-add any pending link input before submitting
    let finalLinks = [...links];
    if (linkInput.trim()) {
      const url = linkInput.trim();
      const normalized = url.startsWith('http') ? url : 'https://' + url;
      try {
        new URL(normalized);
        if (!finalLinks.includes(normalized)) {
          finalLinks.push(normalized);
        }
      } catch { /* ignore invalid */ }
    }

    const hasFinalContent = finalLinks.length > 0 || uploadedDocs.some(d => d.status === 'done') || notes.trim().length > 0;
    if (!hasFinalContent || isUploading) return;
    setSubmitting(true);

    const parts: string[] = [];

    // Notes first (most important context)
    if (notes.trim()) {
      parts.push(notes.trim());
    }

    // Links — explicit format so TP knows to fetch them
    if (finalLinks.length > 0) {
      parts.push(`\nPlease read these links about me and my work:\n${finalLinks.map(l => `- ${l}`).join('\n')}\nFetch each URL and use the content to update my identity and brand.`);
    }

    // Uploaded files
    const doneDocs = uploadedDocs.filter(d => d.status === 'done');
    if (doneDocs.length > 0) {
      parts.push(`\nI've uploaded these files for reference:\n${doneDocs.map(d => `- ${d.name}`).join('\n')}`);
    }

    const message = parts.join('\n');
    onSubmit(message);
  }, [isUploading, notes, links, linkInput, uploadedDocs, onSubmit]);

  return (
    <div className={cn(
      'rounded-xl border border-border bg-background shadow-sm animate-in fade-in slide-in-from-bottom-3 duration-200',
      compact ? 'p-3' : 'p-6'
    )}>
      {/* Header */}
      <div className="flex items-start justify-between mb-5">
        <div>
          <p className={cn('font-medium', compact ? 'text-xs' : 'text-base')}>
            Tell me about yourself and your work
          </p>
          <p className={cn('text-muted-foreground mt-1', compact ? 'text-[11px]' : 'text-sm')}>
            Share anything — I'll figure out where it goes.
          </p>
        </div>
        {onDismiss && (
          <button onClick={onDismiss} className="p-1 text-muted-foreground/40 hover:text-muted-foreground rounded-md hover:bg-muted transition-colors">
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      <div className={cn('space-y-4', compact ? 'space-y-3' : 'space-y-5')}>
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
            rows={5}
            className="w-full text-sm bg-muted/30 border border-border/50 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-1 focus:ring-primary/50 resize-y placeholder:text-muted-foreground/30"
          />
        </div>
      </div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!hasContent || isUploading || submitting}
        className={cn(
          'w-full mt-5 flex items-center justify-center gap-2 rounded-lg font-medium transition-colors',
          compact ? 'py-2 text-xs mt-3' : 'py-3 text-sm',
          hasContent && !isUploading && !submitting
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
