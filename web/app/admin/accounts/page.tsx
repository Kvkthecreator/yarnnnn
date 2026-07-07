"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api/client";
import type { AdminAccountRow } from "@/types/admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Loader2,
  AlertCircle,
  Activity,
  DollarSign,
  GitCommitVertical,
  AlertTriangle,
} from "lucide-react";

/**
 * Admin → Accounts: per-persona live health for the designated test/eval
 * accounts (docs/alpha/personas.yaml). Hat-B surface per CLAUDE.md — dev-only,
 * never shown to real operators. Complements the markdown eval discipline in
 * docs/evaluations/ with substrate-derived live signal (wakes, cost, failures,
 * Reviewer self-amendments).
 */

function timeAgo(iso: string | null): string {
  if (!iso) return "never";
  const then = new Date(iso).getTime();
  const mins = Math.floor((Date.now() - then) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function isStale(iso: string | null): boolean {
  if (!iso) return true;
  return Date.now() - new Date(iso).getTime() > 24 * 60 * 60 * 1000;
}

export default function AdminAccountsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<AdminAccountRow[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        setAccounts(await api.admin.accounts());
      } catch (err) {
        console.error("Failed to fetch accounts:", err);
        setError(err instanceof Error ? err.message : "Failed to fetch accounts");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-muted-foreground">
        <Loader2 className="w-5 h-5 mr-2 animate-spin" />
        Loading test accounts…
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <AlertCircle className="w-8 h-8 mb-2 text-destructive" />
        <p className="font-medium">Error loading accounts</p>
        <p className="text-sm text-muted-foreground">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Test Accounts</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Live health for the eval personas in{" "}
          <code className="text-xs">docs/alpha/personas.yaml</code>. Wakes, cost,
          failures, and agent self-amendments — substrate-derived, no separate
          eval table. <span className="text-foreground">Click a row</span> for the
          full forensic view.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Activity className="w-4 h-4 text-muted-foreground" />
            Per-Persona Health
          </CardTitle>
        </CardHeader>
        <CardContent>
          {accounts.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4">
              No personas found. (personas.yaml may not be present in this deploy.)
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground">
                    <th className="py-2 pr-4 font-medium">Persona</th>
                    <th className="py-2 pr-4 font-medium">Program</th>
                    <th className="py-2 pr-4 font-medium text-right">Wakes 24h</th>
                    <th className="py-2 pr-4 font-medium text-right">Wakes 7d</th>
                    <th className="py-2 pr-4 font-medium text-right">Failed 7d</th>
                    <th className="py-2 pr-4 font-medium text-right">
                      <DollarSign className="w-3 h-3 inline -mt-0.5" /> 7d
                    </th>
                    <th className="py-2 pr-4 font-medium text-right">
                      <GitCommitVertical className="w-3 h-3 inline -mt-0.5" /> Agent 7d
                    </th>
                    <th className="py-2 pr-4 font-medium text-right">Last wake</th>
                  </tr>
                </thead>
                <tbody>
                  {accounts.map((a) => (
                    <tr
                      key={a.user_id}
                      onClick={() => router.push(`/admin/accounts/${a.slug}`)}
                      className="border-b border-border/50 hover:bg-muted/30 cursor-pointer"
                    >
                      <td className="py-2.5 pr-4">
                        <div className="font-medium">{a.slug}</div>
                        {a.label && (
                          <div className="text-xs text-muted-foreground max-w-xs truncate">
                            {a.label}
                          </div>
                        )}
                      </td>
                      <td className="py-2.5 pr-4 text-muted-foreground">
                        {a.program ?? "—"}
                      </td>
                      <td className="py-2.5 pr-4 text-right tabular-nums">
                        {a.wakes_24h}
                      </td>
                      <td className="py-2.5 pr-4 text-right tabular-nums">
                        {a.wakes_7d}
                      </td>
                      <td className="py-2.5 pr-4 text-right tabular-nums">
                        {a.failed_7d > 0 ? (
                          <span
                            className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-500"
                            title={a.top_failure_reason ?? undefined}
                          >
                            <AlertTriangle className="w-3 h-3" />
                            {a.failed_7d}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">0</span>
                        )}
                      </td>
                      <td className="py-2.5 pr-4 text-right tabular-nums">
                        ${a.cost_7d.toFixed(2)}
                      </td>
                      <td className="py-2.5 pr-4 text-right tabular-nums">
                        {a.reviewer_edits_7d}
                      </td>
                      <td
                        className={`py-2.5 pr-4 text-right whitespace-nowrap ${
                          isStale(a.last_wake)
                            ? "text-muted-foreground"
                            : "text-foreground"
                        }`}
                      >
                        {timeAgo(a.last_wake)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">
        <strong>Failed 7d</strong> shows the most common failure reason on hover.{" "}
        <strong>Agent 7d</strong> counts <code>authored_by</code>{" "}
        <code>freddie:*</code> (and legacy <code>reviewer:*</code>) revisions —
        the self-amendment tenure signal. Eval-suite run history (scenarios,
        pass/fail) lives in <code>docs/evaluations/</code> + git, not here.
      </p>
    </div>
  );
}
