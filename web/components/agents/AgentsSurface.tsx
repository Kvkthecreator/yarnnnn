'use client';

/**
 * AgentsSurface — your colleagues (agents-surface-and-debt spec §2).
 *
 * ONE surface, two modes (the ADR-167 list/detail convention, which this
 * route has always used):
 *   - list   (no `?agent=`)      — who you've hired + who you can hire
 *   - detail (`?agent={slug}`)   — one colleague's card
 * `?agent=X` is WINDOW-INTERNAL state (ADR-358 D6), never a second route: a
 * separate /agents/{slug} page would be a second window, a second breadcrumb
 * owner, and — per DP29 "mirror once, compose few" — a second surface over one
 * substrate concern.
 *
 * DISCOVERY IS THE BASE SET. There is no separate "browse": the kernel
 * characters ARE the catalogue, and it is short — three addressed base agents
 * (Thinker · Researcher · Designer, the operations acquire/reason/produce) plus
 * postures over them (Critic = Reason adversarially postured). What grows is
 * CAPABILITY (skills, connections — spec §5), attaching to a base agent's class;
 * a new base row needs a new addressed OPERATION a member reaches for — never a
 * row per engine, never a new output shape. Seven presets would be the spec
 * sheet with makeup on.
 *
 * EVERY AGENT IS THE SAME KIND OF THING (ADR-460 D1, operator-corrected
 * 2026-07-16). Designer is listed, chatted with, and hired exactly like the
 * others — every agent can make artifacts; Designer is the one whose CHARACTER
 * is making. That Studio's lane pins Designer is a fact about the BOUND LANE,
 * not about the agent, and it is not this surface's business. A row rendered
 * here as a different KIND (un-hireable, "system", greyed) is the altitude
 * ladder growing back.
 *
 * ⚠️ EVERY PANE HERE IS IDENTITY OR CAPABILITY — NEVER AUTHORITY. This surface
 * must not become the persona-seat surface by accident (ADR-460 D3.a; the
 * ADR-382 Rung-2 horizon is untouched by this re-surface). The ChatGPT
 * business-agent editor's "Write action safety: Never ask" dropdown is the
 * anti-pattern; `test_agent_registry.py` gates this file against its
 * vocabulary.
 *
 * This replaced a roster over the `agents` DB table — which is EMPTY (ADR-414
 * retired the last row). It mirrors the workspace's Agent folders + the kernel
 * set instead.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Loader2, Pencil, Plus, Sparkles } from 'lucide-react';
import { AgentCard } from '@/components/chat-surface/AgentCard';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { AgentFace } from './AgentFace';
import { useSurfaceParam } from '@/lib/shell/useSurfacePreferences';
import { useWindowCrumb } from '@/contexts/BreadcrumbContext';

interface AgentInfo {
  slug: string;
  name: string;
  blurb: string;
  icon: string;
  avatar?: string;
  /** The image reference the FE trades for a signed URL (ADR-395). */
  avatar_url?: string;
  /** The capability's name + the engine's label — the technical fact, visible. */
  role?: string;
  engine?: string;
  based_on?: string;
  tone?: string;
  /** kernel = a built-in capability you can hire; false = one you named. */
  kernel?: boolean;
}

export function AgentsSurface() {
  const [agents, setAgents] = useState<AgentInfo[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [hiring, setHiring] = useState<{ slug?: string } | null>(null);
  const { get: getParam, set: setParam } = useSurfaceParam('agents');
  const activeSlug = getParam('agent');

  const load = useCallback(async () => {
    try {
      const res = await api.lanes.list();
      setAgents((res.agents ?? []) as AgentInfo[]);
    } catch {
      setAgents([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const mine = useMemo(() => (agents ?? []).filter((a) => a.kernel === false), [agents]);
  const kernel = useMemo(() => (agents ?? []).filter((a) => a.kernel !== false), [agents]);
  const active = useMemo(
    () => (agents ?? []).find((a) => a.slug === activeSlug) ?? null,
    [agents, activeSlug],
  );

  // Per-window locator: detail mode reports "Agents › {name}"; the crumb's
  // click returns to list mode (window-internal, never a route change).
  useWindowCrumb(
    'agents',
    active
      ? [{ label: active.name, kind: 'agent', onClick: () => setParam({ agent: null }) }]
      : [],
  );

  if (loading) {
    return (
      <div className="h-full grid place-items-center">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // ── DETAIL ────────────────────────────────────────────────────────────
  if (active) {
    const base = kernel.find((k) => k.slug === (active.based_on || active.slug));
    return (
      <div className="h-full overflow-y-auto p-6">
        <div className="max-w-lg mx-auto space-y-5">
          <button
            type="button"
            onClick={() => setParam({ agent: null })}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            ← All agents
          </button>

          <div className="flex items-center gap-3">
            <AgentFace name={active.name} avatarUrl={active.avatar_url} size="lg" />
            <div className="min-w-0">
              <h2 className="text-lg font-medium">{active.name}</h2>
              <p className="text-xs text-muted-foreground">{active.blurb}</p>
            </div>
            {active.kernel === false && (
              <button
                type="button"
                onClick={() => setHiring({ slug: active.slug })}
                className="ml-auto px-2 py-1 rounded border border-input text-xs text-muted-foreground hover:text-foreground hover:bg-muted inline-flex items-center gap-1"
              >
                <Pencil className="w-3 h-3" />
                Edit
              </button>
            )}
          </div>

          {hiring?.slug === active.slug ? (
            <AgentCard
              choices={kernel}
              existing={{
                slug: active.slug,
                name: active.name,
                based_on: active.based_on ?? '',
                tone: active.tone,
                avatar: active.avatar,
                avatar_url: active.avatar_url,
              }}
              onCancel={() => setHiring(null)}
              onDone={() => {
                setHiring(null);
                void load();
              }}
            />
          ) : (
            <>
              {/* IDENTITY — theirs. */}
              {active.tone && (
                <section className="space-y-1">
                  <h3 className="text-xs text-muted-foreground">How they sound</h3>
                  <p className="text-sm whitespace-pre-wrap">{active.tone}</p>
                </section>
              )}

              {/* CAPABILITY — who they are. Fixed: it is the job you hired for. */}
              <section className="space-y-1">
                <h3 className="text-xs text-muted-foreground">
                  {active.kernel === false ? 'Hired as' : 'What they do'}
                </h3>
                <p className="text-sm">
                  {active.kernel === false ? (base?.name ?? active.based_on) : active.name}
                  {base && active.kernel === false ? ` — ${base.blurb}` : ''}
                </p>
                {/* The technical fact — visible, never the headline. */}
                {active.engine && (
                  <p className="text-xs text-muted-foreground/70">Runs on {active.engine}</p>
                )}
              </section>

              {/* What they CAN'T do — prose, never a switch (spec §5). A true
                  sentence invites nothing; a disabled toggle invites a ticket. */}
              <section className="border-t border-border pt-4">
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {active.name} works on your files — reads, writes, edits.{' '}
                  {active.name} can&apos;t send email, spend money, or act while
                  you&apos;re away. They answer when you ask.
                </p>
              </section>
            </>
          )}
        </div>
      </div>
    );
  }

  // ── LIST ──────────────────────────────────────────────────────────────
  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-lg mx-auto space-y-6">
        {hiring && !hiring.slug && (
          <AgentCard
            choices={kernel}
            onCancel={() => setHiring(null)}
            onDone={() => {
              setHiring(null);
              void load();
            }}
          />
        )}

        {/* YOURS — the ones they named. First, because they made them. */}
        <section className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium">Your agents</h2>
            {!hiring && (
              <button
                type="button"
                onClick={() => setHiring({})}
                className="px-2 py-1 rounded border border-dashed border-input text-xs text-muted-foreground hover:text-foreground hover:bg-muted inline-flex items-center gap-1"
              >
                <Plus className="w-3 h-3" />
                Make one
              </button>
            )}
          </div>
          {mine.length === 0 ? (
            <p className="text-xs text-muted-foreground py-3">
              You haven&apos;t made any yet. Hire one of the agents below, give them a
              name and a manner, and they&apos;ll show up here.
            </p>
          ) : (
            <div className="space-y-1.5">
              {mine.map((a) => (
                <button
                  key={a.slug}
                  type="button"
                  onClick={() => setParam({ agent: a.slug })}
                  className="w-full flex items-center gap-3 p-2 rounded-md border border-border hover:bg-muted/50 text-left transition-colors"
                >
                  <AgentFace name={a.name} avatarUrl={a.avatar_url} />
                  <span className="min-w-0">
                    <span className="block text-sm">{a.name}</span>
                    <span className="block text-xs text-muted-foreground truncate">
                      {a.tone || a.blurb}
                    </span>
                  </span>
                </button>
              ))}
            </div>
          )}
        </section>

        {/* DISCOVERY — the base set IS the catalogue (spec §2/§3). */}
        <section className="space-y-2">
          <h2 className="text-sm font-medium">Who you can hire</h2>
          <p className="text-xs text-muted-foreground">
            Three colleagues, each good at a different thing. Hire one to give them
            a name and a manner of your own.
          </p>
          <div className="space-y-1.5">
            {kernel.map((a) => (
              <button
                key={a.slug}
                type="button"
                onClick={() => setParam({ agent: a.slug })}
                className="w-full flex items-center gap-3 p-2 rounded-md border border-border hover:bg-muted/50 text-left transition-colors"
              >
                <AgentFace name={a.name} avatarUrl={a.avatar_url} />
                <span className="min-w-0">
                  <span className="block text-sm">{a.name}</span>
                  <span className="block text-xs text-muted-foreground">{a.blurb}</span>
                  {a.engine && (
                    <span className="block text-[10px] text-muted-foreground/60">
                      {a.engine}
                    </span>
                  )}
                </span>
              </button>
            ))}
          </div>
        </section>

        <p className="text-[11px] text-muted-foreground/70 flex items-start gap-1.5 border-t border-border pt-4">
          <Sparkles className="w-3 h-3 mt-0.5 shrink-0" />
          Your agents work on your files, as you — every edit they make is
          attributed to you and kept in the file&apos;s history.
        </p>
      </div>
    </div>
  );
}
