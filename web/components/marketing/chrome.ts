"use client";

import { useTranslations } from "next-intl";
import type { LandingHeaderNav } from "@/components/landing/LandingHeader";
import type { LandingFooterWords } from "@/components/landing/LandingFooter";

/**
 * The words the marketing header and footer need, read once per page.
 *
 * `LandingHeader` and `LandingFooter` take their words as PROPS and call no
 * translation hook, because they also render on the marketing pages that stay
 * English by ruling — those render outside `MarketingIntlScope`, and
 * `useTranslations` throws outside a provider (ADR-660 D8's hazard). This hook
 * is the one place a TRANSLATED page fills those props, so the mapping from
 * catalog key to prop lives once rather than per page.
 *
 * Must be called from inside `MarketingIntlScope`.
 */
export function useMarketingChrome(): {
  nav: LandingHeaderNav;
  footer: LandingFooterWords;
} {
  const n = useTranslations("marketing.nav");
  const f = useTranslations("marketing.footer");
  return {
    nav: {
      howItWorks: n("howItWorks"),
      pricing: n("pricing"),
      faq: n("faq"),
      download: n("download"),
      blog: n("blog"),
      about: n("about"),
      signIn: n("signIn"),
      menu: n("menu"),
    },
    footer: {
      tagline: f("tagline"),
      desktopApp: f("desktopApp"),
      product: f("product"),
      resources: f("resources"),
      company: f("company"),
      legal: f("legal"),
      howItWorks: n("howItWorks"),
      pricing: n("pricing"),
      engines: f("engines"),
      faq: n("faq"),
      download: f("download"),
      blog: n("blog"),
      developers: f("developers"),
      docs: f("docs"),
      support: f("support"),
      feedback: f("feedback"),
      about: n("about"),
      invest: f("invest"),
      yourData: f("yourData"),
      privacy: f("privacy"),
      terms: f("terms"),
      rights: f("rights"),
    },
  };}
