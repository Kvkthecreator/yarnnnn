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
import { useTranslations } from "next-intl";
import { api, APIError } from "@/lib/api/client";
import { useFeedback } from "@/contexts/FeedbackContext";
import { Button } from "@/components/ui/button";
import { Loader2, KeyRound, Check } from "lucide-react";
import type { ByokStatus } from "@/types";

const PROVIDERS: { value: string; label: string }[] = [
  { value: "anthropic", label: "Anthropic (Claude)" },
  { value: "openai", label: "OpenAI (GPT)" },
  { value: "gemini", label: "Google (Gemini)" },
  { value: "deepseek", label: "DeepSeek" },
  { value: "xai", label: "xAI (Grok)" },
];

export function ByokSection() {
  const t = useTranslations("billing.byok");
  const [status, setStatus] = useState<ByokStatus | null>(null);
  const [provider, setProvider] = useState<string>("anthropic");
  const [apiKey, setApiKey] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [toggling, setToggling] = useState(false);
  // Save / turn on-off / remove are discrete verbs: they report through the
  // canonical action-feedback layer (docs/design/ACTION-FEEDBACK.md). The
  // bespoke `err` banner they used to share is gone.
  const { runAction } = useFeedback();

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
    try {
      const s = await runAction(() => api.workspace.setByok(provider, apiKey.trim()), {
        pending: t("savePending"),
        success: t("saveSuccess"),
        error: (e) =>
          e instanceof APIError
            ? (e.data as { detail?: string })?.detail || t("saveError")
            : t("saveError"),
      });
      setStatus(s);
      setApiKey(""); // never keep the plaintext in state after save
    } catch {
      // Reported by the toast; the key stays in the field to be corrected.
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async () => {
    if (!status) return;
    const turningOn = !status.enabled;
    setToggling(true);
    try {
      const s = await runAction(() => api.workspace.toggleByok(turningOn), {
        pending: turningOn ? t("onPending") : t("offPending"),
        success: turningOn ? t("onSuccess") : t("offSuccess"),
        error: (e) =>
          e instanceof APIError
            ? (e.data as { detail?: string })?.detail || t("toggleError")
            : t("toggleError"),
      });
      setStatus(s);
    } catch {
      // Reported by the toast; the card keeps showing the state that still holds.
    } finally {
      setToggling(false);
    }
  };

  const handleClear = async () => {
    setToggling(true);
    try {
      const s = await runAction(() => api.workspace.clearByok(), {
        pending: t("removePending"),
        success: t("removeSuccess"),
        error: (e) =>
          e instanceof APIError
            ? (e.data as { detail?: string })?.detail || t("removeError")
            : t("removeError"),
      });
      setStatus(s);
    } catch {
      // Reported by the toast; the key is still in place.
    } finally {
      setToggling(false);
    }
  };

  return (
    <section className="p-4 border border-border rounded-lg space-y-3">
      <div className="flex items-center gap-2">
        <KeyRound className="w-4 h-4 text-primary" />
        <h3 className="font-medium">{t("title")}</h3>
        {status?.enabled && status?.configured && (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 dark:bg-emerald-950/40 px-2 py-0.5 text-[11px] font-medium text-emerald-700 dark:text-emerald-400">
            <Check className="w-3 h-3" /> {t("active")}
          </span>
        )}
      </div>
      <p className="text-sm text-muted-foreground leading-relaxed">{t("lead")}</p>

      {/* Current key state */}
      {status?.configured ? (
        <div className="flex items-center justify-between gap-3 text-sm border-t border-border/60 pt-3">
          <div className="text-muted-foreground">
            {t("keySetFor")}{" "}
            <span className="font-medium text-foreground">
              {PROVIDERS.find((p) => p.value === status.provider)?.label ?? status.provider}
            </span>{" "}
            · {status.enabled ? t("inUse") : t("storedOff")}
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={handleToggle} disabled={toggling}>
              {toggling ? <Loader2 className="w-4 h-4 animate-spin" /> : status.enabled ? t("turnOff") : t("turnOn")}
            </Button>
            <Button size="sm" variant="ghost" onClick={handleClear} disabled={toggling}>
              {t("remove")}
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
              aria-label={t("providerLabel")}
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
              placeholder={t("keyPlaceholder")}
              className="flex-1 rounded-md border border-border bg-transparent px-3 py-1.5 text-sm outline-none"
              aria-label={t("keyLabel")}
            />
            <Button size="sm" onClick={handleSave} disabled={saving || !apiKey.trim()}>
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : t("save")}
            </Button>
          </div>
          <p className="text-[11px] text-muted-foreground">{t("storedNote")}</p>
        </div>
      )}
    </section>
  );
}
