import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackground } from "@/components/landing/ShaderBackground";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { IntegrationHub } from "@/components/landing/IntegrationHub";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata: Metadata = getMarketingMetadata({
  title: "Autonomous AI That Knows Your Work",
  description:
    "yarnnn connects to Slack, Gmail, Notion, and Calendar, then runs autonomous deliverables for you. It learns from every cycle so your outputs improve over time.",
  path: "/",
  keywords: [
    "autonomous ai",
    "ai work agent",
    "thinking partner",
    "context aware ai",
    "deliverable automation",
    "human in the loop ai",
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

        <section className="flex flex-col items-center justify-center px-6 py-32 md:py-40 min-h-[80vh]">
          <div className="max-w-6xl mx-auto w-full">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-12 lg:gap-20">
              <div className="text-center lg:text-left flex-1 max-w-2xl mx-auto lg:mx-0">
                <div className="font-brand text-4xl md:text-5xl mb-8 text-[#1a1a1a]">yarnnn</div>

                <h1 className="text-2xl sm:text-3xl md:text-4xl font-medium tracking-wide text-[#1a1a1a]/90 mb-6">
                  Autonomous AI that
                  <br />
                  <span className="text-[#1a1a1a]">already knows your work.</span>
                </h1>

                <p className="text-lg md:text-xl text-[#1a1a1a]/50 mb-12 max-w-xl mx-auto lg:mx-0 font-light">
                  Connect your tools once. Configure deliverables once.
                  yarnnn runs recurring, reactive, and proactive work in the background.
                  You supervise outcomes.
                </p>

                <Link
                  href="/auth/login"
                  className="inline-block px-8 py-4 glass-light text-[#1a1a1a] text-lg font-medium hover:bg-white/80 transition-all"
                >
                  Start with yarnnn
                </Link>
              </div>

              <div className="flex-shrink-0 pb-16">
                <IntegrationHub />
              </div>
            </div>
          </div>
        </section>

        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <div>
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">The problem</div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
                  Most AI starts blank every session.
                  <br />
                  <span className="text-[#1a1a1a]/50">So you keep rebuilding context.</span>
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed mb-6">
                  You already have the signal in Slack, Gmail, Notion, and Calendar.
                  But typical AI workflows still ask you to gather and restate everything
                  before useful output appears.
                </p>
                <p className="text-[#1a1a1a]/50 leading-relaxed">
                  That keeps you in operator mode instead of supervisor mode.
                </p>
              </div>
              <div className="glass-card-light p-6">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">How yarnnn is different</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Context in. Deliverables out.</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  yarnnn continuously accumulates context from your connected tools,
                  then runs specialist deliverables that learn from every version.
                  The longer you use it, the less manual work remains.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a] text-center">
              How yarnnn works
            </h2>
            <p className="text-[#1a1a1a]/50 text-center mb-16 max-w-xl mx-auto">
              Define the specialist once, then supervise outputs.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">01</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Define your deliverable</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Use TP or the UI to choose type, mode, schedule, and source scope.
                  Example: weekly digest, reactive watch, or proactive briefing specialist.
                </p>
              </div>

              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">02</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Connect your work stack</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Connect Slack, Gmail, Notion, and Calendar.
                  yarnnn keeps context fresh and accumulates what proves significant.
                </p>
              </div>

              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">03</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Review versions, not prompts</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Each run creates a version. You approve or refine.
                  Those edits become learned behavior for the next cycle.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <div className="md:order-2">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">The advantage</div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
                  Compounding context,
                  <br />
                  <span className="text-[#1a1a1a]/50">per specialist.</span>
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed mb-6">
                  Every sync and every approved version improves the same deliverable specialist.
                  Quality grows with usage instead of resetting on every interaction.
                </p>
                <p className="text-[#1a1a1a]/50 leading-relaxed">
                  That compounding behavior is what makes yarnnn durable in real work.
                </p>
              </div>
              <div className="glass-card-light p-6 md:order-1">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">How it compounds</div>
                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/10 flex items-center justify-center text-xs text-[#1a1a1a]/50 shrink-0 mt-0.5">1</div>
                    <p className="text-[#1a1a1a]/70 text-sm">Sources sync and context deepens</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/10 flex items-center justify-center text-xs text-[#1a1a1a]/50 shrink-0 mt-0.5">2</div>
                    <p className="text-[#1a1a1a]/70 text-sm">Deliverable memory captures what works</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/10 flex items-center justify-center text-xs text-[#1a1a1a]/50 shrink-0 mt-0.5">3</div>
                    <p className="text-[#1a1a1a]/70 text-sm">Output quality rises with each version</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/20 flex items-center justify-center text-xs text-[#1a1a1a]/70 shrink-0 mt-0.5">4</div>
                    <p className="text-[#1a1a1a] text-sm font-medium">You supervise with less effort over time</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
              What yarnnn handles
            </h2>
            <p className="text-[#1a1a1a]/50 mb-12 max-w-xl">
              Purpose-built deliverables across recurring updates, event-driven watch, and research workflows.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Recap</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Platform catchup</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Catch up on everything across a connected platform — daily or weekly.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Brief</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Meeting prep briefs</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Context packets from email, docs, and calendar before important conversations.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Work Summary</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Cross-platform synthesis</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Synthesize activity across your platforms — daily, weekly, or on your schedule.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Watch</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Signal monitoring</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Reactive or proactive monitoring that surfaces meaningful change without noise.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Deep research</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Bounded investigations</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Goal-driven research deliverables that run until the objective is complete.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Coordinator</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Meta automation</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Coordinator specialists can trigger or create downstream deliverables when needed.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
              Put autonomous work on your calendar.
            </h2>
            <p className="text-[#1a1a1a]/50 mb-4">
              Free: 2 active deliverables
            </p>
            <p className="text-[#1a1a1a]/50 mb-4">
              Starter: 5 active deliverables and 4x/day sync
            </p>
            <p className="text-[#1a1a1a]/50 mb-10">
              Pro: unlimited deliverables and hourly sync — $19/mo
            </p>
            <Link
              href="/auth/login"
              className="inline-block px-8 py-4 glass-light text-[#1a1a1a] text-lg font-medium hover:bg-white/80 transition-all"
            >
              Start with yarnnn
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
