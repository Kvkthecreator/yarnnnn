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
 * The mode lives on the connection — the grant side — never on an agent.
 */

import { useCallback, useEffect, useState } from "react";
import {
  ArrowLeft,
  ExternalLink,
  Loader2,
  Plug,
  RefreshCw,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { api, APIError, type AttachedConnector } from "@/lib/api/client";
import { Working } from '@/components/shared/Working';
import { useFeedback } from "@/contexts/FeedbackContext";

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

const MODES: Array<{ value: Mode; label: string; hint: string }> = [
  { value: "off", label: "Off", hint: "Not offered to any conversation." },
  { value: "propose", label: "Ask first", hint: "Each call is queued for you to run." },
  { value: "direct", label: "Direct", hint: "Runs in your turn, under your credential." },
];

export function AttachedConnectorSubsurface({
  provider,
  onBack,
  onDisconnect,
  disconnecting = false,
}: AttachedConnectorSubsurfaceProps) {
  const slug = provider.startsWith("mcp:") ? provider.slice(4) : provider;
  const [row, setRow] = useState<AttachedConnector | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<Record<string, Mode>>({});
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
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
      for (const t of c.tools) next[t.name] = (t.mode ?? "off") as Mode;
      setDraft(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load this connector.");
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    void load();
  }, [load]);

  const dirty =
    !!row &&
    row.tools.some((t) => (draft[t.name] ?? "off") !== ((t.mode ?? "off") as Mode));

  const save = async () => {
    setSaving(true);
    try {
      const aperture: Record<string, "direct" | "propose"> = {};
      for (const [tool, mode] of Object.entries(draft)) {
        if (mode === "direct" || mode === "propose") aperture[tool] = mode;
      }
      const res = await runAction(() => api.connectors.setAperture(slug, aperture), {
        pending: "Saving\u2026",
        success: "Saved what this connector may do",
        error: (e) =>
          e instanceof APIError
            ? (e.data as { detail?: string })?.detail || "Couldn't save that setting"
            : "Couldn't save that setting",
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
      await runAction(() => api.connectors.refresh(slug), {
        pending: "Checking what this server offers\u2026",
        success: "Tool list updated",
        error: (e) =>
          e instanceof APIError
            ? (e.data as { detail?: string })?.detail || "Couldn't reach that server"
            : "Couldn't reach that server",
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

  return (
    <div className="flex h-full flex-col">
      <button
        type="button"
        onClick={onBack}
        className="mb-4 inline-flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Connections
      </button>

      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted">
          <Plug className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-semibold">{row?.title ?? slug}</h2>
          {row?.server_url && (
            <p className="truncate text-sm text-muted-foreground">{row.server_url}</p>
          )}
          <p className="mt-0.5 text-xs text-muted-foreground">
            {row?.category ? `${row.category} · ` : ""}
            {row?.auth === "none" ? "no sign-in required" : "authorized by you"}
            {since ? ` · since ${since}` : ""}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={() => void refreshTools()}
            disabled={refreshing || loading}
            className="inline-flex items-center gap-1 rounded-md border border-border/60 px-2.5 py-1 text-xs hover:bg-muted"
            title="Re-list the server's tools"
          >
            {refreshing ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
            Refresh
          </button>
          {onDisconnect && (
            <button
              type="button"
              onClick={onDisconnect}
              disabled={disconnecting}
              className="inline-flex items-center gap-1 rounded-md border border-border/60 px-2.5 py-1 text-xs text-muted-foreground hover:border-destructive/30 hover:text-destructive"
            >
              {disconnecting ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
              Disconnect
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
        <Working label="Loading the connector…" fill />
      ) : row ? (
        <div className="mt-4 space-y-3">
          <SectionShell title="What you allow">
            <p className="mb-3 text-xs text-muted-foreground">
              Nothing is offered until you choose it. <strong>Ask first</strong> queues
              each call as a proposal you run from your queue. <strong>Direct</strong>{" "}
              runs in your conversation under your own credential. A lock means the
              server says the tool only reads — a hint for you, not a decision.
            </p>
            {row.tools.length === 0 ? (
              <p className="py-2 text-sm text-muted-foreground">
                No tools listed yet. Try Refresh.
              </p>
            ) : (
              <ul className="divide-y divide-border/60">
                {row.tools.map((t) => {
                  const mode = draft[t.name] ?? "off";
                  return (
                    <li key={t.name} className="flex items-start gap-3 py-2">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <code className="truncate text-sm">{t.name}</code>
                          {t.read_only_hint && (
                            <span
                              className="inline-flex items-center gap-1 text-[11px] text-muted-foreground"
                              title="The server marks this tool read-only (a hint, not a guarantee)"
                            >
                              <ShieldCheck className="h-3 w-3" />
                              reads
                            </span>
                          )}
                        </div>
                        {t.description && (
                          <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                            {t.description}
                          </p>
                        )}
                      </div>
                      <div
                        role="radiogroup"
                        aria-label={`${t.name} mode`}
                        className="flex shrink-0 overflow-hidden rounded-md border border-border/60 text-xs"
                      >
                        {MODES.map((m) => (
                          <button
                            key={m.value}
                            type="button"
                            role="radio"
                            aria-checked={mode === m.value}
                            title={m.hint}
                            onClick={() => {
                              setDraft((d) => ({ ...d, [t.name]: m.value }));
                            }}
                            className={`px-2.5 py-1 ${
                              mode === m.value
                                ? "bg-foreground text-background"
                                : "text-muted-foreground hover:bg-muted"
                            }`}
                          >
                            {m.label}
                          </button>
                        ))}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
            <div className="mt-3 flex items-center gap-3">
              <button
                type="button"
                onClick={() => void save()}
                disabled={saving || !dirty}
                className="inline-flex items-center gap-1 rounded-md bg-foreground px-3 py-1.5 text-xs font-medium text-background disabled:opacity-50"
              >
                {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
                Save
              </button>
              <span className="text-xs text-muted-foreground">
                {exposed} of {row.tools.length} tools offered
              </span>
            </div>
          </SectionShell>

          <SectionShell title="What this connection does">
            <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
              <dt className="text-muted-foreground">Reads / writes</dt>
              <dd>
                Whatever tools you allow above, in your own chats, as you. A tool set
                to Ask first waits in To do before it runs.
              </dd>
              <dt className="text-muted-foreground">Agents</dt>
              <dd>
                Never on their own. Only a chat you are in can reach this server.
              </dd>
              <dt className="text-muted-foreground">Where it goes</dt>
              <dd>
                What a chat fetches stays in that chat unless it is saved to a file.
                It goes to the engine you chose for that chat.
              </dd>
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
