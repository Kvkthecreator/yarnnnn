'use client';

/**
 * TaskSetup — Structured intent capture for task creation.
 *
 * Mirrors ContextSetup's interaction shape (links + files + notes → composed
 * message → onSubmit → TP calls ManageTask(create)) but for task creation
 * rather than identity onboarding.
 *
 * Two-screen flow:
 *   Screen 0 — Route selection: "Track something" vs "Get a deliverable"
 *   Screen 1B — Route B: domain + cadence + sources + material injection
 *   Screen 1A — Route A: surface + mode + cadence + delivery + material injection
 *
 * The composed message is a complete intent statement TP can act on in one
 * turn without clarifying. See docs/design/TASK-SETUP-FLOW.md for full spec.
 *
 * Governed by ADR-178 (Task Creation Routes).
 * Parallel to ContextSetup.tsx (same material injection layer).
 */

import React, { useState, useRef, useCallback } from 'react';
import {
  X, Link2, Upload, FileText, Loader2, Plus, ArrowRight,
  Sparkles, ChevronLeft, BarChart2, Database,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Route = 'track' | 'deliverable' | null;

type TrackDomain = 'competitors' | 'market' | 'relationships' | 'projects' | 'custom';
type Cadence = 'daily' | 'weekly' | 'monthly';
type DeliverableSurface = 'report' | 'deck' | 'dashboard' | 'digest';
type DeliverableMode = 'recurring' | 'one-time';
type DeliveryMethod = 'email' | 'in-app';
type TrackSource = 'web' | 'slack' | 'notion' | 'github';

interface UploadedDoc {
  name: string;
  status: 'uploading' | 'done' | 'error';
}

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const TRACK_DOMAINS: { value: TrackDomain; label: string }[] = [
  { value: 'competitors', label: 'Competitors' },
  { value: 'market', label: 'Market' },
  { value: 'relationships', label: 'Relationships' },
  { value: 'projects', label: 'Projects' },
  { value: 'custom', label: 'Custom' },
];

const DELIVERABLE_SURFACES: { value: DeliverableSurface; label: string; icon?: React.ReactNode }[] = [
  { value: 'report', label: 'Report' },
  { value: 'deck', label: 'Deck' },
  { value: 'dashboard', label: 'Dashboard' },
  { value: 'digest', label: 'Digest' },
];

const CADENCES: { value: Cadence; label: string }[] = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ChipGroup<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: T; label: string }[];
  value: T | null;
  onChange: (v: T) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map(opt => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={cn(
            'px-3 py-1.5 rounded-full text-xs font-medium border transition-colors',
            value === opt.value
              ? 'bg-primary text-primary-foreground border-primary'
              : 'border-border text-muted-foreground hover:border-foreground/40 hover:text-foreground bg-background'
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Material injection layer (identical pattern to ContextSetup)
// ---------------------------------------------------------------------------

interface MaterialLayerProps {
  links: string[];
  setLinks: (links: string[]) => void;
  uploadedDocs: UploadedDoc[];
  setUploadedDocs: React.Dispatch<React.SetStateAction<UploadedDoc[]>>;
  notes: string;
  setNotes: (notes: string) => void;
  notesPlaceholder: string;
  linksPlaceholder: string;
}

function MaterialLayer({
  links,
  setLinks,
  uploadedDocs,
  setUploadedDocs,
  notes,
  setNotes,
  notesPlaceholder,
  linksPlaceholder,
}: MaterialLayerProps) {
  const [linkInput, setLinkInput] = useState('');
  const [linkError, setLinkError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
      setLinks([...links, normalized]);
      setLinkInput('');
      setLinkError(null);
    } catch {
      setLinkError('Enter a valid URL');
      setTimeout(() => setLinkError(null), 3000);
    }
  }, [linkInput, links, setLinks]);

  const removeLink = (index: number) => setLinks(links.filter((_, i) => i !== index));

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
  }, [setUploadedDocs]);

  const removeDoc = (index: number) => setUploadedDocs(uploadedDocs.filter((_, i) => i !== index));

  return (
    <div className="space-y-4 border-t border-border/50 pt-4 mt-4">
      <p className="text-[10px] text-muted-foreground/50 uppercase tracking-wide font-medium">
        Reference materials (optional)
      </p>

      {/* Links */}
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
            onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addLink(); } }}
            placeholder={linksPlaceholder}
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

      {/* Files */}
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

      {/* Notes */}
      <div>
        <label className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-1 mb-1.5">
          <Sparkles className="w-3 h-3" />
          Notes
        </label>
        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          placeholder={notesPlaceholder}
          rows={4}
          className="w-full text-sm bg-muted/30 border border-border/50 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-1 focus:ring-primary/50 resize-y placeholder:text-muted-foreground/30"
        />
      </div>
    </div>
  );
}

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
  // Screen state
  const [route, setRoute] = useState<Route>(null);

  // Route B — Track state
  const [trackDomain, setTrackDomain] = useState<TrackDomain | null>(null);
  const [trackCadence, setTrackCadence] = useState<Cadence | null>('weekly');
  const [trackSources, setTrackSources] = useState<Set<TrackSource>>(new Set<TrackSource>(['web']));

  // Route A — Deliverable state
  const [surface, setSurface] = useState<DeliverableSurface | null>(null);
  const [deliverableMode, setDeliverableMode] = useState<DeliverableMode | null>('recurring');
  const [deliverableCadence, setDeliverableCadence] = useState<Cadence | null>('weekly');
  const [delivery, setDelivery] = useState<DeliveryMethod>('email');

  // Shared material state
  const [links, setLinks] = useState<string[]>([]);
  const [uploadedDocs, setUploadedDocs] = useState<UploadedDoc[]>([]);
  const [notes, setNotes] = useState(initialNotes);

  // Submit state
  const [submitting, setSubmitting] = useState(false);

  const isUploading = uploadedDocs.some(d => d.status === 'uploading');

  // Source toggle helper
  const toggleSource = (src: TrackSource) => {
    setTrackSources(prev => {
      const next = new Set(prev);
      if (next.has(src)) {
        if (next.size > 1) next.delete(src); // always keep at least one
      } else {
        next.add(src);
      }
      return next;
    });
  };

  // Build + submit the composed message
  const handleSubmit = useCallback(() => {
    if (submitting || isUploading) return;
    setSubmitting(true);

    const doneDocs = uploadedDocs.filter(d => d.status === 'done');
    const parts: string[] = [];

    if (route === 'track') {
      const domain = trackDomain ?? 'custom';
      const cadence = trackCadence ?? 'weekly';
      const sourceList = Array.from(trackSources).join(', ');

      parts.push(`I want to track ${domain}${notes.trim() ? ` — specifically: ${notes.trim()}` : ''}.`);
      parts.push(`Cadence: ${cadence}. Sources: ${sourceList}.`);

      if (links.length > 0) {
        parts.push(`Please fetch these to discover and create initial entity profiles:\n${links.map(l => `- ${l}`).join('\n')}`);
      }
      if (doneDocs.length > 0) {
        parts.push(`I've uploaded context to seed this domain:\n${doneDocs.map(d => `- ${d.name}`).join('\n')}`);
      }
    } else {
      // Route A — deliverable
      const surf = surface ?? 'report';
      const mode = deliverableMode ?? 'recurring';
      const cadence = deliverableCadence ?? 'weekly';

      const modeStr = mode === 'recurring' ? `recurring, ${cadence}` : 'one-time goal';
      parts.push(`I want a ${surf}${notes.trim() ? ` — ${notes.trim()}` : ''}.`);
      parts.push(`Mode: ${modeStr}. Delivery: ${delivery === 'email' ? 'email' : 'in-app only'}.`);

      if (links.length > 0) {
        parts.push(`Reference materials — fetch each and use to shape DELIVERABLE.md:\n${links.map(l => `- ${l}`).join('\n')}`);
      }
      if (doneDocs.length > 0) {
        parts.push(`I've uploaded reference materials:\n${doneDocs.map(d => `- ${d.name}`).join('\n')}`);
      }
    }

    onSubmit(parts.join('\n'));
  }, [
    submitting, isUploading, route, trackDomain, trackCadence, trackSources,
    surface, deliverableMode, deliverableCadence, delivery,
    notes, links, uploadedDocs, onSubmit,
  ]);

  // Can submit?
  const canSubmitTrack = route === 'track' && !!trackDomain;
  const canSubmitDeliverable = route === 'deliverable' && !!surface;
  const canSubmit = (canSubmitTrack || canSubmitDeliverable) && !isUploading && !submitting;

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className={cn(
      'bg-background animate-in fade-in slide-in-from-bottom-3 duration-200',
      !embedded && 'rounded-xl border border-border shadow-sm',
      compact ? 'p-3' : 'p-6'
    )}>
      {/* Header */}
      <div className="flex items-start justify-between mb-5">
        <div className="flex items-center gap-2">
          {route !== null && (
            <button
              onClick={() => setRoute(null)}
              className="p-1 text-muted-foreground/40 hover:text-muted-foreground rounded-md hover:bg-muted transition-colors"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
          )}
          <div>
            <p className={cn('font-medium', compact ? 'text-xs' : 'text-base')}>
              {route === null && 'What do you want to work on?'}
              {route === 'track' && 'Track something'}
              {route === 'deliverable' && 'Get a deliverable'}
            </p>
            <p className={cn('text-muted-foreground mt-0.5', compact ? 'text-[11px]' : 'text-sm')}>
              {route === null && "I'll set it up and keep it running."}
              {route === 'track' && 'Build a living knowledge base over time.'}
              {route === 'deliverable' && 'Receive a polished output on a schedule.'}
            </p>
          </div>
        </div>
        {onDismiss && (
          <button onClick={onDismiss} className="p-1 text-muted-foreground/40 hover:text-muted-foreground rounded-md hover:bg-muted transition-colors">
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* ── Screen 0: Route selection ── */}
      {route === null && (
        <div className="space-y-2">
          <button
            onClick={() => setRoute('track')}
            className="w-full text-left rounded-lg border border-border bg-muted/20 hover:bg-muted/50 hover:border-foreground/20 px-4 py-3.5 transition-colors group"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-md bg-background border border-border group-hover:border-foreground/20 transition-colors">
                <Database className="w-4 h-4 text-muted-foreground" />
              </div>
              <div>
                <p className="text-sm font-medium">Track something</p>
                <p className="text-xs text-muted-foreground mt-0.5">Competitors, markets, relationships, channels, signals</p>
              </div>
              <ArrowRight className="w-4 h-4 text-muted-foreground/30 ml-auto group-hover:text-muted-foreground transition-colors" />
            </div>
          </button>

          <button
            onClick={() => setRoute('deliverable')}
            className="w-full text-left rounded-lg border border-border bg-muted/20 hover:bg-muted/50 hover:border-foreground/20 px-4 py-3.5 transition-colors group"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-md bg-background border border-border group-hover:border-foreground/20 transition-colors">
                <BarChart2 className="w-4 h-4 text-muted-foreground" />
              </div>
              <div>
                <p className="text-sm font-medium">Get a deliverable</p>
                <p className="text-xs text-muted-foreground mt-0.5">Report, deck, digest, blog post, dashboard</p>
              </div>
              <ArrowRight className="w-4 h-4 text-muted-foreground/30 ml-auto group-hover:text-muted-foreground transition-colors" />
            </div>
          </button>
        </div>
      )}

      {/* ── Screen 1B: Track ── */}
      {route === 'track' && (
        <div className="space-y-4">
          {/* Domain */}
          <div>
            <label className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide block mb-1.5">
              Domain
            </label>
            <ChipGroup
              options={TRACK_DOMAINS}
              value={trackDomain}
              onChange={setTrackDomain}
            />
          </div>

          {/* Cadence */}
          <div>
            <label className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide block mb-1.5">
              How often
            </label>
            <ChipGroup
              options={CADENCES}
              value={trackCadence}
              onChange={setTrackCadence}
            />
          </div>

          {/* Sources */}
          <div>
            <label className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide block mb-1.5">
              Sources
            </label>
            <div className="flex flex-wrap gap-1.5">
              {(['web', 'slack', 'notion', 'github'] as TrackSource[]).map(src => (
                <button
                  key={src}
                  onClick={() => toggleSource(src)}
                  className={cn(
                    'px-3 py-1.5 rounded-full text-xs font-medium border transition-colors',
                    trackSources.has(src)
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'border-border text-muted-foreground hover:border-foreground/40 hover:text-foreground bg-background'
                  )}
                >
                  {src === 'web' ? '✓ ' : ''}{src.charAt(0).toUpperCase() + src.slice(1)}
                  {src !== 'web' && <span className="text-[9px] ml-1 opacity-50">requires connection</span>}
                </button>
              ))}
            </div>
          </div>

          {/* Material injection */}
          <MaterialLayer
            links={links}
            setLinks={setLinks}
            uploadedDocs={uploadedDocs}
            setUploadedDocs={setUploadedDocs}
            notes={notes}
            setNotes={setNotes}
            linksPlaceholder="competitor sites, market pages, GitHub repos to seed entities"
            notesPlaceholder="Track Cursor, Linear, Notion. Focused on pricing + product changes."
          />
        </div>
      )}

      {/* ── Screen 1A: Deliverable ── */}
      {route === 'deliverable' && (
        <div className="space-y-4">
          {/* Surface */}
          <div>
            <label className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide block mb-1.5">
              Surface
            </label>
            <ChipGroup
              options={DELIVERABLE_SURFACES}
              value={surface}
              onChange={setSurface}
            />
          </div>

          {/* Mode */}
          <div>
            <label className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide block mb-1.5">
              Mode
            </label>
            <div className="space-y-1.5">
              {([
                { value: 'recurring' as DeliverableMode, label: 'Recurring', sub: 'runs on a schedule indefinitely' },
                { value: 'one-time' as DeliverableMode, label: 'One-time', sub: 'has a completion event (launch, board date, meeting)' },
              ] as { value: DeliverableMode; label: string; sub: string }[]).map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setDeliverableMode(opt.value)}
                  className={cn(
                    'w-full text-left px-3 py-2 rounded-lg border text-xs transition-colors',
                    deliverableMode === opt.value
                      ? 'bg-primary/10 border-primary text-foreground'
                      : 'border-border text-muted-foreground hover:border-foreground/30 hover:text-foreground bg-background'
                  )}
                >
                  <span className="font-medium">{opt.label}</span>
                  <span className="text-muted-foreground ml-1.5">— {opt.sub}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Cadence — only shown for recurring */}
          {deliverableMode === 'recurring' && (
            <div>
              <label className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide block mb-1.5">
                Cadence
              </label>
              <ChipGroup
                options={CADENCES}
                value={deliverableCadence}
                onChange={setDeliverableCadence}
              />
            </div>
          )}

          {/* Delivery */}
          <div>
            <label className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide block mb-1.5">
              Delivery
            </label>
            <ChipGroup
              options={[
                { value: 'email' as DeliveryMethod, label: 'Email me' },
                { value: 'in-app' as DeliveryMethod, label: 'View in app' },
              ]}
              value={delivery}
              onChange={setDelivery}
            />
          </div>

          {/* Material injection */}
          <MaterialLayer
            links={links}
            setLinks={setLinks}
            uploadedDocs={uploadedDocs}
            setUploadedDocs={setUploadedDocs}
            notes={notes}
            setNotes={setNotes}
            linksPlaceholder="example reports to emulate, reference sources"
            notesPlaceholder="Weekly competitive brief. 2 pages max. Focus on pricing changes."
          />
        </div>
      )}

      {/* Submit — only shown on Screen 1 */}
      {route !== null && (
        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className={cn(
            'w-full mt-5 flex items-center justify-center gap-2 rounded-lg font-medium transition-colors',
            compact ? 'py-2 text-xs mt-3' : 'py-3 text-sm',
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
      )}
    </div>
  );
}
