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
    "yarnnn turns connected work context into autonomous work-agents. Define a specialist, connect sources, review runs, and let quality compound over time.",
  path: "/how-it-works",
  keywords: [
    "how yarnnn works",
    "autonomous ai workflow",
    "agent automation",
    "work agents",
    "context powered agent",
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
        name: "Define your agent specialist (type + mode)",
      },
      {
        "@type": "HowToStep",
        name: "Connect sources from Slack, Gmail, Notion, and Calendar",
      },
      {
        "@type": "HowToStep",
        name: "Review run output and approve",
      },
      {
        "@type": "HowToStep",
        name: "Let memory and context compound each cycle",
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
              Configure once.
              <br />
              <span className="text-white/50">Supervise from there.</span>
            </h1>
            <p className="max-w-2xl text-white/50 text-lg">
              yarnnn combines TP Chat — your single interactive surface — with background work-agents.
              You define intent and constraints, work-agents execute and learn through supervised runs.
            </p>
          </section>

          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">Define work in plain language</h2>
              <p className="text-white/50 leading-relaxed mb-12 max-w-2xl">
                Use TP Chat to describe what you need, or configure work-agents directly in the UI.
                You choose type, mode, sources, and constraints. yarnnn handles orchestration.
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
                        Great. I&apos;ll configure a <span className="text-white">status</span> agent in
                        <span className="text-white"> recurring</span> mode.
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
                        Done. First run will be ready on schedule.
                      </p>
                      <div className="mt-3 pt-3 border-t border-white/10">
                        <p className="text-white/40 text-xs">Agent configured successfully.</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <p className="text-white/30 text-xs mt-6 max-w-xl">
                You can start via conversation or direct UI controls. Both routes use the same execution model.
              </p>
            </div>
          </section>

          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">Execution model</h2>
              <p className="text-white/50 leading-relaxed mb-12 max-w-2xl">
                Types define intent. Modes define behavior. Together they form a specialist that improves over time.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="border border-white/10 rounded-xl p-6">
                  <div className="text-lg font-medium mb-3">Type = what is being built</div>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Use intent-first types such as digest, brief, status, watch, deep_research, coordinator, or custom.
                  </p>
                </div>

                <div className="border border-white/10 rounded-xl p-6">
                  <div className="text-lg font-medium mb-3">Mode = when/how it acts</div>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Choose recurring, goal, reactive, proactive, or coordinator behavior based on how work should run.
                  </p>
                </div>

                <div className="border border-white/10 rounded-xl p-6">
                  <div className="text-lg font-medium mb-3">Runs = supervision loop</div>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Each run creates output you can review. You approve or refine. Feedback informs future generation.
                  </p>
                </div>

                <div className="border border-white/10 rounded-xl p-6">
                  <div className="text-lg font-medium mb-3">Context = performance moat</div>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Synced platform context plus agent memory lets specialists improve with tenure, not reset.
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
                    <h3 className="text-xl font-medium mb-3">Define specialist intent</h3>
                    <p className="text-white/50 leading-relaxed">
                      Pick a type and mode, then define structure, audience, and constraints.
                      This is where you encode how good output should look.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6">
                  <div className="text-4xl font-light text-white/20">02</div>
                  <div>
                    <h3 className="text-xl font-medium mb-3">Connect context sources</h3>
                    <p className="text-white/50 leading-relaxed">
                      Select channels, labels, pages, and calendar context.
                      yarnnn syncs selected sources and keeps them current based on tier cadence.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6">
                  <div className="text-4xl font-light text-white/20">03</div>
                  <div>
                    <h3 className="text-xl font-medium mb-3">Review and refine</h3>
                    <p className="text-white/50 leading-relaxed">
                      Work-agents execute in the background and produce runs.
                      You review, edit, approve, and maintain supervision control.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6">
                  <div className="text-4xl font-light text-white/20">04</div>
                  <div>
                    <h3 className="text-xl font-medium mb-3">Compound quality</h3>
                    <p className="text-white/50 leading-relaxed">
                      Repeated runs on the same specialist increase fidelity to your style and goals.
                      The output improves because context and memory accumulate.
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
                    <p className="text-white/70 text-sm">Preferred structure, tone, and prioritization patterns from approvals</p>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">Cross-platform relationships between messages, docs, meetings, and tasks</p>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">Domain observations for watch/proactive/coordinator specialists</p>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">Execution history that improves future output quality and relevance</p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">Example prompts</h2>
              <p className="text-white/50 leading-relaxed mb-12">
                Typical ways users configure specialists.
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
                  <p className="text-white/70 text-sm italic">&ldquo;Run deep research on this competitor set until complete.&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Before my exec meetings, generate a prep brief from email + docs.&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Set up a coordinator to trigger follow-ups when client threads stall.&rdquo;</p>
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
                Start with one specialist. Then scale your system as context and confidence grow.
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
