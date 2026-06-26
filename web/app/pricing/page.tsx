import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { SpotlightCard } from "@/components/landing/SpotlightCard";
import { Check, Wallet, ShieldCheck } from "lucide-react";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";
import { CTA } from "@/lib/cta";

export const metadata = getMarketingMetadata({
  title: "Pricing — free workspace, a balance you fund, a budget you cap",
  description:
    "The workspace is free forever. An operation draws metered usage from a balance you fund — and never past a monthly budget you set. Pay-as-you-go with a planned ceiling: idle costs nothing, an active operation costs what it draws, and the agent self-throttles to stay under your cap.",
  path: "/pricing",
  keywords: ["yarnnn pricing", "pay as you go ai", "usage-based ai pricing", "ai operation budget", "monthly ai spend cap", "transparent ai usage", "no subscription ai"],
});

// First-principles rewrite (2026-06-24). The money model is THREE facts, not one:
//   1. The workspace is free forever (ADR-172).
//   2. You fund a BALANCE — $3 to start, top-ups from $10; metered usage drawn
//      from it; hard stop at zero (ADR-171/172). Answers "will I get a surprise bill?"
//   3. You set an operation BUDGET — a dollar ceiling over a window (default
//      $50/monthly; in-app presets $30/$50/$100/$200). The agent allocates its
//      own work to stay under your cap (ADR-327). Answers "how do I plan spend?"
// The prior page narrated only (1)+(2) and collapsed all surprise-prevention into
// hard-stop-at-zero, leaving the budget envelope — the thing that makes spend
// PLANNABLE — invisible. The tier ladder below is the public face of (3).
// IMPORTANT: the ladder is a CAP THE OPERATOR SETS, never a charge we bill. No
// subscription exists; cta.ts::seatCheckout stays null. The three rungs are
// cosmetic anchors — the truth is "any amount, set via chat or the in-app dial."

const FUNDING_POINTS = [
  "Metered at transparent rates and drawn from your balance — you read every line. There is no opaque bill.",
  "Idle costs nothing. The workspace is free; only a running operation draws usage.",
  "Hard stop at zero. The operation pauses, nothing is lost, and you resume by topping up. You never owe a surprise.",
];

// The budget ladder. Anchors are illustrative — operators set any amount in-app.
// Labels frame the level of activity each ceiling comfortably covers.
const BUDGET_TIERS = [
  {
    name: "Light",
    anchor: "~$50",
    blurb: "A focused operation — a few runs a week. The default ceiling for most workspaces.",
  },
  {
    name: "Standard",
    anchor: "~$100",
    blurb: "An operation working most days, with room for research and revision.",
  },
  {
    name: "Heavy",
    anchor: "~$150+",
    blurb: "High-cadence work or several operations running at once.",
  },
];

export default function PricingPage() {
  const pricingSchema = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: BRAND.name,
    url: `${BRAND.url}/pricing`,
    applicationCategory: "BusinessApplication",
    offers: [
      {
        "@type": "Offer",
        name: "Workspace + usage",
        description:
          "Free workspace with a $3 starting balance; pay-as-you-go usage drawn from a balance you fund, capped by a monthly budget you set. Top up from $10 as needed.",
        price: "0",
        priceCurrency: "USD",
        url: `${BRAND.url}/pricing`,
      },
    ],
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
                Free to keep.<br />You set what it spends.
              </h1>
              <p className="text-white/50 text-lg max-w-2xl mx-auto">
                The workspace is free forever. When an operation runs on it, it
                draws metered usage from a balance you fund — and never past a
                monthly budget you set. No subscription. No feature gates.
              </p>
            </div>

            {/* Card 1 · Free workspace */}
            <div className="max-w-3xl mx-auto mb-8">
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-8 md:flex md:items-center md:justify-between gap-8">
                  <div className="mb-6 md:mb-0">
                    <div className="flex items-baseline gap-2 mb-2">
                      <h2 className="text-2xl font-medium">Workspace</h2>
                      <span className="text-3xl font-medium">$0</span>
                      <span className="text-white/40 text-sm">forever</span>
                    </div>
                    <p className="text-white/50 text-sm max-w-md leading-relaxed">
                      Your memory: files, notes, and context — kept with a full history and
                      reachable from every AI you use. Starts with a $3 balance — enough to feel it
                      before you spend a cent.
                    </p>
                  </div>
                  <Link
                    href={CTA.signup}
                    className="block shrink-0 text-center px-6 py-3 bg-white text-black font-medium rounded-full hover:bg-white/90 transition-colors"
                  >
                    Start free
                  </Link>
                </div>
              </SpotlightCard>
            </div>

            {/* Card 2 · The budget you set — the centerpiece */}
            <div className="max-w-3xl mx-auto mb-8">
              <SpotlightCard variant="dark" spotlightSize={500} className="ring-1 ring-emerald-400/25">
                <div className="p-8">
                  <div className="flex items-center gap-2 mb-3">
                    <Wallet className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-[10px] font-mono uppercase tracking-wider text-emerald-400">
                      The budget you set
                    </span>
                  </div>
                  <h2 className="text-2xl font-medium mb-2">Name a monthly ceiling.</h2>
                  <p className="text-white/50 text-sm max-w-xl leading-relaxed mb-7">
                    Set how much an operation may spend in a month. The agent allocates
                    its own work to stay under it — it decides how often to run, you decide
                    the most it can cost. Change it anytime.
                  </p>

                  {/* Tier ladder — illustrative anchors, operator-set */}
                  <div className="grid gap-3 sm:grid-cols-3 mb-6">
                    {BUDGET_TIERS.map((t) => (
                      <div
                        key={t.name}
                        className="rounded-xl border border-white/10 bg-white/[0.02] p-4 flex flex-col"
                      >
                        <div className="flex items-baseline justify-between mb-1.5">
                          <span className="text-sm font-medium text-white/80">{t.name}</span>
                          <span className="text-lg font-medium">{t.anchor}<span className="text-white/40 text-xs">/mo</span></span>
                        </div>
                        <p className="text-white/45 text-xs leading-relaxed">{t.blurb}</p>
                      </div>
                    ))}
                  </div>

                  <div className="flex items-start gap-2 rounded-lg bg-emerald-400/[0.06] border border-emerald-400/15 px-4 py-3">
                    <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    <p className="text-white/60 text-xs leading-relaxed">
                      <strong className="text-white/80">This is a cap you set — not a charge.</strong>{" "}
                      Nothing here is billed. You only ever pay for the usage that actually runs
                      (below). The ceiling just stops an operation from spending past it. These
                      three are common starting points — set any amount in chat or the in-app dial.
                    </p>
                  </div>
                </div>
              </SpotlightCard>
            </div>

            {/* Card 3 · What you actually pay */}
            <div className="max-w-3xl mx-auto mb-6">
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-8">
                  <div className="text-[10px] font-mono uppercase tracking-wider text-white/40 mb-3">
                    What you actually pay
                  </div>
                  <div className="flex items-baseline gap-2 mb-5">
                    <h2 className="text-2xl font-medium">Usage</h2>
                    <span className="text-white/40 text-sm">pay-as-you-go · drawn from your balance</span>
                  </div>
                  <ul className="space-y-4">
                    {FUNDING_POINTS.map((p) => (
                      <li key={p} className="flex items-start gap-3 text-sm text-white/70 leading-relaxed">
                        <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span>{p}</span>
                      </li>
                    ))}
                  </ul>
                  <div className="mt-7">
                    <Link
                      href={CTA.signup}
                      className="inline-block text-center px-6 py-3 bg-white text-black font-medium rounded-full hover:bg-white/90 transition-colors"
                    >
                      Start free
                    </Link>
                    <span className="ml-4 text-white/40 text-sm">
                      Top-ups from $10 when you need more.
                    </span>
                  </div>
                </div>
              </SpotlightCard>
            </div>

            <p className="text-center text-white/40 text-sm mb-16">
              No card to start. The $3 balance is enough to feel the loop before you spend a cent.
            </p>

            {/* Two guardrails explainer — the budget vs the floor */}
            <div className="max-w-3xl mx-auto mb-16">
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
                      no more. Raise or lower it whenever.
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
                      The absolute stop. If your balance ever reaches zero the operation simply
                      pauses — nothing is lost, no overage, no surprise. You resume by topping up.
                    </p>
                  </div>
                </SpotlightCard>
              </div>
            </div>

            {/* Three honest paragraphs */}
            <div className="max-w-3xl mx-auto mb-16 grid gap-6">
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6">
                  <h3 className="text-lg font-medium mb-3">What&apos;s an operation?</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    An operation is the optional assistant (in beta) running on your workspace. It
                    draws usage from your balance while it&apos;s working, capped by the budget you
                    set. Your memory, files, and access from any AI are always free.
                  </p>
                </div>
              </SpotlightCard>
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6">
                  <h3 className="text-lg font-medium mb-3">What&apos;s &ldquo;usage&rdquo;?</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Every model call is metered at transparent rates and drawn from your balance —
                    you can read every line of it. Most workspaces spend a few dollars a month;
                    heavier months top up from $10. You only ever pay for what actually ran.
                  </p>
                </div>
              </SpotlightCard>
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6">
                  <h3 className="text-lg font-medium mb-3">Why a budget instead of a subscription?</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    A subscription charges for a month whether you ran anything or not. A budget
                    does the opposite: it&apos;s a ceiling <em>you</em> set, the agent stays under it,
                    and you only pay for the usage that actually happened. You get the predictability
                    of a fixed plan — &ldquo;never more than $100 this month&rdquo; — without paying for
                    an idle month.
                  </p>
                </div>
              </SpotlightCard>
            </div>

            {/* Mini-FAQ */}
            <div className="max-w-3xl mx-auto mb-16">
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6 space-y-4 text-white/50 text-sm leading-relaxed">
                  <p>
                    <strong className="text-white/70">Is the tier a charge?</strong> No. The budget
                    is a ceiling you set, not a plan we bill. You&apos;re only ever charged for the
                    usage that actually runs, drawn from your balance.
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
                    <strong className="text-white/70">If your balance hits zero,</strong> the
                    operation pauses — nothing is lost. Top up to resume.
                  </p>
                  <p>
                    <strong className="text-white/70">If you stop running an operation,</strong> it
                    simply stops drawing usage. The workspace and every file remain yours, free.
                  </p>
                </div>
              </SpotlightCard>
            </div>

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
