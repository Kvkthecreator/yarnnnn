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
  MessageSquare,
  FileText,
  RefreshCw,
  LogOut,
  Bell,
  Mail,
  Link2,
  Shield,
  Package,
  Database,
  Briefcase,
  Sparkles,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { SubscriptionCard } from "@/components/subscription/SubscriptionCard";
import { createClient } from "@/lib/supabase/client";
import { useTP } from "@/contexts/TPContext";

// ADR-039: MemoryStats removed - stats now shown in Context page

interface DangerZoneStats {
  // Tier 1: Individual data types
  chat_sessions: number;
  memories: number;
  documents: number;
  work_tickets: number;
  // Content subtotals
  deliverables: number;
  deliverable_versions: number;
  work_outputs: number;
  // Platform content (ADR-072)
  platform_content: number;
  // Integrations
  platform_connections: number;
  integration_import_jobs: number;
  export_logs: number;
  // Hierarchy
  workspaces: number;
}

interface NotificationPreferences {
  email_deliverable_ready: boolean;
  email_deliverable_failed: boolean;
  email_work_complete: boolean;
  email_weekly_digest: boolean;
  email_suggestion_created: boolean; // ADR-060
}

// ADR-039: Removed "memory" tab - facts now live in unified Context page
type SettingsTab = "billing" | "usage" | "notifications" | "account";
type DangerAction =
  // Tier 1: Selective purge
  | "chat"
  | "memories"
  | "documents"
  | "work"
  // Tier 2: Category reset
  | "content"
  | "context"
  | "integrations"
  // Tier 3: Full actions
  | "reset"
  | "deactivate"
  | null;

export default function SettingsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { clearMessages } = useTP();
  const tabParam = searchParams.get("tab");
  // ADR-039: memory tab removed - redirect to Context page
  const initialTab: SettingsTab =
    tabParam === "usage" ? "usage" :
    tabParam === "notifications" ? "notifications" :
    tabParam === "account" ? "account" :
    "billing";
  const subscriptionSuccess = searchParams.get("subscription") === "success";

  const [activeTab, setActiveTab] = useState<SettingsTab>(initialTab);
  // ADR-039: Memory stats removed - now in Context page
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
    deliverables: number;
    documents: number;
    platforms: { connected: number; total: number };
    facts: number;
  } | null>(null);
  const [isLoadingUsage, setIsLoadingUsage] = useState(false);

  // Fetch usage metrics when usage tab is active
  useEffect(() => {
    if (activeTab === "usage" && !usageMetrics) {
      loadUsageMetrics();
    }
  }, [activeTab, usageMetrics]);

  // Fetch danger zone stats when account tab is active
  useEffect(() => {
    if (activeTab === "account") {
      loadDangerZoneStats();
    }
  }, [activeTab]);

  // Fetch notification preferences when notifications tab is active
  useEffect(() => {
    if (activeTab === "notifications" && !notificationPrefs) {
      loadNotificationPreferences();
    }
  }, [activeTab, notificationPrefs]);

  const loadUsageMetrics = async () => {
    setIsLoadingUsage(true);
    try {
      // Fetch counts from various endpoints in parallel
      const [deliverables, documents, summary, facts] = await Promise.all([
        api.deliverables.list().catch(() => []),
        api.documents.list().catch(() => ({ documents: [] })),
        api.integrations.getSummary().catch(() => ({ platforms: [] })),
        api.userMemories.list().catch(() => []),
      ]);

      const activePlatforms = new Set(
        (summary.platforms || [])
          .filter((p: { status: string }) => p.status === "active")
          .map((p: { provider: string }) => p.provider)
      );

      // Backward-compatibility for older payloads that may still emit "google".
      if (activePlatforms.has("google")) {
        activePlatforms.add("gmail");
        activePlatforms.add("calendar");
      }

      const connectedCount = ["slack", "gmail", "notion", "calendar"].filter((p) =>
        activePlatforms.has(p)
      ).length;

      setUsageMetrics({
        deliverables: Array.isArray(deliverables) ? deliverables.length : 0,
        documents: documents.documents?.length || 0,
        platforms: {
          connected: connectedCount,
          total: 4, // Slack, Gmail, Notion, Calendar
        },
        facts: Array.isArray(facts) ? facts.length : 0,
      });
    } catch (err) {
      console.error("Failed to fetch usage metrics:", err);
    } finally {
      setIsLoadingUsage(false);
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
        // Tier 1: Selective purge
        case "chat":
          result = await api.account.clearChatHistory();
          setPurgeSuccess(result.message);
          // Clear TP chat state so stale messages don't persist
          clearMessages();
          break;
        case "memories":
          result = await api.account.clearMemories();
          setPurgeSuccess(result.message);
          break;
        case "documents":
          result = await api.account.clearDocuments();
          setPurgeSuccess(result.message);
          break;
        case "work":
          result = await api.account.clearWork();
          setPurgeSuccess(result.message);
          break;
        // Tier 2: Category reset
        case "content":
          result = await api.account.clearContent();
          setPurgeSuccess(result.message);
          break;
        case "context":
          result = await api.account.clearContext();
          setPurgeSuccess(result.message);
          // Clear TP chat state (context includes chat sessions)
          clearMessages();
          break;
        case "integrations":
          result = await api.account.clearIntegrations();
          setPurgeSuccess(result.message);
          break;
        // Tier 3: Full actions
        case "reset":
          result = await api.account.resetAccount();
          setPurgeSuccess(result.message);
          // Clear TP chat state before redirect
          clearMessages();
          // Redirect to dashboard after reset
          setTimeout(() => router.push("/dashboard"), 2000);
          break;
        case "deactivate":
          result = await api.account.deactivateAccount();
          setPurgeSuccess(result.message);
          // Sign out and redirect
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
              Your subscription is now active. Enjoy expanded sources, faster syncs, and more deliverables.
            </p>
          </div>
        </div>
      )}

      {/* Tabs - ADR-039: Memory tab removed, now in Context page */}
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
          onClick={() => setActiveTab("notifications")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === "notifications"
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <span className="flex items-center gap-2">
            <Bell className="w-4 h-4" />
            Notifications
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
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            Usage Overview
          </h2>
          <p className="text-sm text-muted-foreground mb-6">
            Your current usage across yarnnn.
          </p>

          {isLoadingUsage ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : usageMetrics ? (
            <div className="grid grid-cols-2 gap-4">
              {/* Deliverables */}
              <div className="p-4 border border-border rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Package className="w-4 h-4 text-primary" />
                  <h3 className="font-medium">Deliverables</h3>
                </div>
                <p className="text-2xl font-semibold">{usageMetrics.deliverables}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {usageMetrics.deliverables === 1 ? "Active deliverable" : "Active deliverables"}
                </p>
              </div>

              {/* Platforms */}
              <div className="p-4 border border-border rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Link2 className="w-4 h-4 text-primary" />
                  <h3 className="font-medium">Connected Platforms</h3>
                </div>
                <p className="text-2xl font-semibold">
                  {usageMetrics.platforms.connected}
                  <span className="text-sm font-normal text-muted-foreground">
                    /{usageMetrics.platforms.total}
                  </span>
                </p>
                <p className="text-xs text-muted-foreground mt-1">Connected platforms</p>
              </div>

              {/* Documents */}
              <div className="p-4 border border-border rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <FileText className="w-4 h-4 text-primary" />
                  <h3 className="font-medium">Documents</h3>
                </div>
                <p className="text-2xl font-semibold">{usageMetrics.documents}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {usageMetrics.documents === 1 ? "Uploaded document" : "Uploaded documents"}
                </p>
              </div>

              {/* Facts */}
              <div className="p-4 border border-border rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Brain className="w-4 h-4 text-primary" />
                  <h3 className="font-medium">Facts</h3>
                </div>
                <p className="text-2xl font-semibold">{usageMetrics.facts}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {usageMetrics.facts === 1 ? "Stored fact" : "Stored facts"}
                </p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Unable to load usage data.</p>
          )}

          {/* Link to Context page */}
          <div className="mt-6 p-4 bg-muted/30 rounded-lg">
            <p className="text-sm text-muted-foreground">
              Manage your context sources in the{" "}
              <a href="/context" className="text-primary hover:underline">Context page</a>.
            </p>
          </div>
        </section>
      )}

      {/* Notifications Tab */}
      {activeTab === "notifications" && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Bell className="w-5 h-5" />
            Email Notifications
          </h2>
          <p className="text-sm text-muted-foreground mb-6">
            Control which email notifications you receive from yarnnn.
          </p>

          {isLoadingNotifications ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : notificationPrefs ? (
            <div className="space-y-4">
              {/* Deliverable Ready */}
              <div className="p-4 border border-border rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Mail className="w-5 h-5 text-muted-foreground" />
                    <div>
                      <div className="font-medium">Deliverable Ready</div>
                      <div className="text-sm text-muted-foreground">
                        Get notified when a scheduled deliverable is ready for review
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleNotificationToggle("email_deliverable_ready", !notificationPrefs.email_deliverable_ready)}
                    disabled={isSavingNotifications}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      notificationPrefs.email_deliverable_ready ? "bg-primary" : "bg-muted"
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        notificationPrefs.email_deliverable_ready ? "translate-x-6" : "translate-x-1"
                      }`}
                    />
                  </button>
                </div>
              </div>

              {/* Deliverable Failed */}
              <div className="p-4 border border-border rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="w-5 h-5 text-muted-foreground" />
                    <div>
                      <div className="font-medium">Deliverable Failed</div>
                      <div className="text-sm text-muted-foreground">
                        Get notified when a deliverable fails to generate
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleNotificationToggle("email_deliverable_failed", !notificationPrefs.email_deliverable_failed)}
                    disabled={isSavingNotifications}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      notificationPrefs.email_deliverable_failed ? "bg-primary" : "bg-muted"
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        notificationPrefs.email_deliverable_failed ? "translate-x-6" : "translate-x-1"
                      }`}
                    />
                  </button>
                </div>
              </div>

              {/* Work Complete */}
              <div className="p-4 border border-border rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Check className="w-5 h-5 text-muted-foreground" />
                    <div>
                      <div className="font-medium">Work Complete</div>
                      <div className="text-sm text-muted-foreground">
                        Get notified when a work ticket finishes execution
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleNotificationToggle("email_work_complete", !notificationPrefs.email_work_complete)}
                    disabled={isSavingNotifications}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      notificationPrefs.email_work_complete ? "bg-primary" : "bg-muted"
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        notificationPrefs.email_work_complete ? "translate-x-6" : "translate-x-1"
                      }`}
                    />
                  </button>
                </div>
              </div>

              {/* Weekly Digest */}
              <div className="p-4 border border-border rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-muted-foreground" />
                    <div>
                      <div className="font-medium">Weekly Digest</div>
                      <div className="text-sm text-muted-foreground">
                        Receive a weekly summary of your activity
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleNotificationToggle("email_weekly_digest", !notificationPrefs.email_weekly_digest)}
                    disabled={isSavingNotifications}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      notificationPrefs.email_weekly_digest ? "bg-primary" : "bg-muted"
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        notificationPrefs.email_weekly_digest ? "translate-x-6" : "translate-x-1"
                      }`}
                    />
                  </button>
                </div>
              </div>

              {/* ADR-060: Suggested Deliverables */}
              <div className="p-4 border border-border rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Sparkles className="w-5 h-5 text-muted-foreground" />
                    <div>
                      <div className="font-medium">Suggested Deliverables</div>
                      <div className="text-sm text-muted-foreground">
                        Get notified when new deliverables are suggested based on your conversations
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleNotificationToggle("email_suggestion_created", !notificationPrefs.email_suggestion_created)}
                    disabled={isSavingNotifications}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      notificationPrefs.email_suggestion_created ? "bg-primary" : "bg-muted"
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        notificationPrefs.email_suggestion_created ? "translate-x-6" : "translate-x-1"
                      }`}
                    />
                  </button>
                </div>
              </div>

              {isSavingNotifications && (
                <p className="text-sm text-muted-foreground flex items-center gap-2">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Saving...
                </p>
              )}
            </div>
          ) : (
            <div className="text-muted-foreground">Failed to load notification preferences</div>
          )}
        </section>
      )}

      {/* ADR-039: Memory tab removed - user memory now in /memory */}

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
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                <div className="p-4 border border-border rounded-lg text-center">
                  <MessageSquare className="w-5 h-5 mx-auto mb-2 text-muted-foreground" />
                  <div className="text-2xl font-bold">{dangerStats.chat_sessions}</div>
                  <div className="text-xs text-muted-foreground">Chats</div>
                </div>
                <div className="p-4 border border-border rounded-lg text-center">
                  <Brain className="w-5 h-5 mx-auto mb-2 text-muted-foreground" />
                  <div className="text-2xl font-bold">{dangerStats.memories}</div>
                  <div className="text-xs text-muted-foreground">Memories</div>
                </div>
                <div className="p-4 border border-border rounded-lg text-center">
                  <FileText className="w-5 h-5 mx-auto mb-2 text-muted-foreground" />
                  <div className="text-2xl font-bold">{dangerStats.documents}</div>
                  <div className="text-xs text-muted-foreground">Docs</div>
                </div>
                <div className="p-4 border border-border rounded-lg text-center">
                  <Package className="w-5 h-5 mx-auto mb-2 text-muted-foreground" />
                  <div className="text-2xl font-bold">{dangerStats.deliverables}</div>
                  <div className="text-xs text-muted-foreground">Deliverables</div>
                </div>
              </div>

              {/* Tier 1: Selective Purge */}
              <div className="mb-6">
                <h3 className="text-sm font-medium text-muted-foreground mb-3 uppercase tracking-wide">
                  Selective Purge
                </h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Remove individual data types while keeping everything else.
                </p>
                <div className="space-y-3">
                  {/* Clear Conversations */}
                  <div className="p-4 border border-border rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium flex items-center gap-2">
                          <MessageSquare className="w-4 h-4" />
                          Clear Conversations
                        </div>
                        <div className="text-sm text-muted-foreground">
                          Delete all {dangerStats.chat_sessions} chat sessions
                        </div>
                      </div>
                      <button
                        onClick={() => initiateDangerAction("chat")}
                        disabled={dangerStats.chat_sessions === 0}
                        className="px-4 py-2 border border-border rounded-md text-sm font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Clear
                      </button>
                    </div>
                  </div>

                  {/* Clear Memories */}
                  <div className="p-4 border border-border rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium flex items-center gap-2">
                          <Brain className="w-4 h-4" />
                          Clear Memories
                        </div>
                        <div className="text-sm text-muted-foreground">
                          Delete all {dangerStats.memories} memories
                        </div>
                      </div>
                      <button
                        onClick={() => initiateDangerAction("memories")}
                        disabled={dangerStats.memories === 0}
                        className="px-4 py-2 border border-border rounded-md text-sm font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Clear
                      </button>
                    </div>
                  </div>

                  {/* Clear Documents */}
                  <div className="p-4 border border-border rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium flex items-center gap-2">
                          <FileText className="w-4 h-4" />
                          Clear Documents
                        </div>
                        <div className="text-sm text-muted-foreground">
                          Delete all {dangerStats.documents} documents
                        </div>
                      </div>
                      <button
                        onClick={() => initiateDangerAction("documents")}
                        disabled={dangerStats.documents === 0}
                        className="px-4 py-2 border border-border rounded-md text-sm font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Clear
                      </button>
                    </div>
                  </div>

                  {/* Clear Work History */}
                  <div className="p-4 border border-border rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium flex items-center gap-2">
                          <Briefcase className="w-4 h-4" />
                          Clear Work History
                        </div>
                        <div className="text-sm text-muted-foreground">
                          Delete all {dangerStats.work_tickets} work tickets
                        </div>
                      </div>
                      <button
                        onClick={() => initiateDangerAction("work")}
                        disabled={dangerStats.work_tickets === 0}
                        className="px-4 py-2 border border-border rounded-md text-sm font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Clear
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Tier 2: Category Reset */}
              <div className="mb-6">
                <h3 className="text-sm font-medium text-destructive/80 mb-3 uppercase tracking-wide flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  Category Reset
                </h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Reset entire categories of data at once.
                </p>
                <div className="space-y-3">
                  {/* Clear All Content */}
                  <div className="p-4 border border-destructive/30 rounded-lg bg-destructive/5">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium flex items-center gap-2">
                          <Package className="w-4 h-4" />
                          Clear All Content
                        </div>
                        <div className="text-sm text-muted-foreground">
                          Delete {dangerStats.deliverables} deliverables + {dangerStats.work_tickets} work items
                        </div>
                      </div>
                      <button
                        onClick={() => initiateDangerAction("content")}
                        disabled={dangerStats.deliverables === 0 && dangerStats.work_tickets === 0}
                        className="px-4 py-2 bg-destructive/10 text-destructive border border-destructive/30 rounded-md text-sm font-medium hover:bg-destructive/20 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Clear All
                      </button>
                    </div>
                  </div>

                  {/* Clear All Context */}
                  <div className="p-4 border border-destructive/30 rounded-lg bg-destructive/5">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium flex items-center gap-2">
                          <Database className="w-4 h-4" />
                          Clear All Context
                        </div>
                        <div className="text-sm text-muted-foreground">
                          Delete {dangerStats.memories} memories + {dangerStats.documents} docs + {dangerStats.platform_content} synced items + {dangerStats.chat_sessions} chats
                        </div>
                      </div>
                      <button
                        onClick={() => initiateDangerAction("context")}
                        disabled={dangerStats.memories === 0 && dangerStats.documents === 0 && dangerStats.chat_sessions === 0}
                        className="px-4 py-2 bg-destructive/10 text-destructive border border-destructive/30 rounded-md text-sm font-medium hover:bg-destructive/20 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Clear All
                      </button>
                    </div>
                  </div>

                  {/* Clear Integrations */}
                  <div className="p-4 border border-destructive/30 rounded-lg bg-destructive/5">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium flex items-center gap-2">
                          <Link2 className="w-4 h-4" />
                          Clear Integrations
                        </div>
                        <div className="text-sm text-muted-foreground">
                          Disconnect {dangerStats.platform_connections} integrations, clear import/export history
                        </div>
                      </div>
                      <button
                        onClick={() => initiateDangerAction("integrations")}
                        disabled={dangerStats.platform_connections === 0}
                        className="px-4 py-2 bg-destructive/10 text-destructive border border-destructive/30 rounded-md text-sm font-medium hover:bg-destructive/20 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Disconnect
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Tier 3: Full Actions */}
              <div className="mb-6">
                <h3 className="text-sm font-medium text-destructive mb-3 uppercase tracking-wide flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  Full Actions
                </h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Irreversible actions that affect your entire account.
                </p>
                <div className="space-y-3">
                  {/* Full Data Reset */}
                  <div className="p-4 border border-destructive rounded-lg bg-destructive/10">
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
                  <div className="p-4 border border-destructive rounded-lg bg-destructive/10">
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
                 "Confirm Deletion"}
              </h3>
            </div>

            <div className="text-muted-foreground mb-6">
              {/* Tier 1: Individual purges */}
              {dangerAction === "memories" && (
                <p>
                  Are you sure you want to delete all <strong>{dangerStats?.memories}</strong> memories?
                  yarnnn will need to relearn your preferences.
                </p>
              )}
              {dangerAction === "chat" && (
                <p>
                  Are you sure you want to delete all <strong>{dangerStats?.chat_sessions}</strong> chat
                  sessions? Your conversation history will be permanently erased.
                </p>
              )}
              {dangerAction === "documents" && (
                <p>
                  Are you sure you want to delete all <strong>{dangerStats?.documents}</strong> documents?
                  All uploaded documents and their extracted content will be removed.
                </p>
              )}
              {dangerAction === "work" && (
                <p>
                  Are you sure you want to delete all <strong>{dangerStats?.work_tickets}</strong> work tickets?
                  All scheduled work and execution history will be removed.
                </p>
              )}

              {/* Tier 2: Category resets */}
              {dangerAction === "content" && (
                <>
                  <p className="mb-2">
                    Are you sure you want to <strong>clear all content</strong>? This will delete:
                  </p>
                  <ul className="list-disc list-inside text-sm space-y-1">
                    <li>{dangerStats?.deliverables} deliverables and {dangerStats?.deliverable_versions} versions</li>
                    <li>{dangerStats?.work_tickets} work tickets</li>
                  </ul>
                  <p className="mt-2 text-sm">You will return to the onboarding flow.</p>
                </>
              )}
              {dangerAction === "context" && (
                <>
                  <p className="mb-2">
                    Are you sure you want to <strong>clear all context</strong>? This will delete:
                  </p>
                  <ul className="list-disc list-inside text-sm space-y-1">
                    <li>{dangerStats?.memories} memories</li>
                    <li>{dangerStats?.documents} documents</li>
                    <li>{dangerStats?.platform_content} synced platform items</li>
                    <li>{dangerStats?.chat_sessions} chat sessions</li>
                  </ul>
                  <p className="mt-2 text-sm">yarnnn will lose all knowledge about you and need to start from scratch.</p>
                </>
              )}
              {dangerAction === "integrations" && (
                <>
                  <p className="mb-2">
                    Are you sure you want to <strong>clear all integrations</strong>? This will:
                  </p>
                  <ul className="list-disc list-inside text-sm space-y-1">
                    <li>Disconnect {dangerStats?.platform_connections} connected services</li>
                    <li>Delete OAuth tokens (you&apos;ll need to reconnect)</li>
                    <li>Clear {dangerStats?.integration_import_jobs} import jobs</li>
                    <li>Clear {dangerStats?.export_logs} export logs</li>
                  </ul>
                </>
              )}

              {/* Tier 3: Full actions */}
              {dangerAction === "reset" && (
                <>
                  <p className="mb-2">
                    Are you sure you want to <strong>reset your entire account</strong>? This will delete:
                  </p>
                  <ul className="list-disc list-inside text-sm space-y-1">
                    <li>{dangerStats?.deliverables} deliverables</li>
                    <li>{dangerStats?.chat_sessions} chat sessions</li>
                    <li>{dangerStats?.memories} memories</li>
                    <li>{dangerStats?.documents} documents</li>
                    <li>{dangerStats?.work_tickets} work tickets</li>
                    <li>{dangerStats?.platform_connections} integrations</li>
                  </ul>
                  <p className="mt-2 text-sm">Your account will remain active with a fresh workspace.</p>
                </>
              )}
              {dangerAction === "deactivate" && (
                <>
                  <p className="font-medium text-destructive mb-2">
                    This action is PERMANENT and cannot be undone.
                  </p>
                  <p className="mb-2">All your data will be permanently deleted:</p>
                  <ul className="list-disc list-inside text-sm space-y-1">
                    <li>All deliverables, memories, documents, and chat history</li>
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
