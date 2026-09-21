"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { SpotlightCard } from "@/components/landing/SpotlightCard";
import { ScrollReveal } from "@/components/landing/ScrollReveal";
import { Check, Wallet, ShieldCheck } from "lucide-react";
import { BRAND } from "@/lib/metadata";
import { CTA } from "@/lib/cta";
// ADR-445 §6 — prices live in ONE place (billing_tiers.py::TIER_CONFIG,
// mirrored by lib/subscription/usage.ts). Both languages interpolate from it
// as ICU arguments; neither re-types a number.
import { PRICE_COPY } from "@/lib/subscription/usage";
import { type Locale } from "@/i18n/config";
import { useMarketingChrome } from "./chrome";
import { HtmlLang } from "./HtmlLang";

/**
 * Pricing, in either language.
 *
 * ADR-490 (2026-07-28): two free seats + pay-as-you-go usage. There is NO base
 * fee and NO included allowance — the paid subscription IS the per-seat price.
 *   ① SEATS — the first TWO humans are free; each additional human is a priced
 *      seat. Unlimited workspaces; the free→paid boundary is the 3rd human. AI
 *      connections are never seats, never charged.
 *   ② USAGE — pure pay-as-you-go from one shared balance; hard-stop at zero;
 *      top-ups never expire.
 *
 * ── Prices are NOT translated ─────────────────────────────────────────────
 * Every figure arrives as an ICU argument from `PRICE_COPY`. A translated
 * catalog that spelled "$20" would be a second home for the number and would
 * silently go stale the day the price moves — the exact drift ADR-445 §6
 * exists to prevent. The words around the number are what differ per locale.
 *
 * The plan ladder's ORDER and which card is featured are structure and stay
 * in code, so the two languages cannot sell a different shape.
 */

const PLANS = [
  { key: "free", price: "$0", href: CTA.signup, featured: false },
  { key: "team", price: PRICE_COPY.seat, href: CTA.signup, featured: true },
] as const;

const HOW_KEYS = ["free", "seat", "payg", "topup"] as const;

export function PricingPageBody({ locale }: { locale: Locale }) {
  const t = useTranslations("marketing.pricing");
  const chrome = useMarketingChrome();

  const args = {
    seat: PRICE_COPY.seat,
    topUpMin: PRICE_COPY.topUpMin,
    signupGrant: PRICE_COPY.signupGrant,
  };

  const plans = PLANS.map((p) => ({
    ...p,
    name: t(`plan.${p.key}.name`),
    cadence: t(`plan.${p.key}.cadence`),
    blurb: t(`plan.${p.key}.blurb`),
    cta: t(`plan.${p.key}.cta`),
    points: (["p1", "p2", "p3", "p4"] as const).map((n) => t(`plan.${p.key}.${n}`, args)),
  }));

  const pricingSchema = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: BRAND.name,
    url: `${BRAND.url}/pricing`,
    applicationCategory: "BusinessApplication",
    offers: plans.map((p) => ({
      "@type": "Offer",
      name: p.name,
      description: p.blurb,
      price: p.price.replace("$", "") || "0",
      priceCurrency: "USD",
      url: `${BRAND.url}/pricing`,
    })),
  };

  return (
    <div className="relative min-h-screen flex flex-col bg-[#0f1419] text-white overflow-x-hidden">
      <HtmlLang locale={locale} />
      <GrainOverlay variant="dark" />
      <ShaderBackgroundDark />

      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted locale={locale} nav={chrome.nav} path="/pricing" />

        <main className="flex-1 flex flex-col items-center px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto w-full">
            <div className="text-center mb-12">
              <h1 className="text-4xl md:text-5xl font-medium mb-4 tracking-tight">
                {t("headingA")}
                <br />
                <span className="text-white/50">{t("headingB")}</span>
              </h1>
              <p className="text-white/50 max-w-2xl mx-auto leading-relaxed">{t("intro")}</p>
            </div>

            {/* Plan ladder — Free + one paid plan (ADR-490); two cards, centered */}
            <ScrollReveal className="mb-8">
              <div className="grid gap-4 sm:grid-cols-2 max-w-2xl mx-auto">
                {plans.map((plan, i) => (
                  <SpotlightCard
                    key={plan.key}
                    variant="dark"
                    spotlightSize={500}
                    className={plan.featured ? "ring-1 ring-emerald-400/30" : undefined}
                  >
                    <div className="p-6 flex flex-col h-full">
                      {plan.featured && (
                        <span className="self-start mb-3 text-[10px] font-mono uppercase tracking-wider text-emerald-400">
                          {t("popular")}
                        </span>
                      )}
                      <h2 className="text-xl font-medium mb-1">{plan.name}</h2>
                      <div className="flex items-baseline gap-1 mb-3">
                        <span className="text-3xl font-medium">{plan.price}</span>
                        <span className="text-white/40 text-sm">{plan.cadence}</span>
                      </div>
                      <p className="text-white/50 text-sm leading-relaxed mb-5">{plan.blurb}</p>
                      <ul className="space-y-2.5 mb-6 flex-1">
                        {plan.points.map((pt) => (
                          <li key={pt} className="flex items-start gap-2.5 text-sm text-white/70 leading-relaxed">
                            <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                            <span>{pt}</span>
                          </li>
                        ))}
                      </ul>
                      <Link
                        href={plan.href}
                        className={`block text-center px-6 py-3 font-medium rounded-full transition-colors ${
                          plan.featured || i === 0
                            ? "bg-white text-black hover:bg-white/90"
                            : "border border-white/20 text-white hover:bg-white/10"
                        }`}
                      >
                        {plan.cta}
                      </Link>
                    </div>
                  </SpotlightCard>
                ))}
              </div>
            </ScrollReveal>

            <p className="text-center text-white/40 text-sm mb-16">{t("noCard", args)}</p>

            {/* How usage works */}
            <ScrollReveal className="max-w-3xl mx-auto mb-8" delay={80}>
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-8">
                  <div className="text-[10px] font-mono uppercase tracking-wider text-white/40 mb-3">
                    {t("usageEyebrow")}
                  </div>
                  <div className="flex items-baseline gap-2 mb-5">
                    <h2 className="text-2xl font-medium">{t("usageTitle")}</h2>
                    <span className="text-white/40 text-sm">{t("usageAside")}</span>
                  </div>
                  <ul className="space-y-4">
                    {HOW_KEYS.map((k) => (
                      <li key={k} className="flex items-start gap-3 text-sm text-white/70 leading-relaxed">
                        <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span>{t(`how.${k}`, args)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </SpotlightCard>
            </ScrollReveal>

            {/* Two guardrails explainer — visibility + the floor (ADR-490) */}
            <ScrollReveal className="max-w-3xl mx-auto mb-16">
              <div className="text-center mb-6">
                <h3 className="text-xl font-medium mb-2">{t("guardTitle")}</h3>
                <p className="text-white/45 text-sm max-w-xl mx-auto">{t("guardBody")}</p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <SpotlightCard variant="dark" spotlightSize={500}>
                  <div className="p-6">
                    <div className="flex items-center gap-2 mb-2">
                      <Wallet className="w-4 h-4 text-emerald-400" />
                      <h4 className="text-base font-medium">{t("guardRanTitle")}</h4>
                    </div>
                    <p className="text-white/50 text-sm leading-relaxed">{t("guardRanBody")}</p>
                  </div>
                </SpotlightCard>
                <SpotlightCard variant="dark" spotlightSize={500}>
                  <div className="p-6">
                    <div className="flex items-center gap-2 mb-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                      <h4 className="text-base font-medium">{t("guardFloorTitle")}</h4>
                    </div>
                    <p className="text-white/50 text-sm leading-relaxed">{t("guardFloorBody")}</p>
                  </div>
                </SpotlightCard>
              </div>
            </ScrollReveal>

            {/* Three honest paragraphs */}
            <ScrollReveal className="max-w-3xl mx-auto mb-16 grid gap-6">
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6">
                  <h3 className="text-lg font-medium mb-3">{t("seatQ")}</h3>
                  <p className="text-white/50 text-sm leading-relaxed">{t("seatA", args)}</p>
                </div>
              </SpotlightCard>
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6">
                  <h3 className="text-lg font-medium mb-3">{t("usageQ")}</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    {t("usageA1")}{" "}
                    <Link
                      href="/engines"
                      className="text-white/70 underline underline-offset-4 decoration-white/30 hover:decoration-white/70"
                    >
                      {t("usageLink")}
                    </Link>
                    .
                  </p>
                </div>
              </SpotlightCard>
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6">
                  <h3 className="text-lg font-medium mb-3">{t("paygQ")}</h3>
                  <p className="text-white/50 text-sm leading-relaxed">{t("paygA")}</p>
                </div>
              </SpotlightCard>
            </ScrollReveal>

            {/* Mini-FAQ */}
            <ScrollReveal className="max-w-3xl mx-auto mb-16">
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6 space-y-4 text-white/50 text-sm leading-relaxed">
                  <p>
                    <strong className="text-white/70">{t("faqNeedLabel")}</strong> {t("faqNeed", args)}
                  </p>
                  <p>
                    <strong className="text-white/70">{t("faqBalanceLabel")}</strong>{" "}
                    {t("faqBalance", args)}
                  </p>
                  <p>
                    <strong className="text-white/70">{t("faqRunoutLabel")}</strong> {t("faqRunout")}
                  </p>
                  <p>
                    <strong className="text-white/70">{t("faqStopLabel")}</strong> {t("faqStop")}
                  </p>
                </div>
              </SpotlightCard>
            </ScrollReveal>

            <div className="text-center mt-4 mb-8">
              <p className="text-white/40 text-sm mb-4">{t("questions")}</p>
              <a
                href="mailto:admin@yarnnn.com"
                className="text-white hover:text-white/80 underline underline-offset-4 text-sm"
              >
                {t("contact")}
              </a>
            </div>
          </div>
        </main>

        <LandingFooter inverted locale={locale} words={chrome.footer} />
      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(pricingSchema) }}
      />
    </div>
  );
}
