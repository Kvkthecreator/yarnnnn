'use client';

/**
 * ConversationHeader — one row that says WHO you are talking to (ADR-495 D1).
 *
 * THE GRAMMAR (conventional messaging, per the operator's ruling 2026-07-30):
 *
 *     [stacked faces] Title              · N people        [⋯]
 *
 * That is the whole header. It is deliberately the shape Messenger / iMessage /
 * Slack converged on, because the job is the same one: name the room, say how
 * many are in it, and put everything else one tap away.
 *
 * WHAT IT REPLACES. The shipped header did four jobs in one flex row: identity
 * (face + name + sub-label), the lane name behind a divider, the FULL cast as a
 * chip per participant with an inline Add popover, and an actions portal. At
 * three participants it wrapped; on a phone it was unusable. The cast moves
 * behind `⋯` (the drill-in, `ConversationDetail`) — which is where a
 * conventional app puts it, and which is the only shape that survives N
 * participants.
 *
 * WHO LEADS (unchanged rule, now applied to the mixed cast too): people lead
 * whenever there are people — a conversation with colleagues is named by them
 * even when an Agent is also in the room. Only a conversation with no other
 * humans is named by its Agent. The engine is never the headline; it rides in
 * the sub-label, where it stays visible without pretending to be the
 * counterpart (ADR-460 D4 / ADR-463 §3).
 *
 * The faces are a LINK when a single Agent is the counterpart (the
 * `/chat`→`/agents` door, §6.10c). In a group there is no single card to open,
 * so the faces open the drill-in instead — one gesture, one destination.
 */

import { MoreHorizontal } from 'lucide-react';
import { AgentFace } from '@/components/agents/AgentFace';
import { SurfaceLink } from '@/components/shell/SurfaceLink';
import { cn } from '@/lib/utils';

export interface HeaderFace {
  /** Display name — also the initial fallback when there is no picture. */
  name: string;
  /** Resolved avatar reference (Agents); people have none today. */
  avatarUrl?: string | null;
}

interface ConversationHeaderProps {
  /** The room's name — people when there are people, else the Agent/engine. */
  title: string;
  /** The quiet second line: `N people · with Lisa`, `Critic · GPT-5`, … */
  subtitle?: string;
  /** Up to three faces, stacked. Empty renders no avatar cluster. */
  faces: HeaderFace[];
  /** Total participants including the viewer — rendered as the count chip when
   *  greater than two (a 1:1 needs no count; "2 people" is noise). */
  participantCount: number;
  /** When exactly one Agent is the counterpart, its slug — the faces become a
   *  link to its card. Absent in groups. */
  agentSlug?: string | null;
  /** Open the participants/details drill-in. */
  onOpenDetails: () => void;
}

/** Stacked faces, newest behind — the conventional group avatar. */
function FaceStack({ faces }: { faces: HeaderFace[] }) {
  if (!faces.length) return null;
  const shown = faces.slice(0, 3);
  return (
    <span className="flex items-center shrink-0">
      {shown.map((f, i) => (
        <span
          key={`${f.name}-${i}`}
          // Overlap all but the first; later faces sit behind, so the primary
          // participant stays fully legible.
          className={cn(i > 0 && '-ml-2')}
          style={{ zIndex: shown.length - i }}
        >
          <AgentFace
            name={f.name}
            avatarUrl={f.avatarUrl}
            size={shown.length > 1 ? 'sm' : 'md'}
            className={shown.length > 1 ? 'ring-2 ring-background' : undefined}
          />
        </span>
      ))}
    </span>
  );
}

export function ConversationHeader({
  title,
  subtitle,
  faces,
  participantCount,
  agentSlug,
  onOpenDetails,
}: ConversationHeaderProps) {
  const identity = (
    <>
      <FaceStack faces={faces} />
      <span className="min-w-0">
        <span className="block text-sm font-medium truncate">{title}</span>
        {subtitle && (
          <span className="block text-[10px] text-muted-foreground truncate">
            {subtitle}
          </span>
        )}
      </span>
    </>
  );

  return (
    <div className="flex items-center gap-2 px-3 py-2 border-b border-border shrink-0">
      {agentSlug ? (
        <SurfaceLink
          to="agents"
          params={{ agent: agentSlug }}
          className="flex items-center gap-2 min-w-0 rounded hover:bg-muted -mx-1 px-1 py-0.5 transition-colors"
          title={`About ${title}`}
        >
          {identity}
        </SurfaceLink>
      ) : (
        // No single card to open (a group, or a pre-registry lane) — the
        // identity opens the details instead. Never a dead affordance.
        <button
          type="button"
          onClick={onOpenDetails}
          className="flex items-center gap-2 min-w-0 rounded hover:bg-muted -mx-1 px-1 py-0.5 transition-colors text-left"
          title="Conversation details"
        >
          {identity}
        </button>
      )}

      {/* The count — the one fact the old header never showed. Suppressed at
          two, where it would only restate what the title already says. */}
      {participantCount > 2 && (
        <button
          type="button"
          onClick={onOpenDetails}
          className="shrink-0 px-1.5 py-px rounded-full bg-muted text-[10px] text-muted-foreground hover:text-foreground transition-colors"
          title="See who's in this conversation"
        >
          {participantCount} people
        </button>
      )}

      <div className="ml-auto flex items-center gap-1 shrink-0">
        <button
          type="button"
          onClick={onOpenDetails}
          className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          aria-label="Conversation details"
          title="Details"
        >
          <MoreHorizontal className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
