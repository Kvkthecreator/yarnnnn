"use client";

import { useTranslations } from "next-intl";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { DESKTOP_PLATFORM_NAMES, downloadPath } from "@/lib/shell/desktop-app";
import { type Locale } from "@/i18n/config";
import { useMarketingChrome } from "./chrome";
import { HtmlLang } from "./HtmlLang";

/**
 * /download — the desktop app, in either language.
 *
 * Every download link in the product points at `/download/{platform}` and
 * every help link at this page (lib/shell/desktop-app.ts). The builds are
 * unsigned during the beta (operator ruling, 2026-09-23), so this page is
 * what makes a public link honest: it says so before the button, and gives
 * each platform its one step to open. When a build is signed, its steps go
 * and nothing else changes.
 *
 * The Mac step is System Settings → "Open Anyway", which needs the build's
 * ad-hoc signature to VERIFY — a broken one reads "damaged" and offers no
 * such button (scripts/release-shell.sh records why). The Terminal line is
 * the fallback for that case only.
 *
 * Both platforms are listed; the page never guesses the visitor's machine
 * (ADR-661 §7.6).
 */

const MAC_UNQUARANTINE = "xattr -dr com.apple.quarantine /Applications/yarnnn.app";

export function DownloadPageBody({ locale }: { locale: Locale }) {
  const t = useTranslations("marketing.download");
  const chrome = useMarketingChrome();
  const mac = downloadPath("mac");
  const windows = downloadPath("windows");

  return (
    <div className="relative min-h-screen flex flex-col bg-[#0f1419] text-white overflow-x-hidden">
      <HtmlLang locale={locale} />
      <GrainOverlay variant="dark" />
      <ShaderBackgroundDark />

      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted locale={locale} nav={chrome.nav} path="/download" />

        <main className="flex-1">
          <section className="max-w-3xl mx-auto px-6 py-24 md:py-32">
            <h1 className="text-4xl md:text-5xl font-medium mb-4 tracking-tight leading-[1.1]">
              {t("heading")}
            </h1>
            <p className="text-white/50 mb-6 max-w-xl">{t("intro")}</p>
            <p className="text-sm text-white/70 border border-white/10 rounded-lg px-4 py-3 mb-16 max-w-xl">
              {t("beta")}
            </p>

            <div className="space-y-16">
              <div className="border-b border-white/5 pb-12">
                <div className="flex flex-wrap items-baseline justify-between gap-4 mb-2">
                  <h2 className="text-2xl font-medium">
                    {t("platformTitle", { platform: DESKTOP_PLATFORM_NAMES.mac })}
                  </h2>
                  {mac ? (
                    <a
                      href={mac}
                      className="inline-block px-6 py-2.5 bg-white text-black text-sm font-medium rounded-full hover:bg-white/90 transition-colors"
                    >
                      {t("downloadFor", { platform: DESKTOP_PLATFORM_NAMES.mac })}
                    </a>
                  ) : (
                    <span className="text-sm text-white/40">{t("notYet")}</span>
                  )}
                </div>
                <p className="text-sm text-white/40 mb-8">{t("macRequires")}</p>

                <h3 className="text-xs text-white/30 uppercase tracking-widest mb-4">{t("firstOpen")}</h3>
                <ol className="list-decimal pl-5 space-y-3 text-white/60 leading-relaxed">
                  <li>{t("macStep1")}</li>
                  <li>{t("macStep2")}</li>
                  <li>{t("macStep3")}</li>
                </ol>
                <p className="text-sm text-white/40 mt-6 mb-2">{t("macDamaged")}</p>
                <code className="block text-sm bg-white/5 border border-white/10 rounded-md px-3 py-2 overflow-x-auto whitespace-nowrap">
                  {MAC_UNQUARANTINE}
                </code>
              </div>

              <div className="border-b border-white/5 pb-12">
                <div className="flex flex-wrap items-baseline justify-between gap-4 mb-2">
                  <h2 className="text-2xl font-medium">
                    {t("platformTitle", { platform: DESKTOP_PLATFORM_NAMES.windows })}
                  </h2>
                  {windows ? (
                    <a
                      href={windows}
                      className="inline-block px-6 py-2.5 bg-white text-black text-sm font-medium rounded-full hover:bg-white/90 transition-colors"
                    >
                      {t("downloadFor", { platform: DESKTOP_PLATFORM_NAMES.windows })}
                    </a>
                  ) : (
                    <span className="text-sm text-white/40">{t("notYet")}</span>
                  )}
                </div>
                <p className="text-sm text-white/40 mb-8">{t("windowsRequires")}</p>

                <h3 className="text-xs text-white/30 uppercase tracking-widest mb-4">{t("firstOpen")}</h3>
                <ol className="list-decimal pl-5 space-y-3 text-white/60 leading-relaxed">
                  <li>{t("windowsStep1")}</li>
                  <li>{t("windowsStep2")}</li>
                </ol>
              </div>

              <div>
                <h2 className="text-xs text-white/30 uppercase tracking-widest mb-4">{t("afterTitle")}</h2>
                <p className="text-white/50 leading-relaxed">{t("afterBody")}</p>
              </div>
            </div>
          </section>
        </main>

        <LandingFooter inverted locale={locale} words={chrome.footer} />
      </div>
    </div>
  );
}
