import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackground } from "@/components/landing/ShaderBackground";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { IntegrationHub } from "@/components/landing/IntegrationHub";
import { AnimatedTimeline } from "@/components/landing/AnimatedTimeline";
import { SpotlightCard, BentoGrid } from "@/components/landing/SpotlightCard";
import { MockPDF, MockEmail, MockBrief } from "@/components/landing/MockOutputs";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata: Metadata = getMarketingMetadata({
  title: "Autonomous Agents for Recurring Knowledge Work",
  description:
    "Persistent agents, Thinking Partner, and recurring tasks that run from shared workspace context. Supervise the system instead of rebuilding the same work every cycle.",
  path: "/",
  keywords: [
    "autonomous ai",
    "ai agent platform",
    "recurring knowledge work",
    "persistent agents",
    "slack ai summary",
    "notion ai summary",
    "autonomous workflow",
    "agent automation",
    "recurring ai work",
    "ai task automation",
  ],
});

export default function LandingPage() {
  const websiteSchema = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: BRAND.name,
    url: BRAND.url,
    description: BRAND.description,
    publisher: {
      "@type": "Organization",
      name: BRAND.name,
      url: BRAND.url,
    },
  };

  return (
    <main className="relative min-h-screen w-full overflow-x-hidden bg-[#faf8f5] text-[#1a1a1a]">
      <GrainOverlay />
      <ShaderBackground />

      <div className="relative z-10">
        <LandingHeader />

        {/* ─── Hero ─────────────────────────────────────────────────────── */}
        <section className="flex flex-col items-center justify-center px-6 py-32 md:py-40 min-h-[80vh]">
          <div className="max-w-6xl mx-auto w-full">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-12 lg:gap-20">
              <div className="text-center lg:text-left flex-1 max-w-2xl mx-auto lg:mx-0">
                <div className="font-brand text-4xl md:text-5xl mb-8 text-[#1a1a1a]">yarnnn</div>

                <h1 className="text-2xl sm:text-3xl md:text-4xl font-medium tracking-wide text-[#1a1a1a]/90 mb-6">
                  Recurring work,
                  <br />
                  <span className="text-[#1a1a1a]">without re-prompting.</span>
                </h1>

                <p className="text-lg md:text-xl text-[#1a1a1a]/50 mb-12 max-w-xl mx-auto lg:mx-0 font-light">
                  Connect your workspace, define recurring tasks, and let persistent
                  agents execute on schedule. Thinking Partner orchestrates. Your
                  feedback compounds instead of disappearing with the tab.
                </p>

                <Link
                  href="/auth/login"
                  className="inline-block px-8 py-4 glass-light text-[#1a1a1a] text-lg font-medium hover:bg-white/80 transition-all"
                >
                  Start free
                </Link>
              </div>

              <div className="flex-shrink-0 pb-16">
                <IntegrationHub />
              </div>
            </div>
          </div>
        </section>

        {/* ─── Problem → Solution (merged, tighter) ─────────────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-start">
              <div>
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">The problem</div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
                  Every Monday, same work.
                  <br />
                  <span className="text-[#1a1a1a]/50">Still doing it yourself.</span>
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed">
                  You spend hours pulling updates, summarizing docs, and stitching context
                  across tools. AI chat tools help in the moment — but close the tab and
                  everything resets. You&apos;re still the one rebuilding context from scratch.
                </p>
              </div>
              <div>
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">What yarnnn does</div>
                <h3 className="text-xl font-medium mb-4 text-[#1a1a1a]">Keep the system running.</h3>
                <p className="text-[#1a1a1a]/50 leading-relaxed mb-4">
                  yarnnn keeps shared context, a persistent workforce, and recurring
                  tasks in one system. You define the work. Agents execute it. TP
                  explains what happened and adjusts what should happen next.
                </p>
                <p className="text-[#1a1a1a] text-sm font-medium">
                  Agents are who. Tasks are what.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ─── How it works (animated timeline) ────────────────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-16">
              <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
                Connect context. Define tasks. Supervise the loop.
              </h2>
              <p className="text-[#1a1a1a]/50 max-w-md mx-auto">
                Persistent agents, shared workspace context, and recurring work that compounds.
              </p>
            </div>

            <AnimatedTimeline />
          </div>
        </section>

        {/* ─── Bento grid (team + tasks + outputs + moat) ──────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <BentoGrid>
              {/* Large card: Your team */}
              <SpotlightCard
                className="md:col-span-4 md:row-span-2"
                spotlightColor="rgba(99,102,241,0.06)"
              >
                <div className="p-6 md:p-8 h-full">
                  <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-4">Your team</div>
                  <h3 className="text-xl md:text-2xl font-medium mb-2 text-[#1a1a1a]">
                    Ten agents, one workforce
                  </h3>
                  <p className="text-[#1a1a1a]/50 text-sm mb-8 max-w-md">
                    Five domain stewards, one reporting synthesizer, three platform
                    bots, and Thinking Partner as the meta-cognitive agent.
                  </p>

                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {([
                      { name: "Competitive Intel", letter: "CI", color: "#6366f1", desc: "Competitors, external signals" },
                      { name: "Market Research", letter: "MR", color: "#0ea5e9", desc: "Research, market context" },
                      { name: "Business Dev", letter: "BD", color: "#10b981", desc: "Relationships, opportunities" },
                      { name: "Operations", letter: "OP", color: "#f59e0b", desc: "Process, execution health" },
                      { name: "Marketing", letter: "M", color: "#ef4444", desc: "Positioning, creative context" },
                      { name: "Reporting", letter: "RP", color: "#8b5cf6", desc: "Cross-domain synthesis" },
                      { name: "Slack Bot", letter: "S", color: "#E01E5A", desc: "Channels & threads" },
                      { name: "Notion Bot", letter: "N", color: "#191919", desc: "Pages & databases" },
                      { name: "GitHub Bot", letter: "G", color: "#111827", desc: "Repos & code context" },
                      { name: "Thinking Partner", letter: "TP", color: "#374151", desc: "System orchestration" },
                    ] as const).map((agent) => (
                      <div key={agent.name} className="flex items-center gap-3 p-2 rounded-xl hover:bg-[#1a1a1a]/[0.02] transition-colors">
                        <div
                          className="w-9 h-9 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
                          style={{ backgroundColor: agent.color }}
                        >
                          {agent.letter}
                        </div>
                        <div className="min-w-0">
                          <div className="text-sm font-medium text-[#1a1a1a] truncate">{agent.name}</div>
                          <div className="text-[10px] text-[#1a1a1a]/40 truncate">{agent.desc}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </SpotlightCard>

              {/* Task example card */}
              <SpotlightCard
                className="md:col-span-2"
                spotlightColor="rgba(14,165,233,0.06)"
              >
                <div className="p-6 h-full flex flex-col">
                  <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Example task</div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-5 h-5 rounded-full bg-violet-500 flex items-center justify-center">
                      <span className="text-[8px] text-white font-bold">RP</span>
                    </div>
                    <span className="text-sm font-medium text-[#1a1a1a]">Weekly leadership brief</span>
                  </div>
                  <p className="text-[#1a1a1a]/40 text-xs leading-relaxed flex-1">
                    Reporting turns fresh workspace context into an executive brief:
                    key updates, blockers, decisions, and what changed across the week.
                  </p>
                  <div className="mt-3 flex items-center gap-2">
                    <span className="text-[9px] px-2 py-0.5 rounded-full bg-[#1a1a1a]/[0.04] text-[#1a1a1a]/40">Recurring</span>
                    <span className="text-[9px] px-2 py-0.5 rounded-full bg-[#1a1a1a]/[0.04] text-[#1a1a1a]/40">Weekly</span>
                  </div>
                </div>
              </SpotlightCard>

              {/* Feedback loop card */}
              <SpotlightCard
                className="md:col-span-2"
                spotlightColor="rgba(245,158,11,0.06)"
              >
                <div className="p-6 h-full flex flex-col">
                  <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Feedback loop</div>
                  <div className="flex-1 flex flex-col justify-center">
                    <div className="space-y-3">
                      <div className="flex items-center gap-2">
                        <div className="w-5 h-5 rounded-full bg-[#1a1a1a]/[0.06] flex items-center justify-center text-[8px] text-[#1a1a1a]/50">1</div>
                        <span className="text-xs text-[#1a1a1a]/60">Agent delivers output</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-5 h-5 rounded-full bg-[#1a1a1a]/[0.06] flex items-center justify-center text-[8px] text-[#1a1a1a]/50">2</div>
                        <span className="text-xs text-[#1a1a1a]/60">You edit or redirect</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-5 h-5 rounded-full bg-amber-100 flex items-center justify-center text-[8px] text-amber-700">3</div>
                        <span className="text-xs text-[#1a1a1a] font-medium">Preferences learned</span>
                      </div>
                    </div>
                  </div>
                </div>
              </SpotlightCard>

              {/* Output formats card */}
              <SpotlightCard
                className="md:col-span-2"
                spotlightColor="rgba(16,185,129,0.06)"
              >
                <div className="p-6 h-full">
                  <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Output formats</div>
                  <div className="flex flex-wrap gap-2">
                    {["PDF", "PPTX", "XLSX", "Email", "HTML", "Charts"].map((fmt) => (
                      <span
                        key={fmt}
                        className="px-3 py-1.5 rounded-lg bg-[#1a1a1a]/[0.03] border border-[#1a1a1a]/[0.06] text-xs text-[#1a1a1a]/60 font-medium"
                      >
                        {fmt}
                      </span>
                    ))}
                  </div>
                  <p className="text-[#1a1a1a]/40 text-xs mt-4 leading-relaxed">
                    Agents produce rich output. Format depends on the task.
                  </p>
                </div>
              </SpotlightCard>

              {/* Day 90 moat card */}
              <SpotlightCard
                className="md:col-span-2"
                spotlightColor="rgba(99,102,241,0.06)"
              >
                <div className="p-6 h-full flex flex-col justify-center">
                  <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Why it compounds</div>
                  <h3 className="text-lg font-medium mb-2 text-[#1a1a1a]">
                    Day 1 is good.
                  </h3>
                  <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]/50">
                    Day 90 is irreplaceable.
                  </h3>
                  <p className="text-[#1a1a1a]/40 text-xs leading-relaxed">
                    3 months of context, feedback, and domain knowledge can&apos;t be
                    replicated by switching tools. That&apos;s the whole point.
                  </p>
                </div>
              </SpotlightCard>
            </BentoGrid>
          </div>
        </section>

        {/* ─── What agents produce (mock outputs) ──────────────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-16">
              <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
                Real output, not chat responses
              </h2>
              <p className="text-[#1a1a1a]/50 max-w-lg mx-auto">
                Agents produce finished deliverables — formatted, attributed, and delivered
                on schedule. Not conversation fragments.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 items-start">
              <MockPDF />
              <MockEmail />
              <MockBrief />
            </div>
          </div>
        </section>

        {/* ─── CTA ─────────────────────────────────────────────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
              Start with one task.
            </h2>
            <p className="text-[#1a1a1a]/50 mb-4">
              Free: 2 active tasks, 20 work credits/month, daily sync
            </p>
            <p className="text-[#1a1a1a]/50 mb-10">
              Pro: 10 active tasks, 500 work credits/month, hourly sync — $19/mo
            </p>
            <Link
              href="/auth/login"
              className="inline-block px-8 py-4 bg-[#1a1a1a] text-white text-lg font-medium rounded-full hover:bg-[#1a1a1a]/90 transition-all"
            >
              Start free
            </Link>
          </div>
        </section>

        <LandingFooter />
      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteSchema) }}
      />
    </main>
  );
}
