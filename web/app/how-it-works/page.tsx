import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { SpotlightCard } from "@/components/landing/SpotlightCard";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";
import { CTA, PRIMARY_CTA_LABEL } from "@/lib/cta";

export const metadata: Metadata = getMarketingMetadata({
  title: "How yarnnn works — the workspace where work compounds",
  description:
    "Pick your operation. Write the constitution. Bring in your reality. It produces; you correct; corrections stay. The seat answers for what ships.",
  path: "/how-it-works",
  keywords: [
    "how yarnnn works",
    "accountable ai workflow",
    "cumulative ai workspace",
    "ai judgment seat",
    "ai delegation dial",
    "owned ai context",
    "solopreneur ai",
  ],
});

const STEPS = [
  {
    number: "01",
    title: "Pick your operation",
    body: "Choose a program — trading, authoring; more coming — or start with a bare workspace. The program declares what the operation is: what it watches, what it produces, what counts as ground truth.",
  },
  {
    number: "02",
    title: "Write the constitution",
    body: "What it's for, the rules it judges by, how much it may do alone. Authored by you, amendable by you, versioned forever. This is the standing intent every agent reasons against and the seat enforces.",
  },
  {
    number: "03",
    title: "Connect and bring in your reality",
    body: "Link your platforms; import your files and history. Your context becomes owned, attributed substrate — not a context window that empties when you close the tab.",
    stageB:
      "Bring your track record — the seat reconciles your past decisions into a calibration trail on day one.",
  },
  {
    number: "04",
    title: "It produces; you correct; corrections stay",
    body: "Artifacts trace to the sources they were composed from. Fix one source file and every future artifact inherits the fix. Nothing you correct is lost; every cycle starts from a higher floor.",
  },
  {
    number: "05",
    title: "The seat answers for what ships",
    body: "Proposals, verdicts, reconciled outcomes — a trail you can audit. A judgment seat you author the principles for evaluates consequential actions against your declared intent, then approves, queues for your review, or defers pending more information. Move the dial as trust accrues.",
  },
];

const VERDICTS = [
  {
    label: "Approve",
    desc: "If the action aligns with your declared intent and falls within your delegated ceiling, it executes. No manual approval needed.",
  },
  {
    label: "Queue",
    desc: "If the action exceeds your ceiling or the seat isn't confident, it surfaces in your review queue. You decide.",
  },
  {
    label: "Defer",
    desc: "If the proposal has an evidence gap, the seat commissions the missing research before deciding. It doesn't guess.",
  },
];

const MECHANISM_TRIO = [
  {
    tag: "Traceable",
    title: "Everything has an author",
    desc: "Every file, every change, every artifact traces to its sources. Nothing mutates anonymously.",
  },
  {
    tag: "Compounds",
    title: "Corrections carry forward",
    desc: "Fix one source and the future inherits it. The work is monotonically improving; everywhere else resets.",
  },
  {
    tag: "Judged",
    title: "Reconciled against reality",
    desc: "The seat's calls are checked against what actually happened — a track record, not a safety filter.",
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
              You set it up once.
              <br />
              <span className="text-white/50">It compounds from there.</span>
            </h1>
            <p className="max-w-2xl text-white/50 text-lg">
              YARNNN is the workspace where the work you run is cumulative. You author the
              operation and its rules; agents you own produce from them; and a judgment seat
              answers for what ships. Here&apos;s the five-step walk from a bare workspace to a
              running operation.
            </p>
          </section>

          {/* The five-step setup walk */}
          {STEPS.map((step) => (
            <section
              key={step.number}
              className="border-t border-white/10 px-6 py-24 md:py-32"
            >
              <div className="max-w-4xl mx-auto">
                <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6">
                  <div className="text-4xl font-light text-white/20">{step.number}</div>
                  <div>
                    <h2 className="text-2xl md:text-3xl font-medium mb-4">{step.title}</h2>
                    <p className="text-white/55 leading-relaxed max-w-2xl text-lg font-light">
                      {step.body}
                    </p>
                    {step.stageB && (
                      <p className="mt-4 text-white/35 text-sm italic max-w-2xl">
                        {step.stageB}
                      </p>
                    )}

                    {/* Step 05 carries the verdict trio inline */}
                    {step.number === "05" && (
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-10">
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
                    )}
                  </div>
                </div>
              </div>
            </section>
          ))}

          {/* Mechanism trio + CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-12 text-center">
                What makes it categorically different.
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
            </div>
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
