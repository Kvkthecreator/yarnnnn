'use client';

/**
 * SlashMenu — the `/` insert palette (ADR-572 D14).
 *
 * Operator: *"can you consider if we can use the slash command shortcut key on
 * the page like notion?"*
 *
 * ## Why this is not a port of Docs' palette
 *
 * Docs has the same gesture and **none of its machinery transfers**. There the
 * canvas is a sandboxed iframe, so the runtime must bridge every step across
 * the frame boundary: `onSlashOpen` with a frame-relative rect, `onSlashFilter`
 * mirroring the typed run back out, `onSlashMove`/`onSlashEnter` because the
 * document holds the caret and the parent cannot hear its keys, and a
 * `slashTake` nonce commanding the runtime to delete the run it alone can
 * locate. Roughly six message types to do one thing.
 *
 * In CodeMirror the caret, the text and the keymap are all in this document.
 * The whole gesture is: read the run behind the caret, show a list, and on pick
 * replace `[runStart, caret)` with the edit. No bridge, no nonce.
 *
 * ## What it inserts
 *
 * The SAME `markdownEdits` functions the toolbar calls — the palette is a
 * second DOOR to one mechanism, never a second mechanism (the ADR-505 D4 rule
 * Docs states for its own toolbar/slash pair). So a slash insert and a toolbar
 * press produce byte-identical markdown, and neither can drift from the other.
 */

import { useEffect, useMemo, useRef } from 'react';
import type { LucideIcon } from 'lucide-react';
import {
  Code,
  Heading1,
  Heading2,
  Heading3,
  Image as ImageIcon,
  List,
  ListChecks,
  ListOrdered,
  Minus,
  Quote,
  Sheet,
  Table,
  Workflow,
} from 'lucide-react';
import type { ToolbarAction } from '@/components/text/MarkdownToolbar';
import { cn } from '@/lib/utils';

export interface SlashItem {
  id: string;
  label: string;
  hint: string;
  icon: LucideIcon;
  action: ToolbarAction;
  /** Extra words the filter matches, so "bullet" finds the bulleted list. */
  keywords: string[];
  /** ADR-579 D4 — the provenance group: `new` mints from thin air; `add`
   *  brings in what the workspace already holds (the two picker-backed kinds,
   *  ADR-572 D17/D18). Groups are contiguous in declaration order so the flat
   *  keyboard index and the rendered rows can never disagree. */
  group: 'new' | 'add';
}

/**
 * The block-shaped kinds only. Bold/italic/link are deliberately absent: they
 * act on a SELECTION, and the slash run is by definition a collapsed caret —
 * offering them would be offering a control that cannot do anything.
 */
export const SLASH_ITEMS: SlashItem[] = [
  // ── NEW — minted from thin air (ADR-579 D4). The caret's common case
  //    leads. ──
  { id: 'h1', label: 'Heading 1', hint: 'Large section heading', icon: Heading1, action: { kind: 'heading', level: 1 }, keywords: ['title', 'h1'], group: 'new' },
  { id: 'h2', label: 'Heading 2', hint: 'Medium section heading', icon: Heading2, action: { kind: 'heading', level: 2 }, keywords: ['h2', 'subtitle'], group: 'new' },
  { id: 'h3', label: 'Heading 3', hint: 'Small section heading', icon: Heading3, action: { kind: 'heading', level: 3 }, keywords: ['h3'], group: 'new' },
  { id: 'bullet', label: 'Bulleted list', hint: 'A simple list', icon: List, action: { kind: 'list', ordered: false }, keywords: ['bullet', 'ul', 'unordered'], group: 'new' },
  { id: 'number', label: 'Numbered list', hint: 'A list in order', icon: ListOrdered, action: { kind: 'list', ordered: true }, keywords: ['ol', 'ordered', '1'], group: 'new' },
  { id: 'task', label: 'Task list', hint: 'Tick items off', icon: ListChecks, action: { kind: 'checklist' }, keywords: ['todo', 'checkbox', 'check'], group: 'new' },
  { id: 'quote', label: 'Quote', hint: 'Set text apart', icon: Quote, action: { kind: 'quote' }, keywords: ['blockquote', 'cite'], group: 'new' },
  { id: 'table', label: 'Table', hint: 'Rows and columns', icon: Table, action: { kind: 'table' }, keywords: ['grid'], group: 'new' },
  { id: 'divider', label: 'Divider', hint: 'A section break', icon: Minus, action: { kind: 'rule' }, keywords: ['hr', 'rule', 'line', 'separator'], group: 'new' },
  // ADR-572 D17 — the thin-air media kinds. Heavier acts than a list or a
  // heading; `/dia` and `/code` reach them in a few keystrokes.
  { id: 'mermaid', label: 'Diagram', hint: 'A mermaid diagram', icon: Workflow, action: { kind: 'mermaid' }, keywords: ['mermaid', 'chart', 'flow', 'graph'], group: 'new' },
  { id: 'code', label: 'Code block', hint: 'Fenced, with a language', icon: Code, action: { kind: 'code' }, keywords: ['fence', 'snippet', 'pre'], group: 'new' },
  // ── ADD — from the workspace (ADR-579 D4): the two picker-backed kinds.
  //    `/csv` and `/img` still reach them in a few keystrokes; the header
  //    answers the discovery need the old sits-beside-the-table placement
  //    served (ADR-572 D18). ──
  { id: 'image', label: 'Image', hint: 'From your workspace', icon: ImageIcon, action: { kind: 'image' }, keywords: ['img', 'picture', 'photo', 'figure'], group: 'add' },
  { id: 'csvtable', label: 'Table from CSV', hint: 'Rows from a workspace file', icon: Sheet, action: { kind: 'csvtable' }, keywords: ['csv', 'data', 'spreadsheet', 'import'], group: 'add' },
];

/** Rows matching `filter`, in declaration order. Empty filter → everything. */
export function filterSlashItems(filter: string): SlashItem[] {
  const q = filter.trim().toLowerCase();
  if (!q) return SLASH_ITEMS;
  return SLASH_ITEMS.filter(
    (i) =>
      i.label.toLowerCase().includes(q) ||
      i.keywords.some((k) => k.startsWith(q)),
  );
}

export function SlashMenu({
  items,
  active,
  coords,
  onPick,
  onHover,
}: {
  items: SlashItem[];
  active: number;
  /** Viewport coordinates of the caret, from `EditorView.coordsAtPos`. */
  coords: { left: number; top: number; bottom: number };
  onPick: (item: SlashItem) => void;
  onHover: (index: number) => void;
}) {
  const listRef = useRef<HTMLDivElement | null>(null);

  // Keep the highlighted row in view when ↑/↓ walks past the fold.
  useEffect(() => {
    const el = listRef.current?.querySelector<HTMLElement>(`[data-idx="${active}"]`);
    el?.scrollIntoView({ block: 'nearest' });
  }, [active]);

  // Flip above the caret when there is not room below — a palette that opens
  // off-screen is a palette the member cannot use.
  const style = useMemo(() => {
    const H = 300;
    const below = typeof window !== 'undefined' ? window.innerHeight - coords.bottom : H;
    const flip = below < H && coords.top > below;
    return flip
      ? { left: coords.left, bottom: `calc(100vh - ${coords.top}px + 6px)` }
      : { left: coords.left, top: coords.bottom + 6 };
  }, [coords]);

  if (items.length === 0) return null;

  return (
    <div
      role="listbox"
      aria-label="Insert"
      ref={listRef}
      style={style}
      className="fixed z-50 max-h-[300px] w-64 overflow-y-auto rounded-md border border-border bg-popover p-1 shadow-md"
    >
      {items.map((item, i) => (
        <div key={item.id}>
          {/* ADR-579 D4 — the provenance headers. Declaration order keeps the
              groups contiguous, so a header renders exactly where the group
              starts and the flat keyboard index is untouched. */}
          {(i === 0 || items[i - 1].group !== item.group) && (
            <p className="px-2 pb-0.5 pt-1.5 text-[9.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/70">
              {item.group === 'add' ? 'Add — from the workspace' : 'New'}
            </p>
          )}
        <button
          type="button"
          role="option"
          aria-selected={i === active}
          data-idx={i}
          // `onMouseDown` + preventDefault: a click would blur the editor and
          // the caret — and therefore the run being replaced — would be gone
          // by the time the handler ran.
          onMouseDown={(e) => {
            e.preventDefault();
            onPick(item);
          }}
          onMouseEnter={() => onHover(i)}
          className={cn(
            'flex w-full items-center gap-2.5 rounded px-2 py-1.5 text-left transition-colors',
            i === active ? 'bg-muted' : 'hover:bg-muted/50',
          )}
        >
          <item.icon className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
          <span className="min-w-0">
            <span className="block truncate text-xs font-medium text-foreground">{item.label}</span>
            <span className="block truncate text-[10px] text-muted-foreground">{item.hint}</span>
          </span>
        </button>
        </div>
      ))}
    </div>
  );
}
