"use client";

/**
 * ManageConnectionSubsurface — the per-connection detail page (ADR-582 model;
 * drill-in routed by `settings.connector=<provider>` from the Connections pane).
 *
 * A connector is a WRITER: connect (OAuth) → select slices → attributed
 * observation files land at the destination on a cadence (ADR-582 D1). The
 * page presents that lifecycle in consent-line order:
 *
 *   - Header — the connection fact (workspace · since) + Refresh + the ⋮ menu
 *     (Reconnect / Disconnect — the lifecycle verbs, one honest place).
 *   - ACCESS — the consent fact: granted OAuth scopes (metadata.scope) and the
 *     on-demand validate probe (the ONLY honest liveness signal — the stored
 *     status column is a connect-time fact, ADR-401 D6).
 *   - SCOPE — the aperture: the selection checklist, saved to the ONE store
 *     (landscape.selected_sources, ADR-582 D2). It bounds BOTH dispositions:
 *     what capture lands, and what agents may reach (ADR-576 D2). Discovery
 *     failures render HERE (scoped), so a dead token never hides the recovery
 *     affordances above it.
 *   - CAPTURE — the three ADR-582 dials on settings["connector"]: cadence
 *     (D2), destination (D3), digest (D5, opt-in). Rendered only when the API
 *     serves the `settings` object (FE and API deploy separately).
 *   - YIELD — the read-back: connector-level freshness + a deep-link into the
 *     landed files. Hidden while the capture lane is dormant (ADR-404 D2).
 *
 * Semantics vs the Claude.ai connector page this borrows legibility from:
 * ours is a capture-aperture + settings surface, not per-tool permissions —
 * the selection list is what gets WRITTEN, not what may be CALLED.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowUpRight,
  Check,
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
}

interface Observed {
  status?: string;
  observed_at?: string;
  items?: number;
  last_error?: string;
}

interface ConnectorSettings {
  cadence: string;
  destination: string | null;
  digest: boolean;
}

interface ConnectorDoes {
  reads: string;
  writes: string;
  agents: string;
}

interface ConnectionFacts {
  workspace_name: string | null;
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

/** Friendly labels for the bounded cadence enum (ADR-582 D2, floor 15min). */
const CADENCE_LABELS: Record<string, string> = {
  "@every 15min": "Every 15 minutes",
  "@every 1h": "Hourly",
  "@every 6h": "Every 6 hours",
  "@every 24h": "Daily",
};

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
  const [settings, setSettings] = useState<ConnectorSettings | null>(null);
  const [does, setDoes] = useState<ConnectorDoes | null>(null);
  const [nothingSelected, setNothingSelected] = useState(false);
  const [cadenceChoices, setCadenceChoices] = useState<string[]>([]);
  const [agentEnabled, setAgentEnabled] = useState(true);
  // ADR-404 D2: the capture lane is dormant for the commons-first launch —
  // YIELD renders only when the deployment runs the lane; the CAPTURE dials
  // stay visible (they bind now, take effect on re-light) with an honest note.
  const [captureEnabled, setCaptureEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // The landscape (SCOPE's resource list) loads SEPARATELY so a discovery
  // failure — a revoked token, a platform outage — renders inside SCOPE and
  // never hides ACCESS, where Test connection and Reconnect live.
  const [resources, setResources] = useState<Resource[]>([]);
  const [scopeLoading, setScopeLoading] = useState(true);
  const [scopeError, setScopeError] = useState<string | null>(null);

  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [probing, setProbing] = useState(false);
  const [probe, setProbe] = useState<ProbeResult | null>(null);
  const [dialSaving, setDialSaving] = useState(false);
  const [dialError, setDialError] = useState<string | null>(null);
  const [destinationDraft, setDestinationDraft] = useState("");
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
      // `settings`/`does` are post-ADR-582 payload fields — absent on an
      // older API, in which case their sections simply don't render.
      setSettings(signal?.settings ?? null);
      setDoes(signal?.does ?? null);
      setDestinationDraft(signal?.settings?.destination ?? "");
      setNothingSelected(signal?.capture?.paused ?? false);
      setCadenceChoices(signal?.cadence_choices ?? []);
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
          (landscape.resources || []).map((r) => ({ id: r.id, name: r.name })),
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
      // "Paused" is simply an empty selection now (ADR-582 — no seeded entry);
      // reflect it without a full reload.
      setNothingSelected(selected.size === 0);
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

  // One dial write path — partial patch, echo the normalized store back.
  const patchSettings = async (patch: {
    cadence?: string;
    destination?: string | null;
    digest?: boolean;
  }) => {
    setDialSaving(true);
    setDialError(null);
    try {
      const res = await api.integrations.updateConnectorSettings(provider, patch);
      setSettings(res.settings);
      setDestinationDraft(res.settings.destination ?? "");
    } catch (e) {
      setDialError(
        e instanceof Error ? e.message : "Could not save the connector settings.",
      );
    } finally {
      setDialSaving(false);
    }
  };

  const commitDestination = () => {
    const draft = destinationDraft.trim();
    const current = settings?.destination ?? "";
    if (draft === current) return;
    void patchSettings({ destination: draft === "" ? null : draft });
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

  const defaultLane = `inbound/${provider}`;
  const filesPath = settings?.destination
    ? `/workspace/${settings.destination}`
    : `/workspace/${defaultLane}`;

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
          <p className="text-sm text-muted-foreground">
            Connected
            {connection?.workspace_name ? ` · ${connection.workspace_name}` : ""}
            {since ? ` · since ${since}` : ""}
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

            {/* WHAT THIS CONNECTION DOES — the capability facts, served by the
                API from the machinery that enacts them (capture binding ·
                exporter registry · the ADR-577 refusal). Facts, not controls:
                there is no per-tool enforcement point on the outbound side to
                bind dials to — the OAuth scope is the platform's control. */}
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
                  <div className="flex gap-2">
                    <dt className="w-14 shrink-0 font-medium">Agents</dt>
                    <dd className="text-muted-foreground">{does.agents}</dd>
                  </div>
                </dl>
              </SectionShell>
            )}

            {/* SCOPE — the aperture, both dispositions. */}
            <SectionShell title="Scope">
              <p className="mb-2 text-xs text-muted-foreground">
                Selected {resourceNoun} are this connection&apos;s aperture:
                what gets captured into your workspace, and what agents may
                reach through platform tools.
              </p>
              {!captureEnabled && (
                <p className="mb-2 text-xs text-muted-foreground">
                  Background reading is paused, so nothing is being captured on a
                  schedule. Your selection still bounds what agents may reach.
                </p>
              )}
              {scopeLoading ? (
                <div className="flex items-center gap-2 py-2 text-xs text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Discovering {resourceNoun}…
                </div>
              ) : scopeError ? (
                // Discovery failed — scoped here so ACCESS (Test/Reconnect)
                // stays usable. A 502 from the landscape route usually means
                // the token no longer authenticates.
                <div className="py-2">
                  <p className="text-sm text-destructive">
                    Couldn&apos;t list {resourceNoun}: {scopeError}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    This usually means the connection&apos;s authorization has
                    expired — Reconnect to refresh it, then Refresh here.
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
                <div className="space-y-1 rounded-md border border-border/60 p-1">
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
                    {selected.size} in scope{savedAt ? " · saved" : ""}
                  </span>
                </div>
              )}
            </SectionShell>

            {/* CAPTURE — the three ADR-582 dials. Rendered only when the API
                serves `settings` (a post-582 payload field — the FE and API
                deploy separately, so absence means an older API, not a bug). */}
            {settings && (
              <SectionShell title="Capture">
                {!agentEnabled ? (
                  <p className="mb-2 text-xs text-muted-foreground">
                    Reads are off — the agent layer is disabled on this
                    deployment.
                  </p>
                ) : !captureEnabled ? (
                  <p className="mb-2 text-xs text-muted-foreground">
                    Background reading is paused on this deployment. These
                    settings bind now and take effect when reading resumes.
                  </p>
                ) : nothingSelected ? (
                  <p className="mb-2 text-xs text-muted-foreground">
                    Nothing selected — captures skip this connector until you
                    select at least one {resourceNounSingular}.
                  </p>
                ) : null}

                <div className="space-y-3">
                  {/* Cadence (ADR-582 D2) — bounded enum, floor 15min. */}
                  <div className="flex flex-wrap items-center gap-3">
                    <label
                      htmlFor="connector-cadence"
                      className="w-24 shrink-0 text-xs font-medium"
                    >
                      Cadence
                    </label>
                    <select
                      id="connector-cadence"
                      value={
                        cadenceChoices.includes(settings.cadence)
                          ? settings.cadence
                          : ""
                      }
                      disabled={dialSaving}
                      onChange={(e) => {
                        if (e.target.value) {
                          void patchSettings({ cadence: e.target.value });
                        }
                      }}
                      className="rounded-md border border-border/60 bg-background px-2 py-1 text-xs disabled:opacity-60"
                    >
                      {!cadenceChoices.includes(settings.cadence) && (
                        <option value="" disabled>
                          {settings.cadence}
                        </option>
                      )}
                      {cadenceChoices.map((c) => (
                        <option key={c} value={c}>
                          {CADENCE_LABELS[c] ?? c}
                        </option>
                      ))}
                    </select>
                    <span className="text-xs text-muted-foreground">
                      How often selected {resourceNoun} are read.
                    </span>
                  </div>

                  {/* Destination (ADR-582 D3) — where snapshots land. */}
                  <div className="flex flex-wrap items-center gap-3">
                    <label
                      htmlFor="connector-destination"
                      className="w-24 shrink-0 text-xs font-medium"
                    >
                      Destination
                    </label>
                    <input
                      id="connector-destination"
                      type="text"
                      value={destinationDraft}
                      placeholder={defaultLane}
                      disabled={dialSaving}
                      onChange={(e) => setDestinationDraft(e.target.value)}
                      onBlur={commitDestination}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          (e.target as HTMLInputElement).blur();
                        }
                      }}
                      className="w-56 rounded-md border border-border/60 bg-background px-2 py-1 font-mono text-xs disabled:opacity-60"
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Workspace folder where snapshots land. Empty = the default{" "}
                    <span className="font-mono">{defaultLane}</span> lane, which
                    is cleaned up on the retention window; a folder you name
                    keeps its files like any other workspace files.
                  </p>

                  {/* Digest (ADR-582 D5) — the opt-in derive consumer. */}
                  <label className="flex cursor-pointer items-start gap-2">
                    <input
                      type="checkbox"
                      checked={settings.digest}
                      disabled={dialSaving}
                      onChange={(e) =>
                        void patchSettings({ digest: e.target.checked })
                      }
                      className="mt-0.5 h-3.5 w-3.5 accent-primary"
                    />
                    <span className="text-xs">
                      <span className="font-medium">Digest</span>{" "}
                      <span className="text-muted-foreground">
                        — maintain a living summary of each selected{" "}
                        {resourceNounSingular}, citing the raw snapshots. Uses
                        AI credits; off = snapshots only.
                      </span>
                    </span>
                  </label>

                  {dialSaving && (
                    <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                  )}
                  {dialError && (
                    <p className="text-xs text-destructive">{dialError}</p>
                  )}
                </div>
              </SectionShell>
            )}

            {/* YIELD — the read-back (connector grain).
                ADR-404 D2: hidden while the capture lane is dormant. */}
            {captureEnabled && (
              <SectionShell title="Yield">
                <div className="flex items-center gap-2 rounded-md bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
                  <Clock className="h-3.5 w-3.5 shrink-0" />
                  <span>{freshnessLabel()}</span>
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  Captured {resourceNoun} land as attributed observation files
                  at the destination — readable immediately, cited by anything
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
