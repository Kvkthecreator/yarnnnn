"use client";

/**
 * RetentionDial — the workspace-level raw-capture retention window (ADR-392 D8).
 *
 * Controls governance/_retention.yaml `retention_days` via GET/PUT
 * /integrations/retention. WORKSPACE-scoped — one window for all connectors'
 * raw lanes (per-connection retention is D8's deferred "eventually"). Presets
 * (7/14/30) over a dynamic int; the kernel default is 30.
 *
 * What it governs: how long raw pulled content lives in the capture lane
 * (inbound/{platform}/) before derive-then-prune GC drops it (only after a
 * derived act has cited it — un-distilled evidence is never dropped).
 */

import { useEffect, useState } from "react";
import { Loader2, Check } from "lucide-react";
import { api } from "@/lib/api/client";

export function RetentionDial() {
  const [days, setDays] = useState<number | null>(null);
  const [presets, setPresets] = useState<number[]>([7, 14, 30]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<number | null>(null);
  const [savedDays, setSavedDays] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const r = await api.integrations.getRetention();
        if (!active) return;
        setDays(r.retention_days);
        if (r.presets?.length) setPresets(r.presets);
      } catch {
        if (active) setDays(30); // kernel default fallback
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const choose = async (value: number) => {
    if (value === days) return;
    setSaving(value);
    try {
      const r = await api.integrations.updateRetention(value);
      setDays(r.retention_days);
      setSavedDays(r.retention_days);
    } catch {
      // keep prior value on failure
    } finally {
      setSaving(null);
    }
  };

  return (
    <div className="rounded-lg border border-border p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-medium">Raw capture retention</div>
          <p className="text-xs text-muted-foreground">
            How long raw pulled content is kept before it&apos;s pruned (only after a
            derived act has cited it). One window for all connectors.
          </p>
        </div>
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        ) : (
          <div className="inline-flex items-center gap-1 rounded-md border border-border p-0.5">
            {presets.map((p) => {
              const active = days === p;
              return (
                <button
                  key={p}
                  type="button"
                  onClick={() => void choose(p)}
                  disabled={saving !== null}
                  className={`inline-flex items-center gap-1 rounded px-2.5 py-1 text-sm transition-colors ${
                    active
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-muted"
                  }`}
                >
                  {saving === p ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : active && savedDays === p ? (
                    <Check className="h-3 w-3" />
                  ) : null}
                  {p}d
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
