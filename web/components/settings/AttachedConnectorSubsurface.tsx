"use client";

/**
 * AttachedConnectorSubsurface — the per-connection page for an ATTACHED
 * connector (ADR-635): an MCP server the member attached from the directory
 * or by URL, keyed `mcp:{slug}`. The drill-in from Settings → Connectors.
 *
 * Two strata, mirroring ManageConnectionSubsurface:
 *
 *   CONNECTION — the server (title · URL · category · since), Refresh tools,
 *   Disconnect.
 *
 *   APERTURE — the member's consent, tool by tool. A fresh attach exposes NO
 *   tool (selection is consent, never a default — ADR-582). Each tool is one
 *   of: Off (not offered to any turn) · Ask first (every call is queued as a
 *   proposal the member executes) · Direct (runs in the member's turn). The
 *   server's read-only HINT is shown beside the choice and never decides it.
 *
 * ADR-635 D4 am.1 — two things this surface learned from a 31-tool server:
 *
 *   ERGONOMICS. The picker was exercised at Notion's handful; a commerce
 *   server advertises ~31. So: a filter box, and the list SPLIT by the
 *   server's own read-only hint (reads first, writes after) with a count on
 *   each group. What is NOT here, deliberately: no group defaults to on, no
 *   "allow all writes", no mode is preselected. The bulk control sets the
 *   tools CURRENTLY MATCHING THE FILTER, one explicit gesture per group, and
 *   it is still a draft the member must Save. The hint groups the list; it
 *   never decides a mode (ADR-635 D4, and the MCP SDK's own docstring).
 *
 *   DRIFT. `metadata.tools` is a snapshot and the aperture is keyed on tool
 *   NAMES: when a server renames or withdraws a tool the member's consent for
 *   it evaporates and the tool starts refusing. That is correct and it was
 *   silent. The last refresh's drift is served on the row and named at the
 *   top of the aperture; saving clears it.
 *
 * The mode lives on the connection — the grant side — never on an agent.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import {
  AlertTriangle,
  ArrowLeft,
  ExternalLink,
  Loader2,
  RefreshCw,
  Search,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { api, APIError, type AttachedConnector } from "@/lib/api/client";
import { Working } from '@/components/shared/Working';
import { useFeedback } from "@/contexts/FeedbackContext";
import { ConnectorAvatar } from "@/components/connectors/ConnectorAvatar";

type Mode = "off" | "propose" | "direct";

interface AttachedConnectorSubsurfaceProps {
  /** The `mcp:{slug}` provider key. */
  provider: string;
  onBack: () => void;
  onDisconnect?: () => void;
  disconnecting?: boolean;
}

function sinceLabel(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString(undefined, { month: "short", year: "numeric" });
}

function SectionShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-md border border-border/60 p-3">
      <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </h3>
      {children}
    </section>
  );
}

/** The three modes, as catalog KEYS. A module-level table is evaluated at
 *  IMPORT, before any member's language is known, so it may hold only keys —
 *  the words are resolved at render below. */
const MODES: Array<{ value: Mode; labelKey: string; hintKey: string }> = [
  { value: "off", labelKey: "modeOff", hintKey: "modeOffHint" },
  { value: "propose", labelKey: "modePropose", hintKey: "modeProposeHint" },
  { value: "direct", labelKey: "modeDirect", hintKey: "modeDirectHint" },
];

export function AttachedConnectorSubsurface({
  provider,
  onBack,
  onDisconnect,
  disconnecting = false,
}: AttachedConnectorSubsurfaceProps) {
  const t = useTranslations("billing.attached");
  const slug = provider.startsWith("mcp:") ? provider.slice(4) : provider;
  const [row, setRow] = useState<AttachedConnector | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<Record<string, Mode>>({});
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState("");
  // Save and Refresh report through the canonical action-feedback layer
  // (docs/design/ACTION-FEEDBACK.md); `error` below stays for the LOAD, which
  // has no verb behind it and must survive until the member retries.
  const { runAction } = useFeedback();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const c = await api.connectors.get(slug);
      setRow(c);
      const next: Record<string, Mode> = {};
      for (const tool of c.tools) next[tool.name] = (tool.mode ?? "off") as Mode;
      setDraft(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("loadError"));
    } finally {
      setLoading(false);
    }
  }, [slug, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const dirty =
    !!row &&
    row.tools.some(
      (tool) => (draft[tool.name] ?? "off") !== ((tool.mode ?? "off") as Mode),
    );

  const save = async () => {
    setSaving(true);
    try {
      const aperture: Record<string, "direct" | "propose"> = {};
      for (const [tool, mode] of Object.entries(draft)) {
        if (mode === "direct" || mode === "propose") aperture[tool] = mode;
      }
      const res = await runAction(() => api.connectors.setAperture(slug, aperture), {
        pending: t("savePending"),
        success: t("saveSuccess"),
        error: (e) =>
          e instanceof APIError
            ? (e.data as { detail?: string })?.detail || t("saveError")
            : t("saveError"),
      });
      if (res.connector) setRow(res.connector);
    } catch {
      // Reported by the toast; the draft stays as the member left it.
    } finally {
      setSaving(false);
    }
  };

  const refreshTools = async () => {
    setRefreshing(true);
    try {
      // The success line says WHAT it found, derived from the same drift
      // record the banner reads \u2014 "Tool list updated" was true of a server
      // that changed nothing and of one that withdrew a tool the member had
      // allowed, which is the silence this amendment exists to end.
      await runAction(() => api.connectors.refresh(slug), {
        pending: t("refreshPending"),
        success: (res) => {
          const d = res?.connector?.drift;
          if (d?.withdrawn.length) {
            return t("refreshWithdrawn", { count: d.withdrawn.length });
          }
          if (d?.appeared.length) {
            return t("refreshAppeared", { count: d.appeared.length });
          }
          return t("refreshNoChange");
        },
        error: (e) =>
          e instanceof APIError
            ? (e.data as { detail?: string })?.detail || t("refreshError")
            : t("refreshError"),
      });
      await load();
    } catch {
      // Reported by the toast; the tools already on screen stay as they were.
    } finally {
      setRefreshing(false);
    }
  };

  const exposed = Object.values(draft).filter((m) => m !== "off").length;
  const since = sinceLabel(row?.connected_at);

  // ADR-635 D4 am.1 — the list, filtered then SPLIT by the server's own
  // read-only hint. The split is presentation: it groups what the member
  // reads, and carries no mode with it.
  const groups = useMemo(() => {
    const q = filter.trim().toLowerCase();
    const shown = (row?.tools ?? []).filter(
      (tool) =>
        !q ||
        tool.name.toLowerCase().includes(q) ||
        (tool.description ?? "").toLowerCase().includes(q),
    );
    return [
      {
        key: "reads" as const,
        label: t("groupReads"),
        note: t("groupReadsNote"),
        tools: shown.filter((tool) => tool.read_only_hint),
      },
      {
        key: "writes" as const,
        label: t("groupWrites"),
        note: t("groupWritesNote"),
        tools: shown.filter((tool) => !tool.read_only_hint),
      },
    ].filter((g) => g.tools.length > 0);
  }, [row?.tools, filter, t]);

  const shownCount = groups.reduce((n, g) => n + g.tools.length, 0);

  /** Set every tool CURRENTLY SHOWN in one group to one mode. An explicit
   *  member gesture per group, on what they can see, still a draft. */
  const setGroup = (names: string[], mode: Mode) => {
    setDraft((d) => {
      const next = { ...d };
      for (const n of names) next[n] = mode;
      return next;
    });
  };

  return (
    <div className="flex h-full flex-col">
      <button
        type="button"
        onClick={onBack}
        className="mb-4 inline-flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        {t("back")}
      </button>

      <div className="flex items-start gap-3">
        <ConnectorAvatar size="lg" url={row?.server_url} title={row?.title ?? slug} />
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-semibold">{row?.title ?? slug}</h2>
          {row?.server_url && (
            <p className="truncate text-sm text-muted-foreground">{row.server_url}</p>
          )}
          <p className="mt-0.5 text-xs text-muted-foreground">
            {row?.category ? t("categoryPrefix", { category: row.category }) : ""}
            {row?.auth === "none" ? t("noSignIn") : t("authorized")}
            {since ? t("sinceSuffix", { since }) : ""}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={() => void refreshTools()}
            disabled={refreshing || loading}
            className="inline-flex items-center gap-1 rounded-md border border-border/60 px-2.5 py-1 text-xs hover:bg-muted"
            title={t("refreshTitle")}
          >
            {refreshing ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
            {t("refresh")}
          </button>
          {onDisconnect && (
            <button
              type="button"
              onClick={onDisconnect}
              disabled={disconnecting}
              className="inline-flex items-center gap-1 rounded-md border border-border/60 px-2.5 py-1 text-xs text-muted-foreground hover:border-destructive/30 hover:text-destructive"
            >
              {disconnecting ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
              {t("disconnect")}
            </button>
          )}
        </div>
      </div>

      {error && (
        <p role="alert" className="mt-3 text-sm text-destructive">
          {error}
        </p>
      )}

      {loading ? (
        <Working label={t("loading")} fill />
      ) : row ? (
        <div className="mt-4 space-y-3">
          <SectionShell title={t("allowTitle")}>
            {/* The two mode names are emphasised INSIDE the sentence, so they
                ride as rich-text tags — a language orders the clause its own
                way and the bold has to travel with the word. */}
            <p className="mb-3 text-xs text-muted-foreground">
              {t.rich("allowLead", {
                askFirst: () => <strong>{t("modePropose")}</strong>,
                direct: () => <strong>{t("modeDirect")}</strong>,
              })}
            </p>
            {/* ADR-635 D4 am.1 — the server moved under the member's consent.
                A tool they ALLOWED that is gone now refuses every call; this
                is the only place that says so. Saving clears it. */}
            {row.drift && (row.drift.withdrawn.length > 0 || row.drift.appeared.length > 0) && (
              <div
                role="status"
                className="mb-3 flex items-start gap-2 rounded-md border border-amber-500/30 bg-amber-500/5 p-2.5 text-xs"
              >
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
                <div className="min-w-0">
                  <p className="font-medium text-amber-700 dark:text-amber-500">
                    {t("driftTitle")}
                  </p>
                  {row.drift.withdrawn.length > 0 && (
                    <p className="mt-0.5 text-muted-foreground">
                      {t.rich("driftWithdrawn", {
                        count: row.drift.withdrawn.length,
                        names: () => (
                          <span className="text-foreground">
                            {row.drift?.withdrawn.join(", ")}
                          </span>
                        ),
                      })}
                    </p>
                  )}
                  {row.drift.appeared.length > 0 && (
                    <p className="mt-0.5 text-muted-foreground">
                      {t("driftAppeared", { count: row.drift.appeared.length })}
                    </p>
                  )}
                </div>
              </div>
            )}

            {row.tools.length === 0 ? (
              <p className="py-2 text-sm text-muted-foreground">{t("noTools")}</p>
            ) : (
              <>
                {/* At a handful of tools this is noise; at ~31 it is the only
                    way to find one. Shown once the list outgrows a screen. */}
                {row.tools.length > 8 && (
                  <div className="relative mb-3">
                    <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                    <input
                      type="search"
                      value={filter}
                      onChange={(e) => setFilter(e.target.value)}
                      placeholder={t("filterPlaceholder", { count: row.tools.length })}
                      aria-label={t("filterLabel")}
                      className="w-full rounded-md border border-border/60 bg-transparent py-1.5 pl-8 pr-2 text-xs outline-none focus:border-foreground/30"
                    />
                  </div>
                )}

                {shownCount === 0 ? (
                  <p className="py-2 text-sm text-muted-foreground">
                    {t("noMatch", { query: filter })}
                  </p>
                ) : (
                  groups.map((g) => {
                    const names = g.tools.map((tool) => tool.name);
                    return (
                      <div key={g.key} className="mb-3 last:mb-0">
                        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1 border-b border-border/60 pb-1.5">
                          <h4 className="text-xs font-medium">
                            {g.label}
                            <span className="ml-1.5 font-normal text-muted-foreground">
                              {g.tools.length}
                            </span>
                          </h4>
                          <p className="text-[11px] text-muted-foreground">{g.note}</p>
                          {/* Consent stays explicit: this sets exactly what is
                              on screen, to a mode the member names, and it is
                              still a draft until Save. Nothing here is a
                              default and nothing turns on by itself. */}
                          <div className="ml-auto flex shrink-0 items-center gap-1 text-[11px]">
                            <span className="text-muted-foreground">
                              {filter.trim() ? t("setThese") : t("setAll")}
                            </span>
                            {MODES.map((m) => (
                              <button
                                key={m.value}
                                type="button"
                                title={t("modeTitle", {
                                  label: t(m.labelKey),
                                  hint: t(m.hintKey),
                                })}
                                onClick={() => setGroup(names, m.value)}
                                className="rounded border border-border/60 px-1.5 py-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                              >
                                {t(m.labelKey)}
                              </button>
                            ))}
                          </div>
                        </div>
                        <ul className="divide-y divide-border/60">
                          {g.tools.map((tool) => {
                            const mode = draft[tool.name] ?? "off";
                            return (
                              <li key={tool.name} className="flex items-start gap-3 py-2">
                                <div className="min-w-0 flex-1">
                                  <div className="flex items-center gap-2">
                                    <code className="truncate text-sm">{tool.name}</code>
                                    {tool.read_only_hint && (
                                      <span
                                        className="inline-flex items-center gap-1 text-[11px] text-muted-foreground"
                                        title={t("readsBadgeTitle")}
                                      >
                                        <ShieldCheck className="h-3 w-3" />
                                        {t("readsBadge")}
                                      </span>
                                    )}
                                  </div>
                                  {tool.description && (
                                    <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                                      {tool.description}
                                    </p>
                                  )}
                                </div>
                                <div
                                  role="radiogroup"
                                  aria-label={t("toolModeLabel", { tool: tool.name })}
                                  className="flex shrink-0 overflow-hidden rounded-md border border-border/60 text-xs"
                                >
                                  {MODES.map((m) => (
                                    <button
                                      key={m.value}
                                      type="button"
                                      role="radio"
                                      aria-checked={mode === m.value}
                                      title={t(m.hintKey)}
                                      onClick={() => {
                                        setDraft((d) => ({ ...d, [tool.name]: m.value }));
                                      }}
                                      className={`px-2.5 py-1 ${
                                        mode === m.value
                                          ? "bg-foreground text-background"
                                          : "text-muted-foreground hover:bg-muted"
                                      }`}
                                    >
                                      {t(m.labelKey)}
                                    </button>
                                  ))}
                                </div>
                              </li>
                            );
                          })}
                        </ul>
                      </div>
                    );
                  })
                )}
              </>
            )}
            <div className="mt-3 flex items-center gap-3">
              <button
                type="button"
                onClick={() => void save()}
                disabled={saving || !dirty}
                className="inline-flex items-center gap-1 rounded-md bg-foreground px-3 py-1.5 text-xs font-medium text-background disabled:opacity-50"
              >
                {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
                {t("save")}
              </button>
              <span className="text-xs text-muted-foreground">
                {t("exposedCount", { exposed, total: row.tools.length })}
                {filter.trim() ? t("shownSuffix", { count: shownCount }) : ""}
              </span>
            </div>
          </SectionShell>

          <SectionShell title={t("doesTitle")}>
            <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
              <dt className="text-muted-foreground">{t("readsWrites")}</dt>
              <dd>{t("readsWritesBody")}</dd>
              <dt className="text-muted-foreground">{t("agents")}</dt>
              <dd>{t("agentsBody")}</dd>
              <dt className="text-muted-foreground">{t("whereItGoes")}</dt>
              <dd>{t("whereItGoesBody")}</dd>
            </dl>
            {row.server_url && (
              <a
                href={row.server_url}
                target="_blank"
                rel="noreferrer"
                className="mt-2 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
              >
                {row.server_url}
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </SectionShell>
        </div>
      ) : null}
    </div>
  );
}
