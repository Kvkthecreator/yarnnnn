"use client";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  AlertTriangle,
  ArrowRight,
  Loader2,
  Check,
  User,
  RefreshCw,
  LogOut,
  Bell,
  Mail,
  Link2,
  Shield,
  History,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { useSurfacePreferences, useSurfaceParam } from "@/lib/shell/useSurfacePreferences";
import { createClient } from "@/lib/supabase/client";
import { useNarrative } from "@/contexts/NarrativeContext";
// ADR-347 → ADR-416 follow-on (2026-07-08): this `settings` surface is the
// ACCOUNT window — genuinely user_id-scoped (data & privacy, danger zone).
// Billing + Usage moved OUT to Workspace Settings (both workspace-scoped money,
// ADR-416, superseding ADR-347's account-door placement). The shared
// SettingsPaneShell renders the sidebar + pane switch (ADR-341 D5).
import { SettingsPaneShell, PaneHeader, type PaneGroup } from "@/components/settings/SettingsPaneShell";
// The sanctioned cross-surface link (2026-06-25). These two point at the
// OTHER Settings door; as raw <a href> they hard-navigated, which remounted
// the SPA and painted THIS surface before the pathname sync foregrounded the
// target — the operator-visible two-step. See SurfaceLink's docblock.
import { SurfaceLink } from "@/components/shell/SurfaceLink";
// ADR-425 — the Connectors pane (a human's platform credentials) lives in the
// account door now. The section is location-agnostic; it was formerly mounted
// under Workspace Settings → Perception.
import { ConnectedIntegrationsSection } from "@/components/settings/ConnectedIntegrationsSection";
// ADR-496 — the inbound half of a member's own connections. This is the SAME
// component the workspace door renders, in `scope="mine"` + `readOnly` — not a
// look-alike. One roster, one row renderer, so the two surfaces are identical
// by construction rather than by careful copying.
import { WorkspaceMembersCard } from "@/components/workspace-concepts/WorkspaceMembersCard";
// ADR-491 D1 — Billing + Usage LEFT this door (again, finally) for Workspace
// Settings: with members real (seats live, ADR-490), billing is role-gated
// workspace governance, and the enterprise convention (ChatGPT/Claude Team)
// puts it behind the workspace door. This door is now genuinely personal:
// Account + Connectors. Legacy ?settings.pane=billing|usage redirects across
// (effect below).

interface DangerZoneStats {
  workspace_files: number;
  agents: number;
  tasks: number;
  chat_sessions: number;
  platform_connections: number;
  // Phase 3 (L1): count of past task runs — drives the "Clear Work History" card.
  agent_runs: number;
  // ADR-194 Reviewer queue — pending proposals; surfaced so L2/L4 confirmation
  // copy can tell the user what gets discarded.
  action_proposals: number;
}

// ADR-489 D5 — the ONE prefs store is member_state['notification_prefs'],
// keyed (acting workspace, principal): mute one commons, not all. Shape +
// quiet defaults mirror services/notifications.py DEFAULT_NOTIFICATION_PREFS.
// witness_email is the after-witness push dial (ADR-405 D2): the bell stays
// the canonical channel; email push is opt-in.
interface NotificationPreferences {
  delivery_email: boolean;
  failure_email: boolean;
  witness_email: 'all' | 'high' | 'none';
}

const DEFAULT_NOTIFICATION_PREFS: NotificationPreferences = {
  delivery_email: true,
  failure_email: true,
  witness_email: 'high',
};

// The `settings` surface is the ACCOUNT window — genuinely user_id-scoped, the
// human/principal's concern (data & privacy, danger zone). ADR-416 follow-on
// (2026-07-08): Billing + Usage MOVED OUT to Workspace Settings — both are
// WORKSPACE-scoped (the workspace is the billing unit, ADR-416; getLimits /
// getUsageDetail key on the acting workspace_id, migration 200). This supersedes
// ADR-347's account-door placement, which predated the ADR-416 billing-unit
// ratification.
// ADR-425 (2026-07-09): Connectors moves IN — a platform credential is an
// account object (a human's own Slack/Notion/GitHub, keyed user_id), not a
// workspace peripheral. So the account door holds Account + Connections.
// ADR-491 D1 (2026-07-28): Billing + Usage move OUT to Workspace Settings —
// with members real, billing is authority-gated workspace governance (the
// ChatGPT/Claude Team convention). Supersedes ADR-429 §13.3's account-door
// placement.
type SettingsTab = "account" | "connectors";

// Connections LEADS (2026-08-21, operator ruling). This door is opened to
// manage a connection far more often than to reset an account, and Account's
// contents are destructive verbs — a danger zone is a poor landing pane. The
// nav order and the default pane move together; a sidebar whose first item is
// not what loads reads as a bug.
const PANE_GROUPS: PaneGroup[] = [
  // ADR-425 — a human's platform connections are their own credentials, in
  // their account. (The workspace does not present "its connectors"; it
  // presents who has a grant + what they authored.)
  {
    label: "Connections",
    panes: [{ key: "connectors", label: "Connectors", icon: Link2 }],
  },
  {
    label: "Account",
    panes: [{ key: "account", label: "Account", icon: User }],
  },
];

const ALL_PANES: SettingsTab[] = PANE_GROUPS.flatMap((g) => g.panes.map((p) => p.key as SettingsTab));
// ADR-425 §2 — "integrations" is GONE with its card and endpoint. Leaving a
// dead member here is what let the ADR-476 D3 move keep live plumbing behind.
type DangerAction =
  | "reset"
  | "deactivate"
  | null;

export default function SettingsPage() {
  const router = useRouter();
  const { navigateToSurface } = useSurfacePreferences();
  const accountParam = useSurfaceParam('settings');
  const searchParams = useSearchParams();
  const { clearMessages } = useNarrative();
  const tabParam = searchParams.get("tab");
  // ADR-358 D6: the pane is the WINDOW-NAMESPACED `settings.pane` (so the
  // account door never collides with workspace-settings on a flat `?pane=`).
  // `?tab=` kept as a flat legacy alias. The page derives `activeTab` from
  // the same param the SettingsPaneShell reads — single source (the URL).
  const paneParam = accountParam.get("pane");
  // ADR-215 R3 (2026-04-24): `memory` tab retired — identity/brand/profile
  // are substrate, edited on Files (/files?path=/workspace/constitution|governance|operation/… (ADR-320 roots)).
  // Legacy `?tab=memory` redirects to Files IDENTITY.md via effect below.
  const requestedPane = paneParam ?? tabParam;
  // ADR-341: the shared SettingsPaneShell owns sidebar selection + `?pane=`
  // URL sync. The page derives `activeTab` from the same search param to
  // drive its data-loading effects (usage/account) — single source (the
  // URL), no duplicate selection state.
  // Must match SettingsPaneShell's `defaultPane` below — the page derives its
  // data-loading effects from this value, so a disagreement loads one pane's
  // data while rendering another's.
  const activeTab: SettingsTab = ALL_PANES.includes(requestedPane as SettingsTab)
    ? (requestedPane as SettingsTab)
    : "connectors";

  // ADR-531 — the OAuth outcome params. The callback has always encoded these
  // (`provider`, `status`, and on failure `error` + `error_reason`); until now
  // NOTHING read them, so a failed connection returned the operator to settings
  // with no indication anything had gone wrong. They are flat params because
  // the OAuth provider redirects to a bare URL the shell never namespaces.
  const oauthProvider = searchParams.get("provider");
  const oauthStatus = searchParams.get("status");
  const oauthError = searchParams.get("error");
  const oauthErrorReason = searchParams.get("error_reason");

  // ADR-215 R3: legacy `/settings?tab=memory` redirects to Files with
  // IDENTITY.md preselected. One edit surface for substrate (Files).
  // ADR-358: foreground the Files window (navigateToSurface) rather than
  // hard-navigating off the /desktop baseline.
  useEffect(() => {
    if (tabParam === "memory") {
      navigateToSurface("files", { path: "/workspace/context/_shared/IDENTITY.md" });
    }
  }, [tabParam, navigateToSurface]);

  // ADR-494 D5 — the ADR-491 D1 `billing`/`usage` clearing effect is DELETED.
  // It patched the symptom (a stale RESTORE-class pane value with no clearing
  // path); the cause is fixed at the source — `settings.pane` is now ephemeral
  // (SURFACE_EPHEMERAL_PARAM_KEYS), so no stale pane is ever replayed and this
  // door always opens on Account. An old `?pane=billing` bookmark still lands
  // here safely via the ALL_PANES fallback below.

  const [dangerStats, setDangerStats] = useState<DangerZoneStats | null>(null);
  const [isLoadingDangerStats, setIsLoadingDangerStats] = useState(false);
  const [isPurging, setIsPurging] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [dangerAction, setDangerAction] = useState<DangerAction>(null);
  const [purgeSuccess, setPurgeSuccess] = useState<string | null>(null);

  // Notification preferences state
  const [notificationPrefs, setNotificationPrefs] = useState<NotificationPreferences | null>(null);
  const [isLoadingNotifications, setIsLoadingNotifications] = useState(false);
  const [isSavingNotifications, setIsSavingNotifications] = useState(false);

  // Billing + Usage state/effects/loaders removed 2026-07-08 (ADR-416 follow-on)
  // — those panes moved to Workspace Settings as self-contained components
  // (BillingPaneBody / UsagePaneBody), which own their own fetches.

  // Fetch danger zone stats when account tab is active
  useEffect(() => {
    if (activeTab === "account") {
      loadDangerZoneStats();
    }
  }, [activeTab]);

  // Fetch notification preferences when notifications tab is active
  useEffect(() => {
    if (activeTab === "account" && !notificationPrefs) {
      loadNotificationPreferences();
    }
  }, [activeTab, notificationPrefs]);

  const loadNotificationPreferences = async () => {
    setIsLoadingNotifications(true);
    try {
      // ADR-489 D5 — member_state is the one prefs store; missing keys read
      // the quiet defaults.
      const res = await api.memberState.get('notification_prefs');
      const stored = (res.value as Partial<NotificationPreferences> | null) ?? {};
      setNotificationPrefs({ ...DEFAULT_NOTIFICATION_PREFS, ...stored });
    } catch (err) {
      console.error("Failed to fetch notification preferences:", err);
      setNotificationPrefs({ ...DEFAULT_NOTIFICATION_PREFS });
    } finally {
      setIsLoadingNotifications(false);
    }
  };

  const handleNotificationChange = async (patch: Partial<NotificationPreferences>) => {
    if (!notificationPrefs) return;
    const previous = notificationPrefs;
    const next = { ...notificationPrefs, ...patch };

    // Optimistic update, revert on error.
    setNotificationPrefs(next);
    setIsSavingNotifications(true);
    try {
      await api.memberState.put('notification_prefs', next);
    } catch (err) {
      console.error("Failed to update notification preference:", err);
      setNotificationPrefs(previous);
    } finally {
      setIsSavingNotifications(false);
    }
  };

  const loadDangerZoneStats = async () => {
    setIsLoadingDangerStats(true);
    try {
      const stats = await api.account.getDangerZoneStats();
      setDangerStats(stats);
    } catch (err) {
      console.error("Failed to fetch danger zone stats:", err);
    } finally {
      setIsLoadingDangerStats(false);
    }
  };

  // Danger zone action handler
  const handleDangerAction = async () => {
    if (!dangerAction) return;

    setIsPurging(true);
    setPurgeSuccess(null);

    try {
      let result;
      switch (dangerAction) {
        case "reset":
          result = await api.account.resetAccount();
          setPurgeSuccess(result.message);
          clearMessages();
          // Backend now re-scaffolds transactionally (ADR-140/151/161/164 invariants).
          // This call is a harmless safety net; it returns the already-restored state.
          await api.workspace.getState().catch(() => null);
          // Route to /chat so TP greets the user and triggers the onboarding
          // modal (identity is empty/sparse after full reset). Previously routed
          // to /work which skipped onboarding entirely.
          // ADR-297 D19.4 — foreground a surface (window-open), not
          // router.push (which erases the Desktop). ADR-435 (2026-07-10): land
          // on Chat — the steward's voice + activation surface (Home was
          // deleted; identity sparse after full reset, so the steward greets +
          // the onboarding modal triggers). Was 'home', before that 'channels'.
          setTimeout(() => navigateToSurface('chat'), 1500);
          break;
        case "deactivate":
          result = await api.account.deactivateAccount();
          setPurgeSuccess(result.message);
          const supabase = createClient();
          await supabase.auth.signOut();
          router.push("/");
          break;
      }
      // Refresh danger zone stats
      await loadDangerZoneStats();
    } catch (err) {
      console.error("Danger action failed:", err);
      setPurgeSuccess("Operation failed. Please try again.");
    } finally {
      setIsPurging(false);
      setShowConfirm(false);
      setDangerAction(null);
    }
  };

  const initiateDangerAction = (action: DangerAction) => {
    setDangerAction(action);
    setShowConfirm(true);
  };


  // Auto-dismiss purge success
  useEffect(() => {
    if (purgeSuccess) {
      const timer = setTimeout(() => setPurgeSuccess(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [purgeSuccess]);

  // ADR-341: the body for the active pane. The shared SettingsPaneShell
  // owns the sidebar + selection + `?pane=` sync; the page provides the
  // pane bodies. Governance panes (autonomy/budget) are cards; General
  // panes (billing/usage/account) are the heavier blocks below.
  const renderPane = (pane: string) => (
    <>
      {/* ADR-491 D1 — the billing/usage cases LEFT this door for Workspace
          Settings (authority-gated workspace governance). Legacy links redirect
          via the effect above; no cases here. */}

      {/* Connectors — ADR-425: a human's platform connections are account
          objects (their own credential, keyed user_id). Moved here from
          Workspace Settings → Perception. Reuses ConnectedIntegrationsSection
          (location-agnostic); the connector drill-in rides settings.connector. */}
      {pane === "connectors" && (
        <section className="mb-8">
          {!accountParam.get("connector") && (
            <PaneHeader
              icon={Link2}
              title="Connectors"
              subtitle="Your connections — platforms you reach out to, and AI assistants that reach in. Each is authorized by you, and yours to disconnect."
              bordered={false}
            />
          )}
          <ConnectedIntegrationsSection
            redirectTo="/settings?settings.pane=connectors"
            showFreshness
            activeConnector={accountParam.get("connector")}
            onManageConnection={(provider) => accountParam.set({ connector: provider })}
            onBackFromManage={() => accountParam.set({ connector: null })}
            // ADR-531 — the OAuth outcome, surfaced. The section owns the
            // banner because that is where the failed connector's own row is.
            oauthOutcome={
              oauthStatus === "error"
                ? {
                    status: "error",
                    provider: oauthProvider,
                    error: oauthError,
                    reason: oauthErrorReason,
                  }
                : null
            }
            onDismissOauthOutcome={() => {
              // Clear the flat OAuth params without touching pane state — a
              // dismissed banner must not survive a reload (it would report a
              // failure the operator has already retried past).
              const next = new URLSearchParams(searchParams.toString());
              ["provider", "status", "error", "error_reason"].forEach((k) => next.delete(k));
              const qs = next.toString();
              router.replace(qs ? `/settings?${qs}` : "/settings", { scroll: false });
            }}
          />

          {/* ADR-496 D1 — the INBOUND half of this member's own connections.
              An MCP connection is a member's connection (ADR-431 §2:
              `connected_by`), so "what have I connected?" belongs on the
              account door next to the outbound credentials — not only inside a
              workspace-governance roster whose job is governing other people.
              READ-ONLY: governance stays singular in WorkspaceMembersCard.
              Hidden during a connector drill-in so the subsurface stays alone. */}
          {!accountParam.get("connector") && (
            <div className="mt-8 border-t border-border pt-8">
              <h3 className="mb-1 text-sm font-medium">Your AI connections</h3>
              <p className="mb-3 text-xs text-muted-foreground">
                External AI assistants you&apos;ve connected over MCP. Each
                reaches in as itself and writes under your authorization, so a
                connection goes away when you do — and each one reaches ONE
                workspace, so connecting here grants nothing in another.
              </p>
              <WorkspaceMembersCard
                variant="compact"
                scope="mine"
                readOnly
                footer={
                  <SurfaceLink
                    to="workspace-settings"
                    params={{ pane: "members" }}
                    className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                  >
                    Manage access for everyone in the workspace
                    <ArrowRight className="h-3 w-3" />
                  </SurfaceLink>
                }
              />
            </div>
          )}
        </section>
      )}

      {/* Account Tab - Data & Privacy */}
      {pane === "account" && (
        <section className="mb-8">
          <PaneHeader
            icon={Shield}
            title="Data & Privacy"
            subtitle="Your own connections, account reset, and deactivation. Workspace content lives in Workspace Settings."
            bordered={false}
            action={
              <button
                onClick={loadDangerZoneStats}
                disabled={isLoadingDangerStats}
                className="p-2 text-muted-foreground hover:text-foreground"
                title="Refresh stats"
              >
                <RefreshCw className={`w-4 h-4 ${isLoadingDangerStats ? "animate-spin" : ""}`} />
              </button>
            }
          />

          {isLoadingDangerStats ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : dangerStats ? (
            <>
              {/* ADR-476 D3 — workspace-scoped destruction (clear history, clear
                  workspace) lives ONLY in Workspace Settings → Danger Zone, and
                  so do its counts. This door keeps what is genuinely the
                  member's own: their connections, their reset, their
                  deactivation. */}
              {/* ADR-425 §2 + ADR-582 D2 (2026-08-20) — the "Disconnect
                  Platforms" card is DELETED. Disconnecting is a per-connector
                  act on the Connectors pane, which owns its own teardown; a
                  bulk duplicate here cleared a path with zero writers and
                  promised to pause bots that do not exist. */}
              {/* ADR-476 D3 — one line, not a card. A member who comes here
                  looking for the clears must be pointed across; duplicating the
                  cards (or their counts) is what made the two doors disagree. */}
              <p className="text-xs text-muted-foreground mb-6">
                Clearing work history or the whole workspace affects every
                member&apos;s work, so it lives in{" "}
                <SurfaceLink
                  to="workspace-settings"
                  params={{ pane: "danger" }}
                  className="underline"
                >
                  Workspace Settings → Danger Zone
                </SurfaceLink>
                .
              </p>

              {/* Danger Zone */}
              <div className="border-t border-destructive/30 pt-6 mb-6">
                <h3 className="text-sm font-medium text-destructive mb-3 uppercase tracking-wide flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  Danger Zone
                </h3>
                <div className="space-y-3 border border-destructive/40 rounded-lg p-4">
                  {/* Full Data Reset */}
                  <div className="p-4 border border-destructive/30 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium flex items-center gap-2">
                          <RefreshCw className="w-4 h-4" />
                          Full Data Reset
                        </div>
                        <div className="text-sm text-muted-foreground">
                          Delete everything but keep your account active
                        </div>
                      </div>
                      <button
                        onClick={() => initiateDangerAction("reset")}
                        className="px-4 py-2 text-destructive text-sm font-medium hover:underline"
                      >
                        Reset Account
                      </button>
                    </div>
                  </div>

                  {/* Deactivate Account */}
                  <div className="p-4 border border-destructive/30 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium flex items-center gap-2">
                          <LogOut className="w-4 h-4" />
                          Delete Account
                        </div>
                        <div className="text-sm text-muted-foreground">
                          Permanently delete account and all data
                        </div>
                      </div>
                      <button
                        onClick={() => initiateDangerAction("deactivate")}
                        className="px-4 py-2 text-destructive text-sm font-medium hover:underline"
                      >
                        Deactivate
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="text-muted-foreground">Failed to load account stats</div>
          )}

          {/* Notifications (nested under Account) */}
          <div className="mt-8 pt-8 border-t border-border">
            <h3 className="text-base font-semibold mb-4 flex items-center gap-2">
              <Bell className="w-4 h-4" />
              Email Notifications
            </h3>
            {isLoadingNotifications ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
              </div>
            ) : notificationPrefs ? (
              <div className="space-y-3">
                <div className="p-3 border border-border rounded-lg flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Mail className="w-4 h-4 text-muted-foreground" />
                    <div>
                      <div className="text-sm font-medium">Work delivered</div>
                      <div className="text-xs text-muted-foreground">Email when an agent&apos;s output is delivered</div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleNotificationChange({ delivery_email: !notificationPrefs.delivery_email })}
                    disabled={isSavingNotifications}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                      notificationPrefs.delivery_email ? "bg-primary" : "bg-muted"
                    }`}
                  >
                    <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                      notificationPrefs.delivery_email ? "translate-x-4" : "translate-x-0.5"
                    }`} />
                  </button>
                </div>
                <div className="p-3 border border-border rounded-lg flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="w-4 h-4 text-muted-foreground" />
                    <div>
                      <div className="text-sm font-medium">Failures</div>
                      <div className="text-xs text-muted-foreground">Email when a run or delivery fails</div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleNotificationChange({ failure_email: !notificationPrefs.failure_email })}
                    disabled={isSavingNotifications}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                      notificationPrefs.failure_email ? "bg-primary" : "bg-muted"
                    }`}
                  >
                    <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                      notificationPrefs.failure_email ? "translate-x-4" : "translate-x-0.5"
                    }`} />
                  </button>
                </div>
                {/* ADR-489 D4 — the after-witness push dial. The in-app bell
                    is always on (derived); this governs EMAIL about peers'
                    and agents' workspace acts. */}
                <div className="p-3 border border-border rounded-lg flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Bell className="w-4 h-4 text-muted-foreground" />
                    <div>
                      <div className="text-sm font-medium">Workspace activity</div>
                      <div className="text-xs text-muted-foreground">Email when teammates or agents act in the workspace</div>
                    </div>
                  </div>
                  <select
                    value={notificationPrefs.witness_email}
                    onChange={(e) => handleNotificationChange({ witness_email: e.target.value as NotificationPreferences['witness_email'] })}
                    disabled={isSavingNotifications}
                    aria-label="Workspace activity emails"
                    className="h-8 rounded-md border border-border bg-background px-2 text-xs text-foreground"
                  >
                    <option value="high">Urgent only</option>
                    <option value="all">Every action</option>
                    <option value="none">Never</option>
                  </select>
                </div>
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">Failed to load preferences</div>
            )}
          </div>
        </section>
      )}
    </>
  );

  // ADR-341: System Settings mounts the shared SettingsPaneShell (Singular
  // Implementation, ADR-341 D5) with the OS-governance pane set. Modals +
  // toast are fixed-position siblings outside the shell's scroll area.
  return (
    <>
      <SettingsPaneShell
        windowSlug="settings"
        paneGroups={PANE_GROUPS}
        defaultPane="connectors"
        renderPane={renderPane}
      />

      {/* Success Message Toast */}
      {purgeSuccess && (
        <div className="fixed bottom-4 right-4 flex items-center gap-2 px-4 py-3 bg-primary text-primary-foreground rounded-lg shadow-lg z-50">
          <Check className="w-5 h-5" />
          {purgeSuccess}
        </div>
      )}

      {/* Confirmation Modal */}
      {showConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background border border-border rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center gap-3 mb-4">
              <AlertTriangle className="w-6 h-6 text-destructive" />
              <h3 className="text-lg font-semibold">
                {dangerAction === "deactivate" ? "Delete Account Permanently?" :
                 dangerAction === "reset" ? "Full Account Reset?" :
                 "Confirm Deletion"}
              </h3>
            </div>

            <div className="text-muted-foreground mb-6">
              {dangerAction === "reset" && (
                <>
                  <p className="mb-2">
                    Are you sure you want to <strong>reset your entire account</strong>? This will delete:
                  </p>
                  <ul className="list-disc list-inside text-sm space-y-1">
                    <li>{dangerStats?.workspace_files} workspace files</li>
                    <li>{dangerStats?.agents} agents and all scheduled work</li>
                    <li>{dangerStats?.platform_connections} platform connections</li>
                    <li>{dangerStats?.chat_sessions} chat sessions</li>
                    <li>All memories, documents, activity, and sync data</li>
                  </ul>
                  <p className="mt-2 text-sm">
                    Your account stays active with a freshly reset workspace
                    (the default agents and behind-the-scenes setup restored; scheduled
                    work and context start empty).
                  </p>
                </>
              )}
              {dangerAction === "deactivate" && (
                <>
                  <p className="font-medium text-destructive mb-2">
                    This action is PERMANENT and cannot be undone.
                  </p>
                  <p className="mb-2">All your data will be permanently deleted:</p>
                  <ul className="list-disc list-inside text-sm space-y-1">
                    <li>All agents, memories, documents, and chat history</li>
                    <li>All platform connections and synced content</li>
                    <li>Your account will be removed from the system</li>
                  </ul>
                  <p className="mt-2 text-sm">
                    You will be logged out immediately. To use yarnnn again, you would need to create a new account.
                  </p>
                </>
              )}
            </div>

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => {
                  setShowConfirm(false);
                  setDangerAction(null);
                }}
                className="px-4 py-2 border border-border rounded-md"
                disabled={isPurging}
              >
                Cancel
              </button>
              <button
                onClick={handleDangerAction}
                disabled={isPurging}
                className="px-4 py-2 text-destructive text-sm font-medium hover:underline flex items-center gap-2 disabled:opacity-50"
              >
                {isPurging && <Loader2 className="w-4 h-4 animate-spin" />}
                {isPurging
                  ? "Processing..."
                  : dangerAction === "deactivate"
                  ? "Deactivate Account"
                  : dangerAction === "reset"
                  ? "Reset Account"
                  : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
