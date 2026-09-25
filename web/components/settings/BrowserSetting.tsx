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
 *
 * Not connected, and no store listing yet (ADR-664 Amendment 2): the member
 * installs it by hand — the zip, and the three steps Chrome needs. Coming back
 * to this window re-checks, so it says "on" without a reload once it is loaded.
 */

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Check, Copy, Download, Globe } from "lucide-react";
import { browserHands, setBrowserHands, type BrowserHands } from "@/lib/shell/hands";
import { isNativeShell, openExternal, webOrigin } from "@/lib/shell/external-navigation";
import { AddToChrome, EXTENSION_PUBLISHED } from "@/components/shared/AddToChrome";
import { EXTENSION_DOWNLOAD_PATH } from "@/lib/shell/desktop-app";

type StatusKey = "status.on" | "status.off" | "status.missing" | "status.notConnected" | "status.update";

export function BrowserSetting() {
  const t = useTranslations("settings.browser");
  const [hands, setHands] = useState<BrowserHands | null>(null);
  const [busy, setBusy] = useState(false);
  const [declined, setDeclined] = useState(false);

  useEffect(() => {
    let live = true;
    const read = () => browserHands().then((h) => live && setHands(h));
    void read();
    // Installing happens in another window (chrome://extensions); coming back
    // here is when to look again.
    window.addEventListener("focus", read);
    return () => {
      live = false;
      window.removeEventListener("focus", read);
    };
  }, []);

  if (!hands) return null;

  const hostTooOld = hands.executor === null && "hostTooOld" in hands && hands.hostTooOld;
  const connected = hands.executor !== null && hands.connected;
  const version = "version" in hands && hands.version ? hands.version : "";
  // The state first, in two words and a colour; the sentence under it explains.
  // Not connected in the desktop app most often means Chrome is closed (the app
  // reaches the extension through it), so it is not called "not installed".
  const status: { key: StatusKey; dot: string } = hostTooOld
    ? { key: "status.update", dot: "bg-amber-500" }
    : !connected
      ? { key: isNativeShell() ? "status.notConnected" : "status.missing", dot: "bg-muted-foreground/40" }
      : hands.on
        ? { key: "status.on", dot: "bg-emerald-500" }
        : { key: "status.off", dot: "bg-amber-500" };
  const body = hostTooOld
    ? t("update")
    : !connected
      ? t("extensionMissing")
      : hands.on
        ? t("extensionConnected")
        : t("extensionOff");

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
            <p role="status" className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs">
              <span className="inline-flex items-center gap-1.5 font-medium text-foreground">
                <span className={`h-2 w-2 rounded-full ${status.dot}`} aria-hidden />
                {t(status.key)}
              </span>
              {connected && version && (
                <span className="text-muted-foreground">{t("version", { version })}</span>
              )}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">{body}</p>
            {/* The desktop app relays to the extension over native messaging,
                so Chrome must be running — true only there. */}
            {!connected && !hostTooOld && isNativeShell() && (
              <p className="mt-1 text-xs text-muted-foreground">{t("desktopKeepOpen")}</p>
            )}
            {declined && <p className="mt-1 text-xs text-muted-foreground">{t("declined")}</p>}
            {!connected && !hostTooOld && !EXTENSION_PUBLISHED && <InstallByHand />}
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
        {!connected && !hostTooOld && EXTENSION_PUBLISHED && (
          <AddToChrome className="shrink-0 rounded-md border border-border px-3 py-1 text-sm hover:bg-muted" />
        )}
      </div>
    </div>
  );
}

/** Chrome's own address — an identifier, not copy. A web page cannot link to
 *  it (Chrome refuses), so the member copies it. */
const EXTENSIONS_PAGE = "chrome://extensions";

/** The manual install, while the Chrome Web Store reviews the listing. */
function InstallByHand() {
  const t = useTranslations("settings.browser.manual");
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(EXTENSIONS_PAGE);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // No clipboard (an insecure context): the address is on screen to type.
    }
  };
  return (
    <div className="mt-3 rounded-md bg-muted/50 px-3 py-3">
      <p className="text-xs text-muted-foreground">{t("intro")}</p>
      <a
        href={EXTENSION_DOWNLOAD_PATH}
        onClick={(e) => {
          // In the desktop app a download leaves the window (ADR-661 §4.3).
          if (!isNativeShell()) return;
          e.preventDefault();
          openExternal(`${webOrigin()}${EXTENSION_DOWNLOAD_PATH}`);
        }}
        className="mt-2 inline-flex items-center gap-1.5 rounded-md bg-foreground px-3 py-1.5 text-xs font-medium text-background hover:opacity-90"
      >
        <Download className="h-3.5 w-3.5" aria-hidden />
        {t("download")}
      </a>
      <ol className="mt-3 list-decimal space-y-1 pl-4 text-xs text-foreground">
        <li>{t("unzip")}</li>
        <li>
          {t.rich("openExtensions", {
            url: () => (
              <button
                type="button"
                onClick={copy}
                className="mx-0.5 inline-flex items-center gap-1 rounded border border-border bg-background px-1.5 py-0.5 font-mono text-[11px] hover:bg-muted"
              >
                {EXTENSIONS_PAGE}
                {copied ? <Check className="h-3 w-3" aria-hidden /> : <Copy className="h-3 w-3" aria-hidden />}
              </button>
            ),
          })}
        </li>
        <li>{t("loadUnpacked")}</li>
      </ol>
      <p className="mt-2 text-xs text-muted-foreground">{t("after")}</p>
    </div>
  );
}
