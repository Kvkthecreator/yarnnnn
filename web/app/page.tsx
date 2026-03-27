import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackground } from "@/components/landing/ShaderBackground";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { IntegrationHub } from "@/components/landing/IntegrationHub";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata: Metadata = getMarketingMetadata({
  title: "Your AI Workforce — Ready on Day 1",
  description:
    "Sign up and meet your team: Research, Content, Marketing, and CRM agents plus Slack and Notion bots. Assign tasks. They execute on schedule and get better every cycle.",
  path: "/",
  keywords: [
    "autonomous ai",
    "ai agent platform",
    "ai workforce",
    "ai work agent",
    "slack ai summary",
    "notion ai summary",
    "autonomous workflow",
    "ai employee",
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

        {/* Hero */}
        <section className="flex flex-col items-center justify-center px-6 py-32 md:py-40 min-h-[80vh]">
          <div className="max-w-6xl mx-auto w-full">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-12 lg:gap-20">
              <div className="text-center lg:text-left flex-1 max-w-2xl mx-auto lg:mx-0">
                <div className="font-brand text-4xl md:text-5xl mb-8 text-[#1a1a1a]">yarnnn</div>

                <h1 className="text-2xl sm:text-3xl md:text-4xl font-medium tracking-wide text-[#1a1a1a]/90 mb-6">
                  Your AI workforce
                  <br />
                  <span className="text-[#1a1a1a]">is ready on day 1.</span>
                </h1>

                <p className="text-lg md:text-xl text-[#1a1a1a]/50 mb-12 max-w-xl mx-auto lg:mx-0 font-light">
                  Sign up and meet your team — Research, Content, Marketing, and CRM
                  agents ready to work. Share context through conversation, documents,
                  or connected tools. They get better every cycle.
                </p>

                <Link
                  href="/auth/login"
                  className="inline-block px-8 py-4 glass-light text-[#1a1a1a] text-lg font-medium hover:bg-white/80 transition-all"
                >
                  Meet your team
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
                  You spend hours pulling updates from Slack, summarizing docs,
                  and stitching context across tools that don&apos;t talk to each
                  other.
                </p>
                <p className="text-[#1a1a1a]/50 leading-relaxed">
                  AI chat tools help in the moment, but they forget everything
                  between sessions. You&apos;re still the one rebuilding context
                  from scratch every time.
                </p>
              </div>
              <div className="glass-card-light p-6">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">What yarnnn does instead</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Hire the team. Assign the tasks.</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  yarnnn gives you a team of specialist agents on day 1. You assign
                  recurring tasks — weekly recaps, competitor briefs, research reports —
                  and they execute on schedule. They learn from your feedback and deliver
                  better output every cycle. You supervise — they operate.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Your team */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
              Meet your team
            </h2>
            <p className="text-[#1a1a1a]/50 mb-12 max-w-xl">
              Six specialists, ready at sign-up. No configuration required.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Agent</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Research Agent</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Web research, competitive intelligence, topic monitoring. Finds what
                  matters and builds depth with every cycle.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Agent</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Content Agent</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Drafts, reports, briefs, and summaries. Produces polished output in
                  your voice — PDF, slides, spreadsheets, or email.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Agent</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Marketing Agent</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Market signals, positioning analysis, campaign tracking. Keeps you
                  informed on what your market is doing.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Agent</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">CRM Agent</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Relationship tracking, client updates, stakeholder briefings. Remembers
                  the people context you care about.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Bot</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Slack Bot</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Reads channels and threads. Activates when you connect Slack —
                  your agents&apos; eyes and ears in conversations.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Bot</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Notion Bot</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Reads pages and databases. Activates when you connect Notion —
                  your agents&apos; access to structured knowledge.
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
              Agents are who. Tasks are what. You supervise from there.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">01</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Describe your work</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Tell yarnnn what you need — &ldquo;weekly competitor brief&rdquo; or
                  &ldquo;Friday team recap.&rdquo; Share context through conversation,
                  documents, or by connecting Slack and Notion.
                </p>
              </div>

              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">02</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Tasks run on schedule</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Each task is assigned to the right agent and runs on your cadence —
                  daily, weekly, or on-demand. Output ships as email, PDF, slides,
                  or spreadsheets.
                </p>
              </div>

              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">03</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">You review. They learn.</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Review, edit, or redirect. Your feedback becomes learned behavior
                  that carries forward. Quality compounds with every cycle.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* What tasks look like */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
              Tasks that run themselves
            </h2>
            <p className="text-[#1a1a1a]/50 mb-12 max-w-xl">
              Describe the work. yarnnn assigns the right agent and sets the cadence.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Recurring</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Weekly team recap</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Slack Bot syncs channels, Content Agent synthesizes — highlights,
                  decisions, and action items delivered every Monday.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Recurring</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Competitor watch</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Research Agent monitors competitors weekly — combines web intelligence
                  with your internal context to surface what matters.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Recurring</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Status report as PDF</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Content Agent pulls from Slack and Notion, produces a polished
                  PDF delivered to leadership every Friday.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Goal</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Market research deep dive</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Research Agent investigates a topic across multiple cycles, building
                  depth until success criteria are met.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Reactive</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Meeting prep brief</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  On-demand context from Slack and Notion — a 2-minute briefing
                  pulled together before any key meeting.
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
                    <p className="text-[#1a1a1a]/70 text-sm">You share context — conversation, docs, connected tools</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/10 flex items-center justify-center text-xs text-[#1a1a1a]/50 shrink-0 mt-0.5">2</div>
                    <p className="text-[#1a1a1a]/70 text-sm">Tasks run on schedule — agents deliver real output</p>
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
              Your team is waiting.
            </h2>
            <p className="text-[#1a1a1a]/50 mb-4">
              Free: 2 active agents, 60 task runs/month, daily sync
            </p>
            <p className="text-[#1a1a1a]/50 mb-10">
              Pro: 10 active agents, 1,000 task runs/month, hourly sync — $19/mo
            </p>
            <Link
              href="/auth/login"
              className="inline-block px-8 py-4 glass-light text-[#1a1a1a] text-lg font-medium hover:bg-white/80 transition-all"
            >
              Meet your team
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
