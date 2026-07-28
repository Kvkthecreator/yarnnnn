'use client';

/**
 * RoomPanel — a shared Conversation (ADR-492: a room).
 *
 * A room is workspace CONTENT (DP35): every grant-holder reads the same
 * transcript; every turn is attributed. The invariants this panel renders:
 *
 * - NEVER-AMBIENT: sending a plain message fires nothing. An Agent member
 *   answers only when ADDRESSED — the "Ask" chip on the composer (or an
 *   @slug mention in the text). Addressing IS selection (ADR-492 D3).
 * - Attribution verbatim: your turns render as you; an Agent's turns render
 *   with the Agent's face and "via {model}" — the face is the Agent, the
 *   ledger says the member's hands (ADR-460).
 * - Invite is the explicit membership act (D6.e invite·keep·share): humans
 *   from the workspace roster (grant-holders only), Agents from the registry.
 *
 * Freshness is pull (ADR-407 D2 — macOS, not Figma): refetch after your own
 * sends plus a slow poll while the room is open. No presence, no typing
 * indicators (ADR-492 §6 non-goals).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowUp,
  Loader2,
  UserPlus,
  X,
} from 'lucide-react';
import { AgentFace } from '@/components/agents/AgentFace';
import { api } from '@/lib/api/client';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { useWorkspaceRoster } from '@/lib/workspace/viewer';
import { cn } from '@/lib/utils';

const POLL_MS = 8000;

interface RoomMember {
  member_kind: 'human' | 'agent';
  principal_id: string | null;
  agent_slug: string | null;
}

interface RoomMessage {
  id: string;
  author_principal_id: string;
  via_model: string | null;
  agent_slug: string | null;
  content: string;
  created_at: string;
}

export interface RoomAgentInfo {
  slug: string;
  name: string;
  avatar_url?: string;
}

interface RoomPanelProps {
  roomId: string;
  /** The registry chooser payload (ChatSurface already holds it) — faces for
   *  agent members and the invite list. */
  agents: RoomAgentInfo[];
  /** Workspace humans (principal_id → label), for the invite list. */
  people: Array<{ principal_id: string; label: string }>;
  onRenamed?: (title: string) => void;
}

export function RoomPanel({ roomId, agents, people, onRenamed }: RoomPanelProps) {
  const { userId } = useSurfacePreferences();
  const { labels } = useWorkspaceRoster();

  const [members, setMembers] = useState<RoomMember[]>([]);
  const [title, setTitle] = useState('');
  const [messages, setMessages] = useState<RoomMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [ask, setAsk] = useState<string | null>(null);
  const [inviting, setInviting] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const agentBySlug = useMemo(() => {
    const m = new Map<string, RoomAgentInfo>();
    for (const a of agents) m.set(a.slug, a);
    return m;
  }, [agents]);

  const load = useCallback(async () => {
    try {
      const res = await api.rooms.get(roomId);
      setTitle(res.room.title);
      setMembers(res.room.members);
      setMessages(res.messages);
      // The addressed default follows the cast: one Agent → asking them is
      // the obvious default; several → the member picks per turn.
      setAsk((cur) => {
        const agentMembers = res.room.members.filter((m) => m.member_kind === 'agent');
        if (cur && agentMembers.some((m) => m.agent_slug === cur)) return cur;
        return agentMembers.length === 1 ? agentMembers[0].agent_slug : null;
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load this room');
    } finally {
      setLoading(false);
    }
  }, [roomId]);

  useEffect(() => {
    setLoading(true);
    setMessages([]);
    void load();
    const t = setInterval(() => void load(), POLL_MS);
    return () => clearInterval(t);
  }, [load]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' });
  }, [messages.length]);

  const humanMembers = members.filter((m) => m.member_kind === 'human');
  const agentMembers = members.filter((m) => m.member_kind === 'agent');

  const personLabel = useCallback(
    (pid: string) =>
      pid === userId ? 'You' : labels.get(pid) || people.find((p) => p.principal_id === pid)?.label || `member-${pid.slice(0, 8)}`,
    [labels, people, userId],
  );

  const send = useCallback(async () => {
    const content = input.trim();
    if (!content || sending) return;
    setSending(true);
    setError(null);
    // Optimistic: show the human turn immediately.
    const optimistic: RoomMessage = {
      id: `optimistic-${Date.now()}`,
      author_principal_id: userId || '',
      via_model: null,
      agent_slug: null,
      content,
      created_at: new Date().toISOString(),
    };
    setMessages((cur) => [...cur, optimistic]);
    setInput('');
    try {
      await api.rooms.postMessage(roomId, {
        content,
        ...(ask ? { address: ask } : {}),
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not send');
      setMessages((cur) => cur.filter((m) => m.id !== optimistic.id));
      setInput(content);
    } finally {
      setSending(false);
    }
  }, [input, sending, roomId, ask, userId, load]);

  const invite = useCallback(
    async (spec: { kind: 'human' | 'agent'; principal_id?: string; agent_slug?: string }) => {
      setError(null);
      try {
        const res = await api.rooms.invite(roomId, spec);
        setMembers(res.members);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Could not invite');
      }
    },
    [roomId],
  );

  const invitableHumans = people.filter(
    (p) => !humanMembers.some((m) => m.principal_id === p.principal_id),
  );
  const invitableAgents = agents.filter(
    (a) => !agentMembers.some((m) => m.agent_slug === a.slug),
  );

  return (
    <div className="flex-1 min-h-0 flex flex-col">
      {/* Room header: who is in the room + the invite act. */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border shrink-0 flex-wrap">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={() => {
            const t = title.trim();
            if (t) {
              void api.rooms.rename(roomId, t).then(() => onRenamed?.(t)).catch(() => {});
            }
          }}
          className="text-sm font-medium bg-transparent border-none focus:outline-none focus:ring-1 focus:ring-ring rounded px-1 min-w-0 w-40"
          aria-label="Room name"
        />
        <div className="flex items-center gap-1 flex-wrap min-w-0">
          {humanMembers.map((m) => (
            <span
              key={m.principal_id}
              className="px-1.5 py-px rounded-full bg-muted text-[10px] text-muted-foreground"
            >
              {personLabel(m.principal_id || '')}
            </span>
          ))}
          {agentMembers.map((m) => {
            const a = m.agent_slug ? agentBySlug.get(m.agent_slug) : null;
            return (
              <span
                key={m.agent_slug}
                className="flex items-center gap-1 px-1.5 py-px rounded-full bg-muted text-[10px] text-muted-foreground"
              >
                <AgentFace name={a?.name || m.agent_slug || 'agent'} avatarUrl={a?.avatar_url} size="sm" />
                {a?.name || m.agent_slug}
              </span>
            );
          })}
        </div>
        <div className="ml-auto relative">
          <button
            type="button"
            onClick={() => setInviting((v) => !v)}
            className="flex items-center gap-1.5 px-2 py-1 rounded-md border border-border text-[11px] text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            aria-label="Invite to this room"
          >
            <UserPlus className="w-3.5 h-3.5" />
            Invite
          </button>
          {inviting && (
            <div className="absolute right-0 top-full mt-1 w-56 rounded-md border border-border bg-card shadow-lg z-20 p-1.5 space-y-0.5">
              <div className="flex items-center justify-between px-1 pt-0.5 pb-1">
                <span className="text-[10px] uppercase tracking-wide text-muted-foreground">Invite</span>
                <button
                  type="button"
                  onClick={() => setInviting(false)}
                  className="p-0.5 rounded text-muted-foreground hover:text-foreground"
                  aria-label="Close invite"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
              {invitableHumans.map((p) => (
                <button
                  key={p.principal_id}
                  type="button"
                  onClick={() => {
                    void invite({ kind: 'human', principal_id: p.principal_id });
                    setInviting(false);
                  }}
                  className="w-full text-left px-2 py-1 rounded text-xs hover:bg-muted"
                >
                  {p.label}
                </button>
              ))}
              {invitableAgents.map((a) => (
                <button
                  key={a.slug}
                  type="button"
                  onClick={() => {
                    void invite({ kind: 'agent', agent_slug: a.slug });
                    setInviting(false);
                  }}
                  className="w-full flex items-center gap-2 text-left px-2 py-1 rounded text-xs hover:bg-muted"
                >
                  <AgentFace name={a.name} avatarUrl={a.avatar_url} size="sm" />
                  {a.name}
                </button>
              ))}
              {invitableHumans.length === 0 && invitableAgents.length === 0 && (
                <p className="px-2 py-1 text-[11px] text-muted-foreground">
                  Everyone&apos;s already here.
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Transcript. */}
      <div className="flex-1 min-h-0 overflow-y-auto px-3 py-3 space-y-3">
        {loading && (
          <div className="text-xs text-muted-foreground py-6 text-center">Loading room…</div>
        )}
        {!loading && messages.length === 0 && (
          <div className="py-6 px-4 text-center text-xs text-muted-foreground space-y-1">
            <p className="font-medium text-foreground/80">{title}</p>
            <p>
              This room is shared — everyone in this workspace can read it, and
              every turn is attributed. Agents answer when you ask them.
            </p>
          </div>
        )}
        {messages.map((m) => {
          const isEngine = !!m.via_model;
          const isSelf = !isEngine && m.author_principal_id === userId;
          const face = isEngine && m.agent_slug ? agentBySlug.get(m.agent_slug) : null;
          return (
            <div key={m.id} className={cn('flex flex-col', isSelf ? 'items-end' : 'items-start')}>
              {!isSelf && (
                <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground mb-0.5">
                  {isEngine ? (
                    <>
                      <AgentFace name={face?.name || m.agent_slug || 'agent'} avatarUrl={face?.avatar_url} size="sm" />
                      {face?.name || m.agent_slug}
                      <span className="opacity-60">
                        via {m.via_model} · asked by {personLabel(m.author_principal_id)}
                      </span>
                    </>
                  ) : (
                    personLabel(m.author_principal_id)
                  )}
                </span>
              )}
              <div
                className={cn(
                  'rounded-lg px-3 py-2 text-sm whitespace-pre-wrap break-words max-w-[85%]',
                  isSelf ? 'bg-primary text-primary-foreground' : 'bg-muted',
                )}
              >
                {m.content}
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      {error && (
        <p className="px-3 pb-1 text-xs text-destructive" role="alert">
          {error}
        </p>
      )}

      {/* Composer. The "Ask" chips are the addressing act (ADR-492 D3):
          selection by addressing, never an engine picker. None selected =
          a plain message to the room; nothing answers (never-ambient). */}
      <div className="border-t border-border shrink-0 px-3 py-2 space-y-1.5">
        {agentMembers.length > 0 && (
          <div className="flex items-center gap-1 flex-wrap">
            <span className="text-[10px] text-muted-foreground">Ask:</span>
            <button
              type="button"
              onClick={() => setAsk(null)}
              className={cn(
                'px-2 py-0.5 rounded-full text-[11px] transition-colors',
                ask === null
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:text-foreground',
              )}
            >
              No one — just say it
            </button>
            {agentMembers.map((m) => {
              const a = m.agent_slug ? agentBySlug.get(m.agent_slug) : null;
              return (
                <button
                  key={m.agent_slug}
                  type="button"
                  onClick={() => setAsk(m.agent_slug)}
                  className={cn(
                    'px-2 py-0.5 rounded-full text-[11px] transition-colors',
                    ask === m.agent_slug
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-muted-foreground hover:text-foreground',
                  )}
                >
                  {a?.name || m.agent_slug}
                </button>
              );
            })}
          </div>
        )}
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                void send();
              }
            }}
            rows={1}
            placeholder={
              ask
                ? `Ask ${agentBySlug.get(ask)?.name || ask}…`
                : `Message ${title || 'the room'}…`
            }
            className="flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
          />
          <button
            type="button"
            onClick={() => void send()}
            disabled={sending || !input.trim()}
            className="p-2 rounded-md bg-primary text-primary-foreground disabled:opacity-40 shrink-0"
            aria-label="Send"
          >
            {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowUp className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}
