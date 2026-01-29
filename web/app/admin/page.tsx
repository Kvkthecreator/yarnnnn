"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api/client";
import type {
  AdminOverviewStats,
  AdminMemoryStats,
  AdminDocumentStats,
  AdminChatStats,
  AdminUserRow,
} from "@/types/admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatCard } from "@/components/admin/StatCard";
import {
  Users,
  FolderKanban,
  Brain,
  FileText,
  MessageSquare,
  Activity,
  Loader2,
  AlertCircle,
  Download,
} from "lucide-react";
import { Button } from "@/components/ui/button";

export default function AdminDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  const [overviewStats, setOverviewStats] = useState<AdminOverviewStats | null>(null);
  const [memoryStats, setMemoryStats] = useState<AdminMemoryStats | null>(null);
  const [documentStats, setDocumentStats] = useState<AdminDocumentStats | null>(null);
  const [chatStats, setChatStats] = useState<AdminChatStats | null>(null);
  const [users, setUsers] = useState<AdminUserRow[]>([]);

  const handleExportUsers = async () => {
    try {
      setExporting(true);
      await api.admin.exportUsers();
    } catch (err) {
      console.error("Failed to export users:", err);
    } finally {
      setExporting(false);
    }
  };

  useEffect(() => {
    const fetchAllStats = async () => {
      try {
        setLoading(true);
        setError(null);

        const [overview, memory, document, chat, userList] = await Promise.all([
          api.admin.stats(),
          api.admin.memoryStats(),
          api.admin.documentStats(),
          api.admin.chatStats(),
          api.admin.users(),
        ]);

        setOverviewStats(overview);
        setMemoryStats(memory);
        setDocumentStats(document);
        setChatStats(chat);
        setUsers(userList);
      } catch (err) {
        console.error("Failed to fetch admin stats:", err);
        setError(err instanceof Error ? err.message : "Failed to fetch stats");
      } finally {
        setLoading(false);
      }
    };

    fetchAllStats();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <AlertCircle className="w-8 h-8 text-destructive mb-2" />
        <p className="text-destructive font-medium">Error loading dashboard</p>
        <p className="text-sm text-muted-foreground mt-1">{error}</p>
      </div>
    );
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Dashboard Overview</h1>
        <p className="text-muted-foreground mt-1">
          System-wide metrics and user activity
        </p>
      </div>

      {/* Overview Stats */}
      {overviewStats && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <StatCard
            label="Total Users"
            value={overviewStats.total_users}
            trend={overviewStats.users_7d}
            trendLabel="7d"
            icon={Users}
          />
          <StatCard
            label="Projects"
            value={overviewStats.total_projects}
            trend={overviewStats.projects_7d}
            trendLabel="7d"
            icon={FolderKanban}
          />
          <StatCard
            label="Memories"
            value={overviewStats.total_memories}
            trend={overviewStats.memories_7d}
            trendLabel="7d"
            icon={Brain}
          />
          <StatCard
            label="Documents"
            value={overviewStats.total_documents}
            icon={FileText}
          />
          <StatCard
            label="Sessions"
            value={overviewStats.total_sessions}
            icon={MessageSquare}
          />
          <StatCard
            label="Active Sessions"
            value={chatStats?.active_sessions ?? 0}
            icon={Activity}
          />
        </div>
      )}

      {/* Memory & Document Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Memory System */}
        {memoryStats && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Brain className="w-4 h-4" />
                Memory System
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">By Source</p>
                  <ul className="mt-1 space-y-1">
                    <li>Chat: <span className="font-medium">{memoryStats.by_source.chat}</span></li>
                    <li>Document: <span className="font-medium">{memoryStats.by_source.document}</span></li>
                    <li>Manual: <span className="font-medium">{memoryStats.by_source.manual}</span></li>
                    <li>Import: <span className="font-medium">{memoryStats.by_source.import}</span></li>
                  </ul>
                </div>
                <div>
                  <p className="text-muted-foreground">By Scope</p>
                  <ul className="mt-1 space-y-1">
                    <li>User-scoped: <span className="font-medium">{memoryStats.by_scope.user_scoped}</span></li>
                    <li>Project-scoped: <span className="font-medium">{memoryStats.by_scope.project_scoped}</span></li>
                  </ul>
                  <p className="text-muted-foreground mt-3">Avg Importance</p>
                  <p className="font-medium">{memoryStats.avg_importance.toFixed(2)}</p>
                </div>
              </div>
              {memoryStats.total_soft_deleted > 0 && (
                <p className="text-xs text-muted-foreground">
                  {memoryStats.total_soft_deleted} soft-deleted memories
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {/* Document Pipeline */}
        {documentStats && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Document Pipeline
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Processing Status</p>
                  <ul className="mt-1 space-y-1">
                    <li>Completed: <span className="font-medium text-green-600">{documentStats.by_status.completed}</span></li>
                    <li>Processing: <span className="font-medium text-blue-600">{documentStats.by_status.processing}</span></li>
                    <li>Pending: <span className="font-medium text-yellow-600">{documentStats.by_status.pending}</span></li>
                    {documentStats.by_status.failed > 0 && (
                      <li>Failed: <span className="font-medium text-red-600">{documentStats.by_status.failed}</span></li>
                    )}
                  </ul>
                </div>
                <div>
                  <p className="text-muted-foreground">Storage</p>
                  <p className="font-medium">{formatBytes(documentStats.total_storage_bytes)}</p>
                  <p className="text-muted-foreground mt-3">Total Chunks</p>
                  <p className="font-medium">{documentStats.total_chunks}</p>
                  <p className="text-muted-foreground mt-3">Avg Chunks/Doc</p>
                  <p className="font-medium">{documentStats.avg_chunks_per_doc.toFixed(1)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Chat Engagement */}
      {chatStats && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <MessageSquare className="w-4 h-4" />
              Chat Engagement
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Total Sessions</p>
                <p className="text-xl font-semibold">{chatStats.total_sessions}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Active Sessions</p>
                <p className="text-xl font-semibold">{chatStats.active_sessions}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Total Messages</p>
                <p className="text-xl font-semibold">{chatStats.total_messages}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Avg Msgs/Session</p>
                <p className="text-xl font-semibold">{chatStats.avg_messages_per_session.toFixed(1)}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Sessions Today</p>
                <p className="text-xl font-semibold">{chatStats.sessions_today}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Users Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Users className="w-4 h-4" />
            Recent Users
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportUsers}
            disabled={exporting || users.length === 0}
          >
            {exporting ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Download className="w-4 h-4 mr-2" />
            )}
            Export Excel
          </Button>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 px-2 font-medium text-muted-foreground">Email</th>
                  <th className="text-right py-2 px-2 font-medium text-muted-foreground">Projects</th>
                  <th className="text-right py-2 px-2 font-medium text-muted-foreground">Memories</th>
                  <th className="text-right py-2 px-2 font-medium text-muted-foreground">Sessions</th>
                  <th className="text-right py-2 px-2 font-medium text-muted-foreground">Last Active</th>
                  <th className="text-right py-2 px-2 font-medium text-muted-foreground">Joined</th>
                </tr>
              </thead>
              <tbody>
                {users.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-muted-foreground">
                      No users found
                    </td>
                  </tr>
                ) : (
                  users.map((user) => (
                    <tr key={user.id} className="border-b last:border-0 hover:bg-muted/50">
                      <td className="py-2 px-2 truncate max-w-[200px]" title={user.email}>
                        {user.email}
                      </td>
                      <td className="py-2 px-2 text-right">{user.project_count}</td>
                      <td className="py-2 px-2 text-right">{user.memory_count}</td>
                      <td className="py-2 px-2 text-right">{user.session_count}</td>
                      <td className="py-2 px-2 text-right text-muted-foreground">
                        {user.last_activity ? formatDate(user.last_activity) : "—"}
                      </td>
                      <td className="py-2 px-2 text-right text-muted-foreground">
                        {formatDate(user.created_at)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
