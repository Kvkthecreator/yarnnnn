'use client';

/**
 * ConversationHeader — one row that says WHO you are talking to (ADR-495 D1).
 *
 * THE GRAMMAR (conventional messaging, per the operator's rulings 2026-07-30 +
 * 2026-08-03):
 *
 *     [stacked faces] Title       · N members        [+] [⋯]
 *
 * That is the whole header. It is deliberately the shape Messenger / iMessage /
 * Slack converged on, because the job is the same one: name the room, say how
 * many are in it, offer the one act that grows it, and put everything else one
 * tap away.
 *
 * WHAT IT REPLACES. The shipped header did four jobs in one flex row: identity
 * (face + name + sub-label), the lane name behind a divider, the FULL cast as a
 * chip per participant with an inline Add popover, and an actions portal. At
 * three participants it wrapped; on a phone it was unusable. The cast moves
 * behind `⋯` (the drill-in, `ConversationDetail`) — which is where a
 * conventional app puts it, and which is the only shape that survives N
 * participants.
 *
 * WHO LEADS — SPECIES-BLIND (corrected 2026-08-03, ADR-495 D1 + ADR-405 §5).
 * The room is named by EVERY participant but the viewer, in cast order, without
 * asking what kind each one is. A group is a group whether its members are
 * people, Agents, or both.
 *
 * The rule this replaces named the room after "the other humans" and fell
 * through to "the lane's Agent" when there were none — so a cast of {you, Lisa,
 * Thinker} rendered as "Lisa · Critic · GPT-5": one member promoted to be the
 * room's entire identity and the other silently dropped, a group of three
 * reading as a 1:1 with a spec sheet. That fall-through was species law wearing
 * a naming convention — humans made a group, Agents made a counterpart.
 *
 * The engine is never the headline. In a 1:1 with an Agent it rides in the
 * sub-label (`Critic · GPT-5`), where it stays visible without pretending to be
 * the counterpart (ADR-460 D4 / ADR-463 §3); in a group the sub-label says the
 * size instead, because no single member's spec describes the room.
 *
 * The faces are a LINK when a single Agent is the counterpart (the
 * `/chat`→`/agents` door, §6.10c). In a group there is no single card to open,
 * so the faces open the drill-in instead — one gesture, one destination.
 */

import { MoreHorizontal, UserPlus } from 'lucide-react';
import { AgentFace } from '@/components/agents/AgentFace';
import { SurfaceLink } from '@/components/shell/SurfaceLink';
import { engineBrandIcon } from '@/lib/ai-providers/brand-icons';
import { cn } from '@/lib/utils';

export interface HeaderFace {
  /** Display name — also the initial fallback when there is no picture. */
  name: string;
  /** Resolved avatar reference (Agents); people have none today. */
  avatarUrl?: string | null;
}

interface ConversationHeaderProps {
  /** The room's name — EVERY participant but the viewer, species-blind. A
   *  group is named by its cast; a 1:1 by its counterpart, whatever it is. */
  title: string;
  /** The quiet second line: `N members` for a group, `Critic · GPT-5` or
   *  `Direct chat` for a 1:1. */
  subtitle?: string;
  /** ADR-558 D5 — the engine's model id, for the provider's brand mark beside
   *  the subtitle. The MODEL, not a label: the mark keys on the id (the
   *  `brand-icons` contract). Omitted for a group or a person-only chat, where
   *  there is no single engine to attribute. */
  engineModel?: string | null;
  /** Up to three faces, stacked. Empty renders no avatar cluster. */
  faces: HeaderFace[];
  /** Total participants including the viewer, humans AND Agents. Rendered as
   *  the count chip above two (a 1:1 needs no count — the title names it). */
  participantCount: number;
  /** When exactly one Agent is the counterpart, its slug — the faces become a
   *  link to its card. Absent in groups. */
  agentSlug?: string | null;
  /** Open the participants/details drill-in. */
  onOpenDetails: () => void;
  /** Open the add-participant flow — the dedicated header act. Separate from
   *  `onOpenDetails` because ADDING is not the same job as INSPECTING, and
   *  burying the invite inside the roster made it read as absent. */
  onAddParticipant: () => void;
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
  engineModel,
  faces,
  participantCount,
  agentSlug,
  onOpenDetails,
  onAddParticipant,
}: ConversationHeaderProps) {
  const identity = (
    <>
      <FaceStack faces={faces} />
      <span className="min-w-0">
        <span className="block text-sm font-medium truncate">{title}</span>
        {subtitle && (
          <span className="flex items-center gap-1 text-[10px] text-muted-foreground min-w-0">
            {engineModel && (
              <span className="shrink-0 [&>svg]:w-2.5 [&>svg]:h-2.5">
                {engineBrandIcon(engineModel)}
              </span>
            )}
            <span className="truncate">{subtitle}</span>
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

      {/* The count. "members", never "people" — a cast is humans AND Agents,
          and calling a room of {you, Lisa, Thinker} "3 people" is the species
          assumption showing through the chrome (operator-observed 2026-08-03).
          Suppressed at two, where the title already names the counterpart. */}
      {participantCount > 2 && (
        <button
          type="button"
          onClick={onOpenDetails}
          className="shrink-0 px-1.5 py-px rounded-full bg-muted text-[10px] text-muted-foreground hover:text-foreground transition-colors"
          title="See who's in this conversation"
        >
          {participantCount} members
        </button>
      )}

      <div className="ml-auto flex items-center gap-1 shrink-0">
        {/* ADD — a FIRST-CLASS header act (operator ruling 2026-08-03).
            Growing the cast is the primary thing you do to a conversation from
            outside the transcript, and every conventional messaging app puts it
            on the header for that reason. It was previously reachable only
            inside Details, which read as "there is no invite here". */}
        <button
          type="button"
          onClick={onAddParticipant}
          className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          aria-label="Add someone to this conversation"
          title="Add people or agents"
        >
          <UserPlus className="w-4 h-4" />
        </button>
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
