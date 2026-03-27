import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { AnimatedTimeline } from "@/components/landing/AnimatedTimeline";
import { SpotlightCard, BentoGrid } from "@/components/landing/SpotlightCard";
import { MockPDF, MockEmail, MockBrief } from "@/components/landing/MockOutputs";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata: Metadata = getMarketingMetadata({
  title: "How yarnnn works",
  description:
    "Sign up and your AI workforce is ready. Assign tasks to specialist agents — Research, Content, Marketing, CRM. They execute on schedule and learn from your feedback.",
  path: "/how-it-works",
  keywords: [
    "how yarnnn works",
    "autonomous ai workflow",
    "ai agent task automation",
    "ai agents",
    "ai workforce",
    "ai employee",
    "slack ai summary",
    "notion ai summary",
  ],
});

export default function HowItWorksPage() {
  const howToSchema = {
    "@context": "https://schema.org",
    "@type": "HowTo",
    name: "How yarnnn autonomous agents work",
    description: metadata.description,
    url: `${BRAND.url}/how-it-works`,
    step: [
      {
        "@type": "HowToStep",
        name: "Sign up and meet your pre-built AI team",
      },
      {
        "@type": "HowToStep",
        name: "Assign recurring tasks to specialist agents",
      },
      {
        "@type": "HowToStep",
        name: "Share context through conversation, documents, or connected tools",
      },
      {
        "@type": "HowToStep",
        name: "Review output and watch quality compound over time",
      },
    ],
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
            <p className="text-white/40 text-sm uppercase tracking-widest mb-4">How It Works</p>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-10 tracking-tight leading-[1.1]">
              Agents are who.
              <br />
              <span className="text-white/50">Tasks are what.</span>
            </h1>
            <p className="max-w-2xl text-white/50 text-lg">
              yarnnn gives you a team of specialist agents the moment you sign up.
              You assign recurring tasks — they execute on schedule, learn from your
              feedback, and deliver better output every cycle.
            </p>
          </section>

          {/* ─── Timeline overview ─────────────────────────────────────── */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <div className="text-center mb-16">
                <h2 className="text-2xl md:text-3xl font-medium mb-4">
                  Four steps. Then it runs itself.
                </h2>
                <p className="text-white/50 max-w-md mx-auto">
                  From sign-up to compounding output.
                </p>
              </div>

              <AnimatedTimeline
                variant="dark"
                steps={[
                  { number: "01", title: "Meet your team", description: "Sign up and your 6-agent roster is ready — 4 specialists and 2 platform bots." },
                  { number: "02", title: "Assign tasks", description: "Describe the work. yarnnn creates a task and assigns the right agent." },
                  { number: "03", title: "Share context", description: "Chat, upload docs, or connect Slack and Notion. Every source makes output richer." },
                  { number: "04", title: "Review & learn", description: "Edit or redirect. Feedback becomes learned preferences that compound every cycle." },
                ]}
              />
            </div>
          </section>

          {/* ─── Bento: Your team ──────────────────────────────────────── */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6 mb-12">
                <div className="text-4xl font-light text-white/20">01</div>
                <div>
                  <h2 className="text-2xl md:text-3xl font-medium mb-4">Meet your team</h2>
                  <p className="text-white/50 leading-relaxed max-w-2xl">
                    When you sign up, your workforce is already built. No setup, no configuration.
                  </p>
                </div>
              </div>

              <BentoGrid>
                {/* Large team card */}
                <SpotlightCard
                  variant="dark"
                  className="md:col-span-4 md:row-span-2"
                  spotlightColor="rgba(255,255,255,0.05)"
                >
                  <div className="p-6 md:p-8 h-full">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-4">Your roster</div>
                    <h3 className="text-xl font-medium mb-2">Six specialists, ready at sign-up</h3>
                    <p className="text-white/50 text-sm mb-8 max-w-md">
                      Four domain-cognitive agents that reason and accumulate expertise,
                      plus two platform bots that sync your tools.
                    </p>

                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      {([
                        { name: "Research", letter: "R", color: "#6366f1", desc: "Web research, intelligence" },
                        { name: "Content", letter: "C", color: "#0ea5e9", desc: "Drafts, reports, briefs" },
                        { name: "Marketing", letter: "M", color: "#f59e0b", desc: "Market signals, positioning" },
                        { name: "CRM", letter: "CR", color: "#10b981", desc: "Relationships, clients" },
                        { name: "Slack Bot", letter: "S", color: "#E01E5A", desc: "Channels & threads" },
                        { name: "Notion Bot", letter: "N", color: "#191919", desc: "Pages & databases" },
                      ] as const).map((agent) => (
                        <div key={agent.name} className="flex items-center gap-3 p-2 rounded-xl hover:bg-white/[0.03] transition-colors">
                          <div
                            className="w-9 h-9 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
                            style={{ backgroundColor: agent.color }}
                          >
                            {agent.letter}
                          </div>
                          <div className="min-w-0">
                            <div className="text-sm font-medium text-white truncate">{agent.name}</div>
                            <div className="text-[10px] text-white/40 truncate">{agent.desc}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </SpotlightCard>

                {/* Agent vs Bot explainer */}
                <SpotlightCard variant="dark" className="md:col-span-2" spotlightColor="rgba(99,102,241,0.05)">
                  <div className="p-6 h-full flex flex-col">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Two classes</div>
                    <div className="flex-1 space-y-4">
                      <div>
                        <div className="text-sm font-medium mb-1">Agents</div>
                        <p className="text-white/40 text-xs leading-relaxed">
                          Domain-cognitive. Reason across multiple steps. Accumulate expertise over time.
                        </p>
                      </div>
                      <div>
                        <div className="text-sm font-medium mb-1">Bots</div>
                        <p className="text-white/40 text-xs leading-relaxed">
                          Platform-mechanical. Scoped to one API. Activate when you connect a tool.
                        </p>
                      </div>
                    </div>
                  </div>
                </SpotlightCard>

                {/* Identity card */}
                <SpotlightCard variant="dark" className="md:col-span-2" spotlightColor="rgba(16,185,129,0.05)">
                  <div className="p-6 h-full flex flex-col justify-center">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Identity</div>
                    <h3 className="text-lg font-medium mb-2">Agents develop inward</h3>
                    <p className="text-white/40 text-xs leading-relaxed">
                      Your Research Agent becomes a better researcher — not a Content Agent.
                      Capabilities are fixed by type. Knowledge is what grows.
                    </p>
                  </div>
                </SpotlightCard>
              </BentoGrid>
            </div>
          </section>

          {/* ─── Tasks ─────────────────────────────────────────────────── */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6 mb-12">
                <div className="text-4xl font-light text-white/20">02</div>
                <div>
                  <h2 className="text-2xl md:text-3xl font-medium mb-4">Assign tasks</h2>
                  <p className="text-white/50 leading-relaxed max-w-2xl">
                    Describe what you need in plain language. yarnnn creates a task, assigns
                    it to the right agent, and sets the cadence.
                  </p>
                </div>
              </div>

              <BentoGrid>
                {/* Task example — large */}
                <SpotlightCard variant="dark" className="md:col-span-4" spotlightColor="rgba(14,165,233,0.05)">
                  <div className="p-6 md:p-8">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-4">Example task</div>
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-7 h-7 rounded-full bg-sky-500 flex items-center justify-center">
                        <span className="text-[9px] text-white font-bold">C</span>
                      </div>
                      <span className="text-lg font-medium">Weekly team recap</span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/[0.06] text-white/40 ml-auto">Recurring · Weekly</span>
                    </div>
                    <p className="text-white/50 text-sm leading-relaxed max-w-lg">
                      Slack Bot syncs your channels. Content Agent synthesizes highlights,
                      decisions, and action items. Delivered every Monday morning as a PDF.
                    </p>
                  </div>
                </SpotlightCard>

                {/* Three task mode cards */}
                <SpotlightCard variant="dark" className="md:col-span-2" spotlightColor="rgba(99,102,241,0.05)">
                  <div className="p-6 h-full">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Task modes</div>
                    <div className="space-y-4">
                      {([
                        { mode: "Recurring", desc: "Runs on cadence indefinitely — daily, weekly, monthly" },
                        { mode: "Goal", desc: "Bounded. Runs until success criteria are met" },
                        { mode: "Reactive", desc: "On-demand or event-triggered" },
                      ] as const).map((m) => (
                        <div key={m.mode}>
                          <div className="text-sm font-medium mb-0.5">{m.mode}</div>
                          <p className="text-white/40 text-xs leading-relaxed">{m.desc}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </SpotlightCard>

                {/* More task examples */}
                {([
                  { title: "Competitor intelligence", agent: "Research Agent", mode: "Recurring" },
                  { title: "Market research deep dive", agent: "Research Agent", mode: "Goal" },
                  { title: "Meeting prep brief", agent: "Content Agent", mode: "Reactive" },
                ] as const).map((task) => (
                  <SpotlightCard key={task.title} variant="dark" className="md:col-span-2">
                    <div className="p-5">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium">{task.title}</span>
                        <span className="text-[9px] px-2 py-0.5 rounded-full bg-white/[0.06] text-white/40">{task.mode}</span>
                      </div>
                      <p className="text-white/40 text-xs">{task.agent}</p>
                    </div>
                  </SpotlightCard>
                ))}
              </BentoGrid>
            </div>
          </section>

          {/* ─── Context ───────────────────────────────────────────────── */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6 mb-12">
                <div className="text-4xl font-light text-white/20">03</div>
                <div>
                  <h2 className="text-2xl md:text-3xl font-medium mb-4">Share context</h2>
                  <p className="text-white/50 leading-relaxed max-w-2xl">
                    Agents learn from everything you share. No source is required — each one
                    you add makes the output richer.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl">
                {([
                  { name: "Chat", desc: "Describe what matters through conversation" },
                  { name: "Docs", desc: "Upload files that agents reference" },
                  { name: "Slack", desc: "Channels, threads, conversations" },
                  { name: "Notion", desc: "Pages, databases, wikis" },
                ] as const).map((src) => (
                  <SpotlightCard key={src.name} variant="dark" spotlightSize={200} className="rounded-xl">
                    <div className="p-4 text-center">
                      <div className="text-lg font-medium mb-1">{src.name}</div>
                      <p className="text-white/40 text-xs">{src.desc}</p>
                    </div>
                  </SpotlightCard>
                ))}
              </div>

              <p className="text-white/30 text-xs mt-6 max-w-xl">
                No context source is required. Agents can start working immediately
                with just a conversation. Each source you add makes the output richer.
              </p>
            </div>
          </section>

          {/* ─── Review + Mock outputs ─────────────────────────────────── */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6 mb-12">
                <div className="text-4xl font-light text-white/20">04</div>
                <div>
                  <h2 className="text-2xl md:text-3xl font-medium mb-4">You review. They learn.</h2>
                  <p className="text-white/50 leading-relaxed max-w-2xl">
                    Agents produce finished deliverables — formatted, attributed, and delivered
                    on schedule. Edit what needs changing and your feedback becomes learned behavior.
                  </p>
                </div>
              </div>

              {/* Mock outputs */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 items-start mb-16">
                <MockPDF variant="dark" />
                <MockEmail variant="dark" />
                <MockBrief variant="dark" />
              </div>

              {/* Chat example */}
              <SpotlightCard variant="dark" spotlightSize={500} className="max-w-2xl">
                <div className="p-6">
                  <div className="text-xs text-white/30 uppercase tracking-wider mb-4">Feedback loop</div>
                  <div className="space-y-4">
                    <div className="flex justify-end">
                      <div className="bg-white/10 rounded-2xl rounded-br-sm px-4 py-3 max-w-[85%]">
                        <p className="text-white/90 text-sm">
                          The weekly recap is too long. Lead with risks and keep it under 500 words.
                        </p>
                      </div>
                    </div>
                    <div className="flex justify-start">
                      <div className="bg-white/[0.04] border border-white/10 rounded-2xl rounded-bl-sm px-4 py-3 max-w-[85%]">
                        <p className="text-white/70 text-sm">
                          Got it. I&apos;ll restructure to lead with risks and cap at 500 words.
                          This preference will carry forward to all future runs of this task.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </SpotlightCard>
            </div>
          </section>

          {/* ─── Multi-agent collab ────────────────────────────────────── */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">Agents collaborate on tasks</h2>
              <p className="text-white/50 leading-relaxed mb-12 max-w-2xl">
                Most tasks need one agent handling the full chain. For bigger jobs,
                multiple agents contribute domain expertise to a single task.
              </p>

              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6">
                  <div className="text-xs text-white/30 uppercase tracking-wider mb-6">Example: Weekly leadership brief</div>
                  <div className="space-y-4">
                    <div className="flex items-start gap-4">
                      <div className="w-7 h-7 rounded-full bg-indigo-500 flex items-center justify-center shrink-0">
                        <span className="text-[8px] text-white font-bold">R</span>
                      </div>
                      <p className="text-white/70 text-sm pt-1">Research Agent investigates competitor moves and market shifts</p>
                    </div>
                    <div className="flex items-start gap-4">
                      <div className="w-7 h-7 rounded-full bg-sky-500 flex items-center justify-center shrink-0">
                        <span className="text-[8px] text-white font-bold">C</span>
                      </div>
                      <p className="text-white/70 text-sm pt-1">Content Agent synthesizes Slack and Notion activity into highlights</p>
                    </div>
                    <div className="flex items-start gap-4 pt-2 border-t border-white/[0.06]">
                      <div className="w-7 h-7 rounded-full bg-white/[0.1] flex items-center justify-center shrink-0">
                        <span className="text-[8px] text-white/70 font-bold">→</span>
                      </div>
                      <p className="text-white text-sm font-medium pt-1">Task combines their work into one brief, delivered Monday 8 AM</p>
                    </div>
                  </div>
                </div>
              </SpotlightCard>
            </div>
          </section>

          {/* ─── What compounds ─────────────────────────────────────────── */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">Why it gets better, not stale</h2>
              <p className="text-white/50 leading-relaxed mb-12 max-w-2xl">
                Unlike chat tools that reset every session, yarnnn agents accumulate
                real understanding of your work.
              </p>

              <BentoGrid>
                <SpotlightCard variant="dark" className="md:col-span-3" spotlightColor="rgba(245,158,11,0.05)">
                  <div className="p-6">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Preferences</div>
                    <h3 className="text-base font-medium mb-2">Your structure, tone, emphasis</h3>
                    <p className="text-white/40 text-xs leading-relaxed">
                      Learned from your edits. Every correction teaches the agent what you actually want.
                    </p>
                  </div>
                </SpotlightCard>

                <SpotlightCard variant="dark" className="md:col-span-3" spotlightColor="rgba(14,165,233,0.05)">
                  <div className="p-6">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Patterns</div>
                    <h3 className="text-base font-medium mb-2">Cross-platform understanding</h3>
                    <p className="text-white/40 text-xs leading-relaxed">
                      Who talks to whom, what matters, what&apos;s stuck — built from weeks of Slack and Notion context.
                    </p>
                  </div>
                </SpotlightCard>

                <SpotlightCard variant="dark" className="md:col-span-3" spotlightColor="rgba(16,185,129,0.05)">
                  <div className="p-6">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Domain knowledge</div>
                    <h3 className="text-base font-medium mb-2">Research, competitors, team dynamics</h3>
                    <p className="text-white/40 text-xs leading-relaxed">
                      Accumulated findings that deepen with every task run. Can&apos;t be replicated by switching tools.
                    </p>
                  </div>
                </SpotlightCard>

                <SpotlightCard variant="dark" className="md:col-span-3" spotlightColor="rgba(99,102,241,0.05)">
                  <div className="p-6">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">History</div>
                    <h3 className="text-base font-medium mb-2">Every output feeds better output</h3>
                    <p className="text-white/40 text-xs leading-relaxed">
                      Task history, past deliverables, and feedback distillation compound into an irreplaceable context moat.
                    </p>
                  </div>
                </SpotlightCard>
              </BentoGrid>
            </div>
          </section>

          {/* ─── Example prompts ───────────────────────────────────────── */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">What people ask for</h2>
              <p className="text-white/50 leading-relaxed mb-12">
                Describe the task in plain language. yarnnn assigns the right agent and handles the rest.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {[
                  "Give me a weekly digest from #engineering and #product.",
                  "Every Friday, send leadership a status report as a PDF.",
                  "Track these three competitors and give me a weekly update.",
                  "Before my meetings, generate a prep brief from Slack and Notion.",
                  "Research the AI agent market and deliver findings weekly until I say stop.",
                  "Summarize my week across all platforms every Friday.",
                ].map((prompt) => (
                  <SpotlightCard key={prompt} variant="dark" spotlightSize={250} className="rounded-xl">
                    <div className="p-4">
                      <p className="text-white/70 text-sm italic">&ldquo;{prompt}&rdquo;</p>
                    </div>
                  </SpotlightCard>
                ))}
              </div>
            </div>
          </section>

          {/* ─── CTA ───────────────────────────────────────────────────── */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Your team is ready. Assign the first task.
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Sign up, meet your agents, and give them something to do. First output in minutes.
              </p>
              <Link
                href="/auth/login"
                className="inline-block px-8 py-4 bg-white text-black text-lg font-medium rounded-full hover:bg-white/90 transition-colors"
              >
                Meet your team
              </Link>
            </div>
          </section>
        </main>

        <LandingFooter inverted />
      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(howToSchema) }}
      />
    </div>
  );
}
