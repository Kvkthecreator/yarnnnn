'use client';

/**
 * ReachConnected — Reach's CONNECTED pane (ADR-642 D2).
 *
 * Every connection the member holds — platform OAuth rows and attached
 * connectors alike — with WHERE it points, what it READS and WRITES (the
 * `does` facts, derived server-side from the machinery that enacts them,
 * ADR-642 D5), how FRESH its capture is (the capture signal, the same source
 * the Connectors page reads), and WHICH standing declarations read through
 * it (derived from the standing roster's `sources[].connector`).
 *
 * ADR-645 D3 — THIS PANE ACTS. ADR-642's "lists and doors, never acts" clause
 * is amended: three of the four connection decisions (which sources this
 * workspace reads, the per-tool aperture, agent scope) are WORKSPACE decisions
 * that were wearing a Settings costume, and sending a member out of the
 * boundary surface to make a boundary decision institutionalised that. Settings
 * → Connectors is DELETED; this is the one door.
 *
 *   The credential is yours. The reach is this workspace's. (ADR-645 D4)
 *
 * The acts are the EXISTING machinery, moved not forked (ADR-645 D3.a) — a
 * mirrored design is a second write path. The drill-ins are pure-prop
 * components; this pane owns the connect/disconnect/find handlers and the
 * `reach.connector` param that selects a drill-in.
 *
 * ⭐ Acts may join this pane; a new reach SENTENCE may not. Everything telling
 * a member what a connection lets a turn do still renders `reach_status`
 * server-side (`does` / `reach` on the row) — a sentence written here would be
 * ADR-644's fifth face. Nothing here is stored (DP29). No row presents an
 * agent's record (ADR-640).
 */

import { useCallback, useEffect, useState } from 'react';
import { ArrowRight, ChevronRight, FolderOpen, Plug, Plus } from 'lucide-react';
import { api, type StandingSummary } from '@/lib/api/client';
import { connectorMeta, FRESHNESS_PROVIDERS, OFFERED_CONNECTORS } from '@/lib/connectors/registry';
import { formatRelativeTime } from '@/lib/formatting';
import { useSurfacePreferences, useSurfaceParam } from '@/lib/shell/useSurfacePreferences';
import { useFeedback } from '@/contexts/FeedbackContext';
import { cn } from '@/lib/utils';
// ADR-645 D3.a — the acts MOVE here; these are the same components the deleted
// Settings pane mounted, unchanged and unforked.
import { ManageConnectionSubsurface } from '@/components/settings/ManageConnectionSubsurface';
import { AttachedConnectorSubsurface } from '@/components/settings/AttachedConnectorSubsurface';
import { FindConnectorModal } from '@/components/settings/FindConnectorModal';
import { WorkspaceMembersCard } from '@/components/workspace-concepts/WorkspaceMembersCard';
import { SurfaceLink } from '@/components/shell/SurfaceLink';

type Integration = Awaited<ReturnType<typeof api.integrations.list>>['integrations'][number];

interface Freshness {
  status?: string;
  observedAt: string | null;
  items?: number;
  lastError?: string;
}

/** Where a provider returns the member: this pane. One spelling. */
const REACH_CONNECTED_ROUTE = '/reach?reach.pane=connected';

const STATUS_DOT: Record<string, string> = {
  active: 'bg-emerald-500',
  error: 'bg-destructive',
  expired: 'bg-amber-500',
};

function Fact({ label, text, tone = 'muted' }: { label: string; text: string; tone?: 'muted' | 'warn' }) {
  return (
    <div className="flex gap-2">
      <dt className="w-16 shrink-0 text-muted-foreground/60">{label}</dt>
      <dd className={cn('min-w-0 flex-1 leading-snug', tone === 'warn' ? 'text-amber-600' : 'text-muted-foreground')}>
        {text}
      </dd>
    </div>
  );
}

export function ReachConnected() {
  const { navigateToSurface } = useSurfacePreferences();
  const surfaceParam = useSurfaceParam('reach');
  const { confirm: confirmDialog, runAction } = useFeedback();
  const [rows, setRows] = useState<Integration[] | null>(null);
  const [standing, setStanding] = useState<StandingSummary[]>([]);
  const [freshness, setFreshness] = useState<Record<string, Freshness>>({});
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [finderOpen, setFinderOpen] = useState(false);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [disconnecting, setDisconnecting] = useState<string | null>(null);

  // The drill-in target rides `reach.connector` — window-namespaced (ADR-358
  // D6), so it is a shareable deep-link like every other pane param, and the
  // ADR-297 precedence now lets a pasted one win.
  const activeConnector = surfaceParam.get('connector');
  const openConnector = useCallback(
    (provider: string | null) => surfaceParam.set({ connector: provider }),
    [surfaceParam],
  );
  const reload = useCallback(() => setReloadKey((k) => k + 1), []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [ints, decls] = await Promise.all([
          api.integrations.list(),
          api.standing.list().catch(() => [] as StandingSummary[]),
        ]);
        if (cancelled) return;
        const list = ints.integrations ?? [];
        setRows(list);
        setStanding(decls);
        // The capture-signal fan-out (ADR-401 D6 — freshness is DERIVED from
        // the signal, never the stored status column). Each call guarded so
        // one platform's failure never blanks the others.
        const providers = FRESHNESS_PROVIDERS.filter(
          (p): p is 'slack' | 'notion' | 'github' =>
            list.some((i) => i.provider === p && i.status === 'active'),
        );
        const results = await Promise.all(
          providers.map(async (provider) => {
            try {
              const s = await api.integrations.getCaptureSignal(provider);
              const block = s.observed?.[`capture-${provider}`];
              const fresh: Freshness = {
                status: block?.status,
                observedAt: block?.observed_at ?? null,
                items: block?.items,
                lastError: block?.last_error,
              };
              return [provider, fresh] as const;
            } catch {
              return null;
            }
          }),
        );
        if (cancelled) return;
        const map: Record<string, Freshness> = {};
        results.forEach((r) => {
          if (r) map[r[0]] = r[1];
        });
        setFreshness(map);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
          setRows([]);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  // ── The acts (ADR-645 D3) ────────────────────────────────────────────────
  // Moved verbatim in behaviour from the deleted Settings pane: the confirm
  // gate and the reported failure are the 2026-08-22 streamline (a bare
  // `confirm(` and a silent console.error let the member watch nothing happen).

  const handleConnect = async (provider: string) => {
    setConnecting(provider);
    try {
      const back = REACH_CONNECTED_ROUTE;
      const { authorization_url } = await api.integrations.getAuthorizationUrl(provider, back);
      window.location.href = authorization_url;
    } catch (e) {
      console.error(`Failed to initiate ${provider} OAuth:`, e);
      setConnecting(null);
    }
  };

  const handleDisconnect = async (provider: string) => {
    const label = connectorMeta(provider)?.displayName ?? provider.replace(/^mcp:/, '');
    const ok = await confirmDialog({
      title: `Disconnect ${label}?`,
      body: `You'll need to reconnect to reach ${label} again.`,
      confirmLabel: 'Disconnect',
      danger: true,
    });
    if (!ok) return;
    setDisconnecting(provider);
    try {
      await runAction(() => api.integrations.disconnect(provider), {
        pending: `Disconnecting ${label}…`,
        success: `${label} disconnected`,
        error: `Couldn't disconnect ${label} — the connection is unchanged.`,
      });
      openConnector(null);
      reload();
    } catch {
      // runAction reported it.
    } finally {
      setDisconnecting(null);
    }
  };

  /** Does this row open a drill-in? Attached servers always do; a first-party
   *  one does when it is OAuth + selection-capable. Mirrors the routing below —
   *  the row affordance and the route must ask the SAME question. */
  const hasDrillIn = (r: Integration): boolean => {
    if (r.kind === 'attached') return true;
    const m = connectorMeta(r.provider);
    return !!m && m.authKind === 'oauth' && !!m.supportsSelection;
  };

  // ── The drill-ins ────────────────────────────────────────────────────────
  // Guarded on the LIVE row, so a stale `reach.connector` deep-link falls back
  // to the list rather than rendering a page for a connection that is gone.
  const activeRow = activeConnector
    ? (rows ?? []).find((r) => r.provider === activeConnector && r.status === 'active')
    : undefined;

  if (activeRow && activeRow.kind === 'attached') {
    return (
      <AttachedConnectorSubsurface
        provider={activeRow.provider}
        onBack={() => openConnector(null)}
        onDisconnect={() => handleDisconnect(activeRow.provider)}
        disconnecting={disconnecting === activeRow.provider}
      />
    );
  }

  const activeMeta = activeRow ? connectorMeta(activeRow.provider) : undefined;
  if (activeRow && activeMeta && activeMeta.authKind === 'oauth' && activeMeta.supportsSelection) {
    return (
      <ManageConnectionSubsurface
        meta={activeMeta}
        onBack={() => openConnector(null)}
        onDisconnect={() => handleDisconnect(activeMeta.provider)}
        disconnecting={disconnecting === activeMeta.provider}
      />
    );
  }

  if (rows === null) {
    return <div className="h-24 rounded-md bg-muted/30 animate-pulse" />;
  }

  if (rows.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border/60 px-6 py-10 text-center">
        <Plug className="mx-auto mb-3 h-6 w-6 text-muted-foreground/40" />
        <p className="text-sm font-medium text-foreground/80">Nothing is connected yet</p>
        <p className="mt-1 text-xs text-muted-foreground/70">
          Connect a platform once, and this page shows what it reads, what it writes, and who reads through it.
        </p>
        {error && <p className="mt-2 text-[11px] text-destructive">{error}</p>}
        <button
          type="button"
          onClick={() => setFinderOpen(true)}
          className="mt-4 inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground"
        >
          <Plus className="h-3.5 w-3.5" />
          Connect a platform
        </button>
        {finderOpen && (
          <FindConnectorModal
            open={finderOpen}
            onClose={() => setFinderOpen(false)}
            onAttached={() => {
              setFinderOpen(false);
              reload();
            }}
            attachedUrls={new Set()}
            redirectTo={REACH_CONNECTED_ROUTE}
          />
        )}
      </div>
    );
  }

  // Offered but not held. `rows` is the member's connections; a platform with
  // no active row is connectable.
  const heldActive = new Set(rows.filter((r) => r.status === 'active').map((r) => r.provider));
  const available = OFFERED_CONNECTORS.filter(
    (m) => m.authKind === 'oauth' && !heldActive.has(m.provider),
  );

  return (
    <div className="space-y-4">
      <ul className="space-y-3">
        {rows.map((i) => {
          const attached = i.kind === 'attached';
          const meta = attached ? undefined : connectorMeta(i.provider);
          const name = attached
            ? (i.title ?? i.provider.replace(/^mcp:/, ''))
            : (meta?.displayName ?? i.provider);
          const fresh = freshness[i.provider];
          const readers = standing.filter((d) => d.sources.some((s) => s.connector === i.provider));
          return (
            <li key={i.id} className="rounded-lg border border-border/60 p-4">
              <div className="flex items-start gap-3">
                <div
                  className={cn(
                    'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg',
                    meta ? meta.brand.chipClass : 'bg-muted',
                  )}
                >
                  {meta ? meta.brand.icon : <Plug className="h-4 w-4 text-muted-foreground" />}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                    {/* ADR-645 D3 — the name is the door into this connection's
                        own page (selection, aperture, disconnect). */}
                    {hasDrillIn(i) ? (
                      <button
                        type="button"
                        onClick={() => openConnector(i.provider)}
                        className="group inline-flex items-center gap-1 text-sm font-medium text-foreground hover:underline"
                        title={`Manage ${name}`}
                      >
                        {name}
                        <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/50 group-hover:text-foreground" />
                      </button>
                    ) : (
                      <span className="text-sm font-medium text-foreground">{name}</span>
                    )}
                    {i.target && <span className="truncate text-xs text-muted-foreground">{i.target}</span>}
                    <span
                      className={cn('h-1.5 w-1.5 rounded-full', STATUS_DOT[i.status] ?? 'bg-muted-foreground/40')}
                      title={i.status}
                      aria-label={i.status}
                    />
                    {attached && (
                      <span className="rounded-full border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground">
                        attached
                      </span>
                    )}
                    {/* A held connection with no drill-in (a RETIRED api-key
                        connector — commerce/trading) would otherwise have no
                        disconnect affordance at all: its row is not a drill-in
                        and it is never offered anew. Retiring must not orphan
                        an existing fact (ADR-494 D2). */}
                    {!hasDrillIn(i) && (
                      <button
                        type="button"
                        disabled={disconnecting === i.provider}
                        onClick={() => handleDisconnect(i.provider)}
                        className="ml-auto shrink-0 text-[11px] text-muted-foreground hover:text-destructive disabled:opacity-50"
                      >
                        {disconnecting === i.provider ? 'Disconnecting…' : 'Disconnect'}
                      </button>
                    )}
                  </div>
                  <dl className="mt-2 space-y-1 text-[11px]">
                    {i.does?.reads && <Fact label="Reads" text={i.does.reads} />}
                    {i.does?.writes && <Fact label="Writes" text={i.does.writes} />}
                    {/* ADR-644 — the same structure the agent is told: what an
                        agent holds through this connection, in one line. */}
                    {i.reach && (
                      <Fact
                        label="Agents"
                        text={
                          i.reach.agent_writes.length > 0
                            ? `can post here — by proposal, from your queue`
                            : i.reach.reads.length > 0
                              ? `read only — ${i.reach.reads.length} read tool${i.reach.reads.length === 1 ? '' : 's'}; cannot send`
                              : 'no reach — this connection carries only your own clicks'
                        }
                      />
                    )}
                    {attached && (
                      <Fact
                        label="Exposes"
                        text={`${i.tools_exposed ?? 0} tool${i.tools_exposed === 1 ? '' : 's'} to your turns${i.category ? ` · ${i.category}` : ''}`}
                      />
                    )}
                    {/* A connector that never captures (WordPress) has no
                        "last read" — saying "not reading yet" there implies a
                        read that is coming. Shown only where a capture exists. */}
                    {fresh && !(i.does?.reads ?? '').startsWith('nothing') && (
                      <Fact
                        label="Last read"
                        text={
                          fresh.observedAt
                            ? `${formatRelativeTime(fresh.observedAt)}${fresh.items ? ` · ${fresh.items} items` : ''}`
                            : 'not reading yet'
                        }
                        tone={fresh.lastError ? 'warn' : 'muted'}
                      />
                    )}
                    {readers.length > 0 && (
                      <div className="flex gap-2">
                        {/* The declarations are THIS WORKSPACE's (substrate);
                            the connection is the viewer's (account). Say so. */}
                        <dt className="w-16 shrink-0 text-muted-foreground/60" title="Standing declarations in this workspace that read through your connection">Read by</dt>
                        <dd className="flex flex-wrap gap-1">
                          {readers.map((d) => (
                            <button
                              key={d.topic}
                              type="button"
                              onClick={() =>
                                navigateToSurface('files', { path: d.target_path ?? d.declaration_path })
                              }
                              className="inline-flex items-center gap-1 rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground hover:text-foreground"
                              title="A standing declaration reads this connection — open the file it keeps"
                            >
                              <FolderOpen className="h-3 w-3" />
                              {d.topic}
                            </button>
                          ))}
                        </dd>
                      </div>
                    )}
                  </dl>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
      {/* ADR-645 D3 — first-party platforms not yet connected. The finder below
          covers ATTACHED (MCP) servers only, so without this section the move
          would have dropped the ability to connect Slack/Notion/GitHub at all.
          Offered ← OFFERED_CONNECTORS (live only): a retired connector still
          renders above if held, but is never offered anew (ADR-494 D2). */}
      {available.length > 0 && (
        <div className="space-y-2 pt-2">
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
            Available
          </h3>
          <ul className="space-y-2">
            {available.map((meta) => (
              <li
                key={meta.provider}
                className="flex items-center gap-3 rounded-lg border border-border/60 px-4 py-3"
              >
                <div
                  className={cn(
                    'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg',
                    meta.brand.chipClass,
                  )}
                >
                  {meta.brand.icon}
                </div>
                <span className="min-w-0 flex-1 truncate text-sm text-foreground">
                  {meta.displayName}
                </span>
                <button
                  type="button"
                  disabled={connecting === meta.provider}
                  onClick={() => handleConnect(meta.provider)}
                  className="shrink-0 rounded-md border border-border px-3 py-1 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground disabled:opacity-50"
                >
                  {connecting === meta.provider ? 'Connecting…' : 'Connect'}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ADR-645 D3 — the new-connection act, on the boundary surface. */}
      <div className="flex items-center justify-between gap-3 pt-1">
        <p className="text-[11px] leading-snug text-muted-foreground/70">
          {/* ADR-645 D4 — the rule the whole surface embodies, said once. */}
          Each connection is held under your account and travels with you. What this workspace
          reads through it, and what its tools may do, is set on the connection&rsquo;s own page.
        </p>
        <button
          type="button"
          onClick={() => setFinderOpen(true)}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground"
        >
          <Plus className="h-3.5 w-3.5" />
          New connection
        </button>
      </div>

      {/* ADR-645 D3 / ADR-496 D1 — the INBOUND half of the boundary: external
          AI assistants that reach IN over MCP. It sat on the account door
          because a connection is a member's (ADR-431 §2 `connected_by`); it
          belongs here because it is reach. READ-ONLY — governance stays
          singular in WorkspaceMembersCard (workspace-settings → members). */}
      <div className="border-t border-border/60 pt-6">
        <h3 className="mb-1 text-sm font-medium">Your AI connections</h3>
        <p className="mb-3 text-xs text-muted-foreground">
          External AI assistants you&apos;ve connected over MCP. Each reaches in as itself and
          writes under your authorization, so a connection goes away when you do — and each one
          reaches ONE workspace, so connecting here grants nothing in another.
        </p>
        <WorkspaceMembersCard
          variant="compact"
          scope="mine"
          readOnly
          footer={
            <SurfaceLink
              to="workspace-settings"
              params={{ pane: 'members' }}
              className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
            >
              Manage access for everyone in the workspace
              <ArrowRight className="h-3 w-3" />
            </SurfaceLink>
          }
        />
      </div>

      {finderOpen && (
        <FindConnectorModal
          open={finderOpen}
          onClose={() => setFinderOpen(false)}
          onAttached={() => {
            setFinderOpen(false);
            reload();
          }}
          attachedUrls={new Set(
            rows.filter((r) => r.kind === 'attached').map((r) => r.server_url ?? ''),
          )}
          redirectTo={REACH_CONNECTED_ROUTE}
        />
      )}
    </div>
  );
}
