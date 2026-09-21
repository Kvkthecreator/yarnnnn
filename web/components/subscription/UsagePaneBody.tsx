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
import { useTranslations } from "next-intl";
import { BarChart3, Users } from "lucide-react";
import { Working } from '@/components/shared/Working';
import { api } from "@/lib/api/client";
import {
  deriveBalance,
  formatUsd,
  isScheduledWork,
  workItemName,
} from "@/lib/subscription/usage";
import { useWorkspaceRoster, useWorkspaceMemberships } from "@/lib/workspace/viewer";

/**
 * Money for the usage figures. Defers to the shared `formatUsd` (the balance
 * model) above a cent, but a per-run average and a quiet day are routinely
 * sub-cent — and `formatUsd` floors those to "$0.00", which reads as free.
 * Below a cent we widen precision rather than lie about the magnitude.
 */
function fmtUsd(n: number): string {
  const v = Math.max(0, n);
  if (v === 0) return "$0";
  if (v < 0.01) return `$${v.toFixed(4)}`;
  return formatUsd(v);
}

export function UsagePaneBody() {
  const t = useTranslations("billing.usage");
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
  // Hovered trend day (ISO date) — drives the caption readout under the bars.
  const [hoverDay, setHoverDay] = useState<string | null>(null);

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
          (r.principal_id === "unknown" ? t("unattributed") : r.principal_id),
        pct: Math.round((r.spend_usd / total) * 100),
        events: r.event_count,
      }))
      .filter((r) => r.pct > 0 || r.events > 0);
  }, [spendByPrincipal, principalLabels, t]);

  // ⭐ The pane must survive an OLDER server payload. The FE and API deploy
  // independently (separate Render services), so for a window after any FE
  // ship the browser can hold new components while the API still answers the
  // previous shape — which is exactly how `by_model.length` crashed the whole
  // door in production. Every field added after the original contract is read
  // defensively, never trusted.
  const spendTotal =
    usageDetail?.activity.spend_usd ??
    (usageDetail?.trend ?? []).reduce((sum, d) => sum + (d.cost_usd ?? 0), 0);

  if (limitsLoading) {
    return (
      <Working label={t("loading")} className="p-4 text-sm" />
    );
  }

  if (!limits) {
    return <p className="text-sm text-muted-foreground">{t("unavailable")}</p>;
  }

  return (
    <div className="space-y-6">
      {/* The workspace this pane is about (ADR-416/429 §13 guard). */}
      {activeWorkspaceName ? (
        <p className="text-xs text-muted-foreground -mb-2">
          {t.rich("forWorkspace", {
            name: () => (
              <span className="font-medium text-foreground">{activeWorkspaceName}</span>
            ),
          })}
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
          if (!balance) {
            // Per-role (2026-07-29): a member sees the workspace's ACTIVITY
            // (below) but not its wallet — the same split as the Billing
            // pane's member state. The dollar-free states still surface.
            if (limits && limits.billing_authority === false) {
              return (
                <>
                  <h3 className="font-medium">{t("balanceTitle")}</h3>
                  <p className="text-xs text-muted-foreground">
                    {limits.balance_exhausted
                      ? t("memberExhausted")
                      : limits.balance_low
                        ? t("memberLow")
                        : t("memberCalm")}
                  </p>
                </>
              );
            }
            return null;
          }
          return (
            <>
              <div className="flex items-center justify-between">
                <h3 className="font-medium">{t("balanceTitle")}</h3>
                <span
                  className={
                    balance.isExhausted
                      ? "text-sm font-medium tabular-nums text-destructive"
                      : "text-sm font-medium tabular-nums"
                  }
                >
                  {t("remaining", { amount: balance.remainingLabel })}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                {/* `balance.detail` is the shared balance model's sentence
                    (lib/subscription/usage.ts), not this pane's copy. */}
                {balance.detail}
                {runwayDays !== null && t("runway", { count: runwayDays })}
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
              {t("whoUsedIt")}
            </h3>
            <span className="text-xs text-muted-foreground">{t("thisCycle")}</span>
          </div>
          <div className="space-y-2.5">
            {memberUsage.map((m) => (
              <div key={m.principal_id} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="truncate pr-3">{m.label}</span>
                  <span className="font-mono text-xs text-muted-foreground shrink-0">
                    {t("memberRow", { count: m.events, pct: m.pct })}
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
          <p className="text-xs text-muted-foreground">{t("whoNote")}</p>
        </div>
      )}

      {/* Where it went — spend by work item (ADR-172 surface). Secondary to the
          per-member view above (ADR-429 §13.2). */}
      {usageDetail && usageDetail.by_work.length > 0 && (
        <div className="p-4 border border-border rounded-lg space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-medium">{t("whereItWent")}</h3>
            <span className="text-xs text-muted-foreground tabular-nums">
              {t("runsSummary", {
                amount: fmtUsd(spendTotal),
                count: usageDetail.activity.runs,
              })}
            </span>
          </div>
          <div className="space-y-2.5">
            {usageDetail.by_work.map((item) => (
              <div key={item.slug} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="truncate pr-3">{workItemName(item.slug)}</span>
                  <span className="font-mono text-xs text-muted-foreground shrink-0 tabular-nums">
                    {t("workRow", { amount: fmtUsd(item.cost_usd), count: item.runs })}
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
          {usageDetail.by_work[0].pct_runs !== undefined && (
            <p className="text-xs text-muted-foreground">
              {t("barsNote", {
                pct: usageDetail.by_work[0].pct,
                pctRuns: usageDetail.by_work[0].pct_runs,
              })}
              {/* The row names say what was done and to which folder ("Checked ·
                  Fundraising") but not that it ran unattended — the name has
                  ~244px at phone width and spelling it inline truncates the
                  folder. So the panel says it ONCE, and only when such a row is
                  actually present. */}
              {usageDetail.by_work.some((w) => isScheduledWork(w.slug)) && (
                <>{t("scheduledNote")}</>
              )}
            </p>
          )}
        </div>
      )}

      {/* Spend trend — the anchor window (ADR-396 §11: the trend carries its
          dollars). Bars are SPEND, labelled as such; each day also reports its
          run count, so a day with work but no billable draw (a skipped radar
          brief, a cache-only turn) reads as worked-but-free rather than empty.
          Window follows `trend_days`, the same window the panel above sums. */}
      {usageDetail && usageDetail.trend.length > 0 && usageDetail.activity.runs > 0 && (
        <div className="p-4 border border-border rounded-lg space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-medium flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              {t("trendTitle")}
            </h3>
            <span className="text-xs text-muted-foreground">
              {t("trendWindow", {
                count: usageDetail.trend_days ?? usageDetail.trend.length,
              })}
            </span>
          </div>
          {(() => {
            const trend = usageDetail.trend;
            const max = Math.max(...trend.map((d) => d.cost_usd), 0.0001);
            const peak = trend.reduce(
              (best, d) => (d.cost_usd > best.cost_usd ? d : best),
              trend[0],
            );
            const dayLabel = (iso: string) =>
              new Date(iso + "T00:00:00").toLocaleDateString([], {
                month: "short",
                day: "numeric",
              });
            // Hovering a bar reads that day out in the caption line; with no
            // hover the caption states the window total. One readout, so the
            // figure has a stable home instead of a tooltip that vanishes.
            const active = hoverDay
              ? trend.find((d) => d.date === hoverDay) ?? null
              : null;
            return (
              <>
                <div className="flex items-baseline justify-between">
                  <span className="text-lg font-medium tabular-nums">
                    {fmtUsd(spendTotal)}
                  </span>
                  <span className="text-xs text-muted-foreground tabular-nums">
                    {t("peak", { amount: fmtUsd(peak.cost_usd), date: dayLabel(peak.date) })}
                  </span>
                </div>
                <div
                  className="flex items-end gap-1 h-24"
                  onMouseLeave={() => setHoverDay(null)}
                >
                  {trend.map((d) => {
                    const isActive = hoverDay === d.date;
                    // A worked-but-free day gets a visible floor in a muted
                    // tone: real work happened, it just drew nothing.
                    const worked = (d.runs ?? 0) > 0;
                    const pctH = (d.cost_usd / max) * 100;
                    return (
                      <div
                        key={d.date}
                        className="flex-1 h-full flex items-end"
                        onMouseEnter={() => setHoverDay(d.date)}
                      >
                        <div
                          className={
                            "w-full rounded-t transition-colors " +
                            (isActive
                              ? "bg-primary/70"
                              : d.cost_usd > 0
                                ? "bg-primary/25"
                                : worked
                                  ? "bg-muted-foreground/25"
                                  : "bg-muted")
                          }
                          style={{
                            height: `${Math.max(worked || d.cost_usd > 0 ? 3 : 2, pctH)}%`,
                          }}
                        />
                      </div>
                    );
                  })}
                </div>
                <p className="text-xs text-muted-foreground tabular-nums">
                  {active ? (
                    <>
                      {t("dayReadout", {
                        date: dayLabel(active.date),
                        amount: fmtUsd(active.cost_usd),
                      })}
                      {active.runs !== undefined && t("dayRuns", { count: active.runs })}
                      {(active.failed ?? 0) > 0 &&
                        t("dayFailed", { count: active.failed ?? 0 })}
                      {(active.runs ?? 0) > 0 &&
                        active.cost_usd === 0 &&
                        t("noBillableDraw")}
                    </>
                  ) : (
                    <>
                      {t("summaryRuns", {
                        count: usageDetail.activity.runs,
                        amount: fmtUsd(usageDetail.activity.avg_cost_usd),
                      })}
                      {usageDetail.activity.success_rate !== null &&
                        t("summarySuccess", { pct: usageDetail.activity.success_rate })}
                      {usageDetail.activity.failed > 0 &&
                        t("summaryFailed", { count: usageDetail.activity.failed })}
                    </>
                  )}
                </p>
              </>
            );
          })()}
        </div>
      )}

      {/* By engine — spend by model (ADR-556/559: the engine is the cost
          driver, and it is the one lever a member can actually pull). */}
      {usageDetail && (usageDetail.by_model?.length ?? 0) > 0 && (
        <div className="p-4 border border-border rounded-lg space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-medium">{t("byEngine")}</h3>
            <span className="text-xs text-muted-foreground">{t("thisCycle")}</span>
          </div>
          <div className="space-y-2.5">
            {(usageDetail.by_model ?? []).map((m) => (
              <div key={m.model} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="truncate pr-3 font-mono text-xs">{m.model}</span>
                  <span className="font-mono text-xs text-muted-foreground shrink-0 tabular-nums">
                    {t("engineRow", { amount: fmtUsd(m.cost_usd), count: m.runs })}
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
        </div>
      )}

      {/* Plan */}
      <div className="p-4 border border-border rounded-lg">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">{t("planTitle")}</span>
          <span className="text-sm text-muted-foreground capitalize">{limits.tier}</span>
        </div>
        {limits.next_refill && (
          <p className="text-xs text-muted-foreground mt-1">
            {t("renews", { date: new Date(limits.next_refill).toLocaleDateString() })}
          </p>
        )}
      </div>
    </div>
  );
}
