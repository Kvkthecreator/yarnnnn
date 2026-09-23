"use client";

/**
 * Settings → Desktop app → the browser switch (ADR-662 D12/D14).
 *
 * The switch belongs to THIS machine, not the workspace: the answer lives in
 * the desktop app's host, and turning it on is the host's own consent dialog
 * (ADR-663 D4) — this row only asks. Three states, one row:
 *   - the desktop app, with the browser pane: the switch;
 *   - the desktop app, on a host older than the pane: update to get it;
 *   - the web: what the desktop app adds.
 */

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Globe } from "lucide-react";
import { isNativeShell } from "@/lib/shell/external-navigation";
import {
  browserHandsAvailable,
  browserHandsOn,
  disableBrowserHands,
  enableBrowserHands,
} from "@/lib/shell/hands";

type State = "loading" | "web" | "update" | "off" | "on";

export function DesktopBrowserSetting() {
  const t = useTranslations("settings.desktop.browser");
  const [state, setState] = useState<State>("loading");
  const [declined, setDeclined] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    (async () => {
      if (!isNativeShell()) return live && setState("web");
      if (!(await browserHandsAvailable())) return live && setState("update");
      const on = await browserHandsOn();
      if (live) setState(on ? "on" : "off");
    })();
    return () => {
      live = false;
    };
  }, []);

  const toggle = async () => {
    setBusy(true);
    setDeclined(false);
    if (state === "on") {
      await disableBrowserHands();
      setState("off");
    } else {
      const allowed = await enableBrowserHands();
      setState(allowed ? "on" : "off");
      setDeclined(!allowed);
    }
    setBusy(false);
  };

  if (state === "loading") return null;

  return (
    <div className="mt-6 rounded-lg border border-border px-4 py-3">
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 gap-3">
          <Globe className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
          <div className="min-w-0">
            <p className="text-sm font-medium">{t("title")}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {state === "web" ? t("webOnly") : state === "update" ? t("update") : t("body")}
            </p>
            {declined && <p className="mt-1 text-xs text-muted-foreground">{t("declined")}</p>}
          </div>
        </div>
        {(state === "on" || state === "off") && (
          <button
            type="button"
            role="switch"
            aria-checked={state === "on"}
            disabled={busy}
            onClick={toggle}
            className="shrink-0 rounded-md border border-border px-3 py-1 text-sm hover:bg-muted disabled:opacity-50"
          >
            {state === "on" ? t("turnOff") : t("turnOn")}
          </button>
        )}
      </div>
    </div>
  );
}
