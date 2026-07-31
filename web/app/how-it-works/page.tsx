import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { SpotlightCard } from "@/components/landing/SpotlightCard";
import { ScrollReveal } from "@/components/landing/ScrollReveal";
import { StepFlow } from "@/components/landing/StepFlow";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";
import { CTA, PRIMARY_CTA_LABEL } from "@/lib/cta";

/**
 * How it works — product mechanics (re-cut 2026-07-31).
 *
 * This page sells the system itself: a real file system, agents out of the
 * box, documents you build and own — and portability as the consequence.
 * The "why it's different" thesis argument moved to /about; connection
 * concepts are one step here, not the frame.
 */

export const metadata: Metadata = getMarketingMetadata({
  title: "How yarnnn works — a real file system for work made with AI",
  description:
    "A shared file system, agents ready out of the box, documents you build and own — every change signed, human or not. And because the work is real files you own, it goes wherever you go.",
  path: "/how-it-works",
  keywords: [
    "how yarnnn works",
    "ai workspace",
    "ai file system",
    "co-work with ai",
    "ai agents out of the box",
    "documents you own",
    "shared workspace for ai and humans",
  ],
});

const STEPS = [
  {
    number: "01",
    title: "Your workspace is a real file system",
    body: "Not a chat scroll — files and folders you own. Everything anyone makes here, human or AI, lands as a file you can open next week: named, organized, findable. The workspace starts empty and working; there's nothing to set up.",
  },
  {
    number: "02",
    title: "Agents are ready out of the box",
    body: "From the first minute you can talk to named agents — a thinker, a researcher, a designer. They read your files, answer grounded in what's actually there, and write their work back into the same file system. The best engine for the job rides behind each name, and you can swap it any time.",
  },
  {
    number: "03",
    title: "Build documents, decks and pages — and keep them",
    body: "Studio is where artifacts take shape: write directly, or ask an agent to draft against your files. Either way, every edit lands as a signed revision with full history — you can walk any document back to who changed what, when, and why.",
  },
  {
    number: "04",
    title: "Connect the AI you already use",
    body: "Attach ChatGPT, Claude, or Gemini and it works in the same file system, under its own name. The thinking you're already doing in a chat window finally has somewhere to land — no more ferrying it out by hand.",
  },
  {
    number: "05",
    title: "And that's why your work travels",
    body: "Because the work is real files you own — not history trapped in someone's app — it goes wherever you go. Share a document with a link. Invite a teammate into the workspace. Reach it from any AI you use. Leave, and it's still yours.",
  },
];

const GUARANTEES = [
  {
    tag: "Real files",
    title: "A workspace, not a chat log",
    desc: "Everything made here lands as a file you can open, organize, and build on. Nothing evaporates in a scroll.",
  },
  {
    tag: "Every change signed",
    title: "A name on every write",
    desc: "You, your teammates, your agents, every connected AI — each change carries the name of whoever made it, human or not.",
  },
  {
    tag: "Yours to take",
    title: "Owned, not rented",
    desc: "Files, documents, history — yours. Share them, hand them off, take them with you. No one's app is holding your work hostage.",
  },
];

export default function HowItWorksPage() {
  const howToSchema = {
    "@context": "https://schema.org",
    "@type": "HowTo",
    name: "How yarnnn works",
    description: metadata.description ?? undefined,
    url: `${BRAND.url}/how-it-works`,
    step: STEPS.map((s) => ({ "@type": "HowToStep", name: `${s.title} — ${s.body}` })),
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
            <p className="text-white/40 text-sm uppercase tracking-widest mb-4">How It Works</p>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-10 tracking-tight leading-[1.1]">
              Everything you make with AI
              <br />
              <span className="text-white/50">lands somewhere real.</span>
            </h1>
            <p className="max-w-2xl text-white/50 text-lg">
              yarnnn is a workspace built the way AI-first work actually happens: a shared
              file system at the center, agents you can talk to from the first minute, and
              documents that stay yours — every change signed by whoever made it, human or
              not. Here&apos;s the system, top to bottom.
            </p>
          </section>

          {/* The five-step system walk */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <StepFlow steps={STEPS} />
          </section>

          {/* The three guarantees + CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-5xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-12 text-center">
                What the system guarantees.
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
                {GUARANTEES.map((g) => (
                  <SpotlightCard key={g.tag} variant="dark" spotlightSize={300}>
                    <div className="p-6 h-full">
                      <div className="text-xs font-mono text-white/30 uppercase tracking-wider mb-4">
                        {g.tag}
                      </div>
                      <h3 className="text-base font-medium mb-3">{g.title}</h3>
                      <p className="text-white/40 text-sm leading-relaxed">{g.desc}</p>
                    </div>
                  </SpotlightCard>
                ))}
              </div>

              <div className="text-center">
                <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                  <Link
                    href={CTA.signup}
                    className="inline-block px-8 py-4 bg-white text-black text-lg font-medium rounded-full hover:bg-white/90 transition-colors"
                  >
                    {PRIMARY_CTA_LABEL}
                  </Link>
                  <Link
                    href={CTA.pricing}
                    className="inline-block px-8 py-4 border border-white/20 text-white text-lg font-medium rounded-full hover:bg-white/10 transition-colors"
                  >
                    See pricing
                  </Link>
                </div>
              </div>
            </ScrollReveal>
          </section>
        </main>

        <LandingFooter inverted />
      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(howToSchema) }}
      />
    </div>
  );
}
