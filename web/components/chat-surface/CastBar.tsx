'use client';

/**
 * CastBar — who is in this conversation, and the one invite (ADR-495 D1/D3).
 *
 * A Conversation is PARTICIPANTS + TURNS. This is the participant half made
 * visible: one row of faces — humans and Agents together, in join order — and
 * one "Add" popover that invites either.
 *
 * THE SPECIES-BLIND RULE (ADR-495 D3): there is ONE invite. The picker groups
 * people and Agents under headings because that is how a human scans a list,
 * but both call the same endpoint with the same shape, and neither has a
 * different set of consequences. A human invite does not fork, does not flip a
 * scope, does not cost a settle. It adds a participant.
 *
 * The window (ADR-495 D2) is chosen at invite time for humans — "from now" is
 * pre-selected because disclosure is irreversible, and "share full history" is
 * one click away. Agents default to full history (an Agent that cannot see the
 * conversation cannot be useful in it). Both are DEFAULTS, not rules: the
 * control is identical for both, which is the point.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Check, Loader2, UserPlus, X } from 'lucide-react';
import { AgentFace } from '@/components/agents/AgentFace';
import { api, type Participant } from '@/lib/api/client';
import { cn } from '@/lib/utils';

export interface CastAgentChoice {
  slug: string;
  name: string;
  avatar_url?: string;
}

export interface CastPersonChoice {
  principal_id: string;
  label: string;
}

interface CastBarProps {
  laneId: string;
  /** The registry's Agents — invitable faces. */
  agents: CastAgentChoice[];
  /** Workspace humans other than the viewer — invitable people. */
  people: CastPersonChoice[];
  /** The viewer, so their own chip reads "you". Null while unresolved — the
   *  chip falls back to their label, never to a wrong name. */
  viewerId?: string | null;
  /** Seeded from the lane list so the bar paints before its own fetch. */
  initialParticipants?: Participant[];
}

export function CastBar({
  laneId,
  agents,
  people,
  viewerId,
  initialParticipants,
}: CastBarProps) {
  const [participants, setParticipants] = useState<Participant[]>(initialParticipants ?? []);
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // ADR-495 D2 — the window the NEXT human invite carries. Agents always join
  // at full history; for people the inviter chooses, and "from now" leads.
  const [shareHistory, setShareHistory] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    api.lanes
      .participants(laneId)
      .then((res) => !cancelled && setParticipants(res.participants))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [laneId]);

  useEffect(() => {
    if (!adding) return;
    const onDown = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) setAdding(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setAdding(false);
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [adding]);

  const agentBySlug = useMemo(() => new Map(agents.map((a) => [a.slug, a])), [agents]);
  const personById = useMemo(() => new Map(people.map((p) => [p.principal_id, p])), [people]);

  const inCast = useMemo(
    () => ({
      humans: new Set(participants.filter((p) => p.member_kind === 'human').map((p) => p.principal_id)),
      agents: new Set(participants.filter((p) => p.member_kind === 'agent').map((p) => p.agent_slug)),
    }),
    [participants],
  );

  const invitableAgents = agents.filter((a) => !inCast.agents.has(a.slug));
  const invitablePeople = people.filter((p) => !inCast.humans.has(p.principal_id));

  const add = useCallback(
    async (data: Parameters<typeof api.lanes.addParticipant>[1], key: string) => {
      setBusy(key);
      setError(null);
      try {
        const res = await api.lanes.addParticipant(laneId, data);
        setParticipants(res.participants);
        setAdding(false);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Could not add them');
      } finally {
        setBusy(null);
      }
    },
    [laneId],
  );

  const label = (p: Participant) => {
    if (p.member_kind === 'agent') {
      return agentBySlug.get(p.agent_slug || '')?.name || p.agent_slug || 'agent';
    }
    if (p.principal_id && p.principal_id === viewerId) return 'you';
    return personById.get(p.principal_id || '')?.label || 'member';
  };

  const humanCount = participants.filter((p) => p.member_kind === 'human').length;

  return (
    <div className="flex items-center gap-1.5 flex-wrap min-w-0">
      {participants.map((p) => {
        const a = p.member_kind === 'agent' ? agentBySlug.get(p.agent_slug || '') : null;
        return (
          <span
            key={`${p.member_kind}:${p.principal_id || p.agent_slug}`}
            className="flex items-center gap-1 px-1.5 py-px rounded-full bg-muted text-[10px] text-muted-foreground max-w-[140px]"
            title={
              // ADR-495 D2 — the window, said plainly where it is legible.
              p.visible_from_sequence > 0
                ? `Joined partway — sees this conversation from turn ${p.visible_from_sequence}`
                : 'Sees the whole conversation'
            }
          >
            {a && <AgentFace name={a.name} avatarUrl={a.avatar_url} size="sm" />}
            <span className="truncate">{label(p)}</span>
          </span>
        );
      })}

      <div className="relative">
        <button
          type="button"
          onClick={() => setAdding((v) => !v)}
          className="flex items-center gap-1 px-1.5 py-px rounded-full border border-dashed border-border text-[10px] text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          aria-label="Add someone to this conversation"
        >
          <UserPlus className="w-3 h-3" />
          Add
        </button>

        {adding && (
          <div
            ref={popoverRef}
            className="absolute left-0 top-full mt-1 w-64 rounded-md border border-border bg-card shadow-lg z-30 p-1.5"
            role="dialog"
          >
            <div className="flex items-center justify-between px-1 pt-0.5 pb-1">
              <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                Add to this conversation
              </span>
              <button
                type="button"
                onClick={() => setAdding(false)}
                className="p-0.5 rounded text-muted-foreground hover:text-foreground"
                aria-label="Close"
              >
                <X className="w-3 h-3" />
              </button>
            </div>

            {invitablePeople.length > 0 && (
              <>
                <p className="px-1 pt-1 text-[10px] uppercase tracking-wide text-muted-foreground/70">
                  People
                </p>
                {/* ADR-495 D2 — the disclosure choice, made once and visible.
                    Off = they join from here (the conservative default);
                    on = they can read what came before. */}
                <label className="flex items-center gap-1.5 px-1 py-1 text-[10px] text-muted-foreground cursor-pointer">
                  <span
                    className={cn(
                      'w-3 h-3 rounded-sm border flex items-center justify-center shrink-0',
                      shareHistory ? 'bg-foreground border-foreground' : 'border-border',
                    )}
                  >
                    {shareHistory && <Check className="w-2.5 h-2.5 text-background" />}
                  </span>
                  <input
                    type="checkbox"
                    className="sr-only"
                    checked={shareHistory}
                    onChange={(e) => setShareHistory(e.target.checked)}
                  />
                  Let them read what came before
                </label>
                {invitablePeople.map((p) => (
                  <button
                    key={p.principal_id}
                    type="button"
                    disabled={!!busy}
                    onClick={() =>
                      void add(
                        {
                          kind: 'human',
                          principal_id: p.principal_id,
                          ...(shareHistory ? { visible_from_sequence: 0 } : {}),
                        },
                        p.principal_id,
                      )
                    }
                    className="w-full flex items-center gap-2 text-left px-2 py-1 rounded text-xs hover:bg-muted disabled:opacity-50"
                  >
                    <span className="w-5 h-5 rounded-full bg-muted flex items-center justify-center text-[10px] font-medium text-muted-foreground shrink-0">
                      {p.label.slice(0, 1).toUpperCase()}
                    </span>
                    <span className="truncate flex-1">{p.label}</span>
                    {busy === p.principal_id && (
                      <Loader2 className="w-3 h-3 animate-spin text-muted-foreground shrink-0" />
                    )}
                  </button>
                ))}
              </>
            )}

            {invitableAgents.length > 0 && (
              <>
                <p className="px-1 pt-2 text-[10px] uppercase tracking-wide text-muted-foreground/70">
                  Agents
                </p>
                {invitableAgents.map((a) => (
                  <button
                    key={a.slug}
                    type="button"
                    disabled={!!busy}
                    onClick={() => void add({ kind: 'agent', agent_slug: a.slug }, a.slug)}
                    className="w-full flex items-center gap-2 text-left px-2 py-1 rounded text-xs hover:bg-muted disabled:opacity-50"
                  >
                    <AgentFace name={a.name} avatarUrl={a.avatar_url} size="sm" />
                    <span className="truncate flex-1">{a.name}</span>
                    {busy === a.slug && (
                      <Loader2 className="w-3 h-3 animate-spin text-muted-foreground shrink-0" />
                    )}
                  </button>
                ))}
              </>
            )}

            {invitablePeople.length === 0 && invitableAgents.length === 0 && (
              <p className="px-2 py-2 text-[11px] text-muted-foreground">
                Everyone available is already here.
              </p>
            )}

            {error && (
              <p className="px-2 py-1 text-[11px] text-destructive" role="alert">
                {error}
              </p>
            )}
          </div>
        )}
      </div>

      {humanCount > 1 && (
        // The one honest consequence of a second human: the conversation is no
        // longer only yours. Said once, quietly, where the cast is.
        <span className="text-[10px] text-muted-foreground/60">· shared</span>
      )}
    </div>
  );
}
