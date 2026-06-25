"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api/client";
import type { AdminAccountDetail } from "@/types/admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Loader2,
  AlertCircle,
  ArrowLeft,
  AlertTriangle,
  GitCommitVertical,
  ListChecks,
  Radio,
  Gauge,
  FolderTree,
} from "lucide-react";

/**
 * Admin → Account detail (/admin/accounts/[slug]). Seven forensic blocks for
 * one eval persona, all substrate-derived. Hat-B dev surface per CLAUDE.md.
 */

function fmtTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function Section({
  title,
  icon,
  children,
  note,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  note?: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          {icon}
          {title}
        </CardTitle>
        {note && <p className="text-xs text-muted-foreground">{note}</p>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

export default function AdminAccountDetailPage() {
  const params = useParams();
  const slug = String(params?.slug ?? "");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [d, setD] = useState<AdminAccountDetail | null>(null);

  useEffect(() => {
    if (!slug) return;
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        setD(await api.admin.accountDetail(slug));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch detail");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [slug]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-muted-foreground">
        <Loader2 className="w-5 h-5 mr-2 animate-spin" />
        Loading {slug}…
      </div>
    );
  }

  if (error || !d) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <AlertCircle className="w-8 h-8 mb-2 text-destructive" />
        <p className="font-medium">Error loading account</p>
        <p className="text-sm text-muted-foreground">{error}</p>
        <Link href="/admin/accounts" className="text-sm text-primary mt-3 hover:underline">
          ← Back to accounts
        </Link>
      </div>
    );
  }

  const maxCurveCost = Math.max(...d.daily.map((p) => p.cost), 0.0001);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          href="/admin/accounts"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="w-4 h-4" />
          Accounts
        </Link>
        <div className="mt-2 flex items-baseline gap-3 flex-wrap">
          <h1 className="text-2xl font-semibold">{d.slug}</h1>
          {d.program && (
            <span className="text-sm px-2 py-0.5 rounded bg-muted text-muted-foreground">
              {d.program}
            </span>
          )}
          {d.email && (
            <span className="text-sm text-muted-foreground">{d.email}</span>
          )}
        </div>
        {d.label && (
          <p className="text-sm text-muted-foreground mt-1">{d.label}</p>
        )}
        <p className="text-xs text-muted-foreground mt-1 font-mono">{d.user_id}</p>
      </div>

      {/* Block 1: cost/activity curve */}
      <Section
        title={`Daily Activity & Cost (${d.curve_days}d)`}
        icon={<Gauge className="w-4 h-4 text-muted-foreground" />}
        note={
          d.curve_truncated
            ? "⚠ High-frequency account — curve truncated at the 5000-event cap; the oldest days may be partial."
            : undefined
        }
      >
        {d.daily.length === 0 ? (
          <p className="text-sm text-muted-foreground py-2">No wakes in window.</p>
        ) : (
          <div className="space-y-1">
            {[...d.daily].reverse().map((p) => (
              <div key={p.day} className="flex items-center gap-3 text-sm">
                <span className="w-20 text-muted-foreground tabular-nums">
                  {p.day.slice(5)}
                </span>
                <div className="flex-1 h-4 bg-muted/40 rounded overflow-hidden">
                  <div
                    className="h-full bg-primary/60"
                    style={{ width: `${(p.cost / maxCurveCost) * 100}%` }}
                  />
                </div>
                <span className="w-16 text-right tabular-nums">
                  ${p.cost.toFixed(2)}
                </span>
                <span className="w-16 text-right tabular-nums text-muted-foreground">
                  {p.wakes}w
                </span>
                <span className="w-28 text-right tabular-nums text-xs text-muted-foreground">
                  {(p.input_tokens / 1000).toFixed(0)}k/
                  {(p.output_tokens / 1000).toFixed(0)}k tok
                </span>
              </div>
            ))}
          </div>
        )}
      </Section>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Block 2: per-recurrence */}
        <Section
          title="Recurrence Breakdown (7d)"
          icon={<ListChecks className="w-4 h-4 text-muted-foreground" />}
          note="Where wakes + cost go, by recurrence slug."
        >
          {d.by_slug.length === 0 ? (
            <p className="text-sm text-muted-foreground">No activity.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="py-1.5 pr-2 font-medium">Slug</th>
                  <th className="py-1.5 px-2 font-medium text-right">Runs</th>
                  <th className="py-1.5 px-2 font-medium text-right">Failed</th>
                  <th className="py-1.5 pl-2 font-medium text-right">Cost</th>
                </tr>
              </thead>
              <tbody>
                {d.by_slug.map((r) => (
                  <tr key={r.slug} className="border-b border-border/40">
                    <td className="py-1.5 pr-2 font-mono text-xs">{r.slug}</td>
                    <td className="py-1.5 px-2 text-right tabular-nums">{r.runs}</td>
                    <td className="py-1.5 px-2 text-right tabular-nums">
                      {r.failed > 0 ? (
                        <span className="text-amber-600 dark:text-amber-500">
                          {r.failed}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">0</span>
                      )}
                    </td>
                    <td className="py-1.5 pl-2 text-right tabular-nums">
                      ${r.cost.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Section>

        {/* Block 3: wake-source */}
        <Section
          title="Wake Source × Status (7d)"
          icon={<Radio className="w-4 h-4 text-muted-foreground" />}
          note="Trigger health — which sources fire, and which fail."
        >
          {d.by_source.length === 0 ? (
            <p className="text-sm text-muted-foreground">No activity.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="py-1.5 pr-2 font-medium">Source</th>
                  <th className="py-1.5 px-2 font-medium text-right">OK</th>
                  <th className="py-1.5 pl-2 font-medium text-right">Failed</th>
                </tr>
              </thead>
              <tbody>
                {d.by_source.map((r) => (
                  <tr key={r.wake_source} className="border-b border-border/40">
                    <td className="py-1.5 pr-2 font-mono text-xs">{r.wake_source}</td>
                    <td className="py-1.5 px-2 text-right tabular-nums">{r.success}</td>
                    <td className="py-1.5 pl-2 text-right tabular-nums">
                      {r.failed > 0 ? (
                        <span className="text-amber-600 dark:text-amber-500">
                          {r.failed}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">0</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Section>
      </div>

      {/* Block 4: recent failures */}
      <Section
        title="Recent Failures"
        icon={<AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-500" />}
        note="error_reason + error_detail for the latest failed wakes — the triage view."
      >
        {d.recent_failures.length === 0 ? (
          <p className="text-sm text-muted-foreground">No failures. 🎉</p>
        ) : (
          <div className="space-y-2">
            {d.recent_failures.map((f, i) => (
              <div key={i} className="text-sm border-b border-border/40 pb-2 last:border-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs text-muted-foreground tabular-nums">
                    {fmtTime(f.created_at)}
                  </span>
                  <span className="font-mono text-xs">{f.slug}</span>
                  <span className="text-xs px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-600 dark:text-amber-500">
                    {f.error_reason ?? "unknown"}
                  </span>
                </div>
                {f.error_detail && (
                  <p className="text-xs text-muted-foreground mt-1 font-mono break-words">
                    {f.error_detail}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </Section>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Block 5: reviewer trail */}
        <Section
          title="Reviewer Self-Amendments"
          icon={<GitCommitVertical className="w-4 h-4 text-muted-foreground" />}
          note="authored_by reviewer:* revisions — the tenure narrative."
        >
          {d.reviewer_trail.length === 0 ? (
            <p className="text-sm text-muted-foreground">No reviewer revisions.</p>
          ) : (
            <div className="space-y-2">
              {d.reviewer_trail.map((r, i) => (
                <div key={i} className="text-sm border-b border-border/40 pb-2 last:border-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground tabular-nums">
                      {fmtTime(r.created_at)}
                    </span>
                    <span className="font-mono text-xs truncate">{r.path}</span>
                  </div>
                  {r.message && (
                    <p className="text-xs text-muted-foreground mt-0.5">{r.message}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </Section>

        {/* Block 6: proposals + Block 7: footprint/perf */}
        <div className="space-y-6">
          <Section
            title="Decision Queue (30d)"
            icon={<ListChecks className="w-4 h-4 text-muted-foreground" />}
            note="action_proposals status mix."
          >
            {d.proposals.length === 0 ? (
              <p className="text-sm text-muted-foreground">No proposals.</p>
            ) : (
              <div className="flex flex-wrap gap-3">
                {d.proposals.map((p) => (
                  <div
                    key={p.status}
                    className="flex items-baseline gap-1.5 text-sm px-3 py-1.5 rounded bg-muted/40"
                  >
                    <span className="text-lg font-semibold tabular-nums">{p.count}</span>
                    <span className="text-xs text-muted-foreground">{p.status}</span>
                  </div>
                ))}
              </div>
            )}
          </Section>

          <Section
            title="Substrate & Performance"
            icon={<FolderTree className="w-4 h-4 text-muted-foreground" />}
            note="File footprint + avg latency by mode (7d)."
          >
            <div className="flex flex-wrap gap-3 mb-3 text-sm">
              <div className="px-3 py-1.5 rounded bg-muted/40">
                <span className="text-lg font-semibold tabular-nums">{d.total_files}</span>{" "}
                <span className="text-xs text-muted-foreground">files</span>
              </div>
              <div className="px-3 py-1.5 rounded bg-muted/40">
                <span className="text-lg font-semibold tabular-nums">
                  {d.persona_files}
                </span>{" "}
                <span className="text-xs text-muted-foreground">persona</span>
              </div>
              <div className="px-3 py-1.5 rounded bg-muted/40">
                <span className="text-lg font-semibold tabular-nums">
                  {d.operation_files}
                </span>{" "}
                <span className="text-xs text-muted-foreground">operation</span>
              </div>
            </div>
            {d.perf.length > 0 && (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground">
                    <th className="py-1 pr-2 font-medium">Mode</th>
                    <th className="py-1 px-2 font-medium text-right">env ms</th>
                    <th className="py-1 px-2 font-medium text-right">dur ms</th>
                    <th className="py-1 px-2 font-medium text-right">rounds</th>
                    <th className="py-1 pl-2 font-medium text-right">n</th>
                  </tr>
                </thead>
                <tbody>
                  {d.perf.map((p) => (
                    <tr key={p.mode} className="border-b border-border/40">
                      <td className="py-1 pr-2">{p.mode}</td>
                      <td className="py-1 px-2 text-right tabular-nums">
                        {p.avg_envelope_ms ?? "—"}
                      </td>
                      <td className="py-1 px-2 text-right tabular-nums">
                        {p.avg_duration_ms ?? "—"}
                      </td>
                      <td className="py-1 px-2 text-right tabular-nums">
                        {p.avg_tool_rounds ?? "—"}
                      </td>
                      <td className="py-1 pl-2 text-right tabular-nums">{p.n}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Section>
        </div>
      </div>
    </div>
  );
}
