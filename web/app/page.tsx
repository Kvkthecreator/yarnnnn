import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackground } from "@/components/landing/ShaderBackground";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { IntegrationHub } from "@/components/landing/IntegrationHub";
import { TraceCard } from "@/components/landing/TraceCard";
import { CompoundsStepper } from "@/components/landing/CompoundsStepper";
import { SpotlightCard } from "@/components/landing/SpotlightCard";
import { ScrollReveal } from "@/components/landing/ScrollReveal";
import {
  getMarketingMetadata,
  getOrganizationSchema,
  getSoftwareApplicationSchema,
  getWebSiteSchema,
} from "@/lib/metadata";
import { CTA, PRIMARY_CTA_LABEL } from "@/lib/cta";

export const metadata: Metadata = getMarketingMetadata({
  title: "Shared memory for AI + human work | yarnnn",
  description:
    "Memory, context, and files that stay with you. Tell ChatGPT today, Claude knows it tomorrow — everything your AI learns lives in one place you own, and every change is yours to trace.",
  path: "/",
  keywords: [
    "shared ai memory",
    "ai memory",
    "ai memory for teams",
    "ai memory across apps",
    "chatgpt and claude memory",
    "ai context",
    "portable ai memory",
    "ai memory you own",
    "cross-llm memory",
  ],
});

export default function LandingPage() {
  // Emit Organization + SoftwareApplication + WebSite as one JSON-LD graph so
  // agents can identify both the product and the publisher programmatically.
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      getOrganizationSchema(),
      getSoftwareApplicationSchema(),
      getWebSiteSchema(),
    ],
  };

  return (
    <main className="relative min-h-screen w-full overflow-x-hidden bg-[#faf8f5] text-[#1a1a1a]">
      <GrainOverlay />
      <ShaderBackground />

      <div className="relative z-10">
        <LandingHeader />

        {/* ─── Section 1 — Hero (ratified verbatim) ──────────────────────── */}
        <section className="flex flex-col items-center justify-center px-6 py-32 md:py-40 min-h-[80vh]">
          <div className="max-w-6xl mx-auto w-full">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-12 lg:gap-20">
              <div className="text-center lg:text-left flex-1 max-w-2xl mx-auto lg:mx-0">
                <div className="font-brand text-4xl md:text-5xl mb-8 text-[#1a1a1a]">yarnnn</div>

                <h1 className="text-2xl sm:text-3xl md:text-4xl font-medium tracking-wide mb-6">
                  <span className="text-[#de5a2b]">Shared memory for AI + human work.</span>
                  <br />
                  <span className="text-[#1a1a1a]/90">Memory, context, and files that stay with you.</span>
                </h1>

                <p className="text-lg md:text-xl text-[#1a1a1a]/50 mb-10 max-w-xl mx-auto lg:mx-0 font-light">
                  Tell ChatGPT today, and Claude knows it tomorrow. Everything your AI learns
                  about you lives in one place you own — nothing lost, and every change is yours
                  to trace.
                </p>

                <div className="flex flex-col sm:flex-row items-center lg:items-start gap-4 mb-10">
                  <Link
                    href={CTA.signup}
                    className="inline-block px-8 py-4 bg-[#1a1a1a] text-white text-lg font-medium rounded-full hover:bg-[#1a1a1a]/90 transition-all"
                  >
                    {PRIMARY_CTA_LABEL}
                  </Link>
                  <Link
                    href={CTA.howItWorks}
                    className="inline-block px-8 py-4 glass-light text-[#1a1a1a] text-lg font-medium hover:bg-white/80 transition-all"
                  >
                    See how it works
                  </Link>
                </div>

              </div>

              <div className="flex-shrink-0 pb-16">
                <IntegrationHub />
              </div>
            </div>
          </div>
        </section>

        {/* ─── Section 2 — The problem (Beat 1, the self-audit gap) ──────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <ScrollReveal className="max-w-3xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-8 text-[#1a1a1a] leading-tight">
              Your AI&apos;s memory is trapped in one app.
            </h2>
            <div className="space-y-6 text-[#1a1a1a]/60 leading-relaxed text-lg font-light">
              <p>
                Every AI tool remembers a little about you now. But ChatGPT keeps its memory,
                Claude keeps its own, and neither lets you look inside or take it with you.
                Switch apps and you start over — re-explaining who you are, every time.
              </p>
              <p>
                So the context you build never really becomes yours. It&apos;s scattered across
                tools that each keep a private copy, and none of them can tell you how something
                got there or whether it&apos;s still true.
              </p>
            </div>
          </ScrollReveal>
        </section>

        {/* ─── Section 3 — The product (Beat 3, three mechanisms) ────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <ScrollReveal className="max-w-5xl mx-auto">
            <div className="text-center mb-16">
              <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
                One place for everything your AI knows. And it&apos;s yours.
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Card 1 — Traceable: the live demonstration (the moat's uncopyable property) */}
              <TraceCard />

              {/* Card 2 — Cross-LLM + team (ADR-404: the shared commons is the launch) */}
              <SpotlightCard spotlightColor="rgba(99,102,241,0.06)">
                <div className="p-8 h-full">
                  <div className="text-xs font-mono text-[#1a1a1a]/30 uppercase tracking-wider mb-4">
                    Works everywhere
                  </div>
                  <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Same memory — every AI, every teammate.</h3>
                  <p className="text-sm text-[#1a1a1a]/50 leading-relaxed">
                    Write it in one app, use it in the next. ChatGPT, Claude, your tools — and the
                    teammates you invite — all working from the same memory, everyone&apos;s changes
                    signed with their own name.
                  </p>
                </div>
              </SpotlightCard>

              {/* Card 3 — Compounds */}
              <SpotlightCard spotlightColor="rgba(16,185,129,0.06)">
                <div className="p-8 h-full">
                  <div className="text-xs font-mono text-[#1a1a1a]/30 uppercase tracking-wider mb-4">
                    Gets better
                  </div>
                  <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Fix it once, it stays fixed.</h3>
                  <p className="text-sm text-[#1a1a1a]/50 leading-relaxed">
                    Correct something once and it&apos;s corrected for good. Every time you use it,
                    it&apos;s a little sharper. It never resets.
                  </p>
                </div>
              </SpotlightCard>
            </div>

            <p className="text-center text-sm text-[#1a1a1a]/30 mt-10 font-mono">
              fix it once → it&apos;s fixed everywhere, for good
            </p>
          </ScrollReveal>
        </section>

        {/* ─── Section 4 — The delegation dial (AUTONOMY substrate) ──────── */}
        {/* Spec §0.8 + discourse §-9.6: this is the authored-autonomy capability,
            NOT the ADR-334 seat tier. No price/trial/checkout language here. */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <ScrollReveal className="max-w-4xl mx-auto">
            <div className="text-xs font-mono text-[#1a1a1a]/30 uppercase tracking-wider mb-4">
              In beta
            </div>
            <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
              Meet Freddie, a second set of eyes.
            </h2>

            <p className="text-[#1a1a1a]/50 leading-relaxed max-w-2xl mb-6">
              Freddie is the agent that tends your memory: today he reads what you connect, keeps
              it in order, and records every change so you can trace it. Next, he checks important
              work before it goes out — against rules you set. He only ever does as much as you
              allow.
            </p>

            <Link
              href="/freddie"
              className="inline-block text-sm font-medium text-[#de5a2b] hover:text-[#de5a2b]/80 transition-colors mb-10"
            >
              Meet Freddie →
            </Link>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="p-6 rounded-2xl bg-[#1a1a1a]/[0.02] border border-[#1a1a1a]/[0.06]">
                <div className="text-sm font-medium text-[#1a1a1a] mb-2">Goes ahead</div>
                <p className="text-sm text-[#1a1a1a]/50 leading-relaxed">
                  If it fits your rules and stays within what you&apos;ve allowed, it just does it.
                </p>
              </div>
              <div className="p-6 rounded-2xl bg-[#1a1a1a]/[0.02] border border-[#1a1a1a]/[0.06]">
                <div className="text-sm font-medium text-[#1a1a1a] mb-2">Asks you first</div>
                <p className="text-sm text-[#1a1a1a]/50 leading-relaxed">
                  If it&apos;s bigger than that, or it&apos;s unsure, it brings it to you. You decide.
                </p>
              </div>
              <div className="p-6 rounded-2xl bg-[#1a1a1a]/[0.02] border border-[#1a1a1a]/[0.06]">
                <div className="text-sm font-medium text-[#1a1a1a] mb-2">Waits for more</div>
                <p className="text-sm text-[#1a1a1a]/50 leading-relaxed">
                  If something&apos;s missing, it gathers what it needs first. It doesn&apos;t guess.
                </p>
              </div>
            </div>

            <p className="text-[#1a1a1a]/50 leading-relaxed max-w-2xl">
              You set the rules. He earns your trust on the record — and you&apos;re always in charge.
            </p>
          </ScrollReveal>
        </section>

        {/* ─── Section 5 — The insight (Beat 4) ──────────────────────────── */}
        {/* Proof block CUT in v1 (discourse §-9.1). Beat 5 moat is deck/VC-only. */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <ScrollReveal className="max-w-3xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-8 text-[#1a1a1a] leading-tight">
              The AI will change. Your memory shouldn&apos;t.
            </h2>
            <p className="text-[#1a1a1a]/60 leading-relaxed text-lg font-light">
              New models show up every few months. What lasts isn&apos;t any one of them — it&apos;s
              everything you&apos;ve taught them: your notes, your corrections, the history of how it
              all came to be. Keep that in one place you own, and switching tools costs you nothing.
              Ninety days in, starting over anywhere else means starting from zero.
            </p>

            {/* The accumulation trajectory — advance-through stepper (replaces the static bento) */}
            <div className="mt-12">
              <CompoundsStepper />
            </div>
          </ScrollReveal>
        </section>

        {/* ─── Section 6 — Pricing teaser + CTA (Beat 6) ─────────────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <ScrollReveal className="max-w-3xl mx-auto text-center">
            <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
              Free to keep. A plan for the work.
            </h2>
            <p className="text-[#1a1a1a]/50 mb-10 max-w-xl mx-auto leading-relaxed">
              Your memory is free forever — your files, your context, reachable from any AI you
              use. When the optional assistant runs on it, pick a plan for the work: each includes
              a monthly usage allowance, and you cap monthly spend with a budget you set. No seats.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href={CTA.signup}
                className="inline-block px-8 py-4 bg-[#1a1a1a] text-white text-lg font-medium rounded-full hover:bg-[#1a1a1a]/90 transition-all"
              >
                {PRIMARY_CTA_LABEL}
              </Link>
              <Link
                href={CTA.pricing}
                className="inline-block px-8 py-4 glass-light text-[#1a1a1a] text-lg font-medium hover:bg-white/80 transition-all"
              >
                See pricing
              </Link>
            </div>
          </ScrollReveal>
        </section>

        <LandingFooter />
      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
      />
    </main>
  );
}
