"use client";

/**
 * UsagePaneBody — the workspace's usage-this-cycle glance (plan · balance ·
 * where-it-went · activity trend).
 *
 * ADR-416 follow-on (2026-07-08): Usage is WORKSPACE-scoped — every read
 * (getLimits / getUsageDetail) resolves the acting workspace via
 * `effective_workspace_id` and sums `execution_events` by `workspace_id`
 * (migration 200; verified `get_usage_detail` keys on `_acting_workspace_id`).
 * So it lives in the Workspace Settings door (the workspace-content door), not
 * the account door. Extracted from the old `settings/page.tsx` inline body into
 * a self-contained component (Singular Implementation) so the move is a mount
 * swap, and the component owns its own fetches (it loads on mount, since it now
 * renders inside a pane that only mounts when selected).
 *
 * Activity, not dollars (ADR-396 transparency contract, as amended §8): the
 * CONSUMPTION views stay activity-shaped — per-member %-share, relative trend,
 * runway in days, never a running cost ticker. The one dollar figure is the
 * prepaid BALANCE itself, which the operator tops up in dollars and must be able
 * to read (ADR-490: usage is pay-as-you-go from that balance).
 */

import { useEffect, useMemo, useState } from "react";
import { BarChart3, Loader2, Users } from "lucide-react";
import { api } from "@/lib/api/client";
import { humanizeSlug } from "@/lib/schedule";
import { deriveBalance } from "@/lib/subscription/usage";
import { useWorkspaceRoster, useWorkspaceMemberships } from "@/lib/workspace/viewer";

export function UsagePaneBody() {
  // ADR-416/429 §13 SAFETY GUARD: this pane sits under the ACCOUNT door but every
  // figure on it is workspace-scoped, so it must name its subject — otherwise it
  // swaps silently on workspace switch (the exact incoherence the operator caught
  // on Billing, which got the guard; Usage was left without it).
  const { memberships } = useWorkspaceMemberships();
  const activeWorkspaceName = memberships.find((m) => m.is_active)?.label ?? null;
  const [limits, setLimits] = useState<
    Awaited<ReturnType<typeof api.integrations.getLimits>> | null
  >(null);
  const [limitsLoading, setLimitsLoading] = useState(false);
  const [usageDetail, setUsageDetail] = useState<
    Awaited<ReturnType<typeof api.integrations.getUsageDetail>> | null
  >(null);
  // ADR-429 Phase 1 — per-member usage attribution over the shared pool.
  const [spendByPrincipal, setSpendByPrincipal] = useState<
    Awaited<ReturnType<typeof api.integrations.getSpendByPrincipal>> | null
  >(null);
  // ADR-491 D3 — the runway ("~N days at this pace") is the Budget pane's one
  // surviving fact; it lives here now, beside the meter it qualifies. Served by
  // the surviving GET /api/budget (effective balance ÷ daily burn).
  const [runwayDays, setRunwayDays] = useState<number | null>(null);
  // principal_id → humanized label (member email / LLM room / agent slug).
  const { labels: principalLabels } = useWorkspaceRoster();

  useEffect(() => {
    let cancelled = false;
    setLimitsLoading(true);
    api.integrations
      .getLimits()
      .then((d) => {
        if (!cancelled) setLimits(d);
      })
      .catch((err) => console.error("Failed to fetch limits:", err))
      .finally(() => {
        if (!cancelled) setLimitsLoading(false);
      });
    api.integrations
      .getUsageDetail()
      .then((d) => {
        if (!cancelled) setUsageDetail(d);
      })
      .catch(() => {});
    api.integrations
      .getSpendByPrincipal()
      .then((d) => {
        if (!cancelled) setSpendByPrincipal(d);
      })
      .catch(() => {});
    api
      .budget()
      .then((d) => {
        // 999 is the backend's "effectively unlimited" cap — not worth a line.
        const days = (d as { runway_days?: number | null }).runway_days;
        if (!cancelled && typeof days === "number" && days > 0 && days < 999) {
          setRunwayDays(Math.round(days));
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // Per-member rows: humanized label + % of pool + activity count. Activity, not
  // dollars (ADR-396 transparency) — % is share of the pool's spend, computed
  // from the rows' relative cost, and the count is the event tally. Only shown
  // when >1 principal has drawn the pool (a solo workspace has nothing to
  // attribute — it has a single seat, the owner, ADR-445).
  const memberUsage = useMemo(() => {
    const rows = spendByPrincipal?.rows ?? [];
    const total = rows.reduce((sum, r) => sum + r.spend_usd, 0);
    if (rows.length < 2 || total <= 0) return [];
    return rows
      .map((r) => ({
        principal_id: r.principal_id,
        label:
          principalLabels.get(r.principal_id) ??
          (r.principal_id === "unknown" ? "Unattributed" : r.principal_id),
        pct: Math.round((r.spend_usd / total) * 100),
        events: r.event_count,
      }))
      .filter((r) => r.pct > 0 || r.events > 0);
  }, [spendByPrincipal, principalLabels]);

  if (limitsLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground p-4">
        <Loader2 className="w-4 h-4 animate-spin" />
        Loading usage...
      </div>
    );
  }

  if (!limits) {
    return <p className="text-sm text-muted-foreground">Unable to load usage data.</p>;
  }

  return (
    <div className="space-y-6">
      {/* The workspace this pane is about (ADR-416/429 §13 guard). */}
      {activeWorkspaceName ? (
        <p className="text-xs text-muted-foreground -mb-2">
          For <span className="font-medium text-foreground">{activeWorkspaceName}</span>
          {" "}— its usage this cycle. Switch workspaces from the avatar menu.
        </p>
      ) : null}

      {/* Balance — the prepaid pool's remaining dollars (ADR-490 §1③: no
          allowance tranche exists to meter against). Derived by the shared model
          so this pane and the Billing pane can never disagree —
          lib/subscription/usage.ts. Consumption below stays activity-shaped
          (%-share, relative trend); the balance itself is the one dollar figure
          (ADR-396 §10 amendment). */}
      <div className="p-4 border border-border rounded-lg space-y-3">
        {(() => {
          const balance = deriveBalance(limits);
          if (!balance) return null;
          return (
            <>
              <div className="flex items-center justify-between">
                <h3 className="font-medium">Balance</h3>
                <span
                  className={
                    balance.isExhausted
                      ? "text-sm font-medium tabular-nums text-destructive"
                      : "text-sm font-medium tabular-nums"
                  }
                >
                  {balance.remainingLabel} remaining
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                {balance.detail}
                {runwayDays !== null && ` · ~${runwayDays} days left at this pace`}
              </p>
            </>
          );
        })()}
      </div>

      {/* Who used it — per-member attribution over the shared pool (ADR-429
          Phase 1). LEADS the breakdown (ADR-429 §13.2): in a multi-principal
          commons "who spent what" is the headline legibility, above the
          work-item view. Same grammar (bar + %/count), grouped by principal.
          Activity, not dollars. Only when >1 principal has drawn (a solo
          workspace has nothing to attribute — the section is absent). */}
      {memberUsage.length > 0 && (
        <div className="p-4 border border-border rounded-lg space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-medium flex items-center gap-2">
              <Users className="w-4 h-4" />
              Who used it
            </h3>
            <span className="text-xs text-muted-foreground">this cycle</span>
          </div>
          <div className="space-y-2.5">
            {memberUsage.map((m) => (
              <div key={m.principal_id} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="truncate pr-3">{m.label}</span>
                  <span className="font-mono text-xs text-muted-foreground shrink-0">
                    {m.events} {m.events === 1 ? "action" : "actions"} · {m.pct}%
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary/70"
                    style={{ width: `${m.pct}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">
            Share of this workspace&rsquo;s pooled usage, by member. Everyone draws
            the one shared balance.
          </p>
        </div>
      )}

      {/* Where it went — spend by work item (ADR-172 surface). Secondary to the
          per-member view above (ADR-429 §13.2). */}
      {usageDetail && usageDetail.by_work.length > 0 && (
        <div className="p-4 border border-border rounded-lg space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-medium">Where this workspace&rsquo;s usage went</h3>
            <span className="text-xs text-muted-foreground">
              {usageDetail.activity.runs} runs
            </span>
          </div>
          <div className="space-y-2.5">
            {usageDetail.by_work.map((item) => (
              <div key={item.slug} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="truncate pr-3">{humanizeSlug(item.slug)}</span>
                  <span className="font-mono text-xs text-muted-foreground shrink-0">
                    {item.runs} runs · {item.pct}%
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary/70"
                    style={{ width: `${item.pct}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Activity trend — last 14 days (ADR-396: relative activity, not $) */}
      {usageDetail && usageDetail.trend.some((d) => d.cost_usd > 0) && (
        <div className="p-4 border border-border rounded-lg space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-medium flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Activity trend
            </h3>
            <span className="text-xs text-muted-foreground">last 14 days</span>
          </div>
          {(() => {
            const max = Math.max(...usageDetail.trend.map((d) => d.cost_usd), 0.0001);
            return (
              <div className="flex items-end gap-1 h-20">
                {usageDetail.trend.map((d) => (
                  <div
                    key={d.date}
                    className="flex-1 bg-primary/15 rounded-t relative group"
                    style={{ height: `${Math.max(2, (d.cost_usd / max) * 100)}%` }}
                    title={new Date(d.date + "T00:00:00").toLocaleDateString([], {
                      month: "short",
                      day: "numeric",
                    })}
                  >
                    <div className="absolute inset-0 bg-primary/70 rounded-t opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                ))}
              </div>
            );
          })()}
          {usageDetail.activity.success_rate !== null && (
            <p className="text-xs text-muted-foreground">
              {usageDetail.activity.success_rate}% success rate
              {usageDetail.activity.failed > 0 &&
                ` · ${usageDetail.activity.failed} failed`}
            </p>
          )}
        </div>
      )}

      {/* Plan */}
      <div className="p-4 border border-border rounded-lg">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">Plan</span>
          <span className="text-sm text-muted-foreground capitalize">{limits.tier}</span>
        </div>
        {limits.next_refill && (
          <p className="text-xs text-muted-foreground mt-1">
            Renews: {new Date(limits.next_refill).toLocaleDateString()}
          </p>
        )}
      </div>
    </div>
  );
}
