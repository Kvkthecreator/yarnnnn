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
  title: "Pricing — free for one person, a paid seat for every teammate",
  description:
    "Your workspace and memory are free forever for one person. Add a teammate and each extra person is a paid seat; usage is a shared pool the owner funds. AI connections are always free. See every action; never a surprise bill.",
  path: "/pricing",
  keywords: ["yarnnn pricing", "ai workspace pricing", "shared ai workspace", "per seat ai pricing", "team ai plan", "usage-based ai pricing", "transparent ai usage"],
});

// ADR-445 (2026-07-12): the TWO-AXIS pricing model (supersedes ADR-429's three
// axes). There is NO separate per-workspace base fee — the paid subscription IS the
// per-seat price. Two axes:
//   ① SEATS — seat 1 (the owner) is free; each additional human is a priced seat
//      ($20/seat/mo). Unlimited workspaces; a solo workspace is free; a team is paid
//      at (humans − 1) × the seat fee. The free→paid boundary is the 2nd human. AI
//      connections are never seats and never charged.
//   ② METERED USAGE — the paid plan grants a monthly POOLED allowance the whole
//      workspace draws (owner-funded); top-ups sit beneath; hard-stop at zero.
// The tier ladder is Free + one paid plan (`pro` dormant, returns with the capture
// lane). Numbers ($0 / $20 seat / $15 pooled allowance) are launch-test values,
// reversible against first-customer evidence (ADR-396 §7 standing discipline).

const PLANS = [
  {
    name: "Free",
    price: "$0",
    cadence: "for one person",
    blurb: "Your memory — files, notes, and context — kept with full history and reachable from every AI you use. Free forever for one person, no card.",
    cta: "Start free",
    href: CTA.signup,
    featured: false,
    points: [
      "Workspace + memory, free forever for one person",
      "$3 starting balance — feel the loop before you spend",
      "Reachable from any AI over MCP — always free",
      "Add a teammate anytime on the paid plan",
    ],
  },
  {
    name: "Starter",
    price: "$20",
    cadence: "/seat/mo",
    blurb: "For a real team working out of one shared workspace. You stay free; each teammate is a paid seat, and usage is one shared pool the workspace draws from.",
    cta: "Go Starter",
    href: CTA.signup,
    featured: true,
    points: [
      "Everything in Free — your seat stays free",
      "$20/mo per teammate you add",
      "$15 of monthly usage included — one shared pool",
      "Connect any AI over MCP — always free, never a seat",
    ],
  },
];

const HOW_IT_WORKS = [
  "Free for one person. Your workspace, your memory, and your own seat are free forever — you only pay when you bring a teammate.",
  "A seat per teammate. Each additional person on the workspace is a paid seat; AI connections you plug in over MCP are always free and never a seat.",
  "One shared usage pool. The paid plan includes a monthly amount of usage the whole workspace draws from — you, your teammates, and any AI all draw the same pool, funded by the owner.",
  "Need more in a heavy month? Top up any amount from $5. Top-ups never expire and sit beneath your allowance. Hard stop at zero — nothing is lost, you resume by topping up.",
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
                Free for one.<br />A seat for the team.
              </h1>
              <p className="text-white/50 text-lg max-w-2xl mx-auto">
                Your workspace and your memory are free forever for one person. Add a
                teammate and each extra person is a paid seat; usage is one shared
                pool the owner funds. AI connections are always free — never a seat.
                See every action; never a surprise bill.
              </p>
            </div>

            {/* Plan ladder — Free + one paid plan (ADR-445); two cards, centered */}
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
                  <h3 className="text-lg font-medium mb-3">What does a seat cost?</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    A seat is a human on your workspace. The first seat — you, the owner — is free.
                    Each teammate you add is $20/mo. Every human draws the same shared usage pool the
                    owner funds — and any AI you connect over MCP is always free, never a seat and
                    never a charge.
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
                    workspace and your memory are free forever for one person. A paid plan is for a
                    real team — inviting your first teammate makes the workspace paid ($20/mo per
                    person), and includes a shared monthly usage pool the work draws from.
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
