"use client";

import { useEffect, useState } from "react";
import {
  ArrowRight,
  AlertTriangle,
  Check,
  ChevronRight,
  Clock,
  Loader2,
  Plus,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { formatRelativeTime } from "@/lib/formatting";
import {
  CONNECTOR_REGISTRY,
  OFFERED_CONNECTORS,
  FRESHNESS_PROVIDERS,
  connectorMeta,
  type ConnectorMeta,
} from "@/lib/connectors/registry";
import { ConnectorCard } from "./ConnectorCard";
import { ManageConnectionSubsurface } from "./ManageConnectionSubsurface";
import { RetentionDial } from "./RetentionDial";

interface Integration {
  id: string;
  provider: string;
  status: string;
  workspace_name: string | null;
  last_used_at: string | null;
  created_at: string;
}

interface SummaryPlatform {
  provider: string;
  status: string;
}

// ADR-401 D6: per-platform freshness derived from the CAPTURE SIGNAL
// (_capture_signal.yaml via GET /integrations/{provider}/capture-signal) —
// the same single source of truth as the Manage drill-in. The previous
// source (sync-status over `sync_registry`) was a DEAD signal for
// capture-lane connectors: the capture lane never writes sync_registry, so
// the strip showed "not reading yet" even while captures ran. One block per
// connector (the connector is the unit of perception; channels are its
// aperture) — never per-channel.
interface PlatformFreshness {
  status?: string;
  observedAt: string | null;
  items?: number;
  lastError?: string;
}

function relativeTime(iso: string | null): string {
  // ADR-392 D5 — honest freshness. A connected-but-unread platform is "not
  // reading yet" (available, awaiting selection + a capture recurrence), NOT
  // "never synced" (which implies a sync is pending that never fires). The
  // time math itself delegates to the shared formatter (@/lib/formatting).
  if (!iso) return "not reading yet";
  if (Number.isNaN(new Date(iso).getTime())) return "unknown";
  return formatRelativeTime(iso);
}

interface ConnectedIntegrationsSectionProps {
  className?: string;
  children?: React.ReactNode;
  /** Frontend path to return to after OAuth (e.g. "/system"). Defaults to /dashboard. */
  redirectTo?: string;
  /** ADR-377: when true, render a per-platform freshness strip (coverage +
   *  last-synced + errors) inside each connected card, and a "View flow →"
   *  link. The Context Connections pane sets this; Workspace-Settings (when
   *  it still mounted this) left it false — byte-identical legacy behavior. */
  showFreshness?: boolean;
  /** ADR-377: invoked by the per-platform "View flow →" link (the Context
   *  Connections pane wires it to switch to the Flow pane). Omitted → no
   *  flow link rendered. */
  onViewFlow?: (provider: string) => void;
  /** ADR-392 Phase B — the drill-in target: which connected connector's DEEP
   *  Manage subsurface is open (routed by `channels.connector=<provider>`).
   *  Null → the connections list. */
  activeConnector?: string | null;
  /** Open a connector's deep Manage subsurface (sets the `connector` param). */
  onManageConnection?: (provider: string) => void;
  /** Back from the Manage subsurface to the connections list (clears the param). */
  onBackFromManage?: () => void;
}

export function ConnectedIntegrationsSection({
  className,
  children,
  redirectTo,
  showFreshness = false,
  onViewFlow,
  activeConnector = null,
  onManageConnection,
  onBackFromManage,
}: ConnectedIntegrationsSectionProps) {

  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [platformStatuses, setPlatformStatuses] = useState<Record<string, string>>({});
  const [freshness, setFreshness] = useState<Record<string, PlatformFreshness>>({});
  // ADR-404 D2: the capture lane is dormant for the commons-first launch —
  // the freshness strip + retention dial render only when the lane runs.
  const [captureEnabled, setCaptureEnabled] = useState(false);
  const [isLoadingIntegrations, setIsLoadingIntegrations] = useState(false);
  const [connectingProvider, setConnectingProvider] = useState<string | null>(null);
  const [disconnectingProvider, setDisconnectingProvider] = useState<string | null>(null);
  // ADR-494 D2 — the commerce/trading api-key connect state is DELETED along
  // with their credential forms. Both connectors are retired (never offered),
  // so there is no second connect path to keep alive. All remaining connectors
  // are OAuth: `handleConnectIntegration` is the singular connect verb.

  const loadIntegrations = async () => {
    setIsLoadingIntegrations(true);
    try {
      const [listResult, summaryResult] = await Promise.all([
        api.integrations.list(),
        api.integrations.getSummary(),
      ]);

      setIntegrations(listResult.integrations || []);

      const statuses: Record<string, string> = {};
      (summaryResult.platforms || []).forEach((platform: SummaryPlatform) => {
        statuses[platform.provider] = platform.status;
      });

      setPlatformStatuses(statuses);

      // ADR-494 D4 — read the capture-lane flag DIRECTLY, once, from the
      // zero-DB endpoint that exists for exactly this (ADR-404 D2's amendment).
      // Before this the flag was inferred incidentally from a per-provider
      // capture-signal response, so it stayed false whenever no connected
      // freshness-capable provider happened to be fetched — the reason
      // `getCaptureLane()` shipped with no caller at all. One flag, one read.
      try {
        const lane = await api.integrations.getCaptureLane();
        setCaptureEnabled(!!lane.connector_capture_enabled);
      } catch {
        setCaptureEnabled(false); // fail-safe toward dormancy (ADR-404 D2)
      }

      // ADR-401 D6: fan out the capture signal for connected freshness-capable
      // providers (Slack/Notion/GitHub) — health is DERIVED (capture signal),
      // never the stored status column. Each call is independently guarded so
      // one platform's failure doesn't blank the others.
      if (showFreshness) {
        const connected = FRESHNESS_PROVIDERS.filter(
          (p): p is "slack" | "notion" | "github" => statuses[p] === "active",
        );
        const results = await Promise.all(
          connected.map(async (provider) => {
            try {
              const s = await api.integrations.getCaptureSignal(provider);
              // ADR-494 D4: the lane flag is read once above — NOT re-inferred
              // per provider (that was the second source of one fact).
              const block = s.observed?.[`capture-${provider}`];
              const fresh: PlatformFreshness = {
                status: block?.status,
                observedAt: block?.observed_at ?? null,
                items: block?.items,
                lastError: block?.last_error,
              };
              return [provider, fresh] as const;
            } catch {
              return null; // platform freshness unavailable — skip, don't blank
            }
          })
        );
        const map: Record<string, PlatformFreshness> = {};
        results.forEach((r) => {
          if (r) map[r[0]] = r[1];
        });
        setFreshness(map);
      }
    } catch (err) {
      console.error("Failed to fetch integrations:", err);
    } finally {
      setIsLoadingIntegrations(false);
    }
  };

  useEffect(() => {
    loadIntegrations();
  }, []);

  const handleConnectIntegration = async (provider: string) => {
    setConnectingProvider(provider);
    try {
      const result = await api.integrations.getAuthorizationUrl(provider, redirectTo);
      window.location.href = result.authorization_url;
    } catch (err) {
      console.error(`Failed to initiate ${provider} OAuth:`, err);
      setConnectingProvider(null);
    }
  };

  const handleDisconnectIntegration = async (provider: string) => {
    if (!confirm(`Disconnect ${provider}? You'll need to reconnect to export to ${provider} again.`)) {
      return;
    }

    setDisconnectingProvider(provider);
    try {
      await api.integrations.disconnect(provider);
      await loadIntegrations();
    } catch (err) {
      console.error(`Failed to disconnect ${provider}:`, err);
    } finally {
      setDisconnectingProvider(null);
    }
  };

  // ADR-401 D6: the per-platform freshness strip + "View flow →" link,
  // rendered inside each connected freshness-capable card when showFreshness
  // is set. Connector-grain, from the capture signal — one honest line per
  // connector. Returns null in the legacy (Workspace-Settings) mode so
  // behavior is unchanged there.
  const renderFreshness = (provider: string) => {
    if (!showFreshness || !captureEnabled) return null;
    const f = freshness[provider];
    return (
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-border/60 pt-2 text-xs text-muted-foreground">
        {f?.observedAt ? (
          <>
            <span className="inline-flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Last read {relativeTime(f.observedAt)}
            </span>
            {typeof f.items === "number" && (
              <span>
                {f.items} {f.items === 1 ? "source" : "sources"} read
              </span>
            )}
            {f.status && f.status !== "ok" && (
              <span className="inline-flex items-center gap-1 text-destructive">
                <AlertTriangle className="h-3 w-3" />
                {f.lastError || f.status}
              </span>
            )}
          </>
        ) : (
          // ADR-392 D5 — honest empty-state: available, not yet reading.
          <span>Not reading yet — select channels to pull content in</span>
        )}
        {onViewFlow && (
          <button
            type="button"
            onClick={() => onViewFlow(provider)}
            className="ml-auto inline-flex items-center gap-1 text-primary hover:underline"
          >
            View flow
            <ArrowRight className="h-3 w-3" />
          </button>
        )}
      </div>
    );
  };


  // ADR-392 Phase B — the drill-in: when a connector is the active target and it
  // is connected + selection-capable, render its DEEP Manage subsurface instead
  // of the list. Guard on connected+canSelect so a stale/invalid `connector`
  // param falls back to the list.
  const activeMeta = activeConnector ? connectorMeta(activeConnector) : undefined;
  const activeConnected =
    !!activeMeta && platformStatuses[activeMeta.provider] === "active";
  const activeCanSelect =
    !!activeMeta && activeMeta.authKind === "oauth" && !!activeMeta.supportsSelection;

  if (activeMeta && activeConnected && activeCanSelect) {
    return (
      <section className={className}>
        <ManageConnectionSubsurface
          meta={activeMeta}
          onBack={() => onBackFromManage?.()}
        />
      </section>
    );
  }

  // The connections list. Partition the registry into connected vs available —
  // connected connectors are drill-in rows (OAuth+selection) or full cards
  // (api-key, no selection); un-connected go into the "New connection" discovery
  // section below.
  const isConnected = (m: ConnectorMeta) => platformStatuses[m.provider] === "active";
  //
  // ADR-494 D2 — the two halves read DIFFERENT lists, deliberately:
  //   • connected ← CONNECTOR_REGISTRY (all of it), so a historical connection
  //     to a RETIRED connector still renders with its real name + brand and
  //     stays disconnectable. Retiring must never orphan an existing fact.
  //   • available ← OFFERED_CONNECTORS, so a retired connector is never offered
  //     as a new connection.
  const connected = CONNECTOR_REGISTRY.filter(isConnected);
  const available = OFFERED_CONNECTORS.filter((m) => !isConnected(m));

  return (
    <section className={className}>
      {/* No self-header — the pane-level PaneHeader ("Connections") owns the
          title + description. (Singular Implementation — its sole mount is the
          Channels Connections pane.) */}
      {isLoadingIntegrations ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Retention dial — workspace-level (ADR-392 D8). One window for all
              connectors' raw lanes. Rendered on the freshness-bearing pane only. */}
          {showFreshness && captureEnabled && <RetentionDial />}

          {/* Connected connectors. OAuth+selection ones are drill-in ROWS (click
              → the deep Manage subsurface); api-key ones (no selection) keep the
              full card (connect form is spent, only Disconnect matters). */}
          {connected.length > 0 && (
            <div className="space-y-2">
              {connected.map((meta) => {
                const canSelect = meta.authKind === "oauth" && !!meta.supportsSelection;
                if (canSelect) {
                  return (
                    <ConnectedConnectorRow
                      key={meta.provider}
                      meta={meta}
                      freshness={captureEnabled ? freshness[meta.provider] : undefined}
                      captureEnabled={captureEnabled}
                      onManage={() => onManageConnection?.(meta.provider)}
                      onViewFlow={onViewFlow ? () => onViewFlow(meta.provider) : undefined}
                    />
                  );
                }
                // api-key connected connectors — full card, no drill-in.
                const integration = integrations.find((i) => i.provider === meta.provider);
                return (
                  <ConnectorCard
                    key={meta.provider}
                    meta={meta}
                    connected
                    hasIntegration={!!integration}
                    connecting={connectingProvider === meta.provider}
                    disconnecting={disconnectingProvider === meta.provider}
                    onConnect={handleConnectIntegration}
                    onDisconnect={handleDisconnectIntegration}
                    renderFreshness={renderFreshness}
                  />
                );
              })}
            </div>
          )}

          {/* New connection — the discovery section. Un-connected registry
              connectors, each with its connect affordance (OAuth Connect button
              or the api-key credential form). Connecting makes a platform
              AVAILABLE; selecting + a capture makes it READ (ADR-392 D5). */}
          {available.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Plus className="h-4 w-4 text-muted-foreground" />
                <h3 className="text-sm font-medium">New connection</h3>
              </div>
              <p className="text-xs text-muted-foreground">
                Connect a platform to make it available to your operation. It
                doesn&apos;t start reading on its own — after connecting, open
                Manage to pick which channels, pages, or repos are in scope; a
                capture reads the selected ones into your workspace.
              </p>
              {available.map((meta) => {
                const integration = integrations.find((i) => i.provider === meta.provider);
                return (
                  <ConnectorCard
                    key={meta.provider}
                    meta={meta}
                    connected={false}
                    hasIntegration={!!integration}
                    connecting={connectingProvider === meta.provider}
                    disconnecting={disconnectingProvider === meta.provider}
                    onConnect={handleConnectIntegration}
                    onDisconnect={handleDisconnectIntegration}
                    renderFreshness={renderFreshness}
                  />
                );
              })}
            </div>
          )}

          {children}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// ConnectedConnectorRow — a compact drill-in row for a connected, selection-
// capable connector. Clicking the row (or "Manage") opens the deep Manage
// subsurface (ADR-392 Phase B). The footer carries the connector-grain
// capture-signal freshness (ADR-401 D6) + "View flow →".
// ---------------------------------------------------------------------------

function ConnectedConnectorRow({
  meta,
  freshness,
  captureEnabled,
  onManage,
  onViewFlow,
}: {
  meta: ConnectorMeta;
  freshness?: PlatformFreshness;
  /** ADR-494 D4 — whether the capture lane is RUNNING (ADR-404 D2). */
  captureEnabled: boolean;
  onManage: () => void;
  onViewFlow?: () => void;
}) {
  return (
    <div className="rounded-lg border border-border">
      <button
        type="button"
        onClick={onManage}
        className="flex w-full items-center gap-3 p-4 text-left transition-colors hover:bg-muted/50"
      >
        <div
          className={`w-10 h-10 ${meta.brand.chipClass} rounded-lg flex items-center justify-center shrink-0`}
        >
          {meta.brand.icon}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium">{meta.displayName}</span>
            <span className="inline-flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
              <Check className="h-3 w-3" />
              Connected
            </span>
          </div>
          <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
            {!captureEnabled ? (
              // ADR-494 D4 — the honest dormant state. This row previously
              // rendered `freshness` UNGATED, so with the capture lane dormant
              // (ADR-404 D2, default OFF) it kept displaying the last signal
              // written before dormancy — a frozen "Last read 3w ago · 2 sources
              // read" presented as current. A connector that cannot read must
              // not claim a reading. The ADR-392 D5 honest-freshness discipline
              // applied to the dormant case.
              <span>Connected — not reading (capture is paused)</span>
            ) : freshness?.observedAt ? (
              <>
                <span className="inline-flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Last read {relativeTime(freshness.observedAt)}
                </span>
                {typeof freshness.items === "number" && (
                  <span>
                    {freshness.items} {freshness.items === 1 ? "source" : "sources"} read
                  </span>
                )}
                {freshness.status && freshness.status !== "ok" && (
                  <span className="inline-flex items-center gap-1 text-destructive">
                    <AlertTriangle className="h-3 w-3" />
                    {freshness.lastError || freshness.status}
                  </span>
                )}
              </>
            ) : (
              <span>Not reading yet — open Manage to pick {meta.resourceNoun}</span>
            )}
          </div>
        </div>
        <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
      </button>
      {onViewFlow && (
        <div className="border-t border-border/60 px-4 py-2 text-right">
          <button
            type="button"
            onClick={onViewFlow}
            className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
          >
            View flow
            <ArrowRight className="h-3 w-3" />
          </button>
        </div>
      )}
    </div>
  );
}
