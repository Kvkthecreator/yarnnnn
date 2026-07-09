"use client";

/**
 * /workspace-settings — the ONE Settings door (ADR-347, 2026-06-19;
 * created by ADR-341, 2026-06-18).
 *
 * ADR-347 reversed ADR-341's two-door split: this is THE operation-settings
 * door. It configures THIS operation. The account (Billing/Usage/Account)
 * lives on the User Settings door / UserMenu (the human/principal's concern,
 * ADR-347 D2 — Billing/Usage later moved back here per the ADR-416 follow-on
 * as workspace-scoped money). Mounts the shared SettingsPaneShell (Singular
 * Implementation, ADR-341 D5).
 *
 * Sidebar groups (the current live set):
 *   - Operation: Brand · Program (ADR-244/387 D3).
 *   - Access (ADR-373 D2): Workspace Members — who can write the workspace.
 *   - Billing (ADR-416 follow-on): Billing · Usage — this workspace's money.
 *
 * What LEFT this door:
 *   - ADR-421 (2026-07-08): the Constitution group (Mandate/Identity/
 *     Principles) — a workspace has no constitution of its own; those are
 *     per-agent, surfaced on the agent detail (AgentConstitutionBlock).
 *   - ADR-425 (2026-07-09): the Perception group — Connectors → the account
 *     door (a credential is a human's account object), Sources → hidden.
 *   - ADR-426 (2026-07-09): the System Agent group (Freddie's dials +
 *     legibility — Autonomy · Budget · Capabilities · Activity) → its OWN
 *     window-grade door (/system-agent, "Freddie System Agent", same launcher
 *     plane). This door stops mixing the system agent's config with the
 *     operation's; SystemAgentPanes mounts on system-agent/page.tsx now.
 */

import { useEffect, useState } from "react";
import { UserCircle, Package, AlertCircle, Rocket, Loader2, Users, CreditCard, BarChart3 } from "lucide-react";
import { api, APIError } from "@/lib/api/client";
import { useSurfacePreferences } from "@/lib/shell/useSurfacePreferences";
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
// ADR-425 — the Perception group (Connectors · Sources) left this door:
// Connectors → the account door (a credential is a human's account object),
// Sources → hidden. ConnectedIntegrationsSection now mounts in settings/page.tsx;
// SourcesCard is retained but has no operator mount (ADR-425 D2).
// ADR-426 (2026-07-09) — the System Agent group (Freddie's dials + legibility)
// LEFT this door and became its own window-grade surface (/system-agent, the
// "Freddie System Agent" door on the same launcher plane). This door no longer
// mixes the operation's config with the system agent's; SystemAgentPanes now
// mounts on system-agent/page.tsx (Singular Implementation).

// ADR-341/347: pane keys match the kernel registry slugs for pane-grade
// surfaces, so foregroundSurface(slug) → workspace-settings + ?pane=slug
// resolves here. ADR-415: connectors/sources re-homed here (Channels dissolved).
// ADR-426 (2026-07-09): the System Agent group LEFT this door for its own
// surface (/system-agent). This door is now homogeneously about the operation +
// the workspace: Operation (Brand · Program) · Access (Members) · Billing.
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
  // ADR-425 (2026-07-09) — the Perception group is REMOVED. Connectors moved
  // to the account door (User Settings): a platform credential is a human's
  // account object, not a workspace peripheral. Sources is hidden from the
  // operator surface (ADR-425 D2). (Lineage: ADR-341 Workspace-Settings →
  // ADR-385 Channels → ADR-415 back here → ADR-425 Connectors→account, Sources
  // hidden.)
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
  // ADR-425 — the connector drill-in param moved to the account door with the
  // Connectors pane (settings.connector); this door no longer reads it.

  const renderPane = (pane: string) => {
    // ADR-426 — the System Agent panes moved to their own door (/system-agent);
    // they no longer render here.
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
      // ADR-425 — the "connectors" + "sources" cases are REMOVED. Connectors
      // renders in the account door (settings/page.tsx); Sources is hidden from
      // the operator surface (its SourcesCard + GET /api/sources substrate are
      // retained for a future first-class home, ADR-425 D2/OQ3).
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
    <SettingsPaneShell windowSlug="workspace-settings" paneGroups={PANE_GROUPS} defaultPane="brand" renderPane={renderPane} />
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
