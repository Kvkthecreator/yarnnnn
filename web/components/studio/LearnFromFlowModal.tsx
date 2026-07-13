'use client';

/**
 * LearnFromFlowModal — the Learn-from creation flow (ADR-452 v2, source-first).
 *
 * One modal, progressive disclosure: first the SOURCE ("learn from THIS…"),
 * with exactly two ways to answer — a file already in the workspace (the
 * recents feed + filter) OR an upload (the canonical case: "I have this thing
 * and it isn't in the workspace yet" — it lands through the ADR-395 lane and
 * becomes the source). Once a source is chosen, the TARGET cards activate
 * ("…make me THAT"). Start runs the creation flow the landing owns.
 *
 * Supersedes SourcePickerModal (the target-first v1). RenameModal shell.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { FileText, Loader2, Sparkles, Upload } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';
import { api } from '@/lib/api/client';

export interface LearnTarget {
  recipe: string;
  template: 'document' | 'deck' | null;
  label: string;
  description: string;
}

interface LearnFromFlowModalProps {
  open: boolean;
  targets: LearnTarget[];
  onClose: () => void;
  /** Run the creation flow — throws so the failure shows inline here. */
  onStart: (source: { path: string; name: string }, target: LearnTarget) => Promise<void>;
}

function leaf(p: string): string {
  return p.slice(p.lastIndexOf('/') + 1);
}

export function LearnFromFlowModal({ open, targets, onClose, onStart }: LearnFromFlowModalProps) {
  const [mode, setMode] = useState<'files' | 'upload'>('files');
  const [rows, setRows] = useState<Array<{ path: string }> | null>(null);
  const [filter, setFilter] = useState('');
  const [source, setSource] = useState<{ path: string; name: string } | null>(null);
  const [target, setTarget] = useState<LearnTarget | null>(null);
  const [uploading, setUploading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    setMode('files');
    setRows(null);
    setFilter('');
    setSource(null);
    setTarget(null);
    setUploading(false);
    setBusy(false);
    setErr(null);
    api.workspace
      .recentRevisions(40)
      .then((res) => {
        // Dedup by path, newest first; hide machine-config + the extraction
        // plumbing (the raw is the source; its projection is read by the lane).
        const seen = new Set<string>();
        const out: Array<{ path: string }> = [];
        for (const r of res.revisions) {
          const p = r.path;
          if (seen.has(p) || leaf(p).startsWith('_') || p.endsWith('.extracted.md')) continue;
          seen.add(p);
          out.push({ path: p });
        }
        setRows(out);
      })
      .catch(() => setRows([]));
  }, [open]);

  const visible = useMemo(() => {
    if (!rows) return null;
    const f = filter.trim().toLowerCase();
    return f ? rows.filter((r) => r.path.toLowerCase().includes(f)) : rows;
  }, [rows, filter]);

  if (!open) return null;

  const uploadFile = async (file: File) => {
    setUploading(true);
    setErr(null);
    try {
      const res = await api.documents.upload(file);
      const first = res.results?.[0];
      if (first?.success && first.workspace_path) {
        setSource({ path: first.workspace_path, name: first.filename });
      } else {
        setErr(first?.error || 'Upload failed.');
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Upload failed.');
    } finally {
      setUploading(false);
    }
  };

  const start = async () => {
    if (!source || !target || busy) return;
    setBusy(true);
    setErr(null);
    try {
      await onStart(source, target);
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Could not start.');
      setBusy(false);
    }
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
          className="pointer-events-auto flex max-h-[80vh] w-full max-w-md flex-col rounded-lg border border-border bg-card p-5 shadow-xl animate-in fade-in zoom-in-95 duration-150"
          role="dialog"
          aria-modal="true"
        >
          <h3 className="flex items-center gap-1.5 text-base font-semibold text-card-foreground">
            <Sparkles className="h-4 w-4" /> Learn from
          </h3>

          {/* ── Step 1: the source ─────────────────────────────────────── */}
          {source ? (
            <div className="mt-3 flex items-center justify-between gap-2 rounded-md border border-primary/40 bg-primary/5 px-3 py-2">
              <span className="min-w-0">
                <span className="block truncate text-sm text-foreground">{source.name}</span>
                <span className="block truncate text-[11px] text-muted-foreground">
                  {source.path.replace(/^\/workspace\//, '')}
                </span>
              </span>
              <button
                type="button"
                onClick={() => setSource(null)}
                className="shrink-0 text-xs text-muted-foreground underline-offset-2 hover:underline"
              >
                Change
              </button>
            </div>
          ) : (
            <>
              <div className="mt-3 grid grid-cols-2 gap-1 rounded-md border border-border p-1">
                {(
                  [
                    ['files', 'From your files'],
                    ['upload', 'Upload'],
                  ] as const
                ).map(([m, label]) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setMode(m)}
                    className={cn(
                      'rounded px-2 py-1.5 text-xs font-medium transition-colors',
                      mode === m ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground',
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {mode === 'files' ? (
                <>
                  <input
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                    placeholder="Filter recent files…"
                    className="mt-2 w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                    aria-label="Filter files"
                  />
                  <div className="mt-1.5 min-h-0 flex-1 overflow-y-auto" style={{ maxHeight: '30vh' }}>
                    {visible === null ? (
                      <div className="flex items-center justify-center gap-2 p-6 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" /> Loading…
                      </div>
                    ) : visible.length === 0 ? (
                      <p className="p-6 text-center text-sm text-muted-foreground">
                        Nothing matches — try Upload instead.
                      </p>
                    ) : (
                      <ul className="space-y-1">
                        {visible.slice(0, 30).map((r) => (
                          <li key={r.path}>
                            <button
                              type="button"
                              onClick={() => setSource({ path: r.path, name: leaf(r.path) })}
                              className="flex w-full items-center gap-2 rounded-md border border-transparent px-2 py-1.5 text-left transition-colors hover:border-border hover:bg-muted/40"
                            >
                              <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                              <span className="min-w-0">
                                <span className="block truncate text-sm text-foreground">{leaf(r.path)}</span>
                                <span className="block truncate text-[11px] text-muted-foreground">
                                  {r.path.replace(/^\/workspace\//, '')}
                                </span>
                              </span>
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </>
              ) : (
                <div className="mt-2">
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) void uploadFile(f);
                      e.target.value = '';
                    }}
                  />
                  <button
                    type="button"
                    disabled={uploading}
                    onClick={() => fileInputRef.current?.click()}
                    className="flex w-full flex-col items-center gap-1.5 rounded-md border border-dashed border-border p-6 text-sm text-muted-foreground transition-colors hover:bg-muted/20 disabled:opacity-50"
                  >
                    {uploading ? (
                      <Loader2 className="h-5 w-5 animate-spin" />
                    ) : (
                      <Upload className="h-5 w-5" />
                    )}
                    {uploading ? 'Uploading…' : 'Choose a file (PDF, Word, markdown…)'}
                  </button>
                </div>
              )}
            </>
          )}

          {/* ── Step 2: the target (activates once a source is chosen) ──── */}
          <p className="mt-4 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            What should it make?
          </p>
          <div className="mt-1.5 grid grid-cols-3 gap-2">
            {targets.map((t) => (
              <button
                key={t.recipe}
                type="button"
                disabled={!source}
                onClick={() => setTarget(t)}
                className={cn(
                  'rounded-lg border p-2.5 text-left transition-colors disabled:opacity-40',
                  target?.recipe === t.recipe
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:bg-muted/20',
                )}
              >
                <p className="text-sm font-medium">{t.label}</p>
                <p className="mt-0.5 text-[10px] leading-snug text-muted-foreground">{t.description}</p>
              </button>
            ))}
          </div>

          {err && <p className="mt-2 text-xs text-destructive">{err}</p>}
          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-border px-3.5 py-1.5 text-sm text-foreground transition-colors hover:bg-muted/60"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={!source || !target || busy}
              onClick={() => void start()}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-md px-3.5 py-1.5 text-sm font-medium transition-colors',
                source && target && !busy
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                  : 'cursor-not-allowed bg-muted text-muted-foreground',
              )}
            >
              {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Start
            </button>
          </div>
        </div>
      </div>
    </>,
    document.body,
  );
}
