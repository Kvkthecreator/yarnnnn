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
import { Target, UserCircle, Package, AlertCircle, Rocket, Loader2, Users } from "lucide-react";
import { api, APIError } from "@/lib/api/client";
import { useSurfacePreferences, useSurfaceParam } from "@/lib/shell/useSurfacePreferences";
import { SettingsPaneShell, type PaneGroup } from "@/components/settings/SettingsPaneShell";
import { MandateCard } from "@/components/workspace-concepts/MandateCard";
import { WorkspaceMembersCard } from "@/components/workspace-concepts/WorkspaceMembersCard";
import { WorkspaceFileView } from "@/components/shared/WorkspaceFileView";
import { ProgramLifecycleDrawer } from "@/components/library/ProgramLifecycleDrawer";

// ADR-341/347: pane keys match the kernel registry slugs for pane-grade
// surfaces (mandate/identity/principles/budget/autonomy/expected-output/
// program), so foregroundSurface(slug) → workspace-settings + ?pane=slug
// resolves here. ADR-385: connectors/sources moved to pane_of: channels.
// ADR-387 D1 (2026-06-29): the agent-scoped panes — Identity + Principles
// (persona/), Autonomy + Budget (governance/ grant), Expected Output
// (contract/) — MOVED OUT to Freddie's pane (?agent=freddie), where the
// agent's settings belong post-ADR-381/383. A MOVE not a copy (Singular
// Implementation, the ADR-297 invariant): they are gone from here. Deep-links
// to the old pane slugs redirect (ADR-308 stub, see redirectToFreddie below).
// Workspace Settings keeps Mandate (constitution/ — operator intent), Brand
// (operation/ — D3 interim home pending its own rethink), Program (operation/
// — D4, its own scoped ADR), Members (access).
const PANE_GROUPS: PaneGroup[] = [
  {
    label: "Constitution",
    panes: [{ key: "mandate", label: "Mandate", icon: Target }],
  },
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

// ADR-387 D1 — ADR-308 pure-transport redirect: the moved pane slugs land on
// Freddie's pane. A deep-link to workspace-settings.pane=identity (etc.) now
// foregrounds the agents window on Freddie with the matching tab.
const MOVED_TO_FREDDIE: Record<string, string> = {
  identity: "identity",
  principles: "principles",
  autonomy: "autonomy",
  budget: "budget",
  "expected-output": "expected-output",
};

export default function WorkspaceSettingsPage() {
  const { navigateToSurface } = useSurfacePreferences();
  const surfaceParam = useSurfaceParam("workspace-settings");
  const requestedPane = surfaceParam.get("pane");

  // ADR-387 D1 — ADR-308 pure-transport redirect. A deep-link to a moved pane
  // (workspace-settings.pane=identity|principles|autonomy|budget|expected-output)
  // foregrounds Freddie's pane with the matching tab. Done in an effect (a
  // navigation side-effect, not render) so the redirect stub paints nothing
  // (no orphaned frame — ADR-308).
  useEffect(() => {
    if (requestedPane && MOVED_TO_FREDDIE[requestedPane]) {
      navigateToSurface("agents", { agent: "freddie", tab: MOVED_TO_FREDDIE[requestedPane] });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestedPane]);

  const renderPane = (pane: string) => {
    switch (pane) {
      case "mandate":
        return (
          <section className="mb-8">
            <MandateCard variant="full" />
          </section>
        );
      // ADR-387 D3 — Brand stays here (interim). Rendered via the universal
      // WorkspaceFileView reading operation/BRAND.md directly (Identity moved
      // to Freddie, so the old merged "Identity & Brand" card no longer fits).
      case "brand":
        return (
          <section className="mb-8">
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
          </section>
        );
      case "program":
        return (
          <section className="mb-8">
            <ProgramPaneBody onRerunSetup={() => navigateToSurface("setup")} />
          </section>
        );
      // ADR-385 D4 — connectors/sources moved to Channels.
      // ADR-387 D1 — identity/principles/autonomy/budget/expected-output MOVED
      // to Freddie's pane (redirected above); their render cases are gone here.
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
