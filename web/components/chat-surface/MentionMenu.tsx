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
 * PEOPLE ARE LIVE TARGETS (ADR-605 closed the ADR-495 D6 gap). One
 * species-blind gesture, two consequences: an @agent routes a TURN (it
 * answers now); an @person routes ATTENTION (their To-do + bell, and a
 * dial-gated email) — the ADR-492 D3 split, built. The sections stay
 * labelled because the consequences differ and the member should know
 * which kind of colleague they are reaching for.
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
  /** Agents route a turn; people route attention (ADR-605). */
  kind: 'agent' | 'human';
  /** Layer-1 G4 — a workspace member NOT in this cast. Never a mention
   *  target (no delivery to promise); picking one opens the add-participant
   *  drill-in instead — a real door, not the inert row this menu used to
   *  carry. Absent/true = in the cast. */
  inCast?: boolean;
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
  /** Picking a NOT-in-cast member — the host opens the add-participant
   *  drill-in (adding is an explicit disclosure decision with a visibility
   *  window, ADR-495 D2; a mention must never perform it as a side effect). */
  onPickOutsider?: (c: MentionCandidate) => void;
  onClose: () => void;
  /** Reports the SELECTABLE rows up, so the host's Enter picks the same row
   *  this list highlights — agents first, then people, matching the render
   *  order so the highlight index and the visible list never disagree. */
  onItemsChange: (items: MentionCandidate[]) => void;
}

export function MentionMenu({
  candidates,
  filter,
  highlight,
  onHighlight,
  onPick,
  onPickOutsider,
  onClose,
  onItemsChange,
}: MentionMenuProps) {
  const rootRef = useRef<HTMLDivElement>(null);

  const { agents, people, outsiders, selectable } = useMemo(() => {
    const q = filter.trim().toLowerCase();
    const match = (c: MentionCandidate) =>
      !q || c.handle.toLowerCase().includes(q) || c.name.toLowerCase().includes(q);
    const hit = candidates.filter(match);
    const agentRows = hit.filter((c) => c.kind === 'agent' && c.inCast !== false);
    const peopleRows = hit.filter((c) => c.kind === 'human' && c.inCast !== false);
    return {
      agents: agentRows,
      people: peopleRows,
      // G4 — not-in-cast members are click-only doors (never Enter-picked
      // into a mention: there is no delivery to promise).
      outsiders: hit.filter((c) => c.inCast === false),
      // ADR-605 — people are live targets: the flat keyboard order matches
      // the render order (agents, then people).
      selectable: [...agentRows, ...peopleRows],
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
    if (filter.length > 0 && agents.length === 0 && people.length === 0 && outsiders.length === 0)
      onClose();
  }, [filter, agents.length, people.length, outsiders.length, onClose]);

  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [onClose]);

  if (agents.length === 0 && people.length === 0 && outsiders.length === 0) return null;

  return (
    <div
      ref={rootRef}
      role="listbox"
      aria-label="Address someone in this conversation"
      className="absolute bottom-full left-0 mb-2 w-72 max-h-72 overflow-y-auto rounded-md border border-border bg-background p-1 shadow-lg z-30 animate-in fade-in slide-in-from-bottom-2 duration-150"
    >
      {agents.length > 0 && (
        <>
          {/* No "AGENTS" heading when they are the only rows — a section label
              over an unsectioned list is chrome. It returns below only because
              People follow and the two need telling apart. */}
          {people.length > 0 && (
            <div className="px-2 pt-1.5 pb-1 text-[10px] uppercase tracking-wide text-muted-foreground/70">
              Agents
            </div>
          )}
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
              {/* The NAME alone. The blurb was here and it was noise at the
                  moment of choosing: the member is picking a colleague they
                  already know, mid-sentence, and a two-line row pushed the
                  list past a glance. Who they are belongs on the Agents
                  surface; this is an address book. */}
              <span className="min-w-0 flex-1 truncate">{c.name}</span>
            </button>
          ))}
        </>
      )}

      {people.length > 0 && (
        <>
          <div className="px-2 pt-2 pb-1 text-[10px] uppercase tracking-wide text-muted-foreground/70">
            People
          </div>
          {people.map((c, i) => {
            // Flat keyboard index continues past the agent rows (selectable
            // order = render order).
            const idx = agents.length + i;
            return (
              <button
                key={`human-${c.handle}`}
                type="button"
                role="option"
                aria-selected={idx === highlight}
                data-mention-item={idx}
                title="Mentioning a person flags it for them — they’ll see it in their notifications"
                onMouseEnter={() => onHighlight(idx)}
                onMouseDown={(e) => {
                  e.preventDefault();
                  onPick(c);
                }}
                className={cn(
                  'w-full flex items-center gap-2 px-2 py-1.5 rounded text-left text-sm transition-colors',
                  idx === highlight ? 'bg-muted' : 'hover:bg-muted/60',
                )}
              >
                <AgentFace name={c.name} avatarUrl={c.avatarUrl} size="sm" />
                <span className="min-w-0 flex-1 truncate">{c.name}</span>
              </button>
            );
          })}
        </>
      )}

      {outsiders.length > 0 && onPickOutsider && (
        <>
          <div className="px-2 pt-2 pb-1 text-[10px] uppercase tracking-wide text-muted-foreground/70">
            Not in this conversation
          </div>
          {outsiders.map((c) => (
            <button
              key={`outsider-${c.handle}`}
              type="button"
              title="Opens Add people — adding them is your call, never a mention's side effect"
              onMouseDown={(e) => {
                e.preventDefault();
                onPickOutsider(c);
              }}
              className="w-full flex items-center gap-2 px-2 py-1.5 rounded text-left text-sm opacity-70 hover:opacity-100 hover:bg-muted/60 transition-all"
            >
              <AgentFace name={c.name} avatarUrl={c.avatarUrl} size="sm" />
              <span className="min-w-0 flex-1 truncate">{c.name}</span>
              <span className="shrink-0 text-[10px] text-muted-foreground">add…</span>
            </button>
          ))}
        </>
      )}

    </div>
  );
}
