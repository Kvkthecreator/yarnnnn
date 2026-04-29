'use client';

/**
 * RecurrenceSetup — Structured intent capture for recurrence creation (ADR-178 + ADR-231).
 *
 * Composes ComposerInput for the shared textarea + links + files input
 * surface. Owns the logic specific to recurrence creation: route toggle
 * (track vs deliverable), route-adaptive placeholders, and composed message
 * format that YARNNN uses to call
 * `UpdateContext(target='recurrence', action='create', ...)` in the same turn.
 *
 * Route A (deliverable): user anchors on an output. YARNNN reverse-engineers
 *   context needs. Links seed DELIVERABLE.md; files shape the output spec.
 * Route B (track): user anchors on a domain. YARNNN works forward. Links seed
 *   entity profiles; files seed domain context.
 *
 * Consumers: RecurrenceSetupModal (all four surfaces — /chat, /work, /agents,
 *   /context).
 * See: docs/design/COMPOSER-INPUT-PATTERN.md (shared primitive rationale)
 *      docs/adr/ADR-178-task-creation-routes.md
 *      docs/adr/ADR-231-task-abstraction-sunset.md
 */

import { useState, useCallback, useEffect } from 'react';
import { ArrowRight, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ComposerInput, type UploadedDoc } from './ComposerInput';

// ---------------------------------------------------------------------------
// Types + config
// ---------------------------------------------------------------------------

type Route = 'track' | 'deliverable';

const ROUTES: { value: Route; label: string }[] = [
  { value: 'track', label: 'Set up recurring work' },
  { value: 'deliverable', label: 'I have something specific in mind' },
];

const PLACEHOLDERS: Record<Route, string> = {
  track: 'Track Cursor, Linear, Notion. Focused on pricing and product changes.',
  deliverable: 'A weekly competitive brief. 2 pages, pricing focus. Email me Monday mornings.',
};

const LINK_PLACEHOLDERS: Record<Route, string> = {
  track: 'competitor sites, market pages, GitHub repos...',
  deliverable: 'example reports, reference sources...',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface RecurrenceSetupProps {
  /** Called with the composed message when user submits */
  onSubmit: (message: string) => void;
  /** Compact mode (smaller padding) */
  compact?: boolean;
  /** Embedded mode — parent provides the outer frame */
  embedded?: boolean;
  /** Pre-fill notes (e.g. from Heads Up with idle agent names) */
  initialNotes?: string;
}

export function RecurrenceSetup({
  onSubmit,
  compact = false,
  embedded = false,
  initialNotes = '',
}: RecurrenceSetupProps) {
  const [route, setRoute] = useState<Route>('track');
  const [notes, setNotes] = useState(initialNotes);
  const [links, setLinks] = useState<string[]>([]);
  const [uploadedDocs, setUploadedDocs] = useState<UploadedDoc[]>([]);
  const [submitting, setSubmitting] = useState(false);

  // Sync initialNotes when opened from different triggers (e.g. Heads Up)
  useEffect(() => { setNotes(initialNotes); }, [initialNotes]);

  const isUploading = uploadedDocs.some(d => d.status === 'uploading');
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
      const trackText = notes.trim();
      const trackSentence = trackText.endsWith('.') ? trackText : trackText + '.';
      parts.push(trackText ? `I want to track ${trackSentence}` : 'I want to set up recurring tracking work.');
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

  return (
    <div className={cn(
      'bg-background animate-in fade-in slide-in-from-bottom-3 duration-200',
      !embedded && 'rounded-xl border border-border shadow-sm',
      compact ? 'p-3' : 'p-4'
    )}>
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

      {/* Unified composer input */}
      <ComposerInput
        notes={notes}
        onNotesChange={setNotes}
        links={links}
        onLinksChange={setLinks}
        uploadedDocs={uploadedDocs}
        onUploadedDocsChange={setUploadedDocs}
        placeholder={PLACEHOLDERS[route]}
        linkPlaceholder={LINK_PLACEHOLDERS[route]}
        rows={4}
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
        ) : route === 'track' ? (
          <>Set up tracking <ArrowRight className="w-4 h-4" /></>
        ) : (
          <>Set up deliverable <ArrowRight className="w-4 h-4" /></>
        )}
      </button>
    </div>
  );
}
