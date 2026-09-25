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
import { localePath } from "@/lib/marketing/locale";
import { type Locale } from "@/i18n/config";
import { useMarketingChrome } from "./chrome";
import { HtmlLang } from "./HtmlLang";

/**
 * Developer resources, in either language.
 *
 * ── What is NOT translated, and why ───────────────────────────────────────
 * Identifiers are the contract, not copy: the verb names (`whoami`, `open`,
 * `request_upload`), the scope strings (`files:read`), the HTTP lines
 * (`GET /llms.txt`) and every URL stay exactly as a client must type them.
 * Only the SENTENCES describing them are worded per locale. A translated
 * identifier would be a bug report waiting to happen.
 *
 * The verb roster mirrors `_INTEROP_VERBS` (api/mcp_server/server.py), which
 * is the source of truth; `test_gitbook_docs_current.py` asserts the two are
 * the same set. ADR-543 retired remember/recall/trace with no aliases, and
 * this page once kept advertising them — the same drift ADR-635 D9 removed
 * from the discovery card. A new verb is a row there plus its @mcp.tool, then
 * a row here AND a description in both catalogs (the gate holds the pair).
 */

const MCP_URL = "https://mcp.yarnnn.com";

const RESOURCES = [
  { key: "mcp", href: MCP_URL, external: true, detail: "Transport: streamable-http · Auth: OAuth 2.1" },
  { key: "openapi", href: "/openapi.json", external: false, detail: "GET /openapi.json" },
  { key: "discovery", href: "/.well-known/mcp.json", external: false, detail: "GET /.well-known/mcp.json" },
  { key: "oauth", href: `${MCP_URL}/.well-known/oauth-authorization-server`, external: true, detail: "GET /.well-known/oauth-authorization-server" },
  { key: "llms", href: "/llms.txt", external: false, detail: "GET /llms.txt" },
  { key: "docs", href: "https://yarnnn.gitbook.io/docs", external: true, detail: "GitBook" },
] as const;

const VERBS = [
  { name: "whoami", kind: "read" },
  { name: "open", kind: "read" },
  { name: "list", kind: "read" },
  { name: "search", kind: "read" },
  { name: "history", kind: "read" },
  { name: "runs", kind: "read" },
  { name: "save", kind: "write" },
  { name: "edit", kind: "write" },
  { name: "delete", kind: "write" },
  { name: "move", kind: "write" },
  { name: "request_upload", kind: "write" },
  { name: "share", kind: "write" },
] as const;

const SCOPES = ["read", "write", "share"] as const;

export function DevelopersPageBody({ locale }: { locale: Locale }) {
  const t = useTranslations("marketing.developers");
  const chrome = useMarketingChrome();

  // TechArticle reference so this page is identifiable as yarnnn's developer
  // resource hub programmatically.
  const structuredData = {
    "@context": "https://schema.org",
    "@type": "TechArticle",
    headline: t("meta.title"),
    description: t("meta.description"),
    url: `${BRAND.url}${localePath("/developers", locale)}`,
    author: { "@type": "Organization", name: BRAND.name, url: BRAND.url },
    publisher: { "@id": `${BRAND.url}/#organization` },
    about: { "@id": `${BRAND.url}/#software` },
  };

  return (
    <div className="relative min-h-screen flex flex-col bg-[#0f1419] text-white overflow-x-hidden">
      <HtmlLang locale={locale} />
      <GrainOverlay variant="dark" />
      <ShaderBackgroundDark />

      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted locale={locale} nav={chrome.nav} path="/developers" />

        <main className="flex-1">
          {/* Hero */}
          <section className="max-w-4xl mx-auto px-6 py-24 md:py-32">
            <div className="text-xs uppercase tracking-widest text-white/40 mb-6">
              {t("eyebrow")}
            </div>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-10 tracking-tight leading-[1.1]">
              {t("headingA")} <span className="text-[#de5a2b]">{t("headingHighlight")}</span>
            </h1>
            <div className="max-w-2xl space-y-6 text-white/50">
              <p>
                {t("hero1a")}{" "}
                <code className="text-white/70 font-mono text-sm">
                  {MCP_URL.replace("https://", "")}
                </code>{" "}
                {t("hero1b")}
              </p>
              <p>
                {t("hero2a")}{" "}
                <span className="text-white/70">{t("hero2quote")}</span> {t("hero2b")}
              </p>
              <p>{t("hero3")}</p>
            </div>
          </section>

          {/* Resources */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">{t("resourcesTitle")}</h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {RESOURCES.map((r) => {
                  const inner = (
                    <div className="p-6 h-full">
                      <div className="flex items-baseline justify-between gap-3 mb-2">
                        <h3 className="text-lg font-medium text-white">{t(`res.${r.key}.name`)}</h3>
                        <span className="text-white/30 text-xs shrink-0">
                          {r.external ? "↗︎" : "→"}
                        </span>
                      </div>
                      <p className="text-white/50 text-sm leading-relaxed mb-3">
                        {t(`res.${r.key}.what`)}
                      </p>
                      {/* The HTTP line is the contract — never translated. */}
                      <code className="text-white/40 text-xs font-mono break-all">{r.detail}</code>
                    </div>
                  );
                  return (
                    <SpotlightCard key={r.key} variant="dark" spotlightSize={300}>
                      {r.external ? (
                        <a href={r.href} target="_blank" rel="noopener noreferrer" className="block h-full">
                          {inner}
                        </a>
                      ) : (
                        <Link href={r.href} className="block h-full">
                          {inner}
                        </Link>
                      )}
                    </SpotlightCard>
                  );
                })}
              </div>
            </ScrollReveal>
          </section>

          {/* The verb roster */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">{t("verbsTitle")}</h2>
              <p className="text-white/50 mb-16 max-w-xl">
                {t("verbsIntroA")}{" "}
                <Link
                  href="/openapi.json"
                  className="text-white underline underline-offset-4 hover:text-[#de5a2b]"
                >
                  {t("verbsIntroLink")}
                </Link>
                .
              </p>
              <div className="space-y-12">
                {VERBS.map((v) => (
                  <div key={v.name} className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                    <div>
                      {/* The verb name is what a client types — never translated. */}
                      <h3 className="text-lg font-medium text-white mb-1">{v.name}</h3>
                      <span className="text-white/40 text-xs font-mono">
                        {v.kind === "read" ? t("kindRead") : t("kindWrite")}
                      </span>
                    </div>
                    <div className="text-white/50">
                      <p>{t(`verb.${v.name}`)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollReveal>
          </section>

          {/* Scopes */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">{t("scopesTitle")}</h2>
              <p className="text-white/50 mb-16 max-w-xl">
                {t("scopesIntroA")}{" "}
                <code className="text-white/70 font-mono text-sm">files:read</code>{" "}
                {t("scopesIntroB")}
              </p>

              <div className="space-y-8">
                {SCOPES.map((sc) => (
                  <div key={sc} className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                    {/* The scope string is the contract — never translated. */}
                    <code className="text-white font-mono text-sm">files:{sc}</code>
                    <p className="text-white/50">{t(`scope.${sc}`)}</p>
                  </div>
                ))}
              </div>

              <p className="text-white/40 text-sm mt-12 max-w-xl">{t("scopesNote")}</p>
            </ScrollReveal>
          </section>

          {/* Connect CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">{t("ctaTitle")}</h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">{t("ctaBody")}</p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <a
                  href={MCP_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-block px-8 py-4 bg-white text-black text-lg font-medium rounded-full hover:bg-white/90 transition-colors"
                >
                  {t("ctaPrimary")}
                </a>
                <Link
                  href="/openapi.json"
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
        dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
      />
    </div>
  );
}
