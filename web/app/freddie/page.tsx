import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackground } from "@/components/landing/ShaderBackground";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { ScrollReveal } from "@/components/landing/ScrollReveal";
import { TraceCard } from "@/components/landing/TraceCard";
import { FreddieAvatar } from "@/components/freddie/FreddieAvatar";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";
import { CTA, PRIMARY_CTA_LABEL } from "@/lib/cta";

export const metadata: Metadata = getMarketingMetadata({
  title: "Meet Freddie — the agent that tends your memory | yarnnn",
  description:
    "Freddie reads what you connect, keeps your memory in order, and records every change so you can trace it. He works within limits you set, and only ever does as much as you allow. In beta.",
  path: "/freddie",
  keywords: [
    "ai memory agent",
    "ai assistant that remembers",
    "attributed ai memory",
    "ai agent you control",
    "ai memory steward",
    "traceable ai agent",
    "slack notion ai agent",
    "supervised ai assistant",
  ],
});

// Freddie's real, live capabilities — each maps to a shipped primitive an
// operator can verify in-app today (FREDDIE_PRIMITIVES, api/services/
// primitives/registry.py). No promises here: reads = capture + QueryKnowledge
// + SearchFiles; organizes = WriteFile/EditFile/MoveFile/DeleteFile; checks =
// ProposeAction through the ADR-307 gate; records = ListRevisions/DiffRevisions.
const CAPABILITIES = [
  {
    tag: "Reads",
    title: "He sees what you connect.",
    body:
      "Connect Slack, Notion, your files and notes, and Freddie reads them the way you would — pulling up the last message in a channel, finding the doc you half-remember. Ask him and he looks it up.",
  },
  {
    tag: "Organizes",
    title: "He keeps your memory in order.",
    body:
      "Freddie files new things where they belong, tidies what's messy, and edits a detail when you ask. Your memory stays legible instead of piling up — and nothing he touches is ever silently lost.",
  },
  {
    tag: "Checks",
    title: "He weighs work against your rules.",
    body:
      "Write down how you want things done, and Freddie holds work to it — flagging what doesn't fit before it goes anywhere. He proposes; the important calls come to you.",
  },
  {
    tag: "Records",
    title: "He signs and dates every change.",
    body:
      "Everything Freddie does lands with his name on it and a timestamp — nothing happens in the dark.",
  },
];

// The autonomy dial — the SAME three-tile pattern as landing §4 (AUTONOMY
// substrate, not ADR-334 seat entitlements).
const DIAL = [
  {
    label: "Goes ahead",
    body:
      "If it fits your rules and stays within what you've allowed, Freddie just does it — no need to ask.",
  },
  {
    label: "Asks you first",
    body:
      "If it's bigger than that, or he's unsure, he brings it to you. You make the call.",
  },
  {
    label: "Waits for more",
    body:
      "If something's missing, he gathers what he needs before deciding. He doesn't guess.",
  },
];

export default function FreddiePage() {
  return (
    <main className="relative min-h-screen w-full overflow-x-hidden bg-[#faf8f5] text-[#1a1a1a]">
      <GrainOverlay />
      <ShaderBackground />

      <div className="relative z-10">
        <LandingHeader />

        {/* ─── Hero ─────────────────────────────────────────────────────── */}
        <section className="flex flex-col items-center justify-center px-6 py-28 md:py-36 min-h-[70vh]">
          <div className="max-w-4xl mx-auto w-full text-center">
            <div className="flex justify-center mb-8">
              <FreddieAvatar animate className="w-20 h-20 md:w-24 md:h-24" title="Freddie" />
            </div>

            <h1 className="text-3xl sm:text-4xl md:text-5xl font-medium tracking-wide mb-6">
              <span className="text-[#de5a2b]">Meet Freddie.</span>
              <br />
              <span className="text-[#1a1a1a]/90">The agent that tends your memory.</span>
            </h1>

            <p className="text-lg md:text-xl text-[#1a1a1a]/50 mb-10 max-w-2xl mx-auto font-light">
              Your memory is yours. Freddie is who keeps it working — and he only ever
              does as much as you allow.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
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
        </section>

        {/* ─── What Freddie does today (verifiable capabilities) ────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <ScrollReveal className="max-w-5xl mx-auto">
            <div className="text-center mb-16">
              <div className="text-xs font-mono text-[#1a1a1a]/30 uppercase tracking-wider mb-4">
                What he does today
              </div>
              <h2 className="text-2xl md:text-3xl font-medium text-[#1a1a1a]">
                Not a demo. Things Freddie does right now.
              </h2>
              <p className="text-[#1a1a1a]/50 mt-4 max-w-2xl mx-auto leading-relaxed">
                Everything below is live — you can watch him do it the day you sign up.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {CAPABILITIES.map((cap) => (
                <div
                  key={cap.tag}
                  className="p-8 rounded-2xl border border-[#1a1a1a]/[0.06] bg-[#1a1a1a]/[0.02]"
                >
                  <div className="text-xs font-mono text-[#1a1a1a]/30 uppercase tracking-wider mb-4">
                    {cap.tag}
                  </div>
                  <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">{cap.title}</h3>
                  <p className="text-sm text-[#1a1a1a]/50 leading-relaxed">{cap.body}</p>
                </div>
              ))}
            </div>
          </ScrollReveal>
        </section>

        {/* ─── The trace demo (the uncopyable property) ─────────────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <ScrollReveal className="max-w-5xl mx-auto">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
              <div>
                <div className="text-xs font-mono text-[#1a1a1a]/30 uppercase tracking-wider mb-4">
                  Every change, on the record
                </div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a] leading-tight">
                  You can always see what Freddie did.
                </h2>
                <p className="text-[#1a1a1a]/60 leading-relaxed text-lg font-light">
                  Every version of every fact carries an author and a date — you, an AI, or
                  Freddie himself. Nothing gets quietly overwritten: trace exactly how anything
                  got there, and roll it back if you disagree. It&apos;s why handing work to
                  Freddie stays safe.
                </p>
              </div>
              <div>
                <TraceCard />
              </div>
            </div>
          </ScrollReveal>
        </section>

        {/* ─── The autonomy dial (AUTONOMY substrate, not seat tier) ────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <ScrollReveal className="max-w-4xl mx-auto">
            <div className="text-xs font-mono text-[#1a1a1a]/30 uppercase tracking-wider mb-4">
              You&apos;re always in charge
            </div>
            <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
              You set the line. Freddie stays on your side of it.
            </h2>
            <p className="text-[#1a1a1a]/50 leading-relaxed max-w-2xl mb-10">
              How far Freddie goes on his own is a dial you turn:
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {DIAL.map((d) => (
                <div
                  key={d.label}
                  className="p-6 rounded-2xl bg-[#1a1a1a]/[0.02] border border-[#1a1a1a]/[0.06]"
                >
                  <div className="text-sm font-medium text-[#1a1a1a] mb-2">{d.label}</div>
                  <p className="text-sm text-[#1a1a1a]/50 leading-relaxed">{d.body}</p>
                </div>
              ))}
            </div>
          </ScrollReveal>
        </section>

        {/* ─── The honesty band (Rung-1 boundary, said plainly) ─────────── */}
        {/* ADR-380/381: Freddie is the Rung-1 substrate steward — reversible
            memory work is real TODAY; taking consequential action out in the
            world is the Rung-2 horizon, earned on the record, not switched on.
            Stated as confidence (everything above is verifiable), not a hedge. */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <ScrollReveal className="max-w-3xl mx-auto">
            <div className="text-xs font-mono text-[#1a1a1a]/30 uppercase tracking-wider mb-4">
              Where the line is
            </div>
            <h2 className="text-2xl md:text-3xl font-medium mb-8 text-[#1a1a1a] leading-tight">
              What&apos;s real today, and what&apos;s next.
            </h2>
            <div className="space-y-6 text-[#1a1a1a]/60 leading-relaxed text-lg font-light">
              <p>
                <span className="text-[#1a1a1a]/90 font-normal">Today,</span> everything above is
                live — reversible, attributed, yours to verify the day you sign up. Tending your
                memory is real work, and it&apos;s the work Freddie does now.
              </p>
              <p>
                <span className="text-[#1a1a1a]/90 font-normal">Next,</span> Freddie takes action
                out in the world on your behalf — within limits you set. That&apos;s the horizon,
                and it&apos;s earned on the record, not flipped on by a switch. We&apos;d rather
                under-promise what an agent can do with your trust than overstate it.
              </p>
            </div>
          </ScrollReveal>
        </section>

        {/* ─── CTA ──────────────────────────────────────────────────────── */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <ScrollReveal className="max-w-3xl mx-auto text-center">
            <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
              Start with your memory. Meet Freddie inside.
            </h2>
            <p className="text-[#1a1a1a]/50 mb-10 max-w-xl mx-auto leading-relaxed">
              The workspace and your memory are free forever. Freddie&apos;s there from the start —
              turn him up when you&apos;re ready.
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
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "WebPage",
            name: "Meet Freddie — the agent that tends your memory",
            url: `${BRAND.url}/freddie`,
            description: metadata.description ?? undefined,
            isPartOf: {
              "@type": "WebSite",
              name: BRAND.name,
              url: BRAND.url,
            },
          }),
        }}
      />
    </main>
  );
}
