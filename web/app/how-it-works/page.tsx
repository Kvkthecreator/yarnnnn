import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata: Metadata = getMarketingMetadata({
  title: "Meet TP — How Your AI Agent Works",
  description:
    "TP is your autonomous AI agent. Not a chatbot. Not a prompt box. It connects to your platforms, accumulates context, and produces deliverables on schedule.",
  path: "/how-it-works",
  keywords: [
    "ai agent",
    "autonomous ai agent",
    "thinking partner",
    "how yarnnn works",
    "context powered agent",
  ],
});

export default function HowItWorksPage() {
  const howToSchema = {
    "@context": "https://schema.org",
    "@type": "HowTo",
    name: "How your AI agent TP works",
    description: metadata.description,
    url: `${BRAND.url}/how-it-works`,
    step: [
      {
        "@type": "HowToStep",
        name: "Brief your agent on what you need",
      },
      {
        "@type": "HowToStep",
        name: "Give TP access to your platforms",
      },
      {
        "@type": "HowToStep",
        name: "Review what TP produces",
      },
      {
        "@type": "HowToStep",
        name: "Watch TP get smarter every cycle",
      },
    ],
  };

  return (
    <div className="relative min-h-screen flex flex-col bg-[#0f1419] text-white overflow-x-hidden">
      <GrainOverlay variant="dark" />
      <ShaderBackgroundDark />

      {/* Content layer */}
      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted />

        <main className="flex-1">
          {/* Hero */}
          <section className="max-w-4xl mx-auto px-6 py-24 md:py-32">
            <p className="text-white/40 text-sm uppercase tracking-widest mb-4">How It Works</p>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-10 tracking-tight leading-[1.1]">
              TP is your autonomous
              <br />
              <span className="text-white/50">AI agent.</span>
            </h1>
            <p className="max-w-2xl text-white/50 text-lg">
              Not a chatbot. Not a prompt box. TP is an agent that already knows your work —
              connected to your platforms, accumulating context continuously,
              and producing your deliverables on schedule.
            </p>
          </section>

          {/* The Conversation Model */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">You talk. TP listens.</h2>
              <p className="text-white/50 leading-relaxed mb-12 max-w-2xl">
                No wizards. No configuration screens. Just describe what you need in plain language,
                and TP figures out the rest.
              </p>

              {/* Chat Example */}
              <div className="border border-white/10 rounded-2xl p-6 bg-white/5 max-w-2xl">
                <div className="space-y-6">
                  {/* User message */}
                  <div className="flex justify-end">
                    <div className="bg-white/10 rounded-2xl rounded-br-sm px-4 py-3 max-w-[85%]">
                      <p className="text-white/90 text-sm">I need to send a weekly update to Sarah</p>
                    </div>
                  </div>

                  {/* TP response */}
                  <div className="flex justify-start">
                    <div className="bg-white/5 border border-white/10 rounded-2xl rounded-bl-sm px-4 py-3 max-w-[85%]">
                      <p className="text-white/70 text-sm mb-2">
                        Got it. I see you have #engineering and #product connected.
                      </p>
                      <p className="text-white/70 text-sm">
                        Should I pull from both for your updates?
                      </p>
                    </div>
                  </div>

                  {/* User message */}
                  <div className="flex justify-end">
                    <div className="bg-white/10 rounded-2xl rounded-br-sm px-4 py-3 max-w-[85%]">
                      <p className="text-white/90 text-sm">Just engineering for now</p>
                    </div>
                  </div>

                  {/* TP response */}
                  <div className="flex justify-start">
                    <div className="bg-white/5 border border-white/10 rounded-2xl rounded-bl-sm px-4 py-3 max-w-[85%]">
                      <p className="text-white/70 text-sm mb-2">
                        Perfect. When does Sarah need this?
                      </p>
                    </div>
                  </div>

                  {/* User message */}
                  <div className="flex justify-end">
                    <div className="bg-white/10 rounded-2xl rounded-br-sm px-4 py-3 max-w-[85%]">
                      <p className="text-white/90 text-sm">Monday mornings</p>
                    </div>
                  </div>

                  {/* TP final response */}
                  <div className="flex justify-start">
                    <div className="bg-white/5 border border-white/10 rounded-2xl rounded-bl-sm px-4 py-3 max-w-[85%]">
                      <p className="text-white/70 text-sm mb-3">
                        I&apos;ll have your first draft ready Sunday evening.
                      </p>
                      <p className="text-white/70 text-sm">
                        Based on this week&apos;s #engineering activity, here&apos;s what I&apos;d include...
                      </p>
                      <div className="mt-3 pt-3 border-t border-white/10">
                        <p className="text-white/40 text-xs">Draft preview loading...</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <p className="text-white/30 text-xs mt-6 max-w-xl">
                That&apos;s it. No configuration screens. TP figures out what you need
                and sets everything up through conversation.
              </p>
            </div>
          </section>

          {/* What TP Does */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">What makes TP different</h2>
              <p className="text-white/50 leading-relaxed mb-12 max-w-2xl">
                Every other agent starts from zero. TP combines four things that make
                it the only agent worth using long-term.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="border border-white/10 rounded-xl p-6">
                  <div className="text-lg font-medium mb-3">Your agent interface</div>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Talk to TP like a colleague. It understands your work context, sets up
                    deliverables through conversation, and operates autonomously on your behalf.
                  </p>
                </div>

                <div className="border border-white/10 rounded-xl p-6">
                  <div className="text-lg font-medium mb-3">TP works on schedule</div>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Status reports, investor updates, client briefs — TP produces them on schedule
                    without you lifting a finger. You review and approve.
                  </p>
                </div>

                <div className="border border-white/10 rounded-xl p-6">
                  <div className="text-lg font-medium mb-3">TP already knows your world</div>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Slack, Gmail, Notion, Calendar sync continuously. TP accumulates a deepening
                    understanding of your work. The context compounds.
                  </p>
                </div>

                <div className="border border-white/10 rounded-xl p-6">
                  <div className="text-lg font-medium mb-3">TP learns from every interaction</div>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Every approval, every edit, every sync cycle. After 90 days,
                    no other agent comes close to TP&apos;s understanding of your work.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* The Flow */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">The flow</h2>
              <p className="text-white/50 leading-relaxed mb-16 max-w-2xl">
                From first conversation to full autonomy.
              </p>

              <div className="space-y-16">
                {/* Step 1 */}
                <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6">
                  <div className="text-4xl font-light text-white/20">01</div>
                  <div>
                    <h3 className="text-xl font-medium mb-3">Brief your agent</h3>
                    <p className="text-white/50 leading-relaxed">
                      &ldquo;I need a weekly status report for my manager&rdquo; or
                      &ldquo;Monthly investor update, first Tuesday&rdquo;.
                      Just say it. TP asks clarifying questions and sets everything up.
                    </p>
                  </div>
                </div>

                {/* Step 2 */}
                <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6">
                  <div className="text-4xl font-light text-white/20">02</div>
                  <div>
                    <h3 className="text-xl font-medium mb-3">Give TP access to your world</h3>
                    <p className="text-white/50 leading-relaxed">
                      Connect Slack, Gmail, Notion, Calendar — wherever
                      your work lives. One-time OAuth. TP starts accumulating context immediately.
                    </p>
                  </div>
                </div>

                {/* Step 3 */}
                <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6">
                  <div className="text-4xl font-light text-white/20">03</div>
                  <div>
                    <h3 className="text-xl font-medium mb-3">Review what TP produces</h3>
                    <p className="text-white/50 leading-relaxed">
                      On schedule, TP produces your deliverable autonomously.
                      You review, tweak if needed, and approve. You supervise — TP operates.
                    </p>
                  </div>
                </div>

                {/* Step 4 */}
                <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6">
                  <div className="text-4xl font-light text-white/20">04</div>
                  <div>
                    <h3 className="text-xl font-medium mb-3">Watch TP get smarter</h3>
                    <p className="text-white/50 leading-relaxed">
                      Every cycle deepens context, every approval teaches preferences.
                      By week 8, you&apos;re approving with barely a glance. That&apos;s the moat.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Context Accumulation */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">Why TP outperforms every other agent</h2>
              <p className="text-white/50 leading-relaxed mb-12 max-w-2xl">
                Other agents reset every session. TP accumulates a persistent,
                deepening understanding of your work across every platform you connect.
              </p>

              <div className="border border-white/10 rounded-xl p-6 bg-white/5">
                <div className="text-xs text-white/30 uppercase tracking-wider mb-6">What accumulates over time</div>
                <div className="space-y-4">
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">
                      Conversations, decisions, and patterns from your Slack channels
                    </p>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">
                      Your writing style, structure preferences, and tone for each audience
                    </p>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">
                      Client relationships, project context, and team dynamics from email and docs
                    </p>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">
                      What metrics matter, what wins to highlight, what context each stakeholder needs
                    </p>
                  </div>
                </div>
              </div>

              <p className="text-white/30 text-sm mt-6">
                90 days of accumulated context is irreplaceable.
                That&apos;s what separates TP from every other agent.
              </p>
            </div>
          </section>

          {/* Examples */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">What you can say to TP</h2>
              <p className="text-white/50 leading-relaxed mb-12">
                No magic phrases. Just tell TP what you need.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;I need a weekly status report for Sarah&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Summarize my client emails from this week&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Create a monthly investor update&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;What happened in #engineering this week?&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Make this draft more concise&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Add the metrics from our Notion dashboard&rdquo;</p>
                </div>
              </div>
            </div>
          </section>

          {/* CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Your agent is ready.
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Start a conversation. Connect your platforms.
                Watch TP get smarter every cycle.
              </p>
              <Link
                href="/auth/login"
                className="inline-block px-8 py-4 bg-white text-black text-lg font-medium rounded-full hover:bg-white/90 transition-colors"
              >
                Start talking to TP
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
