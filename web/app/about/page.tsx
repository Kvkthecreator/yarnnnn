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
    "We built yarnnn because AI should do the recurring work, not just answer questions. A pre-built AI workforce with persistent agents that learn your context and deliver on schedule.",
  path: "/about",
  keywords: [
    "about yarnnn",
    "autonomous ai",
    "ai workforce",
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
                yarnnn is what we built: a team of specialist AI agents — ready on day 1 —
                that take on your recurring tasks, run on schedule, and get better with every
                cycle. You assign the work. They execute. You supervise outcomes.
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
                    <h3 className="text-lg font-medium text-white">Your team should be ready on day 1</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      You shouldn&apos;t have to build an AI workforce from scratch. When you sign up
                      for yarnnn, you get Research, Content, Marketing, and CRM agents plus Slack and
                      Notion bots — a complete team of specialists, pre-built and ready to take on work.
                    </p>
                    <p className="text-white/30 text-sm">
                      Agents are who. Tasks are what. You describe the work, and the right
                      agent handles it.
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
                      Agents run tasks in the background on schedule and deliver finished work.
                      You review, redirect, and move on.
                    </p>
                    <p className="text-white/30 text-sm">
                      The shift: from operator to supervisor. From building context to reviewing output.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Agents develop inward</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      A good employee gets better by going deeper, not wider. Your Research Agent
                      doesn&apos;t try to become a Content Agent — it becomes a better researcher.
                      Every edit, every review, every task run builds domain knowledge that compounds.
                    </p>
                    <p className="text-white/30 text-sm">
                      Agent identity is persistent. Capabilities are fixed by type. Knowledge is
                      what grows.
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
                      3 months of your Slack and Notion patterns, your feedback history, and your
                      domain context can&apos;t be replicated by switching to another tool.
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
                    You can talk to yarnnn, but the product is the tasks that run in the background.
                    Agents execute on schedule — the real work happens when you&apos;re not looking.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-medium mb-2">Not template automation</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Agents generate from live context and accumulated memory, not
                    static form fields. Every task run uses fresh data.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-medium mb-2">Not one-shot task execution</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    We optimize for recurring, high-context work — tasks that run weekly, daily,
                    or on a cadence — not arbitrary one-off commands.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-medium mb-2">Not uncontrolled automation</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Every task has run history, delivery controls, and explicit user oversight.
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
                    Assign those tasks to your agents instead.
                  </p>
                </div>

                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-2">Teams spread across Slack and Notion</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    If your workflow spans multiple platforms, yarnnn&apos;s bots sync it all
                    and your agents turn that context into coherent, recurring output.
                  </p>
                </div>

                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-2">Anyone who wants to supervise instead of execute</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    If you&apos;d rather review a finished brief than build one from scratch,
                    yarnnn gives you a team that does the work while you direct.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Meet your team. Assign the first task.
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Your AI workforce is ready the moment you sign up. No setup required.
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
        dangerouslySetInnerHTML={{ __html: JSON.stringify(aboutSchema) }}
      />
    </div>
  );
}
