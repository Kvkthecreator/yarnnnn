import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackground } from "@/components/landing/ShaderBackground";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { IntegrationHub } from "@/components/landing/IntegrationHub";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata: Metadata = getMarketingMetadata({
  title: "Autonomous AI That Compounds With Your Context",
  description:
    "yarnnn connects to your Slack, Gmail, Notion, and Calendar to produce recurring work autonomously and improve with every cycle.",
  path: "/",
  keywords: [
    "autonomous ai",
    "context aware ai",
    "recurring work automation",
    "slack gmail notion ai",
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
                  AI that works autonomously—
                  <br />
                  <span className="text-[#1a1a1a]">and gets smarter the longer you use it.</span>
                </h1>

                {/* Supporting headline */}
                <p className="text-lg md:text-xl text-[#1a1a1a]/50 mb-12 max-w-xl mx-auto lg:mx-0 font-light">
                  It connects to your Slack, Gmail, Notion, and Calendar.
                  It learns your world. It produces your recurring work on schedule.
                  You just review and approve.
                </p>

                <Link
                  href="/auth/login"
                  className="inline-block px-8 py-4 glass-light text-[#1a1a1a] text-lg font-medium hover:bg-white/80 transition-all"
                >
                  Start for free
                </Link>
              </div>

              {/* Right side - Animated Integration Hub (hidden on mobile/tablet) */}
              <div className="flex-shrink-0 pb-16">
                <IntegrationHub />
              </div>
            </div>
          </div>
        </section>

        {/* The Gap */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <div>
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">The problem</div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
                  Every AI tool forgets.
                  <br />
                  <span className="text-[#1a1a1a]/50">None work autonomously.</span>
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed mb-6">
                  You use AI every day. Every day, it forgets everything. Your context,
                  your preferences, your last conversation. You start from scratch,
                  re-explain your world, and do all the assembly yourself.
                </p>
                <p className="text-[#1a1a1a]/50 leading-relaxed">
                  AI is powerful. But stateless, one-shot AI can&apos;t actually work for you.
                </p>
              </div>
              <div className="glass-card-light p-6">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">How yarnnn is different</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Context in. Autonomy out.</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  yarnnn connects to where your work lives, accumulates context over time,
                  and produces your recurring work on schedule. You shift from operator to
                  supervisor—reviewing and approving instead of writing and assembling.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* How It Works - Visual */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a] text-center">
              How it works
            </h2>
            <p className="text-[#1a1a1a]/50 text-center mb-16 max-w-xl mx-auto">
              Three steps. Then it runs on its own.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">01</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Connect your world</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Link Slack, Gmail, Notion, or Calendar—wherever your work lives.
                  yarnnn starts accumulating context from day one.
                </p>
              </div>

              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">02</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Tell TP what you need</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Talk to your Thinking Partner in plain language. TP sets up
                  your recurring deliverables and learns how you work.
                </p>
              </div>

              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">03</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Supervise, don&apos;t write</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  yarnnn produces your work on schedule. You review and approve.
                  Each cycle, it gets closer to exactly what you want.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* The Accumulation Moat */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <div className="md:order-2">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">The advantage</div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
                  It gets smarter
                  <br />
                  <span className="text-[#1a1a1a]/50">every single day.</span>
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed mb-6">
                  Every sync cycle, yarnnn absorbs more of your work context—conversations,
                  decisions, patterns. Every approval teaches it your preferences. The context
                  compounds.
                </p>
                <p className="text-[#1a1a1a]/50 leading-relaxed">
                  After 90 days, yarnnn understands your work better than any tool you&apos;ve ever used.
                  That understanding is irreplaceable.
                </p>
              </div>
              <div className="glass-card-light p-6 md:order-1">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">How it compounds</div>
                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/10 flex items-center justify-center text-xs text-[#1a1a1a]/50 shrink-0 mt-0.5">1</div>
                    <p className="text-[#1a1a1a]/70 text-sm">Your platforms sync continuously—context accumulates</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/10 flex items-center justify-center text-xs text-[#1a1a1a]/50 shrink-0 mt-0.5">2</div>
                    <p className="text-[#1a1a1a]/70 text-sm">TP learns your style, your tone, what matters to you</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/10 flex items-center justify-center text-xs text-[#1a1a1a]/50 shrink-0 mt-0.5">3</div>
                    <p className="text-[#1a1a1a]/70 text-sm">Deliverables get more autonomous with each cycle</p>
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

        {/* What yarnnn Handles */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
              Work that happens without you
            </h2>
            <p className="text-[#1a1a1a]/50 mb-12 max-w-xl">
              If it&apos;s recurring, context-dependent, and you owe it to someone—yarnnn handles it.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Autonomous</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Weekly status reports</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Synthesized from your Slack channels and threads.
                  Delivered on schedule, in your voice.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Autonomous</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Client follow-ups</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Open threads, pending items, next steps—pulled from Gmail
                  and ready for your review.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Autonomous</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Investor updates</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Metrics, milestones, and narrative—drafted from your
                  Notion docs and project notes.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Autonomous</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Meeting prep briefs</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Attendee context, past interactions, relevant docs—ready
                  before your Calendar event starts.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Autonomous</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Stakeholder briefs</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Cross-platform context combined into one coherent update
                  for execs or partners.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Your call</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Anything recurring</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  If it follows a pattern and your platforms have the context,
                  yarnnn can learn to produce it autonomously.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Two Ways to Start */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a] text-center">
              Two ways to get started
            </h2>
            <p className="text-[#1a1a1a]/50 text-center mb-12 max-w-xl mx-auto">
              Connect your platforms for full autonomy.
              Or start with a conversation and connect later.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="glass-card-light p-8">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-2">Recommended</div>
                <h3 className="text-xl font-medium mb-4 text-[#1a1a1a]">Connect your platforms</h3>
                <p className="text-[#1a1a1a]/50 text-sm mb-6 leading-relaxed">
                  Link Slack, Gmail, Notion, or Calendar. Context accumulates automatically.
                  yarnnn gets smarter with every sync cycle.
                </p>
                <ul className="space-y-2 text-sm text-[#1a1a1a]/70">
                  <li className="flex items-start gap-2">
                    <span className="text-[#1a1a1a]/40">+</span>
                    Context compounds over time
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[#1a1a1a]/40">+</span>
                    Fully autonomous output on schedule
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[#1a1a1a]/40">+</span>
                    yarnnn discovers patterns you didn&apos;t notice
                  </li>
                </ul>
              </div>

              <div className="glass-card-light p-8 opacity-80">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-2">Also works</div>
                <h3 className="text-xl font-medium mb-4 text-[#1a1a1a]">Start with TP</h3>
                <p className="text-[#1a1a1a]/50 text-sm mb-6 leading-relaxed">
                  Just talk to your Thinking Partner. Describe what you need,
                  paste context manually, and connect platforms when you&apos;re ready.
                </p>
                <ul className="space-y-2 text-sm text-[#1a1a1a]/70">
                  <li className="flex items-start gap-2">
                    <span className="text-[#1a1a1a]/40">+</span>
                    Start in seconds
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[#1a1a1a]/40">+</span>
                    No permissions needed upfront
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[#1a1a1a]/40">+</span>
                    Upgrade to full autonomy anytime
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
              AI that works for you—
              <br />
              <span className="text-[#1a1a1a]/50">not just with you.</span>
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
              Start for free
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
