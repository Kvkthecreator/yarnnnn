'use client';

/**
 * StudioSlashPalette — the '/' block palette (ADR-456 W2, the Notion gesture).
 *
 * Opens when the edit runtime reports a '/' typed in an empty context (the
 * runtime has already committed + exited the edit). Anchored at the block's
 * rect over the canvas; a filter input owns the keyboard (type to filter,
 * ↑/↓ to move, Enter to pick, Esc to dismiss).
 *
 * v1 lists the PLAIN-INSERT kinds + chart (the generative ask). The cited
 * kinds (figure/table/gallery) need their pickers and stay in Insert ▾ — a
 * palette row that half-opens a different panel would be worse than absent.
 *
 * The palette EXECUTES nothing itself — the surface routes the pick: an empty
 * block CONVERTS in place (turn-into), a non-empty one gets the block
 * inserted after it. Same one door, one revision.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import type { StudioVocabulary } from './StudioToolbar';

/** Kinds the slash palette offers — everything except the picker-backed ones. */
const SLASH_EXCLUDED = new Set(['figure', 'table', 'gallery']);

interface StudioSlashPaletteProps {
  vocabulary: StudioVocabulary | null;
  /** Anchor within the canvas wrapper (already clamped by the surface). */
  left: number;
  top: number;
  onPick: (kind: string, label: string, fragment: string) => void;
  onClose: () => void;
}

export function StudioSlashPalette({
  vocabulary,
  left,
  top,
  onPick,
  onClose,
}: StudioSlashPaletteProps) {
  const [filter, setFilter] = useState('');
  const [highlight, setHighlight] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const items = useMemo(() => {
    const all = (vocabulary?.blocks ?? []).filter((b) => !SLASH_EXCLUDED.has(b.kind));
    const q = filter.trim().toLowerCase();
    if (!q) return all;
    return all.filter(
      (b) => b.label.toLowerCase().includes(q) || b.kind.toLowerCase().includes(q),
    );
  }, [vocabulary, filter]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);
  useEffect(() => {
    setHighlight(0);
  }, [filter]);

  // Click-away dismisses (the typed '/' never landed — nothing to undo).
  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [onClose]);

  const pick = (i: number) => {
    const b = items[i];
    if (b) onPick(b.kind, b.label, b.fragment);
  };

  return (
    <div
      ref={rootRef}
      style={{ left, top }}
      className="absolute z-30 w-64 rounded-md border border-border bg-background p-1 shadow-lg"
    >
      <input
        ref={inputRef}
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Escape') {
            e.preventDefault();
            onClose();
          } else if (e.key === 'Enter') {
            e.preventDefault();
            pick(highlight);
          } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            setHighlight((h) => Math.min(h + 1, items.length - 1));
          } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setHighlight((h) => Math.max(h - 1, 0));
          }
        }}
        placeholder="Filter blocks…"
        className="mb-1 w-full rounded border border-border bg-transparent px-2 py-1 text-xs outline-none"
      />
      <div className="max-h-56 overflow-y-auto">
        {items.length === 0 && (
          <p className="p-2 text-[11px] text-muted-foreground">No matching block.</p>
        )}
        {items.map((b, i) => (
          <button
            key={b.kind}
            type="button"
            onClick={() => pick(i)}
            onMouseEnter={() => setHighlight(i)}
            className={`flex w-full flex-col rounded px-2 py-1.5 text-left ${
              i === highlight ? 'bg-muted/50' : 'hover:bg-muted/30'
            }`}
          >
            <span className="text-xs">{b.label}</span>
            <span className="truncate text-[10px] leading-snug text-muted-foreground">
              {b.description}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
