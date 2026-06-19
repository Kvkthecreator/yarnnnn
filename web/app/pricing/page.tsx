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
  title: "Pricing — pay for what runs, nothing you don't",
  description:
    "The workspace is free forever. Running an operation costs only the usage it draws — metered at transparent rates, read line by line, hard stop at zero. No seats, no subscription, no feature gates.",
  path: "/pricing",
  keywords: ["yarnnn pricing", "pay as you go ai", "usage-based ai pricing", "ai operation pricing", "transparent ai usage", "no subscription ai"],
});

// ADR-172/291 balance model is the SOLE active pricing model (ADR-334 seat tiers
// demoted to deferred hypothesis 2026-06-19). This page reflects pay-as-you-go:
// free workspace + metered usage drawn from a balance. No seat tiers advertised,
// no checkout beyond the live bare-workspace signup. cta.ts::seatCheckout stays null.

const PAYG_POINTS = [
  "The full product on every workspace — files, chat, context reachable from any AI you use (MCP), and operations when you run them. No features locked behind a tier.",
  "Usage is metered at transparent rates and drawn from your balance. You read every line — there is no opaque bill.",
  "Hard stop at zero. The operation pauses; nothing is lost; you resume by topping up. You never owe a surprise.",
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
          "Free workspace with a $3 starting balance; pay-as-you-go usage drawn from balance, topped up as needed.",
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
                Pay for what runs.
              </h1>
              <p className="text-white/50 text-lg max-w-2xl mx-auto">
                The workspace is free. When an operation runs on it, you pay only the
                usage it draws — metered at transparent rates, read line by line. No seats,
                no subscription, no feature gates.
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
                      use (MCP). Starts with a $3 usage balance. Top up whenever you want to run
                      more — only what you use is ever charged.
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

            {/* Pay-as-you-go card */}
            <div className="max-w-3xl mx-auto mb-6">
              <SpotlightCard variant="dark" spotlightSize={500} className="ring-1 ring-white/15">
                <div className="p-8">
                  <div className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 mb-3">
                    How running costs work
                  </div>
                  <div className="flex items-baseline gap-2 mb-5">
                    <h2 className="text-2xl font-medium">Usage</h2>
                    <span className="text-white/40 text-sm">pay-as-you-go · no subscription</span>
                  </div>
                  <ul className="space-y-4">
                    {PAYG_POINTS.map((p) => (
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

            {/* Three honest paragraphs */}
            <div className="max-w-3xl mx-auto mb-16 grid gap-6">
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6">
                  <h3 className="text-lg font-medium mb-3">What&apos;s an operation?</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    An activated program running on your workspace — your newsletter operation,
                    your portfolio operation. It draws usage from your balance while it runs. The
                    workspace itself is always free.
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
                  <h3 className="text-lg font-medium mb-3">Why not a subscription?</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Because you shouldn&apos;t pay for a month you didn&apos;t run. Pricing follows
                    the work: an idle workspace costs nothing, an active operation costs what it
                    draws. As real usage teaches us what a fair plan looks like, we&apos;ll offer
                    one — we won&apos;t guess one ahead of you.
                  </p>
                </div>
              </SpotlightCard>
            </div>

            {/* Mini-FAQ */}
            <div className="max-w-3xl mx-auto mb-16">
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6 space-y-4 text-white/50 text-sm leading-relaxed">
                  <p>
                    <strong className="text-white/70">Starting balance.</strong> Every workspace
                    begins with a $3 usage credit — enough to author your context and watch the
                    correction loop firsthand before you spend anything.
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
