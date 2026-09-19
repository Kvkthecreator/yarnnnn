'use client';

/**
 * ConnectorAvatar — a connector's face, identical wherever it appears.
 *
 * The identity itself is resolved in `lib/connectors/marks.tsx`; this is the
 * one place that renders it. Both halves matter: a shared resolver with two
 * render sites still drifts (one pads, one doesn't; one rounds `lg`, one
 * `md`), and the whole point is that the row a member clicks in the finder is
 * visibly the row they land on in Connected.
 *
 * Three sizes, because the surfaces genuinely differ and inventing a fourth is
 * how a system stops looking like one:
 *   sm (28px) — a dense list row: the finder's browse step.
 *   md (36px) — a card: the Connected list, the Available list.
 *   lg (44px) — a subsurface header: the attached-connector detail page.
 */

import { cn } from '@/lib/utils';
import { connectorIdentity } from '@/lib/connectors/marks';
import type { ReactNode } from 'react';

const SIZE: Record<'sm' | 'md' | 'lg', { box: string; letter: string }> = {
  sm: { box: 'h-7 w-7 rounded-md', letter: 'text-[11px]' },
  md: { box: 'h-9 w-9 rounded-lg', letter: 'text-sm' },
  lg: { box: 'h-11 w-11 rounded-xl', letter: 'text-base' },
};

export function ConnectorAvatar({
  url,
  title,
  connectorKey,
  size = 'md',
  /** An already-resolved mark — the four platform-OAuth connectors carry their
   *  own brand in CONNECTOR_REGISTRY and pass it through here, so they render
   *  in the same box as everything else without being re-derived. Their glyphs
   *  carry their OWN colour classes (`text-white dark:text-black` on the SVG),
   *  so an override supplies no `glyphClass` — imposing one here would fight
   *  the mark and flip Notion's glyph invisible in dark mode. */
  override,
  className,
}: {
  url?: string | null;
  title?: string | null;
  connectorKey?: string | null;
  size?: 'sm' | 'md' | 'lg';
  override?: { chipClass: string; icon: ReactNode };
  className?: string;
}) {
  const id = override
    ? { chipClass: override.chipClass, glyphClass: '', icon: override.icon, letter: '', branded: true }
    : connectorIdentity({ url, title, key: connectorKey });
  const s = SIZE[size];
  return (
    <div
      aria-hidden="true"
      className={cn(
        'flex shrink-0 items-center justify-center overflow-hidden',
        s.box,
        id.chipClass,
        id.glyphClass,
        className,
      )}
    >
      {id.icon ?? <span className={cn('font-semibold leading-none', s.letter)}>{id.letter}</span>}
    </div>
  );
}
