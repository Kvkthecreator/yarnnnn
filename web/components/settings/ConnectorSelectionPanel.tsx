"use client";

/**
 * ConnectorSelectionPanel — ADR-392 D7 (Phase 2: Select).
 *
 * The per-platform selection subsurface, one level down from the Connections
 * pane. Shows the connected platform's discovered resources (channels / pages /
 * repos) with per-item in/out toggles; saving authors the connector-watch
 * declaration (operation/_connectors/{platform}/_watch.yaml) via
 * PUT /integrations/{provider}/sources — which is what the Phase-3 capture
 * recurrence reads to know which slices to pull into inbound/{platform}/.
 *
 * This is the missing bridge between "connected" (a token) and "read" (content
 * in substrate): connecting makes a platform available; selecting a slice here
 * is what puts it in the operation's perception aperture (DP27 — declared, never
 * crawled). Selection is a DECLARATION, not a sync — it names what is perceived;
 * the capture recurrence does the pulling.
 */

import { useCallback, useEffect, useState } from "react";
import { Loader2, Check, RefreshCw } from "lucide-react";
import { api } from "@/lib/api/client";

type SelectableProvider = "slack" | "notion" | "github";

interface Resource {
  id: string;
  name: string;
}

interface ConnectorSelectionPanelProps {
  provider: SelectableProvider;
  /** Human label for the resource kind, e.g. "channels", "pages", "repos". */
  resourceNoun: string;
}

export function ConnectorSelectionPanel({
  provider,
  resourceNoun,
}: ConnectorSelectionPanelProps) {
  const [resources, setResources] = useState<Resource[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  const load = useCallback(
    async (refresh?: boolean) => {
      setLoading(true);
      setError(null);
      try {
        const [landscape, current] = await Promise.all([
          api.integrations.getLandscape(provider, refresh),
          api.integrations.getSources(provider),
        ]);
        setResources(
          (landscape.resources || []).map((r) => ({ id: r.id, name: r.name })),
        );
        // current.sources is the selected set; seed the toggle state from it.
        const sel = new Set<string>(
          (current.sources || []).map((s) => s.id).filter(Boolean),
        );
        setSelected(sel);
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

  return (
    <div className="mt-3 border-t border-border/60 pt-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground">
          Pick which {resourceNoun} are in scope. Selected {resourceNoun} become
          your operation&apos;s perception — a capture reads them into substrate.
          Selecting is a declaration, not a sync.
        </p>
        <button
          type="button"
          onClick={() => void load(true)}
          disabled={loading}
          className="inline-flex shrink-0 items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          title="Re-discover from the platform"
        >
          <RefreshCw className={`h-3 w-3 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-6">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : error ? (
        <p className="py-3 text-xs text-destructive">{error}</p>
      ) : resources.length === 0 ? (
        <p className="py-3 text-xs text-muted-foreground">
          No {resourceNoun} discovered. Try Refresh.
        </p>
      ) : (
        <>
          <div className="max-h-64 space-y-1 overflow-y-auto rounded-md border border-border/60 p-1">
            {resources.map((r) => {
              const on = selected.has(r.id);
              return (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => toggle(r.id)}
                  className={`flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm transition-colors hover:bg-muted ${
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

          <div className="mt-3 flex items-center gap-3">
            <button
              type="button"
              onClick={() => void save()}
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
            >
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Save selection
            </button>
            <span className="text-xs text-muted-foreground">
              {selected.size} in scope
              {savedAt ? " · saved" : ""}
            </span>
          </div>
        </>
      )}
    </div>
  );
}
