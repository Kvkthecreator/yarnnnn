"use client";

/**
 * Settings → Desktop app → the browser row (ADR-662 D15).
 *
 * The agent works in the member's own Chrome through the yarnnn extension, in
 * Chrome directly or relayed from the desktop app. The extension is switched,
 * and its sites managed, from its own toolbar button — this row only says
 * whether it is connected here, and where to get it.
 */

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Globe } from "lucide-react";
import { CHROME_EXTENSION, browserHands, type BrowserHands } from "@/lib/shell/hands";

export function DesktopBrowserSetting() {
  const t = useTranslations("settings.desktop.browser");
  const [hands, setHands] = useState<BrowserHands | null>(null);

  useEffect(() => {
    let live = true;
    browserHands().then((h) => live && setHands(h));
    return () => {
      live = false;
    };
  }, []);

  if (!hands) return null;

  const hostTooOld = hands.executor === null && "hostTooOld" in hands && hands.hostTooOld;
  const connected = hands.executor !== null && hands.on;
  const body = hostTooOld
    ? t("update")
    : connected
      ? t("extensionConnected", { version: "version" in hands && hands.version ? hands.version : "" })
      : t("extensionMissing");

  return (
    <div className="mt-6 rounded-lg border border-border px-4 py-3">
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 gap-3">
          <Globe className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
          <div className="min-w-0">
            <p className="text-sm font-medium">{t("title")}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{body}</p>
          </div>
        </div>
        {!connected && !hostTooOld && (
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
