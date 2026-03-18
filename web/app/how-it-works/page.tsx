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
    "yarnnn connects to your work tools and creates autonomous agents that deliver recurring work and improve with every cycle. Connect, supervise, compound.",
  path: "/how-it-works",
  keywords: [
    "how yarnnn works",
    "autonomous ai workflow",
    "agent automation",
    "ai agents",
    "context powered agent",
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
        name: "Agents run on schedule and deliver work",
      },
      {
        "@type": "HowToStep",
        name: "Review, refine, or redirect agent output",
      },
      {
        "@type": "HowToStep",
        name: "Quality compounds as context and memory accumulate",
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
          <section className="max-w-4xl mx-auto px-6 py-24 md:py-32">
            <p className="text-white/40 text-sm uppercase tracking-widest mb-4">How It Works</p>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-10 tracking-tight leading-[1.1]">
              Connect once.
              <br />
              <span className="text-white/50">Supervise from there.</span>
            </h1>
            <p className="max-w-2xl text-white/50 text-lg">
              yarnnn connects to your work tools and creates agents that run in the background.
              You supervise their work from a dashboard. Quality compounds with every cycle.
            </p>
          </section>

          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">Create agents in plain language</h2>
              <p className="text-white/50 leading-relaxed mb-12 max-w-2xl">
                Use the Orchestrator to describe what you need. yarnnn figures out
                the right agent setup — sources, schedule, delivery, and work product.
              </p>

              <div className="border border-white/10 rounded-2xl p-6 bg-white/5 max-w-2xl">
                <div className="space-y-6">
                  <div className="flex justify-end">
                    <div className="bg-white/10 rounded-2xl rounded-br-sm px-4 py-3 max-w-[85%]">
                      <p className="text-white/90 text-sm">
                        Create a weekly status update for leadership from #engineering and Notion launch docs.
                      </p>
                    </div>
                  </div>

                  <div className="flex justify-start">
                    <div className="bg-white/5 border border-white/10 rounded-2xl rounded-bl-sm px-4 py-3 max-w-[85%]">
                      <p className="text-white/70 text-sm mb-2">
                        Great. I&apos;ll set up a <span className="text-white">weekly status</span> agent
                        pulling from <span className="text-white">#engineering</span> and your Notion docs.
                      </p>
                      <p className="text-white/70 text-sm">
                        Do you want Monday 9:00 AM delivery and a concise executive format?
                      </p>
                    </div>
                  </div>

                  <div className="flex justify-end">
                    <div className="bg-white/10 rounded-2xl rounded-br-sm px-4 py-3 max-w-[85%]">
                      <p className="text-white/90 text-sm">Yes. Keep it short and include risks first.</p>
                    </div>
                  </div>

                  <div className="flex justify-start">
                    <div className="bg-white/5 border border-white/10 rounded-2xl rounded-bl-sm px-4 py-3 max-w-[85%]">
                      <p className="text-white/70 text-sm mb-3">
                        Done. First run will be delivered on schedule.
                      </p>
                      <div className="mt-3 pt-3 border-t border-white/10">
                        <p className="text-white/40 text-xs">Agent configured successfully.</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <p className="text-white/30 text-xs mt-6 max-w-xl">
                You can also connect a platform and let yarnnn create your first agent automatically.
              </p>
            </div>
          </section>

          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">What agents can do</h2>
              <p className="text-white/50 leading-relaxed mb-12 max-w-2xl">
                Each agent has a job and a schedule. yarnnn matches the right setup to what you need.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="border border-white/10 rounded-xl p-6">
                  <div className="text-lg font-medium mb-3">Recap</div>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Daily or weekly summaries of Slack channels, Gmail labels, or Notion pages. The most common starting point.
                  </p>
                </div>

                <div className="border border-white/10 rounded-xl p-6">
                  <div className="text-lg font-medium mb-3">Meeting Prep</div>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Before each meeting, yarnnn pulls relevant context from email, Slack, and docs into a briefing.
                  </p>
                </div>

                <div className="border border-white/10 rounded-xl p-6">
                  <div className="text-lg font-medium mb-3">Watch</div>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Monitor channels or topics for emerging themes. Get alerted when something needs your attention.
                  </p>
                </div>

                <div className="border border-white/10 rounded-xl p-6">
                  <div className="text-lg font-medium mb-3">Research</div>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Track a topic, competitor, or market. Combines your internal context with web research.
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">The flow</h2>
              <p className="text-white/50 leading-relaxed mb-16 max-w-2xl">
                From definition to compounding output.
              </p>

              <div className="space-y-16">
                <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6">
                  <div className="text-4xl font-light text-white/20">01</div>
                  <div>
                    <h3 className="text-xl font-medium mb-3">Connect your tools</h3>
                    <p className="text-white/50 leading-relaxed">
                      Link Slack, Gmail, Notion, or Calendar. Choose which channels, labels, or
                      pages to include. yarnnn creates your first agent automatically.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6">
                  <div className="text-4xl font-light text-white/20">02</div>
                  <div>
                    <h3 className="text-xl font-medium mb-3">Agents run on schedule</h3>
                    <p className="text-white/50 leading-relaxed">
                      Each agent executes in the background and delivers work you can review.
                      Your dashboard shows agent health, recent activity, and anything needing attention.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6">
                  <div className="text-4xl font-light text-white/20">03</div>
                  <div>
                    <h3 className="text-xl font-medium mb-3">Review and refine</h3>
                    <p className="text-white/50 leading-relaxed">
                      Review, edit, or redirect. Your feedback teaches the agent
                      your preferred structure, tone, and priorities.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6">
                  <div className="text-4xl font-light text-white/20">04</div>
                  <div>
                    <h3 className="text-xl font-medium mb-3">Compound quality</h3>
                    <p className="text-white/50 leading-relaxed">
                      Each cycle makes the agent better. Context deepens, memory
                      accumulates, and supervision effort drops over time.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">What accumulates</h2>
              <p className="text-white/50 leading-relaxed mb-12 max-w-2xl">
                yarnnn keeps only what matters for better future work.
              </p>

              <div className="border border-white/10 rounded-xl p-6 bg-white/5">
                <div className="text-xs text-white/30 uppercase tracking-wider mb-6">Compounding signals</div>
                <div className="space-y-4">
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">Preferred structure, tone, and prioritization patterns from edits and follow-up direction</p>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">Cross-platform relationships between messages, docs, meetings, and tasks</p>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">Domain observations for monitoring and research agents</p>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">Execution and delivery history that improves future output quality and relevance</p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">Example prompts</h2>
              <p className="text-white/50 leading-relaxed mb-12">
                Typical ways users create agents.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Create a weekly digest from #engineering and #product.&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Make a status update every Friday for leadership.&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Watch customer-feedback threads and brief me when themes emerge.&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Research this competitor set and give me a weekly update.&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Before my exec meetings, generate a prep brief from email + docs.&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Summarize my week across Slack, Gmail, and Notion every Friday.&rdquo;</p>
                </div>
              </div>
            </div>
          </section>

          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Ready to run autonomous work?
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Start with one agent. Scale your system as context and confidence grow.
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
