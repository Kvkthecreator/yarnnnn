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
    "AI tools reset when you close the tab. AI employees show up every day, accumulate expertise, and deliver without being asked. We built yarnnn to be the second kind.",
  path: "/about",
  keywords: [
    "about yarnnn",
    "autonomous ai",
    "ai workforce",
    "ai employee",
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
              Tools reset.
              <br />
              <span className="text-white/50">Employees accumulate.</span>
            </h1>
            <div className="max-w-2xl space-y-6 text-white/50">
              <p>
                The best AI products in the world are tools. Open a session, do the work,
                close the tab. Tomorrow, start over. They&apos;re impressive in the moment
                and stateless by design.
              </p>
              <p>
                But real knowledge work is recurring. The same reports, the same synthesis,
                the same updates across the same tools &mdash; week after week. That kind
                of work doesn&apos;t need a better tool. It needs someone who shows up,
                remembers what happened last time, and does it better this time.
              </p>
              <p className="text-white font-medium">
                yarnnn is what we built: AI employees. A team of specialist agents &mdash; ready
                on day 1 &mdash; that take on your recurring work, run on schedule, learn
                from your feedback, and deliver without being asked.
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
                    <h3 className="text-lg font-medium text-white">Employees, not tools</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      The AI agent industry is splitting into two categories. Tools are session-scoped
                      and interactive &mdash; powerful in the moment, stateless between uses. Employees
                      are persistent and autonomous &mdash; they accumulate expertise, run on schedule,
                      and compound quality with tenure. We&apos;re building the second kind.
                    </p>
                    <p className="text-white/30 text-sm">
                      You don&apos;t pay $19/month for a tool you invoke when you remember to. You
                      pay for employees that work while you sleep.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Your team should be ready on day 1</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      You shouldn&apos;t have to build an AI workforce from scratch. When you sign up
                      for yarnnn, you get Research, Content, Marketing, and CRM agents plus Slack and
                      Notion bots &mdash; a complete team of specialists, pre-built and ready to take on work.
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
                      You review, redirect, and move on. That&apos;s the difference between operating
                      a tool and supervising an employee.
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
                      doesn&apos;t try to become a Content Agent &mdash; it becomes a better researcher.
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
                  { title: "Not a tool you operate", desc: "Tools need you present. yarnnn agents run on schedule, deliver finished work, and learn from your feedback \u2014 whether you open the app or not." },
                  { title: "Not a local agent", desc: "Local agents die when your laptop closes. yarnnn agents are cloud-native: always-on, always-accumulating, always-available. That\u2019s structural, not preferential." },
                  { title: "Not one-shot task execution", desc: "We optimize for recurring, high-context work \u2014 tasks that run weekly, daily, or on a cadence \u2014 not arbitrary one-off commands." },
                  { title: "Not uncontrolled automation", desc: "Every task has run history, delivery controls, and explicit user oversight. You supervise employees. You don\u2019t give them a blank check." },
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
                  { title: "People tired of re-prompting the same work every week", desc: "Founders, consultants, chiefs of staff, and team leads who spend hours synthesizing across tools \u2014 every Monday, every Friday, before every meeting. Assign those tasks to your AI employees instead." },
                  { title: "Anyone graduating from tools to employees", desc: "If you\u2019ve used ChatGPT or Claude for recurring work and wished it would just \u2026 do it automatically next week, yarnnn is the product you\u2019re looking for." },
                  { title: "People who want to supervise instead of execute", desc: "If you\u2019d rather review a finished brief Monday morning than build one from scratch, yarnnn gives you a team that does the work while you direct." },
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
                Meet your team. Assign the first task.
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Your AI employees are ready the moment you sign up. No setup required.
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
