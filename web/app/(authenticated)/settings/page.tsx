"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
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
} from "lucide-react";
import { api } from "@/lib/api/client";
import type { Project } from "@/types";
import { SubscriptionCard } from "@/components/subscription/SubscriptionCard";
import { UsageIndicator } from "@/components/subscription/UpgradePrompt";
import { useSubscriptionGate } from "@/hooks/useSubscriptionGate";
import { SUBSCRIPTION_LIMITS } from "@/lib/subscription/limits";

interface MemoryStats {
  userMemories: number;
  projectMemories: Map<string, { name: string; count: number }>;
  totalMemories: number;
}

type SettingsTab = "memory" | "billing" | "usage";

export default function SettingsPage() {
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab");
  const initialTab: SettingsTab = tabParam === "billing" ? "billing" : tabParam === "usage" ? "usage" : "memory";
  const subscriptionSuccess = searchParams.get("subscription") === "success";

  const [activeTab, setActiveTab] = useState<SettingsTab>(initialTab);
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isPurging, setIsPurging] = useState(false);
  const [purgeTarget, setPurgeTarget] = useState<"user" | "project" | "all" | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const [purgeSuccess, setPurgeSuccess] = useState<string | null>(null);
  const [showSubscriptionSuccess, setShowSubscriptionSuccess] = useState(subscriptionSuccess);
  const { tier, projects: projectsLimit, isPro } = useSubscriptionGate();

  // Fetch stats on mount
  useEffect(() => {
    async function fetchStats() {
      try {
        // Fetch user memories
        const userMemories = await api.userMemories.list();

        // Fetch projects
        const projectList = await api.projects.list();
        setProjects(projectList);

        // Fetch project memories for each project
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

  const handlePurge = async () => {
    if (!purgeTarget) return;

    setIsPurging(true);
    setPurgeSuccess(null);

    try {
      if (purgeTarget === "user") {
        // Delete all user memories
        const memories = await api.userMemories.list();
        for (const mem of memories) {
          await api.memories.delete(mem.id);
        }
        setPurgeSuccess(`Deleted ${memories.length} user memories`);
      } else if (purgeTarget === "project" && selectedProjectId) {
        // Delete all memories for selected project
        const memories = await api.projectMemories.list(selectedProjectId);
        for (const mem of memories) {
          await api.memories.delete(mem.id);
        }
        const projectName = stats?.projectMemories.get(selectedProjectId)?.name || "project";
        setPurgeSuccess(`Deleted ${memories.length} memories from ${projectName}`);
      } else if (purgeTarget === "all") {
        // Delete all memories (user + all projects)
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

      // Refresh stats
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

  const initiateUserPurge = () => {
    setPurgeTarget("user");
    setShowConfirm(true);
  };

  const initiateProjectPurge = (projectId: string) => {
    setPurgeTarget("project");
    setSelectedProjectId(projectId);
    setShowConfirm(true);
  };

  const initiateAllPurge = () => {
    setPurgeTarget("all");
    setShowConfirm(true);
  };

  // Auto-dismiss subscription success message
  useEffect(() => {
    if (showSubscriptionSuccess) {
      const timer = setTimeout(() => setShowSubscriptionSuccess(false), 5000);
      return () => clearTimeout(timer);
    }
  }, [showSubscriptionSuccess]);

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
      <div className="flex gap-1 mb-8 border-b border-border">
        <button
          onClick={() => setActiveTab("memory")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
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
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
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
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
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
            {/* Projects */}
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

            {/* Memories */}
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

            {/* Documents */}
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

      {/* Memory Tab */}
      {activeTab === "memory" && (
        <>
      {/* Memory Stats */}
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
            {/* Summary Card */}
            <div className="p-4 border border-border rounded-lg bg-muted/30">
              <div className="text-3xl font-bold">{stats.totalMemories}</div>
              <div className="text-sm text-muted-foreground">Total memories stored</div>
            </div>

            {/* User Memories */}
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

            {/* Project Memories */}
            {projects.length > 0 && (
              <div className="space-y-2">
                <div className="text-sm font-medium text-muted-foreground px-1">
                  Project Memories
                </div>
                {projects.map((project) => {
                  const projectStats = stats.projectMemories.get(project.id);
                  return (
                    <div
                      key={project.id}
                      className="p-4 border border-border rounded-lg"
                    >
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

      {/* Danger Zone */}
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
              onClick={initiateAllPurge}
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

      {/* Success Message */}
      {purgeSuccess && (
        <div className="fixed bottom-4 right-4 flex items-center gap-2 px-4 py-3 bg-primary text-primary-foreground rounded-lg shadow-lg">
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
              <h3 className="text-lg font-semibold">Confirm Deletion</h3>
            </div>

            <p className="text-muted-foreground mb-6">
              {purgeTarget === "user" && (
                <>
                  Are you sure you want to delete all <strong>{stats?.userMemories}</strong> user
                  memories? This will remove everything Yarn has learned about you.
                </>
              )}
              {purgeTarget === "project" && selectedProjectId && (
                <>
                  Are you sure you want to delete all{" "}
                  <strong>{stats?.projectMemories.get(selectedProjectId)?.count}</strong> memories
                  from <strong>{stats?.projectMemories.get(selectedProjectId)?.name}</strong>?
                </>
              )}
              {purgeTarget === "all" && (
                <>
                  Are you sure you want to delete <strong>ALL {stats?.totalMemories}</strong>{" "}
                  memories? This will completely reset Yarn&apos;s knowledge about you and all
                  your projects.
                </>
              )}
            </p>

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => {
                  setShowConfirm(false);
                  setPurgeTarget(null);
                  setSelectedProjectId(null);
                }}
                className="px-4 py-2 border border-border rounded-md"
                disabled={isPurging}
              >
                Cancel
              </button>
              <button
                onClick={handlePurge}
                disabled={isPurging}
                className="px-4 py-2 bg-destructive text-destructive-foreground rounded-md flex items-center gap-2"
              >
                {isPurging && <Loader2 className="w-4 h-4 animate-spin" />}
                {isPurging ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
