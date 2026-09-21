"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { FEEDBACK_FORM } from "@/lib/cta";
import { localePath } from "@/lib/marketing/locale";
import { type Locale } from "@/i18n/config";
import { useMarketingChrome } from "./chrome";
import { HtmlLang } from "./HtmlLang";

/**
 * /support — the one support surface, in either language.
 *
 * The address is admin@yarnnn.com because it is the only one the product
 * actually publishes today — the privacy policy and the landing footer both
 * carry it. A dedicated support@ alias would read better and was declined:
 * publishing an address whose routing is unverified on a REQUIRED FIELD of
 * two external listings is worse than a plainer one that demonstrably
 * reaches someone.
 *
 * The feedback door is FEEDBACK_FORM (lib/cta.ts) — the same Tally form the
 * footer and the in-app account menu open, so a visitor's report and a
 * member's land in the same place. One form, three doors.
 *
 * `/contact` and `/help` are pure server redirects here (ADR-308); they are
 * NOT duplicated per locale, because a redirect carries no copy and the
 * target already resolves to the reader's language via the toggle.
 */

const SUPPORT_EMAIL = "admin@yarnnn.com";

export function SupportPageBody({ locale }: { locale: Locale }) {
  const t = useTranslations("marketing.support");
  const chrome = useMarketingChrome();

  return (
    <div className="relative min-h-screen flex flex-col bg-[#0f1419] text-white overflow-x-hidden">
      <HtmlLang locale={locale} />
      <GrainOverlay variant="dark" />
      <ShaderBackgroundDark />

      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted locale={locale} nav={chrome.nav} path="/support" />

        <main className="flex-1">
          <section className="max-w-3xl mx-auto px-6 py-24 md:py-32">
            <h1 className="text-4xl md:text-5xl font-medium mb-4 tracking-tight leading-[1.1]">
              {t("heading")}
            </h1>
            <p className="text-white/50 mb-16 max-w-xl">{t("intro")}</p>

            <div className="space-y-16">
              <div>
                <h2 className="text-xs text-white/30 uppercase tracking-widest mb-8">
                  {t("reachTitle")}
                </h2>

                <div className="border-b border-white/5 pb-8">
                  <h3 className="text-lg font-medium mb-3">{t("emailTitle")}</h3>
                  <p className="text-white/50 leading-relaxed mb-4">
                    {t("emailPre")}{" "}
                    <a
                      href={`mailto:${SUPPORT_EMAIL}`}
                      className="text-white underline underline-offset-4 hover:text-white/80 transition-colors"
                    >
                      {SUPPORT_EMAIL}
                    </a>{" "}
                    {t("emailPost")}
                  </p>
                  <p className="text-white/50 leading-relaxed">{t("emailTips")}</p>
                </div>

                <div className="border-b border-white/5 py-8">
                  <h3 className="text-lg font-medium mb-3">{t("reportTitle")}</h3>
                  <p className="text-white/50 leading-relaxed">
                    {t("reportPre")}{" "}
                    <a
                      href={FEEDBACK_FORM.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-white underline underline-offset-4 hover:text-white/80 transition-colors"
                    >
                      {t("reportLink")}
                    </a>{" "}
                    {t("reportPost")}
                  </p>
                </div>

                <div className="py-8">
                  <h3 className="text-lg font-medium mb-3">{t("dataTitle")}</h3>
                  <p className="text-white/50 leading-relaxed">
                    {t("dataPre")}{" "}
                    <Link
                      href="/privacy"
                      className="text-white underline underline-offset-4 hover:text-white/80 transition-colors"
                    >
                      {t("dataLink")}
                    </Link>
                    .
                  </p>
                </div>
              </div>

              <div>
                <h2 className="text-xs text-white/30 uppercase tracking-widest mb-8">
                  {t("selfTitle")}
                </h2>

                <div className="space-y-8">
                  <div className="border-b border-white/5 pb-8">
                    <h3 className="text-lg font-medium mb-3">
                      <Link
                        href={localePath("/faq", locale)}
                        className="underline underline-offset-4 decoration-white/25 hover:decoration-white/60 transition-colors"
                      >
                        {t("faqLink")}
                      </Link>
                    </h3>
                    <p className="text-white/50 leading-relaxed">{t("faqBody")}</p>
                  </div>

                  <div className="border-b border-white/5 pb-8">
                    <h3 className="text-lg font-medium mb-3">
                      <Link
                        href={localePath("/how-it-works", locale)}
                        className="underline underline-offset-4 decoration-white/25 hover:decoration-white/60 transition-colors"
                      >
                        {t("howLink")}
                      </Link>
                    </h3>
                    <p className="text-white/50 leading-relaxed">{t("howBody")}</p>
                  </div>

                  <div className="pb-8">
                    <h3 className="text-lg font-medium mb-3">
                      <a
                        href="https://yarnnn.gitbook.io/docs"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="underline underline-offset-4 decoration-white/25 hover:decoration-white/60 transition-colors"
                      >
                        {t("docsLink")}
                      </a>
                    </h3>
                    <p className="text-white/50 leading-relaxed">
                      {t("docsPre")}{" "}
                      <Link
                        href={localePath("/developers", locale)}
                        className="text-white underline underline-offset-4 hover:text-white/80 transition-colors"
                      >
                        {t("docsDevLink")}
                      </Link>
                      .
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-24 text-center">
              <h2 className="text-2xl font-medium mb-4">{t("stuckTitle")}</h2>
              <p className="text-white/50 mb-8">{t("stuckBody")}</p>
              <a
                href={`mailto:${SUPPORT_EMAIL}`}
                className="inline-block px-8 py-3 bg-white text-black font-medium rounded-full hover:bg-white/90 transition-colors"
              >
                {t("stuckCta")}
              </a>
            </div>
          </section>
        </main>

        <LandingFooter inverted locale={locale} words={chrome.footer} />
      </div>
    </div>
  );
}
