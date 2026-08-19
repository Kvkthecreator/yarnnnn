import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { SpotlightCard } from "@/components/landing/SpotlightCard";
// ADR-445 §6 — prices live in ONE place (billing_tiers.py::TIER_CONFIG, mirrored
// by lib/subscription/usage.ts). This page interpolates; it never re-types a number.
import { PRICE_COPY } from "@/lib/subscription/usage";
import { ScrollReveal } from "@/components/landing/ScrollReveal";
import { Check, Wallet, ShieldCheck } from "lucide-react";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";
import { CTA } from "@/lib/cta";

export const metadata = getMarketingMetadata({
  title: "Pricing — free for two people, a paid seat for every extra teammate",
  description:
    "Your workspace and memory are free for you and a teammate. From the 3rd person, each extra seat is paid; usage is pay-as-you-go from one shared balance the owner funds. AI connections are always free. See every action; never a surprise bill.",
  path: "/pricing",
  keywords: ["yarnnn pricing", "ai workspace pricing", "shared ai workspace", "per seat ai pricing", "team ai plan", "usage-based ai pricing", "transparent ai usage"],
});

// ADR-490 (2026-07-28): two free seats + pay-as-you-go usage. There is NO base
// fee and NO included allowance — the paid subscription IS the per-seat price.
//   ① SEATS — the first TWO humans (you + one teammate) are free; each additional
//      human is a priced seat ($20/seat/mo). Unlimited workspaces; the free→paid
//      boundary is the 3rd human. AI connections are never seats, never charged.
//   ② USAGE — pure pay-as-you-go from one shared balance (signup grant + top-ups,
//      owner-funded); hard-stop at zero; top-ups never expire.
// The tier ladder is Free + one paid plan (`pro` dormant, returns with the capture
// lane). Numbers ($0 / $20 seat) are launch-test values, reversible against
// first-customer evidence (ADR-396 §7 standing discipline).

const PLANS = [
  {
    name: "Free",
    price: "$0",
    cadence: "for two people",
    blurb: "Your memory — files, notes, and context — kept with full history and reachable from every AI you use. Free for you and a teammate, no card.",
    cta: "Start free",
    href: CTA.signup,
    featured: false,
    points: [
      "Workspace + memory, free for two people",
      `${PRICE_COPY.signupGrant} starting balance — feel the loop before you spend`,
      "Usage pay-as-you-go — top up only for what runs",
      "Reachable from any AI over MCP — always free",
    ],
  },
  {
    name: "Team",
    price: PRICE_COPY.seat,
    cadence: "/extra seat/mo",
    blurb: "For a real team working out of one shared workspace. Two of you stay free; from the 3rd person each seat is paid, and usage stays one shared pay-as-you-go balance.",
    cta: "Bring the team",
    href: CTA.signup,
    featured: true,
    points: [
      "Everything in Free — your first two seats stay free",
      `${PRICE_COPY.seat}/mo per seat from the 3rd person`,
      "One shared usage balance the whole workspace draws",
      "Connect any AI over MCP — always free, never a seat",
    ],
  },
];

const HOW_IT_WORKS = [
  "Free for two people. Your workspace, your memory, and your first teammate are free — you only pay a seat from the 3rd person.",
  "A seat per extra teammate. Each person beyond the first two is a paid seat; AI connections you plug in over MCP are always free and never a seat.",
  "Usage is pay-as-you-go. Every judgment call draws one shared balance the owner funds — you, your teammates, and any AI all draw the same pool. Only what actually ran counts.",
  `Top up any amount from ${PRICE_COPY.topUpMin}. Top-ups never expire. Hard stop at zero — nothing is lost, you resume by topping up.`,
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
                Free for two.<br />A seat for the rest.
              </h1>
              <p className="text-white/50 text-lg max-w-2xl mx-auto">
                Your workspace and your memory are free for you and a teammate. From
                the 3rd person, each extra seat is paid; usage is pay-as-you-go from
                one shared balance the owner funds. AI connections are always free —
                never a seat. See every action; never a surprise bill.
              </p>
            </div>

            {/* Plan ladder — Free + one paid plan (ADR-490); two cards, centered */}
            <ScrollReveal className="mb-8">
              <div className="grid gap-4 sm:grid-cols-2 max-w-2xl mx-auto">
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
              No card to start. The {PRICE_COPY.signupGrant} balance is enough to feel the loop before you spend a cent.
            </p>

            {/* How usage works */}
            <ScrollReveal className="max-w-3xl mx-auto mb-8" delay={80}>
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-8">
                  <div className="text-[10px] font-mono uppercase tracking-wider text-white/40 mb-3">
                    How usage works
                  </div>
                  <div className="flex items-baseline gap-2 mb-5">
                    <h2 className="text-2xl font-medium">One shared pool, then top up</h2>
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

            {/* Two guardrails explainer — visibility + the floor (ADR-490) */}
            <ScrollReveal className="max-w-3xl mx-auto mb-16">
              <div className="text-center mb-6">
                <h3 className="text-xl font-medium mb-2">Two guardrails, so spend is never a surprise</h3>
                <p className="text-white/45 text-sm max-w-xl mx-auto">
                  You see everything, and nothing can overrun.
                </p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <SpotlightCard variant="dark" spotlightSize={500}>
                  <div className="p-6">
                    <div className="flex items-center gap-2 mb-2">
                      <Wallet className="w-4 h-4 text-emerald-400" />
                      <h4 className="text-base font-medium">You only pay for what ran</h4>
                    </div>
                    <p className="text-white/50 text-sm leading-relaxed">
                      Usage is pay-as-you-go: each judgment call draws the shared balance, and the
                      Usage screen shows every action — what ran, and who ran it. Idle costs
                      nothing; there is no subscription for usage, no monthly commitment.
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
                      The absolute stop. If the balance ever reaches zero the work simply pauses —
                      nothing is lost, no overage, no surprise. You resume by topping up.
                    </p>
                  </div>
                </SpotlightCard>
              </div>
            </ScrollReveal>

            {/* Three honest paragraphs */}
            <ScrollReveal className="max-w-3xl mx-auto mb-16 grid gap-6">
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6">
                  <h3 className="text-lg font-medium mb-3">What does a seat cost?</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    A seat is a human on your workspace. The first two — you and a teammate — are
                    free. Each person from the 3rd onward is {PRICE_COPY.seat}/mo. Every human draws the same
                    shared balance the owner funds — and any AI you connect over MCP is always
                    free, never a seat and never a charge.
                  </p>
                </div>
              </SpotlightCard>
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6">
                  <h3 className="text-lg font-medium mb-3">What&apos;s &ldquo;usage&rdquo;?</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Usage is the model work your workspace runs — a judgment call, a piece of
                    research, a draft. It draws your balance as it happens, and you see every
                    action on your Usage screen. Only what actually ran counts. The engine you
                    pick is the biggest lever on what it costs —{" "}
                    <Link
                      href="/engines"
                      className="text-white/70 underline underline-offset-4 decoration-white/30 hover:decoration-white/70"
                    >
                      how to choose one
                    </Link>
                    .
                  </p>
                </div>
              </SpotlightCard>
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6">
                  <h3 className="text-lg font-medium mb-3">Why pay-as-you-go instead of a usage plan?</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Because work is uneven. Heavy months you top up; idle months you pay nothing —
                    there is no monthly usage fee to outgrow or waste. The seat price is the only
                    subscription, and it buys something that doesn&apos;t fluctuate: your team&apos;s access.
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
                    workspace and your memory are free for two people. The paid plan is for a
                    bigger team — from the 3rd person, each extra seat is {PRICE_COPY.seat}/mo. Usage stays
                    pay-as-you-go either way.
                  </p>
                  <p>
                    <strong className="text-white/70">Starting balance.</strong> Every workspace
                    begins with a {PRICE_COPY.signupGrant} usage credit — enough to author your context and watch the
                    correction loop firsthand before you spend anything.
                  </p>
                  <p>
                    <strong className="text-white/70">If your balance runs out,</strong> the work
                    simply pauses. Top up any amount — it never expires — and everything resumes at
                    once. Nothing is lost while paused.
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
