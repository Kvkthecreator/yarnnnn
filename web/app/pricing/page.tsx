import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { SpotlightCard } from "@/components/landing/SpotlightCard";
import { Check, X } from "lucide-react";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata = getMarketingMetadata({
  title: "Pricing",
  description:
    "Free and Pro plans for autonomous recurring work. Every plan includes the scaffolded workforce, Thinking Partner, and platform integrations. Upgrade for more active tasks and higher monthly usage.",
  path: "/pricing",
  keywords: ["yarnnn pricing", "autonomous AI pricing", "AI workforce plans", "agent pricing", "ai task pricing"],
});

interface PricingFeature {
  name: string;
  free: string | boolean;
  pro: string | boolean;
}

const features: PricingFeature[] = [
  { name: "Scaffolded workforce", free: "Included", pro: "Included" },
  { name: "Active tasks", free: "2", pro: "10" },
  { name: "Monthly usage included", free: "$3", pro: "$20" },
  { name: "Monthly messages", free: "150", pro: "Unlimited" },
  { name: "Platforms available", free: "All", pro: "All" },
  { name: "Slack sources", free: "5", pro: "Unlimited" },
  { name: "Notion pages", free: "10", pro: "Unlimited" },
  { name: "Sync frequency", free: "1x daily", pro: "Hourly" },
  { name: "Rich output (PDF, PPTX, XLSX)", free: true, pro: true },
  { name: "Task history & review", free: true, pro: true },
  { name: "Learning from your edits", free: true, pro: true },
  { name: "Multi-agent tasks", free: true, pro: true },
  { name: "Priority support", free: false, pro: true },
];

function FeatureValue({ value }: { value: string | boolean }) {
  if (typeof value === "boolean") {
    return value ? (
      <Check className="w-5 h-5 text-emerald-400" />
    ) : (
      <X className="w-5 h-5 text-white/30" />
    );
  }
  return <span>{value}</span>;
}

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
        name: "Free",
        price: "0",
        priceCurrency: "USD",
        url: `${BRAND.url}/pricing`,
      },
      {
        "@type": "Offer",
        name: "Pro",
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
            <div className="text-center mb-16">
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-6 tracking-tight">
                Simple, honest pricing
              </h1>
              <p className="text-white/50 text-lg max-w-2xl mx-auto">
                Every plan includes the scaffolded workforce, Thinking Partner,
                and platform integrations. Upgrade when you need more active
                tasks and fresher sync.
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-8 max-w-3xl mx-auto mb-16">
              {/* Free */}
              <SpotlightCard variant="dark" spotlightSize={400} className="flex flex-col">
                <div className="p-8 flex flex-col flex-1">
                  <div className="mb-8">
                    <h2 className="text-2xl font-medium mb-2">Free</h2>
                    <p className="text-white/50 text-sm mb-6">See the system run</p>
                    <div className="flex items-baseline gap-1">
                      <span className="text-4xl font-medium">$0</span>
                      <span className="text-white/50">/month</span>
                    </div>
                  </div>

                  <ul className="space-y-3 flex-1 mb-8">
                    <li className="flex items-center gap-3 text-sm">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>Scaffolded workforce + TP</span>
                    </li>
                    <li className="flex items-center gap-3 text-sm">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>2 active tasks</span>
                    </li>
                    <li className="flex items-center gap-3 text-sm">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>$3 usage included / month</span>
                    </li>
                    <li className="flex items-center gap-3 text-sm">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>150 messages / month</span>
                    </li>
                    <li className="flex items-center gap-3 text-sm">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>All platforms</span>
                    </li>
                    <li className="flex items-center gap-3 text-sm">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>Daily sync</span>
                    </li>
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
              <SpotlightCard variant="dark" spotlightColor="rgba(255,255,255,0.08)" spotlightSize={400} className="relative">
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-20">
                  <span className="px-3 py-1 bg-white text-black text-xs font-medium rounded-full">
                    Early Bird: $9/mo
                  </span>
                </div>

                <div className="p-8 flex flex-col">
                  <div className="mb-8">
                    <h2 className="text-2xl font-medium mb-2">Pro</h2>
                    <p className="text-white/50 text-sm mb-6">For a higher-throughput system</p>
                    <div className="flex items-baseline gap-1">
                      <span className="text-4xl font-medium">$19</span>
                      <span className="text-white/50">/month</span>
                    </div>
                    <p className="text-emerald-400 text-xs mt-2">
                      Beta pricing: $9/mo — locked in while available
                    </p>
                  </div>

                  <ul className="space-y-3 flex-1 mb-8">
                    <li className="flex items-center gap-3 text-sm">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>Scaffolded workforce + TP</span>
                    </li>
                    <li className="flex items-center gap-3 text-sm">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>10 active tasks</span>
                    </li>
                    <li className="flex items-center gap-3 text-sm">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>$20 usage included / month</span>
                    </li>
                    <li className="flex items-center gap-3 text-sm">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>Unlimited messages</span>
                    </li>
                    <li className="flex items-center gap-3 text-sm">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>Hourly sync</span>
                    </li>
                    <li className="flex items-center gap-3 text-sm">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>Unlimited sources</span>
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

            {/* What are task runs */}
            <div className="max-w-3xl mx-auto mb-16">
              <SpotlightCard variant="dark" spotlightSize={500}>
                <div className="p-6">
                <h3 className="text-lg font-medium mb-3">How pricing works</h3>
                <p className="text-white/50 text-sm leading-relaxed mb-4">
                  Every plan includes the same scaffolded workforce and Thinking
                  Partner. What changes by tier is how much autonomous work the
                  system can keep active at once.
                </p>
                <p className="text-white/50 text-sm leading-relaxed mb-4">
                  <strong className="text-white/70">Active tasks</strong> are recurring
                  work contracts the system keeps running. <strong className="text-white/70">Monthly usage</strong>
                  {" "}covers all LLM activity — chat, tasks, and web search — measured in dollars against Anthropic&apos;s published token rates. YARNNN uses Claude Sonnet at $6/M input tokens and $30/M output tokens.
                </p>
                <p className="text-white/40 text-xs">
                  Free is enough to feel the loop. Pro is for a system that runs
                  with more active tasks, higher usage, and faster sync.
                </p>
                </div>
              </SpotlightCard>
            </div>

            {/* Compare table */}
            <div className="border border-white/10 rounded-2xl overflow-hidden max-w-3xl mx-auto">
              <div className="p-6 border-b border-white/10">
                <h3 className="text-lg font-medium">Compare plans</h3>
              </div>
              <div className="overflow-x-auto min-w-0">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-white/10">
                      <th className="text-left p-4 text-sm font-medium text-white/50">Feature</th>
                      <th className="text-center p-4 text-sm font-medium">Free</th>
                      <th className="text-center p-4 text-sm font-medium">Pro</th>
                    </tr>
                  </thead>
                  <tbody>
                    {features.map((feature, i) => (
                      <tr key={feature.name} className={i < features.length - 1 ? "border-b border-white/5" : ""}>
                        <td className="p-4 text-sm">{feature.name}</td>
                        <td className="p-4 text-center text-sm">
                          <div className="flex justify-center">
                            <FeatureValue value={feature.free} />
                          </div>
                        </td>
                        <td className="p-4 text-center text-sm">
                          <div className="flex justify-center">
                            <FeatureValue value={feature.pro} />
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="text-center mt-16 mb-8">
              <p className="text-white/70 text-lg mb-2">All plans include the scaffolded workforce, TP, and all platforms.</p>
              <p className="text-white/40 text-sm">
                Slack, Notion, rich output formats, and feedback-driven learning are included on every plan.
              </p>
            </div>

            <div className="text-center">
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
