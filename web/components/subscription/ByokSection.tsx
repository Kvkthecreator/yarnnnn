"use client";

/**
 * BYOK section — ADR-439. The enterprise-tier capability where the WORKSPACE's own
 * LLM provider key powers the member chat lanes (Altitude-2). When on, those calls
 * run on the customer's key and draw NOTHING from the pool; the steward always
 * meters on our keys.
 *
 * Rendered ONLY when `status.available` (tier_byok_available — enterprise). The key
 * is never returned by the API; this shows enabled/provider/configured and lets the
 * owner set a key, toggle, or clear it.
 */

import { useEffect, useState } from "react";
import { api } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Loader2, KeyRound, Check } from "lucide-react";
import type { ByokStatus } from "@/types";

const PROVIDERS: { value: string; label: string }[] = [
  { value: "anthropic", label: "Anthropic (Claude)" },
  { value: "openai", label: "OpenAI (GPT)" },
  { value: "gemini", label: "Google (Gemini)" },
  { value: "deepseek", label: "DeepSeek" },
];

export function ByokSection() {
  const [status, setStatus] = useState<ByokStatus | null>(null);
  const [provider, setProvider] = useState<string>("anthropic");
  const [apiKey, setApiKey] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.workspace
      .getByok()
      .then((s) => {
        if (!cancelled) {
          setStatus(s);
          if (s.provider) setProvider(s.provider);
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // Not on an enterprise tier → the section does not render at all.
  if (status && !status.available) return null;

  const handleSave = async () => {
    if (!apiKey.trim()) return;
    setSaving(true);
    setErr(null);
    try {
      const s = await api.workspace.setByok(provider, apiKey.trim());
      setStatus(s);
      setApiKey(""); // never keep the plaintext in state after save
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not save the key");
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async () => {
    if (!status) return;
    setToggling(true);
    setErr(null);
    try {
      const s = await api.workspace.toggleByok(!status.enabled);
      setStatus(s);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not update BYOK");
    } finally {
      setToggling(false);
    }
  };

  const handleClear = async () => {
    setToggling(true);
    setErr(null);
    try {
      const s = await api.workspace.clearByok();
      setStatus(s);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not remove the key");
    } finally {
      setToggling(false);
    }
  };

  return (
    <section className="p-4 border border-border rounded-lg space-y-3">
      <div className="flex items-center gap-2">
        <KeyRound className="w-4 h-4 text-primary" />
        <h3 className="font-medium">Your own keys (BYOK)</h3>
        {status?.enabled && status?.configured && (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 dark:bg-emerald-950/40 px-2 py-0.5 text-[11px] font-medium text-emerald-700 dark:text-emerald-400">
            <Check className="w-3 h-3" /> Active
          </span>
        )}
      </div>
      <p className="text-sm text-muted-foreground leading-relaxed">
        Run your team&rsquo;s chat lanes on your organization&rsquo;s own LLM account. When on,
        those model calls bill to your provider and draw nothing from this workspace&rsquo;s
        allowance. The system agent always runs on our keys.
      </p>

      {err && (
        <div className="p-2 rounded border border-destructive/20 bg-destructive/5 text-xs text-destructive">
          {err}
        </div>
      )}

      {/* Current key state */}
      {status?.configured ? (
        <div className="flex items-center justify-between gap-3 text-sm border-t border-border/60 pt-3">
          <div className="text-muted-foreground">
            Key set for{" "}
            <span className="font-medium text-foreground">
              {PROVIDERS.find((p) => p.value === status.provider)?.label ?? status.provider}
            </span>{" "}
            · {status.enabled ? "in use" : "stored, currently off"}
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={handleToggle} disabled={toggling}>
              {toggling ? <Loader2 className="w-4 h-4 animate-spin" /> : status.enabled ? "Turn off" : "Turn on"}
            </Button>
            <Button size="sm" variant="ghost" onClick={handleClear} disabled={toggling}>
              Remove
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-2 border-t border-border/60 pt-3">
          <div className="flex gap-2">
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="rounded-md border border-border bg-transparent px-2 py-1.5 text-sm"
              aria-label="BYOK provider"
            >
              {PROVIDERS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Paste your provider API key"
              className="flex-1 rounded-md border border-border bg-transparent px-3 py-1.5 text-sm outline-none"
              aria-label="Provider API key"
            />
            <Button size="sm" onClick={handleSave} disabled={saving || !apiKey.trim()}>
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save key"}
            </Button>
          </div>
          <p className="text-[11px] text-muted-foreground">
            Stored encrypted; never shown again after saving.
          </p>
        </div>
      )}
    </section>
  );
}
