import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { SpotlightCard } from "@/components/landing/SpotlightCard";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata: Metadata = getMarketingMetadata({
  title: "About — Why we built yarnnn",
  description:
    "Chat resets. Systems compound. yarnnn is an autonomous agent platform for recurring knowledge work built around persistent agents, tasks, and supervision.",
  path: "/about",
  keywords: [
    "about yarnnn",
    "autonomous ai",
    "ai workforce",
    "ai agents",
    "recurring ai work",
    "cloud ai agents",
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
              Chat resets.
              <br />
              <span className="text-white/50">Systems compound.</span>
            </h1>
            <div className="max-w-2xl space-y-6 text-white/50">
              <p>
                Most AI products are still session tools. Open a chat, do the work,
                close the tab, repeat tomorrow. They are impressive in the moment
                and disposable by design.
              </p>
              <p>
                But real knowledge work is recurring. The same reports, the same synthesis,
                the same updates across the same tools &mdash; week after week. That kind
                of work does not need a better prompt. It needs a system that keeps
                context, runs on schedule, and gets sharper every cycle.
              </p>
              <p className="text-white font-medium">
                yarnnn is what we built: an autonomous agent platform for recurring
                knowledge work. Persistent agents, shared workspace context, TP
                orchestration, and recurring tasks that compound through supervision.
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
                    <h3 className="text-lg font-medium text-white">Systems, not sessions</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      The line we care about is not chatbot versus agent. It is
                      session versus system. Sessions help in the moment. Systems
                      keep context, run recurring work, and improve through reuse.
                    </p>
                    <p className="text-white/30 text-sm">
                      The product is not a better way to prompt. It is a better way
                      to keep recurring work running.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Agents are who. Tasks are what.</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      The key separation in the product is simple. Agents are the
                      persistent specialists. Tasks are the work contracts. That
                      split lets one agent deepen over time while tasks come and go.
                    </p>
                    <p className="text-white/30 text-sm">
                      TP manages the system. Domain agents deepen inside their domains.
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
                      You review, redirect, and move on. That is the difference between
                      operating a tool and supervising a system.
                    </p>
                    <p className="text-white/30 text-sm">
                      The shift: from operator to supervisor. From building context to reviewing output.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Context compounds</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      The moat is accumulated context: workspace files, platform data,
                      prior outputs, user feedback, and domain knowledge built across cycles.
                      That is what turns future work from generic to specific.
                    </p>
                    <p className="text-white/30 text-sm">
                      Agent identity is persistent. Task history stays inspectable. Quality compounds with tenure.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Cloud-native by necessity</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      Employees need to be always-on. They run at 6 AM while your laptop is in your bag.
                      They sync Slack at midnight. They accumulate 90 days of context across sessions.
                      None of this works locally. Cloud isn&apos;t a preference &mdash; it&apos;s a structural
                      requirement of autonomous, recurring work.
                    </p>
                    <p className="text-white/30 text-sm">
                      The local-first wave builds great tools. We&apos;re building the layer above.
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

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {([
                  { title: "Not a tool you operate", desc: "Tools need you present. yarnnn keeps recurring work running on schedule, whether you open the app or not." },
                  { title: "Not a local agent", desc: "Local agents die when your laptop closes. yarnnn agents are cloud-native: always-on, always-accumulating, always-available. That\u2019s structural, not preferential." },
                  { title: "Not one-shot task execution", desc: "We optimize for recurring, high-context work \u2014 tasks that run weekly, daily, or on a cadence \u2014 not arbitrary one-off commands." },
                  { title: "Not uncontrolled automation", desc: "Every task has run history, delivery controls, and explicit user oversight. You supervise the system. You don\u2019t give it a blank check." },
                ] as const).map((item) => (
                  <SpotlightCard key={item.title} variant="dark" spotlightSize={300}>
                    <div className="p-6">
                      <h3 className="text-lg font-medium mb-2">{item.title}</h3>
                      <p className="text-white/50 text-sm leading-relaxed">{item.desc}</p>
                    </div>
                  </SpotlightCard>
                ))}
              </div>
            </div>
          </section>

          {/* Who it's for */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-12">Who yarnnn is for</h2>

              <div className="space-y-4">
                {([
                  { title: "People tired of re-prompting the same work every week", desc: "Founders, consultants, chiefs of staff, and team leads who spend hours synthesizing across tools every Monday, every Friday, before every meeting. Those loops should live in a system, not in your memory." },
                  { title: "Anyone graduating from chat to systems", desc: "If you\u2019ve used ChatGPT or Claude for recurring work and wished it would just handle next week automatically, yarnnn is built for that transition." },
                  { title: "People who want to supervise instead of execute", desc: "If you&apos;d rather review a finished brief than build one from scratch every time, yarnnn gives you a system that keeps working while you direct it." },
                ] as const).map((item) => (
                  <SpotlightCard key={item.title} variant="dark" spotlightSize={400}>
                    <div className="p-6">
                      <h3 className="text-base font-medium mb-2">{item.title}</h3>
                      <p className="text-white/50 text-sm leading-relaxed">{item.desc}</p>
                    </div>
                  </SpotlightCard>
                ))}
              </div>
            </div>
          </section>

          {/* CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Start with one recurring task.
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                The scaffold is there from day one. The value comes from putting
                a real loop into motion and supervising it.
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
        dangerouslySetInnerHTML={{ __html: JSON.stringify(aboutSchema) }}
      />
    </div>
  );
}
