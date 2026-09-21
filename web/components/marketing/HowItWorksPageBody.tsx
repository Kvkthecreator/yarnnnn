"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { SpotlightCard } from "@/components/landing/SpotlightCard";
import { ScrollReveal } from "@/components/landing/ScrollReveal";
import { StepFlow } from "@/components/landing/StepFlow";
import { FilesReplica } from "@/components/landing/product/FilesReplica";
import { AgentsReplica } from "@/components/landing/product/AgentsReplica";
import { StudioReplica } from "@/components/landing/product/StudioReplica";
import { ConnectReplica } from "@/components/landing/product/ConnectReplica";
import { CTA } from "@/lib/cta";
import { localePath } from "@/lib/marketing/locale";
import { type Locale } from "@/i18n/config";
import { useMarketingChrome } from "./chrome";
import { HtmlLang } from "./HtmlLang";

/**
 * How it works — product mechanics (re-cut 2026-07-31), in either language.
 *
 * This page sells the system itself: a real file system, agents that come
 * with the apps, documents you build and own — and portability as the
 * consequence. The "why it's different" thesis argument lives on /about.
 *
 * ── Structure in code, words in the catalog (ADR-660 D3) ──────────────────
 * The step ORDER, their numbers and which replica each one shows are
 * structure: both languages must walk the same five steps in the same order,
 * or the page argues differently depending on who is reading. Only the prose
 * is worded per locale.
 *
 * 2026-09-18 note kept: step 02 once promised a cast ADR-599 deleted, and
 * step 04 named Gemini as attachable when it has no MCP connector. The copy
 * below is the corrected version; do not restore the older phrasing from a
 * screenshot or a cached page.
 */

const STEPS = [
  { key: "files", Replica: FilesReplica },
  { key: "agents", Replica: AgentsReplica },
  { key: "build", Replica: StudioReplica },
  { key: "connect", Replica: ConnectReplica },
  { key: "travels", Replica: null },
] as const;

const GUARANTEES = ["lost", "signed", "yours"] as const;

export function HowItWorksPageBody({ locale }: { locale: Locale }) {
  const t = useTranslations("marketing.how");
  const c = useTranslations("marketing.cta");
  const chrome = useMarketingChrome();

  const steps = STEPS.map((s, i) => ({
    number: String(i + 1).padStart(2, "0"),
    title: t(`step.${s.key}.title`),
    body: t(`step.${s.key}.body`),
    extra: s.Replica ? (
      <div className="mt-6 max-w-xl">
        <s.Replica className="shadow-xl" />
      </div>
    ) : undefined,
  }));

  // The schema carries the worded steps, so a Korean result in search
  // describes the Korean page rather than the English one.
  const howToSchema = {
    "@context": "https://schema.org",
    "@type": "HowTo",
    name: t("meta.title"),
    step: steps.map((s) => ({
      "@type": "HowToStep",
      name: s.title,
      text: s.body,
    })),
  };

  return (
    <div className="relative min-h-screen flex flex-col bg-[#0f1419] text-white overflow-x-hidden">
      <HtmlLang locale={locale} />
      <GrainOverlay variant="dark" />
      <ShaderBackgroundDark />

      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted locale={locale} nav={chrome.nav} path="/how-it-works" />

        <main className="flex-1">
          {/* Hero */}
          <section className="max-w-4xl mx-auto px-6 py-24 md:py-32">
            <p className="text-white/40 text-sm uppercase tracking-widest mb-4">
              {t("eyebrow")}
            </p>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-10 tracking-tight leading-[1.1]">
              {t("headingA")}
              <br />
              <span className="text-white/50">{t("headingB")}</span>
            </h1>
            <p className="max-w-2xl text-white/50 text-lg">{t("intro")}</p>
          </section>

          {/* The five-step system walk */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <StepFlow steps={steps} />
          </section>

          {/* The three guarantees + CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-5xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-12 text-center">
                {t("guaranteesTitle")}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
                {GUARANTEES.map((g) => (
                  <SpotlightCard key={g} variant="dark" spotlightSize={300}>
                    <div className="p-6 h-full">
                      <div className="text-xs font-mono text-white/30 uppercase tracking-wider mb-4">
                        {t(`guarantee.${g}.tag`)}
                      </div>
                      <h3 className="text-base font-medium mb-3">{t(`guarantee.${g}.title`)}</h3>
                      <p className="text-white/40 text-sm leading-relaxed">
                        {t(`guarantee.${g}.desc`)}
                      </p>
                    </div>
                  </SpotlightCard>
                ))}
              </div>

              <div className="text-center">
                <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                  <Link
                    href={CTA.signup}
                    className="inline-block px-8 py-4 bg-white text-black text-lg font-medium rounded-full hover:bg-white/90 transition-colors"
                  >
                    {c("signup")}
                  </Link>
                  <Link
                    href={localePath(CTA.pricing, locale)}
                    className="inline-block px-8 py-4 border border-white/20 text-white text-lg font-medium rounded-full hover:bg-white/10 transition-colors"
                  >
                    {t("seePricing")}
                  </Link>
                </div>
                <p className="mt-8 text-sm text-white/35">
                  {t("detailPre")}{" "}
                  <a
                    href="https://yarnnn.gitbook.io/docs/getting-started/how-to-use-yarnnn"
                    className="text-white/60 underline underline-offset-4 hover:text-white transition-colors"
                  >
                    {t("detailLink")}
                  </a>
                  .
                </p>
              </div>
            </ScrollReveal>
          </section>
        </main>

        <LandingFooter inverted locale={locale} words={chrome.footer} />
      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(howToSchema) }}
      />
    </div>
  );
}
