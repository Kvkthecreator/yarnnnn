import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { SpotlightCard } from "@/components/landing/SpotlightCard";
import { ScrollReveal } from "@/components/landing/ScrollReveal";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";
import { CTA, PRIMARY_CTA_LABEL } from "@/lib/cta";

export const metadata: Metadata = getMarketingMetadata({
  title: "About — the memory layer no AI company can build",
  description:
    "A single AI company's memory is locked to its own app, by design. The memory that works across all of them can't be owned by any one of them. So we built it — and here's what we believe.",
  path: "/about",
  keywords: [
    "about yarnnn",
    "ai memory you own",
    "neutral ai memory",
    "cross-llm memory",
    "model-agnostic ai",
    "portable ai memory",
  ],
});

const BELIEFS = [
  {
    title: "Your memory should be yours",
    body: "Built once, kept forever, and available everywhere. The memory is the thing that lasts; the AI models come and go. Everywhere else, it's locked inside someone else's app.",
    sub: "Day 1 it exists. Day 90 it's irreplaceable — not from lock-in, but because it added up.",
  },
  {
    title: "Written by you, not guessed",
    body: "Your notes, your rules, your voice — written by you, kept forever, and never quietly changed. Every edit has a name and a date on it.",
    sub: "Authored, not inferred.",
  },
  {
    title: "Neutral across every AI",
    body: "One memory, available to every tool, with no company in the middle deciding what you're allowed to take with you. The portability is the whole point.",
    sub: "A locked-in memory can't do this. That's the moat.",
  },
  {
    title: "Built for more than one of you",
    body: "You, your teammates, your tools, and even your own AI assistants can all add to the same memory — and you can always see who added what. On your own is just the simplest case.",
    sub: "One memory, many contributors.",
  },
  {
    title: "A checker, separate from the doer (beta)",
    body: "The assistant that does the work shouldn't be the one that decides it's good. So important calls go to a separate checker, against rules you set, measured against what actually happened.",
    sub: "Keeping them separate is what makes handing over more trust safe, not reckless.",
  },
  {
    title: "Receipts, not claims",
    body: "377 decisions written down in the open; every change tracked at the source; built for real use and run on our own work.",
    sub: "The record is the proof.",
  },
];

export default function AboutPage() {
  const aboutSchema = {
    "@context": "https://schema.org",
    "@type": "AboutPage",
    name: "About yarnnn",
    description: metadata.description ?? undefined,
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
          {/* Hero — self-audit thesis */}
          <section className="max-w-4xl mx-auto px-6 py-24 md:py-32">
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-10 tracking-tight leading-[1.1]">
              We built the memory layer
              <br />
              <span className="text-white/50">the AI giants can&apos;t.</span>
            </h1>
            <div className="max-w-2xl space-y-6 text-white/50">
              <p>
                Every AI tool has memory now. But each one&apos;s memory is locked inside its own
                app — that&apos;s the whole point of it. None of them will ever let your context
                follow you to a competitor.
              </p>
              <p>
                A memory that works across all of them can&apos;t belong to any one of them. It has
                to be neutral — and being neutral across your rivals is the one thing a rival
                can&apos;t do. So nobody builds it, because nobody can.
              </p>
              <p>
                So we did: one place that holds everything your AI tools know about you, that you
                own, that keeps a full history of every change, and that any model can read. Under
                the hood, it&apos;s git&apos;s model for memory — every change signed, versioned,
                and yours.
              </p>
              <p className="text-white font-medium">
                We built it ourselves, run it on our own work, and write down every decision in the
                open.
              </p>
            </div>
          </section>

          {/* What we believe — current canon */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">What we believe</h2>

              <div className="space-y-16">
                {BELIEFS.map((b) => (
                  <div key={b.title} className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                    <div>
                      <h3 className="text-lg font-medium text-white">{b.title}</h3>
                    </div>
                    <div className="text-white/50">
                      <p className="mb-4">{b.body}</p>
                      <p className="text-white/30 text-sm">{b.sub}</p>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollReveal>
          </section>

          {/* What yarnnn is not */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">What yarnnn is not</h2>
              <p className="text-white/50 mb-12 max-w-xl">
                We&apos;re focused. These are things we intentionally chose not to be.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {([
                  {
                    title: "Not a memory locked to one app",
                    desc: "Your memory isn't trapped inside ChatGPT or Claude. It's one place both can read — and one you can take anywhere.",
                  },
                  {
                    title: "Not a plain folder of files",
                    desc: "A storage folder hands you back files. yarnnn hands you back the story too: who wrote each version, and exactly how it changed.",
                  },
                  {
                    title: "Not a notes app",
                    desc: "Notes just sit there. This flows in from your tools, stays organized on its own, and feeds straight into every AI you use.",
                  },
                  {
                    title: "Not an AI that grades its own homework (beta)",
                    desc: "When the checker arrives, it's separate and neutral — measured against what really happened, not a company judging its own model.",
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
            </ScrollReveal>
          </section>

          {/* Who it's for — bounded-operation psychographic */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">Who yarnnn is for</h2>
              <p className="text-white/50 mb-12 max-w-xl">
                Anyone tired of re-explaining themselves to every new AI — and anyone who wants the
                context they&apos;ve built to be theirs to keep.
              </p>

              <div className="flex flex-wrap gap-3 mb-12">
                {["people who use ChatGPT and Claude", "small teams", "people building their own AI agents", "anyone whose work lives in five apps"].map(
                  (chip) => (
                    <span
                      key={chip}
                      className="px-4 py-2 rounded-full bg-white/[0.04] border border-white/10 text-sm text-white/60"
                    >
                      {chip}
                    </span>
                  ),
                )}
              </div>

              <div className="space-y-4">
                {([
                  {
                    title: "You use more than one AI",
                    desc: "If you bounce between ChatGPT, Claude, and a few tools and you're tired of repeating yourself, this gives all of them the same memory.",
                  },
                  {
                    title: "You've built up context worth keeping",
                    desc: "Notes, decisions, history — the stuff that makes an AI actually useful for you. Keep it in one place you own instead of scattered and rented.",
                  },
                  {
                    title: "You want to hand off more, safely (beta)",
                    desc: "When you're ready, add a checker that reviews important work against your rules — so you can step back without losing the thread.",
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
            </ScrollReveal>
          </section>

          {/* CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Your memory should follow you.
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Start free. Add a note or connect a tool, watch it show up in every AI you use, and
                add the checker when you&apos;re ready.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link
                  href={CTA.signup}
                  className="inline-block px-8 py-4 bg-white text-black text-lg font-medium rounded-full hover:bg-white/90 transition-colors"
                >
                  {PRIMARY_CTA_LABEL}
                </Link>
                <Link
                  href={CTA.howItWorks}
                  className="inline-block px-8 py-4 border border-white/20 text-white text-lg font-medium rounded-full hover:bg-white/10 transition-colors"
                >
                  See how it works
                </Link>
              </div>
            </ScrollReveal>
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
