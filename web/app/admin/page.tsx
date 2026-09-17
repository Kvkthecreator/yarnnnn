"use client";

/**
 * The operator console (ADR-655).
 *
 * Keyed on the workspace, because the workspace is the substrate's binding unit
 * (ADR-373/378). Every figure here has a live writer, verified against prod —
 * a figure with no live source is deleted, not carried at zero (D2). The
 * predecessor rendered a Tasks card over a 0-row table and an Email column that
 * read "unknown" for all 21 workspaces.
 */

import { useEffect, useState } from "react";
import { api } from "@/lib/api/client";
import { formatLedgerTime } from "@/lib/formatting";
import type {
  AdminOverviewStats,
  AdminExecutionStats,
  AdminWorkspaceRow,
} from "@/types/admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatCard } from "@/components/admin/StatCard";
import {
  Boxes,
  KeyRound,
  MessageSquare,
  AlertCircle,
  DollarSign,
  Activity,
  Clock,
} from "lucide-react";
import { Working } from "@/components/shared/Working";

/** A heartbeat older than this means the scheduler is not draining. */
const HEARTBEAT_STALE_MS = 30 * 60 * 1000;

export default function OperatorConsolePage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [overview, setOverview] = useState<AdminOverviewStats | null>(null);
  const [execStats, setExecStats] = useState<AdminExecutionStats | null>(null);
  const [workspaces, setWorkspaces] = useState<AdminWorkspaceRow[]>([]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [ov, ex, ws] = await Promise.all([
        api.admin.stats(),
        api.admin.executionStats(),
        api.admin.workspaces(),
      ]);
      setOverview(ov);
      setExecStats(ex);
      setWorkspaces(ws);
    } catch (err) {
      console.error("Failed to load the console:", err);
      setError(err instanceof Error ? err.message : "Failed to load the console");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // ADR-429 §12.3a — toggle a workspace's billing-exempt (comp) state.
  // Optimistic: flip locally, call the route, revert on failure.
  const [exemptPending, setExemptPending] = useState<string | null>(null);
  const handleToggleExempt = async (row: AdminWorkspaceRow) => {
    const next = !row.billing_exempt;
    setExemptPending(row.id);
    setWorkspaces((prev) =>
      prev.map((w) => (w.id === row.id ? { ...w, billing_exempt: next } : w)),
    );
    try {
      await api.admin.setBillingExempt(row.id, next);
    } catch (err) {
      console.error("Failed to toggle billing exempt:", err);
      setWorkspaces((prev) =>
        prev.map((w) => (w.id === row.id ? { ...w, billing_exempt: !next } : w)),
      );
    } finally {
      setExemptPending(null);
    }
  };

  /**
   * How a workspace identifies itself. The resolver returns a display name or
   * nothing; a workspace that does not resolve still says which one it is,
   * rather than rendering "unknown" — which reads as data loss when it is only
   * a missing join (ADR-655 D3).
   */
  const identify = (w: AdminWorkspaceRow) => ({
    primary: w.name || w.owner_label || `Workspace ${w.id.slice(0, 8)}`,
    secondary: w.owner_label ?? w.id.slice(0, 8),
  });

  if (loading) {
    return <Working label="Loading the console…" fill className="py-20" />;
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <AlertCircle className="w-8 h-8 text-destructive mb-2" />
        <p className="text-destructive font-medium">The console could not load</p>
        <p className="text-sm text-muted-foreground mt-1">{error}</p>
      </div>
    );
  }

  const heartbeatAt = execStats?.last_scheduler_heartbeat
    ? new Date(execStats.last_scheduler_heartbeat).getTime()
    : null;
  const heartbeatStale =
    heartbeatAt === null || Date.now() - heartbeatAt > HEARTBEAT_STALE_MS;

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      <div>
        <h1 className="text-2xl font-semibold">Console</h1>
        <p className="text-muted-foreground mt-1">
          What the platform is doing, and what it costs.
        </p>
      </div>

      {/* Platform totals */}
      {overview && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <StatCard
            label="Workspaces"
            value={overview.total_workspaces}
            trend={overview.workspaces_7d}
            trendLabel="7d"
            icon={Boxes}
          />
          <StatCard label="Grants" value={overview.total_grants} icon={KeyRound} />
          <StatCard
            label="Sessions"
            value={overview.total_sessions}
            trend={overview.sessions_7d}
            trendLabel="7d"
            icon={MessageSquare}
          />
          <StatCard label="Messages" value={overview.total_messages} icon={MessageSquare} />
          <StatCard
            label="Spend (mo)"
            value={execStats ? `$${execStats.spend_usd_this_month.toFixed(2)}` : "—"}
            icon={DollarSign}
          />
        </div>
      )}

      {/* Scheduler health + the daily guard */}
      {execStats && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Activity className="w-4 h-4" />
              Scheduler
              <span
                className={`text-xs font-normal ml-auto flex items-center gap-1 ${
                  heartbeatStale ? "text-red-600" : "text-muted-foreground"
                }`}
              >
                <Clock className="w-3 h-3" />
                {execStats.last_scheduler_heartbeat
                  ? `Last beat ${formatLedgerTime(execStats.last_scheduler_heartbeat)}`
                  : "No heartbeat recorded"}
                <span className="ml-2">({execStats.heartbeats_24h} in 24h)</span>
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Today&apos;s spend</p>
                <p
                  className={`text-xl font-semibold tabular-nums ${
                    execStats.daily_spend_today >= execStats.daily_spend_ceiling
                      ? "text-red-600"
                      : execStats.daily_spend_today >= execStats.daily_spend_ceiling * 0.8
                        ? "text-yellow-600"
                        : ""
                  }`}
                >
                  ${execStats.daily_spend_today.toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Daily ceiling</p>
                <p className="text-xl font-semibold tabular-nums">
                  ${execStats.daily_spend_ceiling.toFixed(2)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* The workspaces */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Boxes className="w-4 h-4" />
            Workspaces
            <span className="text-xs font-normal text-muted-foreground ml-auto">
              Busiest first, last 7 days
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 px-2 font-medium text-muted-foreground">
                    Workspace
                  </th>
                  <th className="text-left py-2 px-2 font-medium text-muted-foreground">Tier</th>
                  <th
                    className="text-right py-2 px-2 font-medium text-muted-foreground"
                    title="Principals with a grant on this workspace (ADR-405)"
                  >
                    Reach
                  </th>
                  <th className="text-right py-2 px-2 font-medium text-muted-foreground">
                    Events 7d
                  </th>
                  <th className="text-right py-2 px-2 font-medium text-muted-foreground">
                    Spend 7d
                  </th>
                  <th className="text-right py-2 px-2 font-medium text-muted-foreground">
                    Balance
                  </th>
                  <th className="text-right py-2 px-2 font-medium text-muted-foreground">
                    Last active
                  </th>
                  <th
                    className="text-center py-2 px-2 font-medium text-muted-foreground"
                    title="Billing-exempt: the workspace pays nothing (ADR-429 §12.3a)"
                  >
                    Comp
                  </th>
                </tr>
              </thead>
              <tbody>
                {workspaces.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-muted-foreground">
                      No workspaces yet.
                    </td>
                  </tr>
                ) : (
                  workspaces.map((w) => {
                    const id = identify(w);
                    return (
                      <tr key={w.id} className="border-b last:border-0 hover:bg-muted/50">
                        <td className="py-2 px-2">
                          <div className="truncate max-w-[220px]" title={w.id}>
                            {id.primary}
                          </div>
                          <div className="text-xs text-muted-foreground truncate max-w-[220px]">
                            {id.secondary}
                          </div>
                        </td>
                        <td className="py-2 px-2">
                          <span
                            className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${
                              w.tier === "free"
                                ? "bg-gray-100 text-gray-700"
                                : "bg-purple-100 text-purple-700"
                            }`}
                          >
                            {w.tier}
                          </span>
                        </td>
                        <td className="py-2 px-2 text-right tabular-nums">{w.grant_count}</td>
                        <td className="py-2 px-2 text-right tabular-nums">{w.events_7d}</td>
                        <td className="py-2 px-2 text-right tabular-nums">
                          ${w.spend_7d.toFixed(2)}
                        </td>
                        <td className="py-2 px-2 text-right tabular-nums">
                          ${w.balance_usd.toFixed(2)}
                        </td>
                        <td className="py-2 px-2 text-right text-muted-foreground text-xs">
                          {w.last_activity ? formatLedgerTime(w.last_activity) : "—"}
                        </td>
                        <td className="py-2 px-2 text-center">
                          <button
                            type="button"
                            disabled={exemptPending === w.id}
                            onClick={() => handleToggleExempt(w)}
                            title={
                              w.billing_exempt
                                ? "Comped — click to bill normally"
                                : "Billing normally — click to comp"
                            }
                            className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium transition-colors disabled:opacity-40 ${
                              w.billing_exempt
                                ? "bg-emerald-100 text-emerald-700 hover:bg-emerald-200"
                                : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                            }`}
                          >
                            {w.billing_exempt ? "Comped" : "Bill"}
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
