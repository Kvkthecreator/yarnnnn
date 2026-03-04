import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackground } from "@/components/landing/ShaderBackground";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { IntegrationHub } from "@/components/landing/IntegrationHub";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata: Metadata = getMarketingMetadata({
  title: "Autonomous AI That Knows Your Work",
  description:
    "yarnnn connects to your work tools, prepares drafts for recurring work, and improves from your edits over time.",
  path: "/",
  keywords: [
    "autonomous ai",
    "ai work assistant",
    "thinking partner",
    "work automation",
    "weekly report automation",
  ],
});

export default function LandingPage() {
  const websiteSchema = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: BRAND.name,
    url: BRAND.url,
    description: BRAND.description,
    publisher: {
      "@type": "Organization",
      name: BRAND.name,
      url: BRAND.url,
    },
  };

  return (
    <main className="relative min-h-screen w-full overflow-x-hidden bg-[#faf8f5] text-[#1a1a1a]">
      <GrainOverlay />
      <ShaderBackground />

      <div className="relative z-10">
        <LandingHeader />

        <section className="flex flex-col items-center justify-center px-6 py-32 md:py-40 min-h-[80vh]">
          <div className="max-w-6xl mx-auto w-full">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-12 lg:gap-20">
              <div className="text-center lg:text-left flex-1 max-w-2xl mx-auto lg:mx-0">
                <div className="font-brand text-4xl md:text-5xl mb-8 text-[#1a1a1a]">yarnnn</div>

                <h1 className="text-2xl sm:text-3xl md:text-4xl font-medium tracking-wide text-[#1a1a1a]/90 mb-6">
                  AI that does the first draft
                  <br />
                  <span className="text-[#1a1a1a]">for your recurring work.</span>
                </h1>

                <p className="text-lg md:text-xl text-[#1a1a1a]/50 mb-12 max-w-xl mx-auto lg:mx-0 font-light">
                  Connect Slack, Gmail, Notion, and Calendar.
                  Tell yarnnn what you need each week.
                  Review and approve what it prepares.
                </p>

                <Link
                  href="/auth/login"
                  className="inline-block px-8 py-4 glass-light text-[#1a1a1a] text-lg font-medium hover:bg-white/80 transition-all"
                >
                  Start with yarnnn
                </Link>
              </div>

              <div className="flex-shrink-0 pb-16">
                <IntegrationHub />
              </div>
            </div>
          </div>
        </section>

        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <div>
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">The problem</div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
                  Most AI forgets your work.
                  <br />
                  <span className="text-[#1a1a1a]/50">So you repeat yourself every time.</span>
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed mb-6">
                  You copy context into prompts, rewrite the same updates,
                  and lose time gathering information from multiple tools.
                </p>
                <p className="text-[#1a1a1a]/50 leading-relaxed">
                  yarnnn is built so you can review work, not rebuild it.
                </p>
              </div>
              <div className="glass-card-light p-6">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">How yarnnn is different</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Your tools in. Drafts out.</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  yarnnn reads from your connected sources, writes drafts for recurring work,
                  and improves as you edit and approve.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a] text-center">
              How yarnnn works
            </h2>
            <p className="text-[#1a1a1a]/50 text-center mb-16 max-w-xl mx-auto">
              Three simple steps.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">01</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Tell it what to write</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Example: weekly team update, meeting prep, or client summary.
                </p>
              </div>

              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">02</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Connect your tools</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Slack, Gmail, Notion, and Calendar give yarnnn the context it needs.
                </p>
              </div>

              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">03</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Review and approve</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  yarnnn does the first draft. You stay in control and approve final output.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <div className="md:order-2">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">What gets better</div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
                  Less editing over time.
                  <br />
                  <span className="text-[#1a1a1a]/50">Better first drafts each week.</span>
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed mb-6">
                  Every approved draft teaches yarnnn your style and priorities.
                  That means future drafts are closer to what you want.
                </p>
                <p className="text-[#1a1a1a]/50 leading-relaxed">
                  You spend less time writing from scratch and more time making decisions.
                </p>
              </div>
              <div className="glass-card-light p-6 md:order-1">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">Typical progression</div>
                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/10 flex items-center justify-center text-xs text-[#1a1a1a]/50 shrink-0 mt-0.5">1</div>
                    <p className="text-[#1a1a1a]/70 text-sm">Week 1: solid first draft</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/10 flex items-center justify-center text-xs text-[#1a1a1a]/50 shrink-0 mt-0.5">2</div>
                    <p className="text-[#1a1a1a]/70 text-sm">Week 2-4: fewer fixes needed</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/20 flex items-center justify-center text-xs text-[#1a1a1a]/70 shrink-0 mt-0.5">3</div>
                    <p className="text-[#1a1a1a] text-sm font-medium">Month 2+: mostly approve and move on</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
              Common use cases
            </h2>
            <p className="text-[#1a1a1a]/50 mb-12 max-w-xl">
              If it repeats every week or month, yarnnn can probably help.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="glass-card-light p-6">
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Weekly team updates</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">Summarize Slack channels into one clear update.</p>
              </div>

              <div className="glass-card-light p-6">
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Meeting prep</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">Prepare context before meetings from email, docs, and calendar.</p>
              </div>

              <div className="glass-card-light p-6">
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Status reports</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">Build stakeholder updates using your connected sources.</p>
              </div>
            </div>
          </div>
        </section>

        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
              Start with one workflow.
            </h2>
            <p className="text-[#1a1a1a]/50 mb-4">Free: 2 active workflows</p>
            <p className="text-[#1a1a1a]/50 mb-4">Starter: 5 active workflows</p>
            <p className="text-[#1a1a1a]/50 mb-10">Pro: unlimited workflows — $19/mo</p>
            <Link
              href="/auth/login"
              className="inline-block px-8 py-4 glass-light text-[#1a1a1a] text-lg font-medium hover:bg-white/80 transition-all"
            >
              Start with yarnnn
            </Link>
          </div>
        </section>

        <LandingFooter />
      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteSchema) }}
      />
    </main>
  );
}
