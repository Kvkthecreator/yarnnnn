'use client';

/**
 * TextExport — Text's boundary acts (ADR-571), the StudioShareExport analog.
 *
 * Share opens the ONE shared dialog every file surface mounts (ADR-529 D1 —
 * this component never mints a link itself). Export is a small anchored
 * panel, the StudioToolbar popover grammar.
 *
 * What Export offers reached Docs parity in ADR-572 D4. The original cut
 * withheld Print/PDF on the honest ground that "a prose document has no
 * rendered form, so print-to-PDF would be printing a textarea" — true until
 * the reading face existed. It does now (`ProseReader`), so the same three
 * acts Docs offers are all available: print the RENDERED document, take the
 * file (the exact bytes), and hand another AI its address (the interop
 * reference — the round-trip this app exists to serve).
 *
 * Markdown export needs no row: the file already IS markdown. Docs' own panel
 * says "Markdown export arrives with the interchange wave" — Text is the app
 * where that sentence is already answered by Download.
 */

import { useEffect, useRef, useState } from 'react';
import { COPY_FEEDBACK_MS } from '@/contexts/FeedbackContext';
import { Check, Download, Link2, Printer, Share2, Upload } from 'lucide-react';
import { printProse } from '@/components/text/printProse';
import { cn } from '@/lib/utils';
import { formatAiReference } from '@/lib/interop/fileHandle';

export function TextExport({
  share,
  text,
  name,
  path,
  compact,
}: {
  share: () => void;
  text: string;
  name: string;
  path: string;
  compact?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const wrapRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const download = () => {
    // A member-initiated save of bytes they already have — no server round
    // trip, and the leaf keeps its real name.
    const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = path.split('/').pop() || 'document.md';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    setOpen(false);
  };

  const copyReference = async () => {
    await navigator.clipboard.writeText(formatAiReference(path, name));
    setCopied(true);
    setTimeout(() => setCopied(false), COPY_FEEDBACK_MS);
  };

  return (
    <div ref={wrapRef} className="relative flex shrink-0 items-center gap-1">
      <button
        type="button"
        onClick={share}
        title="Share this document"
        className="inline-flex items-center gap-1.5 rounded-md border border-border px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground"
      >
        <Share2 className="h-3.5 w-3.5" />
        {!compact && 'Share…'}
      </button>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        title="Export"
        aria-expanded={open}
        className="inline-flex items-center gap-1.5 rounded-md border border-border px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground"
      >
        <Upload className="h-3.5 w-3.5" />
        {!compact && 'Export'}
      </button>

      {open && (
        <div className="absolute right-0 top-full z-30 mt-1 w-64 rounded-lg border border-border bg-background p-1 shadow-lg">
          <button
            type="button"
            onClick={() => { printProse(text, name); setOpen(false); }}
            className="flex w-full items-start gap-2 rounded-md p-2 text-left hover:bg-muted/50"
          >
            <Printer className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            <span>
              <span className="block text-xs font-medium">Print / PDF…</span>
              <span className="block text-[11px] text-muted-foreground">
                The document as you read it, on A4.
              </span>
            </span>
          </button>
          <button
            type="button"
            onClick={download}
            className="flex w-full items-start gap-2 rounded-md p-2 text-left hover:bg-muted/50"
          >
            <Download className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            <span>
              <span className="block text-xs font-medium">Download .md</span>
              <span className="block text-[11px] text-muted-foreground">
                The exact bytes, as they are on the head.
              </span>
            </span>
          </button>
          <button
            type="button"
            onClick={() => void copyReference()}
            className="flex w-full items-start gap-2 rounded-md p-2 text-left hover:bg-muted/50"
          >
            {copied ? (
              <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />
            ) : (
              <Link2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            )}
            <span>
              <span className="block text-xs font-medium">
                {copied ? 'Copied' : 'Copy reference for AI'}
              </span>
              <span className="block text-[11px] text-muted-foreground">
                Paste into another AI — with the connector it reads the live version.
              </span>
            </span>
          </button>
        </div>
      )}
    </div>
  );
}
