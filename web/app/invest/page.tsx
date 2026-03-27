import type { Metadata } from "next";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { SpotlightCard, BentoGrid } from "@/components/landing/SpotlightCard";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata: Metadata = getMarketingMetadata({
  title: "Invest — Pre-Seed",
  description:
    "yarnnn is raising $500K pre-seed to build the application layer for work context: a pre-built AI workforce with persistent agents, accumulated context, and compounding work products.",
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
                an autonomous AI platform that gives every user a pre-built workforce of
                specialist agents, connects to their tools, accumulates context over time,
                and turns supervision into the default operating model.
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

              <BentoGrid className="mb-16">
                {/* Headline number — large */}
                <SpotlightCard variant="dark" className="md:col-span-3" spotlightColor="rgba(255,255,255,0.05)">
                  <div className="p-6 md:p-8">
                    <p className="text-4xl md:text-5xl font-medium mb-2">$500K</p>
                    <p className="text-white/40 text-sm">Pre-seed round</p>
                  </div>
                </SpotlightCard>
                <SpotlightCard variant="dark" className="md:col-span-3" spotlightColor="rgba(255,255,255,0.05)">
                  <div className="p-6 md:p-8">
                    <p className="text-4xl md:text-5xl font-medium mb-2">$5M</p>
                    <p className="text-white/40 text-sm">Post-money valuation</p>
                  </div>
                </SpotlightCard>

                {/* Smaller stats */}
                <SpotlightCard variant="dark" className="md:col-span-2">
                  <div className="p-5">
                    <p className="text-2xl font-medium mb-1">$9–19</p>
                    <p className="text-white/40 text-xs">Per month pricing</p>
                  </div>
                </SpotlightCard>
                <SpotlightCard variant="dark" className="md:col-span-2">
                  <div className="p-5">
                    <p className="text-2xl font-medium mb-1">$1.14B</p>
                    <p className="text-white/40 text-xs">SAM</p>
                  </div>
                </SpotlightCard>
                <SpotlightCard variant="dark" className="md:col-span-2">
                  <div className="p-5">
                    <p className="text-2xl font-medium mb-1">145+</p>
                    <p className="text-white/40 text-xs">Architecture Decision Records</p>
                  </div>
                </SpotlightCard>

                {/* Use of funds + Stage */}
                <SpotlightCard variant="dark" className="md:col-span-3" spotlightSize={350}>
                  <div className="p-6">
                    <h3 className="text-base font-medium mb-3">Use of funds</h3>
                    <div className="text-white/50 text-sm space-y-2">
                      <p>Senior Tech Lead — accelerate context engine and agent architecture</p>
                      <p>GTM Lead — drive adoption in solo consultant wedge</p>
                      <p>Candidates identified from enterprise consulting network</p>
                    </div>
                  </div>
                </SpotlightCard>
                <SpotlightCard variant="dark" className="md:col-span-3" spotlightSize={350}>
                  <div className="p-6">
                    <h3 className="text-base font-medium mb-3">Stage</h3>
                    <div className="text-white/50 text-sm space-y-2">
                      <p>Delaware C-Corp, pre-revenue</p>
                      <p>MVP live with platform integrations shipping</p>
                      <p>Solo founder — full stack built and shipped independently</p>
                    </div>
                  </div>
                </SpotlightCard>
              </BentoGrid>
            </div>
          </section>

          {/* What We Built */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">What&apos;s live</h2>

              <BentoGrid>
                {/* Workforce — hero card */}
                <SpotlightCard variant="dark" className="md:col-span-4" spotlightColor="rgba(99,102,241,0.05)">
                  <div className="p-6 md:p-8">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Core product</div>
                    <h3 className="text-xl font-medium mb-3">Pre-built AI workforce</h3>
                    <p className="text-white/50 text-sm leading-relaxed mb-6">
                      Every user gets a 6-agent roster at sign-up: Research, Content, Marketing,
                      and CRM specialist agents plus Slack and Notion bots. No setup, no configuration.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {["Research", "Content", "Marketing", "CRM", "Slack Bot", "Notion Bot"].map((a) => (
                        <span key={a} className="text-[10px] px-2.5 py-1 rounded-full bg-white/[0.06] text-white/50 font-medium">{a}</span>
                      ))}
                    </div>
                  </div>
                </SpotlightCard>

                {/* Agent + Task model */}
                <SpotlightCard variant="dark" className="md:col-span-2" spotlightColor="rgba(14,165,233,0.05)">
                  <div className="p-6 h-full">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Architecture</div>
                    <h3 className="text-base font-medium mb-2">Agent + Task model</h3>
                    <p className="text-white/50 text-xs leading-relaxed">
                      Agents are WHO (identity, capabilities, knowledge). Tasks are WHAT
                      (objective, cadence, delivery). Three modes: recurring, goal, reactive.
                    </p>
                  </div>
                </SpotlightCard>

                {/* Integrations */}
                <SpotlightCard variant="dark" className="md:col-span-2" spotlightColor="rgba(225,30,90,0.05)">
                  <div className="p-6 h-full">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Platforms</div>
                    <h3 className="text-base font-medium mb-2">Slack + Notion</h3>
                    <p className="text-white/50 text-xs leading-relaxed">
                      Connected and syncing. Cross-platform context accumulates with every cycle.
                      Bots activate when you connect a tool.
                    </p>
                  </div>
                </SpotlightCard>

                {/* Execution architecture */}
                <SpotlightCard variant="dark" className="md:col-span-2" spotlightColor="rgba(16,185,129,0.05)">
                  <div className="p-6 h-full">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Infrastructure</div>
                    <h3 className="text-base font-medium mb-2">Three-layer execution</h3>
                    <p className="text-white/50 text-xs leading-relaxed">
                      Mechanical scheduling (zero LLM), task execution pipeline (Sonnet),
                      and conversational orchestration. Purpose-built, not an API wrapper.
                    </p>
                  </div>
                </SpotlightCard>

                {/* Moat — wide card */}
                <SpotlightCard variant="dark" className="md:col-span-2" spotlightColor="rgba(245,158,11,0.05)">
                  <div className="p-6 h-full flex flex-col justify-center">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Defensibility</div>
                    <h3 className="text-base font-medium mb-2">Compounding moat</h3>
                    <p className="text-white/50 text-xs leading-relaxed">
                      90 days of context, feedback, and domain knowledge can&apos;t be replicated.
                      Switching costs increase automatically with every cycle.
                    </p>
                  </div>
                </SpotlightCard>
              </BentoGrid>
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
                  yarnnn adds the persistent agent workforce and task execution layer that none of them have.
                </p>
              </div>
            </div>
          </section>

          {/* Market */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">Market</h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-12">
                {([
                  { value: "$4.35B", label: "TAM — AI productivity tools, 31% CAGR" },
                  { value: "$1.14B", label: "SAM — 5M solo consultants at $228/yr" },
                  { value: "$11.4M", label: "Entry SOM — 50K users in 3 years" },
                ] as const).map((stat) => (
                  <SpotlightCard key={stat.value} variant="dark" spotlightSize={280}>
                    <div className="p-6">
                      <p className="text-2xl font-medium mb-2">{stat.value}</p>
                      <p className="text-white/40 text-sm">{stat.label}</p>
                    </div>
                  </SpotlightCard>
                ))}
              </div>

              <p className="text-white/50 max-w-2xl">
                Entry wedge: solo consultants managing multiple clients with recurring tasks
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
                  platform integrations, autonomous agent architecture documented across
                  145+ Architecture Decision Records, and a working context accumulation engine —
                  all before raising a dollar.
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
