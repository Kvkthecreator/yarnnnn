"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { SpotlightCard } from "@/components/landing/SpotlightCard";
import { ScrollReveal } from "@/components/landing/ScrollReveal";
import { BRAND } from "@/lib/metadata";
import { CTA } from "@/lib/cta";
import { localePath } from "@/lib/marketing/locale";
import { type Locale } from "@/i18n/config";
import { useMarketingChrome } from "./chrome";
import { HtmlLang } from "./HtmlLang";

/**
 * About — the neutrality thesis, in either language.
 *
 * The argument order is structure (ADR-660 D3): belief → what we are not →
 * who it is for → the recognition quote → CTA. Both languages walk it the
 * same way; only the words differ.
 *
 * The recognition quote reuses `marketing.home.recognitionQuote` rather than
 * restating it. It is CANON-LOCK Slot 4 and appears on the landing page too —
 * a second copy would let the two pages drift into two different sentences.
 */

const BELIEFS = ["real", "signed", "neutral", "yours", "room", "receipts"] as const;
const NOT_LIST = ["chat", "memory", "bolted", "suite"] as const;
const WHO = ["daily", "shared", "own"] as const;

export function AboutPageBody({ locale }: { locale: Locale }) {
  const t = useTranslations("marketing.about");
  const home = useTranslations("marketing.home");
  const c = useTranslations("marketing.cta");
  const chrome = useMarketingChrome();

  const aboutSchema = {
    "@context": "https://schema.org",
    "@type": "AboutPage",
    name: t("meta.title"),
    description: t("meta.description"),
    url: `${BRAND.url}${localePath("/about", locale)}`,
    isPartOf: { "@type": "WebSite", name: BRAND.name, url: BRAND.url },
  };

  return (
    <div className="relative min-h-screen flex flex-col bg-[#0f1419] text-white overflow-x-hidden">
      <HtmlLang locale={locale} />
      <GrainOverlay variant="dark" />
      <ShaderBackgroundDark />

      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted locale={locale} nav={chrome.nav} path="/about" />

        <main className="flex-1">
          {/* Hero — the neutrality thesis, workspace-era */}
          <section className="max-w-4xl mx-auto px-6 py-24 md:py-32">
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-10 tracking-tight leading-[1.1]">
              {t("headingA")} <span className="text-[#de5a2b]">{t("headingHighlight")}</span>
              <br />
              <span className="text-white/50">{t("headingB")}</span>
            </h1>
            <div className="space-y-6 text-white/50 text-lg leading-relaxed max-w-2xl">
              <p>{t("heroA")}</p>
              <p>
                {t("heroB1")}{" "}
                <em className="not-italic text-white/70">{t("heroBAll")}</em> {t("heroB2")}
              </p>
              <p>{t("heroC")}</p>
              <p>{t("heroD")}</p>
            </div>
          </section>

          {/* What we believe */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">{t("believeTitle")}</h2>

              <div className="space-y-16">
                {BELIEFS.map((b) => (
                  <div key={b} className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                    <div>
                      <h3 className="text-lg font-medium text-white">{t(`belief.${b}.title`)}</h3>
                    </div>
                    <div className="text-white/50">
                      <p className="mb-4">{t(`belief.${b}.body`)}</p>
                      <p className="text-white/30 text-sm">{t(`belief.${b}.sub`)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollReveal>
          </section>

          {/* What yarnnn is not */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">{t("notTitle")}</h2>
              <p className="text-white/50 mb-12 max-w-xl">{t("notIntro")}</p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {NOT_LIST.map((item) => (
                  <SpotlightCard key={item} variant="dark" spotlightSize={300}>
                    <div className="p-6">
                      <h3 className="text-lg font-medium mb-2">{t(`not.${item}.title`)}</h3>
                      <p className="text-white/50 text-sm leading-relaxed">
                        {t(`not.${item}.desc`)}
                      </p>
                    </div>
                  </SpotlightCard>
                ))}
              </div>
            </ScrollReveal>
          </section>

          {/* Who it's for */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">{t("whoTitle")}</h2>
              <p className="text-white/50 mb-12 max-w-xl">{t("whoIntro")}</p>

              <div className="space-y-4">
                {WHO.map((item) => (
                  <SpotlightCard key={item} variant="dark" spotlightSize={400}>
                    <div className="p-6">
                      <h3 className="text-base font-medium mb-2">{t(`who.${item}.title`)}</h3>
                      <p className="text-white/50 text-sm leading-relaxed">
                        {t(`who.${item}.desc`)}
                      </p>
                    </div>
                  </SpotlightCard>
                ))}
              </div>

              {/* The recognition sentence (canon Slot 4) — shared with the landing page */}
              <blockquote className="mt-12 border-l-2 border-[#de5a2b]/50 pl-6">
                <p className="text-xl md:text-2xl font-light text-white/70 italic">
                  &ldquo;{home("recognitionQuote")}&rdquo;
                </p>
                <p className="mt-3 text-sm text-white/35">{t("whoClose")}</p>
              </blockquote>
            </ScrollReveal>
          </section>

          {/* CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">{t("ctaTitle")}</h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">{t("ctaBody")}</p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link
                  href={CTA.signup}
                  className="inline-block px-8 py-4 bg-white text-black text-lg font-medium rounded-full hover:bg-white/90 transition-colors"
                >
                  {c("signup")}
                </Link>
                <Link
                  href={localePath(CTA.howItWorks, locale)}
                  className="inline-block px-8 py-4 border border-white/20 text-white text-lg font-medium rounded-full hover:bg-white/10 transition-colors"
                >
                  {t("ctaSecondary")}
                </Link>
              </div>
            </ScrollReveal>
          </section>
        </main>

        <LandingFooter inverted locale={locale} words={chrome.footer} />
      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(aboutSchema) }}
      />
    </div>
  );
}
