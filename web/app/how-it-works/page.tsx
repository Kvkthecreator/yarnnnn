import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
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
        name: "Connect Slack or Notion to enrich agent context",
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

          {/* Step 1: Meet your team */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6 mb-16">
                <div className="text-4xl font-light text-white/20">01</div>
                <div>
                  <h2 className="text-2xl md:text-3xl font-medium mb-4">Meet your team</h2>
                  <p className="text-white/50 leading-relaxed max-w-2xl mb-8">
                    When you sign up, your workforce is already built — four specialist agents
                    and two platform bots. No setup, no configuration. They&apos;re ready to take
                    on work immediately.
                  </p>

                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 max-w-2xl">
                    <div className="border border-white/10 rounded-xl p-4">
                      <div className="text-xs text-white/30 uppercase tracking-wider mb-2">Agent</div>
                      <div className="text-sm font-medium">Research</div>
                      <p className="text-white/40 text-xs mt-1">Web research, intelligence, monitoring</p>
                    </div>
                    <div className="border border-white/10 rounded-xl p-4">
                      <div className="text-xs text-white/30 uppercase tracking-wider mb-2">Agent</div>
                      <div className="text-sm font-medium">Content</div>
                      <p className="text-white/40 text-xs mt-1">Drafts, reports, briefs, summaries</p>
                    </div>
                    <div className="border border-white/10 rounded-xl p-4">
                      <div className="text-xs text-white/30 uppercase tracking-wider mb-2">Agent</div>
                      <div className="text-sm font-medium">Marketing</div>
                      <p className="text-white/40 text-xs mt-1">Market signals, positioning, campaigns</p>
                    </div>
                    <div className="border border-white/10 rounded-xl p-4">
                      <div className="text-xs text-white/30 uppercase tracking-wider mb-2">Agent</div>
                      <div className="text-sm font-medium">CRM</div>
                      <p className="text-white/40 text-xs mt-1">Relationships, clients, stakeholders</p>
                    </div>
                    <div className="border border-white/10 rounded-xl p-4">
                      <div className="text-xs text-white/30 uppercase tracking-wider mb-2">Bot</div>
                      <div className="text-sm font-medium">Slack</div>
                      <p className="text-white/40 text-xs mt-1">Channels &amp; threads</p>
                    </div>
                    <div className="border border-white/10 rounded-xl p-4">
                      <div className="text-xs text-white/30 uppercase tracking-wider mb-2">Bot</div>
                      <div className="text-sm font-medium">Notion</div>
                      <p className="text-white/40 text-xs mt-1">Pages &amp; databases</p>
                    </div>
                  </div>

                  <p className="text-white/30 text-xs mt-6 max-w-xl">
                    Agents are domain-cognitive — they reason across multiple steps and accumulate
                    expertise. Bots are platform-mechanical — they read and write to one platform.
                    Together, they form your workforce.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Step 2: Assign tasks */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6 mb-16">
                <div className="text-4xl font-light text-white/20">02</div>
                <div>
                  <h2 className="text-2xl md:text-3xl font-medium mb-4">Assign tasks</h2>
                  <p className="text-white/50 leading-relaxed max-w-2xl mb-8">
                    Describe what you need in plain language. yarnnn creates a task, assigns
                    it to the right agent, and sets the cadence. Each task defines the work —
                    objective, schedule, delivery format, and success criteria.
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="border border-white/10 rounded-xl p-6">
                      <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Recurring task</div>
                      <div className="text-lg font-medium mb-3">Weekly team recap</div>
                      <p className="text-white/50 text-sm leading-relaxed">
                        Slack Bot syncs your channels. Content Agent synthesizes highlights,
                        decisions, and action items. Delivered every Monday morning.
                      </p>
                    </div>

                    <div className="border border-white/10 rounded-xl p-6">
                      <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Recurring task</div>
                      <div className="text-lg font-medium mb-3">Competitor intelligence</div>
                      <p className="text-white/50 text-sm leading-relaxed">
                        Research Agent monitors competitors weekly. Combines web research
                        with your internal context. Deepens with every cycle.
                      </p>
                    </div>

                    <div className="border border-white/10 rounded-xl p-6">
                      <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Goal task</div>
                      <div className="text-lg font-medium mb-3">Market research deep dive</div>
                      <p className="text-white/50 text-sm leading-relaxed">
                        Research Agent investigates a topic across cycles, building depth
                        until the deliverable meets your success criteria.
                      </p>
                    </div>

                    <div className="border border-white/10 rounded-xl p-6">
                      <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Reactive task</div>
                      <div className="text-lg font-medium mb-3">Meeting prep brief</div>
                      <p className="text-white/50 text-sm leading-relaxed">
                        On-demand. Content Agent pulls context from Slack and Notion
                        into a 2-minute briefing before any key meeting.
                      </p>
                    </div>
                  </div>

                  <p className="text-white/30 text-xs mt-6 max-w-xl">
                    Three task modes: <strong className="text-white/50">recurring</strong> (runs on cadence indefinitely),{" "}
                    <strong className="text-white/50">goal</strong> (bounded, completes when done),{" "}
                    <strong className="text-white/50">reactive</strong> (on-demand or event-triggered).
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Step 3: Connect tools */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6 mb-16">
                <div className="text-4xl font-light text-white/20">03</div>
                <div>
                  <h2 className="text-2xl md:text-3xl font-medium mb-4">Connect your tools</h2>
                  <p className="text-white/50 leading-relaxed max-w-2xl mb-8">
                    Link Slack or Notion to give your agents real context. Bots activate
                    automatically and start syncing — your agents get eyes on your actual
                    work. You choose which channels or pages to include, or let yarnnn
                    figure it out.
                  </p>

                  <div className="grid grid-cols-2 gap-4 max-w-md">
                    <div className="border border-white/10 rounded-xl p-4 text-center">
                      <div className="text-lg font-medium mb-1">Slack</div>
                      <p className="text-white/40 text-xs">Channels, threads, conversations</p>
                    </div>
                    <div className="border border-white/10 rounded-xl p-4 text-center">
                      <div className="text-lg font-medium mb-1">Notion</div>
                      <p className="text-white/40 text-xs">Pages, databases, wikis</p>
                    </div>
                  </div>

                  <p className="text-white/30 text-xs mt-6 max-w-xl">
                    Platform connections enrich your agents&apos; context but aren&apos;t required
                    to start. Agents can work with web research and documents alone.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Step 4: Review */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6 mb-16">
                <div className="text-4xl font-light text-white/20">04</div>
                <div>
                  <h2 className="text-2xl md:text-3xl font-medium mb-4">You review. They learn.</h2>
                  <p className="text-white/50 leading-relaxed max-w-2xl mb-8">
                    Review task output, edit what needs changing, or redirect an agent&apos;s focus.
                    Your feedback teaches agents your preferred structure, tone, and priorities.
                    Every cycle produces better work than the last.
                  </p>

                  <div className="border border-white/10 rounded-2xl p-6 bg-white/5 max-w-2xl">
                    <div className="space-y-6">
                      <div className="flex justify-end">
                        <div className="bg-white/10 rounded-2xl rounded-br-sm px-4 py-3 max-w-[85%]">
                          <p className="text-white/90 text-sm">
                            The weekly recap is too long. Lead with risks and keep it under 500 words.
                          </p>
                        </div>
                      </div>

                      <div className="flex justify-start">
                        <div className="bg-white/5 border border-white/10 rounded-2xl rounded-bl-sm px-4 py-3 max-w-[85%]">
                          <p className="text-white/70 text-sm">
                            Got it. I&apos;ll restructure to lead with risks and cap at 500 words.
                            This preference will carry forward to all future runs of this task.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  <p className="text-white/30 text-xs mt-6 max-w-xl">
                    Talk to any agent directly. Your direction persists across sessions —
                    agents remember what you told them and apply it to every task they run.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Multi-agent */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">Agents collaborate on tasks</h2>
              <p className="text-white/50 leading-relaxed mb-12 max-w-2xl">
                Most tasks need one agent handling the full chain — sense context, reason
                about it, produce output. For bigger jobs, multiple agents contribute their
                domain expertise to a single task. You get a finished product, not fragments.
              </p>

              <div className="border border-white/10 rounded-xl p-6 bg-white/5">
                <div className="text-xs text-white/30 uppercase tracking-wider mb-6">Example: Weekly leadership brief</div>
                <div className="space-y-4">
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">Research Agent investigates competitor moves and market shifts</p>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">Content Agent synthesizes Slack and Notion activity into highlights</p>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/40 mt-2 shrink-0" />
                    <p className="text-white text-sm font-medium">Task combines their work into one brief, delivered Monday 8 AM</p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* What accumulates */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">Why it gets better, not stale</h2>
              <p className="text-white/50 leading-relaxed mb-12 max-w-2xl">
                Unlike chat tools that reset every session, yarnnn agents accumulate
                real understanding of your work across every task they run.
              </p>

              <div className="border border-white/10 rounded-xl p-6 bg-white/5">
                <div className="text-xs text-white/30 uppercase tracking-wider mb-6">What compounds over time</div>
                <div className="space-y-4">
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">Your preferred structure, tone, and what to emphasize — learned from your edits</p>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">Cross-platform patterns — who talks to whom, what matters, what&apos;s stuck</p>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">Domain knowledge — research findings, competitive landscape, team dynamics</p>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">Task history — every output feeds better future output</p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Example prompts */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">What people ask for</h2>
              <p className="text-white/50 leading-relaxed mb-12">
                Describe the task in plain language. yarnnn assigns the right agent and handles the rest.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Give me a weekly digest from #engineering and #product.&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Every Friday, send leadership a status report as a PDF.&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Track these three competitors and give me a weekly update.&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Before my meetings, generate a prep brief from Slack and Notion.&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Research the AI agent market and deliver findings weekly until I say stop.&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Summarize my week across all platforms every Friday.&rdquo;</p>
                </div>
              </div>
            </div>
          </section>

          {/* CTA */}
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
