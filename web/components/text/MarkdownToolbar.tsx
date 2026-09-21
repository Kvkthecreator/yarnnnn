'use client';

/**
 * MarkdownToolbar — Text's Insert row (ADR-572), the legal half of Docs'
 * toolbar.
 *
 * Docs' Insert opens a slash palette that mints BLOCKS. This mints
 * CHARACTERS: every button routes through `markdownEdits`, which returns a new
 * source string and a caret range. Nothing here knows what a block is, and the
 * file stays the plain `.md` a connector round-trips.
 *
 * Only mounted in Write mode — a formatting control over a reading view would
 * be a button that does nothing to what you can see.
 */

import type { LucideIcon } from 'lucide-react';
import {
  Bold,
  Code,
  Heading1,
  Heading2,
  Heading3,
  Image as ImageIcon,
  Italic,
  Link2,
  List,
  ListChecks,
  ListOrdered,
  Minus,
  Quote,
  Sheet,
  Strikethrough,
  Table,
  Workflow,
} from 'lucide-react';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';

export type ToolbarAction =
  | { kind: 'wrap'; marker: string }
  | { kind: 'heading'; level: number }
  | { kind: 'list'; ordered: boolean }
  | { kind: 'checklist' }
  | { kind: 'quote' }
  | { kind: 'link' }
  | { kind: 'table' }
  | { kind: 'rule' }
  // ADR-572 D17 — the three kinds markdown carries NATIVELY that Insert did
  // not offer. Each keeps its content IN the file, which is what separates
  // them from Docs' citation blocks (`figure`/`gallery`/`table`/`chart`
  // persist as empty `data-ref` elements resolved client-side only).
  | { kind: 'code' }
  | { kind: 'mermaid' }
  /** Opens the workspace image picker; the path arrives on the pick. */
  | { kind: 'image' }
  /**
   * ADR-572 D18 — a table SNAPSHOT from a workspace CSV. Opens the same
   * picker listing CSVs; the rows are read and written as real markdown.
   * Distinct from `table` (an empty skeleton to type into).
   */
  | { kind: 'csvtable' };

interface Item {
  icon: LucideIcon;
  /** ADR-660 — a CATALOG KEY, never a word. This table is evaluated at import,
   *  before any member's language is known, so the label is resolved at render
   *  under `text.toolbar`. */
  labelKey: string;
  action: ToolbarAction;
  /** Rendered as a trailing hint in the tooltip. */
  keys?: string;
}

const GROUPS: Item[][] = [
  [
    { icon: Heading1, labelKey: 'h1', action: { kind: 'heading', level: 1 } },
    { icon: Heading2, labelKey: 'h2', action: { kind: 'heading', level: 2 } },
    { icon: Heading3, labelKey: 'h3', action: { kind: 'heading', level: 3 } },
  ],
  [
    { icon: Bold, labelKey: 'bold', action: { kind: 'wrap', marker: '**' }, keys: '⌘B' },
    { icon: Italic, labelKey: 'italic', action: { kind: 'wrap', marker: '_' }, keys: '⌘I' },
    { icon: Strikethrough, labelKey: 'strikethrough', action: { kind: 'wrap', marker: '~~' } },
    { icon: Link2, labelKey: 'link', action: { kind: 'link' }, keys: '⌘K' },
  ],
  [
    { icon: List, labelKey: 'bullet', action: { kind: 'list', ordered: false } },
    { icon: ListOrdered, labelKey: 'number', action: { kind: 'list', ordered: true } },
    // Docs' `checklist` kind, which markdown expresses natively (GFM task
    // list) and the shared renderer already paints — the one Insert row that
    // survives the medium translation with no annotation.
    { icon: ListChecks, labelKey: 'task', action: { kind: 'checklist' } },
    { icon: Quote, labelKey: 'quote', action: { kind: 'quote' } },
  ],
  // ADR-572 D17 — every kind here keeps its content in the `.md`: a diagram
  // is its own source, code is fenced.
  [
    { icon: Table, labelKey: 'table', action: { kind: 'table' } },
    { icon: Minus, labelKey: 'divider', action: { kind: 'rule' } },
    { icon: Workflow, labelKey: 'mermaid', action: { kind: 'mermaid' } },
    { icon: Code, labelKey: 'code', action: { kind: 'code' } },
  ],
  // ADR-579 D4 — the ADD pair, from the workspace: the two picker-backed
  // kinds (ADR-572 D17/D18) sit together as the toolbar's mirror of the slash
  // palette's Add group. An image is a path; the CSV's rows land as real
  // markdown (which is what Docs' citation block cannot do).
  [
    { icon: ImageIcon, labelKey: 'image', action: { kind: 'image' } },
    { icon: Sheet, labelKey: 'csvtable', action: { kind: 'csvtable' } },
  ],
];

export function MarkdownToolbar({
  onAction,
  className,
}: {
  onAction: (action: ToolbarAction) => void;
  className?: string;
}) {
  const t = useTranslations('text.toolbar');
  return (
    /* The verbs live in the HEADER's centre zone (TextEditor), which is already
       the canvas column — so this component owns no border, no ground and no
       measure of its own. It owned all three when it was a band of its own above
       the canvas; keeping any of them here would draw a second box inside the
       header row.

       `overflow-x-auto` rather than `flex-wrap`: a wrapping toolbar would grow
       the header row and push the canvas down as the pane narrows, so the
       document visibly jumps. Docs scrolls for the same reason. The scrollbar is
       hidden — chrome on chrome, on a row one line tall. */
    <div
      role="toolbar"
      aria-label={t('label')}
      className={cn(
        'flex w-full items-center gap-0.5 overflow-x-auto [&::-webkit-scrollbar]:hidden [scrollbar-width:none]',
        className,
      )}
    >
      {GROUPS.map((group, gi) => (
        <div key={gi} className="flex shrink-0 items-center gap-0.5">
          {gi > 0 && <span className="mx-1.5 h-5 w-px bg-border/60" aria-hidden />}
          {group.map((item) => {
            const label = t(item.labelKey);
            return (
            <button
              key={item.labelKey}
              type="button"
              // `onMouseDown` + preventDefault, never `onClick`: a click would
              // blur the textarea first, and the browser drops the selection
              // on blur — so the edit would apply to a collapsed caret at
              // wherever focus landed. This keeps the member's selection.
              onMouseDown={(e) => {
                e.preventDefault();
                onAction(item.action);
              }}
              // ONE message, never a join: a label glued to its shortcut in
              // code is an English word order (ADR-660).
              title={item.keys ? t('withKeys', { label, keys: item.keys }) : label}
              aria-label={label}
              // Sized to the Docs reference: a 32px target with a 16px glyph
              // reads as a real button rather than a hairline mark, and meets
              // the touch floor closely enough at desktop density.
              className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
            >
              <item.icon className="h-4 w-4" />
            </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}
