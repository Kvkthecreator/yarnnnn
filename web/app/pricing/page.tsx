import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { SpotlightCard } from "@/components/landing/SpotlightCard";
import { Check } from "lucide-react";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";
import { CTA } from "@/lib/cta";

export const metadata = getMarketingMetadata({
  title: "Pricing — priced by trust, not by features",
  description:
    "The workspace is free forever. When you run an operation on it, seats start at $149/month — priced by how much you delegate, not by features. 14-day trial.",
  path: "/pricing",
  keywords: ["yarnnn pricing", "ai operation pricing", "per-operation pricing", "delegation pricing", "ai seat pricing", "solopreneur ai pricing"],
});

// ADR-334 three-seat model. CHECKOUT GUARD (spec §0.8): seat checkout (P1–P3)
// is unbuilt; all CTAs route to CTA.signup under "seat trials open soon" framing.
const SEATS = [
  {
    name: "Supervised",
    price: "$149",
    tagline: "Every consequential action waits for you",
    usage: "$15/mo usage included",
    highlight: false,
    features: ["Full workspace, full trail", "Manual delegation — nothing acts without your approval"],
  },
  {
    name: "Delegated",
    price: "$299",
    tagline: "Acts within ceilings you declare",
    usage: "$30/mo usage included",
    highlight: true,
    features: ["Everything in Supervised", "Bounded autonomy — acts within the limits you set"],
  },
  {
    name: "Autonomous",
    price: "$499",
    tagline: "Runs the framework you authored",
    usage: "$60/mo usage included",
    highlight: false,
    features: ["Everything in Delegated", "Full autonomy within your declared framework"],
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
        name: "Workspace",
        price: "0",
        priceCurrency: "USD",
        url: `${BRAND.url}/pricing`,
      },
      {
        "@type": "Offer",
        name: "Supervised seat",
        price: "149",
        priceCurrency: "USD",
        billingDuration: "P1M",
        url: `${BRAND.url}/pricing`,
      },
      {
        "@type": "Offer",
        name: "Delegated seat",
        price: "299",
        priceCurrency: "USD",
        billingDuration: "P1M",
        url: `${BRAND.url}/pricing`,
      },
      {
        "@type": "Offer",
        name: "Autonomous seat",
        price: "499",
        priceCurrency: "USD",
        billingDuration: "P1M",
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
                Priced by trust, not by features.
              </h1>
              <p className="text-white/50 text-lg max-w-2xl mx-auto">
                Every plan is the full product. The only thing a tier changes is how much the
                operation may do without your approval — and how much usage is included.
              </p>
            </div>

            {/* Free workspace card */}
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
                      The substrate: files, uploads, chat, your context reachable from any AI you
                      use (MCP). No running operation. Includes a $3 usage credit; top-ups
                      available.
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

            {/* Seat cards */}
            <p className="text-center text-white/40 text-sm mb-6">
              Seats — per operation / month <span className="text-white/25">·</span> annual = 10× (two months free)
            </p>
            <div className="grid md:grid-cols-3 gap-6 mb-6">
              {SEATS.map((seat) => (
                <SpotlightCard
                  key={seat.name}
                  variant="dark"
                  spotlightColor={seat.highlight ? "rgba(255,255,255,0.10)" : undefined}
                  spotlightSize={400}
                  className={`flex flex-col ${seat.highlight ? "ring-1 ring-white/20" : ""}`}
                >
                  <div className="p-7 flex flex-col flex-1">
                    {seat.highlight && (
                      <div className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 mb-3">
                        Most operators start here
                      </div>
                    )}
                    <h3 className="text-xl font-medium mb-1">{seat.name}</h3>
                    <div className="flex items-baseline gap-1 mb-1">
                      <span className="text-3xl font-medium">{seat.price}</span>
                      <span className="text-white/40 text-sm">/mo</span>
                    </div>
                    <p className="text-white/50 text-sm mb-4">{seat.tagline}</p>
                    <p className="text-emerald-400/80 text-xs mb-6">{seat.usage}</p>

                    <ul className="space-y-3 flex-1 mb-6">
                      {seat.features.map((f) => (
                        <li key={f} className="flex items-start gap-3 text-sm text-white/70">
                          <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                          <span>{f}</span>
                        </li>
                      ))}
                    </ul>

                    {/* CHECKOUT GUARD §0.8 — routes to bare-workspace signup, not a seat purchase */}
                    <Link
                      href={CTA.signup}
                      className={`block w-full text-center px-6 py-3 font-medium rounded-full transition-colors ${
                        seat.highlight
                          ? "bg-white text-black hover:bg-white/90"
                          : "border border-white/20 text-white hover:bg-white/10"
                      }`}
                    >
                      Start free
                    </Link>
                  </div>
                </SpotlightCard>
              ))}
            </div>

            <p className="text-center text-white/40 text-sm mb-16">
              Seat trials open soon — 14 days, any tier, no card. Start free on the workspace today.
            </p>

            {/* Three honest paragraphs */}
            <div className="max-w-3xl mx-auto mb-16 grid gap-6">
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6">
                  <h3 className="text-lg font-medium mb-3">What&apos;s an operation?</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    An activated program running on your workspace — your newsletter operation,
                    your portfolio operation. Each runs on its own seat with its own dial. The
                    workspace itself is never paid.
                  </p>
                </div>
              </SpotlightCard>
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6">
                  <h3 className="text-lg font-medium mb-3">What&apos;s &ldquo;usage&rdquo;?</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Every model call is metered at transparent rates and drawn from your included
                    balance — you can read every line of it. Most operations use a fraction of
                    what&apos;s included; heavy months top up from $10.
                  </p>
                </div>
              </SpotlightCard>
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6">
                  <h3 className="text-lg font-medium mb-3">Why per-operation?</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Because the value isn&apos;t compute — it&apos;s the calls made correctly and
                    the asset that compounds. You pay for a running operation you trust, at the
                    level you trust it.
                  </p>
                </div>
              </SpotlightCard>
            </div>

            {/* Mini-FAQ */}
            <div className="max-w-3xl mx-auto mb-16">
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6 space-y-4 text-white/50 text-sm leading-relaxed">
                  <p>
                    <strong className="text-white/70">Trial.</strong> When seat trials open, every
                    plan offers 14 days on any tier with no card required — the trial&apos;s job is
                    a felt calibration trail, not a feature tour.
                  </p>
                  <p>
                    <strong className="text-white/70">If your balance hits zero,</strong> the
                    operation stops — nothing is lost. Top up to resume.
                  </p>
                  <p>
                    <strong className="text-white/70">If you cancel,</strong> the operation
                    deactivates. The workspace and every file remain yours, free.
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
