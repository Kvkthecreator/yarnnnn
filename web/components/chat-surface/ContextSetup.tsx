'use client';

/**
 * ContextSetup — Identity capture for the onboarding modal (ADR-144).
 *
 * Composes ComposerInput for the shared textarea + links + files input
 * surface. Owns the message composition logic specific to identity capture:
 * notes are sent as-is (user's words), links carry a "read these about me"
 * instruction, files are listed as uploaded references.
 *
 * On submit, the composed message is forwarded to TP which calls
 * UpdateContext + ManageDomains — no clarifying rounds.
 *
 * Sole consumer: OnboardingModal (embedded mode).
 * See: docs/design/COMPOSER-INPUT-PATTERN.md (shared primitive rationale)
 *      docs/adr/ADR-165-workspace-state-surface.md
 *      docs/adr/ADR-144-inference-first-shared-context.md
 */

import { useState, useCallback } from 'react';
import { X, ArrowRight, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ComposerInput, type UploadedDoc } from './ComposerInput';

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
  const [uploadedDocs, setUploadedDocs] = useState<UploadedDoc[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const isUploading = uploadedDocs.some(d => d.status === 'uploading');
  const canSubmit =
    (notes.trim().length > 0 || links.length > 0 || uploadedDocs.some(d => d.status === 'done')) &&
    !isUploading &&
    !submitting;

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
            Share anything — I'll figure out where it goes.
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

      {/* Unified composer input */}
      <ComposerInput
        notes={notes}
        onNotesChange={setNotes}
        links={links}
        onLinksChange={setLinks}
        uploadedDocs={uploadedDocs}
        onUploadedDocsChange={setUploadedDocs}
        placeholder="I'm a founder building... / I work in... / My team does..."
        linkPlaceholder="linkedin.com/in/..., yourcompany.com"
        rows={5}
        className="mb-3"
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
