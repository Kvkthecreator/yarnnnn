"use client";

/**
 * ManageConnectionSubsurface — the per-connection DEEP manage screen (ADR-392
 * D7 + Phase B). The drill-in one level down from the Connections pane, routed
 * by `channels.connector=<provider>` (the first intra-pane drill-in on the
 * Channels surface). Replaces the inline in-card ConnectorSelectionPanel expand
 * (Singular Implementation — the selector lives here now, full-pane).
 *
 * It renders the DECLARED × OBSERVED selection surface:
 *   - DECLARED — the platform's discovered resources (channels/pages/repos) with
 *     per-item in/out toggles; saving authors the watch declaration
 *     (operation/_connectors/{platform}/_watch.yaml) via PUT .../sources.
 *   - OBSERVED — each in-scope selector's capture freshness from the capture
 *     signal (_capture_signal.yaml, ADR-393 D3): status · last-observed · items,
 *     or "not reading yet" when no capture has run. Honest by construction: a
 *     connector with no capture recurrence shows every selector un-observed.
 *
 * Parent (ConnectedIntegrationsSection) owns the connection lifecycle actions
 * (Reconnect / Disconnect); this subsurface owns selection + freshness. Back to
 * the list is the caller's `onBack` (clears the `connector` param).
 */

import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Check, Clock, Loader2, RefreshCw } from "lucide-react";
import { api } from "@/lib/api/client";
import type { ConnectorMeta } from "@/lib/connectors/registry";

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

export function ManageConnectionSubsurface({
  meta,
  onBack,
}: ManageConnectionSubsurfaceProps) {
  const provider = meta.provider as SelectableProvider;
  const resourceNoun = meta.resourceNoun ?? "sources";

  const [resources, setResources] = useState<Resource[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  // observed freshness keyed by selector id (best-effort — the capture signal
  // is keyed by capture slug; we surface the workspace capture health and match
  // by selector where the lane records it). Empty until a capture runs.
  const [observed, setObserved] = useState<Record<string, Observed>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);

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
        // Map the observed signal by selector id. The capture signal is keyed by
        // capture slug; when the lane records per-selector we match here, else
        // the whole map stays coarse (workspace capture health).
        if (signal?.observed) {
          const byId: Record<string, Observed> = {};
          for (const [slug, block] of Object.entries(signal.observed)) {
            byId[slug] = block as Observed;
          }
          setObserved(byId);
        } else {
          setObserved({});
        }
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
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save selection.");
    } finally {
      setSaving(false);
    }
  };

  // Observed freshness for a given selector, if the capture lane has recorded it.
  const freshnessFor = (id: string): Observed | undefined => observed[id];

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
            Pick which {resourceNoun} are in scope. Selected {resourceNoun} become
            your operation&apos;s perception — a capture reads them into substrate.
            Selecting is a declaration, not a sync.
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

      <div className="mt-4 flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <p className="py-3 text-sm text-destructive">{error}</p>
        ) : resources.length === 0 ? (
          <p className="py-3 text-sm text-muted-foreground">
            No {resourceNoun} discovered. Try Refresh.
          </p>
        ) : (
          <div className="space-y-1 rounded-md border border-border/60 p-1">
            {resources.map((r) => {
              const on = selected.has(r.id);
              const obs = freshnessFor(r.id);
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
                  {/* Observed freshness (declared × observed). Only meaningful
                      for in-scope selectors; a capture writes this when it runs. */}
                  {on && (
                    <span className="ml-auto inline-flex shrink-0 items-center gap-1 text-xs text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      {obs?.observed_at ? (
                        <>
                          {relativeTime(obs.observed_at)}
                          {typeof obs.items === "number" ? ` · ${obs.items}` : ""}
                        </>
                      ) : (
                        "not reading yet"
                      )}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>

      <div className="mt-4 flex items-center gap-3 border-t border-border/60 pt-4">
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
    </div>
  );
}
