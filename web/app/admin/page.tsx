"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api/client";
import type {
  AdminOverviewStats,
  AdminTokenUsage,
  AdminExecutionStats,
  AdminUserRow,
} from "@/types/admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatCard } from "@/components/admin/StatCard";
import {
  Users,
  Zap,
  MessageSquare,
  ListTodo,
  Bot,
  Loader2,
  AlertCircle,
  Download,
  DollarSign,
  Activity,
  Clock,
  TrendingDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";

export default function AdminDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  const [overview, setOverview] = useState<AdminOverviewStats | null>(null);
  const [tokenUsage, setTokenUsage] = useState<AdminTokenUsage | null>(null);
  const [execStats, setExecStats] = useState<AdminExecutionStats | null>(null);
  const [users, setUsers] = useState<AdminUserRow[]>([]);
  const [tokenDays, setTokenDays] = useState(7);

  const fetchData = async (days: number = 7) => {
    try {
      setLoading(true);
      setError(null);

      const [ov, tu, ex, us] = await Promise.all([
        api.admin.stats(),
        api.admin.tokenUsage(days),
        api.admin.executionStats(),
        api.admin.users(),
      ]);

      setOverview(ov);
      setTokenUsage(tu);
      setExecStats(ex);
      setUsers(us);
    } catch (err) {
      console.error("Failed to fetch admin stats:", err);
      setError(err instanceof Error ? err.message : "Failed to fetch stats");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(tokenDays);
  }, [tokenDays]);

  const handleExportReport = async () => {
    try {
      setExporting(true);
      await api.admin.exportReport();
    } catch (err) {
      console.error("Failed to export:", err);
    } finally {
      setExporting(false);
    }
  };

  const formatDate = (dateStr: string) =>
    new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

  const formatTokens = (n: number) => {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
    return n.toString();
  };

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

  // Aggregate token usage by day (combine callers)
  const dailyCosts: Record<string, { chat: number; pipeline: number; total: number }> = {};
  if (tokenUsage) {
    for (const row of tokenUsage.by_day) {
      if (!dailyCosts[row.date]) {
        dailyCosts[row.date] = { chat: 0, pipeline: 0, total: 0 };
      }
      const day = dailyCosts[row.date];
      if (row.caller === "chat") {
        day.chat += row.estimated_cost_usd;
      } else {
        day.pipeline += row.estimated_cost_usd;
      }
      day.total += row.estimated_cost_usd;
    }
  }

  // Max cost for chart scaling
  const maxDailyCost = Math.max(...Object.values(dailyCosts).map((d) => d.total), 0.01);

  return (
    <div className="space-y-8 max-w-6xl mx-auto p-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Admin Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Operational metrics & cost analytics
          </p>
        </div>
        <Button
          variant="default"
          onClick={handleExportReport}
          disabled={exporting || loading}
        >
          {exporting ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Download className="w-4 h-4 mr-2" />
          )}
          Export Report
        </Button>
      </div>

      {/* Overview Stats */}
      {overview && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <StatCard label="Users" value={overview.total_users} trend={overview.users_7d} trendLabel="7d" icon={Users} />
          <StatCard label="Agents" value={overview.total_agents} icon={Bot} />
          <StatCard label="Tasks" value={overview.total_tasks} trend={overview.tasks_7d} trendLabel="7d" icon={ListTodo} />
          <StatCard label="Sessions" value={overview.total_sessions} trend={overview.sessions_7d} trendLabel="7d" icon={MessageSquare} />
          <StatCard label="Messages" value={overview.total_messages} icon={MessageSquare} />
          <StatCard
            label="Spend (mo)"
            value={execStats ? `$${(execStats.spend_usd_this_month ?? 0).toFixed(2)}/$${(execStats.spend_usd_limit ?? 0).toFixed(2)}` : "—"}
            icon={Zap}
          />
        </div>
      )}

      {/* Token & Cost Analytics */}
      {tokenUsage && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <DollarSign className="w-4 h-4" />
                Token Usage & Cost
              </CardTitle>
              <div className="flex gap-1">
                {[7, 14, 30].map((d) => (
                  <Button
                    key={d}
                    variant={tokenDays === d ? "default" : "outline"}
                    size="sm"
                    onClick={() => setTokenDays(d)}
                    className="text-xs px-2 h-7"
                  >
                    {d}d
                  </Button>
                ))}
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Summary row */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Total Cost</p>
                <p className="text-2xl font-semibold">
                  ${tokenUsage.total_estimated_cost_usd.toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Billed Input</p>
                <p className="text-xl font-semibold">{formatTokens(tokenUsage.total_billed_input_tokens)}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Output Tokens</p>
                <p className="text-xl font-semibold">{formatTokens(tokenUsage.total_output_tokens)}</p>
              </div>
              <div>
                <p className="text-muted-foreground">API Calls</p>
                <p className="text-xl font-semibold">{tokenUsage.total_api_calls}</p>
              </div>
              <div>
                <p className="text-muted-foreground flex items-center gap-1">
                  <TrendingDown className="w-3 h-3" /> Cache Hit
                </p>
                <p className={`text-xl font-semibold ${tokenUsage.cache_hit_pct > 0 ? "text-green-600" : "text-yellow-600"}`}>
                  {tokenUsage.cache_hit_pct.toFixed(1)}%
                </p>
              </div>
            </div>

            {/* Daily cost chart (simple bar chart via divs) */}
            {Object.keys(dailyCosts).length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground mb-2">Daily Cost (Chat vs Pipeline)</p>
                <div className="flex items-end gap-1 h-32">
                  {Object.entries(dailyCosts)
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([date, costs]) => {
                      const chatPct = costs.total > 0 ? (costs.chat / costs.total) * 100 : 0;
                      const pipelinePct = 100 - chatPct;
                      const heightPct = (costs.total / maxDailyCost) * 100;
                      return (
                        <div key={date} className="flex-1 flex flex-col items-center gap-1 min-w-0">
                          <div
                            className="w-full rounded-t-sm overflow-hidden flex flex-col justify-end"
                            style={{ height: `${Math.max(heightPct, 2)}%` }}
                            title={`${date}: $${costs.total.toFixed(2)} (chat: $${costs.chat.toFixed(2)}, pipeline: $${costs.pipeline.toFixed(2)})`}
                          >
                            <div
                              className="bg-blue-400 w-full"
                              style={{ height: `${chatPct}%` }}
                            />
                            <div
                              className="bg-orange-400 w-full"
                              style={{ height: `${pipelinePct}%` }}
                            />
                          </div>
                          <span className="text-[9px] text-muted-foreground truncate w-full text-center">
                            {date.slice(5)}
                          </span>
                        </div>
                      );
                    })}
                </div>
                <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <span className="w-3 h-3 bg-blue-400 rounded-sm inline-block" /> Chat
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-3 h-3 bg-orange-400 rounded-sm inline-block" /> Task Pipeline
                  </span>
                </div>
              </div>
            )}

            {/* Per-caller breakdown table */}
            {tokenUsage.by_day.length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground mb-2">Breakdown by Day & Caller</p>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-1.5 px-2 font-medium text-muted-foreground">Date</th>
                        <th className="text-left py-1.5 px-2 font-medium text-muted-foreground">Caller</th>
                        <th className="text-right py-1.5 px-2 font-medium text-muted-foreground">Calls</th>
                        <th className="text-right py-1.5 px-2 font-medium text-muted-foreground">Billed Input</th>
                        <th className="text-right py-1.5 px-2 font-medium text-muted-foreground">Output</th>
                        <th className="text-right py-1.5 px-2 font-medium text-muted-foreground">Cache Read</th>
                        <th className="text-right py-1.5 px-2 font-medium text-muted-foreground">Cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tokenUsage.by_day
                        .sort((a, b) => b.date.localeCompare(a.date) || a.caller.localeCompare(b.caller))
                        .map((row, i) => (
                          <tr key={i} className="border-b last:border-0 hover:bg-muted/50">
                            <td className="py-1.5 px-2">{row.date}</td>
                            <td className="py-1.5 px-2">
                              <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${
                                row.caller === "chat"
                                  ? "bg-blue-100 text-blue-700"
                                  : "bg-orange-100 text-orange-700"
                              }`}>
                                {row.caller}
                              </span>
                            </td>
                            <td className="py-1.5 px-2 text-right tabular-nums">{row.api_calls}</td>
                            <td className="py-1.5 px-2 text-right tabular-nums">{formatTokens(row.billed_input_tokens)}</td>
                            <td className="py-1.5 px-2 text-right tabular-nums">{formatTokens(row.output_tokens)}</td>
                            <td className="py-1.5 px-2 text-right tabular-nums">{formatTokens(row.cache_read_tokens)}</td>
                            <td className="py-1.5 px-2 text-right tabular-nums font-medium">${row.estimated_cost_usd.toFixed(2)}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Execution Stats */}
      {execStats && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Activity className="w-4 h-4" />
              Task Execution
              {execStats.last_scheduler_heartbeat && (
                <span className="text-xs font-normal text-muted-foreground ml-auto flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  Last heartbeat: {formatDate(execStats.last_scheduler_heartbeat)}
                  <span className="ml-2">({execStats.heartbeats_24h} in 24h)</span>
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Run summary + daily spend guard status */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Runs (24h)</p>
                <p className="text-xl font-semibold">{execStats.total_runs_24h}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Runs (7d)</p>
                <p className="text-xl font-semibold">{execStats.total_runs_7d}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Runs (30d)</p>
                <p className="text-xl font-semibold">{execStats.total_runs_30d}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Today's Spend</p>
                <p className={`text-xl font-semibold ${
                  execStats.daily_spend_today >= execStats.daily_spend_ceiling
                    ? "text-red-600"
                    : execStats.daily_spend_today >= execStats.daily_spend_ceiling * 0.8
                    ? "text-yellow-600"
                    : ""
                }`}>
                  ${execStats.daily_spend_today.toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Daily Ceiling</p>
                <p className="text-xl font-semibold">${execStats.daily_spend_ceiling.toFixed(2)}</p>
              </div>
            </div>

            {/* Per-task table */}
            {execStats.tasks.length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground mb-2">Per-Task Breakdown (30d) — cost from execution_events</p>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-1.5 px-2 font-medium text-muted-foreground">Task</th>
                        <th className="text-left py-1.5 px-2 font-medium text-muted-foreground">Agent</th>
                        <th className="text-right py-1.5 px-2 font-medium text-muted-foreground">Runs</th>
                        <th className="text-right py-1.5 px-2 font-medium text-muted-foreground">7d</th>
                        <th className="text-right py-1.5 px-2 font-medium text-muted-foreground">Cost (30d)</th>
                        <th className="text-right py-1.5 px-2 font-medium text-muted-foreground">Failed</th>
                        <th className="text-right py-1.5 px-2 font-medium text-muted-foreground">Avg Input</th>
                        <th className="text-right py-1.5 px-2 font-medium text-muted-foreground">Last Run</th>
                      </tr>
                    </thead>
                    <tbody>
                      {execStats.tasks.map((task, i) => (
                        <tr key={i} className="border-b last:border-0 hover:bg-muted/50">
                          <td className="py-1.5 px-2 font-mono text-xs">{task.task_slug}</td>
                          <td className="py-1.5 px-2">
                            <span className="text-xs">{task.agent_title}</span>
                            <span className="text-[10px] text-muted-foreground ml-1">({task.agent_role})</span>
                          </td>
                          <td className="py-1.5 px-2 text-right tabular-nums font-medium">{task.runs_total}</td>
                          <td className="py-1.5 px-2 text-right tabular-nums">{task.runs_7d}</td>
                          <td className="py-1.5 px-2 text-right tabular-nums font-medium">
                            {task.cost_usd_total != null
                              ? <span className={task.cost_usd_total > 5 ? "text-red-600" : ""}>${task.cost_usd_total.toFixed(2)}</span>
                              : <span className="text-muted-foreground text-xs">—</span>}
                          </td>
                          <td className="py-1.5 px-2 text-right tabular-nums">
                            {task.failed_count > 0
                              ? <span className="text-red-600 font-medium">{task.failed_count}</span>
                              : <span className="text-muted-foreground">0</span>}
                            {task.skipped_count > 0 &&
                              <span className="text-yellow-600 text-xs ml-1">+{task.skipped_count}s</span>}
                          </td>
                          <td className="py-1.5 px-2 text-right tabular-nums">{formatTokens(task.avg_input_tokens)}</td>
                          <td className="py-1.5 px-2 text-right text-muted-foreground text-xs">
                            {task.last_run_at ? formatDate(task.last_run_at) : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Users Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Users className="w-4 h-4" />
            Users
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={async () => {
              try {
                await api.admin.exportUsers();
              } catch (err) {
                console.error("Failed to export users:", err);
              }
            }}
            disabled={users.length === 0}
          >
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 px-2 font-medium text-muted-foreground">Email</th>
                  <th className="text-left py-2 px-2 font-medium text-muted-foreground">Tier</th>
                  <th className="text-right py-2 px-2 font-medium text-muted-foreground">Agents</th>
                  <th className="text-right py-2 px-2 font-medium text-muted-foreground">Tasks</th>
                  <th className="text-right py-2 px-2 font-medium text-muted-foreground">Sessions</th>
                  <th className="text-right py-2 px-2 font-medium text-muted-foreground">Spend (mo)</th>
                  <th className="text-right py-2 px-2 font-medium text-muted-foreground">Last Active</th>
                </tr>
              </thead>
              <tbody>
                {users.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-muted-foreground">
                      No users found
                    </td>
                  </tr>
                ) : (
                  users.map((user) => (
                    <tr key={user.id} className="border-b last:border-0 hover:bg-muted/50">
                      <td className="py-2 px-2 truncate max-w-[200px]" title={user.email}>
                        {user.email}
                      </td>
                      <td className="py-2 px-2">
                        <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${
                          user.tier === "pro"
                            ? "bg-purple-100 text-purple-700"
                            : "bg-gray-100 text-gray-700"
                        }`}>
                          {user.tier}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-right">{user.agent_count}</td>
                      <td className="py-2 px-2 text-right">{user.task_count}</td>
                      <td className="py-2 px-2 text-right">{user.session_count}</td>
                      <td className="py-2 px-2 text-right">${user.spend_usd?.toFixed(2) ?? "—"}</td>
                      <td className="py-2 px-2 text-right text-muted-foreground text-xs">
                        {user.last_activity ? formatDate(user.last_activity) : "—"}
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
