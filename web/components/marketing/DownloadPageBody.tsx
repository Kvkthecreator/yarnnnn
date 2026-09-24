"use client";

import { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { AppWindow, ArrowDown, Check, Copy, Download, LogIn, RefreshCw } from "lucide-react";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { SpotlightCard } from "@/components/landing/SpotlightCard";
import { ScrollReveal } from "@/components/landing/ScrollReveal";
import { ChatReplica } from "@/components/landing/product/ChatReplica";
import {
  DESKTOP_PLATFORMS,
  DESKTOP_PLATFORM_NAMES,
  downloadPath,
  type DesktopPlatform,
} from "@/lib/shell/desktop-app";
import { CTA } from "@/lib/cta";
import { type Locale } from "@/i18n/config";
import { useMarketingChrome } from "./chrome";
import { HtmlLang } from "./HtmlLang";

/**
 * /download — the desktop app, in either language.
 *
 * Every download link in the product points at `/download/{platform}` and
 * every help link at this page (lib/shell/desktop-app.ts). The builds are
 * unsigned during the beta (operator ruling, 2026-09-23), so this page is
 * what makes a public link honest: it says so before the buttons, and gives
 * each platform its one step to open. When a build is signed, its steps go
 * and nothing else changes.
 *
 * The Mac step is System Settings → "Open Anyway", which needs the build's
 * ad-hoc signature to VERIFY — a broken one reads "damaged" and offers no
 * such button (scripts/release-shell.sh records why). The Terminal line is
 * the fallback for that case only.
 *
 * Every platform on the roster is listed, in the hero and in the steps; the
 * page never guesses the visitor's machine (ADR-661 §7.6). `FIRST_OPEN` is
 * keyed by `DesktopPlatform`, so a platform added to the roster does not
 * compile until its steps are written.
 *
 * What the app adds (§ "why") claims only what docs/architecture/desktop-app.md
 * says the host does: its own window, sign-in through the member's browser,
 * and an interface that is the live website. The browser hands (ADR-662) are
 * NOT offered here — the extension has no published listing yet.
 */

const MAC_UNQUARANTINE = "xattr -dr com.apple.quarantine /Applications/yarnnn.app";

/** Each platform's first-open step keys, and its requirement line. */
const FIRST_OPEN: Record<DesktopPlatform, { requires: string; steps: readonly string[] }> = {
  mac: { requires: "macRequires", steps: ["macStep1", "macStep2", "macStep3"] },
  windows: { requires: "windowsRequires", steps: ["windowsStep1", "windowsStep2"] },
};

const WHY = [
  { id: "window", Icon: AppWindow },
  { id: "signIn", Icon: LogIn },
  { id: "current", Icon: RefreshCw },
] as const;

export function DownloadPageBody({ locale }: { locale: Locale }) {
  const t = useTranslations("marketing.download");
  const chrome = useMarketingChrome();

  return (
    <div className="relative min-h-screen flex flex-col bg-[#0f1419] text-white overflow-x-hidden">
      <HtmlLang locale={locale} />
      <GrainOverlay variant="dark" />
      <ShaderBackgroundDark />

      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted locale={locale} nav={chrome.nav} path="/download" />

        <main className="flex-1">
          {/* ─── Hero: the buttons, and the app in its window ─────────────── */}
          <section className="max-w-6xl mx-auto px-6 pt-20 pb-24 md:pt-28 md:pb-32">
            <div className="flex flex-col lg:flex-row lg:items-center gap-14 lg:gap-16">
              <div className="flex-1 max-w-xl">
                <p className="text-xs font-mono text-white/40 uppercase tracking-wider mb-5">
                  {t("eyebrow")}
                </p>
                <h1 className="text-4xl md:text-6xl font-medium mb-6 tracking-tight leading-[1.05]">
                  {t("heading")}
                </h1>
                <p className="text-lg text-white/55 font-light leading-relaxed mb-8">{t("intro")}</p>

                {/* BEFORE the buttons, by ruling (ADR-661 §7q): an unsigned
                    build is linked only where the stranger is told first. */}
                <div className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 mb-8 text-sm text-white/65 leading-relaxed">
                  {t("beta")}{" "}
                  <a
                    href="#first-open"
                    className="inline-flex items-center gap-1 text-white underline underline-offset-4 decoration-white/30 hover:decoration-white transition-colors"
                  >
                    {t("howToOpen")}
                    <ArrowDown className="h-3.5 w-3.5" aria-hidden="true" />
                  </a>
                </div>

                <div className="flex flex-col sm:flex-row gap-3">
                  {DESKTOP_PLATFORMS.map((platform) => (
                    <DownloadButton key={platform} platform={platform} size="lg" />
                  ))}
                </div>
              </div>

              <div className="flex-1 w-full max-w-xl lg:max-w-none">
                <div className="relative">
                  <div
                    aria-hidden="true"
                    className="absolute -inset-8 rounded-[2rem] bg-[#de5a2b]/10 blur-3xl"
                  />
                  <ChatReplica className="relative shadow-2xl shadow-black/40" />
                </div>
              </div>
            </div>
          </section>

          {/* ─── What the app adds ────────────────────────────────────────── */}
          <section className="border-t border-white/[0.06] px-6 py-20 md:py-24">
            <ScrollReveal className="max-w-6xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-10">{t("whyTitle")}</h2>
              <div className="grid gap-4 md:grid-cols-3">
                {WHY.map(({ id, Icon }) => (
                  <SpotlightCard key={id} variant="dark" className="p-7">
                    <Icon className="h-5 w-5 text-[#de5a2b] mb-5" aria-hidden="true" />
                    <h3 className="text-lg font-medium mb-2">{t(`why.${id}.title`)}</h3>
                    <p className="text-sm text-white/50 leading-relaxed">{t(`why.${id}.body`)}</p>
                  </SpotlightCard>
                ))}
              </div>
            </ScrollReveal>
          </section>

          {/* ─── The first open: the beta's honest step, per platform ─────── */}
          <section id="first-open" className="scroll-mt-8 border-t border-white/[0.06] px-6 py-20 md:py-24">
            <ScrollReveal className="max-w-6xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-10">{t("firstOpen")}</h2>

              {/* `grid-cols-1` + `min-w-0`: an implicit track sizes to its
                  content's min-width, and the Terminal line does not wrap —
                  both cards measured 603px wide in a 390px viewport. */}
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {DESKTOP_PLATFORMS.map((platform) => (
                  <div
                    key={platform}
                    className="min-w-0 flex flex-col rounded-2xl border border-white/[0.08] bg-white/[0.03] p-7"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-4 mb-2">
                      <h3 className="text-xl font-medium">
                        {t("platformTitle", { platform: DESKTOP_PLATFORM_NAMES[platform] })}
                      </h3>
                      <DownloadButton platform={platform} size="sm" />
                    </div>
                    <p className="text-sm text-white/40 mb-7">{t(FIRST_OPEN[platform].requires)}</p>

                    <ol className="space-y-4">
                      {FIRST_OPEN[platform].steps.map((step, i) => (
                        <li key={step} className="flex gap-4">
                          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-white/15 text-xs text-white/60">
                            {i + 1}
                          </span>
                          <span className="text-white/65 leading-relaxed">{t(step)}</span>
                        </li>
                      ))}
                    </ol>

                    {platform === "mac" && (
                      <div className="mt-7 border-t border-white/[0.06] pt-6">
                        <p className="text-sm text-white/40 mb-3">{t("macDamaged")}</p>
                        <CommandLine command={MAC_UNQUARANTINE} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </ScrollReveal>
          </section>

          {/* ─── Or the browser ───────────────────────────────────────────── */}
          <section className="border-t border-white/[0.06] px-6 py-20 md:py-24">
            <ScrollReveal className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">{t("browserTitle")}</h2>
              <p className="text-white/50 leading-relaxed mb-8 max-w-xl mx-auto">{t("browserBody")}</p>
              <Link
                href={CTA.signup}
                className="inline-block px-7 py-3 rounded-full border border-white/20 text-white hover:bg-white/10 transition-colors"
              >
                {t("browserCta")}
              </Link>
            </ScrollReveal>
          </section>
        </main>

        <LandingFooter inverted locale={locale} words={chrome.footer} />
      </div>
    </div>
  );
}

function DownloadButton({ platform, size }: { platform: DesktopPlatform; size: "lg" | "sm" }) {
  const t = useTranslations("marketing.download");
  const href = downloadPath(platform);
  if (!href) {
    return <span className="text-sm text-white/40 self-center">{t("notYet")}</span>;
  }
  const shape =
    size === "lg" ? "px-6 py-3.5 text-base gap-2.5" : "px-4 py-2 text-sm gap-2";
  return (
    <a
      href={href}
      className={`inline-flex items-center justify-center rounded-full bg-white text-black font-medium hover:bg-white/90 transition-colors ${shape}`}
    >
      <Download className={size === "lg" ? "h-4 w-4" : "h-3.5 w-3.5"} aria-hidden="true" />
      {t("downloadFor", { platform: DESKTOP_PLATFORM_NAMES[platform] })}
    </a>
  );
}

function CommandLine({ command }: { command: string }) {
  const t = useTranslations("marketing.download");
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard?.writeText(command).then(
      () => {
        setCopied(true);
        setTimeout(() => setCopied(false), 1600);
      },
      () => {},
    );
  };
  return (
    <div className="flex items-stretch rounded-lg border border-white/10 bg-black/30">
      <code className="flex-1 min-w-0 px-3 py-2.5 text-sm font-mono text-white/80 overflow-x-auto whitespace-nowrap">
        {command}
      </code>
      <button
        type="button"
        onClick={copy}
        className="flex shrink-0 items-center gap-1.5 border-l border-white/10 px-3 text-xs text-white/55 hover:text-white transition-colors"
      >
        {copied ? <Check className="h-3.5 w-3.5" aria-hidden="true" /> : <Copy className="h-3.5 w-3.5" aria-hidden="true" />}
        {copied ? t("copied") : t("copy")}
      </button>
    </div>
  );
}
