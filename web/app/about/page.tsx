import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata: Metadata = getMarketingMetadata({
  title: "About",
  description:
    "Learn why yarnnn was built: autonomous AI powered by accumulated work context, designed for supervision over manual operation.",
  path: "/about",
  keywords: [
    "about yarnnn",
    "autonomous ai platform",
    "context accumulation",
    "supervision model",
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

      {/* Content layer */}
      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted />

        <main className="flex-1">
          {/* Hero */}
          <section className="max-w-4xl mx-auto px-6 py-24 md:py-32">
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-10 tracking-tight leading-[1.1]">
              We built yarnnn because
              <br />
              <span className="text-white/50">AI should work for you, not just with you.</span>
            </h1>
            <div className="max-w-2xl space-y-6 text-white/50">
              <p>
                You use AI every day. And every day, it forgets everything. Your preferences,
                your context, your last conversation. You start from scratch, re-explain your
                world, and do all the assembly yourself.
              </p>
              <p>
                AI is powerful. But stateless, one-shot AI can&apos;t actually work on your behalf.
              </p>
              <p className="text-white font-medium">
                So we built yarnnn—autonomous AI that accumulates your context and gets smarter the longer you use it.
              </p>
            </div>
          </section>

          {/* The Philosophy */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">What we believe</h2>

              <div className="space-y-16">
                <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Context is what makes AI useful</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      Raw intelligence without context is just a fancy autocomplete.
                      The difference between generic AI and useful AI is whether it
                      understands your world.
                    </p>
                    <p className="text-white/30 text-sm">
                      yarnnn connects to your platforms and accumulates context continuously.
                      The longer you use it, the deeper it understands.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Autonomy, not assistance</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      Most AI tools assist you—they help you do work faster. yarnnn
                      works on your behalf. It produces your deliverables on schedule.
                      You shift from operator to supervisor.
                    </p>
                    <p className="text-white/30 text-sm">
                      Your job is to decide what matters and approve when it&apos;s right.
                      Not to reassemble the same information week after week.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">AI should compound</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      Every sync cycle, every edit, every approval deepens yarnnn&apos;s
                      understanding. After 90 days, the accumulated context is irreplaceable.
                    </p>
                    <p className="text-white/30 text-sm">
                      This isn&apos;t a feature moat. It&apos;s a data moat. The value grows
                      monotonically with tenure.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Platforms have the signal</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      Your Slack channels, email threads, and Notion docs already contain
                      everything needed. The raw material for autonomous work is already there.
                    </p>
                    <p className="text-white/30 text-sm">
                      yarnnn connects directly to where your work happens—so you never
                      have to paste, summarize, or manually update context again.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* What yarnnn Is Not */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">What yarnnn is not</h2>
              <p className="text-white/50 mb-12 max-w-xl">
                yarnnn does one thing well. Here&apos;s what it doesn&apos;t try to be.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                  <h3 className="text-lg font-medium mb-2">Not a chatbot</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    TP is a partner, not a prompt box. You have conversations
                    that set up autonomous work—not endless back-and-forth.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-medium mb-2">Not stateless AI</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    ChatGPT and Claude forget between sessions. yarnnn accumulates
                    context continuously. It knows your world and it remembers.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-medium mb-2">Not a template tool</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    yarnnn doesn&apos;t fill in blanks. It synthesizes fresh
                    content from accumulated context, every time.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-medium mb-2">Not another agent startup</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Agent platforms are powerful but context-free. yarnnn&apos;s autonomy
                    is meaningful because it&apos;s powered by your actual work context.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Who It's For */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-12">Who it&apos;s for</h2>

              <div className="space-y-6">
                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-2">Solo professionals with recurring obligations</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Consultants, founders, ops leads. If you owe people recurring work
                    and you&apos;re tired of assembling it yourself, yarnnn handles it autonomously.
                  </p>
                </div>

                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-2">People whose work is spread across platforms</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Slack for team chat. Gmail for clients. Notion for docs. Calendar for meetings.
                    The more platforms you connect, the more powerful yarnnn becomes.
                  </p>
                </div>

                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-2">People who want to supervise, not operate</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    If you&apos;d rather review and approve than draft and assemble,
                    yarnnn shifts you from operator to supervisor. That&apos;s the model.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Ready to supervise instead of operate?
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Connect your platforms. Talk to TP.
                Watch your AI get smarter every day.
              </p>
              <Link
                href="/auth/login"
                className="inline-block px-8 py-4 bg-white text-black text-lg font-medium rounded-full hover:bg-white/90 transition-colors"
              >
                Start for free
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
