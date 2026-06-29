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
 */

import { useEffect, useState } from "react";
import { Target, UserCircle, Scale, Package, AlertCircle, Rocket, Loader2, Wallet, ShieldCheck, Crosshair, Users } from "lucide-react";
import { api, APIError } from "@/lib/api/client";
import { useSurfacePreferences } from "@/lib/shell/useSurfacePreferences";
import { SettingsPaneShell, type PaneGroup } from "@/components/settings/SettingsPaneShell";
import { MandateCard } from "@/components/workspace-concepts/MandateCard";
import { IdentityBrandCard } from "@/components/workspace-concepts/IdentityBrandCard";
import { PrinciplesCard } from "@/components/workspace-concepts/PrinciplesCard";
import { AutonomyCard } from "@/components/workspace-concepts/AutonomyCard";
import { BudgetCard } from "@/components/workspace-concepts/BudgetCard";
import { ExpectedOutputCard } from "@/components/workspace-concepts/ExpectedOutputCard";
import { WorkspaceMembersCard } from "@/components/workspace-concepts/WorkspaceMembersCard";
import { ProgramLifecycleDrawer } from "@/components/library/ProgramLifecycleDrawer";

// ADR-341/347: pane keys match the kernel registry slugs for pane-grade
// surfaces (mandate/identity/principles/budget/autonomy/expected-output/
// program), so foregroundSurface(slug) → workspace-settings + ?pane=slug
// resolves here. ADR-385: connectors/sources moved to pane_of: channels.
const PANE_GROUPS: PaneGroup[] = [
  {
    label: "Constitution",
    panes: [
      { key: "mandate", label: "Mandate", icon: Target },
      { key: "identity", label: "Identity", icon: UserCircle },
      { key: "principles", label: "Principles", icon: Scale },
    ],
  },
  {
    // ADR-347/ADR-348 — the operating contract, gathered: Rhythm · Witness
    // · Expected Output. Moved in from the dissolved System Settings door.
    label: "Contract",
    panes: [
      { key: "budget", label: "Budget", icon: Wallet },
      { key: "autonomy", label: "Autonomy", icon: ShieldCheck },
      { key: "expected-output", label: "Expected Output", icon: Crosshair },
    ],
  },
  {
    label: "Operation",
    panes: [{ key: "program", label: "Program", icon: Package }],
  },
  // ADR-385 D4 — the Perception group (Connectors · Sources) is removed from
  // Workspace Settings; perception is now wholly owned by the Channels surface
  // (the connectors/sources slugs are pane_of: channels). Settings tightens to
  // Constitution · Contract · Operation · Access.
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
    switch (pane) {
      case "mandate":
        return (
          <section className="mb-8">
            <MandateCard variant="full" />
          </section>
        );
      case "identity":
        return (
          <section className="mb-8">
            <IdentityBrandCard variant="full" />
          </section>
        );
      case "principles":
        return (
          <section className="mb-8">
            <PrinciplesCard variant="full" />
          </section>
        );
      // ADR-347/ADR-348 — the Contract group (Rhythm · Witness · Expected
      // Output). Operator-authored governance-region → inline editors.
      case "budget":
        return (
          <section className="mb-8">
            <BudgetCard variant="full" />
          </section>
        );
      case "autonomy":
        return (
          <section className="mb-8">
            <AutonomyCard variant="full" />
          </section>
        );
      case "expected-output":
        return (
          <section className="mb-8">
            <ExpectedOutputCard variant="full" />
          </section>
        );
      case "program":
        return (
          <section className="mb-8">
            <ProgramPaneBody onRerunSetup={() => navigateToSurface("setup")} />
          </section>
        );
      // ADR-385 D4 — the connectors + sources render cases are deleted here;
      // those slugs are now pane_of: channels and render on the Channels
      // surface. /connectors + /sources route stubs redirect there.
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
