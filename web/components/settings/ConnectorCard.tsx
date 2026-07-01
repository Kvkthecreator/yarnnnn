"use client";

/**
 * ConnectorCard — the universal, registry-driven connector card (ADR-392 FE
 * Phase A). One component renders any connector (Slack / Notion / GitHub over
 * OAuth; Lemon Squeezy / Alpaca over API key), driven by a `ConnectorMeta`
 * entry from `web/lib/connectors/registry.tsx`.
 *
 * This REPLACES the 5 hardcoded per-platform card IIFE blocks that lived in
 * `ConnectedIntegrationsSection.tsx` (Singular Implementation). The section now
 * maps `CONNECTOR_REGISTRY` → this card.
 *
 * Auth-kind branching (the one real per-connector difference):
 *  - oauth  → a brand-coloured "Connect" button that kicks off the OAuth flow;
 *             when connected, a "Manage {resourceNoun}" toggle mounts the
 *             ConnectorSelectionPanel + a "Reconnect".
 *  - apikey → the parent supplies the credential form via `renderConnectForm`;
 *             no Manage/Reconnect/freshness (API-key connectors have no per-
 *             resource sync registry — ADR-377).
 *
 * Freshness (ADR-377) is parent-owned (it reads sync-status) and injected via
 * `renderFreshness`, rendered only for connected OAuth connectors.
 */

import type { ReactNode } from "react";
import { Check, ExternalLink, Loader2 } from "lucide-react";
import { ConnectorSelectionPanel } from "./ConnectorSelectionPanel";
import type { ConnectorMeta } from "@/lib/connectors/registry";

interface ConnectorCardProps {
  meta: ConnectorMeta;
  /** platformStatuses[provider] === "active" */
  connected: boolean;
  /** an `integrations` row exists for this provider */
  hasIntegration: boolean;
  connecting: boolean;
  disconnecting: boolean;
  /** the Phase-2 Select subsurface is open for this provider */
  managing: boolean;
  onConnect: (provider: string) => void;
  onDisconnect: (provider: string) => void;
  onToggleManage: (provider: string) => void;
  /** ADR-377 freshness strip (parent-owned, OAuth-only). */
  renderFreshness?: (provider: string) => ReactNode;
  /** API-key credential form (parent-owned, apikey-only). */
  renderConnectForm?: (meta: ConnectorMeta) => ReactNode;
}

export function ConnectorCard({
  meta,
  connected,
  hasIntegration,
  connecting,
  disconnecting,
  managing,
  onConnect,
  onDisconnect,
  onToggleManage,
  renderFreshness,
  renderConnectForm,
}: ConnectorCardProps) {
  const isOauth = meta.authKind === "oauth";
  const canSelect = isOauth && !!meta.supportsSelection;

  return (
    <div className="p-4 border border-border rounded-lg">
      <div className="flex items-start gap-3">
        <div
          className={`w-10 h-10 ${meta.brand.chipClass} rounded-lg flex items-center justify-center shrink-0`}
        >
          {meta.brand.icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-4">
            <div>
              <div className="font-medium">{meta.displayName}</div>
              <div className="text-sm text-muted-foreground">{meta.tagline}</div>
            </div>
            {connected ? (
              <span className="text-sm text-green-600 dark:text-green-400 flex items-center gap-1 shrink-0">
                <Check className="w-4 h-4" />
                Connected
              </span>
            ) : null}
          </div>

          <div className="flex items-center gap-2 mt-3 flex-wrap">
            {hasIntegration ? (
              <>
                {canSelect && (
                  /* ADR-392 D7 — the Phase-2 Select subsurface toggle. */
                  <button
                    onClick={() => onToggleManage(meta.provider)}
                    className="px-3 py-1.5 text-sm text-foreground border border-border rounded-md hover:bg-muted transition-colors"
                  >
                    {managing ? "Done" : `Manage ${meta.resourceNoun}`}
                  </button>
                )}
                {isOauth && (
                  <button
                    onClick={() => onConnect(meta.provider)}
                    disabled={connecting}
                    className="px-3 py-1.5 text-sm text-muted-foreground border border-border rounded-md hover:bg-muted transition-colors"
                  >
                    {connecting ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      "Reconnect"
                    )}
                  </button>
                )}
                <button
                  onClick={() => onDisconnect(meta.provider)}
                  disabled={disconnecting}
                  className="px-3 py-1.5 text-sm text-muted-foreground hover:text-destructive border border-border rounded-md hover:border-destructive/30 transition-colors"
                >
                  {disconnecting ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    "Disconnect"
                  )}
                </button>
              </>
            ) : isOauth ? (
              <button
                onClick={() => onConnect(meta.provider)}
                disabled={connecting}
                className={`px-4 py-2 ${meta.brand.chipClass} text-white dark:text-black rounded-md text-sm font-medium flex items-center gap-2`}
              >
                {connecting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <ExternalLink className="w-4 h-4" />
                    Connect
                  </>
                )}
              </button>
            ) : (
              renderConnectForm?.(meta)
            )}
          </div>

          {connected && isOauth && renderFreshness?.(meta.provider)}
          {connected && canSelect && managing && (
            <ConnectorSelectionPanel
              provider={meta.provider as "slack" | "notion" | "github"}
              resourceNoun={meta.resourceNoun!}
            />
          )}
        </div>
      </div>
    </div>
  );
}
