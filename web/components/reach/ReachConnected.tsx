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
import { useTranslations } from 'next-intl';
import { ArrowRight, ChevronRight, FolderOpen, Plug, Plus } from 'lucide-react';
import { Working } from '@/components/shared/Working';
import { api, type StandingSummary } from '@/lib/api/client';
import { connectorMeta, FRESHNESS_PROVIDERS } from '@/lib/connectors/registry';
import { ConnectorAvatar } from '@/components/connectors/ConnectorAvatar';
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
  const t = useTranslations('reach');
  const [rows, setRows] = useState<Integration[] | null>(null);
  const [standing, setStanding] = useState<StandingSummary[]>([]);
  const [freshness, setFreshness] = useState<Record<string, Freshness>>({});
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [finderOpen, setFinderOpen] = useState(false);
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

  // `handleConnect` lived here and moved into the finder with the first-party
  // lane (2026-09-20) — one door, one implementation. Its failure branch was a
  // silent `console.error`, which left the member watching a button do nothing;
  // the finder's version reports the failure where the member is standing.

  const handleDisconnect = async (provider: string) => {
    const label = connectorMeta(provider)?.displayName ?? provider.replace(/^mcp:/, '');
    const ok = await confirmDialog({
      title: t('disconnectConfirm.title', { name: label }),
      body: t('disconnectConfirm.body', { name: label }),
      confirmLabel: t('disconnectConfirm.confirmLabel'),
      danger: true,
    });
    if (!ok) return;
    setDisconnecting(provider);
    try {
      await runAction(() => api.integrations.disconnect(provider), {
        pending: t('disconnectConfirm.pending', { name: label }),
        success: t('disconnectConfirm.success', { name: label }),
        error: t('disconnectConfirm.error', { name: label }),
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
    return <Working label={t('list.loading')} fill />;
  }

  if (rows.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border/60 px-6 py-10 text-center">
        <Plug className="mx-auto mb-3 h-6 w-6 text-muted-foreground/40" />
        <p className="text-sm font-medium text-foreground/80">{t('list.emptyTitle')}</p>
        <p className="mt-1 text-xs text-muted-foreground/70">{t('list.emptyBody')}</p>
        {error && <p className="mt-2 text-[11px] text-destructive">{error}</p>}
        <button
          type="button"
          onClick={() => setFinderOpen(true)}
          className="mt-4 inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground"
        >
          <Plus className="h-3.5 w-3.5" />
          {t('list.newConnection')}
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
            // Nothing is held in this branch by definition (rows.length is 0),
            // so every first-party connector is on offer. This is the branch
            // the 2026-09-20 click-pass found stranded: its copy named four
            // connectors and its one button could offer none of them.
            heldProviders={new Set()}
            redirectTo={REACH_CONNECTED_ROUTE}
          />
        )}
      </div>
    );
  }

  // What the member already holds — passed to the finder so its first-party
  // lane offers only what is NOT connected. The filtering itself lives there,
  // beside the rows it draws (this file used to do both).
  const heldActive = new Set(rows.filter((r) => r.status === 'active').map((r) => r.provider));

  return (
    <div className="space-y-4">
      {/* ADR-645 D3 — the new-connection act, on the boundary surface. Placed
          at the head of the pane: a create affordance belongs where a reader
          arrives, above the roster it adds to, not trailing it. */}
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => setFinderOpen(true)}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground"
        >
          <Plus className="h-3.5 w-3.5" />
          {t('list.newConnection')}
        </button>
      </div>
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
                {/* An attached MCP server used to render the SAME generic plug
                    as every other attached server, so a member who added Linear
                    could not pick it out of their own list. It now resolves its
                    own mark from the server address — the same resolution the
                    finder row used, so the row they clicked and the row they
                    landed on are visibly one connector. */}
                <ConnectorAvatar
                  size="md"
                  url={i.server_url}
                  title={name}
                  override={meta ? meta.brand : undefined}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                    {/* ADR-645 D3 — the name is the door into this connection's
                        own page (selection, aperture, disconnect). */}
                    {hasDrillIn(i) ? (
                      <button
                        type="button"
                        onClick={() => openConnector(i.provider)}
                        className="group inline-flex items-center gap-1 text-sm font-medium text-foreground hover:underline"
                        title={t('list.manage', { name })}
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
                        {t('list.attached')}
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
                        {disconnecting === i.provider ? t('list.disconnecting') : t('list.disconnect')}
                      </button>
                    )}
                  </div>
                  <dl className="mt-2 space-y-1 text-[11px]">
                    {i.does?.reads && <Fact label={t('facts.reads')} text={i.does.reads} />}
                    {i.does?.writes && <Fact label={t('facts.writes')} text={i.does.writes} />}
                    {/* ADR-644 — the same structure the agent is told: what an
                        agent holds through this connection, in one line. */}
                    {i.reach && (
                      <Fact
                        label={t('facts.agents')}
                        text={
                          i.reach.agent_writes.length > 0
                            ? t('facts.agentsCanPost')
                            : i.reach.reads.length > 0
                              ? t('facts.agentsReadOnly')
                              : t('facts.agentsNone')
                        }
                      />
                    )}
                    {attached && (
                      <Fact
                        label={t('facts.exposes')}
                        text={
                          i.category
                            ? t('facts.exposesToolsCategory', {
                                count: i.tools_exposed ?? 0,
                                category: i.category,
                              })
                            : t('facts.exposesTools', { count: i.tools_exposed ?? 0 })
                        }
                      />
                    )}
                    {/* ADR-635 D4 am.1 — the server moved under the member's
                        consent. A withdrawn tool they had ALLOWED is the
                        load-bearing half: it now refuses, and without this
                        line it refuses silently. Named here because this is
                        where they already look; the fix is one click away. */}
                    {attached && (i.drift?.withdrawn.length || i.drift?.appeared.length) ? (
                      <Fact
                        label={t('facts.changed')}
                        tone={i.drift.withdrawn.length > 0 ? 'warn' : 'muted'}
                        text={[
                          i.drift.withdrawn.length > 0
                            ? t('facts.changedWithdrawn', {
                                count: i.drift.withdrawn.length,
                                names: i.drift.withdrawn.join(', '),
                              })
                            : null,
                          i.drift.appeared.length > 0
                            ? t('facts.changedAppeared', { count: i.drift.appeared.length })
                            : null,
                        ]
                          .filter(Boolean)
                          .join(' · ')}
                      />
                    ) : null}
                    {/* A connector that never captures (WordPress) has no
                        "last read" — saying "not reading yet" there implies a
                        read that is coming. Shown only where a capture exists. */}
                    {fresh && !(i.does?.reads ?? '').startsWith('nothing') && (
                      <Fact
                        label={t('facts.lastRead')}
                        text={
                          fresh.observedAt
                            ? fresh.items
                              ? t('facts.lastReadAtItems', {
                                  when: formatRelativeTime(fresh.observedAt),
                                  count: fresh.items,
                                })
                              : formatRelativeTime(fresh.observedAt)
                            : t('facts.lastReadNever')
                        }
                        tone={fresh.lastError ? 'warn' : 'muted'}
                      />
                    )}
                    {readers.length > 0 && (
                      <div className="flex gap-2">
                        {/* The declarations are THIS WORKSPACE's (substrate);
                            the connection is the viewer's (account). Say so. */}
                        <dt className="w-16 shrink-0 text-muted-foreground/60" title={t('facts.readByHint')}>{t('facts.readBy')}</dt>
                        <dd className="flex flex-wrap gap-1">
                          {readers.map((d) => (
                            <button
                              key={d.topic}
                              type="button"
                              onClick={() =>
                                navigateToSurface('files', { path: d.target_path ?? d.declaration_path })
                              }
                              className="inline-flex items-center gap-1 rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground hover:text-foreground"
                              title={t('facts.readerOpenHint')}
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
      {/* The "Available" list lived here (ADR-645 D3) and is DELETED
          (2026-09-20). It was the only way to connect Slack/Notion/GitHub/
          WordPress, and it rendered AFTER the roster — so a member holding no
          connections never reached it. That member hit the empty state above,
          whose one button opens the finder, and the finder had no first-party
          lane: the copy named four connectors and offered none.

          The fix put the lane in the finder, which is the door BOTH branches
          already open. Keeping this list as well would be two doors to one act
          drifting apart — the finder is now the single door, so this goes
          rather than being mirrored. `connecting`/`handleConnect` go with it;
          the finder owns that state now. */}

      {/* ADR-645 D4 — the rule the whole surface embodies, said once. The act
          itself sits at the TOP of the pane (the create affordance a reader
          looks for before scanning the list), not below the roster. */}
      <p className="pt-1 text-[11px] leading-snug text-muted-foreground/70">
        {t('list.yoursGoWithYou')}
      </p>

      {/* ADR-645 D3 / ADR-496 D1 — the INBOUND half of the boundary: external
          AI assistants that reach IN over MCP. It sat on the account door
          because a connection is a member's (ADR-431 §2 `connected_by`); it
          belongs here because it is reach. READ-ONLY — governance stays
          singular in WorkspaceMembersCard (workspace-settings → members). */}
      <div className="border-t border-border/60 pt-6">
        <h3 className="mb-1 text-sm font-medium">{t('aiConnections.title')}</h3>
        <p className="mb-3 text-xs text-muted-foreground">{t('aiConnections.body')}</p>
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
              {t('aiConnections.manageAccess')}
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
          heldProviders={heldActive}
          redirectTo={REACH_CONNECTED_ROUTE}
        />
      )}
    </div>
  );
}
