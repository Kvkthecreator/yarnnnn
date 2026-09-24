"use client";

import { AddToChrome, EXTENSION_PUBLISHED } from "@/components/shared/AddToChrome";
import Link from "next/link";
import { useTranslations } from "next-intl";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackground } from "@/components/landing/ShaderBackground";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { IntegrationHub } from "@/components/landing/IntegrationHub";
import { TraceCard } from "@/components/landing/TraceCard";
import { CompoundsStepper } from "@/components/landing/CompoundsStepper";
import { AppShowcase } from "@/components/landing/AppShowcase";
import { AppStrip } from "@/components/landing/AppStrip";
import { ScrollReveal } from "@/components/landing/ScrollReveal";
import {
  getOrganizationSchema,
  getSoftwareApplicationSchema,
  getWebSiteSchema,
} from "@/lib/metadata";
import { CTA } from "@/lib/cta";
import { Wordmark } from "@/components/shared/Wordmark";
import { localePath } from "@/lib/marketing/locale";
import { type Locale } from "@/i18n/config";
import { useMarketingChrome } from "./chrome";
import { HtmlLang } from "./HtmlLang";

/**
 * Landing page — CANON-LOCK-2026-07-30 (working canon).
 *
 * The hero sequence is the lock's §1 assembled arc, verbatim:
 *   hook → headline pair → subhead → CTA + connector chips → (below the fold)
 *   product chapter → attribution proof → recognition pull-quote → pricing.
 *
 * Discipline notes:
 * - Model names live in the connector chips under the CTA, never in the subhead.
 * - App names (Chat/Studio/Files/Agents) appear ONLY in the product chapter
 *   (AppShowcase) — the roster rule keeps them out of the hero.
 * - "Nothing to set up" is guarded by falsifier 5 (CANON-LOCK §8.5); if it
 *   fires, that line comes out of the subhead here and in the canon together.
 *
 * ── The copy lives in the catalog (`marketing.home`) ──────────────────────
 * The arc above is a RATIFIED sequence, so the Korean is a faithful
 * translation of each slot, never a rewrite: a slot that says something
 * different in one language would silently fork the canon. Both languages
 * render THIS component, so the structure cannot drift between them — only
 * the words differ.
 *
 * Renders inside `MarketingIntlScope`, which is what makes `useTranslations`
 * legal here without a cookie read (and therefore without going dynamic).
 */
export function LandingPageBody({ locale }: { locale: Locale }) {
  const t = useTranslations("marketing.home");
  const c = useTranslations("marketing.cta");
  const chrome = useMarketingChrome();
  // TraceCard and CompoundsStepper also render inside blog posts, outside every
  // scope, so they take WORDS rather than calling a hook (see their headers).
  // A translated page fills them here.
  const tr = useTranslations("marketing.trace");
  const cs = useTranslations("marketing.compounds");
  const traceWords = {
    eyebrow: tr("eyebrow"), title: tr("title"), body: tr("body"), footer: tr("footer"),
    you: tr("you"), agent: tr("agent"),
    whenToday: tr("whenToday"), when3d: tr("when3d"), whenWeek: tr("whenWeek"),
    change1: tr("change1"), change2: tr("change2"), change3: tr("change3"),
  };
  const compoundsWords = {
    day1Label: cs("day1Label"), day30Label: cs("day30Label"), day90Label: cs("day90Label"),
    day1: cs("day1"), day30: cs("day30"), day90: cs("day90"),
  };

  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      getOrganizationSchema(),
      getSoftwareApplicationSchema(),
      getWebSiteSchema(),
    ],
  };

  const CONNECTOR_CHIPS = ["ChatGPT", "Claude", "Gemini"];
  // The lead-door label is CANON-LOCK Channel 1 ("connect your AI first"). It
  // lives in the catalog rather than beside `CTA` so both languages have one
  // home; `lib/cta.ts` keeps owning the HREFS, which are language-neutral.
  const signupLabel = c("signup");

  return (
    <main className="relative min-h-screen w-full overflow-x-hidden bg-[#faf8f5] text-[#1a1a1a]">
      <HtmlLang locale={locale} />
      <GrainOverlay />
      <ShaderBackground />

      <div className="relative z-10">
        <LandingHeader locale={locale} nav={chrome.nav} path="/" />

        {/* ─── Section 1 — Hero (the canon arc: hook → headline → subhead → CTA) ── */}
        <section className="flex flex-col items-center justify-center px-6 py-32 md:py-40 min-h-[80vh]">
          <div className="max-w-6xl mx-auto w-full">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-12 lg:gap-20">
              <div className="text-center lg:text-left flex-1 max-w-2xl mx-auto lg:mx-0">
                {/* The mark, BARE (ADR-629 D4). The ONE `bare` call site. */}
                <div className="mb-8">
                  <Wordmark bare className="text-4xl md:text-5xl text-[#1a1a1a]" />
                </div>

                {/* The hook (Slot 3) */}
                <p className="text-sm md:text-base font-mono text-[#1a1a1a]/40 uppercase tracking-wider mb-5">
                  {t("hook")}
                </p>

                {/* The headline pair (Slot 2, ratified-stable) */}
                <h1 className="text-3xl sm:text-4xl md:text-5xl font-medium tracking-tight mb-6 leading-[1.15]">
                  <span className="text-[#1a1a1a]">{t("headlineA")}</span>
                  <br />
                  <span className="text-[#de5a2b]">{t("headlineB")}</span>
                </h1>

                {/* The subhead (Slot 2, working canon — signed clause non-optional) */}
                <p className="text-lg md:text-xl text-[#1a1a1a]/50 mb-10 max-w-xl mx-auto lg:mx-0 font-light">
                  {t("subhead")}
                </p>

                {/* CTA — the lead door (GROWTH-LOOP Channel 1) + connector chips */}
                <div className="flex flex-col items-center lg:items-start gap-4 mb-4">
                  {/* Stacked again at `lg` only: the hub sits beside this column
                      there, which leaves it ~396px — both labels wrapped onto two
                      lines at 1024px. From `xl` the row fits. */}
                  <div className="flex flex-col sm:flex-row lg:flex-col xl:flex-row items-center lg:items-start gap-4">
                    <Link
                      href={CTA.signup}
                      className="inline-block whitespace-nowrap px-8 py-4 bg-[#1a1a1a] text-white text-lg font-medium rounded-full hover:bg-[#1a1a1a]/90 transition-all"
                    >
                      {signupLabel}
                    </Link>
                    <Link
                      href={localePath(CTA.howItWorks, locale)}
                      className="inline-block whitespace-nowrap px-8 py-4 glass-light text-[#1a1a1a] text-lg font-medium hover:bg-white/80 transition-all"
                    >
                      {c("seeHowItWorks")}
                    </Link>
                  </div>
                  <div className="flex items-center gap-2 pl-1">
                    <span className="text-xs text-[#1a1a1a]/30 font-mono">{c("worksWith")}</span>
                    {CONNECTOR_CHIPS.map((chip) => (
                      <span
                        key={chip}
                        className="rounded-full border border-[#1a1a1a]/[0.1] bg-white/70 px-3 py-1 text-xs font-medium text-[#1a1a1a]/60"
                      >
                        {chip}
                      </span>
                    ))}
                    <span className="text-xs text-[#1a1a1a]/30 font-mono">· {c("more")}</span>
                  </div>
                </div>
              </div>

              <div className="flex-shrink-0 pb-16">
                <IntegrationHub />
              </div>
            </div>
          </div>
        </section>

        {/* ─── Section 2 — The problem (Beat 1: the copy-paste seam) ─────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <ScrollReveal className="max-w-3xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-8 text-[#1a1a1a] leading-tight">
              {t("problemTitle")}
            </h2>
            <div className="space-y-6 text-[#1a1a1a]/60 leading-relaxed text-lg font-light">
              <p>{t("problemA")}</p>
              <p>{t("problemB")}</p>
            </div>

            {/* The recognition sentence (Slot 4) — the conversion point */}
            <blockquote className="mt-10 border-l-2 border-[#de5a2b]/40 pl-6">
              <p className="text-xl md:text-2xl font-light text-[#1a1a1a]/70 italic">
                &ldquo;{t("recognitionQuote")}&rdquo;
              </p>
              <p className="mt-3 text-sm text-[#1a1a1a]/35">{t("recognitionAnswer")}</p>
            </blockquote>
          </ScrollReveal>
        </section>

        {/* ─── Section 2.5 — The roster strip (what's in the box) ───────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-16 md:py-20">
          <ScrollReveal className="max-w-5xl mx-auto">
            <AppStrip />
          </ScrollReveal>
        </section>

        {/* ─── Section 3 — The product chapter (feature-forward) ─────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <ScrollReveal className="text-center mb-20">
              <div className="text-xs font-mono text-[#1a1a1a]/30 uppercase tracking-wider mb-4">
                {t("productEyebrow")}
              </div>
              <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
                {t("productTitleA")}
                <br className="hidden md:block" /> {t("productTitleB")}
              </h2>
              <p className="text-[#1a1a1a]/45 max-w-2xl mx-auto font-light">{t("productBody")}</p>
            </ScrollReveal>

            <AppShowcase />
          </div>
        </section>

        {/* ─── Section 4 — The proof (the attribution walk) ──────────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <ScrollReveal className="max-w-5xl mx-auto">
            <div className="flex flex-col lg:flex-row gap-12 lg:items-center">
              <div className="flex-1 max-w-xl">
                <div className="text-xs font-mono text-[#1a1a1a]/30 uppercase tracking-wider mb-4">
                  {t("proofEyebrow")}
                </div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a] leading-tight">
                  {t("proofTitle")}
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed font-light mb-4">{t("proofA")}</p>
                <p className="text-[#1a1a1a]/50 leading-relaxed font-light">{t("proofB")}</p>
              </div>
              <div className="flex-1 w-full max-w-lg">
                <TraceCard words={traceWords} />
              </div>
            </div>
          </ScrollReveal>
        </section>

        {/* ─── Section 5 — The insight (Beat 4) ──────────────────────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <ScrollReveal className="max-w-3xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-8 text-[#1a1a1a] leading-tight">
              {t("insightTitle")}
            </h2>
            <p className="text-[#1a1a1a]/60 leading-relaxed text-lg font-light">
              {t("insightBody")}
            </p>

            <div className="mt-12">
              <CompoundsStepper words={compoundsWords} />
            </div>
          </ScrollReveal>
        </section>

        {/* ─── Section 5.5 — Where the work goes (ADR-561) ───────────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <ScrollReveal className="max-w-3xl mx-auto">
            <div className="text-xs font-mono text-[#1a1a1a]/30 uppercase tracking-wider mb-4">
              {t("whereEyebrow")}
            </div>
            <h2 className="text-2xl md:text-3xl font-medium mb-8 text-[#1a1a1a] leading-tight">
              {t("whereTitle")}
            </h2>
            <div className="space-y-6 text-[#1a1a1a]/60 leading-relaxed text-lg font-light">
              <p>{t("whereA")}</p>
              <p>{t("whereB")}</p>
            </div>
            <Link
              href="/privacy-architecture"
              className="inline-block mt-8 text-sm text-[#1a1a1a]/50 underline underline-offset-4 hover:text-[#1a1a1a] transition-colors"
            >
              {t("whereLink")}
            </Link>
          </ScrollReveal>
        </section>

        {/* ─── Section 6 — Pricing teaser + CTA (Beat 6) ─────────────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <ScrollReveal className="max-w-3xl mx-auto text-center">
            <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
              {t("pricingTitle")}
            </h2>
            <p className="text-[#1a1a1a]/50 mb-10 max-w-xl mx-auto leading-relaxed">
              {t("pricingBody")}
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href={CTA.signup}
                className="inline-block px-8 py-4 bg-[#1a1a1a] text-white text-lg font-medium rounded-full hover:bg-[#1a1a1a]/90 transition-all"
              >
                {signupLabel}
              </Link>
              <Link
                href={localePath(CTA.pricing, locale)}
                className="inline-block px-8 py-4 glass-light text-[#1a1a1a] text-lg font-medium hover:bg-white/80 transition-all"
              >
                {c("seePricing")}
              </Link>
            </div>
            {/* The desktop app — a quiet third door under the two CTAs, not a
                beat of its own: the canon arc ends on pricing. */}
            <Link
              href={localePath("/download", locale)}
              className="inline-flex items-center gap-2 mt-8 text-sm text-[#1a1a1a]/45 underline underline-offset-4 hover:text-[#1a1a1a] transition-colors"
            >
              {t("desktopLink")}
            </Link>
            {/* ADR-664 am.1 — the member's browser, a fourth quiet door beside
                the desktop app's, shown once the extension can be installed. */}
            {EXTENSION_PUBLISHED && (
              <p className="mt-3 text-sm text-[#1a1a1a]/45">
                {t("browserLine")}{" "}
                <AddToChrome className="underline underline-offset-4 hover:text-[#1a1a1a] transition-colors" />
              </p>
            )}
          </ScrollReveal>
        </section>

        <LandingFooter locale={locale} words={chrome.footer} />
      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
      />
    </main>
  );
}
