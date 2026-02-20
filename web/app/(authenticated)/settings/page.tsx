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
  ExternalLink,
  X,
  Shield,
  Package,
  Database,
  Briefcase,
  Calendar,
  Sparkles,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { SubscriptionCard } from "@/components/subscription/SubscriptionCard";
import { UsageIndicator } from "@/components/subscription/UpgradePrompt";
import { useSubscriptionGate } from "@/hooks/useSubscriptionGate";
import { SUBSCRIPTION_LIMITS } from "@/lib/subscription/limits";
import { createClient } from "@/lib/supabase/client";
import { IntegrationImportModal } from "@/components/IntegrationImportModal";
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

interface Integration {
  id: string;
  provider: string;
  status: string;
  workspace_name: string | null;
  last_used_at: string | null;
  created_at: string;
  metadata?: {
    email?: string;
    name?: string;
    team_id?: string;
    team_name?: string;
    authed_user_id?: string;
    workspace_id?: string;
    capabilities?: string[];
  };
}

// ADR-039: Removed "memory" tab - facts now live in unified Context page
type SettingsTab = "billing" | "usage" | "notifications" | "integrations" | "account";
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
    tabParam === "integrations" ? "integrations" :
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
  const { isPro } = useSubscriptionGate();

  // Notification preferences state
  const [notificationPrefs, setNotificationPrefs] = useState<NotificationPreferences | null>(null);
  const [isLoadingNotifications, setIsLoadingNotifications] = useState(false);
  const [isSavingNotifications, setIsSavingNotifications] = useState(false);

  // Integration state
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [isLoadingIntegrations, setIsLoadingIntegrations] = useState(false);
  const [connectingProvider, setConnectingProvider] = useState<string | null>(null);
  const [disconnectingProvider, setDisconnectingProvider] = useState<string | null>(null);

  // Import modal state (ADR-027, ADR-029, ADR-046)
  const [importModalProvider, setImportModalProvider] = useState<"slack" | "notion" | "gmail" | "google" | "calendar" | null>(null);

  // Signal processing state (ADR-068)
  const [isTriggeringSignals, setIsTriggeringSignals] = useState(false);
  const [signalTriggerResult, setSignalTriggerResult] = useState<{
    status: string;
    message?: string;
    deliverables_created?: number;
    existing_triggered?: number;
  } | null>(null);

  // Usage metrics state
  const [usageMetrics, setUsageMetrics] = useState<{
    deliverables: number;
    documents: number;
    platforms: { connected: number; total: number };
    facts: number;
  } | null>(null);
  const [isLoadingUsage, setIsLoadingUsage] = useState(false);

  // Check for OAuth callback status
  const providerParam = searchParams.get("provider");
  const statusParam = searchParams.get("status");
  const errorParam = searchParams.get("error");

  // State to control notification visibility (auto-dismiss)
  const [showOAuthNotification, setShowOAuthNotification] = useState(true);

  // ADR-039: Memory stats fetch removed - now in Context page

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

  // Fetch integrations when integrations tab is active
  useEffect(() => {
    if (activeTab === "integrations") {
      loadIntegrations();
    }
  }, [activeTab]);

  // Handle OAuth callback redirect
  useEffect(() => {
    if (providerParam && statusParam) {
      // Auto-switch to integrations tab on OAuth callback
      setActiveTab("integrations");
      // Refresh integrations list
      loadIntegrations();
      // Show notification initially
      setShowOAuthNotification(true);
      // Auto-dismiss notification after 5 seconds
      const timer = setTimeout(() => {
        setShowOAuthNotification(false);
        // Also clean up URL params
        router.replace("/settings?tab=integrations", { scroll: false });
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [providerParam, statusParam, router]);

  const loadUsageMetrics = async () => {
    setIsLoadingUsage(true);
    try {
      // Fetch counts from various endpoints in parallel
      const [deliverables, documents, integrations, facts] = await Promise.all([
        api.deliverables.list().catch(() => []),
        api.documents.list().catch(() => ({ documents: [] })),
        api.integrations.list().catch(() => ({ integrations: [] })),
        api.userMemories.list().catch(() => []),
      ]);

      const activeIntegrations = (integrations.integrations || []).filter(
        (i: { status: string }) => i.status === "active"
      );

      setUsageMetrics({
        deliverables: Array.isArray(deliverables) ? deliverables.length : 0,
        documents: documents.documents?.length || 0,
        platforms: {
          connected: activeIntegrations.length,
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

  const loadIntegrations = async () => {
    setIsLoadingIntegrations(true);
    try {
      const result = await api.integrations.list();
      setIntegrations(result.integrations);
    } catch (err) {
      console.error("Failed to fetch integrations:", err);
    } finally {
      setIsLoadingIntegrations(false);
    }
  };

  const handleConnectIntegration = async (provider: string) => {
    setConnectingProvider(provider);
    try {
      const result = await api.integrations.getAuthorizationUrl(provider);
      // Open OAuth in new window/popup
      window.location.href = result.authorization_url;
    } catch (err) {
      console.error(`Failed to initiate ${provider} OAuth:`, err);
      setConnectingProvider(null);
    }
  };

  const handleDisconnectIntegration = async (provider: string) => {
    if (!confirm(`Disconnect ${provider}? You'll need to reconnect to export to ${provider} again.`)) {
      return;
    }
    setDisconnectingProvider(provider);
    try {
      await api.integrations.disconnect(provider);
      setIntegrations(integrations.filter(i => i.provider !== provider));
    } catch (err) {
      console.error(`Failed to disconnect ${provider}:`, err);
    } finally {
      setDisconnectingProvider(null);
    }
  };

  const handleTriggerSignalProcessing = async () => {
    setIsTriggeringSignals(true);
    setSignalTriggerResult(null);

    try {
      const result = await api.signalProcessing.trigger("all");
      setSignalTriggerResult({
        status: result.status,
        message: result.message,
        deliverables_created: result.deliverables_created,
        existing_triggered: result.existing_triggered,
      });

      // Auto-dismiss success message after 5 seconds
      if (result.status === "completed") {
        setTimeout(() => setSignalTriggerResult(null), 5000);
      }
    } catch (err) {
      console.error("Failed to trigger signal processing:", err);
      setSignalTriggerResult({
        status: "error",
        message: err instanceof Error ? err.message : "Failed to scan for signals",
      });
    } finally {
      setIsTriggeringSignals(false);
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

  // Memory purge is now handled through danger zone actions
  // The old per-project purge is removed since projects no longer exist

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
              Welcome to yarnnn Pro!
            </p>
            <p className="text-sm text-green-700 dark:text-green-300">
              Your subscription is now active. Enjoy unlimited projects and scheduled agents.
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
          onClick={() => setActiveTab("integrations")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === "integrations"
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <span className="flex items-center gap-2">
            <Link2 className="w-4 h-4" />
            Integrations
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
                  <h3 className="font-medium">Platforms</h3>
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

      {/* Integrations Tab */}
      {activeTab === "integrations" && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Link2 className="w-5 h-5" />
            Connected Integrations
          </h2>
          <p className="text-sm text-muted-foreground mb-6">
            Connect third-party services to export your deliverables directly to Slack channels or Notion pages.
          </p>

          {/* OAuth Callback Status - auto-dismisses after 5 seconds */}
          {providerParam && statusParam && showOAuthNotification && (
            <div className={`mb-6 p-4 rounded-lg flex items-center gap-3 ${
              statusParam === "success"
                ? "bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800"
                : "bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"
            }`}>
              {statusParam === "success" ? (
                <>
                  <Check className="w-5 h-5 text-green-600" />
                  <div className="flex-1">
                    <p className="font-medium text-green-800 dark:text-green-200">
                      {providerParam.charAt(0).toUpperCase() + providerParam.slice(1)} connected successfully!
                    </p>
                    <p className="text-sm text-green-700 dark:text-green-300">
                      You can now export deliverables to {providerParam}.
                    </p>
                  </div>
                  <button
                    onClick={() => setShowOAuthNotification(false)}
                    className="p-1 hover:bg-green-200 dark:hover:bg-green-800 rounded"
                    aria-label="Dismiss"
                  >
                    <X className="w-4 h-4 text-green-600" />
                  </button>
                </>
              ) : (
                <>
                  <X className="w-5 h-5 text-red-600" />
                  <div className="flex-1">
                    <p className="font-medium text-red-800 dark:text-red-200">
                      Failed to connect {providerParam}
                    </p>
                    <p className="text-sm text-red-700 dark:text-red-300">
                      {errorParam || "Please try again."}
                    </p>
                  </div>
                  <button
                    onClick={() => setShowOAuthNotification(false)}
                    className="p-1 hover:bg-red-200 dark:hover:bg-red-800 rounded"
                    aria-label="Dismiss"
                  >
                    <X className="w-4 h-4 text-red-600" />
                  </button>
                </>
              )}
            </div>
          )}

          {isLoadingIntegrations ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="space-y-4">
              {/* Slack Integration */}
              {(() => {
                const slackIntegration = integrations.find(i => i.provider === "slack");
                return (
                  <div className="p-4 border border-border rounded-lg">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-[#4A154B] rounded-lg flex items-center justify-center">
                          <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z"/>
                          </svg>
                        </div>
                        <div>
                          <div className="font-medium">Slack</div>
                          <div className="text-sm text-muted-foreground">
                            {slackIntegration
                              ? "Team collaboration and context"
                              : "Post deliverables to Slack channels"
                            }
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {slackIntegration ? (
                          <>
                            <span className="text-sm text-green-600 dark:text-green-400 flex items-center gap-1">
                              <Check className="w-4 h-4" />
                              Connected
                            </span>
                            <button
                              onClick={() => handleConnectIntegration("slack")}
                              disabled={connectingProvider === "slack"}
                              className="px-3 py-1.5 text-sm text-muted-foreground border border-border rounded-md hover:bg-muted transition-colors"
                            >
                              {connectingProvider === "slack" ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                "Reconnect"
                              )}
                            </button>
                            <button
                              onClick={() => handleDisconnectIntegration(slackIntegration.provider)}
                              disabled={disconnectingProvider === slackIntegration.provider}
                              className="px-3 py-1.5 text-sm text-muted-foreground hover:text-destructive border border-border rounded-md hover:border-destructive/30 transition-colors"
                            >
                              {disconnectingProvider === slackIntegration.provider ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                "Disconnect"
                              )}
                            </button>
                            <button
                              onClick={() => router.push("/context/slack")}
                              className="px-3 py-1.5 text-sm text-primary border border-primary/30 rounded-md hover:bg-primary/10 transition-colors"
                            >
                              Manage
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => handleConnectIntegration("slack")}
                            disabled={connectingProvider === "slack"}
                            className="px-4 py-2 bg-[#4A154B] text-white rounded-md text-sm font-medium hover:bg-[#3d1140] flex items-center gap-2"
                          >
                            {connectingProvider === "slack" ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <>
                                <ExternalLink className="w-4 h-4" />
                                Connect
                              </>
                            )}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })()}

              {/* Notion Integration */}
              {(() => {
                const notionIntegration = integrations.find(i => i.provider === "notion");
                return (
                  <div className="p-4 border border-border rounded-lg">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-black dark:bg-white rounded-lg flex items-center justify-center">
                          <svg className="w-6 h-6 text-white dark:text-black" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.98-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466l1.823 1.447zm.793 3.08v13.904c0 .747.373 1.027 1.213.98l14.523-.84c.84-.046.934-.56.934-1.166V6.354c0-.606-.234-.933-.746-.886l-15.177.887c-.56.046-.747.326-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952l1.448.327s0 .84-1.168.84l-3.222.186c-.093-.186 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.14c-.093-.513.28-.886.747-.933l3.222-.187zM2.87.119l13.449-.933c1.634-.14 2.055-.047 3.082.7l4.249 2.986c.7.513.934.653.934 1.213v16.378c0 1.026-.373 1.634-1.68 1.726l-15.458.934c-.98.046-1.448-.093-1.962-.747L1.945 18.79c-.56-.747-.793-1.306-.793-1.958V2.005C1.152.933 1.525.212 2.87.119z"/>
                          </svg>
                        </div>
                        <div>
                          <div className="font-medium">Notion</div>
                          <div className="text-sm text-muted-foreground">
                            {notionIntegration
                              ? "Knowledge base and context"
                              : "Export deliverables to Notion pages"
                            }
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {notionIntegration ? (
                          <>
                            <span className="text-sm text-green-600 dark:text-green-400 flex items-center gap-1">
                              <Check className="w-4 h-4" />
                              Connected
                            </span>
                            <button
                              onClick={() => handleConnectIntegration("notion")}
                              disabled={connectingProvider === "notion"}
                              className="px-3 py-1.5 text-sm text-muted-foreground border border-border rounded-md hover:bg-muted transition-colors"
                            >
                              {connectingProvider === "notion" ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                "Reconnect"
                              )}
                            </button>
                            <button
                              onClick={() => handleDisconnectIntegration(notionIntegration.provider)}
                              disabled={disconnectingProvider === notionIntegration.provider}
                              className="px-3 py-1.5 text-sm text-muted-foreground hover:text-destructive border border-border rounded-md hover:border-destructive/30 transition-colors"
                            >
                              {disconnectingProvider === notionIntegration.provider ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                "Disconnect"
                              )}
                            </button>
                            <button
                              onClick={() => router.push("/context/notion")}
                              className="px-3 py-1.5 text-sm text-primary border border-primary/30 rounded-md hover:bg-primary/10 transition-colors"
                            >
                              Manage
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => handleConnectIntegration("notion")}
                            disabled={connectingProvider === "notion"}
                            className="px-4 py-2 bg-black dark:bg-white text-white dark:text-black rounded-md text-sm font-medium hover:bg-gray-800 dark:hover:bg-gray-200 flex items-center gap-2"
                          >
                            {connectingProvider === "notion" ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <>
                                <ExternalLink className="w-4 h-4" />
                                Connect
                              </>
                            )}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })()}

              {/* Google Integration (ADR-046: Unified Gmail + Calendar) */}
              {(() => {
                // ADR-046: Single Google connection provides both Gmail and Calendar
                const googleIntegration = integrations.find(i => i.provider === "gmail" || i.provider === "google");
                return (
                  <div className="p-4 border border-border rounded-lg">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 via-red-500 to-yellow-500 rounded-lg flex items-center justify-center">
                          <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                          </svg>
                        </div>
                        <div>
                          <div className="font-medium">Google</div>
                          <div className="text-sm text-muted-foreground">
                            {googleIntegration
                              ? "Gmail and Calendar access"
                              : "Gmail and Calendar access"
                            }
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {googleIntegration ? (
                          <>
                            <span className="text-sm text-green-600 dark:text-green-400 flex items-center gap-1">
                              <Check className="w-4 h-4" />
                              Connected
                            </span>
                            <button
                              onClick={() => handleDisconnectIntegration(googleIntegration.provider)}
                              disabled={disconnectingProvider === googleIntegration.provider}
                              className="px-3 py-1.5 text-sm text-muted-foreground hover:text-destructive border border-border rounded-md hover:border-destructive/30 transition-colors"
                            >
                              {disconnectingProvider === googleIntegration.provider ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                "Disconnect"
                              )}
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => handleConnectIntegration("google")}
                            disabled={connectingProvider === "google"}
                            className="px-4 py-2 bg-gradient-to-r from-blue-500 to-red-500 text-white rounded-md text-sm font-medium hover:from-blue-600 hover:to-red-600 flex items-center gap-2"
                          >
                            {connectingProvider === "google" ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <>
                                <ExternalLink className="w-4 h-4" />
                                Connect
                              </>
                            )}
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Sub-capabilities: Gmail and Calendar */}
                    {googleIntegration && (
                      <div className="mt-3 pt-3 border-t border-border/50 grid grid-cols-2 gap-3">
                        {/* Gmail capability */}
                        <div className="flex items-center justify-between p-2 rounded-md bg-muted/30">
                          <div className="flex items-center gap-2">
                            <Mail className="w-4 h-4 text-red-500" />
                            <span className="text-sm font-medium">Gmail</span>
                          </div>
                          <button
                            onClick={() => router.push("/context/gmail")}
                            className="px-2 py-1 text-xs text-primary border border-primary/30 rounded hover:bg-primary/10 transition-colors"
                          >
                            Manage
                          </button>
                        </div>

                        {/* Calendar capability */}
                        <div className="flex items-center justify-between p-2 rounded-md bg-muted/30">
                          <div className="flex items-center gap-2">
                            <Calendar className="w-4 h-4 text-blue-500" />
                            <span className="text-sm font-medium">Calendar</span>
                          </div>
                          <button
                            onClick={() => router.push("/context/calendar")}
                            className="px-2 py-1 text-xs text-primary border border-primary/30 rounded hover:bg-primary/10 transition-colors"
                          >
                            Manage
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })()}

              {/* Signal Processing Trigger (ADR-068) - For all connected integrations */}
              {integrations.length > 0 && (
                <div className="p-4 border border-border rounded-lg bg-gradient-to-br from-primary/5 to-primary/10">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Sparkles className="w-5 h-5 text-primary" />
                        <span className="font-medium">Proactive Signal Detection</span>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Scan your connected platforms for behavioral signals (upcoming meetings, silent threads, contact drift). Currently supports Gmail and Calendar, with Slack and Notion signal detection coming soon.
                      </p>
                    </div>
                    <button
                      onClick={handleTriggerSignalProcessing}
                      disabled={isTriggeringSignals}
                      className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 whitespace-nowrap"
                    >
                      {isTriggeringSignals ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Scanning...
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-4 h-4" />
                          Scan Now
                        </>
                      )}
                    </button>
                  </div>

                  {/* Result notification */}
                  {signalTriggerResult && (
                    <div className={`mt-3 p-3 rounded-md text-sm ${
                      signalTriggerResult.status === "completed"
                        ? "bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-200 border border-green-200 dark:border-green-800"
                        : signalTriggerResult.status === "rate_limited"
                        ? "bg-yellow-50 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-200 border border-yellow-200 dark:border-yellow-800"
                        : signalTriggerResult.status === "no_platforms"
                        ? "bg-blue-50 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200 border border-blue-200 dark:border-blue-800"
                        : "bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200 border border-red-200 dark:border-red-800"
                    }`}>
                      <div className="flex items-center justify-between">
                        <span>{signalTriggerResult.message}</span>
                        {signalTriggerResult.status !== "rate_limited" && (
                          <button
                            onClick={() => setSignalTriggerResult(null)}
                            className="ml-2 p-1 hover:opacity-70"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Info note */}
              <div className="mt-6 p-4 bg-muted/50 rounded-lg text-sm text-muted-foreground">
                <p>
                  <strong>How it works:</strong> After connecting, you can export deliverables or import context
                  from your connected services. Use &quot;Import Context&quot; to bring in decisions, action items,
                  and project details from Slack channels, Notion pages, Gmail conversations, or Calendar events.
                </p>
              </div>
            </div>
          )}
        </section>
      )}

      {/* ADR-039: Memory tab removed - facts now in /context?source=facts */}

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
                          Delete {dangerStats.memories} memories + {dangerStats.documents} docs + {dangerStats.chat_sessions} chats
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
                    <li>{dangerStats?.chat_sessions} chat sessions</li>
                  </ul>
                  <p className="mt-2 text-sm">yarnnn will lose all knowledge about you and your projects.</p>
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
                    <li>All workspaces and integrations</li>
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

      {/* Integration Import Modal (ADR-027) */}
      {importModalProvider && (
        <IntegrationImportModal
          isOpen={true}
          onClose={() => setImportModalProvider(null)}
          onSuccess={() => {
            // Refresh stats to show new memories
            setImportModalProvider(null);
          }}
          provider={importModalProvider}
        />
      )}
    </div>
  );
}
