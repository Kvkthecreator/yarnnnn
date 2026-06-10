import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackground } from "@/components/landing/ShaderBackground";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { IntegrationHub } from "@/components/landing/IntegrationHub";
import { SpotlightCard, BentoGrid } from "@/components/landing/SpotlightCard";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";
import { CTA, PRIMARY_CTA_LABEL } from "@/lib/cta";

const VERTICAL_CHIPS = [
  "a newsletter",
  "a portfolio",
  "a shop",
  "a pipeline",
  "a book of business",
];

export const metadata: Metadata = getMarketingMetadata({
  title: "The workspace where the work you run compounds | yarnnn",
  description:
    "Agents you own produce your work. Corrections carry forward. A judgment seat answers for what ships — even when you're not there. The workspace for a solopreneur's newsletter, portfolio, shop, or pipeline.",
  path: "/",
  keywords: [
    "ai agents",
    "autonomous ai agents",
    "ai for solopreneurs",
    "ai for your newsletter",
    "ai for your portfolio",
    "ai for your shop",
    "accountable ai",
    "ai judgment seat",
    "cumulative ai workspace",
    "ai agent operating system",
    "owned ai context",
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

        {/* ─── Section 1 — Hero (ratified verbatim) ──────────────────────── */}
        <section className="flex flex-col items-center justify-center px-6 py-32 md:py-40 min-h-[80vh]">
          <div className="max-w-6xl mx-auto w-full">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-12 lg:gap-20">
              <div className="text-center lg:text-left flex-1 max-w-2xl mx-auto lg:mx-0">
                <div className="font-brand text-4xl md:text-5xl mb-8 text-[#1a1a1a]">yarnnn</div>

                <h1 className="text-2xl sm:text-3xl md:text-4xl font-medium tracking-wide text-[#1a1a1a]/90 mb-6">
                  The work you run shouldn&apos;t reset.
                </h1>

                <p className="text-lg md:text-xl text-[#1a1a1a]/50 mb-10 max-w-xl mx-auto lg:mx-0 font-light">
                  YARNNN is the workspace where it compounds. Agents you own produce it.
                  Corrections carry forward. A judgment seat answers for what ships — even
                  when you&apos;re not there.
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
                    See how it compounds
                  </Link>
                </div>

                <div className="flex flex-wrap justify-center lg:justify-start gap-x-3 gap-y-1 text-sm text-[#1a1a1a]/40 font-light">
                  {VERTICAL_CHIPS.map((chip, i) => (
                    <span key={chip} className="whitespace-nowrap">
                      {chip}
                      {i < VERTICAL_CHIPS.length - 1 && (
                        <span className="text-[#1a1a1a]/20 ml-3">·</span>
                      )}
                    </span>
                  ))}
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
          <div className="max-w-3xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-8 text-[#1a1a1a] leading-tight">
              Every platform now sells you an AI delegate. None will tell you if its judgment
              is any good.
            </h2>
            <div className="space-y-6 text-[#1a1a1a]/60 leading-relaxed text-lg font-light">
              <p>
                The agents got good. Scheduled runs, persistent memory, work done while you&apos;re
                away — that part is everywhere now. But look closer: the same vendor that builds
                the delegate grades the delegate. Memory you can&apos;t read. Actions with no
                attributed trail. &ldquo;Improvement&rdquo; you take on faith.
              </p>
              <p>
                And underneath it all, the work stays episodic. Every artifact is generated fresh.
                Fix today&apos;s output and tomorrow starts from the same place. Nothing is owned,
                so nothing compounds — and nothing answers for itself.
              </p>
            </div>
          </div>
        </section>

        {/* ─── Section 3 — The product (Beat 3, three mechanisms) ────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-16">
              <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
                A workspace where nothing is lost and everything answers for itself.
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="p-8 rounded-2xl border border-[#1a1a1a]/[0.06] bg-[#1a1a1a]/[0.02]">
                <div className="text-xs font-mono text-[#1a1a1a]/30 uppercase tracking-wider mb-4">
                  Traceable
                </div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Everything is traceable.</h3>
                <p className="text-sm text-[#1a1a1a]/50 leading-relaxed">
                  Every file has an author. Every change has a revision. The deck your agent
                  built cites the files it was composed from.
                </p>
              </div>
              <div className="p-8 rounded-2xl border border-[#1a1a1a]/[0.06] bg-[#1a1a1a]/[0.02]">
                <div className="text-xs font-mono text-[#1a1a1a]/30 uppercase tracking-wider mb-4">
                  Compounds
                </div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Corrections compound.</h3>
                <p className="text-sm text-[#1a1a1a]/50 leading-relaxed">
                  Fix one source file and every future artifact inherits the fix. Work here is
                  monotonically improving. Work everywhere else resets.
                </p>
              </div>
              <div className="p-8 rounded-2xl border border-[#1a1a1a]/[0.06] bg-[#1a1a1a]/[0.02]">
                <div className="text-xs font-mono text-[#1a1a1a]/30 uppercase tracking-wider mb-4">
                  Judged
                </div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Judgment is independent.</h3>
                <p className="text-sm text-[#1a1a1a]/50 leading-relaxed">
                  Consequential actions pass through a Reviewer — a judgment seat you author the
                  principles for, whose calls are reconciled against what actually happened. Not
                  a safety filter. A track record.
                </p>
              </div>
            </div>

            <p className="text-center text-sm text-[#1a1a1a]/30 mt-10 font-mono">
              fix one file → every future artifact inherits it
            </p>
          </div>
        </section>

        {/* ─── Section 4 — The delegation dial (AUTONOMY substrate) ──────── */}
        {/* Spec §0.8 + discourse §-9.6: this is the authored-autonomy capability,
            NOT the ADR-334 seat tier. No price/trial/checkout language here. */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
              You decide how much it runs without you.
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="p-6 rounded-2xl bg-[#1a1a1a]/[0.02] border border-[#1a1a1a]/[0.06]">
                <div className="text-sm font-medium text-[#1a1a1a] mb-2">Supervised</div>
                <p className="text-sm text-[#1a1a1a]/50 leading-relaxed">
                  Every consequence waits for your approval.
                </p>
              </div>
              <div className="p-6 rounded-2xl bg-[#1a1a1a]/[0.02] border border-[#1a1a1a]/[0.06]">
                <div className="text-sm font-medium text-[#1a1a1a] mb-2">Delegated</div>
                <p className="text-sm text-[#1a1a1a]/50 leading-relaxed">
                  It acts within ceilings you declared.
                </p>
              </div>
              <div className="p-6 rounded-2xl bg-[#1a1a1a]/[0.02] border border-[#1a1a1a]/[0.06]">
                <div className="text-sm font-medium text-[#1a1a1a] mb-2">Autonomous</div>
                <p className="text-sm text-[#1a1a1a]/50 leading-relaxed">
                  It runs the framework you wrote, and the trail shows you everything.
                </p>
              </div>
            </div>

            <p className="text-[#1a1a1a]/50 leading-relaxed max-w-2xl">
              Trust is earned in the record, and the dial only moves when you move it.
            </p>
          </div>
        </section>

        {/* ─── Section 5 — The insight (Beat 4) ──────────────────────────── */}
        {/* Proof block CUT in v1 (discourse §-9.1). Beat 5 moat is deck/VC-only. */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-3xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-8 text-[#1a1a1a] leading-tight">
              Execution is becoming a commodity. What compounds is yours.
            </h2>
            <p className="text-[#1a1a1a]/60 leading-relaxed text-lg font-light">
              As more work gets delegated, what&apos;s left that matters is the context only you
              have and the judgment only you can authorize. That&apos;s the asset this workspace
              accumulates: your files, your corrections, your watchlist&apos;s history, your
              seat&apos;s track record. Ninety days in, starting over anywhere else means starting
              from zero. That&apos;s not lock-in. That&apos;s accumulation.
            </p>

            {/* The accumulation trajectory — quiet bento, no moat-naming per beat-timing */}
            <div className="mt-12">
              <BentoGrid>
                <SpotlightCard className="md:col-span-2" spotlightColor="rgba(99,102,241,0.06)">
                  <div className="p-6 h-full flex flex-col justify-center">
                    <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Day 1</div>
                    <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                      The asset exists. You author context; the first artifact synthesizes from it,
                      with provenance.
                    </p>
                  </div>
                </SpotlightCard>
                <SpotlightCard className="md:col-span-2" spotlightColor="rgba(14,165,233,0.06)">
                  <div className="p-6 h-full flex flex-col justify-center">
                    <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Day 30</div>
                    <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                      Corrections have compounded. Every cycle starts from a higher floor than the
                      last.
                    </p>
                  </div>
                </SpotlightCard>
                <SpotlightCard className="md:col-span-2" spotlightColor="rgba(16,185,129,0.06)">
                  <div className="p-6 h-full flex flex-col justify-center">
                    <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Day 90</div>
                    <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                      The operation contradicts nothing, forgets nothing, and the judgment trail
                      reads like a track record.
                    </p>
                  </div>
                </SpotlightCard>
              </BentoGrid>
            </div>
          </div>
        </section>

        {/* ─── Section 6 — Pricing teaser + CTA (Beat 6) ─────────────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
              Free to keep. Priced when it runs for you.
            </h2>
            <p className="text-[#1a1a1a]/50 mb-10 max-w-xl mx-auto leading-relaxed">
              The workspace is free forever — your files, your context, reachable from any AI you
              use. When you&apos;re ready to run an operation on it, seats start at $149/month —
              priced by how much you delegate, not by features.
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
