import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackground } from "@/components/landing/ShaderBackground";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { IntegrationHub } from "@/components/landing/IntegrationHub";
import { TraceCard } from "@/components/landing/TraceCard";
import { CompoundsStepper } from "@/components/landing/CompoundsStepper";
import { AppShowcase } from "@/components/landing/AppShowcase";
import { ScrollReveal } from "@/components/landing/ScrollReveal";
import {
  getMarketingMetadata,
  getOrganizationSchema,
  getSoftwareApplicationSchema,
  getWebSiteSchema,
} from "@/lib/metadata";
import { CTA, LEAD_DOOR_CTA_LABEL } from "@/lib/cta";

/**
 * Landing page — CANON-LOCK-2026-07-30 (working canon).
 *
 * The hero sequence is the lock's §1 assembled arc, verbatim:
 *   hook → headline pair → subhead → CTA + connector chips → (below the fold)
 *   product chapter → attribution proof → recognition pull-quote → pricing.
 *
 * Discipline notes:
 * - Model names live in the connector chips under the CTA, never in the subhead.
 * - App names (Chat/Studio/Files/Agents) appear ONLY in the product chapter
 *   (AppShowcase) — the roster rule keeps them out of the hero.
 * - "Nothing to set up" is guarded by falsifier 5 (CANON-LOCK §8.5); if it
 *   fires, that line comes out of the subhead here and in the canon together.
 */

export const metadata: Metadata = getMarketingMetadata({
  title: "your true AI-first workspace | yarnnn",
  description:
    "One workspace for you, your people, and the AI you already use. Nothing to set up — and every change signed by whoever made it, human or not.",
  path: "/",
  keywords: [
    "ai workspace",
    "ai-first workspace",
    "shared ai workspace",
    "co-work with ai",
    "work with chatgpt and claude together",
    "shared workspace for ai and humans",
    "ai collaboration workspace",
    "ai workspace you own",
    "cross-llm workspace",
  ],
});

const CONNECTOR_CHIPS = ["ChatGPT", "Claude", "Gemini"];

export default function LandingPage() {
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

        {/* ─── Section 1 — Hero (the canon arc: hook → headline → subhead → CTA) ── */}
        <section className="flex flex-col items-center justify-center px-6 py-32 md:py-40 min-h-[80vh]">
          <div className="max-w-6xl mx-auto w-full">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-12 lg:gap-20">
              <div className="text-center lg:text-left flex-1 max-w-2xl mx-auto lg:mx-0">
                <div className="font-brand text-4xl md:text-5xl mb-8 text-[#1a1a1a]">yarnnn</div>

                {/* The hook (Slot 3) */}
                <p className="text-sm md:text-base font-mono text-[#1a1a1a]/40 uppercase tracking-wider mb-5">
                  Made with AI. Lost in the chat.
                </p>

                {/* The headline pair (Slot 2, ratified-stable) */}
                <h1 className="text-3xl sm:text-4xl md:text-5xl font-medium tracking-tight mb-6 leading-[1.15]">
                  <span className="text-[#1a1a1a]">your true AI-first workspace.</span>
                  <br />
                  <span className="text-[#de5a2b]">co-work like never before.</span>
                </h1>

                {/* The subhead (Slot 2, working canon — signed clause non-optional) */}
                <p className="text-lg md:text-xl text-[#1a1a1a]/50 mb-10 max-w-xl mx-auto lg:mx-0 font-light">
                  One workspace for you, your people, and the AI you already use.
                  Nothing to set up — and every change signed by whoever made it,
                  human or not.
                </p>

                {/* CTA — the lead door (GROWTH-LOOP Channel 1) + connector chips */}
                <div className="flex flex-col items-center lg:items-start gap-4 mb-4">
                  <div className="flex flex-col sm:flex-row items-center lg:items-start gap-4">
                    <Link
                      href={CTA.signup}
                      className="inline-block px-8 py-4 bg-[#1a1a1a] text-white text-lg font-medium rounded-full hover:bg-[#1a1a1a]/90 transition-all"
                    >
                      {LEAD_DOOR_CTA_LABEL}
                    </Link>
                    <Link
                      href={CTA.howItWorks}
                      className="inline-block px-8 py-4 glass-light text-[#1a1a1a] text-lg font-medium hover:bg-white/80 transition-all"
                    >
                      See how it works
                    </Link>
                  </div>
                  <div className="flex items-center gap-2 pl-1">
                    <span className="text-xs text-[#1a1a1a]/30 font-mono">works with</span>
                    {CONNECTOR_CHIPS.map((c) => (
                      <span
                        key={c}
                        className="rounded-full border border-[#1a1a1a]/[0.1] bg-white/70 px-3 py-1 text-xs font-medium text-[#1a1a1a]/60"
                      >
                        {c}
                      </span>
                    ))}
                    <span className="text-xs text-[#1a1a1a]/30 font-mono">· more</span>
                  </div>
                </div>
              </div>

              <div className="flex-shrink-0 pb-16">
                <IntegrationHub />
              </div>
            </div>
          </div>
        </section>

        {/* ─── Section 2 — The problem (Beat 1: the copy-paste seam) ─────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <ScrollReveal className="max-w-3xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-8 text-[#1a1a1a] leading-tight">
              The real work happens with AI now — in a window only you can see.
            </h2>
            <div className="space-y-6 text-[#1a1a1a]/60 leading-relaxed text-lg font-light">
              <p>
                Drafts, decisions, analysis — the actual thinking happens in an AI chat.
                And then it&apos;s gone: scrolled past, unfindable next week, invisible to
                the people it was made for.
              </p>
              <p>
                Getting it in front of anyone else is still copy-paste. You do the work
                with AI, then you ferry it — into a doc, into a thread, into an email —
                by hand, every time.
              </p>
            </div>

            {/* The recognition sentence (Slot 4) — the conversion point */}
            <blockquote className="mt-10 border-l-2 border-[#de5a2b]/40 pl-6">
              <p className="text-xl md:text-2xl font-light text-[#1a1a1a]/70 italic">
                &ldquo;I&apos;m the human clipboard between my AI and my team.&rdquo;
              </p>
              <p className="mt-3 text-sm text-[#1a1a1a]/35">
                If that&apos;s you, this is the fix.
              </p>
            </blockquote>
          </ScrollReveal>
        </section>

        {/* ─── Section 3 — The product chapter (feature-forward, deck slides 6–10) ── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <ScrollReveal className="text-center mb-20">
              <div className="text-xs font-mono text-[#1a1a1a]/30 uppercase tracking-wider mb-4">
                Built in — nothing to assemble
              </div>
              <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
                Dedicated apps, a shared file system,
                <br className="hidden md:block" /> documents you build with AI.
              </h2>
              <p className="text-[#1a1a1a]/45 max-w-2xl mx-auto font-light">
                Everything below ships with the workspace. Connect your AI and it works in
                the same apps, on the same files, under its own name.
              </p>
            </ScrollReveal>

            <AppShowcase />
          </div>
        </section>

        {/* ─── Section 4 — The proof (the attribution walk) ──────────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <ScrollReveal className="max-w-5xl mx-auto">
            <div className="flex flex-col lg:flex-row gap-12 lg:items-center">
              <div className="flex-1 max-w-xl">
                <div className="text-xs font-mono text-[#1a1a1a]/30 uppercase tracking-wider mb-4">
                  The part no one else can show you
                </div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a] leading-tight">
                  Every change, signed by whoever made it.
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed font-light mb-4">
                  You on Tuesday. Your agent on Thursday. Claude on Friday. One file, three
                  authors — and you can walk every line back to who wrote it, when, and why.
                </p>
                <p className="text-[#1a1a1a]/50 leading-relaxed font-light">
                  A single-vendor tool structurally can&apos;t draw this picture: it only
                  ever sees itself. A shared workspace where every principal signs its work
                  is the one place the whole story exists.
                </p>
              </div>
              <div className="flex-1 w-full max-w-lg">
                <TraceCard />
              </div>
            </div>
          </ScrollReveal>
        </section>

        {/* ─── Section 5 — The insight (Beat 4) ──────────────────────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <ScrollReveal className="max-w-3xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-8 text-[#1a1a1a] leading-tight">
              The AI will change. Your record shouldn&apos;t.
            </h2>
            <p className="text-[#1a1a1a]/60 leading-relaxed text-lg font-light">
              New models show up every few months, and each one is better than the last.
              What lasts isn&apos;t any one of them — it&apos;s the signed record of the
              work: what was decided, what was corrected, who did what. Keep that in one
              place you own, and every new model makes your workspace more valuable, not
              less. Ninety days in, starting over anywhere else means starting from zero.
            </p>

            <div className="mt-12">
              <CompoundsStepper />
            </div>
          </ScrollReveal>
        </section>

        {/* ─── Section 6 — Pricing teaser + CTA (Beat 6) ─────────────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <ScrollReveal className="max-w-3xl mx-auto text-center">
            <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
              Free for two. A seat for the rest.
            </h2>
            <p className="text-[#1a1a1a]/50 mb-10 max-w-xl mx-auto leading-relaxed">
              The workspace is free for you and a teammate — your files, your record,
              reachable from any AI you use. From the 3rd person, each extra seat is paid;
              usage is pay-as-you-go from one shared balance. AI connections are always
              free — never a seat.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href={CTA.signup}
                className="inline-block px-8 py-4 bg-[#1a1a1a] text-white text-lg font-medium rounded-full hover:bg-[#1a1a1a]/90 transition-all"
              >
                {LEAD_DOOR_CTA_LABEL}
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
