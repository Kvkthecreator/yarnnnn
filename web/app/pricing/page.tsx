import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { SpotlightCard } from "@/components/landing/SpotlightCard";
import { ScrollReveal } from "@/components/landing/ScrollReveal";
import { Check, Wallet, ShieldCheck } from "lucide-react";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";
import { CTA } from "@/lib/cta";

export const metadata = getMarketingMetadata({
  title: "Pricing — a free workspace, a plan with included usage, a budget you cap",
  description:
    "The workspace and your memory are free forever. Pick a plan for the work your operation runs — each includes a monthly usage allowance. Top up any time for extra headroom, and cap monthly spend with a budget you set. See every action; never a surprise bill.",
  path: "/pricing",
  keywords: ["yarnnn pricing", "ai subscription plans", "usage-based ai pricing", "ai operation budget", "monthly ai spend cap", "transparent ai usage", "included usage plan"],
});

// ADR-396 (2026-07-01): Type-B subscription over the metered balance. The public
// face is a three-tier plan ladder (Free / Starter / Pro): each paid tier grants
// a monthly INCLUDED USAGE allowance; top-ups are the overage pool beneath it; a
// budget you set caps monthly spend (a ceiling, not a charge — the _budget.yaml
// dial survives ADR-396); zero balance is the hard floor. Transparency contract:
// we show you every ACTION your operation takes; the plan is the price.
// Launch-test numbers (Free / $19 / $49) — set to test in front of a first user,
// reversible against evidence (ADR-396 §7, relaxed).

const PLANS = [
  {
    name: "Free",
    price: "$0",
    cadence: "forever",
    blurb: "Your memory — files, notes, and context — kept with full history and reachable from every AI you use.",
    cta: "Start free",
    href: CTA.signup,
    featured: false,
    points: [
      "Workspace + memory, free forever",
      "$3 starting balance — feel the loop before you spend",
      "Reachable from any AI over MCP",
    ],
  },
  {
    name: "Starter",
    price: "$19",
    cadence: "/mo",
    blurb: "For a focused operation running through the week. Includes a monthly usage allowance for its work.",
    cta: "Go Starter",
    href: CTA.signup,
    featured: true,
    points: [
      "Everything in Free",
      "Monthly included usage for your operation",
      "30-day connector history",
      "Up to 3 connectors",
    ],
  },
  {
    name: "Pro",
    price: "$49",
    cadence: "/mo",
    blurb: "For high-cadence work or several operations at once. A larger allowance and a longer memory of the world.",
    cta: "Go Pro",
    href: CTA.signup,
    featured: false,
    points: [
      "Everything in Starter",
      "Larger monthly included usage",
      "90-day connector history",
      "Unlimited connectors",
    ],
  },
];

const HOW_IT_WORKS = [
  "Each plan includes a monthly usage allowance — the work your operation runs is drawn from it first.",
  "Need more in a heavy month? Top up any amount from $5. Top-ups never expire and sit beneath your allowance.",
  "Idle costs nothing. The workspace and every file are free — only a running operation draws usage.",
  "Hard stop at zero. If your allowance and balance run out, the operation pauses — nothing is lost. You resume by upgrading or topping up.",
];

export default function PricingPage() {
  const pricingSchema = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: BRAND.name,
    url: `${BRAND.url}/pricing`,
    applicationCategory: "BusinessApplication",
    offers: PLANS.map((p) => ({
      "@type": "Offer",
      name: p.name,
      description: p.blurb,
      price: p.price.replace("$", "") || "0",
      priceCurrency: "USD",
      url: `${BRAND.url}/pricing`,
    })),
  };

  return (
    <div className="relative min-h-screen flex flex-col bg-[#0f1419] text-white overflow-x-hidden">
      <GrainOverlay variant="dark" />
      <ShaderBackgroundDark />

      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted />

        <main className="flex-1 flex flex-col items-center px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto w-full">

            {/* Header */}
            <div className="text-center mb-16">
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-6 tracking-tight">
                Free to keep.<br />A plan for the work.
              </h1>
              <p className="text-white/50 text-lg max-w-2xl mx-auto">
                The workspace and your memory are free forever. Pick a plan for the
                operation that runs on them — each includes a monthly usage
                allowance. See every action it takes; never a surprise bill.
              </p>
            </div>

            {/* Plan ladder */}
            <ScrollReveal className="mb-8">
              <div className="grid gap-4 md:grid-cols-3">
                {PLANS.map((plan, i) => (
                  <SpotlightCard
                    key={plan.name}
                    variant="dark"
                    spotlightSize={500}
                    className={plan.featured ? "ring-1 ring-emerald-400/30" : undefined}
                  >
                    <div className="p-6 flex flex-col h-full">
                      {plan.featured && (
                        <span className="self-start mb-3 text-[10px] font-mono uppercase tracking-wider text-emerald-400">
                          Most popular
                        </span>
                      )}
                      <h2 className="text-xl font-medium mb-1">{plan.name}</h2>
                      <div className="flex items-baseline gap-1 mb-3">
                        <span className="text-3xl font-medium">{plan.price}</span>
                        <span className="text-white/40 text-sm">{plan.cadence}</span>
                      </div>
                      <p className="text-white/50 text-sm leading-relaxed mb-5">{plan.blurb}</p>
                      <ul className="space-y-2.5 mb-6 flex-1">
                        {plan.points.map((pt) => (
                          <li key={pt} className="flex items-start gap-2.5 text-sm text-white/70 leading-relaxed">
                            <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                            <span>{pt}</span>
                          </li>
                        ))}
                      </ul>
                      <Link
                        href={plan.href}
                        className={`block text-center px-6 py-3 font-medium rounded-full transition-colors ${
                          plan.featured || i === 0
                            ? "bg-white text-black hover:bg-white/90"
                            : "border border-white/20 text-white hover:bg-white/10"
                        }`}
                      >
                        {plan.cta}
                      </Link>
                    </div>
                  </SpotlightCard>
                ))}
              </div>
            </ScrollReveal>

            <p className="text-center text-white/40 text-sm mb-16">
              No card to start. The $3 balance is enough to feel the loop before you spend a cent.
            </p>

            {/* How usage works */}
            <ScrollReveal className="max-w-3xl mx-auto mb-8" delay={80}>
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-8">
                  <div className="text-[10px] font-mono uppercase tracking-wider text-white/40 mb-3">
                    How usage works
                  </div>
                  <div className="flex items-baseline gap-2 mb-5">
                    <h2 className="text-2xl font-medium">Included, then top up</h2>
                    <span className="text-white/40 text-sm">— never a surprise</span>
                  </div>
                  <ul className="space-y-4">
                    {HOW_IT_WORKS.map((p) => (
                      <li key={p} className="flex items-start gap-3 text-sm text-white/70 leading-relaxed">
                        <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span>{p}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </SpotlightCard>
            </ScrollReveal>

            {/* Two guardrails explainer — the budget vs the floor (survives ADR-396) */}
            <ScrollReveal className="max-w-3xl mx-auto mb-16">
              <div className="text-center mb-6">
                <h3 className="text-xl font-medium mb-2">Two guardrails, so spend is never a surprise</h3>
                <p className="text-white/45 text-sm max-w-xl mx-auto">
                  One ceiling you plan, one floor that never lets anything break.
                </p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <SpotlightCard variant="dark" spotlightSize={500}>
                  <div className="p-6">
                    <div className="flex items-center gap-2 mb-2">
                      <Wallet className="w-4 h-4 text-emerald-400" />
                      <h4 className="text-base font-medium">Your ceiling — the budget</h4>
                    </div>
                    <p className="text-white/50 text-sm leading-relaxed">
                      The planned maximum. The agent paces its own work to stay under the monthly
                      amount you set, so an active operation costs what you decided it could — and
                      no more. Raise or lower it whenever. It&apos;s a cap you set, not a charge.
                    </p>
                  </div>
                </SpotlightCard>
                <SpotlightCard variant="dark" spotlightSize={500}>
                  <div className="p-6">
                    <div className="flex items-center gap-2 mb-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                      <h4 className="text-base font-medium">The floor — zero balance</h4>
                    </div>
                    <p className="text-white/50 text-sm leading-relaxed">
                      The absolute stop. If your allowance and balance ever reach zero the operation
                      simply pauses — nothing is lost, no overage, no surprise. You resume by
                      upgrading or topping up.
                    </p>
                  </div>
                </SpotlightCard>
              </div>
            </ScrollReveal>

            {/* Three honest paragraphs */}
            <ScrollReveal className="max-w-3xl mx-auto mb-16 grid gap-6">
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6">
                  <h3 className="text-lg font-medium mb-3">What&apos;s an operation?</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    An operation is the optional assistant (in beta) running on your workspace. It
                    draws on your plan&apos;s included usage while it&apos;s working, capped by the
                    budget you set. Your memory, files, and access from any AI are always free.
                  </p>
                </div>
              </SpotlightCard>
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6">
                  <h3 className="text-lg font-medium mb-3">What&apos;s &ldquo;usage&rdquo;?</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Usage is the model work your operation runs — a judgment call, a piece of
                    research, a draft. Your plan includes a monthly amount of it; you see every
                    action on your Usage screen. Only what actually ran counts.
                  </p>
                </div>
              </SpotlightCard>
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6">
                  <h3 className="text-lg font-medium mb-3">Why a plan instead of pure pay-as-you-go?</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    A plan makes spend predictable — a known monthly amount, an allowance included,
                    and a budget you cap it at. Heavier months you top up; idle months you don&apos;t.
                    You get the predictability of a fixed plan without paying per opaque token.
                  </p>
                </div>
              </SpotlightCard>
            </ScrollReveal>

            {/* Mini-FAQ */}
            <ScrollReveal className="max-w-3xl mx-auto mb-16">
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6 space-y-4 text-white/50 text-sm leading-relaxed">
                  <p>
                    <strong className="text-white/70">Do I need a paid plan?</strong> No. The
                    workspace and your memory are free forever. A plan is for running an operation
                    on them — it includes the monthly usage that work needs.
                  </p>
                  <p>
                    <strong className="text-white/70">Starting balance.</strong> Every workspace
                    begins with a $3 usage credit — enough to author your context and watch the
                    correction loop firsthand before you spend anything.
                  </p>
                  <p>
                    <strong className="text-white/70">If you hit your budget,</strong> the operation
                    eases off its scheduled work for the rest of the window so it stays under your
                    ceiling. Raise the budget anytime to let it keep going.
                  </p>
                  <p>
                    <strong className="text-white/70">If your allowance runs out,</strong> top up any
                    amount — it never expires — or upgrade your plan. The operation resumes at once.
                  </p>
                  <p>
                    <strong className="text-white/70">If you stop running an operation,</strong> it
                    simply stops drawing usage. The workspace and every file remain yours, free.
                  </p>
                </div>
              </SpotlightCard>
            </ScrollReveal>

            <div className="text-center mt-4 mb-8">
              <p className="text-white/40 text-sm mb-4">Questions about pricing?</p>
              <a
                href="mailto:admin@yarnnn.com"
                className="text-white hover:text-white/80 underline underline-offset-4 text-sm"
              >
                Contact us
              </a>
            </div>
          </div>
        </main>

        <LandingFooter inverted />
      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(pricingSchema) }}
      />
    </div>
  );
}
