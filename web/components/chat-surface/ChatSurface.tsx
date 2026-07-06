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
import { Archive, Loader2, MessageCircle, Plus } from 'lucide-react';
import { LanePanel } from './LanePanel';
import { api } from '@/lib/api/client';
import { formatRelativeTime } from '@/lib/formatting';
import { useSurfaceParam } from '@/lib/shell/useSurfacePreferences';
import { cn } from '@/lib/utils';

interface LaneInfo {
  id: string;
  name: string;
  model: string;
  updated_at?: string;
  created_at?: string;
}

interface LaneData {
  enabled: boolean;
  models: Array<{ id: string; label: string }>;
  lanes: LaneInfo[];
}

export function ChatSurface() {
  const [data, setData] = useState<LaneData | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [newModel, setNewModel] = useState('');
  // D4 — the model FILTER facet (null = all lanes, the default view).
  const [modelFilter, setModelFilter] = useState<string | null>(null);
  const { get: getParam, set: setParam } = useSurfaceParam('chat');
  const activeLaneId = getParam('lane');

  useEffect(() => {
    let cancelled = false;
    api.lanes
      .list()
      .then((res) => {
        if (cancelled) return;
        setData(res as LaneData);
        if (res.models.length > 0) setNewModel((m) => m || res.models[0].id);
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

  // Flat recents — updated_at desc (falls back to created_at). Work-first:
  // the sort key is activity, never the model (D4).
  const lanes = useMemo(() => {
    const all = [...(data?.lanes ?? [])].sort((a, b) => {
      const ta = new Date(a.updated_at ?? a.created_at ?? 0).getTime();
      const tb = new Date(b.updated_at ?? b.created_at ?? 0).getTime();
      return tb - ta;
    });
    return modelFilter ? all.filter((l) => l.model === modelFilter) : all;
  }, [data, modelFilter]);

  // The filter facet only offers models actually present in the list.
  const presentModels = useMemo(
    () => Array.from(new Set((data?.lanes ?? []).map((l) => l.model))),
    [data],
  );

  const activeLane = useMemo(
    () => (data?.lanes ?? []).find((l) => l.id === activeLaneId) ?? null,
    [data, activeLaneId],
  );

  const createLane = useCallback(async () => {
    const name = newName.trim();
    if (!name || !newModel) return;
    try {
      const lane = await api.lanes.create({ name, model: newModel });
      const info: LaneInfo = {
        id: lane.id,
        name: lane.name,
        model: lane.model,
        updated_at: new Date().toISOString(),
      };
      setData((d) => (d ? { ...d, lanes: [...d.lanes, info] } : d));
      setParam({ lane: info.id });
      setCreating(false);
      setNewName('');
    } catch {
      // Creation failure (limit, router off) — keep the form open.
    }
  }, [newName, newModel, setParam]);

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

  const createForm = creating && (
    <div className="flex items-center gap-1.5 p-2 border-b border-border bg-muted/30 shrink-0">
      <input
        value={newName}
        onChange={(e) => setNewName(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') void createLane();
          if (e.key === 'Escape') setCreating(false);
        }}
        placeholder="Lane name (e.g. Docs)"
        className="flex-1 min-w-0 rounded border border-input bg-background px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
        autoFocus
      />
      <select
        value={newModel}
        onChange={(e) => setNewModel(e.target.value)}
        className="rounded border border-input bg-background px-1.5 py-1 text-xs max-w-[130px]"
      >
        {data.models.map((m) => (
          <option key={m.id} value={m.id}>
            {m.label}
          </option>
        ))}
      </select>
      <button
        onClick={() => void createLane()}
        disabled={!newName.trim()}
        className="px-2 py-1 rounded bg-primary text-primary-foreground text-xs disabled:opacity-40"
      >
        Create
      </button>
    </div>
  );

  return (
    <div className="h-full flex min-h-0">
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
        {createForm}

        {/* Model filter facet — the by-engine view on demand, never the
            default grouping (D4). Renders only when ≥2 models are in play. */}
        {presentModels.length > 1 && (
          <div className="flex items-center gap-1 px-2 py-1.5 border-b border-border shrink-0 overflow-x-auto">
            <button
              onClick={() => setModelFilter(null)}
              className={cn(
                'px-2 py-0.5 rounded-full text-[11px] whitespace-nowrap transition-colors',
                modelFilter === null
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:text-foreground',
              )}
            >
              All
            </button>
            {presentModels.map((m) => (
              <button
                key={m}
                onClick={() => setModelFilter((cur) => (cur === m ? null : m))}
                className={cn(
                  'px-2 py-0.5 rounded-full text-[11px] whitespace-nowrap transition-colors',
                  modelFilter === m
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted text-muted-foreground hover:text-foreground',
                )}
              >
                {modelLabel(m)}
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
          {lanes.map((lane) => (
            <button
              key={lane.id}
              onClick={() => setParam({ lane: lane.id })}
              className={cn(
                'w-full text-left px-3 py-2.5 border-b border-border/50 transition-colors group',
                activeLaneId === lane.id ? 'bg-muted' : 'hover:bg-muted/50',
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium truncate">{lane.name}</span>
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
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                {/* D4 — the model is a chip on the row, never the namespace. */}
                <span className="px-1.5 py-px rounded-full bg-muted text-[10px] text-muted-foreground">
                  {modelLabel(lane.model)}
                </span>
                {(lane.updated_at ?? lane.created_at) && (
                  <span className="text-[10px] text-muted-foreground/60">
                    {formatRelativeTime(lane.updated_at ?? lane.created_at!)}
                  </span>
                )}
              </div>
            </button>
          ))}
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
