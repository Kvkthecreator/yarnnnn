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
    "Connect your tools. yarnnn creates AI agents that do recurring work in the background — recaps, briefs, research, reports. You review. They learn.",
  path: "/how-it-works",
  keywords: [
    "how yarnnn works",
    "autonomous ai workflow",
    "agent automation",
    "ai agents",
    "ai employee",
    "slack ai summary",
    "gmail ai digest",
    "ai meeting prep",
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
        name: "Connect your tools — Slack, Gmail, Notion, or Calendar",
      },
      {
        "@type": "HowToStep",
        name: "yarnnn creates agents matched to your workflow",
      },
      {
        "@type": "HowToStep",
        name: "Agents deliver work on schedule",
      },
      {
        "@type": "HowToStep",
        name: "Review, refine, and watch quality compound",
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
              Connect once.
              <br />
              <span className="text-white/50">Wake up to finished work.</span>
            </h1>
            <p className="max-w-2xl text-white/50 text-lg">
              yarnnn connects to your work tools, creates agents that understand your context,
              and runs them on schedule. You supervise outcomes instead of doing the work yourself.
            </p>
          </section>

          {/* Step 1: Connect */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6 mb-16">
                <div className="text-4xl font-light text-white/20">01</div>
                <div>
                  <h2 className="text-2xl md:text-3xl font-medium mb-4">Connect your tools</h2>
                  <p className="text-white/50 leading-relaxed max-w-2xl mb-8">
                    Link Slack, Gmail, Notion, or Calendar. yarnnn immediately syncs your data
                    and creates your first agents — no setup required. You choose which channels,
                    labels, or pages to include. Or let yarnnn figure it out.
                  </p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="border border-white/10 rounded-xl p-4 text-center">
                      <div className="text-lg font-medium mb-1">Slack</div>
                      <p className="text-white/40 text-xs">Channels & threads</p>
                    </div>
                    <div className="border border-white/10 rounded-xl p-4 text-center">
                      <div className="text-lg font-medium mb-1">Gmail</div>
                      <p className="text-white/40 text-xs">Labels & threads</p>
                    </div>
                    <div className="border border-white/10 rounded-xl p-4 text-center">
                      <div className="text-lg font-medium mb-1">Notion</div>
                      <p className="text-white/40 text-xs">Pages & databases</p>
                    </div>
                    <div className="border border-white/10 rounded-xl p-4 text-center">
                      <div className="text-lg font-medium mb-1">Calendar</div>
                      <p className="text-white/40 text-xs">All events</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Step 2: Agents work */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6 mb-16">
                <div className="text-4xl font-light text-white/20">02</div>
                <div>
                  <h2 className="text-2xl md:text-3xl font-medium mb-4">Agents do the recurring work</h2>
                  <p className="text-white/50 leading-relaxed max-w-2xl mb-8">
                    Each agent has a job and runs on schedule. You can create them through
                    conversation or let yarnnn create them automatically when you connect a platform.
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="border border-white/10 rounded-xl p-6">
                      <div className="text-lg font-medium mb-3">Weekly updates</div>
                      <p className="text-white/50 text-sm leading-relaxed">
                        Summaries of Slack channels, Gmail labels, or Notion pages.
                        Delivered on your schedule with highlights, decisions, and action items.
                      </p>
                    </div>

                    <div className="border border-white/10 rounded-xl p-6">
                      <div className="text-lg font-medium mb-3">Meeting prep</div>
                      <p className="text-white/50 text-sm leading-relaxed">
                        Before each meeting, yarnnn pulls relevant context from email,
                        Slack, and docs into a briefing you can skim in 2 minutes.
                      </p>
                    </div>

                    <div className="border border-white/10 rounded-xl p-6">
                      <div className="text-lg font-medium mb-3">Research & monitoring</div>
                      <p className="text-white/50 text-sm leading-relaxed">
                        Track competitors, topics, or trends. Combines your internal context
                        with web research and deepens with each cycle.
                      </p>
                    </div>

                    <div className="border border-white/10 rounded-xl p-6">
                      <div className="text-lg font-medium mb-3">Cross-platform reports</div>
                      <p className="text-white/50 text-sm leading-relaxed">
                        Multiple agents pull from different sources and combine into one
                        polished deliverable — PDF, slides, spreadsheet, or email.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Step 3: Review */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6 mb-16">
                <div className="text-4xl font-light text-white/20">03</div>
                <div>
                  <h2 className="text-2xl md:text-3xl font-medium mb-4">You review. They learn.</h2>
                  <p className="text-white/50 leading-relaxed max-w-2xl mb-8">
                    Review, edit, or redirect. Your feedback teaches agents your preferred
                    structure, tone, and priorities. Every cycle produces better work than the last.
                  </p>

                  <div className="border border-white/10 rounded-2xl p-6 bg-white/5 max-w-2xl">
                    <div className="space-y-6">
                      <div className="flex justify-end">
                        <div className="bg-white/10 rounded-2xl rounded-br-sm px-4 py-3 max-w-[85%]">
                          <p className="text-white/90 text-sm">
                            The weekly update is too long. Lead with risks and keep it under 500 words.
                          </p>
                        </div>
                      </div>

                      <div className="flex justify-start">
                        <div className="bg-white/5 border border-white/10 rounded-2xl rounded-bl-sm px-4 py-3 max-w-[85%]">
                          <p className="text-white/70 text-sm">
                            Got it. I&apos;ll restructure to lead with risks and cap at 500 words.
                            This preference will carry forward to future runs.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  <p className="text-white/30 text-xs mt-6 max-w-xl">
                    Talk to any agent directly in its meeting room. Your direction persists
                    across sessions — agents remember what you told them.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Multi-agent */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">Agents work together</h2>
              <p className="text-white/50 leading-relaxed mb-12 max-w-2xl">
                For bigger jobs, multiple agents collaborate. One pulls from Slack, another
                from Gmail, another does research — then a coordinator assembles their work
                into one deliverable. You get a finished product, not fragments.
              </p>

              <div className="border border-white/10 rounded-xl p-6 bg-white/5">
                <div className="text-xs text-white/30 uppercase tracking-wider mb-6">Example: Weekly leadership brief</div>
                <div className="space-y-4">
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">Slack agent summarizes #engineering and #product activity</p>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">Gmail agent flags key client threads and follow-ups</p>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">Research agent tracks competitor moves</p>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/40 mt-2 shrink-0" />
                    <p className="text-white text-sm font-medium">Coordinator assembles into one brief, delivered Monday 8 AM</p>
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
                real understanding of your work.
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
                    <p className="text-white/70 text-sm">Cross-platform patterns — who talks to whom, what projects matter, what&apos;s stuck</p>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">Domain knowledge — research findings, competitive landscape, team dynamics</p>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">Run history — every output feeds better future output</p>
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
                Describe what you need in plain language. Or just connect a platform and let yarnnn handle it.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Give me a weekly digest from #engineering and #product.&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Every Friday, send leadership a status report as a PDF.&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Watch customer-feedback threads and brief me when themes emerge.&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Track these three competitors and give me a weekly update.&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Before my meetings, generate a prep brief from email and docs.&rdquo;</p>
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
                Your first agent is one click away.
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Connect a platform. Your first agent starts working immediately.
              </p>
              <Link
                href="/auth/login"
                className="inline-block px-8 py-4 bg-white text-black text-lg font-medium rounded-full hover:bg-white/90 transition-colors"
              >
                Start with yarnnn
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
