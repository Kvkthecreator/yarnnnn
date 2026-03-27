import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { Check, X } from "lucide-react";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata = getMarketingMetadata({
  title: "Pricing",
  description:
    "Free and Pro plans for your AI workforce. Every plan includes all 6 agents, Slack, and Notion. Start free, upgrade when you need more task capacity.",
  path: "/pricing",
  keywords: ["yarnnn pricing", "autonomous AI pricing", "AI workforce plans", "agent pricing", "ai task pricing"],
});

interface PricingFeature {
  name: string;
  free: string | boolean;
  pro: string | boolean;
}

const features: PricingFeature[] = [
  { name: "Pre-built agents", free: "6 (full roster)", pro: "6 (full roster)" },
  { name: "Active agents (with tasks)", free: "2", pro: "10" },
  { name: "Task runs / month", free: "60", pro: "1,000" },
  { name: "Monthly messages", free: "50", pro: "Unlimited" },
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
                Your full team is ready on every plan. Upgrade when your agents
                need more task capacity and faster sync.
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-8 max-w-3xl mx-auto mb-16">
              {/* Free */}
              <div className="border border-white/10 rounded-2xl p-8 flex flex-col">
                <div className="mb-8">
                  <h2 className="text-2xl font-medium mb-2">Free</h2>
                  <p className="text-white/50 text-sm mb-6">See what an AI workforce feels like</p>
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-medium">$0</span>
                    <span className="text-white/50">/month</span>
                  </div>
                </div>

                <ul className="space-y-3 flex-1 mb-8">
                  <li className="flex items-center gap-3 text-sm">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Full 6-agent roster</span>
                  </li>
                  <li className="flex items-center gap-3 text-sm">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>2 active agents with tasks</span>
                  </li>
                  <li className="flex items-center gap-3 text-sm">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>60 task runs / month</span>
                  </li>
                  <li className="flex items-center gap-3 text-sm">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>50 messages / month</span>
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

              {/* Pro */}
              <div className="border border-white/20 rounded-2xl p-8 flex flex-col bg-white/5 relative">
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="px-3 py-1 bg-white text-black text-xs font-medium rounded-full">
                    Early Bird: $9/mo
                  </span>
                </div>

                <div className="mb-8">
                  <h2 className="text-2xl font-medium mb-2">Pro</h2>
                  <p className="text-white/50 text-sm mb-6">Full autonomous workforce</p>
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
                    <span>Full 6-agent roster</span>
                  </li>
                  <li className="flex items-center gap-3 text-sm">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>10 active agents with tasks</span>
                  </li>
                  <li className="flex items-center gap-3 text-sm">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>1,000 task runs / month</span>
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
            </div>

            {/* What are task runs */}
            <div className="max-w-3xl mx-auto mb-16">
              <div className="border border-white/10 rounded-2xl p-6">
                <h3 className="text-lg font-medium mb-3">How pricing works</h3>
                <p className="text-white/50 text-sm leading-relaxed mb-4">
                  Every plan includes your full 6-agent roster (4 agents + 2 bots).
                  <strong className="text-white/70"> Active agents</strong> are agents with assigned tasks —
                  Free lets you activate 2, Pro lets you activate up to 10 (create additional
                  agents beyond the default roster as your needs grow).
                </p>
                <p className="text-white/50 text-sm leading-relaxed mb-4">
                  <strong className="text-white/70">Task runs</strong> measure the autonomous work your agents
                  do — each scheduled task execution and rendered output (PDF, slides, etc.) costs
                  one run. Messages (your conversations with agents) are counted separately.
                </p>
                <p className="text-white/40 text-xs">
                  Free: 60 runs/month covers daily tasks for 2 agents. Pro: 1,000 runs/month
                  covers a full workforce running multiple tasks per day.
                </p>
              </div>
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
              <p className="text-white/70 text-lg mb-2">All plans include your full agent roster and all platforms.</p>
              <p className="text-white/40 text-sm">
                Slack, Notion, rich output formats, and learning from feedback — included on every plan.
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
