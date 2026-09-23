"use client";

/**
 * Settings → Desktop app → the browser row (ADR-662 D12/D14/D15).
 *
 * Which executor this page can reach decides the row (`browserHands()`):
 *   - in Chrome with the yarnnn extension: connected, and its own toolbar
 *     button is where it is switched and where sites are managed;
 *   - in Chrome without it: what adding it gives, and where to get it;
 *   - in the desktop app: the host's switch, whose consent is the host's own
 *     dialog (ADR-663 D4) — this row only asks;
 *   - in the desktop app on a host older than the pane: update to get it.
 */

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Globe } from "lucide-react";
import {
  CHROME_EXTENSION,
  browserHands,
  disableBrowserHands,
  enableBrowserHands,
  type BrowserHands,
} from "@/lib/shell/hands";

export function DesktopBrowserSetting() {
  const t = useTranslations("settings.desktop.browser");
  const [hands, setHands] = useState<BrowserHands | null>(null);
  const [declined, setDeclined] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    browserHands().then((h) => live && setHands(h));
    return () => {
      live = false;
    };
  }, []);

  if (!hands) return null;

  const toggleHost = async () => {
    setBusy(true);
    setDeclined(false);
    if (hands.on) {
      await disableBrowserHands();
      setHands({ executor: "host", on: false });
    } else {
      const allowed = await enableBrowserHands();
      setHands({ executor: "host", on: allowed });
      setDeclined(!allowed);
    }
    setBusy(false);
  };

  const body =
    hands.executor === "extension" ? t("extensionConnected", { version: hands.version })
    : hands.executor === "host" ? t("body")
    : "hostTooOld" in hands && hands.hostTooOld ? t("update")
    : t("extensionMissing");

  return (
    <div className="mt-6 rounded-lg border border-border px-4 py-3">
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 gap-3">
          <Globe className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
          <div className="min-w-0">
            <p className="text-sm font-medium">{t("title")}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{body}</p>
            {declined && <p className="mt-1 text-xs text-muted-foreground">{t("declined")}</p>}
          </div>
        </div>
        {hands.executor === "host" && (
          <button
            type="button"
            role="switch"
            aria-checked={hands.on}
            disabled={busy}
            onClick={toggleHost}
            className="shrink-0 rounded-md border border-border px-3 py-1 text-sm hover:bg-muted disabled:opacity-50"
          >
            {hands.on ? t("turnOff") : t("turnOn")}
          </button>
        )}
        {hands.executor === null && !("hostTooOld" in hands && hands.hostTooOld) && (
          CHROME_EXTENSION.storeUrl ? (
            <a
              href={CHROME_EXTENSION.storeUrl}
              target="_blank"
              rel="noreferrer"
              className="shrink-0 rounded-md border border-border px-3 py-1 text-sm hover:bg-muted"
            >
              {t("addToChrome")}
            </a>
          ) : (
            <span className="shrink-0 text-sm text-muted-foreground">{t("notYet")}</span>
          )
        )}
      </div>
    </div>
  );
}
