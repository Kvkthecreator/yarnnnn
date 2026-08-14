'use client';

/**
 * MentionMenu — the '@' cast palette (ADR-492 D3 / ADR-495 D3 addressing).
 *
 * Addressing shipped server-side and had NO affordance: the member had to know
 * the gesture existed, and had to spell the name exactly, with nothing on
 * screen saying either. An unrecognized handle is deliberately never
 * fuzzy-matched (`services/addressing.py` — a typo silently addressing the
 * wrong colleague is worse than not routing), which makes a menu that emits
 * only VALID handles the natural complement rather than a nicety.
 *
 * Modelled on `StudioSlashPalette` (ADR-456 W2), and for the same reasons —
 * this is the same gesture in a different text field:
 *
 *  - The '@' lands as ORDINARY TEXT and the caret never leaves the composer.
 *    What the member types after it IS the filter. There is no input here to
 *    focus; stealing focus would end the typing the gesture depends on.
 *  - Because every typed '@' opens it, DISMISSAL is load-bearing: Esc, a
 *    click away, a caret that leaves the run, and A FILTER THAT MATCHES
 *    NOTHING all close it. That last one is why typing an email address never
 *    strands a menu over the composer.
 *  - The HOST owns the keyboard (Enter/↑/↓) because the textarea has focus;
 *    this reports its filtered rows up via `onItemsChange` so the host can
 *    pick the highlighted one without duplicating the filter logic.
 *
 * WHY PEOPLE APPEAR BUT INERT. The cast is species-blind (ADR-495 D1) and the
 * member should see the whole room, so hiding humans would misrepresent who is
 * here. But a human mention routes NOWHERE today: ADR-495 D6 defers it to
 * notifications, on the grounds that "a mention routing nowhere is theatre."
 * Offering a person as a live target would promise a delivery the system does
 * not make. So they render — greyed, unselectable, with the reason stated once
 * at the foot of the section. The honest middle: visible, and visibly not yet.
 */

import { useEffect, useMemo, useRef } from 'react';
import { AgentFace } from '@/components/agents/AgentFace';
import { cn } from '@/lib/utils';

export interface MentionCandidate {
  /** The token written into the composer, without the '@'. */
  handle: string;
  name: string;
  avatarUrl?: string;
  blurb?: string;
  /** Agents route; people are shown inert (ADR-495 D6). */
  kind: 'agent' | 'human';
}

interface MentionMenuProps {
  /** Everyone in this conversation's cast, viewer excluded. */
  candidates: MentionCandidate[];
  /** The run typed after the '@', mirrored from the composer's caret. */
  filter: string;
  /** Index of the highlighted row — owned by the host, which has the keyboard. */
  highlight: number;
  onHighlight: (i: number) => void;
  onPick: (c: MentionCandidate) => void;
  onClose: () => void;
  /** Reports the SELECTABLE rows up, so the host's Enter picks the same row
   *  this list highlights. People are excluded: they are displayed, not
   *  targets, and a host that could "select" one would write a handle that
   *  routes nowhere. */
  onItemsChange: (items: MentionCandidate[]) => void;
}

export function MentionMenu({
  candidates,
  filter,
  highlight,
  onHighlight,
  onPick,
  onClose,
  onItemsChange,
}: MentionMenuProps) {
  const rootRef = useRef<HTMLDivElement>(null);

  const { agents, people, selectable } = useMemo(() => {
    const q = filter.trim().toLowerCase();
    const match = (c: MentionCandidate) =>
      !q || c.handle.toLowerCase().includes(q) || c.name.toLowerCase().includes(q);
    const hit = candidates.filter(match);
    const agentRows = hit.filter((c) => c.kind === 'agent');
    return {
      agents: agentRows,
      people: hit.filter((c) => c.kind === 'human'),
      selectable: agentRows,
    };
  }, [candidates, filter]);

  useEffect(() => {
    onItemsChange(selectable);
  }, [selectable, onItemsChange]);

  // A filter matching nobody is prose, not a gesture — dismiss, so an email
  // address ("kvk@gmail.com") never strands a menu over the composer. Note the
  // server's own grammar agrees: `_MENTION` requires a leading boundary, so
  // that text was never a mention to begin with.
  useEffect(() => {
    if (filter.length > 0 && agents.length === 0 && people.length === 0) onClose();
  }, [filter, agents.length, people.length, onClose]);

  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [onClose]);

  if (agents.length === 0 && people.length === 0) return null;

  return (
    <div
      ref={rootRef}
      role="listbox"
      aria-label="Address someone in this conversation"
      className="absolute bottom-full left-0 mb-2 w-72 max-h-72 overflow-y-auto rounded-md border border-border bg-background p-1 shadow-lg z-30 animate-in fade-in slide-in-from-bottom-2 duration-150"
    >
      {agents.length > 0 && (
        <>
          <div className="px-2 pt-1.5 pb-1 text-[10px] uppercase tracking-wide text-muted-foreground/70">
            Agents
          </div>
          {agents.map((c, i) => (
            <button
              key={`agent-${c.handle}`}
              type="button"
              role="option"
              aria-selected={i === highlight}
              data-mention-item={i}
              onMouseEnter={() => onHighlight(i)}
              // mousedown, not click: the composer must not lose focus before
              // the pick lands (the same reason the palette never takes focus).
              onMouseDown={(e) => {
                e.preventDefault();
                onPick(c);
              }}
              className={cn(
                'w-full flex items-center gap-2 px-2 py-1.5 rounded text-left text-sm transition-colors',
                i === highlight ? 'bg-muted' : 'hover:bg-muted/60',
              )}
            >
              <AgentFace name={c.name} avatarUrl={c.avatarUrl} size="sm" />
              <span className="min-w-0 flex-1">
                <span className="block truncate">{c.name}</span>
                {c.blurb && (
                  <span className="block truncate text-[11px] text-muted-foreground">
                    {c.blurb}
                  </span>
                )}
              </span>
            </button>
          ))}
        </>
      )}

      {people.length > 0 && (
        <>
          <div className="px-2 pt-2 pb-1 text-[10px] uppercase tracking-wide text-muted-foreground/70">
            People
          </div>
          {people.map((c) => (
            <div
              key={`human-${c.handle}`}
              aria-disabled
              className="w-full flex items-center gap-2 px-2 py-1.5 rounded text-left text-sm opacity-45 cursor-default"
            >
              <AgentFace name={c.name} avatarUrl={c.avatarUrl} size="sm" />
              <span className="min-w-0 flex-1 truncate">{c.name}</span>
            </div>
          ))}
          <div className="px-2 pb-1.5 pt-0.5 text-[10px] text-muted-foreground/70">
            Mentioning a person doesn&apos;t notify them yet.
          </div>
        </>
      )}

      {agents.length > 0 && (
        <div className="border-t border-border/60 mt-1 px-2 py-1 text-[10px] text-muted-foreground/70">
          ↑↓ Navigate · ↵ Select · Esc Close
        </div>
      )}
    </div>
  );
}
