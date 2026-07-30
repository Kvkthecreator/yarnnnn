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

export const metadata: Metadata = getMarketingMetadata({
  title: "How yarnnn works — your true AI-first workspace",
  description:
    "Connect the AI you already use, co-work on shared files and documents, share with a link — and every change signed by whoever made it, human or not. Here's the loop.",
  path: "/how-it-works",
  keywords: [
    "how yarnnn works",
    "ai workspace",
    "co-work with ai",
    "shared workspace for ai and humans",
    "work with chatgpt and claude together",
    "ai memory you own",
    "cross-llm workspace",
  ],
});

const STEPS = [
  {
    number: "01",
    title: "Connect the AI you already use",
    body: "Attach yarnnn to ChatGPT, Claude, or Gemini — nothing to set up beyond that. The first thing you'll see is a write you didn't make, signed by something that isn't you: your AI, working in your workspace.",
  },
  {
    number: "02",
    title: "Co-work in the built-in apps",
    body: "Think in Chat, over your own files. Make documents, decks and pages in Studio. Everything you and your AIs produce lands in one shared file system — no more ferrying work out of a chat window by hand.",
  },
  {
    number: "03",
    title: "Every change is signed — human or not",
    body: "You, your teammates, your agents, and every connected AI write into the same place, and every change carries a name. You can walk any file back to who decided what, when, and why.",
  },
  {
    number: "04",
    title: "Share with a link",
    body: "Send one link and a teammate lands inside the workspace, on the real thing — no export, no paste. Two people work free; the record of who did what comes with it.",
  },
  {
    number: "05",
    title: "Fix it once; it stays fixed",
    body: "Correct a detail and everything made after it inherits the fix. The workspace gets sharper the longer you work in it — and it never resets.",
  },
];

const MECHANISM_TRIO = [
  {
    tag: "Every AI",
    title: "Works with all of them",
    desc: "One workspace, reachable from every AI you use. Neutral on purpose — it's not tied to any one of them.",
  },
  {
    tag: "Every change",
    title: "Nothing changes in the dark",
    desc: "Every edit is signed and dated — human or not. You can always see what changed and who changed it.",
  },
  {
    tag: "Every time",
    title: "It keeps getting better",
    desc: "Fix something once and it stays fixed. Everywhere else, you start over.",
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
              Connect once.
              <br />
              <span className="text-white/50">Co-work everywhere after.</span>
            </h1>
            <p className="max-w-2xl text-white/50 text-lg">
              yarnnn is one shared workspace for you, your people, and the AI you already
              use — shared files, documents you build with AI, and every change signed by
              whoever made it, human or not. Here&apos;s how it goes, from an empty
              workspace to your first co-work moment.
            </p>
          </section>

          {/* The five-step loop — a connected vertical flow (StepFlow). Step 05 carries
              the verdict trio inline via the `extra` slot. */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <StepFlow steps={STEPS} />
          </section>

          {/* Mechanism trio + CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-5xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-12 text-center">
                Why it&apos;s different.
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
                {MECHANISM_TRIO.map((m) => (
                  <SpotlightCard key={m.tag} variant="dark" spotlightSize={300}>
                    <div className="p-6 h-full">
                      <div className="text-xs font-mono text-white/30 uppercase tracking-wider mb-4">
                        {m.tag}
                      </div>
                      <h3 className="text-base font-medium mb-3">{m.title}</h3>
                      <p className="text-white/40 text-sm leading-relaxed">{m.desc}</p>
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
