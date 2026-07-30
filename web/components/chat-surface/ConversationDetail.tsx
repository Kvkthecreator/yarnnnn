'use client';

/**
 * ConversationDetail — the participants drill-in (ADR-495 D1/D3).
 *
 * The nested layout every messaging app has behind its header: who is here,
 * what each may read, add someone, remove someone. Routed by the
 * window-namespaced `chat.detail=participants` param (ADR-358 D6) and closed by
 * `onBack` — the same shape `ManageConnectionSubsurface` established for the
 * Channels surface's intra-pane drill-in. NOT a modal: a modal cannot be
 * deep-linked, cannot own a back chip, and on a phone it fights the one-screen
 * discipline (ADR-297 D15).
 *
 * WHY IT EXISTS. The cast used to live as a chip-per-participant strip inside
 * the header, with the invite behind a popover on that strip. That shape is
 * bounded by pixels: it wrapped at three participants and had nowhere to put
 * per-participant acts. In particular REMOVE was unreachable —
 * `DELETE /lanes/{id}/participants` shipped and was gated by
 * `test_last_human_cannot_be_removed`, but no UI ever called it. A tested
 * endpoint no member can reach is the deleted-affordance failure mode; this is
 * where it gets exercised.
 *
 * SPECIES-BLIND (ADR-495 D3). One list, one add, one remove. People and Agents
 * are grouped under headings because that is how a human scans a list — but the
 * verbs are identical and call the same endpoints with the same shapes. The
 * window control is offered for BOTH classes, which is what ADR-495 D3 claimed
 * and the shipped CastBar did not do (it rendered the checkbox only under
 * "People"; the docstring asserted a symmetry the markup didn't implement).
 * Defaults still differ — Agent full history, human from-now — because
 * class-differing DEFAULTS are dial settings (ADR-405 D4), not species law.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, Check, Loader2, Trash2, UserPlus, X } from 'lucide-react';
import { AgentFace } from '@/components/agents/AgentFace';
import { api, type Participant } from '@/lib/api/client';
import { cn } from '@/lib/utils';

export interface DetailAgentChoice {
  slug: string;
  name: string;
  avatar_url?: string;
}

export interface DetailPersonChoice {
  principal_id: string;
  label: string;
}

interface ConversationDetailProps {
  laneId: string;
  laneName: string;
  agents: DetailAgentChoice[];
  people: DetailPersonChoice[];
  viewerId?: string | null;
  initialParticipants?: Participant[];
  /** Close the drill-in (clears the `chat.detail` param). */
  onBack: () => void;
  /** The cast changed — the parent refreshes its list row + header. */
  onCastChanged?: (participants: Participant[]) => void;
}

export function ConversationDetail({
  laneId,
  laneName,
  agents,
  people,
  viewerId,
  initialParticipants,
  onBack,
  onCastChanged,
}: ConversationDetailProps) {
  const [participants, setParticipants] = useState<Participant[]>(
    initialParticipants ?? [],
  );
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // ADR-495 D2 — the window the NEXT invite carries. Offered for both classes;
  // "from now" leads for people because disclosure is irreversible.
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
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setAdding(false);
      }
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setAdding(false);
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [adding]);

  const agentBySlug = useMemo(
    () => new Map(agents.map((a) => [a.slug, a])),
    [agents],
  );
  const personById = useMemo(
    () => new Map(people.map((p) => [p.principal_id, p])),
    [people],
  );

  const humans = participants.filter((p) => p.member_kind === 'human');
  const castAgents = participants.filter((p) => p.member_kind === 'agent');

  const inCast = useMemo(
    () => ({
      humans: new Set(humans.map((p) => p.principal_id)),
      agents: new Set(castAgents.map((p) => p.agent_slug)),
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [participants],
  );

  const invitableAgents = agents.filter((a) => !inCast.agents.has(a.slug));
  const invitablePeople = people.filter((p) => !inCast.humans.has(p.principal_id));

  const commit = useCallback(
    (next: Participant[]) => {
      setParticipants(next);
      onCastChanged?.(next);
    },
    [onCastChanged],
  );

  const add = useCallback(
    async (data: Parameters<typeof api.lanes.addParticipant>[1], key: string) => {
      setBusy(key);
      setError(null);
      try {
        const res = await api.lanes.addParticipant(laneId, data);
        commit(res.participants);
        setAdding(false);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Could not add them');
      } finally {
        setBusy(null);
      }
    },
    [laneId, commit],
  );

  const remove = useCallback(
    async (p: Participant) => {
      const key = p.principal_id || p.agent_slug || '';
      setBusy(key);
      setError(null);
      try {
        const res = await api.lanes.removeParticipant(
          laneId,
          p.member_kind === 'human'
            ? { principal_id: p.principal_id! }
            : { agent_slug: p.agent_slug! },
        );
        commit(res.participants);
      } catch (e) {
        // The server refuses the last human (a conversation nobody can read is
        // deletion wearing another name) — show ITS words, not a guess.
        setError(e instanceof Error ? e.message : 'Could not remove them');
      } finally {
        setBusy(null);
      }
    },
    [laneId, commit],
  );

  const label = (p: Participant) => {
    if (p.member_kind === 'agent') {
      return agentBySlug.get(p.agent_slug || '')?.name || p.agent_slug || 'agent';
    }
    if (p.principal_id && p.principal_id === viewerId) return 'You';
    return personById.get(p.principal_id || '')?.label || 'member';
  };

  /** The window, said plainly — the same sentence for every participant. */
  const windowNote = (p: Participant) =>
    p.visible_from_sequence > 0
      ? `Joined partway — reads from turn ${p.visible_from_sequence}`
      : 'Reads the whole conversation';

  const row = (p: Participant) => {
    const a = p.member_kind === 'agent' ? agentBySlug.get(p.agent_slug || '') : null;
    const key = `${p.member_kind}:${p.principal_id || p.agent_slug}`;
    const busyKey = p.principal_id || p.agent_slug || '';
    const isSelf = p.member_kind === 'human' && p.principal_id === viewerId;
    return (
      <div
        key={key}
        className="flex items-center gap-2.5 px-3 py-2 border-b border-border/50 group"
      >
        <AgentFace name={a?.name || label(p)} avatarUrl={a?.avatar_url} size="md" />
        <span className="flex-1 min-w-0">
          <span className="block text-sm truncate">{label(p)}</span>
          <span className="block text-[10px] text-muted-foreground truncate">
            {windowNote(p)}
          </span>
        </span>
        {/* Remove — the endpoint that shipped with no door. Hidden on your own
            row: leaving a conversation is a different act from removing someone
            (and the server refuses the last human regardless). */}
        {!isSelf && (
          <button
            type="button"
            disabled={!!busy}
            onClick={() => void remove(p)}
            className="p-1.5 rounded text-muted-foreground/0 group-hover:text-muted-foreground hover:!text-destructive transition-colors disabled:opacity-50"
            aria-label={`Remove ${label(p)}`}
            title="Remove from this conversation"
          >
            {busy === busyKey ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Trash2 className="w-3.5 h-3.5" />
            )}
          </button>
        )}
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col min-h-0">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border shrink-0">
        <button
          type="button"
          onClick={onBack}
          className="p-1 -ml-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          aria-label="Back to the conversation"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <span className="min-w-0">
          <span className="block text-sm font-medium truncate">Details</span>
          <span className="block text-[10px] text-muted-foreground truncate">
            {laneName}
          </span>
        </span>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="px-3 pt-3 pb-1 flex items-center justify-between">
          <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
            {participants.length} in this conversation
          </span>
          <div className="relative">
            <button
              type="button"
              onClick={() => setAdding((v) => !v)}
              className="flex items-center gap-1 px-2 py-1 rounded-md border border-dashed border-border text-[11px] text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              <UserPlus className="w-3 h-3" />
              Add
            </button>

            {adding && (
              <div
                ref={popoverRef}
                className="absolute right-0 top-full mt-1 w-64 rounded-md border border-border bg-card shadow-lg z-30 p-1.5"
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

                {/* ADR-495 D3 — ONE window control, above BOTH groups. The
                    shipped CastBar put it under "People" only, so the symmetry
                    its own docstring claimed wasn't in the markup. */}
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

                {invitablePeople.length > 0 && (
                  <>
                    <p className="px-1 pt-1 text-[10px] uppercase tracking-wide text-muted-foreground/70">
                      People
                    </p>
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
                        onClick={() =>
                          void add(
                            {
                              kind: 'agent',
                              agent_slug: a.slug,
                              // The SAME control, honored identically. Absent →
                              // the server pre-selects the class default.
                              ...(shareHistory ? { visible_from_sequence: 0 } : {}),
                            },
                            a.slug,
                          )
                        }
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
              </div>
            )}
          </div>
        </div>

        {error && (
          <p className="px-3 py-1.5 text-[11px] text-destructive" role="alert">
            {error}
          </p>
        )}

        {humans.length > 0 && (
          <>
            <p className="px-3 pt-2 pb-1 text-[10px] uppercase tracking-wide text-muted-foreground/70">
              People
            </p>
            {humans.map(row)}
          </>
        )}
        {castAgents.length > 0 && (
          <>
            <p className="px-3 pt-3 pb-1 text-[10px] uppercase tracking-wide text-muted-foreground/70">
              Agents
            </p>
            {castAgents.map(row)}
          </>
        )}
        {castAgents.length === 0 && (
          // The honest consequence of a cast with no Agent: nothing here
          // answers. Said where the member is looking at the cast, not as an
          // error somewhere else.
          <p className="px-3 py-3 text-[11px] text-muted-foreground">
            No Agent is in this conversation, so nobody replies automatically —
            it&apos;s just the people here. Add one and replies begin.
          </p>
        )}
      </div>
    </div>
  );
}
