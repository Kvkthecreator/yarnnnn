'use client';

/**
 * FindReplaceBar — ⌘F over the source (ADR-572).
 *
 * Docs has no find at all (audited 2026-08-16: no ⌘F binding, no search UI,
 * no highlight anywhere in `web/components/authoring/`). This is therefore an
 * ADDITION beyond parity, taken because the medium demands it — a 1,000-word
 * brief without find is worse to work in than a 200-word artifact without it,
 * and Text's documents are the long ones.
 *
 * It searches the SOURCE, which is the honest scope: the source is what the
 * member edits and what the file contains. Matches are addressed as character
 * offsets and revealed by selecting them in the textarea — no highlight layer
 * over the text, because a highlight layer would need a position map, which is
 * the annotation shape ADR-456 D1 rules out. Selection IS the browser's own
 * position map, and it costs nothing.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, ChevronUp, Replace, X } from 'lucide-react';
import { findAll } from '@/components/text/markdownEdits';

export function FindReplaceBar({
  text,
  onReveal,
  onReplaceOne,
  onReplaceAll,
  onClose,
}: {
  text: string;
  /** Select [start, end) in the editor and scroll it into view. */
  onReveal: (span: [number, number]) => void;
  onReplaceOne: (span: [number, number], with_: string) => void;
  onReplaceAll: (needle: string, with_: string) => void;
  onClose: () => void;
}) {
  const [needle, setNeedle] = useState('');
  const [replacement, setReplacement] = useState('');
  const [showReplace, setShowReplace] = useState(false);
  const [index, setIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const spans = useMemo(() => findAll(text, needle), [text, needle]);
  const count = spans.length;

  useEffect(() => { inputRef.current?.focus(); inputRef.current?.select(); }, []);

  // A changed needle (or a text edit that dropped matches) resets to the first
  // hit rather than leaving the counter pointing past the end.
  useEffect(() => { setIndex(0); }, [needle]);
  useEffect(() => {
    if (index >= count) setIndex(0);
  }, [count, index]);

  const go = (delta: number) => {
    if (!count) return;
    const next = (index + delta + count) % count;
    setIndex(next);
    onReveal(spans[next]);
  };

  return (
    <div className="flex shrink-0 flex-wrap items-center gap-1.5 border-b border-border bg-muted/20 px-3 py-1.5 text-xs">
      <input
        ref={inputRef}
        value={needle}
        onChange={(e) => setNeedle(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') { e.preventDefault(); go(e.shiftKey ? -1 : 1); }
          if (e.key === 'Escape') { e.preventDefault(); onClose(); }
        }}
        placeholder="Find"
        aria-label="Find in document"
        className="w-40 rounded border border-border bg-background px-2 py-1 outline-none focus:border-foreground/40"
      />
      <span className="min-w-[6ch] tabular-nums text-muted-foreground">
        {needle ? (count ? `${index + 1}/${count}` : 'None') : ''}
      </span>
      <button
        type="button" onClick={() => go(-1)} disabled={!count}
        title="Previous match (⇧⏎)" aria-label="Previous match"
        className="rounded p-1 text-muted-foreground hover:bg-muted/60 hover:text-foreground disabled:opacity-30"
      >
        <ChevronUp className="h-3.5 w-3.5" />
      </button>
      <button
        type="button" onClick={() => go(1)} disabled={!count}
        title="Next match (⏎)" aria-label="Next match"
        className="rounded p-1 text-muted-foreground hover:bg-muted/60 hover:text-foreground disabled:opacity-30"
      >
        <ChevronDown className="h-3.5 w-3.5" />
      </button>
      <button
        type="button" onClick={() => setShowReplace((v) => !v)}
        title="Replace" aria-label="Toggle replace" aria-expanded={showReplace}
        className="rounded p-1 text-muted-foreground hover:bg-muted/60 hover:text-foreground"
      >
        <Replace className="h-3.5 w-3.5" />
      </button>

      {showReplace && (
        <>
          <input
            value={replacement}
            onChange={(e) => setReplacement(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Escape') { e.preventDefault(); onClose(); } }}
            placeholder="Replace with"
            aria-label="Replace with"
            className="w-40 rounded border border-border bg-background px-2 py-1 outline-none focus:border-foreground/40"
          />
          <button
            type="button"
            onClick={() => { if (count) onReplaceOne(spans[index], replacement); }}
            disabled={!count}
            className="rounded border border-border px-2 py-1 hover:bg-muted/60 disabled:opacity-30"
          >
            Replace
          </button>
          <button
            type="button"
            onClick={() => { if (count) onReplaceAll(needle, replacement); }}
            disabled={!count}
            className="rounded border border-border px-2 py-1 hover:bg-muted/60 disabled:opacity-30"
          >
            All
          </button>
        </>
      )}

      <div className="flex-1" />
      <button
        type="button" onClick={onClose} title="Close (Esc)" aria-label="Close find"
        className="rounded p-1 text-muted-foreground hover:bg-muted/60 hover:text-foreground"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
