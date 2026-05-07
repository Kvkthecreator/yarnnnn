import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackground } from "@/components/landing/ShaderBackground";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { IntegrationHub } from "@/components/landing/IntegrationHub";
import { SpotlightCard, BentoGrid } from "@/components/landing/SpotlightCard";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata: Metadata = getMarketingMetadata({
  title: "Agent OS for Recurring Knowledge Work | yarnnn",
  description:
    "Describe your work. YARNNN creates the agents that do it. Persistent agents that connect to your tools, accumulate context from every cycle, and deliver on schedule.",
  path: "/",
  keywords: [
    "ai agents",
    "autonomous ai agents",
    "agent operating system",
    "agent os",
    "ai knowledge work",
    "recurring ai work",
    "ai team",
    "ai business intelligence",
    "autonomous knowledge work",
    "slack ai agent",
    "notion ai agent",
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
                  Describe your work.
                  <br />
                  <span className="text-[#1a1a1a]">YARNNN creates the agents that do it.</span>
                </h1>

                <p className="text-lg md:text-xl text-[#1a1a1a]/50 mb-12 max-w-xl mx-auto lg:mx-0 font-light">
                  Tell YARNNN what you&apos;re trying to accomplish. It creates persistent agents
                  around that work — connected to your tools, running on schedule, accumulating
                  context from every cycle. Built by chatting, not from a catalog.
                </p>

                <Link
                  href="/auth/login"
                  className="inline-block px-8 py-4 glass-light text-[#1a1a1a] text-lg font-medium hover:bg-white/80 transition-all"
                >
                  Start describing your work
                </Link>
              </div>

              <div className="flex-shrink-0 pb-16">
                <IntegrationHub />
              </div>
            </div>
          </div>
        </section>

        {/* ─── Agent OS: Three pillars ───────────────────────────────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-16">
              <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">Agent OS</div>
              <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
                Not an application. An operating system.
              </h2>
              <p className="text-[#1a1a1a]/50 max-w-lg mx-auto">
                Three layers that make autonomous work trustworthy rather than reckless.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="p-8 rounded-2xl border border-[#1a1a1a]/[0.06] bg-[#1a1a1a]/[0.02]">
                <div className="text-xs font-mono text-[#1a1a1a]/30 uppercase tracking-wider mb-4">Kernel</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">The kernel runs the operation</h3>
                <p className="text-sm text-[#1a1a1a]/50 leading-relaxed">
                  Scheduled recurrences, deterministic pipelines, and platform connections
                  execute without you present. LLM reasoning is reserved for work that
                  genuinely requires judgment.
                </p>
              </div>
              <div className="p-8 rounded-2xl border border-[#1a1a1a]/[0.06] bg-[#1a1a1a]/[0.02]">
                <div className="text-xs font-mono text-[#1a1a1a]/30 uppercase tracking-wider mb-4">Substrate</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">The substrate accumulates</h3>
                <p className="text-sm text-[#1a1a1a]/50 leading-relaxed">
                  Your workspace is the persistent memory of the operation — tool context,
                  prior outputs, feedback from your edits. Switching tools means starting
                  over from zero.
                </p>
              </div>
              <div className="p-8 rounded-2xl border border-[#1a1a1a]/[0.06] bg-[#1a1a1a]/[0.02]">
                <div className="text-xs font-mono text-[#1a1a1a]/30 uppercase tracking-wider mb-4">Judgment</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Judgment is independent</h3>
                <p className="text-sm text-[#1a1a1a]/50 leading-relaxed">
                  What agents want to do and whether they should are two separate
                  questions — answered by two different layers. Proposed actions are
                  evaluated against your declared intent before they bind.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ─── The operating loop ───────────────────────────────────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
              Declare. Build. Run. Supervise.
            </h2>
            <p className="text-[#1a1a1a]/50 mb-16 max-w-lg">
              The operating model in four moves. Each one flows into the next.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
              {([
                {
                  number: "01",
                  title: "Declare your intent",
                  desc: "Tell YARNNN what you're trying to accomplish — a mandate, a domain, a recurring task. Described in plain language.",
                },
                {
                  number: "02",
                  title: "Agents are created",
                  desc: "YARNNN creates persistent agents through conversation. Each scoped to your domain. Each authored, not provisioned.",
                },
                {
                  number: "03",
                  title: "The operation runs",
                  desc: "Agents connect to your tools, execute on schedule, accumulate context from every cycle — whether you're online or not.",
                },
                {
                  number: "04",
                  title: "You supervise",
                  desc: "Review what ran, redirect what needs changing. Your corrections feed back into how the operation behaves next cycle.",
                },
              ] as const).map((step) => (
                <div key={step.number} className="flex flex-col">
                  <div className="text-4xl font-light text-[#1a1a1a]/10 mb-4">{step.number}</div>
                  <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">{step.title}</h3>
                  <p className="text-sm text-[#1a1a1a]/50 leading-relaxed">{step.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ─── The authored team (bento) ────────────────────────────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <BentoGrid>
              {/* Large card: The palette */}
              <SpotlightCard
                className="md:col-span-4 md:row-span-2"
                spotlightColor="rgba(99,102,241,0.06)"
              >
                <div className="p-6 md:p-8 h-full">
                  <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-4">The specialist palette</div>
                  <h3 className="text-xl md:text-2xl font-medium mb-2 text-[#1a1a1a]">
                    Six roles. Your agents are built from them.
                  </h3>
                  <p className="text-[#1a1a1a]/50 text-sm mb-8 max-w-md">
                    YARNNN drafts from a palette of specialist roles and platform connectors
                    per task. Your domain agents are persistent — authored through conversation,
                    accumulating expertise over time.
                  </p>

                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {([
                      { name: "Researcher", letter: "R", color: "#6366f1", desc: "Gathers intelligence on any domain" },
                      { name: "Analyst", letter: "A", color: "#0ea5e9", desc: "Turns data into structured insight" },
                      { name: "Writer", letter: "W", color: "#10b981", desc: "Produces drafts, briefs, and content" },
                      { name: "Tracker", letter: "T", color: "#f59e0b", desc: "Monitors signals and watches trends" },
                      { name: "Designer", letter: "D", color: "#ef4444", desc: "Creates charts, visuals, and assets" },
                      { name: "Reporting", letter: "RP", color: "#8b5cf6", desc: "Connects dots across all domains" },
                      { name: "Slack", letter: "S", color: "#E01E5A", desc: "Channels, threads, live discussion" },
                      { name: "Notion", letter: "N", color: "#191919", desc: "Pages, databases, wikis" },
                      { name: "GitHub", letter: "G", color: "#111827", desc: "Repos, issues, and activity" },
                      { name: "YARNNN", letter: "Y", color: "#374151", desc: "The orchestrator you talk to" },
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

              {/* Authorship card */}
              <SpotlightCard
                className="md:col-span-2"
                spotlightColor="rgba(14,165,233,0.06)"
              >
                <div className="p-6 h-full flex flex-col">
                  <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Authorship</div>
                  <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Built by chatting. Not from a catalog.</h3>
                  <p className="text-[#1a1a1a]/40 text-xs leading-relaxed flex-1">
                    Your agents emerge from conversation with YARNNN — scoped to your domain,
                    with your context, accumulating expertise from every run. The switching cost
                    begins with the first one.
                  </p>
                </div>
              </SpotlightCard>

              {/* Cockpit card */}
              <SpotlightCard
                className="md:col-span-2"
                spotlightColor="rgba(245,158,11,0.06)"
              >
                <div className="p-6 h-full flex flex-col">
                  <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">The cockpit</div>
                  <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">You work inside yarnnn.</h3>
                  <p className="text-[#1a1a1a]/40 text-xs leading-relaxed flex-1">
                    Overview. Agents. Work. Context. Review. The cockpit is where the operation
                    is visible, the team is tuned, and pending decisions are made. Not a report
                    factory you check elsewhere.
                  </p>
                </div>
              </SpotlightCard>

              {/* Day 90 moat card */}
              <SpotlightCard
                className="md:col-span-2"
                spotlightColor="rgba(99,102,241,0.06)"
              >
                <div className="p-6 h-full flex flex-col justify-center">
                  <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">The moat</div>
                  <h3 className="text-lg font-medium mb-2 text-[#1a1a1a]">Day 1 is useful.</h3>
                  <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]/50">Day 90 is irreplaceable.</h3>
                  <p className="text-[#1a1a1a]/40 text-xs leading-relaxed">
                    Months of accumulated context about your domain, your preferences, and your
                    operation can&apos;t be rebuilt by switching to a fresh tool.
                  </p>
                </div>
              </SpotlightCard>

              {/* Output formats card */}
              <SpotlightCard
                className="md:col-span-2"
                spotlightColor="rgba(16,185,129,0.06)"
              >
                <div className="p-6 h-full">
                  <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">What agents produce</div>
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
                    Not chat responses. Formatted deliverables scheduled and delivered on cadence.
                  </p>
                </div>
              </SpotlightCard>
            </BentoGrid>
          </div>
        </section>

        {/* ─── The judgment layer ───────────────────────────────────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-start">
              <div>
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">Independent review</div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
                  Agents propose.
                  <br />
                  <span className="text-[#1a1a1a]/50">A separate layer judges.</span>
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed">
                  What your agents want to do and whether they should do it are two separate
                  questions — answered by two different layers. An independent judgment function
                  reads your declared intent and evaluates proposed actions before they bind.
                  The result: the system can act more autonomously because every action that
                  runs has already passed a principled test.
                </p>
              </div>

              <div className="space-y-4">
                <div className="p-5 rounded-xl border border-[#1a1a1a]/[0.06] bg-[#1a1a1a]/[0.02]">
                  <div className="text-xs font-medium text-[#1a1a1a]/30 mb-2 uppercase tracking-wider">Without a judgment layer</div>
                  <p className="text-sm text-[#1a1a1a]/50 leading-relaxed">
                    Agent proposes → auto-executes or waits forever. Confidence and correctness
                    treated as the same thing. Autonomy means risk.
                  </p>
                </div>
                <div className="p-5 rounded-xl border border-[#1a1a1a]/[0.10] bg-[#1a1a1a]/[0.03]">
                  <div className="text-xs font-medium text-[#1a1a1a] mb-2 uppercase tracking-wider">With a judgment layer</div>
                  <p className="text-sm text-[#1a1a1a]/70 leading-relaxed">
                    Agent proposes → independent function evaluates against your declared intent
                    → executes if aligned, queues for your review if not. Autonomy becomes
                    trustworthy.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ─── vs. the landscape ─────────────────────────────────────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-16">
              <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
                An OS is not a chatbot.
              </h2>
              <p className="text-[#1a1a1a]/50 max-w-lg mx-auto">
                You already have great AI tools. Here&apos;s the structural difference.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="p-6 rounded-2xl bg-[#1a1a1a]/[0.02] border border-[#1a1a1a]/[0.06]">
                <div className="text-sm font-medium text-[#1a1a1a]/40 mb-3">vs ChatGPT / Claude</div>
                <p className="text-sm text-[#1a1a1a]/70 leading-relaxed">
                  Chat is a session. yarnnn is an operation. Sessions help in the moment
                  and reset when you close the tab. Operations keep running, keep accumulating,
                  and compound with every cycle.
                </p>
              </div>
              <div className="p-6 rounded-2xl bg-[#1a1a1a]/[0.02] border border-[#1a1a1a]/[0.06]">
                <div className="text-sm font-medium text-[#1a1a1a]/40 mb-3">vs cloud agent tools</div>
                <p className="text-sm text-[#1a1a1a]/70 leading-relaxed">
                  Generic agent services execute without domain context. yarnnn agents accumulate
                  expertise specific to your work. Three months of context can&apos;t be replicated
                  by starting over elsewhere.
                </p>
              </div>
              <div className="p-6 rounded-2xl bg-[#1a1a1a]/[0.02] border border-[#1a1a1a]/[0.06]">
                <div className="text-sm font-medium text-[#1a1a1a]/40 mb-3">vs self-hosted frameworks</div>
                <p className="text-sm text-[#1a1a1a]/70 leading-relaxed">
                  Self-hosted frameworks need server provisioning, API wiring, and ongoing
                  maintenance. yarnnn is a running operation from signup — your first agents
                  emerge within minutes of the first conversation.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ─── CTA ─────────────────────────────────────────────────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
              Start with one piece of work.
            </h2>
            <p className="text-[#1a1a1a]/50 mb-2">
              Describe it to YARNNN. Watch the agents it creates take over.
            </p>
            <p className="text-[#1a1a1a]/50 mb-10">
              Free to start. Pro at $19/mo for the full palette.
            </p>
            <Link
              href="/auth/login"
              className="inline-block px-8 py-4 bg-[#1a1a1a] text-white text-lg font-medium rounded-full hover:bg-[#1a1a1a]/90 transition-all"
            >
              Describe your work
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
