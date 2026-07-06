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
 * (Identity · Principles · Autonomy · Budget · Expected Output ·
 * Capabilities · Activity) re-home HERE from the /agents roster, reversing
 * ADR-387 §6.4's placement: the Agents surface is Altitude 3 (domain +
 * persona agents); the system agent's inspection surface belongs on the
 * system layer. Bodies render via SystemAgentPanes (Singular
 * Implementation — the roster mount is deleted). The ADR-387
 * MOVED_TO_FREDDIE redirect net is deleted with it: the old
 * workspace-settings.pane= URLs simply resolve here again.
 */

import { useEffect, useState } from "react";
import { Target, UserCircle, Package, AlertCircle, Rocket, Loader2, Users } from "lucide-react";
import { api, APIError } from "@/lib/api/client";
import { useSurfacePreferences } from "@/lib/shell/useSurfacePreferences";
import { SettingsPaneShell, type PaneGroup } from "@/components/settings/SettingsPaneShell";
import { MandateCard } from "@/components/workspace-concepts/MandateCard";
import { GrantGate } from "@/components/workspace-concepts/GrantGate";
import { WorkspaceMembersCard } from "@/components/workspace-concepts/WorkspaceMembersCard";
import { WorkspaceFileView } from "@/components/shared/WorkspaceFileView";
import { ProgramLifecycleDrawer } from "@/components/library/ProgramLifecycleDrawer";
// ADR-412 D5 — the System Agent group (Freddie's panes, re-homed from the
// /agents roster; reverses ADR-387 §6.4).
import {
  SYSTEM_AGENT_PANE_GROUP,
  SYSTEM_AGENT_PANE_KEYS,
  renderSystemAgentPane,
} from "@/components/agents/SystemAgentPanes";

// ADR-341/347: pane keys match the kernel registry slugs for pane-grade
// surfaces, so foregroundSurface(slug) → workspace-settings + ?pane=slug
// resolves here. ADR-385: connectors/sources moved to pane_of: channels.
// ADR-412 D5 (2026-07-06): the ADR-387 §6.4 move is REVERSED — the
// agent-scoped panes (identity/principles/autonomy/budget/expected-output +
// capabilities/activity) return as the System Agent group, since Freddie
// left the /agents roster. Registry rows carry pane_of: workspace-settings
// again; capabilities/activity stay local pane keys (no registry row).
const PANE_GROUPS: PaneGroup[] = [
  {
    label: "Constitution",
    panes: [{ key: "mandate", label: "Mandate", icon: Target }],
  },
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
  // ADR-385 D4 — the Perception group (Connectors · Sources) was removed.
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
];

export default function WorkspaceSettingsPage() {
  const { navigateToSurface } = useSurfacePreferences();

  const renderPane = (pane: string) => {
    // ADR-412 D5 — the System Agent panes render via the shared module.
    if (SYSTEM_AGENT_PANE_KEYS.includes(pane)) {
      return <section className="mb-8">{renderSystemAgentPane(pane)}</section>;
    }
    switch (pane) {
      case "mandate":
        // ADR-412 D3 — constitutional pane: reads stay universal; write
        // affordances render per the viewer's grant coverage (explicit
        // read-only banner when constitution/ is outside it).
        return (
          <section className="mb-8">
            <GrantGate region="constitution/">
              <MandateCard variant="full" />
            </GrantGate>
          </section>
        );
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
      // ADR-385 D4 — connectors/sources moved to Channels.
      case "members":
        // ADR-373 D2 — read-only Workspace Members legibility.
        return (
          <section className="mb-8">
            <WorkspaceMembersCard variant="full" />
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
