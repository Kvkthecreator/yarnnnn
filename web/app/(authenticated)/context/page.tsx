"use client";

/**
 * /context — Context: the operation's boundary composition (ADR-370, 2026-06-25).
 *
 * The THIRD composition window (after Home/Dwell and Notifications/operate-
 * the-work). One operator act: understand + manage the edge where the
 * workspace meets the outside world. Three lenses, a SettingsPaneShell split-
 * nav (the same shell behind Home/Notifications/Workspace Settings — Singular
 * Implementation):
 *
 *   In   (pane `in`)   — what context FEEDS the operation. The Perception
 *                        field (ADR-335): Connectors + Sources. Second mount
 *                        of the Workspace-Settings → Perception panes
 *                        (ConnectedIntegrationsSection + SourcesCard) — same
 *                        self-contained bodies, gathered here under the
 *                        boundary framing.
 *   Out  (pane `out`)  — what the operation EMITS, to whom, when. The
 *                        operator-addressing dispatch ledger (EmissionsView
 *                        over GET /api/emissions), read-only. Sends stay
 *                        system infrastructure (ADR-299/304) — this is
 *                        legibility, never a send affordance.
 *   Flow (pane `flow`) — the complete NARRATIVE (FeedSurface intact, ADR-289
 *                        typed-row grammar). The operator's "TOTAL": every
 *                        invocation, every wake, every crossing.
 *
 * Intended redundancy with Notifications → Activity (both mount FeedSurface):
 * the macOS tiered-access principle (ADR-367 D3) — same substrate, two
 * compositions, distinct primary jobs (operate the work vs. understand the
 * boundary). One body, two mounts (ADR-340 D8).
 *
 * It owns no substrate and no state — a composition over existing mirrors,
 * like Home (ADR-312) and Notifications (ADR-346). The `/feed` route folds in
 * here as the Flow lens; /feed survives only as an ADR-308 redirect stub →
 * /context?context.pane=flow. The prior /context → /files redirect stub is
 * deleted (ADR-370 D5): the context/ substrate ROOT was retired by ADR-320,
 * so the route slug is free + unrelated to any filesystem namespace.
 *
 * Mounts the shared SettingsPaneShell in fullBleed mode so the Flow pane
 * (FeedSurface) fills the pane region.
 */

import { ArrowDownToLine, ArrowUpFromLine, ScrollText } from "lucide-react";
import { SettingsPaneShell, type PaneGroup } from "@/components/settings/SettingsPaneShell";
import { ConnectedIntegrationsSection } from "@/components/settings/ConnectedIntegrationsSection";
import { SourcesCard } from "@/components/workspace-concepts/SourcesCard";
import { EmissionsView } from "@/components/context/EmissionsView";
import { FeedSurface } from "@/components/feed-surface/FeedSurface";

const PANE_GROUPS: PaneGroup[] = [
  {
    label: "Boundary",
    panes: [
      { key: "in", label: "In", icon: ArrowDownToLine },
      { key: "out", label: "Out", icon: ArrowUpFromLine },
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
  const renderPane = (pane: string) => {
    switch (pane) {
      case "in":
        // What context feeds the operation — the Perception field (ADR-335).
        // Connectors (platform transports) + Sources (standing web/RSS
        // watches). Second mount of the Workspace-Settings → Perception
        // panes; same self-contained bodies, gathered under the boundary.
        return (
          <div className="flex h-full flex-col">
            <PaneHeader
              title="In"
              subtitle="What feeds the operation — connected platforms and standing-watch sources."
            />
            <div className="flex-1 overflow-y-auto p-6 space-y-8">
              <ConnectedIntegrationsSection
                title="Connectors"
                description="Connect platforms to give your agents data. Platforms are infrastructure — connect once, agents read automatically."
                redirectTo="/context?context.pane=in"
              />
              <SourcesCard variant="full" />
            </div>
          </div>
        );
      case "out":
        // What the operation emits — the operator-addressing dispatch ledger
        // (ADR-299/304). Read-only legibility over GET /api/emissions.
        return (
          <div className="flex h-full flex-col">
            <PaneHeader
              title="Out"
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
      defaultPane="flow"
      renderPane={renderPane}
      fullBleed
      navLabel="Context lenses"
    />
  );
}
