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
  title: "About — the layer the platforms structurally can't build",
  description:
    "Platforms build delegates. They won't build the layer that holds delegates accountable. The structural argument for the cumulative workspace and the judgment seat — and what we believe.",
  path: "/about",
  keywords: [
    "about yarnnn",
    "accountable ai",
    "ai judgment seat",
    "cumulative ai workspace",
    "model-agnostic ai",
    "owned ai context",
  ],
});

const BELIEFS = [
  {
    title: "Work should be cumulative, not episodic",
    body: "Fix something once and everything after inherits it. Your accumulated workspace is the asset; the agents are the labor; what they produce is the dividend. Everywhere else, work resets.",
    sub: "Day 1 the asset exists. Day 90 it's irreplaceable — not from lock-in, from accumulation.",
  },
  {
    title: "Operating system, not application",
    body: "A kernel runs the operation; programs run in userspace; the workspace is yours. Chat is the interface — the product is what runs underneath and keeps running while you're away.",
    sub: "You don't operate yarnnn. You supervise it.",
  },
  {
    title: "Judgment is separate from execution",
    body: "The agent that proposes an action shouldn't decide whether it's a good idea. Consequential actions pass through a Reviewer — a judgment seat you author the principles for — whose calls are reconciled against what actually happened.",
    sub: "The separation is architectural, not advisory. That's what makes more autonomy trustworthy, not reckless.",
  },
  {
    title: "Authored, not inferred",
    body: "Your context, your rules, your voice — written by you, versioned forever, never silently mutated. Every revision is attributed; nothing changes anonymously.",
    sub: "The stance, in three words: authored, not inferred.",
  },
  {
    title: "You supervise; the operation runs",
    body: "You set the delegation dial — manual, bounded, autonomous. The operation runs at the level of trust it has earned, and the trail shows you everything. You're the principal, not a safety mechanism.",
    sub: "From operator to supervisor. From building context to answering for outcomes.",
  },
  {
    title: "Receipts, not claims",
    body: "300+ recorded architecture decisions; attribution enforced at the write path; the calibration loop live in the alpha programs. We built it operator-first and run it on its own operations.",
    sub: "The architecture is the proof. The receipts culture is the identity.",
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
              We built the layer the
              <br />
              <span className="text-white/50">platforms structurally can&apos;t.</span>
            </h1>
            <div className="max-w-2xl space-y-6 text-white/50">
              <p>
                Every platform now sells you an AI delegate, and the delegates are genuinely good
                — scheduled runs, persistent memory, work done while you&apos;re away. But the same
                vendor that builds the delegate grades the delegate. Memory you can&apos;t read.
                Actions with no attributed trail. &ldquo;Improvement&rdquo; you take on faith.
              </p>
              <p>
                No platform will tell you whether its own agent&apos;s judgment is any good —
                structurally can&apos;t, for the same reason ratings agencies aren&apos;t run by the
                banks they rate. A platform judging its own model&apos;s agents has a self-audit
                problem. A neutral, model-agnostic seat does not.
              </p>
              <p>
                And underneath, all of them make work episodic. Every artifact is generated fresh;
                nothing you correct today makes tomorrow&apos;s output better. The two gaps are the
                same gap: nothing is owned, so nothing compounds and nothing is accountable.
              </p>
              <p className="text-white font-medium">
                yarnnn is the workspace where work is cumulative and a neutral judgment seat
                answers for what ships. We built it operator-first, run it on its own operations,
                and record every architectural decision in the open.
              </p>
            </div>
          </section>

          {/* What we believe — current canon */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
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
            </div>
          </section>

          {/* What yarnnn is not */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">What yarnnn is not</h2>
              <p className="text-white/50 mb-12 max-w-xl">
                We&apos;re focused. These are things we intentionally chose not to be.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {([
                  {
                    title: "Not a chat session that resets",
                    desc: "Sessions help in the moment and reset when you close the tab. Here the work is cumulative — your context is an owned, attributed asset, and corrections carry forward to every future cycle.",
                  },
                  {
                    title: "Not a platform agent that grades its own homework",
                    desc: "The vendor that builds the delegate can't credibly judge it. The seat here is neutral and model-agnostic — its calls are reconciled against what actually happened, and you can read the trail.",
                  },
                  {
                    title: "Not a memory wiki with no operation",
                    desc: "Memory remembers; it doesn't decide and doesn't answer for outcomes. Context with no action loop is a wiki. Here the substrate is wired to an operation with a judgment seat.",
                  },
                  {
                    title: "Not a safety filter bolted onto a model",
                    desc: "An approval button isn't judgment. The seat is a calibrated record of whether the calls were right — with a governance boundary the agent can't cross on its own.",
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
            </div>
          </section>

          {/* Who it's for — bounded-operation psychographic */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">Who yarnnn is for</h2>
              <p className="text-white/50 mb-12 max-w-xl">
                Someone with something that&apos;s theirs to run, that they can&apos;t be
                continuously present for, and who refuses to let it reset — the operator of a
                bounded operation.
              </p>

              <div className="flex flex-wrap gap-3 mb-12">
                {["a newsletter", "a portfolio", "a shop", "a pipeline", "a book of business"].map(
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
                    title: "A repeating consequential decision",
                    desc: "Work with a real call to make on cadence — what to ship, what to list, what to enter — where being right matters and the trail should prove whether you were.",
                  },
                  {
                    title: "A track record you're not learning from",
                    desc: "You have a history of decisions and outcomes that, right now, teaches you nothing. The seat reconciles it into a calibration trail and every future call starts from a higher floor.",
                  },
                  {
                    title: "Anyone moving from prompting to supervising",
                    desc: "If you'd rather author the rules once and answer for what ships than re-prompt the same work every week — and you want the operation to get better at your specific work over time.",
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
            </div>
          </section>

          {/* CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                The work you run shouldn&apos;t reset.
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Start free on the workspace. Author your context, watch the first artifact
                compound, and move the dial as trust accrues.
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
                  See how it compounds
                </Link>
              </div>
            </div>
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
