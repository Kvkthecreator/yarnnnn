import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackground } from "@/components/landing/ShaderBackground";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { IntegrationHub } from "@/components/landing/IntegrationHub";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata: Metadata = getMarketingMetadata({
  title: "Meet TP — Your Autonomous AI Agent",
  description:
    "TP is an AI agent that already knows your work. Connected to your Slack, Gmail, Notion, and Calendar. It produces your deliverables on schedule and gets smarter every cycle.",
  path: "/",
  keywords: [
    "autonomous ai agent",
    "ai agent",
    "thinking partner",
    "context aware ai",
    "slack gmail notion ai agent",
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

      {/* Content layer */}
      <div className="relative z-10">
        <LandingHeader />

        {/* Hero Section */}
        <section className="flex flex-col items-center justify-center px-6 py-32 md:py-40 min-h-[80vh]">
          <div className="max-w-6xl mx-auto w-full">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-12 lg:gap-20">
              {/* Left side - Text content */}
              <div className="text-center lg:text-left flex-1 max-w-2xl mx-auto lg:mx-0">
                {/* Brand name */}
                <div className="font-brand text-4xl md:text-5xl mb-8 text-[#1a1a1a]">
                  yarnnn
                </div>

                {/* Hero headline */}
                <h1 className="text-2xl sm:text-3xl md:text-4xl font-medium tracking-wide text-[#1a1a1a]/90 mb-6">
                  Meet TP — your autonomous AI agent.
                  <br />
                  <span className="text-[#1a1a1a]">It already knows your work.</span>
                </h1>

                {/* Supporting headline */}
                <p className="text-lg md:text-xl text-[#1a1a1a]/50 mb-12 max-w-xl mx-auto lg:mx-0 font-light">
                  Connected to your Slack, Gmail, Notion, and Calendar.
                  Producing your deliverables on schedule.
                  Getting smarter every cycle. You just supervise.
                </p>

                <Link
                  href="/auth/login"
                  className="inline-block px-8 py-4 glass-light text-[#1a1a1a] text-lg font-medium hover:bg-white/80 transition-all"
                >
                  Start talking to TP
                </Link>
              </div>

              {/* Right side - Animated Integration Hub */}
              <div className="flex-shrink-0 pb-16">
                <IntegrationHub />
              </div>
            </div>
          </div>
        </section>

        {/* The Agent Problem */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <div>
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">The problem</div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
                  Every AI agent disappoints.
                  <br />
                  <span className="text-[#1a1a1a]/50">Because they all start from zero.</span>
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed mb-6">
                  You&apos;ve tried the agent platforms. They&apos;re powerful but context-free.
                  They don&apos;t know your clients, your projects, your writing style,
                  or what happened in last week&apos;s standup.
                </p>
                <p className="text-[#1a1a1a]/50 leading-relaxed">
                  An agent without context is just automation with better marketing.
                </p>
              </div>
              <div className="glass-card-light p-6">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">How TP is different</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Your context in. Real work out.</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  TP connects to where your work lives and accumulates context over time.
                  It doesn&apos;t start from a blank prompt — it starts from your world.
                  That&apos;s why TP&apos;s output actually sounds like you wrote it.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* How TP Works */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a] text-center">
              How TP works
            </h2>
            <p className="text-[#1a1a1a]/50 text-center mb-16 max-w-xl mx-auto">
              Three steps. Then your agent runs on its own.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">01</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Talk to TP</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Tell your agent what you need in plain language.
                  &ldquo;Weekly status report for Sarah&rdquo; or &ldquo;Monthly investor update.&rdquo;
                  TP asks the right questions and sets everything up.
                </p>
              </div>

              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">02</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Give TP your world</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Connect Slack, Gmail, Notion, or Calendar.
                  TP starts accumulating context immediately — your conversations,
                  decisions, patterns, and relationships.
                </p>
              </div>

              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">03</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Supervise, don&apos;t write</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  TP produces your deliverables on schedule. You review and approve.
                  Every edit teaches TP your preferences.
                  Each cycle, the output gets closer to exactly what you want.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Why TP Is Different */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <div className="md:order-2">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">The advantage</div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
                  After 90 days,
                  <br />
                  <span className="text-[#1a1a1a]/50">no other agent comes close.</span>
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed mb-6">
                  Every sync cycle, TP absorbs more of your work context — conversations,
                  decisions, patterns. Every approval teaches it your preferences.
                  The context compounds.
                </p>
                <p className="text-[#1a1a1a]/50 leading-relaxed">
                  Other agents reset every session. TP accumulates.
                  That accumulated understanding is irreplaceable.
                </p>
              </div>
              <div className="glass-card-light p-6 md:order-1">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">How TP compounds</div>
                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/10 flex items-center justify-center text-xs text-[#1a1a1a]/50 shrink-0 mt-0.5">1</div>
                    <p className="text-[#1a1a1a]/70 text-sm">Your platforms sync continuously — TP&apos;s context deepens</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/10 flex items-center justify-center text-xs text-[#1a1a1a]/50 shrink-0 mt-0.5">2</div>
                    <p className="text-[#1a1a1a]/70 text-sm">TP learns your style, your tone, what matters to each audience</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/10 flex items-center justify-center text-xs text-[#1a1a1a]/50 shrink-0 mt-0.5">3</div>
                    <p className="text-[#1a1a1a]/70 text-sm">Deliverables get sharper with each cycle</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/20 flex items-center justify-center text-xs text-[#1a1a1a]/70 shrink-0 mt-0.5">4</div>
                    <p className="text-[#1a1a1a] text-sm font-medium">You approve with barely a glance</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* What TP Handles */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
              What TP handles for you
            </h2>
            <p className="text-[#1a1a1a]/50 mb-12 max-w-xl">
              If it&apos;s recurring, context-dependent, and you owe it to someone — TP handles it.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">TP produces</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Weekly status reports</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Synthesized from your Slack channels and threads.
                  Delivered on schedule, in your voice.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">TP produces</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Client follow-ups</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Open threads, pending items, next steps — pulled from Gmail
                  and ready for your review.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">TP produces</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Investor updates</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Metrics, milestones, and narrative — drafted from your
                  Notion docs and project notes.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">TP produces</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Meeting prep briefs</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Attendee context, past interactions, relevant docs — ready
                  before your Calendar event starts.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">TP produces</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Stakeholder briefs</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Cross-platform context combined into one coherent update
                  for execs or partners.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">You decide</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Anything recurring</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  If it follows a pattern and your platforms have the context,
                  TP can learn to produce it autonomously.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
              Your agent is ready.
            </h2>
            <p className="text-[#1a1a1a]/50 mb-4">
              Free: 1 deliverable, unlimited platform connections
            </p>
            <p className="text-[#1a1a1a]/50 mb-10">
              Pro: Unlimited deliverables — $19/mo
            </p>
            <Link
              href="/auth/login"
              className="inline-block px-8 py-4 glass-light text-[#1a1a1a] text-lg font-medium hover:bg-white/80 transition-all"
            >
              Start talking to TP
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
