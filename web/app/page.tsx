import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackground } from "@/components/landing/ShaderBackground";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { IntegrationHub } from "@/components/landing/IntegrationHub";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata: Metadata = getMarketingMetadata({
  title: "AI Agents That Work While You Sleep",
  description:
    "yarnnn connects to Slack, Gmail, Notion, and Calendar, then runs AI agents that deliver real work on schedule. Connect once. Wake up to finished work.",
  path: "/",
  keywords: [
    "autonomous ai",
    "ai agent platform",
    "ai work agent",
    "slack ai summary",
    "gmail ai digest",
    "ai meeting prep",
    "autonomous workflow",
    "ai employee",
    "agent automation",
    "recurring ai work",
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

        {/* Hero */}
        <section className="flex flex-col items-center justify-center px-6 py-32 md:py-40 min-h-[80vh]">
          <div className="max-w-6xl mx-auto w-full">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-12 lg:gap-20">
              <div className="text-center lg:text-left flex-1 max-w-2xl mx-auto lg:mx-0">
                <div className="font-brand text-4xl md:text-5xl mb-8 text-[#1a1a1a]">yarnnn</div>

                <h1 className="text-2xl sm:text-3xl md:text-4xl font-medium tracking-wide text-[#1a1a1a]/90 mb-6">
                  AI agents that work
                  <br />
                  <span className="text-[#1a1a1a]">while you sleep.</span>
                </h1>

                <p className="text-lg md:text-xl text-[#1a1a1a]/50 mb-12 max-w-xl mx-auto lg:mx-0 font-light">
                  Connect your tools once. yarnnn runs agents in the background
                  that deliver real work on schedule — recaps, briefs, research,
                  reports. You wake up to finished work. They get better every cycle.
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

        {/* The problem */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <div>
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">The problem</div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
                  Every Monday, same work.
                  <br />
                  <span className="text-[#1a1a1a]/50">Still doing it yourself.</span>
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed mb-6">
                  You spend hours pulling updates from Slack, summarizing emails,
                  prepping for meetings, and stitching context across tools that
                  don&apos;t talk to each other.
                </p>
                <p className="text-[#1a1a1a]/50 leading-relaxed">
                  AI chat tools help in the moment, but they forget everything
                  between sessions. You&apos;re still the one rebuilding context
                  from scratch every time.
                </p>
              </div>
              <div className="glass-card-light p-6">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">What yarnnn does instead</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Hire agents. Supervise outcomes.</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  yarnnn connects to your work tools and creates agents that handle
                  recurring work in the background. They remember everything, learn
                  from your feedback, and deliver better output every cycle.
                  You supervise — they operate.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* How it works */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a] text-center">
              Three steps. Then it runs itself.
            </h2>
            <p className="text-[#1a1a1a]/50 text-center mb-16 max-w-xl mx-auto">
              Connect once, supervise from there.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">01</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Connect your tools</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Link Slack, Gmail, Notion, or Calendar. yarnnn immediately
                  creates your first agents and starts syncing.
                </p>
              </div>

              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">02</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Agents do the work</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Each agent runs on schedule and delivers real output — recaps,
                  briefs, reports, research. Multiple agents work together on
                  bigger jobs.
                </p>
              </div>

              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">03</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">You review. They learn.</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Review, edit, or redirect. Your feedback becomes their learned behavior.
                  Quality compounds with every cycle.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* What agents handle */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
              Work that runs itself
            </h2>
            <p className="text-[#1a1a1a]/50 mb-12 max-w-xl">
              Tell yarnnn what you need, or connect a platform and let it figure it out.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Weekly team update</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Slack and email, synthesized</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Daily or weekly summaries of your channels and inboxes — highlights, decisions,
                  and action items delivered on schedule.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Meeting prep</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Briefed before every meeting</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Every morning, yarnnn reads your calendar and pulls context from
                  Slack, Gmail, and Notion into a prep briefing for each meeting.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Competitor watch</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Continuous intelligence</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Track competitors, markets, or topics. Combines your internal context
                  with web research and delivers updates on your cadence.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Status report</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Cross-platform synthesis</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Multiple agents pull from different sources, then combine into one
                  polished report — PDF, slides, or email-ready.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Email triage</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">What needs your attention</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Daily recap of your Gmail labels — key threads, follow-ups, and
                  what actually needs you vs. what can wait.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Research tracker</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Deep dives on autopilot</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Set a research topic. yarnnn monitors, investigates, and
                  delivers findings on schedule — building depth with each cycle.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Compounding */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <div className="md:order-2">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">Why it gets better</div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
                  Day 1 is good.
                  <br />
                  <span className="text-[#1a1a1a]/50">Day 90 is irreplaceable.</span>
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed mb-6">
                  Every sync, every edit, and every review makes your agents smarter.
                  They learn your preferred structure, tone, and priorities.
                </p>
                <p className="text-[#1a1a1a]/50 leading-relaxed">
                  After 90 days, your agents know your work better than any tool
                  you could switch to. That&apos;s the whole point.
                </p>
              </div>
              <div className="glass-card-light p-6 md:order-1">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">What compounds</div>
                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/10 flex items-center justify-center text-xs text-[#1a1a1a]/50 shrink-0 mt-0.5">1</div>
                    <p className="text-[#1a1a1a]/70 text-sm">Your tools sync — agents see everything</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/10 flex items-center justify-center text-xs text-[#1a1a1a]/50 shrink-0 mt-0.5">2</div>
                    <p className="text-[#1a1a1a]/70 text-sm">Agents deliver work — you review and redirect</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/10 flex items-center justify-center text-xs text-[#1a1a1a]/50 shrink-0 mt-0.5">3</div>
                    <p className="text-[#1a1a1a]/70 text-sm">Your feedback becomes learned behavior</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/20 flex items-center justify-center text-xs text-[#1a1a1a]/70 shrink-0 mt-0.5">4</div>
                    <p className="text-[#1a1a1a] text-sm font-medium">Next cycle is better. Repeat.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
              Your first AI employee starts today.
            </h2>
            <p className="text-[#1a1a1a]/50 mb-4">
              Free: 50 messages/month, 2 agents, daily sync
            </p>
            <p className="text-[#1a1a1a]/50 mb-10">
              Pro: unlimited messages, 10 agents, hourly sync — $19/mo
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
