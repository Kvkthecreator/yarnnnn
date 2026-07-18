'use client';

/**
 * ChatSurface — the lanes workbench (ADR-412 D3/D4).
 *
 * Altitude 2's chrome home: the member's model-pinned helper threads
 * (ADR-411 lanes) as a windowed surface — a working area, summoned like any
 * window, distinct from the steward rail (Altitude 1, chat drawer) and the
 * Agents roster (Altitude 3).
 *
 * D4 — lanes organize by WORK, never by model: the list is flat recents
 * (updated_at desc — the API touches updated_at on every turn), each row
 * named by its work with the pinned model as a CHIP; a model FILTER facet
 * gives the by-engine view on demand. Model-first folders are rejected
 * (ADR-385 precedent: group by relationship, never transport).
 *
 * The guardrail (ADR-412 D3): this is a workbench over the shared
 * workspace, not the product's center — the ADR-411 contract is restated
 * in the empty states (lanes are isolated conversations; the workspace is
 * the shared memory; the work lands in files, attributed).
 *
 * Member-experience scope: `GET /api/lanes` returns only the viewer's
 * lanes in the acting workspace (ADR-407 D6). Active lane deep-links via
 * the window-namespaced `chat.lane` param (ADR-358 D6).
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Archive, Loader2, MessageCircle, Pencil, Pin, Plus, Search, X } from 'lucide-react';
import { LanePanel } from './LanePanel';
import { AgentFace } from '@/components/agents/AgentFace';
import { NewChatModal } from './NewChatModal';
import { api } from '@/lib/api/client';
import { formatRelativeTime } from '@/lib/formatting';
import { cn } from '@/lib/utils';
import { useSurfaceParam } from '@/lib/shell/useSurfacePreferences';
import { useSelfLocatedSurface, useWindowCrumb } from '@/contexts/BreadcrumbContext';

interface LaneInfo {
  id: string;
  name: string;
  model: string;
  /** ADR-460 D4 — WHO this lane talks to. Absent on pre-registry lanes and on
   *  Studio/derive lanes: the UI falls back to the model label, which is
   *  honest (that IS what those lanes are) rather than guessed. */
  agent?: string | null;
  /** Phase-A hygiene: pinned lanes sort first. */
  pinned?: boolean;
  updated_at?: string;
  created_at?: string;
  /** ADR-450 D3 — the derive binding (null/absent for plain chat lanes). */
  derive_recipe?: string | null;
  derive_source?: string | null;
}

interface LaneData {
  enabled: boolean;
  /** ADR-460 D4 — the chooser: named colleagues, not a spec sheet. The member
   *  picks WHO; the engine rides behind the name. */
  agents?: Array<{
    slug: string; name: string; blurb: string; icon: string;
    color?: string; avatar?: string; based_on?: string; tone?: string;
    /** The image reference the FE trades for a signed URL (ADR-395). */
    avatar_url?: string;
    /** The capability's name (Critic) + the engine's label (GPT-5) — the
     *  technical fact stays VISIBLE, it just isn't the headline. */
    role?: string; engine?: string;
    /** kernel = a built-in capability; false = one the member hired + named. */
    kernel?: boolean;
  }>;
  /** Still served: every model stays routable (Studio/derive bind one
   *  directly, and the lane filter facet reads it). The registry changes what
   *  the CHOOSER asks, not what the system can run. */
  models: Array<{ id: string; label: string; vision?: boolean }>;
  /** ADR-450 D5 — kernel recipes (the Learn-from chooser payload). */
  recipes?: Array<{ slug: string; label: string; description: string }>;
  lanes: LaneInfo[];
}

export function ChatSurface() {
  const [data, setData] = useState<LaneData | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  // D4 — the FILTER facet (null = all lanes, the default view). ADR-460: it
  // filters by WHO you talked to, not by which engine ran — the last
  // spec-sheet surface in chat, re-axed. A lane with no agent (pre-registry,
  // Studio/derive) files under its engine label, which is honest: that IS
  // what those lanes are.
  const [whoFilter, setWhoFilter] = useState<string | null>(null);
  // Phase-A hygiene: search (name locally + transcript content server-side,
  // debounced) and inline rename state.
  const [query, setQuery] = useState('');
  const [contentHits, setContentHits] = useState<Set<string> | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameText, setRenameText] = useState('');
  const { get: getParam, set: setParam } = useSurfaceParam('chat');
  const activeLaneId = getParam('lane');

  // Debounced transcript search — content matches union with name matches.
  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setContentHits(null);
      return;
    }
    const t = setTimeout(() => {
      api.lanes
        .search(q)
        .then((res) => setContentHits(new Set(res.matches.map((m) => m.lane_id))))
        .catch(() => setContentHits(null));
    }, 300);
    return () => clearTimeout(t);
  }, [query]);

  useEffect(() => {
    let cancelled = false;
    api.lanes
      .list()
      .then((res) => {
        if (cancelled) return;
        setData(res as LaneData);
      })
      .catch(() => !cancelled && setData(null))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const modelLabel = useCallback(
    (modelId: string) => data?.models.find((m) => m.id === modelId)?.label ?? modelId,
    [data],
  );

  // ADR-460 D4 — a lane is named by WHO it talks to. Falls back to the engine
  // label for pre-registry lanes: those genuinely ARE a model doing a job, so
  // naming them by their engine is honest, not a gap.
  const laneAgent = useCallback(
    (lane: { agent?: string | null }) =>
      (lane.agent && data?.agents?.find((a) => a.slug === lane.agent)) || null,
    [data],
  );
  const laneLabel = useCallback(
    (lane: { agent?: string | null; model: string }) =>
      laneAgent(lane)?.name || modelLabel(lane.model),
    [laneAgent, modelLabel],
  );
  // The second line: `role · engine`. The operator's rule — a nickname must
  // still say what it IS, at minimum the model and the role. Identity leads;
  // the technical fact rides quietly behind it. A lane with no agent shows its
  // engine alone, which is honest: that IS what it is.
  const laneSubLabel = useCallback(
    (lane: { agent?: string | null; model: string }) => {
      const a = laneAgent(lane);
      if (!a) return modelLabel(lane.model);
      return [a.kernel === false ? a.role : null, a.engine || modelLabel(lane.model)]
        .filter(Boolean)
        .join(' · ');
    },
    [laneAgent, modelLabel],
  );

  // Flat recents — pinned first (Phase-A hygiene), then updated_at desc
  // (falls back to created_at). Work-first: the sort key is activity, never
  // the model (D4).
  const lanes = useMemo(() => {
    const all = [...(data?.lanes ?? [])].sort((a, b) => {
      if (!!a.pinned !== !!b.pinned) return a.pinned ? -1 : 1;
      const ta = new Date(a.updated_at ?? a.created_at ?? 0).getTime();
      const tb = new Date(b.updated_at ?? b.created_at ?? 0).getTime();
      return tb - ta;
    });
    const byModel = whoFilter
      ? all.filter((l) => laneLabel(l) === whoFilter)
      : all;
    const q = query.trim().toLowerCase();
    if (!q) return byModel;
    return byModel.filter(
      (l) => l.name.toLowerCase().includes(q) || contentHits?.has(l.id),
    );
  }, [data, whoFilter, query, contentHits, laneLabel]);

  // The facet only offers colleagues actually present in the list.
  const presentWho = useMemo(
    () => Array.from(new Set((data?.lanes ?? []).map((l) => laneLabel(l)))),
    [data, laneLabel],
  );

  const activeLane = useMemo(
    () => (data?.lanes ?? []).find((l) => l.id === activeLaneId) ?? null,
    [data, activeLaneId],
  );

  // ADR-450 D5: a derive-bound lane arrives with ONE starter chip — the
  // suggested ask in the member's words (click fills the composer, the member
  // sends — never auto-sent, the ADR-446 lesson). The recipe section on the
  // lane's turns does the heavy lifting; the chip is just the door handle.
  const deriveSuggestions = useMemo(() => {
    if (!activeLane?.derive_recipe || !activeLane?.derive_source) return undefined;
    const label =
      data?.recipes?.find((r) => r.slug === activeLane.derive_recipe)?.label ??
      activeLane.derive_recipe;
    const leaf = activeLane.derive_source.slice(activeLane.derive_source.lastIndexOf('/') + 1);
    return [`Learn from ${leaf} — create the ${label.toLowerCase()}.`];
  }, [activeLane, data]);

  // ADR-442 D5: locator honesty — the active lane is the surface's crumb
  // (`Chat › ‹lane›`; the strip's root-click returns to the lane list). The
  // in-body headers stay: they carry content state (the model chip), not
  // surface chrome (ADR-442 D3).
  useWindowCrumb(
    'chat',
    activeLane
      ? [{ label: activeLane.name, onClick: () => setParam({ lane: null }) }]
      : [],
  );
  // 2026-07-14 (operator ruling): Chat renders its OWN locator in-body — the
  // always-visible lane-list column names "Chat" + every lane (it IS the
  // navigator), and the conversation header names the active lane + model. So
  // the OS surface bar suppresses for Chat — one "you are here", never two, and
  // the ~28px band is reclaimed. (The crumb still registers above so the mobile
  // WindowFrame / any future consumer has the data; only the OS strip hides.)
  useSelfLocatedSurface('chat', true);

  const createLane = useCallback(async (agentSlug: string) => {
    if (!agentSlug) return;
    try {
      // ADR-460 D4 — send WHO. The engine resolves server-side (the slug is
      // the face, the model is the fact; the fact comes back on the response).
      // No name: a lane auto-names from its first message (Phase-A hygiene).
      const lane = await api.lanes.create({ agent: agentSlug });
      const info: LaneInfo = {
        id: lane.id,
        name: lane.name,
        model: lane.model,
        agent: lane.agent ?? agentSlug,
        updated_at: new Date().toISOString(),
      };
      setData((d) => (d ? { ...d, lanes: [...d.lanes, info] } : d));
      setParam({ lane: info.id });
      setCreating(false);
    } catch (e) {
      // SHOW it. This swallowed a live 409 ("Lane limit reached") and the
      // member saw a click that did nothing, with no reason given. The modal
      // renders what we throw.
      throw e instanceof Error ? e : new Error('Could not start this chat');
    }
  }, [setParam]);

  const archiveLane = useCallback(
    async (laneId: string) => {
      try {
        await api.lanes.archive(laneId);
        setData((d) =>
          d ? { ...d, lanes: d.lanes.filter((l) => l.id !== laneId) } : d,
        );
        if (activeLaneId === laneId) setParam({ lane: null });
      } catch {}
    },
    [activeLaneId, setParam],
  );

  // Phase-A hygiene: pin toggle + rename (lane_meta writes via PATCH).
  const updateLaneLocal = useCallback((laneId: string, patch: Partial<LaneInfo>) => {
    setData((d) =>
      d
        ? { ...d, lanes: d.lanes.map((l) => (l.id === laneId ? { ...l, ...patch } : l)) }
        : d,
    );
  }, []);

  const togglePin = useCallback(
    async (lane: LaneInfo) => {
      const next = !lane.pinned;
      updateLaneLocal(lane.id, { pinned: next });
      try {
        await api.lanes.patch(lane.id, { pinned: next });
      } catch {
        updateLaneLocal(lane.id, { pinned: lane.pinned });
      }
    },
    [updateLaneLocal],
  );

  const commitRename = useCallback(async () => {
    const laneId = renamingId;
    const name = renameText.trim();
    setRenamingId(null);
    if (!laneId || !name) return;
    const prev = data?.lanes.find((l) => l.id === laneId)?.name;
    updateLaneLocal(laneId, { name });
    try {
      await api.lanes.patch(laneId, { name });
    } catch {
      if (prev) updateLaneLocal(laneId, { name: prev });
    }
  }, [renamingId, renameText, data, updateLaneLocal]);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        <Loader2 className="w-5 h-5 animate-spin" />
      </div>
    );
  }

  // Router off — lanes have no engine (ADR-411 D2 gate). Honest state, no
  // dead affordances.
  if (!data?.enabled) {
    return (
      <div className="h-full flex items-center justify-center p-8">
        <div className="max-w-sm text-center space-y-2 text-sm text-muted-foreground">
          <MessageCircle className="w-6 h-6 mx-auto text-muted-foreground/50" />
          <p className="font-medium text-foreground/80">Lanes are not enabled</p>
          <p>
            Chat lanes run on the model router, which is not live on this
            deployment. Your conversation with Freddie is unaffected — summon
            it from the chat button.
          </p>
        </div>
      </div>
    );
  }

  // The new-chat flow is a MODAL (NewChatModal) — choosing a colleague is a
  // deliberate act with its own moment, not a drawer that shoves the lane
  // list around. The inline panel that lived here is deleted, not hidden.

  return (
    <div className="h-full flex min-h-0">
      {creating && (
        <NewChatModal
          agents={data?.agents ?? []}
          onPick={createLane}
          onClose={() => setCreating(false)}
        />
      )}
      {/* Lane list — flat recents, work-first (D4). */}
      <div className="w-72 shrink-0 border-r border-border flex flex-col min-h-0">
        <div className="flex items-center justify-between px-3 py-2.5 border-b border-border shrink-0">
          <span className="text-sm font-medium">Chat</span>
          <button
            onClick={() => setCreating((v) => !v)}
            className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            aria-label="New lane"
            title="New lane"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        {/* Phase-A hygiene: search — lane names locally + transcript content
            server-side (debounced), one filter over the same list. */}
        <div className="px-2 py-1.5 border-b border-border shrink-0">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/60" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Escape') setQuery('');
              }}
              placeholder="Search chats…"
              className="w-full rounded border border-input bg-background pl-7 pr-6 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
            />
            {query && (
              <button
                onClick={() => setQuery('')}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 p-0.5 rounded text-muted-foreground hover:text-foreground"
                aria-label="Clear search"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>

        {/* The filter facet — by WHO, on demand, never the default grouping
            (D4). Renders only when ≥2 colleagues are in play. */}
        {presentWho.length > 1 && (
          <div className="flex items-center gap-1 px-2 py-1.5 border-b border-border shrink-0 overflow-x-auto">
            <button
              onClick={() => setWhoFilter(null)}
              className={cn(
                'px-2 py-0.5 rounded-full text-[11px] whitespace-nowrap transition-colors',
                whoFilter === null
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:text-foreground',
              )}
            >
              All
            </button>
            {presentWho.map((m) => (
              <button
                key={m}
                onClick={() => setWhoFilter((cur) => (cur === m ? null : m))}
                className={cn(
                  'px-2 py-0.5 rounded-full text-[11px] whitespace-nowrap transition-colors',
                  whoFilter === m
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted text-muted-foreground hover:text-foreground',
                )}
              >
                {m}
              </button>
            ))}
          </div>
        )}

        <div className="flex-1 min-h-0 overflow-y-auto">
          {lanes.length === 0 && (
            <div className="px-4 py-8 text-center text-xs text-muted-foreground space-y-1.5">
              <p className="font-medium text-foreground/80">No lanes yet</p>
              <p>
                A lane is a conversation pinned to a model of your choice.
                Each lane is isolated — the workspace files are the shared
                memory, and a lane&apos;s work lands there, attributed to you
                via its model.
              </p>
            </div>
          )}
          {lanes.length === 0 && query.trim() && (
            <div className="px-4 py-6 text-center text-xs text-muted-foreground">
              No chats match “{query.trim()}”.
            </div>
          )}
          {lanes.map((lane) =>
            renamingId === lane.id ? (
              // Rename mode replaces the row — an input can't nest inside the
              // row <button> (invalid interactive nesting).
              <div
                key={lane.id}
                className="px-3 py-2.5 border-b border-border/50 bg-muted"
              >
                <input
                  value={renameText}
                  onChange={(e) => setRenameText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') void commitRename();
                    if (e.key === 'Escape') setRenamingId(null);
                  }}
                  onBlur={() => void commitRename()}
                  className="w-full rounded border border-input bg-background px-1.5 py-0.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                  autoFocus
                />
              </div>
            ) : (
            <button
              key={lane.id}
              onClick={() => setParam({ lane: lane.id })}
              className={cn(
                'w-full text-left px-3 py-2.5 border-b border-border/50 transition-colors group',
                'flex items-start gap-2.5',
                activeLaneId === lane.id ? 'bg-muted' : 'hover:bg-muted/50',
              )}
            >
              {/* The colleague's face leads the row — you scan for WHO, not for
                  which engine ran (the shipped list once showed the raw engine
                  name on every row: the spec sheet, surviving where it was least
                  visible). */}
              <AgentFace
                name={laneLabel(lane)}
                avatarUrl={laneAgent(lane)?.avatar_url}
                size="md"
                className="mt-0.5"
              />
              <span className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-1">
                <span className="text-sm font-medium truncate flex items-center gap-1">
                  {lane.pinned && (
                    <Pin className="w-3 h-3 shrink-0 text-muted-foreground rotate-45" />
                  )}
                  {lane.name}
                </span>
                {/* Phase-A hygiene: pin / rename / archive on hover. */}
                <span className="flex items-center shrink-0">
                  <span
                    role="button"
                    tabIndex={-1}
                    onClick={(e) => {
                      e.stopPropagation();
                      void togglePin(lane);
                    }}
                    className={cn(
                      'p-1 rounded transition-colors hover:!text-foreground',
                      lane.pinned
                        ? 'text-muted-foreground'
                        : 'text-muted-foreground/0 group-hover:text-muted-foreground',
                    )}
                    aria-label={lane.pinned ? 'Unpin lane' : 'Pin lane'}
                    title={lane.pinned ? 'Unpin' : 'Pin'}
                  >
                    <Pin className={cn('w-3.5 h-3.5', lane.pinned && 'rotate-45')} />
                  </span>
                  <span
                    role="button"
                    tabIndex={-1}
                    onClick={(e) => {
                      e.stopPropagation();
                      setRenamingId(lane.id);
                      setRenameText(lane.name);
                    }}
                    className="p-1 rounded text-muted-foreground/0 group-hover:text-muted-foreground hover:!text-foreground transition-colors"
                    aria-label="Rename lane"
                    title="Rename"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </span>
                  <span
                    role="button"
                    tabIndex={-1}
                    onClick={(e) => {
                      e.stopPropagation();
                      void archiveLane(lane.id);
                    }}
                    className="p-1 rounded text-muted-foreground/0 group-hover:text-muted-foreground hover:!text-foreground transition-colors"
                    aria-label="Archive lane"
                    title="Archive lane"
                  >
                    <Archive className="w-3.5 h-3.5" />
                  </span>
                </span>
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                {/* The colleague, then the technical fact — "Lisa · Critic ·
                    GPT-5". The operator's rule: a nickname must still say what
                    it IS (at minimum the role + the model). Identity leads; the
                    spec rides quietly behind it. */}
                <span className="text-[11px] text-foreground/70 truncate">
                  {laneLabel(lane)}
                </span>
                <span className="text-[10px] text-muted-foreground/70 truncate">
                  {laneSubLabel(lane)}
                </span>
                {(lane.updated_at ?? lane.created_at) && (
                  <span className="text-[10px] text-muted-foreground/60">
                    {formatRelativeTime(lane.updated_at ?? lane.created_at!)}
                  </span>
                )}
              </div>
              </span>
            </button>
            ),
          )}
        </div>
      </div>

      {/* Conversation area. */}
      <div className="flex-1 min-w-0 flex flex-col min-h-0">
        {activeLane ? (
          <>
            <div className="flex items-center gap-2 px-3 py-2.5 border-b border-border shrink-0">
              <span className="text-sm font-medium">{activeLane.name}</span>
              <span className="px-1.5 py-px rounded-full bg-muted text-[10px] text-muted-foreground">
                {modelLabel(activeLane.model)}
              </span>
            </div>
            <LanePanel
              key={activeLane.id}
              laneId={activeLane.id}
              laneName={activeLane.name}
              modelLabel={modelLabel(activeLane.model)}
              suggestions={deriveSuggestions}
              // Phase-A hygiene: the first turn auto-names a default-named
              // lane server-side; reflect it in the list + header.
              onLaneRenamed={(name) => updateLaneLocal(activeLane.id, { name })}
              // Phase-A attachments: gate the image affordance on the lane
              // model's vision flag (the server guards regardless).
              visionCapable={
                data.models.find((m) => m.id === activeLane.model)?.vision ?? true
              }
            />
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center p-8">
            <div className="max-w-sm text-center space-y-2 text-sm text-muted-foreground">
              <MessageCircle className="w-6 h-6 mx-auto text-muted-foreground/50" />
              <p className="font-medium text-foreground/80">
                Your helper conversations
              </p>
              <p>
                Lanes are isolated conversations, each pinned to a model; the
                workspace is the shared memory. Pick a lane on the left or
                create one — its work lands in the shared files, attributed to
                you via the lane&apos;s model.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
