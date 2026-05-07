import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { SpotlightCard, BentoGrid } from "@/components/landing/SpotlightCard";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata: Metadata = getMarketingMetadata({
  title: "How yarnnn works",
  description:
    "Declare your intent. Create agents through conversation. The OS runs the operation. You supervise from the cockpit.",
  path: "/how-it-works",
  keywords: [
    "how yarnnn works",
    "autonomous ai workflow",
    "agent os",
    "agent operating system",
    "ai agents",
    "ai knowledge work",
    "recurring ai work",
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
      { "@type": "HowToStep", name: "Declare your intent — tell YARNNN what you're trying to accomplish" },
      { "@type": "HowToStep", name: "Agents are created through conversation, scoped to your domain" },
      { "@type": "HowToStep", name: "The operation runs — agents connect to tools and execute on schedule" },
      { "@type": "HowToStep", name: "You supervise from the cockpit — redirect, refine, and watch it compound" },
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
              Declare. Build.
              <br />
              <span className="text-white/50">Run. Supervise.</span>
            </h1>
            <p className="max-w-2xl text-white/50 text-lg">
              yarnnn is an operating system for recurring knowledge work. You declare
              what you&apos;re trying to accomplish. Agents are created around that intent through
              conversation. The OS runs the operation — scheduled, connected, accumulating.
              You supervise from the cockpit.
            </p>
          </section>

          {/* ─── The operating model ──────────────────────────────────────── */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6 mb-16">
                <div className="text-4xl font-light text-white/10">00</div>
                <div>
                  <h2 className="text-2xl md:text-3xl font-medium mb-4">The operating model</h2>
                  <p className="text-white/50 leading-relaxed max-w-2xl">
                    Every yarnnn workspace runs as an operation, not a series of queries.
                    Three layers make it work.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <SpotlightCard variant="dark" spotlightColor="rgba(99,102,241,0.05)">
                  <div className="p-6 h-full">
                    <div className="text-xs font-mono text-white/30 uppercase tracking-wider mb-4">Kernel</div>
                    <h3 className="text-base font-medium mb-3">The kernel runs it</h3>
                    <p className="text-white/40 text-sm leading-relaxed">
                      Scheduled recurrences, platform connections, and deterministic pipelines
                      execute without you present. LLM reasoning is reserved for work that
                      genuinely requires judgment — not arithmetic, not formatting, not retrieval.
                    </p>
                  </div>
                </SpotlightCard>
                <SpotlightCard variant="dark" spotlightColor="rgba(14,165,233,0.05)">
                  <div className="p-6 h-full">
                    <div className="text-xs font-mono text-white/30 uppercase tracking-wider mb-4">Substrate</div>
                    <h3 className="text-base font-medium mb-3">The substrate accumulates</h3>
                    <p className="text-white/40 text-sm leading-relaxed">
                      Your workspace is the persistent memory of the operation — tool context,
                      prior outputs, preferences from your edits, domain knowledge from every
                      run. The substrate is what makes Day 90 different from Day 1.
                    </p>
                  </div>
                </SpotlightCard>
                <SpotlightCard variant="dark" spotlightColor="rgba(245,158,11,0.05)">
                  <div className="p-6 h-full">
                    <div className="text-xs font-mono text-white/30 uppercase tracking-wider mb-4">Judgment</div>
                    <h3 className="text-base font-medium mb-3">Judgment is independent</h3>
                    <p className="text-white/40 text-sm leading-relaxed">
                      What agents want to do and whether they should are two separate questions.
                      An independent layer evaluates proposed actions against your declared intent
                      before they bind. Autonomy that you can actually trust.
                    </p>
                  </div>
                </SpotlightCard>
              </div>
            </div>
          </section>

          {/* ─── Step 01: Declare ─────────────────────────────────────────── */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6 mb-12">
                <div className="text-4xl font-light text-white/20">01</div>
                <div>
                  <h2 className="text-2xl md:text-3xl font-medium mb-4">Declare your intent</h2>
                  <p className="text-white/50 leading-relaxed max-w-2xl">
                    Tell YARNNN what you&apos;re trying to accomplish — a domain you want to track,
                    a recurring deliverable you want produced, an operation you want running.
                    Plain language. No configuration forms.
                  </p>
                </div>
              </div>

              <BentoGrid>
                <SpotlightCard variant="dark" className="md:col-span-4" spotlightColor="rgba(99,102,241,0.05)">
                  <div className="p-6 md:p-8">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-4">In conversation</div>
                    <div className="space-y-4 max-w-lg">
                      <div className="flex justify-end">
                        <div className="bg-white/10 rounded-2xl rounded-br-sm px-4 py-3 max-w-[85%]">
                          <p className="text-white/90 text-sm">
                            I want a weekly competitive intelligence brief. Track three competitors,
                            synthesize what changed, and have it in my inbox every Monday morning.
                          </p>
                        </div>
                      </div>
                      <div className="flex justify-start">
                        <div className="bg-white/[0.04] border border-white/10 rounded-2xl rounded-bl-sm px-4 py-3 max-w-[85%]">
                          <p className="text-white/70 text-sm">
                            Got it. I&apos;ll create a Researcher scoped to competitive intelligence
                            and a Writer for the brief. Once you confirm, I&apos;ll set it to run
                            every Sunday evening so you have it Monday morning.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </SpotlightCard>

                <SpotlightCard variant="dark" className="md:col-span-2" spotlightColor="rgba(245,158,11,0.05)">
                  <div className="p-6 h-full flex flex-col">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">The mandate</div>
                    <h3 className="text-base font-medium mb-2">What you&apos;re trying to accomplish</h3>
                    <p className="text-white/40 text-xs leading-relaxed flex-1">
                      Your declared intent is the north star the system reasons against.
                      Agents evaluate their own output against it. The judgment layer evaluates
                      proposed actions against it. The operation is always trying to serve it.
                    </p>
                  </div>
                </SpotlightCard>

                <SpotlightCard variant="dark" className="md:col-span-2" spotlightColor="rgba(16,185,129,0.05)">
                  <div className="p-6 h-full flex flex-col">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Task shapes</div>
                    <div className="space-y-3 flex-1">
                      {([
                        { mode: "Recurring", desc: "Runs on cadence indefinitely" },
                        { mode: "Goal-bound", desc: "Runs until success criteria are met" },
                        { mode: "Reactive", desc: "Fires on event or on-demand" },
                      ] as const).map((m) => (
                        <div key={m.mode}>
                          <div className="text-sm font-medium mb-0.5">{m.mode}</div>
                          <p className="text-white/40 text-xs leading-relaxed">{m.desc}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </SpotlightCard>
              </BentoGrid>
            </div>
          </section>

          {/* ─── Step 02: Build ───────────────────────────────────────────── */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6 mb-12">
                <div className="text-4xl font-light text-white/20">02</div>
                <div>
                  <h2 className="text-2xl md:text-3xl font-medium mb-4">Agents are created through conversation</h2>
                  <p className="text-white/50 leading-relaxed max-w-2xl">
                    You don&apos;t pick from a catalog. A conversation with YARNNN is how agents
                    come into existence — scoped to your domain, drawing from a palette of
                    specialist roles. The team is authored, not provisioned.
                  </p>
                </div>
              </div>

              <BentoGrid>
                {/* The palette — large */}
                <SpotlightCard
                  variant="dark"
                  className="md:col-span-4 md:row-span-2"
                  spotlightColor="rgba(255,255,255,0.03)"
                >
                  <div className="p-6 md:p-8 h-full">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-4">The specialist palette</div>
                    <h3 className="text-xl font-medium mb-2">Six roles. Your agents are built from them.</h3>
                    <p className="text-white/50 text-sm mb-8 max-w-md">
                      YARNNN drafts specialist combinations per task from a universal palette.
                      Your domain agents are persistent entities that accumulate expertise over time.
                    </p>

                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      {([
                        { name: "Researcher", letter: "R", color: "#6366f1", desc: "Finds and evaluates sources" },
                        { name: "Analyst", letter: "A", color: "#0ea5e9", desc: "Synthesizes patterns and meaning" },
                        { name: "Writer", letter: "W", color: "#10b981", desc: "Drafts polished deliverables" },
                        { name: "Tracker", letter: "T", color: "#f59e0b", desc: "Monitors signals and changes" },
                        { name: "Designer", letter: "D", color: "#ef4444", desc: "Creates charts, images & visuals" },
                        { name: "Slack", letter: "S", color: "#E01E5A", desc: "Reads your channels & threads" },
                        { name: "Notion", letter: "N", color: "#191919", desc: "Reads your pages & databases" },
                        { name: "GitHub", letter: "G", color: "#111827", desc: "Follows repos & activity" },
                        { name: "YARNNN", letter: "Y", color: "#374151", desc: "The orchestrator you talk to" },
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

                {/* Authorship card */}
                <SpotlightCard variant="dark" className="md:col-span-2" spotlightColor="rgba(99,102,241,0.05)">
                  <div className="p-6 h-full flex flex-col">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Authorship</div>
                    <h3 className="text-base font-medium mb-2">The team is yours. Built over time.</h3>
                    <p className="text-white/40 text-xs leading-relaxed flex-1">
                      Each agent accumulates domain knowledge, learned preferences, and output
                      history specific to your work. The switching cost begins with the first one.
                    </p>
                  </div>
                </SpotlightCard>

                {/* Context sources card */}
                <SpotlightCard variant="dark" className="md:col-span-2" spotlightColor="rgba(16,185,129,0.05)">
                  <div className="p-6 h-full flex flex-col">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Context sources</div>
                    <div className="grid grid-cols-2 gap-2 flex-1">
                      {([
                        { name: "Chat", desc: "Describe what matters" },
                        { name: "Docs", desc: "Upload files agents reference" },
                        { name: "Slack", desc: "Channels and threads" },
                        { name: "Notion", desc: "Pages and databases" },
                      ] as const).map((src) => (
                        <div key={src.name} className="p-3 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                          <div className="text-sm font-medium mb-0.5">{src.name}</div>
                          <p className="text-white/40 text-[10px]">{src.desc}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </SpotlightCard>
              </BentoGrid>
            </div>
          </section>

          {/* ─── Step 03: Run ─────────────────────────────────────────────── */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6 mb-12">
                <div className="text-4xl font-light text-white/20">03</div>
                <div>
                  <h2 className="text-2xl md:text-3xl font-medium mb-4">The operation runs</h2>
                  <p className="text-white/50 leading-relaxed max-w-2xl">
                    Agents connect to your tools, execute on schedule, and accumulate context
                    from every cycle — whether you&apos;re online or not. The kernel handles what&apos;s
                    deterministic. LLM judgment handles what actually requires reasoning.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                {([
                  {
                    title: "Scheduled execution",
                    desc: "Daily, weekly, monthly — or event-triggered. Tasks run on cadence without you initiating them.",
                  },
                  {
                    title: "Platform-connected",
                    desc: "Agents read fresh context from Slack, Notion, and GitHub every cycle. The substrate stays current.",
                  },
                  {
                    title: "Accumulating",
                    desc: "Prior outputs feed future ones. Domain knowledge deepens with every run. The team gets better at its job.",
                  },
                ] as const).map((item) => (
                  <SpotlightCard key={item.title} variant="dark" spotlightSize={250}>
                    <div className="p-6">
                      <h3 className="text-base font-medium mb-2">{item.title}</h3>
                      <p className="text-white/40 text-sm leading-relaxed">{item.desc}</p>
                    </div>
                  </SpotlightCard>
                ))}
              </div>

              <div className="mt-8">
                <SpotlightCard variant="dark" spotlightSize={500} className="max-w-2xl">
                  <div className="p-6">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-4">Multi-agent example</div>
                    <div className="space-y-4">
                      <div className="flex items-start gap-4">
                        <div className="w-7 h-7 rounded-full bg-pink-500 flex items-center justify-center shrink-0">
                          <span className="text-[8px] text-white font-bold">S</span>
                        </div>
                        <p className="text-white/70 text-sm pt-1">Slack connector keeps fresh internal context available each cycle</p>
                      </div>
                      <div className="flex items-start gap-4">
                        <div className="w-7 h-7 rounded-full bg-indigo-500 flex items-center justify-center shrink-0">
                          <span className="text-[8px] text-white font-bold">R</span>
                        </div>
                        <p className="text-white/70 text-sm pt-1">Researcher adds external signals and market movements</p>
                      </div>
                      <div className="flex items-start gap-4">
                        <div className="w-7 h-7 rounded-full bg-emerald-500 flex items-center justify-center shrink-0">
                          <span className="text-[8px] text-white font-bold">W</span>
                        </div>
                        <p className="text-white/70 text-sm pt-1">Writer synthesizes both into a finished brief</p>
                      </div>
                      <div className="flex items-start gap-4 pt-2 border-t border-white/[0.06]">
                        <div className="w-7 h-7 rounded-full bg-white/[0.1] flex items-center justify-center shrink-0">
                          <span className="text-[8px] text-white/70 font-bold">→</span>
                        </div>
                        <p className="text-white text-sm font-medium pt-1">Delivered Monday 8 AM. Every week.</p>
                      </div>
                    </div>
                  </div>
                </SpotlightCard>
              </div>
            </div>
          </section>

          {/* ─── Step 04: Supervise ───────────────────────────────────────── */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6 mb-12">
                <div className="text-4xl font-light text-white/20">04</div>
                <div>
                  <h2 className="text-2xl md:text-3xl font-medium mb-4">You supervise from the cockpit</h2>
                  <p className="text-white/50 leading-relaxed max-w-2xl">
                    Review what ran, redirect what needs changing, and watch the operation compound
                    over time. You work inside yarnnn — not consuming reports elsewhere. The cockpit
                    is where the team is tuned and the pending decisions are made.
                  </p>
                </div>
              </div>

              <BentoGrid>
                <SpotlightCard variant="dark" className="md:col-span-3" spotlightColor="rgba(245,158,11,0.05)">
                  <div className="p-6">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Feedback loop</div>
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
                            Got it. Updated to lead with risks, capped at 500 words. That preference
                            carries forward to every future run.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </SpotlightCard>

                <SpotlightCard variant="dark" className="md:col-span-3" spotlightColor="rgba(99,102,241,0.05)">
                  <div className="p-6">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">The cockpit</div>
                    <div className="space-y-3">
                      {([
                        { label: "Overview", desc: "What's happening and what needs you" },
                        { label: "Agents", desc: "Your team — identity, health, accumulated expertise" },
                        { label: "Work", desc: "What's running, what's produced, what's scheduled" },
                        { label: "Context", desc: "What the workspace knows — accumulated and searchable" },
                        { label: "Review", desc: "Proposed actions and the judgment trail" },
                      ] as const).map((item) => (
                        <div key={item.label} className="flex items-center gap-3">
                          <span className="text-sm font-medium text-white w-20 shrink-0">{item.label}</span>
                          <span className="text-white/40 text-xs">{item.desc}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </SpotlightCard>
              </BentoGrid>
            </div>
          </section>

          {/* ─── The judgment layer ───────────────────────────────────────── */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <div className="text-sm text-white/30 mb-4 font-mono uppercase tracking-wider">Independent review</div>
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Agents propose.
                <br />
                <span className="text-white/50">A separate layer judges.</span>
              </h2>
              <p className="text-white/50 leading-relaxed mb-12 max-w-2xl">
                What your agents want to do and whether they should do it are two separate
                questions — answered by two different layers. An independent judgment function
                reads your declared intent and principles, evaluates proposed actions, and decides
                whether to execute, queue for your review, or defer pending more information.
                This is what makes higher autonomy trustworthy rather than reckless.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <SpotlightCard variant="dark" spotlightSize={250}>
                  <div className="p-6">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Approve</div>
                    <p className="text-white/60 text-sm leading-relaxed">
                      If the proposed action aligns with your declared intent and falls within
                      your delegated autonomy ceiling — the action executes. No manual approval needed.
                    </p>
                  </div>
                </SpotlightCard>
                <SpotlightCard variant="dark" spotlightSize={250}>
                  <div className="p-6">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Queue</div>
                    <p className="text-white/60 text-sm leading-relaxed">
                      If the action exceeds your autonomy ceiling or the judgment layer isn&apos;t
                      confident, it surfaces in your review queue. You decide.
                    </p>
                  </div>
                </SpotlightCard>
                <SpotlightCard variant="dark" spotlightSize={250}>
                  <div className="p-6">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Defer</div>
                    <p className="text-white/60 text-sm leading-relaxed">
                      If the proposal has an evidence gap, the judgment layer commissions the
                      missing research before deciding. It doesn&apos;t guess.
                    </p>
                  </div>
                </SpotlightCard>
              </div>
            </div>
          </section>

          {/* ─── What compounds ─────────────────────────────────────────── */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">Why it gets better, not stale</h2>
              <p className="text-white/50 leading-relaxed mb-12 max-w-2xl">
                The substrate is the moat. Not the model underneath — that&apos;s becoming a
                commodity. What accumulates in your workspace is what can&apos;t be replicated
                by starting over.
              </p>

              <BentoGrid>
                <SpotlightCard variant="dark" className="md:col-span-3" spotlightColor="rgba(245,158,11,0.05)">
                  <div className="p-6">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Preferences</div>
                    <h3 className="text-base font-medium mb-2">Your structure, tone, emphasis</h3>
                    <p className="text-white/40 text-xs leading-relaxed">
                      Learned from your edits. Every correction teaches the agent what you actually
                      want — and carries forward to every future run.
                    </p>
                  </div>
                </SpotlightCard>

                <SpotlightCard variant="dark" className="md:col-span-3" spotlightColor="rgba(14,165,233,0.05)">
                  <div className="p-6">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Domain knowledge</div>
                    <h3 className="text-base font-medium mb-2">Research, patterns, and relationships</h3>
                    <p className="text-white/40 text-xs leading-relaxed">
                      Accumulated findings from every task run — competitors, market signals,
                      team dynamics. Can&apos;t be replicated by switching tools.
                    </p>
                  </div>
                </SpotlightCard>

                <SpotlightCard variant="dark" className="md:col-span-3" spotlightColor="rgba(16,185,129,0.05)">
                  <div className="p-6">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Output history</div>
                    <h3 className="text-base font-medium mb-2">Prior outputs feed better future outputs</h3>
                    <p className="text-white/40 text-xs leading-relaxed">
                      Three months of accumulated work means every new output builds on
                      everything that came before. The team compounds.
                    </p>
                  </div>
                </SpotlightCard>

                <SpotlightCard variant="dark" className="md:col-span-3" spotlightColor="rgba(99,102,241,0.05)">
                  <div className="p-6">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Platform context</div>
                    <h3 className="text-base font-medium mb-2">Fresh material every cycle</h3>
                    <p className="text-white/40 text-xs leading-relaxed">
                      Slack, Notion, and GitHub keep the workspace current. Agents always work
                      from what&apos;s actually happening, not a stale snapshot.
                    </p>
                  </div>
                </SpotlightCard>
              </BentoGrid>
            </div>
          </section>

          {/* ─── Example prompts ───────────────────────────────────────────── */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">What people describe</h2>
              <p className="text-white/50 leading-relaxed mb-12">
                Describe the work to YARNNN in plain language. It creates the agents and sets the operation.
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

          {/* ─── CTA ───────────────────────────────────────────────────────── */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Start with one piece of work.
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Describe it to YARNNN. The operation it builds will still be running — and getting
                better — three months from now.
              </p>
              <Link
                href="/auth/login"
                className="inline-block px-8 py-4 bg-white text-black text-lg font-medium rounded-full hover:bg-white/90 transition-colors"
              >
                Describe your work
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
