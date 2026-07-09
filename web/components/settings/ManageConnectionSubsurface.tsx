"use client";

/**
 * ManageConnectionSubsurface — the per-connection DEEP manage screen (ADR-392
 * D7 + Phase B; 4-section design per ADR-401 D7 / docs/design/connection-manager.md).
 * The drill-in one level down from the Connections pane, routed by
 * `channels.connector=<provider>` (the first intra-pane drill-in on the
 * Channels surface).
 *
 * Four sections, consent-line ordered (grant → scope → cadence → yield):
 *   - ACCESS — the consent fact: granted OAuth scopes (metadata.scope), the
 *     on-demand validate probe (the ONLY honest liveness signal — the stored
 *     status column is a connect-time fact, ADR-401 D6), and Reconnect
 *     (re-runs authorize→callback; the upsert overwrites credentials).
 *   - SCOPE — the aperture: the DECLARED selection checklist. Saving authors
 *     the watch declaration (operation/_connectors/{platform}/_watch.yaml).
 *   - CADENCE — the capture entry's read interval (_captures.yaml, seeded at
 *     select-time per ADR-394 D2), with honest paused / agent-disabled states.
 *   - YIELD — the read-back: one connector-level freshness line (the capture
 *     signal's true grain — the connector is the unit of perception, channels
 *     are its aperture; per-channel freshness is deliberately not modelled),
 *     the derive truth (retained now, understood when the agent engages), and
 *     a deep-link into the Files surface at inbound/{platform}/.
 *
 * Parent (ConnectedIntegrationsSection) owns Disconnect; this subsurface owns
 * everything else in the lifecycle's operator half. Back to the list is the
 * caller's `onBack` (clears the `connector` param).
 */

import { useCallback, useEffect, useState } from "react";
import {
  ArrowLeft,
  ArrowUpRight,
  Check,
  Clock,
  Loader2,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { api } from "@/lib/api/client";
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

interface CaptureEntry {
  schedule: string | null;
  paused: boolean;
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
}

function relativeTime(iso?: string): string {
  if (!iso) return "not reading yet";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "unknown";
  const mins = Math.floor((Date.now() - then) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function sinceLabel(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString(undefined, { month: "short", year: "numeric" });
}

/** "@every 15min" → "every 15min"; cron-ish strings render verbatim. */
function scheduleLabel(schedule: string | null): string {
  if (!schedule) return "on its default cadence";
  const s = schedule.trim();
  return s.startsWith("@every ") ? `every ${s.slice("@every ".length)}` : `on ${s}`;
}

/** Friendly labels for the bounded cadence enum (ADR-401 Phase 4). */
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
}: ManageConnectionSubsurfaceProps) {
  const provider = meta.provider as SelectableProvider;
  const resourceNoun = meta.resourceNoun ?? "sources";

  const [resources, setResources] = useState<Resource[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  // Connector-level capture freshness (ADR-393 grain). The capture health signal
  // (_capture_signal.yaml) is keyed by CAPTURE SLUG (`capture-{platform}`) — ONE
  // block per connector, not per selector. The connector is the unit of
  // perception; the selected channels are its aperture (ADR-335).
  const [connectorFreshness, setConnectorFreshness] = useState<Observed | null>(null);
  const [grantedScopes, setGrantedScopes] = useState<string[]>([]);
  const [connection, setConnection] = useState<ConnectionFacts | null>(null);
  const [capture, setCapture] = useState<CaptureEntry | null>(null);
  const [cadenceChoices, setCadenceChoices] = useState<string[]>([]);
  const [cadenceSaving, setCadenceSaving] = useState(false);
  const [agentEnabled, setAgentEnabled] = useState(true);
  // ADR-404 D2: the capture lane is dormant for the commons-first launch —
  // CADENCE + YIELD render only when the deployment runs the lane.
  const [captureEnabled, setCaptureEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [probing, setProbing] = useState(false);
  const [probe, setProbe] = useState<ProbeResult | null>(null);

  const load = useCallback(
    async (refresh?: boolean) => {
      setLoading(true);
      setError(null);
      try {
        const [landscape, current, signal] = await Promise.all([
          api.integrations.getLandscape(provider, refresh),
          api.integrations.getSources(provider),
          api.integrations.getCaptureSignal(provider).catch(() => null),
        ]);
        setResources(
          (landscape.resources || []).map((r) => ({ id: r.id, name: r.name })),
        );
        setSelected(
          new Set<string>((current.sources || []).map((s) => s.id).filter(Boolean)),
        );
        // One observed block for the whole connector, keyed by capture slug.
        const block = signal?.observed?.[`capture-${provider}`] ?? null;
        setConnectorFreshness(block as Observed | null);
        setGrantedScopes(signal?.granted_scopes ?? []);
        setConnection(signal?.connection ?? null);
        setCapture(signal?.capture ?? null);
        setCadenceChoices(signal?.cadence_choices ?? []);
        setAgentEnabled(signal?.agent_enabled ?? true);
        setCaptureEnabled(signal?.connector_capture_enabled ?? false);
      } catch (e) {
        setError(
          e instanceof Error ? e.message : `Could not load ${provider} ${resourceNoun}.`,
        );
      } finally {
        setLoading(false);
      }
    },
    [provider, resourceNoun],
  );

  useEffect(() => {
    void load();
  }, [load]);

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
      // Seed-at-select (ADR-394 D2) may have just created/paused the capture
      // entry — refresh the CADENCE facts without a full reload.
      const signal = await api.integrations.getCaptureSignal(provider).catch(() => null);
      if (signal) setCapture(signal.capture ?? null);
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
  // There is deliberately no separate reconnect endpoint.
  const reconnect = async () => {
    try {
      // ADR-425 (2026-07-09): connectors re-homed to the account door (a
      // platform credential is a human's account object). The reconnect
      // round-trip returns to the account door's Connectors pane + drill-in.
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

  const cadenceLine = (): string => {
    if (!agentEnabled)
      return "Reads are off — the agent layer is disabled on this deployment.";
    if (!capture)
      return "Not reading yet — save a selection to start reads.";
    if (capture.paused)
      return `Not reading — select at least one ${resourceNoun.replace(/s$/, "")}.`;
    // With the dial rendered the sentence completes as "Reads [select]";
    // without choices it stays a full sentence.
    return cadenceChoices.length > 0 ? "Reads" : `Reads ${scheduleLabel(capture.schedule)}.`;
  };

  // The CADENCE dial (ADR-401 Phase 4) — bounded enum, floor 15min. The
  // write edits only the capture entry's schedule; the index rematerializes
  // server-side so next_run recomputes.
  const changeCadence = async (schedule: string) => {
    if (!schedule) return;
    setCadenceSaving(true);
    setError(null);
    try {
      await api.integrations.updateCadence(provider, schedule);
      setCapture((prev) => (prev ? { ...prev, schedule } : prev));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not change the read cadence.");
    } finally {
      setCadenceSaving(false);
    }
  };

  const since = sinceLabel(connection?.connected_at);
  const probeLabel =
    probe &&
    (probe.status === "healthy"
      ? `read OK · ${relativeTime(new Date(probe.at).toISOString())}`
      : `${probe.status}${probe.errors?.length ? ` — ${probe.errors[0]}` : ""}`);

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
        <button
          type="button"
          onClick={() => void load(true)}
          disabled={loading}
          className="ml-auto inline-flex shrink-0 items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          title="Re-discover from the platform"
        >
          <RefreshCw className={`h-3 w-3 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      <div className="mt-4 flex-1 space-y-3 overflow-y-auto pb-2">
        {loading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <p className="py-3 text-sm text-destructive">{error}</p>
        ) : (
          <>
            {/* ACCESS — the consent fact (above the line). */}
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
                <button
                  type="button"
                  onClick={() => void reconnect()}
                  className="inline-flex items-center gap-1 text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
                  title="Re-runs authorization; existing credentials are replaced"
                >
                  Reconnect
                  <ArrowUpRight className="h-3 w-3" />
                </button>
              </div>
            </SectionShell>

            {/* SCOPE — the aperture (above the line). */}
            <SectionShell title="Scope">
              <p className="mb-2 text-xs text-muted-foreground">
                Selected {resourceNoun} become your operation&apos;s perception.
                Selecting is a declaration, not a sync.
              </p>
              {resources.length === 0 ? (
                <p className="py-2 text-sm text-muted-foreground">
                  No {resourceNoun} discovered. Try Refresh.
                </p>
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
            </SectionShell>

            {/* CADENCE — the read interval, operator-tunable within the
                bounded enum (ADR-401 Phase 4). The select only renders once
                a capture entry exists (seeded at first save-with-selection).
                ADR-404 D2: hidden while the capture lane is dormant. */}
            {captureEnabled && (
            <SectionShell title="Cadence">
              <div className="flex flex-wrap items-center gap-3">
                <p className="text-sm text-muted-foreground">{cadenceLine()}</p>
                {capture && !capture.paused && agentEnabled && cadenceChoices.length > 0 && (
                  <select
                    value={
                      capture.schedule && cadenceChoices.includes(capture.schedule)
                        ? capture.schedule
                        : ""
                    }
                    disabled={cadenceSaving}
                    onChange={(e) => void changeCadence(e.target.value)}
                    className="rounded-md border border-border/60 bg-background px-2 py-1 text-xs disabled:opacity-60"
                    aria-label="Read cadence"
                  >
                    {capture.schedule && !cadenceChoices.includes(capture.schedule) && (
                      <option value="" disabled>
                        {scheduleLabel(capture.schedule)}
                      </option>
                    )}
                    {cadenceChoices.map((c) => (
                      <option key={c} value={c}>
                        {CADENCE_LABELS[c] ?? scheduleLabel(c)}
                      </option>
                    ))}
                  </select>
                )}
                {cadenceSaving && (
                  <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
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
                Captured {resourceNoun} are retained in the operation&apos;s
                inbound lane. Your agent distills them into memory when it next
                engages — retained now, understood on engagement.
              </p>
              {connectorFreshness?.observed_at && (
                <SurfaceLink
                  to="files"
                  params={{ path: `/workspace/inbound/${provider}` }}
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
