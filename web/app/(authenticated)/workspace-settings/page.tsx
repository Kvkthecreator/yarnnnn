"use client";

/**
 * /workspace-settings — the ONE Settings door (ADR-347, 2026-06-19;
 * created by ADR-341, 2026-06-18).
 *
 * ADR-347 reversed ADR-341's two-door split: this is now THE Settings door
 * — the operation's settings. It configures THIS operation (the ADR-320
 * constitution/ + governance/ + operation/ + persona/ roots). The account
 * (Billing/Usage/Account) moved OUT to the UserMenu (the human/principal's
 * concern, ADR-347 D2). Mounts the shared SettingsPaneShell (Singular
 * Implementation, ADR-341 D5).
 *
 * Sidebar groups:
 *   - Constitution: Mandate · Identity · Principles — read/manage panes
 *     reusing the existing *Card full variants (read-mostly, "Edit via
 *     chat"; ADR-244 read-mostly + ADR-206 D6). Their FIRST-CLASS door
 *     stays the Home constitution band (ADR-312 D5 preserved).
 *   - Contract (ADR-347/ADR-348): Budget (Rhythm) · Autonomy (Witness) ·
 *     Expected Output — the operating contract. Operator-authored
 *     governance-region → inline editors (ADR-347 §3). Moved in from the
 *     dissolved System Settings door.
 *   - Operation: Program — the program lifecycle (ADR-244).
 *   - Access (ADR-373 D2): Workspace Members — who can write the workspace.
 *
 * ADR-385 D4 (2026-06-29): the Perception group (Connectors · Sources) is
 * removed — perception is wholly owned by the Channels surface now; the
 * connectors/sources slugs are pane_of: channels.
 *
 * ADR-412 D5 (2026-07-06): the SYSTEM AGENT group lands — Freddie's panes
 * re-home HERE from the /agents roster (the Agents surface is Altitude 3;
 * the system agent's inspection surface belongs on the system layer).
 *
 * ADR-418 (2026-07-08): the System Agent group is PURIFIED to what the
 * steward actually owns post ADR-414 D2 — its two dials (Autonomy = witness,
 * Budget = allocation) + read-only legibility (Capabilities · Activity).
 *   - Identity + Principles rejoin the Constitution group (they are
 *     constitution mirrors doored from the Home band, NOT the steward's
 *     persona — which is a kernel constant now). Rendered in the switch below.
 *   - Expected Output went DORMANT (a hired-agent contract, no band door;
 *     returns with the per-agent FE — ADR-382 / ADR-414 §9b).
 * The System Agent group's remaining panes still render via SystemAgentPanes
 * (Singular Implementation).
 */

import { useEffect, useState } from "react";
import { UserCircle, Package, AlertCircle, Rocket, Loader2, Users, Link2, Rss, CreditCard, BarChart3 } from "lucide-react";
import { api, APIError } from "@/lib/api/client";
import { useSurfacePreferences, useSurfaceParam } from "@/lib/shell/useSurfacePreferences";
import { SettingsPaneShell, PaneHeader, type PaneGroup } from "@/components/settings/SettingsPaneShell";
// ADR-416 follow-on — Billing + Usage re-home HERE (the workspace is the
// billing unit; both read the acting workspace's money). Self-contained bodies.
import { BillingPaneBody } from "@/components/subscription/BillingPaneBody";
import { UsagePaneBody } from "@/components/subscription/UsagePaneBody";
// ADR-421 — the Constitution-pane card imports were removed with the group (a
// workspace has no constitution of its own; the mandate/persona/principles cards
// render on the agent detail via AgentConstitutionBlock, ADR-419).
import { GrantGate } from "@/components/workspace-concepts/GrantGate";
import { WorkspaceMembersCard } from "@/components/workspace-concepts/WorkspaceMembersCard";
import { WorkspaceFileView } from "@/components/shared/WorkspaceFileView";
import { ProgramLifecycleDrawer } from "@/components/library/ProgramLifecycleDrawer";
// ADR-415 — Perception (Connectors · Sources) re-homed here from the dissolved
// Channels surface; a management pane, always-present (managing a connector ≠
// running its capture lane, so no CONNECTOR_CAPTURE_ENABLED gating on the UI).
import { ConnectedIntegrationsSection } from "@/components/settings/ConnectedIntegrationsSection";
import { SourcesCard } from "@/components/workspace-concepts/SourcesCard";
// ADR-412 D5 — the System Agent group (Freddie's panes, re-homed from the
// /agents roster; reverses ADR-387 §6.4).
import {
  SYSTEM_AGENT_PANE_GROUP,
  SYSTEM_AGENT_PANE_KEYS,
  renderSystemAgentPane,
} from "@/components/agents/SystemAgentPanes";

// ADR-341/347: pane keys match the kernel registry slugs for pane-grade
// surfaces, so foregroundSurface(slug) → workspace-settings + ?pane=slug
// resolves here. ADR-415: connectors/sources re-homed here (Channels dissolved).
// ADR-418 (2026-07-08): the System Agent group carries only the steward's own
// surface (autonomy/budget dials + capabilities/activity reads); identity/
// principles moved to the Constitution group (constitution mirrors, doored from
// the Home band); expected-output went dormant. capabilities/activity stay
// local pane keys (no registry row).
const PANE_GROUPS: PaneGroup[] = [
  // ADR-421 (2026-07-08): the Constitution group is REMOVED. A workspace has no
  // constitution of its own — mandate/identity/principles are per-agent concepts
  // (ADR-414 D6): a hired agent's declared intent + persona + judgment framework,
  // read from agents/{slug}/ and surfaced on the agent detail
  // (AgentConstitutionBlock, ADR-419). The steward's versions are kernel
  // constants (ADR-414 D2). Neither is a workspace-level pane. (ADR-418 moved
  // these into a Constitution group; ADR-419 made them home-aware; ADR-421
  // removes the workspace surface entirely — the honest endpoint.) The Home
  // HEADER still reads MANDATE.md content until the ADR-414 §9b Home recompose.
  SYSTEM_AGENT_PANE_GROUP,
  {
    // ADR-387 D3 — Brand stays here (interim). It is operation/-rooted output
    // styling consumed by writing-agents, NOT Freddie's reasoning-character —
    // so it did not move with Identity. Its permanent home is deferred to the
    // D4 follow-on ADR (agent output-styling vs operator brand vs per-persona).
    label: "Operation",
    panes: [
      { key: "brand", label: "Brand", icon: UserCircle },
      { key: "program", label: "Program", icon: Package },
    ],
  },
  // ADR-415 (2026-07-08) — the Perception group RETURNS here (reverses
  // ADR-385 D4). Connectors + Sources are the operation's data-feed
  // management: what platforms feed it, what web/RSS it watches. They live in
  // the management plane unconditionally — the ADR-404 capture-lane flag
  // governs runtime INGESTION, not whether the management UI is visible.
  {
    label: "Perception",
    panes: [
      { key: "connectors", label: "Connectors", icon: Link2 },
      { key: "sources", label: "Sources", icon: Rss },
    ],
  },
  // ADR-387 D1 — the Constitution (Identity/Principles) + Contract
  // (Budget/Autonomy/Expected Output) groups dissolved (moved to Freddie).
  {
    // ADR-373 D2 — the multi-principal access view. Who (humans, agents,
    // external LLMs over MCP, platforms) can write to this workspace, and
    // what region each holds. Read-only legibility; provisioning is a
    // separate ADR.
    label: "Access",
    panes: [{ key: "members", label: "Workspace Members", icon: Users }],
  },
  {
    // ADR-416 follow-on (2026-07-08): Billing + Usage move HERE from the account
    // door. The workspace is the billing unit (ADR-416) — balance + tier live on
    // `workspaces`, checkout targets the acting workspace (authorized by billing
    // grant), and Usage sums `execution_events` by workspace_id. So the
    // workspace's money belongs in the workspace-content door, not the human's
    // account door. Supersedes the ADR-347 account-door placement (which
    // predated the ADR-416 "workspace is the billing unit" ratification).
    label: "Billing",
    panes: [
      { key: "billing", label: "Billing", icon: CreditCard },
      { key: "usage", label: "Usage", icon: BarChart3 },
    ],
  },
];

export default function WorkspaceSettingsPage() {
  const { navigateToSurface } = useSurfacePreferences();
  // ADR-415 — the connector drill-in param (was channels.connector).
  const surfaceParam = useSurfaceParam("workspace-settings");

  const renderPane = (pane: string) => {
    // ADR-412 D5 — the System Agent panes render via the shared module.
    if (SYSTEM_AGENT_PANE_KEYS.includes(pane)) {
      return <section className="mb-8">{renderSystemAgentPane(pane)}</section>;
    }
    switch (pane) {
      // ADR-421 — the Mandate/Identity/Principles cases are REMOVED. A workspace
      // has no constitution of its own (ADR-414 D6): these are a hired agent's
      // concerns, surfaced on the agent detail (AgentConstitutionBlock, ADR-419).
      // The registry slugs are dormant; nothing routes here.
      // ADR-387 D3 — Brand stays here (interim). Rendered via the universal
      // WorkspaceFileView reading operation/BRAND.md directly (Identity moved
      // to Freddie, so the old merged "Identity & Brand" card no longer fits).
      case "brand":
        return (
          <section className="mb-8">
            <GrantGate region="operation/">
              <WorkspaceFileView
                title="Brand voice"
                path="/workspace/operation/BRAND.md"
                tagline="How produced output should sound — the brand voice writing-agents apply. Operator-authored. (Its permanent home is a follow-on ADR — ADR-387 D3.)"
                editPrompt="Help me define my brand voice — the tone, style, and conventions all produced content should follow."
                onEdit={(prompt) => navigateToSurface("chat", { prompt })}
                emptyBody={
                  <p className="text-center text-xs">
                    No brand voice declared yet. Author it to shape how produced
                    content sounds.
                  </p>
                }
              />
            </GrantGate>
          </section>
        );
      case "program":
        // ADR-412 D3 — activation/deactivation amends the constitution (the
        // bundle fork writes MANDATE/persona/governance seeds); same gate as
        // the Home activation CTA.
        return (
          <section className="mb-8">
            <GrantGate region="constitution/">
              <ProgramPaneBody onRerunSetup={() => navigateToSurface("setup")} />
            </GrantGate>
          </section>
        );
      // ADR-415 — Perception panes (re-homed from the dissolved Channels
      // surface). Connectors carries a deep Manage drill-in via the
      // `workspace-settings.connector=<provider>` param (was channels.connector).
      case "connectors": {
        const activeConnector = surfaceParam.get("connector");
        return (
          <section className="mb-8">
            {!activeConnector && (
              <PaneHeader
                icon={Link2}
                title="Connectors"
                subtitle="Connected platforms feeding the operation — status, coverage, and freshness."
              />
            )}
            <ConnectedIntegrationsSection
              redirectTo="/workspace-settings?workspace-settings.pane=connectors"
              showFreshness
              activeConnector={activeConnector}
              onManageConnection={(provider) => surfaceParam.set({ connector: provider })}
              onBackFromManage={() => surfaceParam.set({ connector: null })}
            />
          </section>
        );
      }
      case "sources":
        return (
          <section className="mb-8">
            <PaneHeader
              icon={Rss}
              title="Sources"
              subtitle="Standing web and RSS watches the operation tracks."
            />
            <SourcesCard variant="full" />
          </section>
        );
      case "members":
        // ADR-373 D2 — read-only Workspace Members legibility.
        return (
          <section className="mb-8">
            <WorkspaceMembersCard variant="full" />
          </section>
        );
      case "billing":
        // ADR-416 follow-on — the workspace's plan · balance · top-ups. The
        // body names the workspace it bills (BillingPaneBody) so switching is
        // legible, not silent.
        return (
          <section className="mb-8">
            <PaneHeader
              icon={CreditCard}
              title="Billing"
              subtitle="This workspace's plan, balance, and top-ups."
              bordered={false}
            />
            <BillingPaneBody />
          </section>
        );
      case "usage":
        // ADR-416 follow-on — this workspace's usage this cycle (activity, not
        // dollars — ADR-396 transparency). Workspace-scoped read.
        return (
          <section className="mb-8">
            <PaneHeader
              icon={BarChart3}
              title="Usage"
              subtitle="This workspace's included usage this cycle."
              bordered={false}
            />
            <UsagePaneBody />
          </section>
        );
      default:
        return null;
    }
  };

  return (
    <SettingsPaneShell windowSlug="workspace-settings" paneGroups={PANE_GROUPS} defaultPane="mandate" renderPane={renderPane} />
  );
}

/**
 * ProgramPaneBody — the Program pane (lifted from the ADR-340 P2
 * SettingsPage; re-homed to Workspace Settings per ADR-341). Wraps
 * ProgramLifecycleDrawer (ADR-244) + the "re-run setup" re-entry door
 * (Setup itself stays a window-grade Sequence surface per ADR-331).
 */
function ProgramPaneBody({ onRerunSetup }: { onRerunSetup: () => void }) {
  const [state, setState] = useState<Awaited<ReturnType<typeof api.workspace.getState>> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const next = await api.workspace.getState();
      setState(next);
      setError(null);
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Failed to load program state");
    }
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-4">
      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {!state && !error && (
        <div className="flex items-center justify-center py-10">
          <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
        </div>
      )}
      {state && <ProgramLifecycleDrawer state={state} onMutation={refresh} />}
      <button
        onClick={onRerunSetup}
        className="flex items-center gap-2 text-sm text-primary hover:underline"
      >
        <Rocket className="w-4 h-4" />
        Re-run setup
      </button>
    </div>
  );
}
