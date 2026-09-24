"use client";

import { EXTENSION_PUBLISHED } from "@/components/shared/AddToChrome";
import Link from "next/link";
import { useTranslations } from "next-intl";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { BRAND } from "@/lib/metadata";
import { CTA } from "@/lib/cta";
// ADR-445 §6 — prices interpolate from the single source. A translated answer
// carries `{seat}` / `{topUpMin}` / `{signupGrant}` as ICU arguments, so the
// number is still typed in exactly one place and neither language can drift
// from it.
import { PRICE_COPY } from "@/lib/subscription/usage";
import { useMarketingChrome } from "./chrome";
import { HtmlLang } from "./HtmlLang";
import { type Locale } from "@/i18n/config";

/**
 * The FAQ page, in whichever language it is rendered.
 *
 * ── The roster is KEYS, ordered here ──────────────────────────────────────
 * Section order and membership are structure, not copy, so they live in code
 * (ADR-660 D3). Only the words come from the catalog, which means the two
 * languages cannot answer a different set of questions.
 *
 * `useTranslations` is legal here because both routes wrap this in
 * `MarketingIntlScope`, which takes its locale as an argument — no cookie
 * read, so the page still prerenders statically.
 */

const SECTIONS = [
  { cat: "difference", items: ["memory", "mine", "trace", "team"] },
  { cat: "work", items: ["inout", "models"] },
  { cat: "data", items: ["where", "cando"] },
  { cat: "pricing", items: ["cost", "cap", "runout"] },
  { cat: "start", items: ["howstart", "desktop", "firstmove"] },
] as const;

export function FaqPageBody({ locale }: { locale: Locale }) {
  const t = useTranslations("marketing.faq");
  const chrome = useMarketingChrome();

  const priceArgs = {
    seat: PRICE_COPY.seat,
    topUpMin: PRICE_COPY.topUpMin,
    signupGrant: PRICE_COPY.signupGrant,
  };

  // ADR-629 D4 — derived from the ONE stage declaration; gone when it is.
  const stageItem = BRAND.stage
    ? {
        question: t("q.stage.q", { brand: BRAND.name, stage: BRAND.stage }),
        answer: t("q.stage.a"),
      }
    : null;

  // ADR-664 am.1 — the member's browser, answered once a visitor can install
  // the extension (the one switch, `EXTENSION_PUBLISHED`); gone until then.
  const browserItem = EXTENSION_PUBLISHED
    ? { question: t("q.browser.q"), answer: t("q.browser.a") }
    : null;

  const sections = SECTIONS.map((s) => ({
    category: t(`cat.${s.cat}`),
    items: [
      ...s.items.map((k) => ({
        question: t(`q.${k}.q`),
        // Only the pricing answer takes arguments; passing them to every key is
        // harmless and keeps the map one shape.
        answer: t(`q.${k}.a`, priceArgs),
      })),
      ...(s.cat === "work" && browserItem ? [browserItem] : []),
      ...(s.cat === "start" && stageItem ? [stageItem] : []),
    ],
  }));

  // The schema carries the SAME worded strings the page renders, so a Korean
  // result in search shows the Korean answer rather than an English one.
  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: sections.flatMap((s) =>
      s.items.map((item) => ({
        "@type": "Question",
        name: item.question,
        acceptedAnswer: { "@type": "Answer", text: item.answer },
      })),
    ),
  };

  return (
    <div className="relative min-h-screen flex flex-col bg-[#0f1419] text-white overflow-x-hidden">
      <HtmlLang locale={locale} />
      <GrainOverlay variant="dark" />
      <ShaderBackgroundDark />

      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted locale={locale} nav={chrome.nav} path="/faq" />

        <main className="flex-1">
          <section className="max-w-3xl mx-auto px-6 py-24 md:py-32">
            <h1 className="text-4xl md:text-5xl font-medium mb-4 tracking-tight leading-[1.1]">
              {t("heading")}
            </h1>
            <p className="text-white/50 mb-16 max-w-xl">{t("intro")}</p>

            <div className="space-y-16">
              {sections.map((section) => (
                <div key={section.category}>
                  <h2 className="text-xs text-white/30 uppercase tracking-widest mb-8">
                    {section.category}
                  </h2>

                  <div className="space-y-8">
                    {section.items.map((item) => (
                      <div key={item.question} className="border-b border-white/5 pb-8 last:border-0">
                        <h3 className="text-lg font-medium mb-3">{item.question}</h3>
                        <p className="text-white/50 leading-relaxed">{item.answer}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-24 text-center">
              <h2 className="text-2xl font-medium mb-4">{t("stillTitle")}</h2>
              <p className="text-white/50 mb-8">{t("stillBody")}</p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  href={CTA.signup}
                  className="inline-block px-8 py-3 bg-white text-black font-medium rounded-full hover:bg-white/90 transition-colors"
                >
                  {t("startFree")}
                </Link>
                <a
                  href="mailto:admin@yarnnn.com"
                  className="inline-block px-8 py-3 border border-white/20 text-white font-medium rounded-full hover:bg-white/10 transition-colors"
                >
                  {t("contact")}
                </a>
              </div>
            </div>
          </section>
        </main>

        <LandingFooter inverted locale={locale} words={chrome.footer} />
      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }}
      />
    </div>
  );
}
