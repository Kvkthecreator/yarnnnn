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
  Heading1,
  Heading2,
  Heading3,
  Italic,
  Link2,
  List,
  ListOrdered,
  Minus,
  Quote,
  Strikethrough,
  Table,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export type ToolbarAction =
  | { kind: 'wrap'; marker: string }
  | { kind: 'heading'; level: number }
  | { kind: 'list'; ordered: boolean }
  | { kind: 'quote' }
  | { kind: 'link' }
  | { kind: 'table' }
  | { kind: 'rule' };

interface Item {
  icon: LucideIcon;
  label: string;
  action: ToolbarAction;
  /** Rendered as a trailing hint in the tooltip. */
  keys?: string;
}

const GROUPS: Item[][] = [
  [
    { icon: Heading1, label: 'Heading 1', action: { kind: 'heading', level: 1 } },
    { icon: Heading2, label: 'Heading 2', action: { kind: 'heading', level: 2 } },
    { icon: Heading3, label: 'Heading 3', action: { kind: 'heading', level: 3 } },
  ],
  [
    { icon: Bold, label: 'Bold', action: { kind: 'wrap', marker: '**' }, keys: '⌘B' },
    { icon: Italic, label: 'Italic', action: { kind: 'wrap', marker: '_' }, keys: '⌘I' },
    { icon: Strikethrough, label: 'Strikethrough', action: { kind: 'wrap', marker: '~~' } },
    { icon: Link2, label: 'Link', action: { kind: 'link' }, keys: '⌘K' },
  ],
  [
    { icon: List, label: 'Bulleted list', action: { kind: 'list', ordered: false } },
    { icon: ListOrdered, label: 'Numbered list', action: { kind: 'list', ordered: true } },
    { icon: Quote, label: 'Quote', action: { kind: 'quote' } },
  ],
  [
    { icon: Table, label: 'Table', action: { kind: 'table' } },
    { icon: Minus, label: 'Divider', action: { kind: 'rule' } },
  ],
];

export function MarkdownToolbar({
  onAction,
  className,
}: {
  onAction: (action: ToolbarAction) => void;
  className?: string;
}) {
  return (
    <div
      role="toolbar"
      aria-label="Markdown formatting"
      className={cn(
        'flex shrink-0 flex-wrap items-center gap-0.5 border-b border-border px-3 py-1',
        className,
      )}
    >
      {GROUPS.map((group, gi) => (
        <div key={gi} className="flex items-center gap-0.5">
          {gi > 0 && <span className="mx-1 h-4 w-px bg-border/60" aria-hidden />}
          {group.map((item) => (
            <button
              key={item.label}
              type="button"
              // `onMouseDown` + preventDefault, never `onClick`: a click would
              // blur the textarea first, and the browser drops the selection
              // on blur — so the edit would apply to a collapsed caret at
              // wherever focus landed. This keeps the member's selection.
              onMouseDown={(e) => {
                e.preventDefault();
                onAction(item.action);
              }}
              title={item.keys ? `${item.label} (${item.keys})` : item.label}
              aria-label={item.label}
              className="inline-flex h-7 w-7 items-center justify-center rounded text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
            >
              <item.icon className="h-3.5 w-3.5" />
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}
