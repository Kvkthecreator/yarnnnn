'use client';

/**
 * StudioShareExport — the boundary acts (Share · Export) as HEADER verbs
 * (2026-07-24 relocation).
 *
 * Share and Export are document-global acts that lived as Properties-pane
 * sections (ADR-458 D3 / ADR-466 D6). But the Properties pane is the SHAPING
 * home — tokens, measures, scopes — and the boundary acts were the only rows
 * there that never touch the artifact's form. They now sit in the toolbar row,
 * right of the zoom cluster — a header verb answers where the eye already is,
 * without opening a side pane. The Properties sections are DELETED, not
 * mirrored (Singular Implementation).
 *
 * ADR-515 §2.0's two-mount carve is PRESERVED: Share belongs beside Export
 * because both are boundary acts (the file crossing out of the workspace, one
 * way or another). What ADR-529 D1 changed is the asymmetry inside that
 * placement — **Export owns a panel here; Share owns nothing here.** Share is
 * a trigger for the one `ShareDialog` that Files and every file surface mount,
 * so the act is identical wherever it is invoked (the operator's rule:
 * "the concept should feel the same regardless of ANY surface").
 *
 * DELETED by ADR-529 D4: this component's own share popover — two shape
 * buttons + `runShare` + the `sharing`/`shareState`/`sharedMode` state. It
 * dismissed on outclick (a governance act should not), never showed the minted
 * URL, and pointed at "Files" for management — a surface that never managed
 * shares.
 *
 * The verbs still RUN in the parent (StudioSurface owns artifactPath + api);
 * this component owns only Export's transient state.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { FileOutput, Share2 } from 'lucide-react';

interface StudioShareExportProps {
  /** OPEN the share dialog for this artifact (ADR-529 D1). Studio no longer
   *  mints here: the two-button popover this component used to own is deleted,
   *  and the act lives in the one `ShareDialog` every file surface mounts.
   *  Fire-and-forget — the dialog owns the outcome, the error and the link. */
  share: () => void;
  /** The browser's print over the resolved projection (ADR-466 D6). */
  print: () => void;
  /** Copy the interop-face reference (recall/trace via the yarnnn connector). */
  copyAiRef: () => Promise<void>;
  /** ADR-475 §13 — the IMAGES app's raster projection. Undefined for Studio,
   *  whose boundary projection is Print/PDF. */
  exportPng?: () => Promise<void>;
  /** COMPACT (2026-08-12) — the boundary acts drop their text labels and keep
   *  their glyphs at the ladder's narrow rungs. Same grammar and same reason as
   *  StudioToolbar's `compact`: the header row cannot scroll (its panels are
   *  `absolute top-full`), so the cluster must NEED less width rather than be
   *  given somewhere to overflow. These two verbs are document-grain and
   *  infrequent, so they are the first labels the row can afford to lose. */
  compact?: boolean;
  /** Touch parity — 44px targets under a coarse pointer. */
  coarsePointer?: boolean;
}

export function StudioShareExport({
  share,
  print,
  copyAiRef,
  exportPng,
  compact = false,
  coarsePointer = false,
}: StudioShareExportProps) {
  // Only Export has a panel now — Share is a dialog trigger (ADR-529 D1).
  const [open, setOpen] = useState<null | 'export'>(null);
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

  // ── Export: AI reference copy + raster state ────────────────────────────
  //
  // The share panel that used to live here — two buttons, `runShare`, and the
  // `sharing`/`shareState`/`sharedMode` transient state — is DELETED (ADR-529
  // D4). It offered the right two shapes but dismissed on outclick, showed the
  // operator no URL, and told them to "manage or revoke shares from Files",
  // which was never the surface that managed shares. Share is now a trigger.
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
    'inline-flex shrink-0 items-center justify-center gap-1 whitespace-nowrap rounded-md border border-border text-[11px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground disabled:opacity-40 ' +
    (coarsePointer ? 'min-h-[44px] ' : '') +
    (compact ? (coarsePointer ? 'w-11 px-0' : 'h-7 w-8 px-0') : 'px-2 py-1');
  const panel =
    'absolute right-0 top-full z-30 mt-1 w-72 rounded-md border border-border bg-background p-2 shadow-md';
  const act =
    'inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[10px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground disabled:opacity-40';

  return (
    <div ref={menuRef} className="relative flex shrink-0 items-center gap-1 pr-2">
      {/* ADR-529 D1: opens the dialog. It does NOT mint, and it does not copy
          anything on click — the word "Share" is reserved for the act that
          changes who can reach the file (ADR-515 D1), and that act always asks. */}
      <button
        type="button"
        className={btn}
        onClick={() => { setOpen(null); share(); }}
        title="Share this artifact — choose who can reach it, and get a link"
        aria-label={compact ? 'Share…' : undefined}
      >
        <Share2 className="h-3 w-3" />
        {!compact && ' Share…'}
      </button>
      <button
        type="button"
        className={btn}
        onClick={() => setOpen(open === 'export' ? null : 'export')}
        title="Export this artifact — print, PDF, AI reference"
        aria-label={compact ? 'Export' : undefined}
      >
        <FileOutput className="h-3 w-3" />
        {!compact && ' Export'}
      </button>

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
