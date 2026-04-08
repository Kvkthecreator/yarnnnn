"use client";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  Settings,
  Brain,
  AlertTriangle,
  Loader2,
  Check,
  User,
  CreditCard,
  BarChart3,
  FileText,
  RefreshCw,
  LogOut,
  Bell,
  Mail,
  Link2,
  Shield,
  FolderKanban,
  Package,
  Database,
  History,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { SubscriptionCard } from "@/components/subscription/SubscriptionCard";
import { createClient } from "@/lib/supabase/client";
import { useTP } from "@/contexts/TPContext";
import { MemorySection } from "@/components/settings/MemorySection";
import { SystemSection } from "@/components/settings/SystemSection";
import { ConnectedIntegrationsSection } from "@/components/settings/ConnectedIntegrationsSection";

interface DangerZoneStats {
  workspace_files: number;
  agents: number;
  projects: number;
  chat_sessions: number;
  platform_connections: number;
  // ADR-158: files under /workspace/context/{slack,notion,github}/
  platform_context_files: number;
  // Phase 3 (L1): count of past task runs — drives the "Clear Work History" card.
  agent_runs: number;
}

interface NotificationPreferences {
  email_agent_ready: boolean;
  email_agent_failed: boolean;
}

type SettingsTab = "billing" | "usage" | "memory" | "system" | "connectors" | "account";
type DangerAction =
  | "work-history"
  | "workspace"
  | "integrations"
  | "reset"
  | "deactivate"
  | null;

export default function SettingsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { clearMessages } = useTP();
  const tabParam = searchParams.get("tab");
  const initialTab: SettingsTab =
    tabParam === "usage" ? "usage" :
    tabParam === "memory" ? "memory" :
    tabParam === "system" ? "system" :
    tabParam === "connectors" ? "connectors" :
    tabParam === "account" ? "account" :
    "billing";
  const subscriptionSuccess = searchParams.get("subscription") === "success";

  const [activeTab, setActiveTab] = useState<SettingsTab>(initialTab);
  const [dangerStats, setDangerStats] = useState<DangerZoneStats | null>(null);
  const [isLoadingDangerStats, setIsLoadingDangerStats] = useState(false);
  const [isPurging, setIsPurging] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [dangerAction, setDangerAction] = useState<DangerAction>(null);
  const [purgeSuccess, setPurgeSuccess] = useState<string | null>(null);
  const [showSubscriptionSuccess, setShowSubscriptionSuccess] = useState(subscriptionSuccess);

  // Notification preferences state
  const [notificationPrefs, setNotificationPrefs] = useState<NotificationPreferences | null>(null);
  const [isLoadingNotifications, setIsLoadingNotifications] = useState(false);
  const [isSavingNotifications, setIsSavingNotifications] = useState(false);

  // Usage metrics state
  const [usageMetrics, setUsageMetrics] = useState<{
    agents: number;
    documents: number;
    platforms: { connected: number; total: number };
    facts: number;
  } | null>(null);
  const [isLoadingUsage, setIsLoadingUsage] = useState(false);

  // Usage limits state (moved from SubscriptionCard — ADR-100)
  const [limits, setLimits] = useState<Awaited<ReturnType<typeof api.integrations.getLimits>> | null>(null);
  const [limitsLoading, setLimitsLoading] = useState(false);

  // Fetch usage metrics + limits when usage tab is active
  useEffect(() => {
    if (activeTab === "usage") {
      if (!usageMetrics) loadUsageMetrics();
      if (!limits) loadLimits();
    }
  }, [activeTab, usageMetrics, limits]);

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

  const loadUsageMetrics = async () => {
    setIsLoadingUsage(true);
    try {
      // Fetch counts from various endpoints in parallel
      const [agents, documents, summary, facts] = await Promise.all([
        api.agents.list().catch(() => []),
        api.documents.list().catch(() => ({ documents: [] })),
        api.integrations.getSummary().catch(() => ({ platforms: [] })),
        api.userMemories.list().catch(() => []),
      ]);

      const activePlatforms = new Set(
        (summary.platforms || [])
          .filter((p: { status: string }) => p.status === "active")
          .map((p: { provider: string }) => p.provider)
      );

      const connectedCount = ["slack", "notion", "github"].filter((p) =>
        activePlatforms.has(p)
      ).length;

      setUsageMetrics({
        agents: Array.isArray(agents) ? agents.length : 0,
        documents: documents.documents?.length || 0,
        platforms: {
          connected: connectedCount,
          total: 2, // Slack, Notion
        },
        facts: Array.isArray(facts) ? facts.length : 0,
      });
    } catch (err) {
      console.error("Failed to fetch usage metrics:", err);
    } finally {
      setIsLoadingUsage(false);
    }
  };

  const loadLimits = async () => {
    setLimitsLoading(true);
    try {
      const data = await api.integrations.getLimits();
      setLimits(data);
    } catch (err) {
      console.error("Failed to fetch limits:", err);
    } finally {
      setLimitsLoading(false);
    }
  };

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
          await api.onboarding.getState().catch(() => null);
          // Route to /work (ADR-167 list-mode landing): the three essential tasks
          // are immediately visible in the list, giving the user concrete proof
          // their re-scaffolded workspace is alive. Pre-ADR-167 we routed to
          // /context because /work auto-selected and felt jarring; now /work is
          // a meaningful list surface and the better landing.
          setTimeout(() => router.push('/work'), 1500);
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
          await api.onboarding.getState().catch(() => null);
          // Route to /work (ADR-167 list-mode landing): the three essential tasks
          // are immediately visible in the list, giving the user concrete proof
          // their re-scaffolded workspace is alive.
          setTimeout(() => router.push('/work'), 1500);
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

  // Auto-dismiss subscription success message
  useEffect(() => {
    if (showSubscriptionSuccess) {
      const timer = setTimeout(() => setShowSubscriptionSuccess(false), 5000);
      return () => clearTimeout(timer);
    }
  }, [showSubscriptionSuccess]);

  // Auto-dismiss purge success
  useEffect(() => {
    if (purgeSuccess) {
      const timer = setTimeout(() => setPurgeSuccess(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [purgeSuccess]);

  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="flex items-center gap-3 mb-6">
        <Settings className="w-6 h-6" />
        <h1 className="text-2xl font-bold">Settings</h1>
      </div>

      {/* Subscription Success Banner */}
      {showSubscriptionSuccess && (
        <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg flex items-center gap-3">
          <Check className="w-5 h-5 text-green-600" />
          <div>
            <p className="font-medium text-green-800 dark:text-green-200">
              Subscription activated!
            </p>
            <p className="text-sm text-green-700 dark:text-green-300">
              Your subscription is now active. Enjoy expanded sources, faster syncs, and more agents.
            </p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-8 border-b border-border overflow-x-auto">
        <button
          onClick={() => setActiveTab("billing")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === "billing"
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <span className="flex items-center gap-2">
            <CreditCard className="w-4 h-4" />
            Billing
          </span>
        </button>
        <button
          onClick={() => setActiveTab("usage")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === "usage"
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <span className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4" />
            Usage
          </span>
        </button>
        <button
          onClick={() => setActiveTab("memory")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === "memory"
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <span className="flex items-center gap-2">
            <Brain className="w-4 h-4" />
            Profile
          </span>
        </button>
        <button
          onClick={() => setActiveTab("system")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === "system"
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <span className="flex items-center gap-2">
            <Database className="w-4 h-4" />
            System
          </span>
        </button>
        <button
          onClick={() => setActiveTab("connectors")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === "connectors"
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <span className="flex items-center gap-2">
            <Link2 className="w-4 h-4" />
            Connectors
          </span>
        </button>
        <button
          onClick={() => setActiveTab("account")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === "account"
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <span className="flex items-center gap-2">
            <User className="w-4 h-4" />
            Account
          </span>
        </button>
      </div>

      {/* Billing Tab */}
      {activeTab === "billing" && (
        <section className="mb-8">
          <SubscriptionCard />
        </section>
      )}

      {/* Usage Tab */}
      {activeTab === "usage" && (
        <section className="mb-8 space-y-6">
          <div>
            <h2 className="text-lg font-semibold mb-1 flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              Usage & Limits
            </h2>
            <p className="text-sm text-muted-foreground">
              Your current usage against plan limits.
            </p>
          </div>

          {limitsLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground p-4">
              <Loader2 className="w-4 h-4 animate-spin" />
              Loading usage...
            </div>
          ) : limits ? (
            <>
              {/* Work Credits — the primary meter */}
              <div className="p-4 border border-border rounded-lg space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium">Work Credits</h3>
                  <span className="text-sm text-muted-foreground">
                    {limits.usage.credits_used} / {limits.limits.monthly_credits} this month
                  </span>
                </div>
                {(() => {
                  const percent = Math.min(100, Math.round((limits.usage.credits_used / Math.max(1, limits.limits.monthly_credits)) * 100));
                  return (
                    <>
                      <div className="h-2 rounded-full bg-muted overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${percent >= 90 ? "bg-destructive" : percent >= 70 ? "bg-yellow-500" : "bg-primary"}`}
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Task run = 3 credits, Render = 1 credit. {limits.limits.monthly_credits - limits.usage.credits_used} credits remaining.
                      </p>
                    </>
                  );
                })()}
              </div>

              {/* Chat — only shown for Free tier */}
              {limits.limits.monthly_messages !== -1 && (
                <div className="p-4 border border-border rounded-lg space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="font-medium">Chat Messages</h3>
                    <span className="text-sm text-muted-foreground">
                      {limits.usage.monthly_messages_used} / {limits.limits.monthly_messages} this month
                    </span>
                  </div>
                  {(() => {
                    const percent = Math.min(100, Math.round((limits.usage.monthly_messages_used / Math.max(1, limits.limits.monthly_messages)) * 100));
                    return (
                      <div className="h-2 rounded-full bg-muted overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${percent >= 90 ? "bg-destructive" : percent >= 70 ? "bg-yellow-500" : "bg-primary"}`}
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                    );
                  })()}
                  <p className="text-xs text-muted-foreground">
                    Upgrade to Pro for unlimited chat.
                  </p>
                </div>
              )}

              {/* Other limits */}
              <div className="p-4 border border-border rounded-lg space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium">Plan details</h3>
                  <span className="text-xs text-muted-foreground">
                    Sync: {({ "1x_daily": "1x daily", "2x_daily": "2x daily", "4x_daily": "4x daily", "hourly": "Hourly" } as Record<string, string>)[limits.limits.sync_frequency] || limits.limits.sync_frequency}
                  </span>
                </div>
                {[
                  { label: "Active tasks", used: limits.usage.active_tasks, limit: limits.limits.active_tasks },
                  { label: "Slack sources", used: limits.usage.slack_channels, limit: limits.limits.slack_channels },
                  { label: "Notion pages", used: limits.usage.notion_pages, limit: limits.limits.notion_pages },
                ].map((row) => {
                  const formatUsage = (used: number, limit: number) =>
                    limit === -1 ? `${used} / Unlimited` : `${used} / ${limit}`;
                  return (
                    <div key={row.label} className="flex items-center justify-between text-sm">
                      <span>{row.label}</span>
                      <span className="text-muted-foreground">{formatUsage(row.used, row.limit)}</span>
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
              <p className="text-sm text-muted-foreground">Unable to load usage data.</p>
          )}
        </section>
      )}

      {/* Memory Tab */}
      {activeTab === "memory" && (
        <section className="mb-8">
          <MemorySection />
        </section>
      )}

      {/* System Tab */}
      {activeTab === "system" && (
        <section className="mb-8">
          <SystemSection />
        </section>
      )}

      {/* Notifications Tab */}
      {/* Connectors Tab — platform connections (ADR-133: moved from Workspace) */}
      {activeTab === "connectors" && (
        <ConnectedIntegrationsSection
          title="Connectors"
          description="Connect platforms to give your agents data. Platforms are infrastructure — connect once, agents read automatically."
          redirectTo="/settings?tab=connectors"
        />
      )}

      {/* Account Tab - Data & Privacy */}
      {activeTab === "account" && (
        <section className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Shield className="w-5 h-5" />
              Data & Privacy
            </h2>
            <button
              onClick={loadDangerZoneStats}
              disabled={isLoadingDangerStats}
              className="p-2 text-muted-foreground hover:text-foreground"
              title="Refresh stats"
            >
              <RefreshCw className={`w-4 h-4 ${isLoadingDangerStats ? "animate-spin" : ""}`} />
            </button>
          </div>
          <p className="text-sm text-muted-foreground mb-6">
            Manage your data and privacy settings. All deletions are permanent.
          </p>

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
                  <div className="text-2xl font-bold">{dangerStats.agents}</div>
                  <div className="text-xs text-muted-foreground">Tasks</div>
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

              {/* Purge Actions */}
              <div className="border-t border-border pt-6 space-y-3 mb-6">
                {/* L1: Clear Work History — lightest layer, no agent/task loss */}
                <div className="p-4 border border-border rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium flex items-center gap-2">
                        <History className="w-4 h-4" />
                        Clear Work History
                      </div>
                      <div className="text-sm text-muted-foreground">
                        Delete {dangerStats.agent_runs} past run records and all task output folders. Tasks, agents, identity, and accumulated context are preserved.
                      </div>
                    </div>
                    <button
                      onClick={() => initiateDangerAction("work-history")}
                      disabled={dangerStats.agent_runs === 0}
                      className="px-4 py-2 text-muted-foreground border border-border rounded-md text-sm font-medium hover:text-foreground hover:border-foreground/30 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Clear History
                    </button>
                  </div>
                </div>

                {/* L2: Clear Workspace — heavier, wipes agents+tasks but reinit restores roster */}
                <div className="p-4 border border-border rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium flex items-center gap-2">
                        <Database className="w-4 h-4" />
                        Clear Workspace
                      </div>
                      <div className="text-sm text-muted-foreground">
                        Delete {dangerStats.agents} agents, {dangerStats.workspace_files} workspace files, and all activity
                      </div>
                    </div>
                    <button
                      onClick={() => initiateDangerAction("workspace")}
                      disabled={dangerStats.workspace_files === 0 && dangerStats.agents === 0}
                      className="px-4 py-2 text-muted-foreground border border-border rounded-md text-sm font-medium hover:text-foreground hover:border-foreground/30 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Clear
                    </button>
                  </div>
                </div>

                {/* Disconnect Platforms */}
                <div className="p-4 border border-border rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium flex items-center gap-2">
                        <Link2 className="w-4 h-4" />
                        Disconnect Platforms
                      </div>
                      <div className="text-sm text-muted-foreground">
                        Disconnect {dangerStats.platform_connections} platforms and clear {dangerStats.platform_context_files} synced context files
                      </div>
                    </div>
                    <button
                      onClick={() => initiateDangerAction("integrations")}
                      disabled={dangerStats.platform_connections === 0 && dangerStats.platform_context_files === 0}
                      className="px-4 py-2 text-muted-foreground border border-border rounded-md text-sm font-medium hover:text-foreground hover:border-foreground/30 disabled:opacity-50 disabled:cursor-not-allowed"
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
                        className="px-4 py-2 bg-destructive text-destructive-foreground rounded-md text-sm font-medium hover:bg-destructive/90"
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
                        className="px-4 py-2 bg-destructive text-destructive-foreground rounded-md text-sm font-medium hover:bg-destructive/90"
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
                    <li>{dangerStats?.agent_runs} past task run records</li>
                    <li>All <code>/tasks/&lt;slug&gt;/outputs/</code> folders (every past deliverable)</li>
                    <li>All <code>/tasks/&lt;slug&gt;/memory/_run_log.md</code> files (re-created on next run)</li>
                  </ul>
                  <p className="mt-2 text-sm">
                    <strong>Preserved:</strong> all tasks, all agents, identity/brand, accumulated context (Competitive Intelligence, Market, etc.), chat sessions, platform connections, agent learning files (steering, feedback, reflections). Your next scheduled task fire will populate fresh outputs.
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
                    <li>{dangerStats?.workspace_files} workspace files (memory, context, outputs)</li>
                    <li>All tasks, activity history, and work budget records</li>
                  </ul>
                  <p className="mt-2 text-sm">
                    Your workspace will be re-scaffolded to a fresh state: default agent roster,
                    context domains, identity/brand templates, and the essential daily-update task.
                    Platform connections remain intact.
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
                    <li>{dangerStats?.agents} agents and all tasks</li>
                    <li>{dangerStats?.platform_connections} platform connections</li>
                    <li>{dangerStats?.chat_sessions} chat sessions</li>
                    <li>All memories, documents, activity, and sync data</li>
                  </ul>
                  <p className="mt-2 text-sm">
                    Your account will remain active with a freshly re-scaffolded workspace
                    (default agents, context domains, and essential tasks restored).
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
                className="px-4 py-2 bg-destructive text-destructive-foreground rounded-md flex items-center gap-2"
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

    </div>
  );
}
