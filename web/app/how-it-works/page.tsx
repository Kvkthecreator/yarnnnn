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
  title: "How yarnnn works — shared memory for AI + human work",
  description:
    "Connect your tools, and everything your AI knows lands in one place you own — reachable from every app, with a full history of every change. Here's the loop.",
  path: "/how-it-works",
  keywords: [
    "how yarnnn works",
    "ai memory across apps",
    "shared ai memory",
    "chatgpt and claude memory",
    "portable ai memory",
    "ai memory you own",
    "cross-llm memory",
  ],
});

const STEPS = [
  {
    number: "01",
    title: "Connect your tools",
    body: "Link Slack, Notion, your files and notes. Whatever they know flows into one place — and it doesn't disappear when you close the tab.",
  },
  {
    number: "02",
    title: "It becomes one memory you own",
    body: "Everything lands with your name on it and a date attached. Nothing is anonymous, and nothing gets quietly overwritten — you can always see how it got there.",
  },
  {
    number: "03",
    title: "Reach it from any AI",
    body: "The same memory is available to ChatGPT, Claude, and your other tools. Write it in one, pick up in the next — no copy-paste, no starting over.",
  },
  {
    number: "04",
    title: "Fix it once; it stays fixed",
    body: "Correct a detail and every future answer uses the fix. Nothing you correct is lost, and each time is a little better than the last.",
  },
  {
    number: "05",
    title: "Beta: add a second set of eyes",
    body: "When you're ready, turn on an assistant that reviews important work before it goes out — against rules you write — and records every call it makes. It does only as much as you allow.",
  },
];

const VERDICTS = [
  {
    label: "Goes ahead",
    desc: "If it fits the rules you set and stays within what you've allowed, it just does it — no need to ask.",
  },
  {
    label: "Asks you first",
    desc: "If it's bigger than what you've allowed, or it's not sure, it brings it to you. You make the call.",
  },
  {
    label: "Waits for more",
    desc: "If something's missing, it gathers what it needs before deciding. It doesn't guess.",
  },
];

const MECHANISM_TRIO = [
  {
    tag: "Every AI",
    title: "Works with all of them",
    desc: "One memory, available to every AI tool you use. Neutral on purpose — it's not tied to any one of them.",
  },
  {
    tag: "Every change",
    title: "Nothing changes in the dark",
    desc: "Every edit is signed and dated. You can always see what changed and who changed it.",
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
              Set it up once.
              <br />
              <span className="text-white/50">It&apos;s everywhere after.</span>
            </h1>
            <p className="max-w-2xl text-white/50 text-lg">
              yarnnn turns the scattered memory across your AI tools into one place you own — fed
              by your apps, reachable from every model. Here&apos;s how it goes, from an empty
              workspace to a memory that follows you everywhere.
            </p>
          </section>

          {/* The five-step loop — a connected vertical flow (StepFlow). Step 05 carries
              the verdict trio inline via the `extra` slot. */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <StepFlow
              steps={STEPS.map((step) => ({
                ...step,
                extra:
                  step.number === "05" ? (
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-8">
                      {VERDICTS.map((v) => (
                        <SpotlightCard key={v.label} variant="dark" spotlightSize={250}>
                          <div className="p-5">
                            <div className="text-xs text-white/30 uppercase tracking-wider mb-2">
                              {v.label}
                            </div>
                            <p className="text-white/60 text-sm leading-relaxed">{v.desc}</p>
                          </div>
                        </SpotlightCard>
                      ))}
                    </div>
                  ) : undefined,
              }))}
            />
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
