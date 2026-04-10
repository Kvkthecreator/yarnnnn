import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { SpotlightCard } from "@/components/landing/SpotlightCard";
import { Check } from "lucide-react";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata = getMarketingMetadata({
  title: "Pricing",
  description:
    "Usage-based pricing. Start with $3 free, top up when you need more, or subscribe for $20/month auto-refill. Every feature available on every plan.",
  path: "/pricing",
  keywords: ["yarnnn pricing", "autonomous AI pricing", "AI workforce pricing", "usage-based AI", "agent pricing"],
});

const everythingIncluded = [
  "Scaffolded 10-agent workforce",
  "Thinking Partner (TP)",
  "Unlimited tasks",
  "Slack, Notion, GitHub integrations",
  "Rich output — PDF, PPTX, XLSX",
  "Learning from your edits",
  "Multi-agent orchestration",
  "MCP context hub",
];

const topups = [
  { amount: "$10", detail: "~1,600 chat messages or ~20 full task runs" },
  { amount: "$25", detail: "~4,000 chat messages or ~50 full task runs" },
  { amount: "$50", detail: "~8,000 chat messages or ~100 full task runs" },
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
        name: "Pay as you go",
        price: "0",
        priceCurrency: "USD",
        url: `${BRAND.url}/pricing`,
      },
      {
        "@type": "Offer",
        name: "Pro subscription",
        price: "19",
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
                Pay for what you use
              </h1>
              <p className="text-white/50 text-lg max-w-2xl mx-auto">
                Start with $3 free. Top up when you need more, or subscribe for
                $20/month auto-refill. Every feature is available on every plan.
              </p>
            </div>

            {/* Two cards: Pay as you go + Pro */}
            <div className="grid md:grid-cols-2 gap-8 max-w-3xl mx-auto mb-16">

              {/* Pay as you go */}
              <SpotlightCard variant="dark" spotlightSize={400} className="flex flex-col">
                <div className="p-8 flex flex-col flex-1">
                  <div className="mb-8">
                    <h2 className="text-2xl font-medium mb-2">Pay as you go</h2>
                    <p className="text-white/50 text-sm mb-6">No subscription needed</p>
                    <div className="flex items-baseline gap-1">
                      <span className="text-4xl font-medium">$3</span>
                      <span className="text-white/50"> free to start</span>
                    </div>
                    <p className="text-white/40 text-xs mt-2">Then top up $10, $25, or $50 as needed</p>
                  </div>

                  <ul className="space-y-3 flex-1 mb-8">
                    {everythingIncluded.map((item) => (
                      <li key={item} className="flex items-center gap-3 text-sm">
                        <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>

                  <Link
                    href="/auth/login"
                    className="block w-full text-center px-6 py-3 border border-white/20 text-white font-medium rounded-full hover:bg-white/10 transition-colors"
                  >
                    Start free
                  </Link>
                </div>
              </SpotlightCard>

              {/* Pro */}
              <SpotlightCard variant="dark" spotlightColor="rgba(255,255,255,0.08)" spotlightSize={400} className="relative flex flex-col">
                <div className="p-8 flex flex-col flex-1">
                  <div className="mb-8">
                    <h2 className="text-2xl font-medium mb-2">Pro</h2>
                    <p className="text-white/50 text-sm mb-6">For high-throughput workflows</p>
                    <div className="flex items-baseline gap-1">
                      <span className="text-4xl font-medium">$19</span>
                      <span className="text-white/50">/month</span>
                    </div>
                    <p className="text-emerald-400 text-xs mt-2">
                      $20 usage balance auto-refills every billing cycle
                    </p>
                  </div>

                  <ul className="space-y-3 flex-1 mb-8">
                    {everythingIncluded.map((item) => (
                      <li key={item} className="flex items-center gap-3 text-sm">
                        <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                        <span>{item}</span>
                      </li>
                    ))}
                    <li className="flex items-center gap-3 text-sm">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span className="font-medium">$20 balance refills monthly</span>
                    </li>
                    <li className="flex items-center gap-3 text-sm">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>Priority support</span>
                    </li>
                  </ul>

                  <Link
                    href="/auth/login"
                    className="block w-full text-center px-6 py-3 bg-white text-black font-medium rounded-full hover:bg-white/90 transition-colors"
                  >
                    Get Pro
                  </Link>
                </div>
              </SpotlightCard>
            </div>

            {/* Top-up reference card */}
            <div className="max-w-3xl mx-auto mb-16">
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6">
                  <h3 className="text-lg font-medium mb-1">Top-up amounts</h3>
                  <p className="text-white/40 text-sm mb-5">
                    One-time purchases, no subscription required. Balance never expires.
                  </p>
                  <div className="space-y-3">
                    {topups.map(({ amount, detail }) => (
                      <div key={amount} className="flex items-center justify-between">
                        <span className="text-sm font-medium">{amount}</span>
                        <span className="text-white/40 text-xs">{detail}</span>
                      </div>
                    ))}
                  </div>
                  <p className="text-white/30 text-xs mt-5">
                    Estimates based on Claude Sonnet at $6/M input · $30/M output tokens (2× Anthropic list rates).
                  </p>
                </div>
              </SpotlightCard>
            </div>

            {/* How pricing works */}
            <div className="max-w-3xl mx-auto mb-16">
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6">
                  <h3 className="text-lg font-medium mb-3">How it works</h3>
                  <div className="space-y-3 text-white/50 text-sm leading-relaxed">
                    <p>
                      Your <strong className="text-white/70">balance</strong> is the only gate.
                      Every chat message, task run, and web search draws from it.
                      When it hits zero, work pauses — top up to continue.
                    </p>
                    <p>
                      <strong className="text-white/70">Pro subscribers</strong> get $20 balance
                      auto-refilled every billing cycle. You can also top up at any time regardless of plan.
                    </p>
                    <p>
                      All features — tasks, agents, integrations, output formats, multi-agent work —
                      are available on every plan. There are no capability tiers.
                    </p>
                  </div>
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
