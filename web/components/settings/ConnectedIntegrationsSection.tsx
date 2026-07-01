"use client";

import { useEffect, useState } from "react";
import {
  ArrowRight,
  AlertTriangle,
  Clock,
  Loader2,
} from "lucide-react";
import { api } from "@/lib/api/client";
import {
  CONNECTOR_REGISTRY,
  FRESHNESS_PROVIDERS,
  type ConnectorMeta,
} from "@/lib/connectors/registry";
import { ConnectorCard } from "./ConnectorCard";

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

// ADR-377: per-platform freshness summary (Context Connections pane). Derived
// from GET /api/integrations/{provider}/sync-status — coverage + recency, the
// real inbound signal that survives ADR-153 (platform_content sunset). NOT a
// per-event ingestion log; that data no longer exists.
interface PlatformFreshness {
  resourceCount: number;
  itemsSynced: number;
  lastSynced: string | null; // most-recent last_synced across resources
  staleCount: number;
  errorCount: number;
}

function relativeTime(iso: string | null): string {
  // ADR-392 D5 — honest freshness. A connected-but-unread platform is "not
  // reading yet" (available, awaiting selection + a capture recurrence), NOT
  // "never synced" (which implies a sync is pending that never fires).
  if (!iso) return "not reading yet";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "unknown";
  const mins = Math.floor((Date.now() - then) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
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
}

export function ConnectedIntegrationsSection({
  className,
  children,
  redirectTo,
  showFreshness = false,
  onViewFlow,
}: ConnectedIntegrationsSectionProps) {

  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [platformStatuses, setPlatformStatuses] = useState<Record<string, string>>({});
  const [freshness, setFreshness] = useState<Record<string, PlatformFreshness>>({});
  const [isLoadingIntegrations, setIsLoadingIntegrations] = useState(false);
  const [connectingProvider, setConnectingProvider] = useState<string | null>(null);
  const [disconnectingProvider, setDisconnectingProvider] = useState<string | null>(null);
  // ADR-392 D7 — which platform's selection subsurface (Phase 2 Select) is open.
  const [managingProvider, setManagingProvider] = useState<string | null>(null);
  // Commerce (API key auth, not OAuth)
  const [commerceApiKey, setCommerceApiKey] = useState("");
  const [commerceError, setCommerceError] = useState<string | null>(null);
  // Trading (API key + secret auth — ADR-187)
  const [tradingApiKey, setTradingApiKey] = useState("");
  const [tradingApiSecret, setTradingApiSecret] = useState("");
  const [tradingPaper, setTradingPaper] = useState(true);
  const [tradingError, setTradingError] = useState<string | null>(null);

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

      // ADR-377: fan out sync-status for connected freshness-capable
      // providers (Slack/Notion/GitHub). Each call is independently
      // guarded so one platform's failure doesn't blank the others.
      if (showFreshness) {
        const connected = FRESHNESS_PROVIDERS.filter((p) => statuses[p] === "active");
        const results = await Promise.all(
          connected.map(async (provider) => {
            try {
              const s = await api.integrations.getSyncStatus(provider);
              const resources = s.synced_resources || [];
              const lastSynced = resources
                .map((r) => r.last_synced)
                .filter((t): t is string => !!t)
                .sort()
                .pop() ?? null;
              const fresh: PlatformFreshness = {
                resourceCount: resources.length,
                itemsSynced: resources.reduce((sum, r) => sum + (r.items_synced || 0), 0),
                lastSynced,
                staleCount: s.stale_count || 0,
                errorCount: s.error_count || 0,
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

  // ADR-377: the per-platform freshness strip + "View flow →" link, rendered
  // inside each connected freshness-capable card when showFreshness is set.
  // Returns null in the legacy (Workspace-Settings) mode so behavior is
  // unchanged there.
  const renderFreshness = (provider: string) => {
    if (!showFreshness) return null;
    const f = freshness[provider];
    return (
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-border/60 pt-2 text-xs text-muted-foreground">
        {f ? (
          <>
            <span className="inline-flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {relativeTime(f.lastSynced)}
            </span>
            <span>
              {f.resourceCount} {f.resourceCount === 1 ? "source" : "sources"}
              {f.itemsSynced > 0 ? ` · ${f.itemsSynced} items` : ""}
            </span>
            {f.errorCount > 0 && (
              <span className="inline-flex items-center gap-1 text-destructive">
                <AlertTriangle className="h-3 w-3" />
                {f.errorCount} {f.errorCount === 1 ? "error" : "errors"}
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

  const handleConnectCommerce = async () => {
    if (!commerceApiKey.trim()) {
      setCommerceError("API key is required");
      return;
    }
    setConnectingProvider("commerce");
    setCommerceError(null);
    try {
      await api.integrations.connectCommerce(commerceApiKey.trim());
      setCommerceApiKey("");
      await loadIntegrations();
    } catch (err: any) {
      setCommerceError(err?.message || "Failed to connect. Check your API key.");
    } finally {
      setConnectingProvider(null);
    }
  };

  const handleConnectTrading = async () => {
    if (!tradingApiKey.trim() || !tradingApiSecret.trim()) {
      setTradingError("API key and secret are required");
      return;
    }
    setConnectingProvider("trading");
    setTradingError(null);
    try {
      await api.integrations.connectTrading(
        tradingApiKey.trim(),
        tradingApiSecret.trim(),
        tradingPaper,
      );
      setTradingApiKey("");
      setTradingApiSecret("");
      await loadIntegrations();
    } catch (err: any) {
      setTradingError(err?.message || "Failed to connect. Check your credentials.");
    } finally {
      setConnectingProvider(null);
    }
  };

  // ADR-392 FE Phase A — the api-key credential form, injected into the
  // universal ConnectorCard for api-key connectors (commerce/trading). Lifted
  // VERBATIM from the prior hardcoded commerce/trading card blocks. OAuth
  // connectors render their brand Connect button inside the card and never
  // reach this.
  const renderConnectForm = (meta: ConnectorMeta): React.ReactNode => {
    if (meta.provider === "commerce") {
      return (
        <div className="flex flex-col gap-2 w-full">
          <div className="flex items-center gap-2">
            <input
              type="password"
              value={commerceApiKey}
              onChange={(e) => {
                setCommerceApiKey(e.target.value);
                setCommerceError(null);
              }}
              placeholder="Paste your Lemon Squeezy API key"
              className="flex-1 px-3 py-2 text-sm border border-border rounded-md bg-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
              onKeyDown={(e) => {
                if (e.key === "Enter") handleConnectCommerce();
              }}
            />
            <button
              onClick={handleConnectCommerce}
              disabled={connectingProvider === "commerce" || !commerceApiKey.trim()}
              className="px-4 py-2 bg-[#7C3AED] text-white rounded-md text-sm font-medium hover:bg-[#6D28D9] flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
            >
              {connectingProvider === "commerce" ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                "Connect"
              )}
            </button>
          </div>
          {commerceError && (
            <p className="text-sm text-destructive">{commerceError}</p>
          )}
          <p className="text-xs text-muted-foreground">
            Find your API key at{" "}
            <a
              href="https://app.lemonsqueezy.com/settings/api"
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-foreground"
            >
              app.lemonsqueezy.com/settings/api
            </a>
          </p>
        </div>
      );
    }

    if (meta.provider === "trading") {
      return (
        <div className="flex flex-col gap-2 w-full">
          <div className="flex items-center gap-2">
            <input
              type="password"
              value={tradingApiKey}
              onChange={(e) => {
                setTradingApiKey(e.target.value);
                setTradingError(null);
              }}
              placeholder="Alpaca API key"
              className="flex-1 px-3 py-2 text-sm border border-border rounded-md bg-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
            <input
              type="password"
              value={tradingApiSecret}
              onChange={(e) => {
                setTradingApiSecret(e.target.value);
                setTradingError(null);
              }}
              placeholder="API secret"
              className="flex-1 px-3 py-2 text-sm border border-border rounded-md bg-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
              onKeyDown={(e) => {
                if (e.key === "Enter") handleConnectTrading();
              }}
            />
          </div>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer">
              <input
                type="checkbox"
                checked={tradingPaper}
                onChange={(e) => setTradingPaper(e.target.checked)}
                className="w-4 h-4 rounded border-border"
              />
              Paper trading (simulated)
            </label>
            <button
              onClick={handleConnectTrading}
              disabled={connectingProvider === "trading" || !tradingApiKey.trim() || !tradingApiSecret.trim()}
              className="px-4 py-2 bg-[#FFDC00] text-black rounded-md text-sm font-medium hover:bg-[#E6C600] flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shrink-0 ml-auto"
            >
              {connectingProvider === "trading" ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                "Connect"
              )}
            </button>
          </div>
          {tradingError && (
            <p className="text-sm text-destructive">{tradingError}</p>
          )}
          <p className="text-xs text-muted-foreground">
            Get your API keys at{" "}
            <a
              href="https://app.alpaca.markets/brokerage/account/api-keys"
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-foreground"
            >
              app.alpaca.markets
            </a>
          </p>
        </div>
      );
    }

    return null;
  };

  return (
    <section className={className}>
      {/* No self-header — the pane-level PaneHeader ("Connections") owns the
          title + description. This component renders only the connector cards.
          (Singular Implementation, 2026-07-01 — killed the Connectors double-
          header; its sole mount is the Channels Connections pane.) */}
      {isLoadingIntegrations ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="space-y-4">
          {CONNECTOR_REGISTRY.map((meta) => {
            const integration = integrations.find((i) => i.provider === meta.provider);
            return (
              <ConnectorCard
                key={meta.provider}
                meta={meta}
                connected={platformStatuses[meta.provider] === "active"}
                hasIntegration={!!integration}
                connecting={connectingProvider === meta.provider}
                disconnecting={disconnectingProvider === meta.provider}
                managing={managingProvider === meta.provider}
                onConnect={handleConnectIntegration}
                onDisconnect={handleDisconnectIntegration}
                onToggleManage={(p) => setManagingProvider((cur) => (cur === p ? null : p))}
                renderFreshness={renderFreshness}
                renderConnectForm={renderConnectForm}
              />
            );
          })}

          {children}

          <div className="p-4 bg-muted/30 rounded-lg text-sm text-muted-foreground">
            <p>
              {/* ADR-392 D5 — honest connect contract. Connecting makes a
                  platform AVAILABLE; it does not start reading on its own.
                  Selecting a channel/page/label + a capture recurrence is what
                  makes it READ. The prior copy ("a platform-awareness recurrence
                  is created automatically") promised an auto-sync that does not
                  exist (no sync path fires on connect — landscape discovery lists
                  names only). */}
              <strong>How it works:</strong> Connecting makes a platform available to your operation — it doesn&apos;t start reading on its own.
              Use &quot;Manage&quot; to pick which channels, pages, or repos are in scope; a capture then reads the selected ones into your workspace. Connectors here handle connect, reconnect, disconnect, and selection.
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
