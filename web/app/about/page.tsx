import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata: Metadata = getMarketingMetadata({
  title: "About — Why we built yarnnn",
  description:
    "We built yarnnn because AI should do the recurring work, not just answer questions. Persistent agents that learn your context and deliver real output on schedule.",
  path: "/about",
  keywords: [
    "about yarnnn",
    "autonomous ai",
    "ai employee",
    "agent intelligence",
    "recurring ai work",
  ],
});

export default function AboutPage() {
  const aboutSchema = {
    "@context": "https://schema.org",
    "@type": "AboutPage",
    name: "About yarnnn",
    description: metadata.description,
    url: `${BRAND.url}/about`,
    isPartOf: {
      "@type": "WebSite",
      name: BRAND.name,
      url: BRAND.url,
    },
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
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-10 tracking-tight leading-[1.1]">
              AI should do the work,
              <br />
              <span className="text-white/50">not just answer questions.</span>
            </h1>
            <div className="max-w-2xl space-y-6 text-white/50">
              <p>
                Most AI products are impressive in a single conversation. But close the tab
                and everything resets. Tomorrow you&apos;re starting from scratch.
              </p>
              <p>
                Real knowledge work is recurring. The same reports, the same updates, the same
                synthesis across the same tools — week after week. Good AI for this kind of work
                needs memory, context from your actual systems, and the ability to run without you.
              </p>
              <p className="text-white font-medium">
                yarnnn is what we built: AI agents that know your work, run on schedule, and get
                better with every cycle. You supervise outcomes instead of doing the work yourself.
              </p>
            </div>
          </section>

          {/* What we believe */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">What we believe</h2>

              <div className="space-y-16">
                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">AI should know your work</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      Intelligence without context produces generic output. Useful AI needs
                      grounded awareness of your team, your projects, your communication patterns,
                      and what happened last week.
                    </p>
                    <p className="text-white/30 text-sm">
                      yarnnn connects to Slack, Gmail, Notion, and Calendar — and remembers
                      everything across sessions.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Supervision, not prompting</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      The goal isn&apos;t faster prompting. The goal is to not have to prompt at all.
                      Agents run in the background and deliver work. You review, redirect, and
                      move on.
                    </p>
                    <p className="text-white/30 text-sm">
                      The shift: from operator to supervisor. From building context to reviewing output.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Agents should develop</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      A good assistant gets better over time. They learn your preferences,
                      understand what matters, and require less direction the longer they work for you.
                    </p>
                    <p className="text-white/30 text-sm">
                      yarnnn agents learn from your edits, remember your feedback, and build
                      domain knowledge that compounds with every cycle.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">The longer it runs, the better it gets</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      Day 1, the output is good. Day 90, it&apos;s irreplaceable. An agent that knows
                      3 months of your Slack, email, and meeting patterns can&apos;t be replicated by
                      switching to another tool.
                    </p>
                    <p className="text-white/30 text-sm">
                      That compounding intelligence is the product. Everything else is support.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* What yarnnn is not */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">What yarnnn is not</h2>
              <p className="text-white/50 mb-12 max-w-xl">
                We&apos;re focused. These are things we intentionally chose not to be.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                  <h3 className="text-lg font-medium mb-2">Not a chatbot</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    You can talk to yarnnn, but the product is the work that happens
                    when you&apos;re not talking. Agents run in the background.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-medium mb-2">Not template automation</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Agents generate from live context and accumulated memory, not
                    static form fields.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-medium mb-2">Not one-shot task execution</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    We optimize for recurring, high-context work — not arbitrary one-off commands
                    disconnected from your real systems.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-medium mb-2">Not uncontrolled automation</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Every agent has run history, delivery controls, and explicit user oversight.
                    Supervised autonomy, not a black box.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Who it's for */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-12">Who yarnnn is for</h2>

              <div className="space-y-6">
                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-2">People who do the same knowledge work every week</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Founders, consultants, chiefs of staff, and team leads who spend hours
                    synthesizing across tools — every Monday, every Friday, before every meeting.
                  </p>
                </div>

                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-2">Teams spread across Slack, Gmail, Notion, and Calendar</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    If your workflow spans multiple platforms, yarnnn turns that sprawl into
                    coherent, recurring output. Automatically.
                  </p>
                </div>

                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-2">Anyone who wants to supervise instead of execute</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    If you&apos;d rather review a finished brief than build one from scratch,
                    yarnnn is built for that shift.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Put your first agent to work.
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Connect your tools, let yarnnn create your first agent, and start supervising.
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
        dangerouslySetInnerHTML={{ __html: JSON.stringify(aboutSchema) }}
      />
    </div>
  );
}
