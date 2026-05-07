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
    "An agent-native operating system for recurring knowledge work. The structural argument for why this layer exists, and what we believe about how it should work.",
  path: "/about",
  keywords: [
    "about yarnnn",
    "autonomous ai",
    "agent operating system",
    "agent os",
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
                Right now, it genuinely looks like the big LLM providers will own every layer.
                Claude has Code, Cowork, and desktop agents. ChatGPT has memory, browsing, and
                plugins. Google is embedding Gemini into everything. The prevailing assumption
                is that these companies will consume the whole stack.
              </p>
              <p>
                We think that&apos;s wrong — or more precisely, we think the pattern will rhyme
                with every prior platform cycle. In 2008, Google looked invincible on the web.
                In 2012, Facebook looked like it would own all of social commerce. In 2015, AWS
                looked like it would own every cloud application. The platform provider always
                looks like it will do everything — until the application layer emerges and proves
                that domain-specific, context-specific value can&apos;t be built by a general-purpose
                platform.
              </p>
              <p>
                Notice what application layer the LLM providers built first: code. Structured
                input, verifiable output, the model&apos;s core capability mapping directly to the
                product. Work context — your projects, your communication patterns, your
                recurring knowledge loops across platforms — is the opposite: unstructured,
                personal, cross-platform, and domain-specific. That&apos;s why no LLM provider is
                building it, even as they build coding agents.
              </p>
              <p className="text-white font-medium">
                yarnnn is what we built: an agent-native operating system for recurring
                knowledge work. You describe your work, create persistent agents around it
                through conversation, and supervise a system that runs and compounds.
                The team is yours. The context accumulates. The operation keeps going.
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
                    <h3 className="text-lg font-medium text-white">Operating system, not application</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      Chat is the interface. The product is what runs underneath — a kernel that
                      schedules and executes, a workspace that accumulates, a judgment layer that
                      reviews what agents propose. That distinction matters: it means agents can
                      operate while you sleep, and you can trust what they do because the
                      operating model enforces it.
                    </p>
                    <p className="text-white/30 text-sm">
                      The shift from tool to OS is architectural, not cosmetic. You don&apos;t
                      operate yarnnn. You supervise it.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Agents are who. Tasks are what.</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      The key separation in the product is simple. Agents are the persistent
                      specialists — created through conversation, scoped to your domain, deepening
                      in expertise with every run. Tasks are the work contracts — what to produce,
                      on what cadence, delivered where.
                    </p>
                    <p className="text-white/30 text-sm">
                      Agents deepen their knowledge. Tasks come and go. The system keeps learning.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Judgment is separate from execution</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      The same agent that proposes an action shouldn&apos;t decide whether that action
                      is a good idea. An independent judgment function reads your declared intent
                      and evaluates proposed actions before they bind. That separation isn&apos;t
                      advisory — it&apos;s architectural.
                    </p>
                    <p className="text-white/30 text-sm">
                      The result: the system can act more autonomously, not less, because you can
                      trust that its actions have already passed a principled test.
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
                    <h3 className="text-lg font-medium text-white">Substrate, not context window</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      The moat isn&apos;t the model. Models are becoming commodities — GPT-4, Claude,
                      Gemini are roughly interchangeable for most tasks. The real differentiation
                      is what accumulates over time: domain context, calibrated preferences,
                      prior outputs feeding future ones, accumulated corrections from your edits.
                    </p>
                    <p className="text-white/30 text-sm">
                      That&apos;s what turns future work from generic to specific. And it can&apos;t be
                      rebuilt by starting over with a new tool.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Cloud-native by necessity</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      Agents need to be always-on. They run at 6 AM while your laptop is in your
                      bag. They sync platforms at midnight. They accumulate 90 days of context
                      across sessions. None of this works locally. Cloud isn&apos;t a preference
                      — it&apos;s a structural requirement of autonomous, recurring work.
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
                  {
                    title: "Not a tool you operate",
                    desc: "Tools need you present. yarnnn keeps recurring work running on schedule, whether you open the app or not. You supervise the system. The system does the work.",
                  },
                  {
                    title: "Not a session-based assistant",
                    desc: "Sessions help in the moment and reset when you close the tab. yarnnn agents accumulate — the same domain expert keeps running against the same domain, deepening with every cycle.",
                  },
                  {
                    title: "Not one-shot task execution",
                    desc: "We optimize for recurring, high-context work — tasks that run weekly, daily, or on cadence — not arbitrary one-off commands. The value is what compounds, not what executes once.",
                  },
                  {
                    title: "Not uncontrolled automation",
                    desc: "Every proposed action passes through an independent judgment layer. Every task has run history and explicit operator oversight. You set the intent and the limits. The OS respects them.",
                  },
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
                  {
                    title: "Operators who want a running system, not a better prompt",
                    desc: "If you've used ChatGPT or Claude for recurring work and wished it would just handle next week automatically — yarnnn is built for that transition. Declare the work once. The OS keeps it going.",
                  },
                  {
                    title: "People tired of re-prompting the same work every week",
                    desc: "Founders, consultants, chiefs of staff, and team leads who spend hours synthesizing across tools every Monday, every Friday, before every meeting. Those loops should live in a system, not in your memory.",
                  },
                  {
                    title: "Anyone moving from supervision of prompts to supervision of agents",
                    desc: "If you'd rather review a finished brief than build one from scratch every time — and you want the system to get better at your specific work over time — yarnnn is built for that.",
                  },
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
                Start with one piece of work.
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Describe it to YARNNN. The agents it creates will still be running three months
                from now — with everything they&apos;ve learned along the way.
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
        dangerouslySetInnerHTML={{ __html: JSON.stringify(aboutSchema) }}
      />
    </div>
  );
}
