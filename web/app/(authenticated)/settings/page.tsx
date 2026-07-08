"use client";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  AlertTriangle,
  Loader2,
  Check,
  User,
  FileText,
  RefreshCw,
  LogOut,
  Bell,
  Mail,
  Link2,
  Shield,
  FolderKanban,
  Database,
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

interface DangerZoneStats {
  workspace_files: number;
  agents: number;
  tasks: number;
  chat_sessions: number;
  platform_connections: number;
  // ADR-158: files under /workspace/context/{slack,notion,github}/
  platform_context_files: number;
  // Phase 3 (L1): count of past task runs — drives the "Clear Work History" card.
  agent_runs: number;
  // ADR-194 Reviewer queue — pending proposals; surfaced so L2/L4 confirmation
  // copy can tell the user what gets discarded.
  action_proposals: number;
}

interface NotificationPreferences {
  email_agent_ready: boolean;
  email_agent_failed: boolean;
}

// The `settings` surface is the ACCOUNT window — genuinely user_id-scoped, the
// human/principal's concern (data & privacy, danger zone). ADR-416 follow-on
// (2026-07-08): Billing + Usage MOVED OUT to Workspace Settings — both are
// WORKSPACE-scoped (the workspace is the billing unit, ADR-416; getLimits /
// getUsageDetail key on the acting workspace_id, migration 200). This supersedes
// ADR-347's account-door placement, which predated the ADR-416 billing-unit
// ratification. The account door now holds only Account.
type SettingsTab = "account";

const PANE_GROUPS: PaneGroup[] = [
  {
    label: "Account",
    panes: [{ key: "account", label: "Account", icon: User }],
  },
];

const ALL_PANES: SettingsTab[] = PANE_GROUPS.flatMap((g) => g.panes.map((p) => p.key as SettingsTab));
type DangerAction =
  | "work-history"
  | "workspace"
  | "integrations"
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
  const activeTab: SettingsTab = ALL_PANES.includes(requestedPane as SettingsTab)
    ? (requestedPane as SettingsTab)
    : "account";

  // ADR-215 R3: legacy `/settings?tab=memory` redirects to Files with
  // IDENTITY.md preselected. One edit surface for substrate (Files).
  // ADR-358: foreground the Files window (navigateToSurface) rather than
  // hard-navigating off the /desktop baseline.
  useEffect(() => {
    if (tabParam === "memory") {
      navigateToSurface("files", { path: "/workspace/context/_shared/IDENTITY.md" });
    }
  }, [tabParam, navigateToSurface]);

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
      const prefs = await api.account.getNotificationPreferences();
      setNotificationPrefs(prefs);
    } catch (err) {
      console.error("Failed to fetch notification preferences:", err);
    } finally {
      setIsLoadingNotifications(false);
    }
  };

  const handleNotificationToggle = async (key: keyof NotificationPreferences, value: boolean) => {
    if (!notificationPrefs) return;

    // Optimistic update
    setNotificationPrefs({ ...notificationPrefs, [key]: value });
    setIsSavingNotifications(true);

    try {
      const updated = await api.account.updateNotificationPreferences({ [key]: value });
      setNotificationPrefs(updated);
    } catch (err) {
      console.error("Failed to update notification preference:", err);
      // Revert on error
      setNotificationPrefs({ ...notificationPrefs, [key]: !value });
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
        case "work-history":
          result = await api.account.clearWorkHistory();
          setPurgeSuccess(result.message);
          // No reinit needed (L1 invariants don't include anything purged here).
          // No route change — the user stays on Settings to see the success
          // banner. Their tasks are still active and their next scheduled run
          // will populate fresh outputs.
          break;
        case "workspace":
          result = await api.account.clearWorkspace();
          setPurgeSuccess(result.message);
          clearMessages();
          // Backend now re-scaffolds transactionally (ADR-140/151/161/164 invariants).
          // This call is a harmless safety net; it returns the already-restored state.
          await api.workspace.getState().catch(() => null);
          // Route to /chat so TP greets the user and triggers the onboarding
          // modal (identity is empty/sparse after purge). Previously routed to
          // /work which skipped onboarding entirely.
          // ADR-297 D19.4 — foreground a surface (window-open), not
          // router.push (which erases the Desktop). ADR-415 (2026-07-08): land
          // on Home — the composition front page whose constitution band is the
          // activation CTA (identity sparse after purge). Was 'channels' (the
          // dissolved perception surface).
          setTimeout(() => navigateToSurface('home'), 1500);
          break;
        case "integrations":
          result = await api.account.clearIntegrations();
          setPurgeSuccess(result.message);
          break;
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
          // router.push (which erases the Desktop). ADR-415 (2026-07-08): land
          // on Home — the composition front page whose constitution band is the
          // activation CTA (identity sparse after full reset). Was 'channels'.
          setTimeout(() => navigateToSurface('home'), 1500);
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
      {/* Billing + Usage moved to Workspace Settings (ADR-416 follow-on,
          2026-07-08) — workspace-scoped money. This door is Account only. */}

      {/* Account Tab - Data & Privacy */}
      {pane === "account" && (
        <section className="mb-8">
          <PaneHeader
            icon={Shield}
            title="Data & Privacy"
            subtitle="Manage your data and privacy settings. All deletions are permanent."
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
              {/* Data Summary Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="p-4 border border-border rounded-lg text-center">
                  <FolderKanban className="w-5 h-5 mx-auto mb-2 text-muted-foreground" />
                  <div className="text-2xl font-bold">{dangerStats.tasks}</div>
                  <div className="text-xs text-muted-foreground">Scheduled work</div>
                </div>
                <div className="p-4 border border-border rounded-lg text-center">
                  <Database className="w-5 h-5 mx-auto mb-2 text-muted-foreground" />
                  <div className="text-2xl font-bold">{dangerStats.agents}</div>
                  <div className="text-xs text-muted-foreground">Agents</div>
                </div>
                <div className="p-4 border border-border rounded-lg text-center">
                  <FileText className="w-5 h-5 mx-auto mb-2 text-muted-foreground" />
                  <div className="text-2xl font-bold">{dangerStats.workspace_files}</div>
                  <div className="text-xs text-muted-foreground">Workspace files</div>
                </div>
                <div className="p-4 border border-border rounded-lg text-center">
                  <Link2 className="w-5 h-5 mx-auto mb-2 text-muted-foreground" />
                  <div className="text-2xl font-bold">{dangerStats.platform_connections}</div>
                  <div className="text-xs text-muted-foreground">Platforms</div>
                </div>
              </div>

              {/* Purge Actions — graduated severity L1→L3 */}
              <div className="border-t border-border pt-6 space-y-3 mb-6">
                {/* L1: Clear Work History — lightest layer, no agent/task loss */}
                <div className="p-4 border border-amber-200 dark:border-amber-900/50 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium flex items-center gap-2">
                        <History className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                        Clear Work History
                      </div>
                      <div className="text-sm text-muted-foreground">
                        Delete {dangerStats.agent_runs} past run records and all dated output folders. Scheduled work, agents, identity, and accumulated context are preserved.
                      </div>
                    </div>
                    <button
                      onClick={() => initiateDangerAction("work-history")}
                      disabled={dangerStats.agent_runs === 0}
                      className="px-4 py-2 text-amber-700 dark:text-amber-400 border border-amber-300 dark:border-amber-700 rounded-md text-sm font-medium hover:bg-amber-50 dark:hover:bg-amber-950/40 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      Clear History
                    </button>
                  </div>
                </div>

                {/* L2: Clear Workspace — heavier, wipes agents+tasks but reinit restores roster */}
                <div className="p-4 border border-orange-200 dark:border-orange-900/50 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium flex items-center gap-2">
                        <Database className="w-4 h-4 text-orange-600 dark:text-orange-400" />
                        Clear Workspace
                      </div>
                      <div className="text-sm text-muted-foreground">
                        Delete {dangerStats.agents} agents, {dangerStats.workspace_files} workspace files, {dangerStats.action_proposals} pending proposals, and all activity
                      </div>
                    </div>
                    <button
                      onClick={() => initiateDangerAction("workspace")}
                      disabled={dangerStats.workspace_files === 0 && dangerStats.agents === 0 && dangerStats.action_proposals === 0}
                      className="px-4 py-2 text-orange-700 dark:text-orange-400 border border-orange-300 dark:border-orange-700 rounded-md text-sm font-medium hover:bg-orange-50 dark:hover:bg-orange-950/40 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      Clear
                    </button>
                  </div>
                </div>

                {/* L3: Disconnect Platforms — pauses bots, clears platform context dirs */}
                <div className="p-4 border border-orange-200 dark:border-orange-900/50 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium flex items-center gap-2">
                        <Link2 className="w-4 h-4 text-orange-600 dark:text-orange-400" />
                        Disconnect Platforms
                      </div>
                      <div className="text-sm text-muted-foreground">
                        Disconnect {dangerStats.platform_connections} platforms and clear {dangerStats.platform_context_files} synced context files
                      </div>
                    </div>
                    <button
                      onClick={() => initiateDangerAction("integrations")}
                      disabled={dangerStats.platform_connections === 0 && dangerStats.platform_context_files === 0}
                      className="px-4 py-2 text-orange-700 dark:text-orange-400 border border-orange-300 dark:border-orange-700 rounded-md text-sm font-medium hover:bg-orange-50 dark:hover:bg-orange-950/40 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      Disconnect
                    </button>
                  </div>
                </div>
              </div>

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
                      <div className="text-sm font-medium">Agent Ready</div>
                      <div className="text-xs text-muted-foreground">Notified when a scheduled agent is ready</div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleNotificationToggle("email_agent_ready", !notificationPrefs.email_agent_ready)}
                    disabled={isSavingNotifications}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                      notificationPrefs.email_agent_ready ? "bg-primary" : "bg-muted"
                    }`}
                  >
                    <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                      notificationPrefs.email_agent_ready ? "translate-x-4" : "translate-x-0.5"
                    }`} />
                  </button>
                </div>
                <div className="p-3 border border-border rounded-lg flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="w-4 h-4 text-muted-foreground" />
                    <div>
                      <div className="text-sm font-medium">Agent Failed</div>
                      <div className="text-xs text-muted-foreground">Notified when an agent fails to generate</div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleNotificationToggle("email_agent_failed", !notificationPrefs.email_agent_failed)}
                    disabled={isSavingNotifications}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                      notificationPrefs.email_agent_failed ? "bg-primary" : "bg-muted"
                    }`}
                  >
                    <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                      notificationPrefs.email_agent_failed ? "translate-x-4" : "translate-x-0.5"
                    }`} />
                  </button>
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
        defaultPane="account"
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
                 dangerAction === "work-history" ? "Clear Work History?" :
                 "Confirm Deletion"}
              </h3>
            </div>

            <div className="text-muted-foreground mb-6">
              {dangerAction === "work-history" && (
                <>
                  <p className="mb-2">
                    Are you sure you want to <strong>clear your work history</strong>? This will delete:
                  </p>
                  <ul className="list-disc list-inside text-sm space-y-1">
                    <li>{dangerStats?.agent_runs} past invocation records</li>
                    <li>All dated output folders under <code>/workspace/operation/reports/&lt;slug&gt;/</code> (every past deliverable)</li>
                    <li>The run log for each scheduled item (re-created on the next run)</li>
                  </ul>
                  <p className="mt-2 text-sm">
                    <strong>Preserved:</strong> all your scheduled work, all agents, your identity, brand, and mandate, accumulated context, chat history, platform connections, and your saved feedback and intent. The next scheduled run will produce fresh outputs.
                  </p>
                </>
              )}
              {dangerAction === "workspace" && (
                <>
                  <p className="mb-2">
                    Are you sure you want to <strong>clear your workspace</strong>? This will delete:
                  </p>
                  <ul className="list-disc list-inside text-sm space-y-1">
                    <li>{dangerStats?.agents} agents and all their runs</li>
                    <li>{dangerStats?.workspace_files} workspace files (memory, context, outputs, scheduled work)</li>
                    <li>All scheduled work, activity history, and budget records</li>
                  </ul>
                  <p className="mt-2 text-sm">
                    Your workspace will be reset to a fresh state: the default agents,
                    your identity and brand templates, and the behind-the-scenes setup.
                    Scheduled work and context start empty — you set them up in chat.
                    Platform connections stay intact.
                  </p>
                </>
              )}
              {dangerAction === "integrations" && (
                <>
                  <p className="mb-2">
                    Are you sure you want to <strong>disconnect all platforms</strong>? This will:
                  </p>
                  <ul className="list-disc list-inside text-sm space-y-1">
                    <li>Disconnect {dangerStats?.platform_connections} connected platforms</li>
                    <li>Delete OAuth tokens (you&apos;ll need to reconnect)</li>
                    <li>Clear {dangerStats?.platform_context_files} synced context files (Slack / Notion / GitHub)</li>
                    <li>Pause platform-bot agents (reconnecting will reactivate them)</li>
                  </ul>
                </>
              )}
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
