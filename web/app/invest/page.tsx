import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata: Metadata = getMarketingMetadata({
  title: "Invest — Pre-Seed",
  description:
    "yarnnn is raising $500K pre-seed to build the application layer for work context: persistent agents, accumulated context, and compounding work products for recurring knowledge work.",
  path: "/invest",
  keywords: [
    "yarnnn invest",
    "pre-seed",
    "ai startup fundraise",
    "autonomous ai investment",
    "work context ai",
  ],
});

export default function InvestPage() {
  const investSchema = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: "Invest in yarnnn",
    description: metadata.description,
    url: `${BRAND.url}/invest`,
    isPartOf: {
      "@type": "WebSite",
      name: BRAND.name,
      url: BRAND.url,
    },
  };

  return (
    <div className="relative min-h-screen flex flex-col bg-[#0f1419] text-white overflow-x-hidden">
      <GrainOverlay variant="dark" />
      <ShaderBackgroundDark />

      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted />

        <main className="flex-1">
          {/* Hero */}
          <section className="max-w-4xl mx-auto px-6 py-24 md:py-32">
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-10 tracking-tight leading-[1.1]">
              The application layer
              <br />
              <span className="text-white/50">for work context.</span>
            </h1>
            <div className="max-w-2xl space-y-6 text-white/50">
              <p>
                Every platform cycle produces an application layer the platform provider
                doesn&apos;t own. LLMs are no different. yarnnn is building that layer for work —
                an autonomous AI platform that connects to your tools, accumulates context over time,
                creates persistent agents around recurring jobs, and turns supervision into the default
                operating model.
              </p>
              <p className="text-white font-medium">
                We&apos;re raising $500K pre-seed at $5M post-money.
              </p>
            </div>
          </section>

          {/* The Raise */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">The raise</h2>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-16">
                <div>
                  <p className="text-3xl md:text-4xl font-medium">$500K</p>
                  <p className="text-white/40 text-sm mt-1">Pre-seed round</p>
                </div>
                <div>
                  <p className="text-3xl md:text-4xl font-medium">$5M</p>
                  <p className="text-white/40 text-sm mt-1">Post-money valuation</p>
                </div>
                <div>
                  <p className="text-3xl md:text-4xl font-medium">$9–19</p>
                  <p className="text-white/40 text-sm mt-1">Per month pricing</p>
                </div>
                <div>
                  <p className="text-3xl md:text-4xl font-medium">$1.14B</p>
                  <p className="text-white/40 text-sm mt-1">SAM</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-3">Use of funds</h3>
                  <div className="text-white/50 text-sm space-y-2">
                    <p>Senior Tech Lead — accelerate context engine and agent architecture</p>
                    <p>GTM Lead — drive adoption in solo consultant wedge</p>
                    <p>Candidates identified from enterprise consulting network</p>
                  </div>
                </div>
                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-3">Stage</h3>
                  <div className="text-white/50 text-sm space-y-2">
                    <p>Delaware C-Corp, pre-revenue</p>
                    <p>MVP live with all four integrations shipping</p>
                    <p>Solo founder — full stack built and shipped independently</p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* What We Built */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">What&apos;s live</h2>

              <div className="space-y-16">
                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Four integrations</h3>
                  </div>
                  <div className="text-white/50">
                    <p>
                      Slack, Gmail, Notion, and Google Calendar — all connected and syncing.
                      Cross-platform context accumulates automatically with every sync cycle.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Two operating modes</h3>
                  </div>
                  <div className="text-white/50">
                    <p>
                      Orchestrator for context-aware conversations. Autonomous agents for scheduled
                      work — weekly recaps, project summaries, meeting prep, and richer
                      work products — generated without repeated prompting.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Supervision model</h3>
                  </div>
                  <div className="text-white/50">
                    <p>
                      The product shifts the user from operator to supervisor. Instead of rebuilding
                      context and regenerating the same draft every cycle, users review, redirect,
                      and refine a running system that compounds with tenure.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">90+ ADRs</h3>
                  </div>
                  <div className="text-white/50">
                    <p>
                      Architecture Decision Records documenting every design choice — from the
                      unified content layer to workspace outputs and output skills. This is a
                      purpose-built work system, not an API wrapper.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Compounding moat</h3>
                  </div>
                  <div className="text-white/50">
                    <p>
                      After 90 days of accumulated context, the system knows your preferences,
                      your clients, and your style. Switching to a competitor means starting
                      from zero. The moat deepens automatically with every cycle.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Thesis */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">Investment thesis</h2>
              <div className="max-w-2xl space-y-6 text-white/50">
                <p>
                  Context is what makes autonomy meaningful — and cross-platform context
                  accumulation is the application layer that no existing company is positioned to own.
                  But the user-facing expression of that layer is not storage alone. It is persistent
                  agents that turn accumulated context into recurring work products.
                </p>
                <p>
                  Google didn&apos;t become Salesforce. Facebook didn&apos;t become Shopify. AWS
                  didn&apos;t become Datadog. General-purpose platforms always look invincible — until
                  the application layer emerges. LLM providers built code first (the easy case).
                  Work context is the hard case: unstructured, personal, cross-platform, and
                  domain-specific. The winner will be the company that turns that substrate into
                  compounding supervised autonomy.
                </p>
                <p className="text-white font-medium">
                  The comparable companies that validated this market — Notion ($11B), Glean ($7.2B),
                  Granola ($250M), Mem.ai ($110M) — all proved demand for AI-powered context.
                  yarnnn adds the persistent agent and work-product layer that none of them have.
                </p>
              </div>
            </div>
          </section>

          {/* Market */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">Market</h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
                <div className="border border-white/10 rounded-2xl p-6">
                  <p className="text-2xl font-medium mb-2">$4.35B</p>
                  <p className="text-white/40 text-sm">TAM — AI productivity tools, 31% CAGR</p>
                </div>
                <div className="border border-white/10 rounded-2xl p-6">
                  <p className="text-2xl font-medium mb-2">$1.14B</p>
                  <p className="text-white/40 text-sm">SAM — 5M solo consultants at $228/yr</p>
                </div>
                <div className="border border-white/10 rounded-2xl p-6">
                  <p className="text-2xl font-medium mb-2">$11.4M</p>
                  <p className="text-white/40 text-sm">Entry SOM — 50K users in 3 years</p>
                </div>
              </div>

              <p className="text-white/50 max-w-2xl">
                Entry wedge: solo consultants managing multiple clients with recurring agents
                across 3+ tools. Clearest pain, shortest sales cycle, highest willingness to pay.
                Expansion path: founders, executives, teams, then all knowledge workers.
              </p>
            </div>
          </section>

          {/* Founder */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">Founder</h2>

              <div className="max-w-2xl space-y-6 text-white/50">
                <p className="text-white font-medium text-lg">
                  Kevin Kim — Solo Founder & CEO
                </p>
                <p>
                  Korean-born, US-based. A decade of work spanning enterprise systems, cross-border
                  operations, and context architecture — from deploying CRM for Japan Tobacco in
                  post-military Myanmar to building GTM systems for cross-border sales teams.
                </p>
                <p>
                  Shipped the entire MVP solo: full-stack application (Next.js + FastAPI + Supabase),
                  four platform integrations, unified agent architecture documented across 90+
                  Architecture Decision Records, and a working context accumulation engine — all
                  before raising a dollar.
                </p>
              </div>
            </div>
          </section>

          {/* CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Let&apos;s talk.
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                If you&apos;re investing at pre-seed in AI infrastructure, work tools, or
                autonomous agents — I&apos;d love to share the deck and walk through the architecture.
              </p>
              <a
                href="mailto:kvkthecreator@gmail.com"
                className="inline-block px-8 py-4 bg-white text-black text-lg font-medium rounded-full hover:bg-white/90 transition-colors"
              >
                kvkthecreator@gmail.com
              </a>
            </div>
          </section>
        </main>

        <LandingFooter inverted />
      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(investSchema) }}
      />
    </div>
  );
}
