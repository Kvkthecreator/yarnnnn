"use client";

/**
 * /channels — Channels: the operation's PERCEPTION + PRINCIPAL surface
 * (ADR-385, 2026-06-29). Renamed from `context` (the word "context" is
 * ambiguous — the filesystem [Files surface] and the operation/context/
 * substrate namespace are both "context").
 *
 * Supersedes ADR-377's four-pane `connections|sources|emissions|flow` rename:
 * In/Out/Flow are restored as distinct nav items (operator decision) because
 * Out is a genuinely DIFFERENT data source (the emissions ledger), not a
 * filter of the narrative. A SettingsPaneShell split-nav, two groups:
 *
 *   CHANNELS — what crosses the operation's edge
 *     Connections (pane `connections`) — platform data-feeds. The OWNED rich
 *       connector UI (ConnectedIntegrationsSection with showFreshness): each
 *       platform's status · coverage · last-synced · errors, plus a
 *       "View flow →" link into the Flow pane.
 *     Sources (pane `sources`) — standing web/RSS watches (SourcesCard,
 *       ADR-335/336).
 *     AI Connections (pane slug `external-agents`) — MCP / external-LLM
 *       principals. A FILTERED VIEW of WorkspaceMembersCard (role ∈ {foreign-llm,
 *       a2a, platform}) reading principal_grants (ADR-373). One substrate, two
 *       views — NOT a parallel data source (ADR-385 D3, DP29).
 *   ACTIVITY — the boundary crossing-ledger, scoped to the channels above.
 *     This is NOT the global workspace narrative (operator↔Freddie chat +
 *     reviewer cycles + agent runs) — that lives at Notifications → Activity.
 *     A Channels surface tracks only what crossed its edge:
 *     In (pane `in`, DEFAULT) — inbound crossings: the narrative FILTERED to
 *       writes that landed in substrate via a channel (connector sync, upload,
 *       MCP `remember` — direction inferred from the `writtenTo` envelope
 *       signal). One FeedSurface, filtered (Singular Impl).
 *     Out (pane `out`) — the emissions / dispatch ledger (EmissionsView over
 *       GET /api/emissions; ADR-299/304 — sends stay system infrastructure,
 *       this is read-only legibility).
 *
 * The `flow` pane was RETIRED (2026-07-02): it mounted the workspace-global
 * narrative — a fossil from when this surface WAS the Feed (ADR-259/370). On a
 * Channels surface that stream is dominated by internal cycles + operator chat,
 * none of which is boundary activity; it was pure redundancy with Notifications
 * → Activity (the narrative's real home). ACTIVITY is now In + Out only.
 *
 * Two orthogonal planes co-locate in CHANNELS without overlap (ADR-385 §2):
 * Connections = WHAT feeds the operation (platform_connections); External
 * Agents = WHO can write the commons (principal_grants).
 *
 * Honest data note (ADR-377 §2): "per-platform activity" is a deep-link from a
 * connection into the In crossing-ledger + the in-card coverage/freshness — NOT
 * a per-event inbound ledger (platform_content was sunset by ADR-153).
 *
 * `/context` and `/feed` redirect onto this surface — as of the ADR-385
 * follow-on (2026-06-30) via next.config.js `redirects()` (the legacy `context`
 * + `feed` surface slugs + their page stubs were deleted; full alias deletion).
 *
 * Mounts the shared SettingsPaneShell (Singular Implementation — same shell
 * behind System/Workspace Settings) in fullBleed mode so the Flow pane fills
 * the pane region.
 */

import { Link2, Rss, Cpu, ArrowDownToLine, ArrowUpFromLine } from "lucide-react";
import { SettingsPaneShell, PaneHeader, type PaneGroup } from "@/components/settings/SettingsPaneShell";
import { ConnectedIntegrationsSection } from "@/components/settings/ConnectedIntegrationsSection";
import { SourcesCard } from "@/components/workspace-concepts/SourcesCard";
import { WorkspaceMembersCard } from "@/components/workspace-concepts/WorkspaceMembersCard";
import { EmissionsView } from "@/components/context/EmissionsView";
import { FeedSurface } from "@/components/feed-surface/FeedSurface";
import { useSurfaceParam } from "@/lib/shell/useSurfacePreferences";
import { isInbound } from "@/lib/feed-direction";

// ADR-385 D3 — the external/automation principal classes shown on the
// AI Connections pane (slug `external-agents`): MCP LLMs, agent-to-agent
// callers, platform writers. Human owner/member and internal own-agent live on
// Workspace-Settings → Access (the full roster).
const EXTERNAL_PRINCIPAL_ROLES = ["foreign-llm", "a2a", "platform"];

const PANE_GROUPS: PaneGroup[] = [
  {
    // What crosses the operation's edge (was PERCEPTION).
    label: "Channels",
    panes: [
      // pane key `connectors` matches the kernel pane-grade slug so
      // foregroundSurface('connectors') → channels?channels.pane=connectors
      // resolves here (the generic pane_of mechanism delivers `pane: slug`).
      { key: "connectors", label: "Connections", icon: Link2 },
      { key: "sources", label: "Sources", icon: Rss },
      // Label "AI Connections" (display) — slug stays `external-agents` for
      // deep-link/URL stability (relabel-keep-slug, ADR-251 precedent).
      { key: "external-agents", label: "AI Connections", icon: Cpu },
    ],
  },
  {
    // The boundary's crossing-ledger, scoped to the channels above (was FEED).
    // In = inbound crossings (the narrative filtered to writes that landed via
    // a channel); Out = the emissions ledger (a different source). The global
    // workspace narrative lives at Notifications → Activity, not here.
    label: "Activity",
    panes: [
      { key: "in", label: "In", icon: ArrowDownToLine },
      { key: "out", label: "Out", icon: ArrowUpFromLine },
    ],
  },
];

// PaneHeader is the shared shell component (Singular Implementation, 2026-07-01).
// In owns its own header (FeedSurface), so it skips it.

export default function ChannelsPage() {
  // Pane-switch within the Channels window (the "View flow →" link).
  const surfaceParam = useSurfaceParam("channels");

  const renderPane = (pane: string) => {
    switch (pane) {
      case "connectors": {
        // The OWNED rich connector UI — the perception home (ADR-377/392).
        // ADR-392 Phase B: `channels.connector=<provider>` drills into a
        // connected connector's DEEP Manage subsurface (declared × observed
        // selection + freshness). Absent → the connections list (drill-in rows +
        // New-connection discovery + the workspace retention dial). The pane
        // header hides in the drill-in — the subsurface owns its back-crumb.
        const activeConnector = surfaceParam.get("connector");
        return (
          <div className="flex h-full flex-col">
            {!activeConnector && (
              <PaneHeader
                icon={Link2}
                title="Connections"
                subtitle="Connected platforms feeding the operation — status, coverage, and freshness."
              />
            )}
            <div className="flex-1 overflow-y-auto p-6">
              <ConnectedIntegrationsSection
                redirectTo="/channels?channels.pane=connectors"
                showFreshness
                onViewFlow={() => surfaceParam.set({ pane: "in" })}
                activeConnector={activeConnector}
                onManageConnection={(provider) => surfaceParam.set({ connector: provider })}
                onBackFromManage={() => surfaceParam.set({ connector: null })}
              />
            </div>
          </div>
        );
      }
      case "sources":
        // Standing web/RSS watches (ADR-336). The non-platform half of the
        // Perception field.
        return (
          <div className="flex h-full flex-col">
            <PaneHeader
              icon={Rss}
              title="Sources"
              subtitle="Standing web and RSS watches the operation tracks."
            />
            <div className="flex-1 overflow-y-auto p-6">
              <SourcesCard variant="full" />
            </div>
          </div>
        );
      case "external-agents":
        // ADR-385 D3 — MCP / external-LLM principals. A filtered view of the
        // workspace member roster (principal_grants) — NOT a new data source.
        // Reads GET /api/workspace/members; renders only the external classes.
        // Empty at N=1 until a foreign-llm grant is written (read-only;
        // granting/scoping is the ADR-373 provisioning follow-on).
        return (
          <div className="flex h-full flex-col">
            <PaneHeader
              icon={Cpu}
              title="AI Connections"
              subtitle="The AI that connects to this workspace — ChatGPT, Claude, and other LLMs reaching in over MCP. Each writes as itself, to a specific region."
            />
            <div className="flex-1 overflow-y-auto p-6">
              <WorkspaceMembersCard
                variant="full"
                roleFilter={EXTERNAL_PRINCIPAL_ROLES}
                emptyTitle="No AI connected yet"
                emptyHint="When an external LLM (ChatGPT, Claude, …) connects to this workspace over MCP, it appears here as a connection — attributing its writes as itself."
              />
            </div>
          </div>
        );
      case "in":
        // In (DEFAULT) — the inbound crossings: the complete narrative FILTERED
        // to writes that landed in substrate via a channel (direction inferred
        // from the `writtenTo` envelope signal — MCP `remember`, connector sync,
        // upload). Reads (recall/trace), internal cycles, and operator chat are
        // excluded; the full workspace narrative lives at Notifications →
        // Activity. One FeedSurface, filtered (Singular Impl).
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
        // Out — what the operation emitted: the operator-addressing dispatch
        // ledger (ADR-299/304). Read-only legibility over GET /api/emissions.
        // (Sends live in destination_delivery_log + notifications, not the
        // narrative — so Out reads the emissions ledger directly rather than
        // filtering the narrative.)
        return (
          <div className="flex h-full flex-col">
            <PaneHeader
              icon={ArrowUpFromLine}
              title="Out"
              subtitle="What the operation has emitted — sends to the outside world, to whom and when."
            />
            <div className="flex-1 overflow-y-auto p-6">
              <EmissionsView />
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <SettingsPaneShell
      windowSlug="channels"
      paneGroups={PANE_GROUPS}
      defaultPane="in"
      renderPane={renderPane}
      fullBleed
      navLabel="Channels sections"
    />
  );
}
