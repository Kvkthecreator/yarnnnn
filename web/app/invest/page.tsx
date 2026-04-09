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
    "yarnnn is raising $500K pre-seed to build persistent agent systems for recurring knowledge work — shared context, recurring tasks, and compounding outputs instead of session-only tools.",
  path: "/invest",
  keywords: [
    "yarnnn invest",
    "pre-seed",
    "ai startup fundraise",
    "persistent agents",
    "autonomous ai investment",
    "ai workforce platform",
    "ai agent startup",
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
              Persistent systems,
              <br />
              <span className="text-white/50">not session tools.</span>
            </h1>
            <div className="max-w-2xl space-y-6 text-white/50">
              <p>
                The AI agent industry is bifurcating. One side builds tools &mdash;
                session-scoped, user-present, interactive. The other side builds
                systems that keep context, run recurring work, and compound.
                Tools reset when you close the tab. Systems do not.
              </p>
              <p>
                yarnnn builds the second category: persistent agents, shared workspace
                context, TP orchestration, and recurring task execution for knowledge work
                that repeats every week whether the user is present or not.
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
                    <p className="text-2xl font-medium mb-1">$9&ndash;19</p>
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
                    <p className="text-2xl font-medium mb-1">150+</p>
                    <p className="text-white/40 text-xs">Architecture Decision Records</p>
                  </div>
                </SpotlightCard>

                {/* Use of funds + Stage */}
                <SpotlightCard variant="dark" className="md:col-span-3" spotlightSize={350}>
                  <div className="p-6">
                    <h3 className="text-base font-medium mb-3">Use of funds</h3>
                    <div className="text-white/50 text-sm space-y-2">
                      <p>Senior Tech Lead &mdash; accelerate execution pipeline and agent architecture</p>
                      <p>GTM Lead &mdash; drive adoption in solo consultant wedge</p>
                      <p>Candidates identified from enterprise consulting network</p>
                    </div>
                  </div>
                </SpotlightCard>
                <SpotlightCard variant="dark" className="md:col-span-3" spotlightSize={350}>
                  <div className="p-6">
                    <h3 className="text-base font-medium mb-3">Stage</h3>
                    <div className="text-white/50 text-sm space-y-2">
                      <p>Delaware C-Corp, pre-revenue</p>
                      <p>MVP live with autonomous agent execution shipping</p>
                      <p>Solo founder &mdash; full stack built and shipped independently</p>
                    </div>
                  </div>
                </SpotlightCard>
              </BentoGrid>
            </div>
          </section>

          {/* The Bifurcation */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">The bifurcation</h2>
              <p className="text-white/50 mb-16 max-w-2xl">
                OpenClaw hit 307K GitHub stars in 60 days. Claude shipped Cowork. The
                demand for AI that does real work is proven. But every one of these products
                is a tool &mdash; session-scoped, user-present, stateless between runs.
                Recurring knowledge work requires something structurally different.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-12">
                <SpotlightCard variant="dark" spotlightColor="rgba(255,255,255,0.03)" spotlightSize={400}>
                  <div className="p-6 md:p-8">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-4">Category 1</div>
                    <h3 className="text-xl font-medium mb-4">AI Tools</h3>
                    <div className="space-y-3 text-white/50 text-sm">
                      <p>Session-scoped. User must be present. Context resets or degrades between uses. Quality of session 51 is roughly equal to session 1.</p>
                      <div className="pt-3 border-t border-white/[0.06] space-y-1.5 text-white/30 text-xs">
                        <p>OpenClaw &mdash; local agent, dies when terminal closes</p>
                        <p>Claude Code &mdash; session-scoped, CLAUDE.md is static</p>
                        <p>Cowork &mdash; desktop agent, no autonomous execution</p>
                        <p>ChatGPT &mdash; memory is facts, not domain expertise</p>
                      </div>
                    </div>
                  </div>
                </SpotlightCard>

                <SpotlightCard variant="dark" spotlightColor="rgba(99,102,241,0.08)" spotlightSize={400}>
                  <div className="p-6 md:p-8">
                    <div className="text-xs text-indigo-400/60 uppercase tracking-wider mb-4">Category 2</div>
                    <h3 className="text-xl font-medium mb-4">Persistent agent systems</h3>
                    <div className="space-y-3 text-white/50 text-sm">
                      <p>Persistent. Autonomous. Run recurring tasks without the user. Feedback becomes learned behavior. Quality compounds with tenure. Day 90 output is irreplaceable.</p>
                      <div className="pt-3 border-t border-white/[0.06] space-y-1.5 text-xs">
                        <p className="text-white/60 font-medium">yarnnn &mdash; workspace, agents, TP, tasks</p>
                        <p className="text-white/30">Cloud-native by structural necessity, not preference</p>
                      </div>
                    </div>
                  </div>
                </SpotlightCard>
              </div>

              <div className="max-w-2xl text-white/40 text-sm">
                <p>
                  The local-first wave proves the demand. Every OpenClaw user who automates
                  recurring tasks locally will eventually want those tasks to run without them,
                  accumulate learning, and deliver on schedule. That graduation path &mdash; from
                  tools to systems &mdash; is yarnnn&apos;s market.
                </p>
              </div>
            </div>
          </section>

          {/* Why Cloud Is Structural */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">Why persistent systems require cloud</h2>
              <p className="text-white/50 mb-12 max-w-2xl">
                This isn&apos;t a preference. It&apos;s the structural requirement of
                the problem space.
              </p>

              <BentoGrid>
                {([
                  { title: "Runs without you", desc: "Agents execute at 6 AM Monday. Your laptop is in your bag. Cloud compute is the only option for autonomous scheduled work.", col: "md:col-span-3" },
                  { title: "Accumulates over months", desc: "90 days of Slack patterns, feedback history, and domain knowledge requires persistent storage that outlives any session.", col: "md:col-span-3" },
                  { title: "Cross-platform sync", desc: "Server-side OAuth and always-on polling. Can't sync Slack and Notion while you sleep.", col: "md:col-span-2" },
                  { title: "Multi-agent coordination", desc: "Research Agent feeds Content Agent on shared state. Local filesystems are single-tenant.", col: "md:col-span-2" },
                  { title: "Feedback compounds", desc: "Every edit teaches every future run. Persistent memory across weeks, not sessions.", col: "md:col-span-2" },
                ] as const).map((item) => (
                  <SpotlightCard key={item.title} variant="dark" className={item.col} spotlightSize={300}>
                    <div className="p-5">
                      <h3 className="text-sm font-medium mb-2">{item.title}</h3>
                      <p className="text-white/40 text-xs leading-relaxed">{item.desc}</p>
                    </div>
                  </SpotlightCard>
                ))}
              </BentoGrid>
            </div>
          </section>

          {/* What's Live */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">What&apos;s live</h2>

              <BentoGrid>
                {/* Workforce — hero card */}
                <SpotlightCard variant="dark" className="md:col-span-4" spotlightColor="rgba(99,102,241,0.05)">
                  <div className="p-6 md:p-8">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Core product</div>
                    <h3 className="text-xl font-medium mb-3">Scaffolded workforce + TP</h3>
                    <p className="text-white/50 text-sm leading-relaxed mb-6">
                      Every user gets the current 10-agent scaffold at sign-up: five domain
                      stewards, Reporting, three platform bots, and Thinking Partner.
                      The point is not the list itself. The point is that the system
                      starts with persistent workers and a meta-cognitive controller.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {["Competitive Intelligence", "Market Research", "Business Development", "Operations", "Marketing", "Reporting", "Slack Bot", "Notion Bot", "GitHub Bot", "Thinking Partner"].map((a) => (
                        <span key={a} className="text-[10px] px-2.5 py-1 rounded-full bg-white/[0.06] text-white/50 font-medium">{a}</span>
                      ))}
                    </div>
                  </div>
                </SpotlightCard>

                {/* Execution */}
                <SpotlightCard variant="dark" className="md:col-span-2" spotlightColor="rgba(14,165,233,0.05)">
                  <div className="p-6 h-full">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Execution</div>
                    <h3 className="text-base font-medium mb-2">Autonomous task pipeline</h3>
                    <p className="text-white/50 text-xs leading-relaxed">
                      Three-layer architecture: mechanical scheduling (zero LLM), multi-agent execution
                      (Sonnet), conversational orchestration. Purpose-built, not an API wrapper.
                    </p>
                  </div>
                </SpotlightCard>

                {/* Integrations */}
                <SpotlightCard variant="dark" className="md:col-span-2" spotlightColor="rgba(225,30,90,0.05)">
                  <div className="p-6 h-full">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Platforms</div>
                    <h3 className="text-base font-medium mb-2">Slack + Notion + GitHub</h3>
                    <p className="text-white/50 text-xs leading-relaxed">
                      Always-on sync. Cross-platform context accumulates with every cycle.
                      Bots activate when you connect a tool.
                    </p>
                  </div>
                </SpotlightCard>

                {/* Context domains */}
                <SpotlightCard variant="dark" className="md:col-span-2" spotlightColor="rgba(16,185,129,0.05)">
                  <div className="p-6 h-full">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Intelligence</div>
                    <h3 className="text-base font-medium mb-2">Shared context domains</h3>
                    <p className="text-white/50 text-xs leading-relaxed">
                      Six structured domains (competitors, market, relationships, projects, content,
                      signals) where agents deposit and refine intelligence across cycles.
                    </p>
                  </div>
                </SpotlightCard>

                {/* Moat */}
                <SpotlightCard variant="dark" className="md:col-span-2" spotlightColor="rgba(245,158,11,0.05)">
                  <div className="p-6 h-full flex flex-col justify-center">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Defensibility</div>
                    <h3 className="text-base font-medium mb-2">Compounding moat</h3>
                    <p className="text-white/50 text-xs leading-relaxed">
                      90 days of accumulated context, feedback, and domain knowledge can&apos;t be
                      replicated by downloading a new tool. Switching costs increase automatically.
                    </p>
                  </div>
                </SpotlightCard>
              </BentoGrid>
            </div>
          </section>

          {/* Investment Thesis */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">Investment thesis</h2>
              <div className="max-w-2xl space-y-6 text-white/50">
                <p>
                  The AI agent market is proving massive demand (OpenClaw: 307K stars in 60 days).
                  But every viral product in this wave is a tool &mdash; session-scoped, stateless,
                  resets between uses. The structural requirements of recurring knowledge work
                  (persistence, scheduling, cross-platform sync, feedback loops) can only be met
                  by cloud-native architecture. This creates a natural bifurcation: tools for
                  interactive work, systems for autonomous work.
                </p>
                <p>
                  yarnnn is building the system layer: persistent agents, a shared workspace,
                  TP orchestration, and recurring tasks that accumulate domain expertise and
                  deliver compounding work products. The subscription model is straightforward:
                  pay for a system that keeps running while you sleep.
                </p>
                <p className="text-white font-medium">
                  The local-first wave isn&apos;t competition &mdash; it&apos;s demand validation.
                  Every user who automates recurring work with a local tool will eventually need it
                  to run without them. That graduation from tools to systems is yarnnn&apos;s market.
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
                  { value: "$4.35B", label: "TAM \u2014 AI productivity tools, 31% CAGR" },
                  { value: "$1.14B", label: "SAM \u2014 5M solo consultants at $228/yr" },
                  { value: "$11.4M", label: "Entry SOM \u2014 50K users in 3 years" },
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
                Expansion: founders, executives, teams, then every knowledge worker who wants
                to supervise recurring work instead of rebuilding it in chat tools.
              </p>
            </div>
          </section>

          {/* Founder */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">Founder</h2>

              <div className="max-w-2xl space-y-6 text-white/50">
                <p className="text-white font-medium text-lg">
                  Kevin Kim &mdash; Solo Founder &amp; CEO
                </p>
                <p>
                  Korean-born, US-based. A decade of work spanning enterprise systems, cross-border
                  operations, and context architecture &mdash; from deploying CRM for Japan Tobacco in
                  post-military Myanmar to building GTM systems for cross-border sales teams.
                </p>
                <p>
                  Shipped the entire MVP solo: full-stack application (Next.js + FastAPI + Supabase),
                  platform integrations, autonomous agent execution pipeline documented across
                  150+ Architecture Decision Records, and a working context accumulation engine &mdash;
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
                If you&apos;re investing at pre-seed in AI infrastructure, autonomous agents,
                or the future of knowledge work &mdash; I&apos;d love to share the deck and walk
                through the architecture.
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
