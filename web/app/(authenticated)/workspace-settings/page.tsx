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
 *   - Operation: Program (ADR-432 — Brand RETIRED per D1c; Program's gate/framing
 *     fixed to the hire model, folds into /agents under ADR-382).
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
 *     plane). REVERSED by ADR-454 D4 (2026-07-13, the ambient steward): the
 *     two dials came BACK as the unbranded System group below; the persona
 *     panes stay dormant in SystemAgentPanes; /system-agent is a redirect stub.
 */

import { AlertTriangle, BarChart3, CreditCard, KeyRound, Users } from "lucide-react";
import { SettingsPaneShell, PaneHeader, type PaneGroup } from "@/components/settings/SettingsPaneShell";
// ADR-491 D1 (2026-07-28) — Billing + Usage return to THIS door (the third and
// final placement flip): with members real (seats live, ADR-490), billing is
// authority-gated WORKSPACE governance — the ChatGPT/Claude Team convention.
// Billing gates on the server's 403 (billing authority, ADR-416 D1) inside
// SubscriptionCard; Usage stays member-visible (commons legibility, DP29).
import { BillingPaneBody } from "@/components/subscription/BillingPaneBody";
import { UsagePaneBody } from "@/components/subscription/UsagePaneBody";
// ADR-454 D4 (2026-07-13) — the ambient steward: the ADR-426 "Freddie System
// Agent" door is REVERSED. The steward's two operator-tunable dials come back
// to this door as an unbranded SYSTEM group (same pane bodies, third move,
// never duplicated); the persona panes (About · Activity) stay dormant in
// SystemAgentPanes pending the narrative-posture regroup.
// ADR-551 — the renderSystemAgentPane import is REMOVED with the group. That
// module's other two panes (About · Activity) were ALREADY mountless since
// ADR-454 D4; with `autonomy` gone it has no importer at all, so the whole
// SystemAgentPanes module is now dead and deleted rather than left orphaned.
// ADR-429 §13.3 (2026-07-09) — Billing + Usage LEFT this door for the account
// door (User Settings, Vercel-style). The workspace-as-billing-unit data-model is
// unchanged — only the door moved (see settings/page.tsx).
// ADR-421 — the Constitution-pane card imports were removed with the group.
// ADR-432 D1c/D2d — Brand + Program pane imports removed (Brand retired; the
// operator-facing Program hire UI is retired, its lifecycle-drawer component
// stays in the Setup sequence).
import { WorkspaceMembersCard } from "@/components/workspace-concepts/WorkspaceMembersCard";
// ADR-566 D5 — the workspace's own allocated credentials (its agents' reach).
// A SECOND, disjoint store from the account door's Connectors pane (ADR-425 D1),
// never a re-merge of the pane ADR-425 removed.
import { WorkspaceCredentialsCard } from "@/components/workspace-concepts/WorkspaceCredentialsCard";
import { useWorkspaceMembers } from "@/lib/workspace/viewer";
import { WorkspaceDangerZone } from "@/components/workspace-concepts/WorkspaceDangerZone";
// ADR-425 — the Perception group (Connectors · Sources) left this door:
// Connectors → the account door (a credential is a human's account object),
// Sources → hidden. ConnectedIntegrationsSection now mounts in settings/page.tsx;
// SourcesCard is retained but has no operator mount (ADR-425 D2).
// ADR-426 (2026-07-09) carved the System Agent group into its own door;
// ADR-454 D4 (2026-07-13) reversed it — the two dials render here again via
// renderSystemAgentPane (the System group), Singular Implementation.

// ADR-341/347: pane keys match the kernel registry slugs for pane-grade
// surfaces, so foregroundSurface(slug) → workspace-settings + ?pane=slug
// resolves here. ADR-415: connectors/sources re-homed here (Channels dissolved).
// ADR-454 D4 (2026-07-13): the door set is Access (Members) · System
// (Autonomy · Budget — back from the reversed ADR-426 door).
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
  // ADR-432 (2026-07-09) — the OPERATION group is REMOVED entirely.
  //  - Brand: retired in full (D1c) — operation/BRAND.md read by no producing path.
  //  - Program: the operator-facing pane is RETIRED (D2d). Zero hired-program
  //    grants exist anywhere; activation has never fired; the pane presented a
  //    launch operator a "hire a program" action into the deliberately-unvalidated
  //    Rung-2 path (ADR-380). The `program` surface goes DORMANT (like ADR-421 did
  //    to the constitution surfaces); the hire MACHINERY is untouched (getState
  //    available_programs / active_program_slug, routes/programs.py, the compositor
  //    program-cockpit, the lifecycle-drawer via the Setup sequence). Activation
  //    re-surfaces on the /agents roster when ADR-382 builds it (D2c).
  // With Billing/Usage gone (ADR-429 §13.3), the door is now Access alone.
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
    panes: [
      { key: "members", label: "Workspace Members", icon: Users },
      // ADR-566 D5 — the WORKSPACE's own allocated credentials: what its agents
      // act through. NOT the pane ADR-425 D1 removed (that one showed HUMANS'
      // connectors under a workspace heading, the mis-scoping 425 fixed, and a
      // member's own connectors stay in the account door). It sits under Access
      // because it answers the same question the roster does — what can reach
      // this workspace, and what can this workspace reach — not under a revived
      // "Perception" grouping (ADR-425 OQ3: no cosmetic re-merge).
      { key: "credentials", label: "Agent Credentials", icon: KeyRound },
    ],
  },
  {
    // ADR-491 D1 — the workspace's money. Billing is authority-gated (the
    // owner's verbs; a member sees the calm pointer state); Usage is
    // member-visible legibility. Each pane names the workspace it bills.
    label: "Billing",
    panes: [
      { key: "billing", label: "Billing", icon: CreditCard },
      { key: "usage", label: "Usage", icon: BarChart3 },
    ],
  },
  // ADR-551 — the SYSTEM AGENT group is REMOVED (reversing ADR-491 D4, which
  // reversed ADR-426, which carved it out of ADR-454 D4's group; the pane had
  // moved four times without the question underneath it being re-asked).
  //
  // The question this door must answer is "what does this workspace's shared
  // settings govern". Autonomy is not that: the gate it drives applies ONLY to
  // the steward's own calls — `permission.py::resolve_permission` returns
  // APPLY at `non_freddie_caller` before ever reading the dial — so every
  // human, lane and MCP write bypasses it entirely. File mutation through the
  // chat primitives is first-class and ungated by design.
  //
  // So a workspace-level control implied a scope it never had. Autonomy is a
  // property of AN AGENT, not of the shared commons; it belongs on the agent
  // detail (ADR-414 D6's per-agent sidecar) when ADR-382 builds that roster.
  //
  // The MECHANICS stay — see api/services/review_policy.py. Deleting the file
  // would invert ADR-408 D3 and queue every steward write. It is live code
  // that is currently dormant (prod: `invocations=0/0` on every scheduler tick),
  // which is exactly why it needed a recorded reason rather than a silent pane.
  {
    // ADR-476 D3 — the workspace-CONTENT purges. L1 (clear work history) and
    // L2 (clear workspace) destroy every member's work, so under ADR-407 they
    // are workspace-scope, not account-scope. They moved here from System
    // Settings → Account, which keeps the genuinely account-scoped actions
    // (a member's own connections, account reset, deactivation).
    label: "Danger Zone",
    panes: [{ key: "danger", label: "Clear Workspace", icon: AlertTriangle }],
  },
];

export default function WorkspaceSettingsPage() {
  // ADR-412 D6 — the roster read is the surface's access probe. It is already
  // fetched once per workspace bind and cached, so this adds no request.
  const { forbidden: accessRefused } = useWorkspaceMembers();

  // ADR-494 D5 — the ADR-491 D3 `budget` → `usage` normalizer is DELETED. It
  // existed only to clean a PERSISTED retired pane value; `pane` is no longer
  // remembered (SURFACE_EPHEMERAL_PARAM_KEYS), so a stale value can no longer
  // be replayed and there is nothing to normalize. A retired pane now falls to
  // the shell's default-pane fallback by construction — one mechanism instead
  // of a hand-written case per retirement.

  const renderPane = (pane: string) => {
    switch (pane) {
      // ADR-421 — Mandate/Identity/Principles cases REMOVED (workspace has no
      // constitution of its own; per-agent, ADR-419). ADR-432 D1c — `brand` case
      // REMOVED (Brand retired). ADR-432 D2d — `program` case REMOVED (the
      // operator-facing hire UI is retired; the `program` surface is dormant, the
      // hire machinery stays — see PANE_GROUPS). ADR-425 — connectors/sources
      // cases REMOVED (connectors → account door; sources hidden).
      case "members":
        // ADR-373 D2 — read-only Workspace Members legibility.
        return (
          <section className="mb-8">
            <WorkspaceMembersCard variant="full" />
          </section>
        );
      // ADR-566 D5 — what this workspace's AGENTS act through. The subtitle
      // does the load-bearing work of keeping the two stores apart at a glance:
      // a member arriving here must not read it as "my connections".
      case "credentials":
        return (
          <section className="mb-8">
            <PaneHeader
              icon={KeyRound}
              title="Agent Credentials"
              subtitle="What this workspace's agents can reach. Your own connections live in your account settings."
              bordered={false}
            />
            <WorkspaceCredentialsCard />
          </section>
        );
      // ADR-491 D1 — the workspace's money (returned from the account door).
      case "billing":
        return (
          <section className="mb-8">
            <PaneHeader
              icon={CreditCard}
              title="Billing"
              subtitle="This workspace's plan, seats, and balance."
              bordered={false}
            />
            <BillingPaneBody />
          </section>
        );
      case "usage":
        return (
          <section className="mb-8">
            <PaneHeader
              icon={BarChart3}
              title="Usage"
              subtitle="This workspace's usage — what ran, what it drew from the shared balance, and who used it."
              bordered={false}
            />
            <UsagePaneBody />
          </section>
        );
      // ADR-551 — the `autonomy` case is REMOVED with its group. A stale
      // `?workspace-settings.pane=autonomy` link (or the /autonomy redirect
      // stub) now falls to the shell's default-pane fallback, which is the
      // mechanism ADR-494 D5 built for exactly this — a retired pane needs no
      // hand-written case.
      // ADR-476 D3 — the workspace-content purges (L1/L2), owner-gated.
      case "danger":
        return (
          <section className="mb-8">
            <PaneHeader
              icon={AlertTriangle}
              title="Clear Workspace"
              subtitle="Remove this workspace's shared content. These actions affect every member's work and cannot be undone."
              bordered={false}
            />
            <WorkspaceDangerZone />
          </section>
        );
      // ADR-429 §13.3 — the billing/usage cases LEFT this door for the account
      // door (settings/page.tsx). No cases here; nothing routes to them.
      default:
        return null;
    }
  };

  // A viewer with NO grant on the bound workspace (revoked, or never granted)
  // gets a plain statement instead of the full pane chrome. Every pane's fetch
  // 403s underneath, so the surface previously rendered its nav and headings
  // over nothing at all — accurate refusal, unreadable presentation
  // (2026-07-31 click-pass F3). `forbidden` is specifically a 403, never a
  // transport blip, so a flaky network cannot lock a real member out of it.
  if (accessRefused) {
    return (
      <div className="mx-auto max-w-lg px-6 py-16 text-center">
        <h1 className="text-base font-semibold text-foreground">
          You don&rsquo;t have access to this workspace
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Your access may have been revoked, or you may be viewing a workspace
          you were never added to. Switch workspaces from the avatar menu, or
          ask the owner to invite you again.
        </p>
      </div>
    );
  }

  return (
    <SettingsPaneShell windowSlug="workspace-settings" paneGroups={PANE_GROUPS} defaultPane="members" renderPane={renderPane} />
  );
}

// ADR-432 D2d (2026-07-09): the in-file Program pane body was REMOVED with the
// operator-facing Program pane. The lifecycle-drawer component it wrapped stays
// (used by the Setup sequence); the getState / hire machinery is untouched.
