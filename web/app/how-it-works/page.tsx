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
    "Connect workspace context, define recurring tasks, and let persistent agents execute on schedule. Thinking Partner orchestrates and feedback compounds over time.",
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
        name: "Connect workspace context",
      },
      {
        "@type": "HowToStep",
        name: "Define recurring tasks with Thinking Partner",
      },
      {
        "@type": "HowToStep",
        name: "Let persistent agents execute and deliver",
      },
      {
        "@type": "HowToStep",
        name: "Review output and let feedback compound over time",
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
              Shared context.
              <br />
              <span className="text-white/50">Persistent agents. Recurring tasks.</span>
            </h1>
            <p className="max-w-2xl text-white/50 text-lg">
              yarnnn keeps workspace context, a scaffolded workforce, and recurring
              task execution inside one system. TP orchestrates. Domain agents deepen.
              Your feedback compounds instead of resetting every session.
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
                  From first context to a running system.
                </p>
              </div>

              <AnimatedTimeline
                variant="dark"
                steps={[
                  { number: "01", title: "Accumulate context", description: "Connect tools, upload docs, or start from chat. The workspace becomes the shared operating substrate." },
                  { number: "02", title: "Define tasks", description: "Describe recurring work in plain language. TP turns it into a standing task definition." },
                  { number: "03", title: "Agents execute", description: "Persistent agents run tasks on schedule, gather context, and deliver outputs." },
                  { number: "04", title: "Supervise & compound", description: "Review what changed. Feedback sharpens future runs instead of disappearing." },
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
                  <h2 className="text-2xl md:text-3xl font-medium mb-4">A workforce is scaffolded at signup</h2>
                  <p className="text-white/50 leading-relaxed max-w-2xl">
                    The system does not start empty. Domain agents, platform bots,
                    Reporting, and TP are scaffolded from day one.
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
                    <h3 className="text-xl font-medium mb-2">Ten agents across four classes</h3>
                    <p className="text-white/50 text-sm mb-8 max-w-md">
                      Five domain stewards, one reporting synthesizer, three platform
                      bots, and Thinking Partner as the meta-cognitive agent.
                    </p>

                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      {([
                        { name: "Competitive Intel", letter: "CI", color: "#6366f1", desc: "Competitors, external signals" },
                        { name: "Market Research", letter: "MR", color: "#0ea5e9", desc: "Research, market context" },
                        { name: "Business Dev", letter: "BD", color: "#10b981", desc: "Relationships, opportunities" },
                        { name: "Operations", letter: "OP", color: "#f59e0b", desc: "Process, operational health" },
                        { name: "Marketing", letter: "M", color: "#ef4444", desc: "Positioning, creative context" },
                        { name: "Reporting", letter: "RP", color: "#8b5cf6", desc: "Cross-domain synthesis" },
                        { name: "Slack Bot", letter: "S", color: "#E01E5A", desc: "Channels & threads" },
                        { name: "Notion Bot", letter: "N", color: "#191919", desc: "Pages & databases" },
                        { name: "GitHub Bot", letter: "G", color: "#111827", desc: "Repos & code context" },
                        { name: "Thinking Partner", letter: "TP", color: "#374151", desc: "System orchestration" },
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
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Four classes</div>
                    <div className="flex-1 space-y-4">
                      <div>
                        <div className="text-sm font-medium mb-1">Domain stewards</div>
                        <p className="text-white/40 text-xs leading-relaxed">
                          Specialists that keep a context domain fresh and useful over time.
                        </p>
                      </div>
                      <div>
                        <div className="text-sm font-medium mb-1">Reporting</div>
                        <p className="text-white/40 text-xs leading-relaxed">
                          The synthesizer that turns multiple inputs into one deliverable.
                        </p>
                      </div>
                      <div>
                        <div className="text-sm font-medium mb-1">Platform bots</div>
                        <p className="text-white/40 text-xs leading-relaxed">
                          Platform-shaped specialists for Slack, Notion, and GitHub context.
                        </p>
                      </div>
                      <div>
                        <div className="text-sm font-medium mb-1">Thinking Partner</div>
                        <p className="text-white/40 text-xs leading-relaxed">
                          The meta-cognitive agent that manages tasks, explains behavior, and keeps the system coherent.
                        </p>
                      </div>
                    </div>
                  </div>
                </SpotlightCard>

                {/* Identity card */}
                <SpotlightCard variant="dark" className="md:col-span-2" spotlightColor="rgba(16,185,129,0.05)">
                  <div className="p-6 h-full flex flex-col justify-center">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Identity</div>
                    <h3 className="text-lg font-medium mb-2">Agents deepen. TP orchestrates.</h3>
                    <p className="text-white/40 text-xs leading-relaxed">
                      Capability breadth is stable. Knowledge and judgment are what
                      compound with tenure and repeated work.
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
                    Describe what you need in plain language. TP turns that into a
                    task definition with objective, cadence, delivery, and assignment.
                  </p>
                </div>
              </div>

              <BentoGrid>
                {/* Task example — large */}
                <SpotlightCard variant="dark" className="md:col-span-4" spotlightColor="rgba(14,165,233,0.05)">
                  <div className="p-6 md:p-8">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-4">Example task</div>
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-7 h-7 rounded-full bg-violet-500 flex items-center justify-center">
                        <span className="text-[9px] text-white font-bold">RP</span>
                      </div>
                      <span className="text-lg font-medium">Weekly leadership brief</span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/[0.06] text-white/40 ml-auto">Recurring · Weekly</span>
                    </div>
                    <p className="text-white/50 text-sm leading-relaxed max-w-lg">
                      Slack and Notion keep the workspace fresh. Reporting assembles the
                      week's changes, decisions, and risks into one Monday morning brief.
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
                  { title: "Competitor intelligence brief", agent: "Competitive Intelligence", mode: "Recurring" },
                  { title: "Market research deep dive", agent: "Market Research", mode: "Goal" },
                  { title: "Meeting prep brief", agent: "Reporting", mode: "Reactive" },
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
                    The workspace is the shared substrate. Every source you add gives
                    TP and the agents more grounded material to work with.
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
                No one source is required. The system can start from conversation
                alone, then get more grounded as documents and connected tools accumulate.
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
                          Got it. I&apos;ll update this task to lead with risks and cap
                          at 500 words. That preference will carry forward to future runs.
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
                      <div className="w-7 h-7 rounded-full bg-pink-500 flex items-center justify-center shrink-0">
                        <span className="text-[8px] text-white font-bold">S</span>
                      </div>
                      <p className="text-white/70 text-sm pt-1">Slack Bot keeps fresh internal discussion and decision context available</p>
                    </div>
                    <div className="flex items-start gap-4">
                      <div className="w-7 h-7 rounded-full bg-indigo-500 flex items-center justify-center shrink-0">
                        <span className="text-[8px] text-white font-bold">CI</span>
                      </div>
                      <p className="text-white/70 text-sm pt-1">Competitive Intelligence adds external moves and market shifts</p>
                    </div>
                    <div className="flex items-start gap-4">
                      <div className="w-7 h-7 rounded-full bg-violet-500 flex items-center justify-center shrink-0">
                        <span className="text-[8px] text-white font-bold">RP</span>
                      </div>
                      <p className="text-white/70 text-sm pt-1">Reporting synthesizes it into one brief for leadership</p>
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
                    <h3 className="text-base font-medium mb-2">Shared workspace context</h3>
                    <p className="text-white/40 text-xs leading-relaxed">
                      Fresh material from tools, files, and prior outputs keeps every task grounded instead of cold-started.
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
                Start with one task.
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Sign up, connect context, and let TP set the first recurring loop in motion.
              </p>
              <Link
                href="/auth/login"
                className="inline-block px-8 py-4 bg-white text-black text-lg font-medium rounded-full hover:bg-white/90 transition-colors"
              >
                Start free
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
