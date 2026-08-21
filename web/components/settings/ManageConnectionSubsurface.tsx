"use client";

/**
 * ManageConnectionSubsurface — the per-connection detail page (ADR-582 model;
 * drill-in routed by `settings.connector=<provider>` from the Connections pane).
 *
 * TWO STRATA, deliberately:
 *
 *   CONNECTION — the connection-level facts: header (workspace · since),
 *   Refresh + the ⋮ lifecycle menu (Reconnect / Disconnect), ACCESS (granted
 *   OAuth scopes + the validate probe — the ONLY honest liveness signal,
 *   ADR-401 D6), and WHAT THIS CONNECTION DOES (reads/writes/agents facts,
 *   served by the API from the machinery that enacts them — facts, not
 *   controls: no per-tool enforcement point exists on the outbound side).
 *
 *   CAPTURE — the aperture: which slices may be read at all (the selection —
 *   CONSENT, never auto-filled; ADR-079/113 smart defaults died 2026-08-19
 *   and survive only as the `Suggested` badge). Where snapshots land is a
 *   FACT, not a dial (ADR-594 D1: the fixed intake lane). For GitHub the
 *   selection also bounds platform-tool reach (ADR-576 D2; empty =
 *   unrestricted).
 *
 *   YIELD — the writer's read-back (freshness + landed files), flag-gated.
 *
 * Discovery failures render scoped inside CAPTURE so a dead token never
 * hides the recovery affordances (Test / Reconnect) above it.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowUpRight,
  Check,
  ChevronDown,
  ChevronRight,
  Clock,
  Loader2,
  MoreHorizontal,
  RefreshCw,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { formatRelativeTime } from "@/lib/formatting";
import type { ConnectorMeta } from "@/lib/connectors/registry";
import { SurfaceLink } from "@/components/shell/SurfaceLink";

type SelectableProvider = "slack" | "notion" | "github";

interface Resource {
  id: string;
  name: string;
  recommended?: boolean;
}

interface Observed {
  status?: string;
  observed_at?: string;
  items?: number;
  last_error?: string;
}

interface ConnectorDoes {
  reads: string;
  writes: string;
  chat?: string;
  agents: string;
}

interface ConnectionFacts {
  workspace_name: string | null;
  /** WHERE this connection points, resolved server-side across the
   *  per-provider metadata shapes (GitHub names an account, not a workspace). */
  target?: string | null;
  connected_at: string | null;
}

interface ProbeResult {
  status: "healthy" | "degraded" | "unhealthy" | "unknown";
  at: number;
  errors?: string[];
}

interface ManageConnectionSubsurfaceProps {
  meta: ConnectorMeta;
  onBack: () => void;
  /** Disconnect this connection (parent owns the confirm + the row delete).
   *  Omitted → no Disconnect item in the ⋮ menu. */
  onDisconnect?: () => void;
  disconnecting?: boolean;
}

function relativeTime(iso?: string): string {
  // Connector freshness labels (ADR-392 D5); time math via @/lib/formatting.
  if (!iso) return "not reading yet";
  if (Number.isNaN(new Date(iso).getTime())) return "unknown";
  return formatRelativeTime(iso);
}

function sinceLabel(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString(undefined, { month: "short", year: "numeric" });
}

function SectionShell({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-md border border-border/60 p-3">
      <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </h3>
      {children}
    </section>
  );
}

export function ManageConnectionSubsurface({
  meta,
  onBack,
  onDisconnect,
  disconnecting = false,
}: ManageConnectionSubsurfaceProps) {
  const provider = meta.provider as SelectableProvider;
  const resourceNoun = meta.resourceNoun ?? "sources";
  const resourceNounSingular = resourceNoun.replace(/s$/, "");

  // Core connection facts (capture-signal + sources — one round-trip each).
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [connectorFreshness, setConnectorFreshness] = useState<Observed | null>(null);
  const [grantedScopes, setGrantedScopes] = useState<string[]>([]);
  const [connection, setConnection] = useState<ConnectionFacts | null>(null);
  const [does, setDoes] = useState<ConnectorDoes | null>(null);
  const [agentEnabled, setAgentEnabled] = useState(true);
  // ADR-404 D2: the capture lane is dormant for the commons-first launch —
  // the CAPTURE block collapses to one honest line and YIELD hides entirely.
  const [captureEnabled, setCaptureEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // The landscape (the capture block's resource list) loads SEPARATELY so a
  // discovery failure — a revoked token, a platform outage — renders inside
  // CAPTURE and never hides ACCESS, where Test connection and Reconnect live.
  const [resources, setResources] = useState<Resource[]>([]);
  const [scopeLoading, setScopeLoading] = useState(true);
  const [scopeError, setScopeError] = useState<string | null>(null);

  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [probing, setProbing] = useState(false);
  const [probe, setProbe] = useState<ProbeResult | null>(null);
  // Operator-opened while dormant; forced open when the lane runs.
  const [captureOpen, setCaptureOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    function handler(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen]);

  const loadCore = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [current, signal] = await Promise.all([
        api.integrations.getSources(provider),
        api.integrations.getCaptureSignal(provider).catch(() => null),
      ]);
      setSelected(
        new Set<string>((current.sources || []).map((s) => s.id).filter(Boolean)),
      );
      // One observed block for the whole connector, keyed by capture slug
      // (the connector is the unit of perception — ADR-393).
      const block = signal?.observed?.[`capture-${provider}`] ?? null;
      setConnectorFreshness(block as Observed | null);
      setGrantedScopes(signal?.granted_scopes ?? []);
      setConnection(signal?.connection ?? null);
      // `does` is a post-ADR-582 payload field — absent on an older API, in
      // which case its section simply doesn't render. (`settings` is gone —
      // ADR-594 D1 fixed the landing grammar and deleted the last dial.)
      setDoes(signal?.does ?? null);
      setAgentEnabled(signal?.agent_enabled ?? true);
      setCaptureEnabled(signal?.connector_capture_enabled ?? false);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : `Could not load the ${provider} connection.`,
      );
    } finally {
      setLoading(false);
    }
  }, [provider]);

  const loadLandscape = useCallback(
    async (refresh?: boolean) => {
      setScopeLoading(true);
      setScopeError(null);
      try {
        const landscape = await api.integrations.getLandscape(provider, refresh);
        setResources(
          (landscape.resources || []).map((r) => ({
            id: r.id,
            name: r.name,
            recommended: r.recommended,
          })),
        );
      } catch (e) {
        setScopeError(
          e instanceof Error ? e.message : `Could not list ${provider} ${resourceNoun}.`,
        );
      } finally {
        setScopeLoading(false);
      }
    },
    [provider, resourceNoun],
  );

  useEffect(() => {
    void loadCore();
    void loadLandscape();
  }, [loadCore, loadLandscape]);

  const refreshAll = () => {
    void loadCore();
    void loadLandscape(true);
  };

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    setSavedAt(null);
  };

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      await api.integrations.updateSources(provider, Array.from(selected));
      setSavedAt(Date.now());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save selection.");
    } finally {
      setSaving(false);
    }
  };

  // The ONLY honest liveness signal — the on-demand validate probe (for Slack
  // it actually reads the platform). Never render health from the stored
  // status column (always 'active'; ADR-401 D6).
  const testConnection = async () => {
    setProbing(true);
    try {
      const res = await api.integrations.getHealth(provider, true);
      setProbe({ status: res.status, at: Date.now(), errors: res.errors });
    } catch {
      setProbe({ status: "unknown", at: Date.now() });
    } finally {
      setProbing(false);
    }
  };

  // Reconnect = re-run authorize→callback (the upsert overwrites credentials).
  // There is deliberately no separate reconnect endpoint. For Notion this is
  // also how the operator changes WHICH pages are shared — access is granted
  // page-by-page on the provider's consent screen.
  const reconnect = async () => {
    try {
      // ADR-425: connectors live on the account door; the round-trip returns
      // to this drill-in.
      const back = `/settings?settings.pane=connectors&settings.connector=${provider}`;
      const result = await api.integrations.getAuthorizationUrl(provider, back);
      window.location.href = result.authorization_url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start reauthorization.");
    }
  };

  // The honest connector-level freshness line. Item count is the number of
  // selectors captured, not message count (ADR-393 signal is thin).
  const freshnessLabel = (): string => {
    if (!connectorFreshness?.observed_at) return "Not reading yet";
    const when = relativeTime(connectorFreshness.observed_at);
    const status = connectorFreshness.status;
    const items =
      typeof connectorFreshness.items === "number"
        ? ` · ${connectorFreshness.items} ${resourceNoun} read`
        : "";
    const errored = status && status !== "ok" ? ` · ${status}` : "";
    return `Last read ${when}${items}${errored}`;
  };

  const since = sinceLabel(connection?.connected_at);
  const probeLabel =
    probe &&
    (probe.status === "healthy"
      ? `read OK · ${relativeTime(new Date(probe.at).toISOString())}`
      : `${probe.status}${probe.errors?.length ? ` — ${probe.errors[0]}` : ""}`);

  // ADR-594 D1 — the landing grammar is FIXED: a connection is a rail
  // (consent + credential + aperture), it carries no placement choice.
  const defaultLane = `inbound/${provider}`;
  const filesPath = `/workspace/${defaultLane}`;
  const captureExpanded = captureEnabled || captureOpen;

  const scopeEmptyState = () =>
    provider === "notion" ? (
      // Notion grants access page-by-page on ITS consent screen — an empty
      // list with a live token means nothing is shared with the integration.
      // "Try Refresh" would re-run the same honest empty; the real recovery
      // is re-consenting with pages picked (or sharing pages inside Notion).
      <div className="py-2">
        <p className="text-sm text-muted-foreground">
          No pages are shared with the yarnnn integration yet.
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Notion grants access page-by-page. Reconnect and pick pages on
          Notion&apos;s consent screen — or share pages to yarnnn inside Notion,
          then Refresh.
        </p>
        <button
          type="button"
          onClick={() => void reconnect()}
          className="mt-2 inline-flex items-center gap-1 rounded-md border border-border/60 px-2.5 py-1 text-xs hover:bg-muted"
        >
          Reconnect
          <ArrowUpRight className="h-3 w-3" />
        </button>
      </div>
    ) : (
      <p className="py-2 text-sm text-muted-foreground">
        No {resourceNoun} discovered. Try Refresh.
      </p>
    );

  return (
    <div className="flex h-full flex-col">
      {/* Back-crumb — clears the drill-in param, returns to the connections list. */}
      <button
        type="button"
        onClick={onBack}
        className="mb-4 inline-flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Connections
      </button>

      <div className="flex items-start gap-3">
        <div
          className={`w-10 h-10 ${meta.brand.chipClass} rounded-lg flex items-center justify-center shrink-0`}
        >
          {meta.brand.icon}
        </div>
        <div className="min-w-0">
          <h2 className="text-lg font-semibold">{meta.displayName}</h2>
          {/* WHERE this connection points gets its OWN line, in the
              foreground. It used to sit mid-sentence between a status word
              and a date ("Connected · yarnnn · since Jul 2026"), which read
              as metadata about the connection rather than as the thing the
              connection IS — and it is the one fact that distinguishes this
              connection from another of the same provider. `target` resolves
              across the per-provider shapes (GitHub names an ACCOUNT), so the
              label is generic; `workspace_name` remains the fallback for a
              payload that predates it. */}
          {(connection?.target ?? connection?.workspace_name) && (
            <p className="truncate text-sm font-medium text-foreground">
              {connection.target ?? connection.workspace_name}
            </p>
          )}
          <p className="text-xs text-muted-foreground">
            Connected{since ? ` · since ${since}` : ""}
          </p>
        </div>
        <div className="ml-auto flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={refreshAll}
            disabled={loading || scopeLoading}
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            title="Re-discover from the platform"
          >
            <RefreshCw
              className={`h-3 w-3 ${loading || scopeLoading ? "animate-spin" : ""}`}
            />
            Refresh
          </button>
          {/* The lifecycle verbs — one honest place (the Claude.ai shape). */}
          <div className="relative" ref={menuRef}>
            <button
              type="button"
              onClick={() => setMenuOpen((o) => !o)}
              disabled={disconnecting}
              className="inline-flex h-7 w-7 items-center justify-center rounded border border-border text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50"
              aria-label="Connection actions"
            >
              {disconnecting ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <MoreHorizontal className="h-3.5 w-3.5" />
              )}
            </button>
            {menuOpen && (
              <div className="absolute right-0 top-full z-20 mt-1 min-w-[150px] rounded-md border border-border bg-popover py-1 shadow-md">
                <button
                  type="button"
                  onClick={() => {
                    setMenuOpen(false);
                    void reconnect();
                  }}
                  className="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
                  title="Re-runs authorization; existing credentials are replaced"
                >
                  <ArrowUpRight className="h-3 w-3" /> Reconnect
                </button>
                {onDisconnect && (
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpen(false);
                      onDisconnect();
                    }}
                    className="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-destructive hover:bg-destructive/10"
                  >
                    <Trash2 className="h-3 w-3" /> Disconnect
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="mt-4 flex-1 space-y-3 overflow-y-auto pb-2">
        {loading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            {error && <p className="py-1 text-sm text-destructive">{error}</p>}

            {/* ═══ CONNECTION stratum ═══ */}

            {/* ACCESS — the consent fact. */}
            <SectionShell title="Access">
              {grantedScopes.length > 0 ? (
                <div className="mb-2 flex flex-wrap gap-1">
                  {grantedScopes.map((s) => (
                    <span
                      key={s}
                      className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="mb-2 text-xs text-muted-foreground">
                  {meta.displayName} grants access at the app level — the{" "}
                  {resourceNoun} you shared during authorization.
                </p>
              )}
              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={() => void testConnection()}
                  disabled={probing}
                  className="inline-flex items-center gap-1.5 rounded-md border border-border/60 px-2.5 py-1 text-xs hover:bg-muted disabled:opacity-60"
                >
                  {probing ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <ShieldCheck className="h-3 w-3" />
                  )}
                  Test connection
                </button>
                {probeLabel && (
                  <span
                    className={`text-xs ${
                      probe?.status === "healthy"
                        ? "text-muted-foreground"
                        : "text-destructive"
                    }`}
                  >
                    {probe?.status === "healthy" ? "✓ " : ""}
                    {probeLabel}
                  </span>
                )}
              </div>
            </SectionShell>

            {/* WHAT THIS CONNECTION DOES — capability facts, served by the API
                from the machinery that enacts them (capture binding · exporter
                registry · the ADR-577 refusal). Facts, not controls. */}
            {does && (
              <SectionShell title="What this connection does">
                <dl className="space-y-1.5 text-xs">
                  <div className="flex gap-2">
                    <dt className="w-14 shrink-0 font-medium">Reads</dt>
                    <dd className="text-muted-foreground">
                      {does.reads}
                      {!captureEnabled && " (background reading paused)"}
                    </dd>
                  </div>
                  <div className="flex gap-2">
                    <dt className="w-14 shrink-0 font-medium">Writes</dt>
                    <dd className="text-muted-foreground">{does.writes}</dd>
                  </div>
                  {does.chat && (
                    <div className="flex gap-2">
                      <dt className="w-14 shrink-0 font-medium">Chat</dt>
                      <dd className="text-muted-foreground">{does.chat}</dd>
                    </div>
                  )}
                  <div className="flex gap-2">
                    <dt className="w-14 shrink-0 font-medium">Agents</dt>
                    <dd className="text-muted-foreground">{does.agents}</dd>
                  </div>
                </dl>
              </SectionShell>
            )}

            {/* ═══ CAPTURE stratum — the background writer's configuration,
                one consumer block: selection + destination.
                Collapsed to one honest line while the lane is dormant. ═══ */}
            <SectionShell title="Capture">
              {!captureEnabled && (
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-xs text-muted-foreground">
                    Nothing runs on a schedule — snapshots land when something
                    you set up reads this connection (a maintained file&apos;s
                    sources, a chat turn).
                    {selected.size > 0 &&
                      ` ${selected.size} ${resourceNoun} in scope.`}
                  </p>
                  <button
                    type="button"
                    onClick={() => setCaptureOpen((o) => !o)}
                    className="inline-flex items-center gap-1 text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
                  >
                    {captureExpanded ? (
                      <>
                        Hide configuration <ChevronDown className="h-3 w-3" />
                      </>
                    ) : (
                      <>
                        Configure <ChevronRight className="h-3 w-3" />
                      </>
                    )}
                  </button>
                </div>
              )}

              {captureExpanded && (
                <div className={captureEnabled ? "" : "mt-3"}>
                  <p className="mb-2 text-xs text-muted-foreground">
                    The background writer reads only the {resourceNoun} you
                    select here — snapshots land in your workspace as attributed
                    observation files. Nothing is ever selected for you.
                    {provider === "github" &&
                      " For GitHub this selection also bounds which repos platform tools may answer about (empty = unrestricted)."}
                  </p>

                  {scopeLoading ? (
                    <div className="flex items-center gap-2 py-2 text-xs text-muted-foreground">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      Discovering {resourceNoun}…
                    </div>
                  ) : scopeError ? (
                    // Discovery failed — scoped here so ACCESS (Test/Reconnect)
                    // stays usable. A 502 from the landscape route usually
                    // means the token no longer authenticates.
                    <div className="py-2">
                      <p className="text-sm text-destructive">
                        Couldn&apos;t list {resourceNoun}: {scopeError}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        This usually means the connection&apos;s authorization
                        has expired — Reconnect to refresh it, then Refresh
                        here.
                      </p>
                      <button
                        type="button"
                        onClick={() => void reconnect()}
                        className="mt-2 inline-flex items-center gap-1 rounded-md border border-border/60 px-2.5 py-1 text-xs hover:bg-muted"
                      >
                        Reconnect
                        <ArrowUpRight className="h-3 w-3" />
                      </button>
                    </div>
                  ) : resources.length === 0 ? (
                    scopeEmptyState()
                  ) : (
                    <div className="max-h-72 space-y-1 overflow-y-auto rounded-md border border-border/60 p-1">
                      {resources.map((r) => {
                        const on = selected.has(r.id);
                        return (
                          <button
                            key={r.id}
                            type="button"
                            onClick={() => toggle(r.id)}
                            className={`flex w-full items-center gap-2 rounded px-2 py-2 text-left text-sm transition-colors hover:bg-muted ${
                              on ? "text-foreground" : "text-muted-foreground"
                            }`}
                          >
                            <span
                              className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${
                                on
                                  ? "border-primary bg-primary text-primary-foreground"
                                  : "border-border"
                              }`}
                            >
                              {on && <Check className="h-3 w-3" />}
                            </span>
                            <span className="truncate">{r.name}</span>
                            {/* ADR-079 scoring survives as a HINT only — never
                                a pre-check (auto-selection died 2026-08-19). */}
                            {r.recommended && !on && (
                              <span className="ml-auto shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                                Suggested
                              </span>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {resources.length > 0 && !scopeError && (
                    <div className="mt-3 flex items-center gap-3">
                      <button
                        type="button"
                        onClick={() => void save()}
                        disabled={saving}
                        className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
                      >
                        {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                        Save selection
                      </button>
                      <span className="text-xs text-muted-foreground">
                        {selected.size === 0
                          ? `nothing selected — the writer captures nothing`
                          : `${selected.size} selected${savedAt ? " · saved" : ""}`}
                      </span>
                    </div>
                  )}

                  {/* ADR-594 D1: no dials — the landing grammar is a fact,
                      stated, not configured. */}
                  <div className="mt-4 space-y-2 border-t border-border/60 pt-3">
                    {!agentEnabled && (
                      <p className="text-xs text-muted-foreground">
                        Reads are off — the agent layer is disabled on this
                        deployment.
                      </p>
                    )}
                    <p className="text-xs text-muted-foreground">
                      {/* ADR-594 D1: the landing grammar is fixed — no
                          destination dial. Snapshots stay until something
                          removes them (no GC sweeps this lane). */}
                      Snapshots land as attributed observation files under{" "}
                      <span className="font-mono">{defaultLane}</span>, and stay
                      until something removes them — kept, not swept.
                    </p>
                  </div>
                </div>
              )}
            </SectionShell>

            {/* YIELD — the writer's read-back (connector grain).
                ADR-404 D2: hidden while the capture lane is dormant. */}
            {captureEnabled && (
              <SectionShell title="Yield">
                <div className="flex items-center gap-2 rounded-md bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
                  <Clock className="h-3.5 w-3.5 shrink-0" />
                  <span>{freshnessLabel()}</span>
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  Captured {resourceNoun} land as attributed observation files
                  at the fixed intake lane — readable immediately, cited by anything
                  built from them.
                </p>
                {connectorFreshness?.observed_at && (
                  <SurfaceLink
                    to="files"
                    params={{ path: filesPath }}
                    className="mt-2 inline-flex items-center gap-1 text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
                  >
                    View captured files
                    <ArrowUpRight className="h-3 w-3" />
                  </SurfaceLink>
                )}
              </SectionShell>
            )}
          </>
        )}
      </div>
    </div>
  );
}
