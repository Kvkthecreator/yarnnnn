'use client';

/**
 * NewDesignSystemModal — the ONE creation flow for a design system
 * (DESIGN-SYSTEMS.md §6, the 2026-07-19 regroup).
 *
 * The first cut split creation into two landing buttons (Import · Derive) that
 * (1) forked one intent before the member had chosen it, (2) fired a blind file
 * picker with no explanation, and (3) reused the generic learn-from modal — a
 * redundant "what should it make?" step plus an UNCONSTRAINED source (a font or
 * a deck was selectable, nonsense-in → workspace pollution).
 *
 * This modal already KNOWS it is making a design system (no target step). It
 * asks the one real question — where does this look come from? — with two
 * source shapes:
 *   · IMPORT  — "I have an export": a .zip, EXPLAINED before the picker.
 *   · DERIVE  — "Derive from a source": evidence-of-a-look, FILTERED to
 *               look-carrying types (fonts/decks/data hidden + rejected).
 *
 * The modal owns the source choice + the guardrails; the parent owns the two
 * terminal actions (onImport writes the folder; onDerive creates the lane) so
 * navigation/refresh stay where the surface state lives. Portal + z-tier shell,
 * matching LearnFromFlowModal.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { ArrowLeft, FileText, Loader2, Palette, Upload } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';
import { api } from '@/lib/api/client';

// Look-carrying source types (DESIGN-SYSTEMS.md §6). A design system is derived
// from evidence of a LOOK — a brand guide, a styled page, a screenshot, a CSS
// export. NOT from a font (it IS a face, not a look), a deck (an artifact, not a
// source), or data. The list filters to these; upload's accept enforces them.
// A guardrail, not a guarantee — a .md could be a grocery list; this blocks the
// absurd and trusts the plausible.
const LOOK_SOURCE_EXTS = ['.md', '.html', '.htm', '.pdf', '.png', '.jpg', '.jpeg', '.webp', '.css'];
const LOOK_ACCEPT = LOOK_SOURCE_EXTS.join(',');

function leaf(p: string): string {
  return p.slice(p.lastIndexOf('/') + 1);
}
function isLookSource(path: string): boolean {
  const low = path.toLowerCase();
  return LOOK_SOURCE_EXTS.some((e) => low.endsWith(e));
}

interface NewDesignSystemModalProps {
  open: boolean;
  /** Whether the derive path is available (chat helpers enabled). Import always
   *  is — it is deterministic, no lane. */
  deriveEnabled: boolean;
  onClose: () => void;
  /** IMPORT a .zip → the folder. Throws so the failure shows inline; resolves
   *  with the receipt name so the modal can confirm + the parent refreshes. */
  onImport: (file: File) => Promise<{ name: string; written: number; warnings: number }>;
  /** DERIVE from a chosen source → the lane. Throws so failure shows inline; on
   *  success the parent navigates (the modal just closes). */
  onDerive: (source: { path: string; name: string }) => Promise<void>;
}

type Mode = 'choose' | 'import' | 'derive';

export function NewDesignSystemModal({
  open,
  deriveEnabled,
  onClose,
  onImport,
  onDerive,
}: NewDesignSystemModalProps) {
  const [mode, setMode] = useState<Mode>('choose');
  // derive state
  const [srcTab, setSrcTab] = useState<'files' | 'upload'>('files');
  const [rows, setRows] = useState<Array<{ path: string }> | null>(null);
  const [filter, setFilter] = useState('');
  const [source, setSource] = useState<{ path: string; name: string } | null>(null);
  const [uploading, setUploading] = useState(false);
  // shared
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [importMsg, setImportMsg] = useState<string | null>(null);
  const zipInputRef = useRef<HTMLInputElement>(null);
  const srcUploadRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    setMode('choose');
    setSrcTab('files');
    setRows(null);
    setFilter('');
    setSource(null);
    setUploading(false);
    setBusy(false);
    setErr(null);
    setImportMsg(null);
  }, [open]);

  // Load the recent files ONLY when the member enters the derive path — and
  // filter to look-carrying types at the source (fonts/decks never appear).
  useEffect(() => {
    if (mode !== 'derive' || rows !== null) return;
    api.workspace
      .recentRevisions(60)
      .then((res) => {
        const seen = new Set<string>();
        const out: Array<{ path: string }> = [];
        for (const r of res.revisions) {
          const p = r.path;
          if (seen.has(p) || leaf(p).startsWith('_') || p.endsWith('.extracted.md')) continue;
          if (!isLookSource(p)) continue; // the guardrail — hide non-look files
          seen.add(p);
          out.push({ path: p });
        }
        setRows(out);
      })
      .catch(() => setRows([]));
  }, [mode, rows]);

  const visible = useMemo(() => {
    if (!rows) return null;
    const f = filter.trim().toLowerCase();
    return f ? rows.filter((r) => r.path.toLowerCase().includes(f)) : rows;
  }, [rows, filter]);

  if (!open) return null;

  const runImport = async (file: File) => {
    setBusy(true);
    setErr(null);
    try {
      const r = await onImport(file);
      const warns = r.warnings ? ` · ${r.warnings} warning(s)` : '';
      setImportMsg(`Imported “${r.name}” — ${r.written} files${warns}.`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Import failed.');
    } finally {
      setBusy(false);
    }
  };

  const uploadSource = async (file: File) => {
    // Belt-and-braces on the accept filter: reject a non-look upload in the
    // member's words rather than deriving a design system from a font.
    if (!isLookSource(file.name)) {
      setErr('That file type can’t seed a look. Use a brand guide, a styled page, a screenshot, or a CSS export.');
      return;
    }
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

  const startDerive = async () => {
    if (!source || busy) return;
    setBusy(true);
    setErr(null);
    try {
      await onDerive(source); // parent navigates on success
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Could not start.');
      setBusy(false);
    }
  };

  const shell = 'inline-flex items-center gap-1.5 rounded-md px-3.5 py-1.5 text-sm font-medium transition-colors';

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
            {mode !== 'choose' && (
              <button
                type="button"
                onClick={() => {
                  setMode('choose');
                  setErr(null);
                  setImportMsg(null);
                }}
                className="text-muted-foreground transition-colors hover:text-foreground"
                aria-label="Back"
              >
                <ArrowLeft className="h-4 w-4" />
              </button>
            )}
            <Palette className="h-4 w-4" /> New design system
          </h3>

          {/* ── Choose: the ONE question — where does this look come from? ── */}
          {mode === 'choose' && (
            <>
              <p className="mt-3 text-sm text-muted-foreground">
                A design system is the look your artifacts wear — its colors, type,
                and shape. Start it one of two ways:
              </p>
              <div className="mt-3 space-y-2">
                <button
                  type="button"
                  onClick={() => setMode('import')}
                  className="flex w-full flex-col items-start rounded-lg border border-border p-3 text-left transition-colors hover:bg-muted/30"
                >
                  <span className="flex items-center gap-1.5 text-sm font-medium">
                    <Upload className="h-3.5 w-3.5" /> I have an export
                  </span>
                  <span className="mt-0.5 text-[11px] leading-snug text-muted-foreground">
                    A design-system <code>.zip</code> — tokens, styles, and fonts
                    (e.g. from Claude Design).
                  </span>
                </button>
                <button
                  type="button"
                  disabled={!deriveEnabled}
                  onClick={() => setMode('derive')}
                  title={deriveEnabled ? undefined : 'Chat helpers aren’t enabled on this workspace.'}
                  className="flex w-full flex-col items-start rounded-lg border border-border p-3 text-left transition-colors hover:bg-muted/30 disabled:opacity-40"
                >
                  <span className="flex items-center gap-1.5 text-sm font-medium">
                    <Palette className="h-3.5 w-3.5" /> Derive from a source
                  </span>
                  <span className="mt-0.5 text-[11px] leading-snug text-muted-foreground">
                    Point at something that <em>shows</em> your look — a brand
                    guide, a styled page, a screenshot — and it derives the tokens.
                  </span>
                </button>
              </div>
            </>
          )}

          {/* ── Import: explain BEFORE the picker, then confirm ── */}
          {mode === 'import' && (
            <>
              <p className="mt-3 text-sm text-muted-foreground">
                Choose a design-system export — a <code>.zip</code> of tokens,
                styles, and fonts. yarnnn flattens the stylesheets, carries the
                fonts, and writes a system your artifacts can wear.
              </p>
              <input
                ref={zipInputRef}
                type="file"
                accept=".zip"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) void runImport(f);
                  e.target.value = '';
                }}
              />
              <button
                type="button"
                disabled={busy}
                onClick={() => zipInputRef.current?.click()}
                className="mt-3 flex w-full flex-col items-center gap-1.5 rounded-md border border-dashed border-border p-6 text-sm text-muted-foreground transition-colors hover:bg-muted/20 disabled:opacity-50"
              >
                {busy ? <Loader2 className="h-5 w-5 animate-spin" /> : <Upload className="h-5 w-5" />}
                {busy ? 'Importing…' : 'Choose a .zip export…'}
              </button>
              {importMsg && <p className="mt-2 text-xs text-emerald-600">{importMsg}</p>}
            </>
          )}

          {/* ── Derive: type-filtered source, then Start ── */}
          {mode === 'derive' && (
            <>
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
                  <p className="mt-3 text-[11px] text-muted-foreground">
                    Pick something that <em>shows</em> your look. Fonts, decks, and
                    data files aren’t listed — they don’t carry a design.
                  </p>
                  <div className="mt-2 grid grid-cols-2 gap-1 rounded-md border border-border p-1">
                    {(
                      [
                        ['files', 'From your files'],
                        ['upload', 'Upload'],
                      ] as const
                    ).map(([m, label]) => (
                      <button
                        key={m}
                        type="button"
                        onClick={() => setSrcTab(m)}
                        className={cn(
                          'rounded px-2 py-1.5 text-xs font-medium transition-colors',
                          srcTab === m ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground',
                        )}
                      >
                        {label}
                      </button>
                    ))}
                  </div>

                  {srcTab === 'files' ? (
                    <>
                      <input
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                        placeholder="Filter files…"
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
                            No look-carrying files yet — try Upload.
                          </p>
                        ) : (
                          <ul className="space-y-1">
                            {visible.slice(0, 40).map((r) => (
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
                        ref={srcUploadRef}
                        type="file"
                        accept={LOOK_ACCEPT}
                        className="hidden"
                        onChange={(e) => {
                          const f = e.target.files?.[0];
                          if (f) void uploadSource(f);
                          e.target.value = '';
                        }}
                      />
                      <button
                        type="button"
                        disabled={uploading}
                        onClick={() => srcUploadRef.current?.click()}
                        className="flex w-full flex-col items-center gap-1.5 rounded-md border border-dashed border-border p-6 text-sm text-muted-foreground transition-colors hover:bg-muted/20 disabled:opacity-50"
                      >
                        {uploading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Upload className="h-5 w-5" />}
                        {uploading ? 'Uploading…' : 'Upload a brand guide, screenshot, or CSS…'}
                      </button>
                    </div>
                  )}
                </>
              )}

              <div className="mt-4 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={onClose}
                  className={cn(shell, 'border border-border text-foreground hover:bg-muted/60')}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={!source || busy}
                  onClick={() => void startDerive()}
                  className={cn(
                    shell,
                    source && !busy
                      ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                      : 'cursor-not-allowed bg-muted text-muted-foreground',
                  )}
                >
                  {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Start
                </button>
              </div>
            </>
          )}

          {err && <p className="mt-2 text-xs text-destructive">{err}</p>}

          {/* Choose + import don't have their own footer button row; a done/close
              lives in the header back-arrow + backdrop. Import shows Done once a
              system landed so the member has a deliberate exit. */}
          {(mode === 'choose' || (mode === 'import' && !busy)) && (
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={onClose}
                className={cn(shell, 'border border-border text-foreground hover:bg-muted/60')}
              >
                {importMsg ? 'Done' : 'Cancel'}
              </button>
            </div>
          )}
        </div>
      </div>
    </>,
    document.body,
  );
}
