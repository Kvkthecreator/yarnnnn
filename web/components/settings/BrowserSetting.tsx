"use client";

/**
 * Settings → Your browser (ADR-662 D15 → ADR-664 Amendment 1).
 *
 * The agent works in the member's own Chrome through the yarnnn extension —
 * from yarnnn on the web in Chrome, or relayed from the desktop app. It is not
 * a desktop feature, so it has its own pane rather than a row in the desktop
 * app's (where it sat until 2026-09-24, hidden from every web member). This row
 * says whether it is connected here, and is its on/off switch. Off applies at once; ON is asked
 * of the member in a window the EXTENSION draws (ADR-663 D4) — this row can
 * only ask. The site lists stay in the extension's toolbar button.
 */

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Globe } from "lucide-react";
import { browserHands, setBrowserHands, type BrowserHands } from "@/lib/shell/hands";
import { isNativeShell } from "@/lib/shell/external-navigation";
import { AddToChrome } from "@/components/shared/AddToChrome";

export function BrowserSetting() {
  const t = useTranslations("settings.browser");
  const [hands, setHands] = useState<BrowserHands | null>(null);
  const [busy, setBusy] = useState(false);
  const [declined, setDeclined] = useState(false);

  useEffect(() => {
    let live = true;
    browserHands().then((h) => live && setHands(h));
    return () => {
      live = false;
    };
  }, []);

  if (!hands) return null;

  const hostTooOld = hands.executor === null && "hostTooOld" in hands && hands.hostTooOld;
  const connected = hands.executor !== null && hands.connected;
  const version = "version" in hands && hands.version ? hands.version : "";
  const body = hostTooOld
    ? t("update")
    : !connected
      ? t("extensionMissing")
      : hands.on
        ? t("extensionConnected", { version })
        : t("extensionOff", { version });

  const toggle = async () => {
    setBusy(true);
    setDeclined(false);
    const want = !hands.on;
    const on = await setBrowserHands(want);
    setDeclined(want && !on);
    setHands(await browserHands());
    setBusy(false);
  };

  return (
    <div className="rounded-lg border border-border px-4 py-3">
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 gap-3">
          <Globe className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
          <div className="min-w-0">
            <p className="text-sm font-medium">{t("title")}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{body}</p>
            {/* The desktop app relays to the extension over native messaging,
                so Chrome must be running — true only there. */}
            {!connected && !hostTooOld && isNativeShell() && (
              <p className="mt-1 text-xs text-muted-foreground">{t("desktopKeepOpen")}</p>
            )}
            {declined && <p className="mt-1 text-xs text-muted-foreground">{t("declined")}</p>}
          </div>
        </div>
        {connected && (
          <button
            type="button"
            role="switch"
            aria-checked={hands.on}
            aria-label={t("title")}
            disabled={busy}
            onClick={toggle}
            className={
              "relative mt-0.5 inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors disabled:opacity-50 " +
              (hands.on ? "bg-foreground" : "bg-muted-foreground/30")
            }
          >
            <span
              className={
                "inline-block h-4 w-4 rounded-full bg-background shadow transition-transform " +
                (hands.on ? "translate-x-[18px]" : "translate-x-[2px]")
              }
            />
          </button>
        )}
        {!connected && !hostTooOld && (
          <AddToChrome
            fallback
            className="shrink-0 rounded-md border border-border px-3 py-1 text-sm hover:bg-muted"
            fallbackClassName="max-w-[12rem] shrink-0 text-right text-xs text-muted-foreground"
          />
        )}
      </div>
    </div>
  );
}
