'use client';

/**
 * StudioShareExport — the boundary acts (Share · Export) as HEADER verbs
 * (2026-07-24 relocation).
 *
 * Share and Export are document-global acts that lived as Properties-pane
 * sections (ADR-458 D3 / ADR-466 D6). But the Properties pane is the SHAPING
 * home — tokens, measures, scopes — and the boundary acts were the only rows
 * there that never touch the artifact's form. They now sit in the toolbar row,
 * right of the zoom cluster, each with its own anchored panel — the same
 * popover grammar as New-‹noun›/Re-arrange (StudioToolbar) and for the same
 * reason: a header verb answers where the eye already is, without opening a
 * side pane. The Properties sections are DELETED, not mirrored (Singular
 * Implementation — the Re-arrange dual-mount was deleted the same way,
 * 2026-07-21).
 *
 * The verbs still RUN in the parent (StudioSurface owns artifactPath + api);
 * this component owns only the transient per-act state (working / copied /
 * error), lifted verbatim from the deleted sections.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { FileOutput, Share2 } from 'lucide-react';

interface StudioShareExportProps {
  /** Mint a /s/{token} membership link for this artifact and copy it
   *  (ADR-437 D4 / ADR-465). Resolves on success, rejects on failure. */
  share: () => Promise<void>;
  /** The browser's print over the resolved projection (ADR-466 D6). */
  print: () => void;
  /** Copy the interop-face reference (recall/trace via the yarnnn connector). */
  copyAiRef: () => Promise<void>;
  /** ADR-475 §13 — the IMAGES app's raster projection. Undefined for Studio,
   *  whose boundary projection is Print/PDF. */
  exportPng?: () => Promise<void>;
}

export function StudioShareExport({ share, print, copyAiRef, exportPng }: StudioShareExportProps) {
  const [open, setOpen] = useState<null | 'share' | 'export'>(null);
  // The trigger cluster (buttons + panels) — the click-away boundary, same
  // shape as StudioToolbar's menuRef (and the same iframe caveat: the canvas
  // bridges in-frame presses out as `yarnnn-canvas-press`).
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(null);
    const onDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) close();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
    };
    const onFrame = (e: MessageEvent) => {
      if ((e.data as { type?: string } | null)?.type === 'yarnnn-canvas-press') close();
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    window.addEventListener('message', onFrame);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
      window.removeEventListener('message', onFrame);
    };
  }, [open]);

  // ── Share: mint-and-copy with transient copied/error state ──────────────
  const [sharing, setSharing] = useState(false);
  const [shareState, setShareState] = useState<'idle' | 'copied' | 'error'>('idle');
  const runShare = useCallback(async () => {
    setSharing(true);
    setShareState('idle');
    try {
      await share();
      setShareState('copied');
      setTimeout(() => setShareState('idle'), 2500);
    } catch {
      setShareState('error');
      setTimeout(() => setShareState('idle'), 3000);
    } finally {
      setSharing(false);
    }
  }, [share]);

  // ── Export: AI reference copy + raster state ────────────────────────────
  const [aiRefState, setAiRefState] = useState<'idle' | 'copied'>('idle');
  const runCopyAiRef = useCallback(async () => {
    try {
      await copyAiRef();
      setAiRefState('copied');
      setTimeout(() => setAiRefState('idle'), 2500);
    } catch {
      /* clipboard denied — nothing durable failed */
    }
  }, [copyAiRef]);

  const [pngState, setPngState] = useState<'idle' | 'working' | 'error'>('idle');
  const runExportPng = useCallback(async () => {
    if (!exportPng) return;
    setPngState('working');
    try {
      await exportPng();
      setPngState('idle');
    } catch {
      setPngState('error');
      setTimeout(() => setPngState('idle'), 3000);
    }
  }, [exportPng]);

  // StudioToolbar's btn/panel grammar; panels anchor RIGHT (the cluster sits
  // at the row's right edge — a left-anchored panel would overflow the window).
  const btn =
    'inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-md border border-border px-2 py-1 text-[11px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground disabled:opacity-40';
  const panel =
    'absolute right-0 top-full z-30 mt-1 w-72 rounded-md border border-border bg-background p-2 shadow-md';
  const act =
    'inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[10px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground disabled:opacity-40';

  return (
    <div ref={menuRef} className="relative flex shrink-0 items-center gap-1 pr-2">
      <button
        type="button"
        className={btn}
        onClick={() => setOpen(open === 'share' ? null : 'share')}
        title="Share this artifact — a link that invites someone into your workspace"
      >
        <Share2 className="h-3 w-3" /> Share
      </button>
      <button
        type="button"
        className={btn}
        onClick={() => setOpen(open === 'export' ? null : 'export')}
        title="Export this artifact — print, PDF, AI reference"
      >
        <FileOutput className="h-3 w-3" /> Export
      </button>

      {/* Share (ADR-437 D4 wedge / ADR-465 — the membership act, distinct from
          the File section's Copy link, an in-app member deep-link). */}
      {open === 'share' && (
        <div className={panel}>
          <p className="px-1 pb-1 pt-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            Share
          </p>
          <div className="space-y-1.5 px-1 pb-1">
            <button type="button" className={act} onClick={runShare} disabled={sharing}>
              {sharing ? 'Creating link…' : shareState === 'copied' ? 'Link copied ✓' : 'Share…'}
            </button>
            <p className="text-[10px] leading-snug text-muted-foreground">
              {shareState === 'error'
                ? 'Could not create the share link. Try again.'
                : shareState === 'copied'
                  ? 'Anyone with the link can open this and join your workspace with full access. Manage or revoke shares from Files.'
                  : 'Creates a link. Whoever opens it joins your workspace with full access — narrow it later.'}
            </p>
          </div>
        </div>
      )}

      {/* Export (ADR-466 D6) — the boundary projections: Print/PDF over the
          resolved projection (no render engine, ADR-417) + the AI reference
          (the interop-face handle) + PNG on the IMAGES app (ADR-475 §13). */}
      {open === 'export' && (
        <div className={panel}>
          <p className="px-1 pb-1 pt-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            Export
          </p>
          <div className="space-y-1.5 px-1 pb-1">
            <div className="flex flex-wrap gap-1">
              {exportPng && (
                <button
                  type="button"
                  className={act}
                  onClick={runExportPng}
                  disabled={pngState === 'working'}
                  title="Rasterize this stage and download it as a PNG"
                >
                  {pngState === 'working'
                    ? 'Rendering…'
                    : pngState === 'error'
                      ? 'Export failed — retry'
                      : 'Download PNG'}
                </button>
              )}
              <button
                type="button"
                className={act}
                onClick={() => {
                  setOpen(null); // the print dialog takes the screen — close first
                  print();
                }}
                title="Open the print dialog over the rendered artifact — save as PDF from there"
              >
                Print / PDF…
              </button>
              <button
                type="button"
                className={act}
                onClick={runCopyAiRef}
                title="Copy a reference any connected AI can use to recall this artifact via the yarnnn connector"
              >
                {aiRefState === 'copied' ? 'Reference copied ✓' : 'Copy AI reference'}
              </button>
            </div>
            <p className="text-[10px] leading-snug text-muted-foreground">
              {exportPng
                ? 'The PNG is a flat projection — the composition stays the source (trace walks its layers). A deck prints one slide per page.'
                : 'A deck prints one slide per page. Markdown export arrives with the interchange wave (ADR-456 W4).'}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
