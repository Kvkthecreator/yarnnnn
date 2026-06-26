"use client";

/**
 * /context — Context: the operation's PERCEPTION HOME (ADR-377, 2026-06-26).
 *
 * Supersedes the ADR-370 "composition over mirrors" In/Out/Flow lens triple.
 * Context is now a Settings-like section-nav surface (Option A) — the
 * all-in-one home for the operation's boundary with the outside world. It is
 * the canonical home for platform connections (perception), not a second
 * mount of the Workspace-Settings → Perception panes (the dual-home ADR-377
 * resolves; Workspace-Settings keeps a thin "manage in Context →" pointer).
 *
 * A SettingsPaneShell split-nav, two groups:
 *
 *   PERCEPTION
 *     Connections (pane `connections`, DEFAULT) — what feeds the operation.
 *       The OWNED rich connector UI (ConnectedIntegrationsSection with
 *       showFreshness): each platform's status · coverage · last-synced ·
 *       errors, plus a "View flow →" link into the Flow pane. The perception
 *       home lands here — on what's feeding it.
 *     Sources (pane `sources`) — standing web/RSS watches (SourcesCard).
 *   BOUNDARY
 *     Emissions (pane `emissions`) — what the operation EMITTED, read-only
 *       (EmissionsView over GET /api/emissions; ADR-299/304 — sends stay
 *       system infrastructure, this is legibility).
 *     Flow (pane `flow`) — the complete NARRATIVE (FeedSurface, ADR-289
 *       typed-row grammar). The `/feed` route folds in here (redirect stub →
 *       /context?context.pane=flow).
 *
 * Honest data note (ADR-377 §2): "per-platform flow" is a deep-link from a
 * connection into the Flow narrative + the in-card coverage/freshness — NOT a
 * per-event inbound ledger (platform_content was sunset by ADR-153). The
 * "View flow →" link switches to the Flow pane; it does not filter by
 * platform (the narrative read carries no platform filter today).
 *
 * Mounts the shared SettingsPaneShell (Singular Implementation — same shell
 * behind System/Workspace Settings) in fullBleed mode so the Flow pane fills
 * the pane region.
 */

import { Link2, Rss, ArrowDownToLine, ArrowUpFromLine, ScrollText } from "lucide-react";
import { SettingsPaneShell, type PaneGroup } from "@/components/settings/SettingsPaneShell";
import { ConnectedIntegrationsSection } from "@/components/settings/ConnectedIntegrationsSection";
import { SourcesCard } from "@/components/workspace-concepts/SourcesCard";
import { EmissionsView } from "@/components/context/EmissionsView";
import { FeedSurface } from "@/components/feed-surface/FeedSurface";
import { useSurfaceParam } from "@/lib/shell/useSurfacePreferences";
import { isInbound } from "@/lib/feed-direction";

const PANE_GROUPS: PaneGroup[] = [
  {
    label: "Perception",
    panes: [
      { key: "connections", label: "Connections", icon: Link2 },
      { key: "sources", label: "Sources", icon: Rss },
    ],
  },
  {
    // The legacy "Feed" name operators know — the boundary's activity, as
    // three DIRECTION-FILTERED views over the one complete narrative (ADR-377
    // "track everything, filter at the surface"). In = inbound crossings
    // (writes that landed in substrate, direction inferred from `writtenTo`);
    // Out = outbound sends (the emissions ledger); Flow = the complete,
    // unfiltered narrative (the escape hatch).
    label: "Feed",
    panes: [
      { key: "in", label: "Context In", icon: ArrowDownToLine },
      { key: "out", label: "Context Out", icon: ArrowUpFromLine },
      { key: "flow", label: "Flow", icon: ScrollText },
    ],
  },
];

/** Shared pane header — title + subtitle. Flow owns its own header (FeedSurface). */
function PaneHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="border-b border-border/60 px-6 py-3 shrink-0">
      <h2 className="text-sm font-medium text-foreground">{title}</h2>
      <p className="text-xs text-muted-foreground">{subtitle}</p>
    </div>
  );
}

export default function ContextPage() {
  // Pane-switch within the Context window (the "View flow →" link).
  const surfaceParam = useSurfaceParam("context");

  const renderPane = (pane: string) => {
    switch (pane) {
      case "connections":
        // The OWNED rich connector UI — the perception home (ADR-377). Status
        // + coverage + freshness per platform; "View flow →" switches to the
        // Flow pane. redirectTo lands the OAuth round-trip back here.
        return (
          <div className="flex h-full flex-col">
            <PaneHeader
              title="Connections"
              subtitle="Connected platforms feeding the operation — status, coverage, and freshness."
            />
            <div className="flex-1 overflow-y-auto p-6">
              <ConnectedIntegrationsSection
                title="Connectors"
                description="Connect platforms to give the operation data. Platforms are infrastructure — connect once, the operation reads automatically."
                redirectTo="/context?context.pane=connections"
                showFreshness
                onViewFlow={() => surfaceParam.set({ pane: "flow" })}
              />
            </div>
          </div>
        );
      case "sources":
        // Standing web/RSS watches (ADR-336). The non-platform half of the
        // Perception field.
        return (
          <div className="flex h-full flex-col">
            <PaneHeader
              title="Sources"
              subtitle="Standing web and RSS watches the operation tracks."
            />
            <div className="flex-1 overflow-y-auto p-6">
              <SourcesCard variant="full" />
            </div>
          </div>
        );
      case "in":
        // Context In — the inbound crossings: the complete narrative FILTERED
        // to writes that landed in substrate (direction inferred from the
        // `writtenTo` envelope signal — MCP `remember`, connector sync,
        // upload). Reads (recall/trace) and internal cycles are excluded; see
        // the full picture in Flow. One FeedSurface, filtered (Singular Impl).
        return (
          <div className="flex h-full flex-col min-h-0">
            <FeedSurface
              messageFilter={(m) =>
                isInbound({ writtenTo: m.narrative?.writtenTo, tool: m.narrative?.tool })
              }
              emptyLabel="No inbound activity yet — when a connector syncs or a tool writes to the workspace, it lands here."
            />
          </div>
        );
      case "out":
        // Context Out — what the operation emitted: the operator-addressing
        // dispatch ledger (ADR-299/304). Read-only legibility over
        // GET /api/emissions. (Sends live in destination_delivery_log +
        // notifications, not the narrative — so Out reads the emissions
        // ledger directly rather than filtering the narrative.)
        return (
          <div className="flex h-full flex-col">
            <PaneHeader
              title="Context Out"
              subtitle="What the operation has emitted — sends to the outside world, to whom and when."
            />
            <div className="flex-1 overflow-y-auto p-6">
              <EmissionsView />
            </div>
          </div>
        );
      case "flow":
        // The complete narrative — FeedSurface intact (ADR-289 row grammar).
        // Fills the pane region; its own header carries filter + substrate
        // overlay + chat-summon.
        return (
          <div className="flex h-full flex-col min-h-0">
            <FeedSurface />
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <SettingsPaneShell
      windowSlug="context"
      paneGroups={PANE_GROUPS}
      defaultPane="connections"
      renderPane={renderPane}
      fullBleed
      navLabel="Context sections"
    />
  );
}
