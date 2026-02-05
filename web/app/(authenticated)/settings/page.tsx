"use client";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  Settings,
  Trash2,
  Brain,
  AlertTriangle,
  Loader2,
  Check,
  User,
  FolderOpen,
  CreditCard,
  BarChart3,
  MessageSquare,
  FileText,
  RefreshCw,
  LogOut,
  Bell,
  Mail,
} from "lucide-react";
import { api } from "@/lib/api/client";
import type { Project } from "@/types";
import { SubscriptionCard } from "@/components/subscription/SubscriptionCard";
import { UsageIndicator } from "@/components/subscription/UpgradePrompt";
import { useSubscriptionGate } from "@/hooks/useSubscriptionGate";
import { SUBSCRIPTION_LIMITS } from "@/lib/subscription/limits";
import { createClient } from "@/lib/supabase/client";

interface MemoryStats {
  userMemories: number;
  projectMemories: Map<string, { name: string; count: number }>;
  totalMemories: number;
}

interface DangerZoneStats {
  chat_sessions: number;
  memories: number;
  deliverables: number;
  deliverable_versions: number;
  documents: number;
  projects: number;
  workspaces: number;
}

interface NotificationPreferences {
  email_deliverable_ready: boolean;
  email_deliverable_failed: boolean;
  email_work_complete: boolean;
  email_weekly_digest: boolean;
}

type SettingsTab = "memory" | "billing" | "usage" | "notifications" | "account";
type DangerAction = "memories" | "chat" | "deliverables" | "reset" | "deactivate" | null;

export default function SettingsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab");
  const initialTab: SettingsTab =
    tabParam === "billing" ? "billing" :
    tabParam === "usage" ? "usage" :
    tabParam === "notifications" ? "notifications" :
    tabParam === "account" ? "account" :
    "memory";
  const subscriptionSuccess = searchParams.get("subscription") === "success";

  const [activeTab, setActiveTab] = useState<SettingsTab>(initialTab);
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [dangerStats, setDangerStats] = useState<DangerZoneStats | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingDangerStats, setIsLoadingDangerStats] = useState(false);
  const [isPurging, setIsPurging] = useState(false);
  const [purgeTarget, setPurgeTarget] = useState<"user" | "project" | "all" | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const [dangerAction, setDangerAction] = useState<DangerAction>(null);
  const [purgeSuccess, setPurgeSuccess] = useState<string | null>(null);
  const [showSubscriptionSuccess, setShowSubscriptionSuccess] = useState(subscriptionSuccess);
  const { projects: projectsLimit, isPro } = useSubscriptionGate();

  // Notification preferences state
  const [notificationPrefs, setNotificationPrefs] = useState<NotificationPreferences | null>(null);
  const [isLoadingNotifications, setIsLoadingNotifications] = useState(false);
  const [isSavingNotifications, setIsSavingNotifications] = useState(false);

  // Fetch memory stats on mount
  useEffect(() => {
    async function fetchStats() {
      try {
        const userMemories = await api.userMemories.list();
        const projectList = await api.projects.list();
        setProjects(projectList);

        const projectMemories = new Map<string, { name: string; count: number }>();
        let totalProjectMemories = 0;

        for (const project of projectList) {
          try {
            const memories = await api.projectMemories.list(project.id);
            projectMemories.set(project.id, {
              name: project.name,
              count: memories.length,
            });
            totalProjectMemories += memories.length;
          } catch {
            projectMemories.set(project.id, { name: project.name, count: 0 });
          }
        }

        setStats({
          userMemories: userMemories.length,
          projectMemories,
          totalMemories: userMemories.length + totalProjectMemories,
        });
      } catch (err) {
        console.error("Failed to fetch stats:", err);
      } finally {
        setIsLoading(false);
      }
    }

    fetchStats();
  }, []);

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

  // Memory purge handler (existing)
  const handleMemoryPurge = async () => {
    if (!purgeTarget) return;

    setIsPurging(true);
    setPurgeSuccess(null);

    try {
      if (purgeTarget === "user") {
        const memories = await api.userMemories.list();
        for (const mem of memories) {
          await api.memories.delete(mem.id);
        }
        setPurgeSuccess(`Deleted ${memories.length} user memories`);
      } else if (purgeTarget === "project" && selectedProjectId) {
        const memories = await api.projectMemories.list(selectedProjectId);
        for (const mem of memories) {
          await api.memories.delete(mem.id);
        }
        const projectName = stats?.projectMemories.get(selectedProjectId)?.name || "project";
        setPurgeSuccess(`Deleted ${memories.length} memories from ${projectName}`);
      } else if (purgeTarget === "all") {
        const userMemories = await api.userMemories.list();
        for (const mem of userMemories) {
          await api.memories.delete(mem.id);
        }
        for (const project of projects) {
          const projectMemories = await api.projectMemories.list(project.id);
          for (const mem of projectMemories) {
            await api.memories.delete(mem.id);
          }
        }
        setPurgeSuccess(`Deleted all ${stats?.totalMemories || 0} memories`);
      }

      // Refresh memory stats
      setIsLoading(true);
      const userMemories = await api.userMemories.list();
      const projectMemories = new Map<string, { name: string; count: number }>();
      let totalProjectMemories = 0;

      for (const project of projects) {
        try {
          const memories = await api.projectMemories.list(project.id);
          projectMemories.set(project.id, {
            name: project.name,
            count: memories.length,
          });
          totalProjectMemories += memories.length;
        } catch {
          projectMemories.set(project.id, { name: project.name, count: 0 });
        }
      }

      setStats({
        userMemories: userMemories.length,
        projectMemories,
        totalMemories: userMemories.length + totalProjectMemories,
      });
    } catch (err) {
      console.error("Purge failed:", err);
      setPurgeSuccess("Failed to delete memories");
    } finally {
      setIsPurging(false);
      setShowConfirm(false);
      setPurgeTarget(null);
      setSelectedProjectId(null);
      setIsLoading(false);
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
        case "chat":
          result = await api.account.clearChatHistory();
          setPurgeSuccess(result.message);
          break;
        case "deliverables":
          result = await api.account.deleteAllDeliverables();
          setPurgeSuccess(result.message);
          break;
        case "reset":
          result = await api.account.resetAccount();
          setPurgeSuccess(result.message);
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

  const initiateUserPurge = () => {
    setPurgeTarget("user");
    setDangerAction("memories");
    setShowConfirm(true);
  };

  const initiateProjectPurge = (projectId: string) => {
    setPurgeTarget("project");
    setSelectedProjectId(projectId);
    setDangerAction("memories");
    setShowConfirm(true);
  };

  const initiateAllMemoryPurge = () => {
    setPurgeTarget("all");
    setDangerAction("memories");
    setShowConfirm(true);
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

      {/* Tabs */}
      <div className="flex gap-1 mb-8 border-b border-border overflow-x-auto">
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
            Memory
          </span>
        </button>
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
            {isPro ? "You have unlimited usage on Pro." : "Track your usage against Free tier limits."}
          </p>

          <div className="space-y-6">
            <div className="p-4 border border-border rounded-lg">
              <h3 className="font-medium mb-3 flex items-center gap-2">
                <FolderOpen className="w-4 h-4" />
                Projects
              </h3>
              <UsageIndicator
                current={projectsLimit.current}
                limit={projectsLimit.limit}
                label="Projects created"
                feature="projects"
                showUpgrade={!isPro}
              />
            </div>

            <div className="p-4 border border-border rounded-lg">
              <h3 className="font-medium mb-3 flex items-center gap-2">
                <Brain className="w-4 h-4" />
                Memories
              </h3>
              {isLoading ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <div className="space-y-4">
                  {projects.map((project) => {
                    const memCount = stats?.projectMemories.get(project.id)?.count || 0;
                    const memLimit = isPro ? -1 : SUBSCRIPTION_LIMITS.free.memoriesPerProject;
                    return (
                      <UsageIndicator
                        key={project.id}
                        current={memCount}
                        limit={memLimit}
                        label={project.name}
                        feature="memories"
                        showUpgrade={!isPro}
                      />
                    );
                  })}
                  {projects.length === 0 && (
                    <p className="text-sm text-muted-foreground">No projects yet</p>
                  )}
                </div>
              )}
            </div>

            <div className="p-4 border border-border rounded-lg">
              <h3 className="font-medium mb-3 flex items-center gap-2">
                <FolderOpen className="w-4 h-4" />
                Documents
              </h3>
              <p className="text-sm text-muted-foreground">
                {isPro ? "Unlimited document uploads" : `${SUBSCRIPTION_LIMITS.free.documents} documents per project`}
              </p>
            </div>
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

      {/* Memory Tab */}
      {activeTab === "memory" && (
        <>
          <section className="mb-8">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Brain className="w-5 h-5" />
              Memory Overview
            </h2>

            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
              </div>
            ) : stats ? (
              <div className="space-y-4">
                <div className="p-4 border border-border rounded-lg bg-muted/30">
                  <div className="text-3xl font-bold">{stats.totalMemories}</div>
                  <div className="text-sm text-muted-foreground">Total memories stored</div>
                </div>

                <div className="p-4 border border-border rounded-lg">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <User className="w-5 h-5 text-primary" />
                      <div>
                        <div className="font-medium">About You (User Memories)</div>
                        <div className="text-sm text-muted-foreground">
                          Portable across all projects
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-lg font-semibold">{stats.userMemories}</span>
                      {stats.userMemories > 0 && (
                        <button
                          onClick={initiateUserPurge}
                          className="p-2 text-muted-foreground hover:text-destructive transition-colors"
                          title="Delete all user memories"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                {projects.length > 0 && (
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-muted-foreground px-1">
                      Project Memories
                    </div>
                    {projects.map((project) => {
                      const projectStats = stats.projectMemories.get(project.id);
                      return (
                        <div key={project.id} className="p-4 border border-border rounded-lg">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <FolderOpen className="w-5 h-5 text-muted-foreground" />
                              <div>
                                <div className="font-medium">{project.name}</div>
                                <div className="text-sm text-muted-foreground">
                                  Project-specific context
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center gap-4">
                              <span className="text-lg font-semibold">
                                {projectStats?.count || 0}
                              </span>
                              {(projectStats?.count || 0) > 0 && (
                                <button
                                  onClick={() => initiateProjectPurge(project.id)}
                                  className="p-2 text-muted-foreground hover:text-destructive transition-colors"
                                  title={`Delete all memories from ${project.name}`}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-muted-foreground">Failed to load memory stats</div>
            )}
          </section>

          {/* Memory Danger Zone */}
          <section className="mb-8">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2 text-destructive">
              <AlertTriangle className="w-5 h-5" />
              Danger Zone
            </h2>

            <div className="p-4 border border-destructive/30 rounded-lg bg-destructive/5">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">Delete All Memories</div>
                  <div className="text-sm text-muted-foreground">
                    Permanently delete all user and project memories. This cannot be undone.
                  </div>
                </div>
                <button
                  onClick={initiateAllMemoryPurge}
                  disabled={!stats || stats.totalMemories === 0}
                  className="px-4 py-2 bg-destructive text-destructive-foreground rounded-md text-sm font-medium hover:bg-destructive/90 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Delete All
                </button>
              </div>
            </div>
          </section>
        </>
      )}

      {/* Account Tab */}
      {activeTab === "account" && (
        <section className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <User className="w-5 h-5" />
              Account Data
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

          {isLoadingDangerStats ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : dangerStats ? (
            <>
              {/* Data Summary */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                <div className="p-4 border border-border rounded-lg text-center">
                  <MessageSquare className="w-5 h-5 mx-auto mb-2 text-muted-foreground" />
                  <div className="text-2xl font-bold">{dangerStats.chat_sessions}</div>
                  <div className="text-xs text-muted-foreground">Chat Sessions</div>
                </div>
                <div className="p-4 border border-border rounded-lg text-center">
                  <Brain className="w-5 h-5 mx-auto mb-2 text-muted-foreground" />
                  <div className="text-2xl font-bold">{dangerStats.memories}</div>
                  <div className="text-xs text-muted-foreground">Memories</div>
                </div>
                <div className="p-4 border border-border rounded-lg text-center">
                  <FileText className="w-5 h-5 mx-auto mb-2 text-muted-foreground" />
                  <div className="text-2xl font-bold">{dangerStats.deliverables}</div>
                  <div className="text-xs text-muted-foreground">Deliverables</div>
                </div>
                <div className="p-4 border border-border rounded-lg text-center">
                  <FolderOpen className="w-5 h-5 mx-auto mb-2 text-muted-foreground" />
                  <div className="text-2xl font-bold">{dangerStats.projects}</div>
                  <div className="text-xs text-muted-foreground">Projects</div>
                </div>
              </div>

              {/* Danger Zone */}
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-destructive">
                <AlertTriangle className="w-5 h-5" />
                Danger Zone
              </h3>

              <div className="space-y-4">
                {/* Tier 1: Clear Data */}
                <div className="p-4 border border-border rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium flex items-center gap-2">
                        <MessageSquare className="w-4 h-4" />
                        Clear Conversation History
                      </div>
                      <div className="text-sm text-muted-foreground">
                        Delete all {dangerStats.chat_sessions} chat sessions. Start fresh with your Thinking Partner.
                      </div>
                    </div>
                    <button
                      onClick={() => initiateDangerAction("chat")}
                      disabled={dangerStats.chat_sessions === 0}
                      className="px-4 py-2 border border-border rounded-md text-sm font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Clear History
                    </button>
                  </div>
                </div>

                {/* Tier 2: Delete Deliverables */}
                <div className="p-4 border border-destructive/30 rounded-lg bg-destructive/5">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium flex items-center gap-2">
                        <FileText className="w-4 h-4" />
                        Delete All Deliverables
                      </div>
                      <div className="text-sm text-muted-foreground">
                        Remove all {dangerStats.deliverables} deliverables and {dangerStats.deliverable_versions} versions. Returns you to onboarding.
                      </div>
                    </div>
                    <button
                      onClick={() => initiateDangerAction("deliverables")}
                      disabled={dangerStats.deliverables === 0}
                      className="px-4 py-2 bg-destructive/10 text-destructive border border-destructive/30 rounded-md text-sm font-medium hover:bg-destructive/20 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Delete All
                    </button>
                  </div>
                </div>

                {/* Tier 2: Full Reset */}
                <div className="p-4 border border-destructive/30 rounded-lg bg-destructive/5">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium flex items-center gap-2">
                        <RefreshCw className="w-4 h-4" />
                        Full Account Reset
                      </div>
                      <div className="text-sm text-muted-foreground">
                        Delete everything: deliverables, chat history, memories, documents, projects.
                        Your account and subscription remain active.
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

                {/* Tier 3: Deactivate */}
                <div className="p-4 border border-destructive rounded-lg bg-destructive/10">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium flex items-center gap-2">
                        <LogOut className="w-4 h-4" />
                        Deactivate Account
                      </div>
                      <div className="text-sm text-muted-foreground">
                        Permanently delete your account and all data. This cannot be undone.
                        You will be logged out immediately.
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
                {dangerAction === "deactivate" ? "Deactivate Account?" : "Confirm Deletion"}
              </h3>
            </div>

            <p className="text-muted-foreground mb-6">
              {dangerAction === "memories" && purgeTarget === "user" && (
                <>
                  Are you sure you want to delete all <strong>{stats?.userMemories}</strong> user
                  memories? This will remove everything yarnnn has learned about you.
                </>
              )}
              {dangerAction === "memories" && purgeTarget === "project" && selectedProjectId && (
                <>
                  Are you sure you want to delete all{" "}
                  <strong>{stats?.projectMemories.get(selectedProjectId)?.count}</strong> memories
                  from <strong>{stats?.projectMemories.get(selectedProjectId)?.name}</strong>?
                </>
              )}
              {dangerAction === "memories" && purgeTarget === "all" && (
                <>
                  Are you sure you want to delete <strong>ALL {stats?.totalMemories}</strong>{" "}
                  memories? This will completely reset yarnnn&apos;s knowledge about you.
                </>
              )}
              {dangerAction === "chat" && (
                <>
                  Are you sure you want to delete all <strong>{dangerStats?.chat_sessions}</strong> chat
                  sessions? Your conversation history will be permanently erased.
                </>
              )}
              {dangerAction === "deliverables" && (
                <>
                  Are you sure you want to delete all <strong>{dangerStats?.deliverables}</strong>{" "}
                  deliverables and <strong>{dangerStats?.deliverable_versions}</strong> versions?
                  You will return to the onboarding flow.
                </>
              )}
              {dangerAction === "reset" && (
                <>
                  Are you sure you want to <strong>reset your entire account</strong>? This will delete:
                  <ul className="list-disc list-inside mt-2 text-sm">
                    <li>{dangerStats?.deliverables} deliverables</li>
                    <li>{dangerStats?.chat_sessions} chat sessions</li>
                    <li>{dangerStats?.memories} memories</li>
                    <li>{dangerStats?.documents} documents</li>
                    <li>{dangerStats?.projects} projects</li>
                  </ul>
                  <span className="block mt-2">Your account will remain active but empty.</span>
                </>
              )}
              {dangerAction === "deactivate" && (
                <>
                  <strong>This action is permanent and cannot be undone.</strong>
                  <br /><br />
                  All your data will be permanently deleted and you will be logged out immediately.
                  To use yarnnn again, you would need to create a new account.
                </>
              )}
            </p>

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => {
                  setShowConfirm(false);
                  setPurgeTarget(null);
                  setSelectedProjectId(null);
                  setDangerAction(null);
                }}
                className="px-4 py-2 border border-border rounded-md"
                disabled={isPurging}
              >
                Cancel
              </button>
              <button
                onClick={dangerAction === "memories" ? handleMemoryPurge : handleDangerAction}
                disabled={isPurging}
                className="px-4 py-2 bg-destructive text-destructive-foreground rounded-md flex items-center gap-2"
              >
                {isPurging && <Loader2 className="w-4 h-4 animate-spin" />}
                {isPurging
                  ? "Processing..."
                  : dangerAction === "deactivate"
                  ? "Deactivate Account"
                  : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
