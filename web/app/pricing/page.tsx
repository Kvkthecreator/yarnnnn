import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { Check, X } from "lucide-react";

export const metadata: Metadata = {
  title: "Pricing",
  description: "Simple pricing for turning your work platforms into deliverables. Free tier available. Pro at $19/mo.",
};

interface PricingFeature {
  name: string;
  free: string | boolean;
  pro: string | boolean;
}

const features: PricingFeature[] = [
  { name: "Active deliverables", free: "1", pro: "Unlimited" },
  { name: "Connected integrations", free: "Unlimited", pro: "Unlimited" },
  { name: "Versions per deliverable", free: "Unlimited", pro: "Unlimited" },
  { name: "Scheduled production", free: true, pro: true },
  { name: "Fresh context every cycle", free: true, pro: true },
  { name: "Learning from approvals", free: true, pro: true },
  { name: "Chat refinement", free: "10/month", pro: "Unlimited" },
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
  return (
    <div className="relative min-h-screen flex flex-col bg-[#0f1419] text-white overflow-x-hidden">
      <GrainOverlay variant="dark" />
      <ShaderBackgroundDark />

      {/* Content layer */}
      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted />

        <main className="flex-1 flex flex-col items-center px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto w-full">
            <div className="text-center mb-16">
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-6 tracking-tight">
                Simple pricing
              </h1>
              <p className="text-white/50 text-lg max-w-md mx-auto">
                Start free. Upgrade when you need more deliverables.
              </p>
            </div>

            {/* Pricing Cards */}
            <div className="grid md:grid-cols-2 gap-8 mb-16">
              {/* Free Tier */}
              <div className="border border-white/10 rounded-2xl p-8 flex flex-col">
                <div className="mb-8">
                  <h2 className="text-2xl font-medium mb-2">Free</h2>
                  <p className="text-white/50 text-sm mb-6">
                    Try the full supervision experience
                  </p>
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-medium">$0</span>
                    <span className="text-white/50">/month</span>
                  </div>
                </div>

                <ul className="space-y-3 flex-1 mb-8">
                  <li className="flex items-center gap-3 text-sm">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>1 active deliverable</span>
                  </li>
                  <li className="flex items-center gap-3 text-sm">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Unlimited integrations</span>
                  </li>
                  <li className="flex items-center gap-3 text-sm">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Unlimited versions</span>
                  </li>
                  <li className="flex items-center gap-3 text-sm">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Scheduled production</span>
                  </li>
                  <li className="flex items-center gap-3 text-sm">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Fresh context every cycle</span>
                  </li>
                  <li className="flex items-center gap-3 text-sm text-white/50">
                    <X className="w-4 h-4 text-white/30 shrink-0" />
                    <span>Multiple deliverables</span>
                  </li>
                </ul>

                <Link
                  href="/auth/login"
                  className="block w-full text-center px-6 py-3 border border-white/20 text-white font-medium rounded-full hover:bg-white/10 transition-colors"
                >
                  Get started free
                </Link>
              </div>

              {/* Pro Tier */}
              <div className="border border-white/20 rounded-2xl p-8 flex flex-col bg-white/5 relative">
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="px-3 py-1 bg-white text-black text-xs font-medium rounded-full">
                    Most popular
                  </span>
                </div>

                <div className="mb-8">
                  <h2 className="text-2xl font-medium mb-2">Pro</h2>
                  <p className="text-white/50 text-sm mb-6">
                    For professionals with multiple recurring deliverables
                  </p>
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-medium">$19</span>
                    <span className="text-white/50">/month</span>
                  </div>
                </div>

                <ul className="space-y-3 flex-1 mb-8">
                  <li className="flex items-center gap-3 text-sm">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Unlimited deliverables</span>
                  </li>
                  <li className="flex items-center gap-3 text-sm">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Unlimited integrations</span>
                  </li>
                  <li className="flex items-center gap-3 text-sm">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Unlimited versions</span>
                  </li>
                  <li className="flex items-center gap-3 text-sm">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Scheduled production</span>
                  </li>
                  <li className="flex items-center gap-3 text-sm">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Fresh context every cycle</span>
                  </li>
                  <li className="flex items-center gap-3 text-sm">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Unlimited chat refinement</span>
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
                  Start free trial
                </Link>
              </div>
            </div>

            {/* Feature Comparison Table */}
            <div className="border border-white/10 rounded-2xl overflow-hidden">
              <div className="p-6 border-b border-white/10">
                <h3 className="text-lg font-medium">Compare plans</h3>
              </div>
              <div className="overflow-x-auto min-w-0">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-white/10">
                      <th className="text-left p-4 text-sm font-medium text-white/50">
                        Feature
                      </th>
                      <th className="text-center p-4 text-sm font-medium">
                        Free
                      </th>
                      <th className="text-center p-4 text-sm font-medium">
                        Pro
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {features.map((feature, i) => (
                      <tr
                        key={feature.name}
                        className={
                          i < features.length - 1
                            ? "border-b border-white/5"
                            : ""
                        }
                      >
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

            {/* Value Prop */}
            <div className="text-center mt-16 mb-8">
              <p className="text-white/70 text-lg mb-2">
                Stop gathering. Start supervising.
              </p>
              <p className="text-white/40 text-sm">
                Same price as ChatGPT Plus. But yarnnn pulls from your platforms and learns from your approvals.
              </p>
            </div>

            {/* Integrations Note */}
            <div className="border border-white/10 rounded-xl p-6 text-center mb-8">
              <h4 className="text-white/70 font-medium mb-2">Why are integrations unlimited on all plans?</h4>
              <p className="text-white/40 text-sm max-w-lg mx-auto">
                The more platforms you connect, the better yarnnn works. We want everyone to experience
                the full supervision workflow—fresh context from where your work actually happens.
              </p>
            </div>

            {/* FAQ / Contact */}
            <div className="text-center">
              <p className="text-white/40 text-sm mb-4">
                Have questions about pricing or need a custom plan?
              </p>
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
    </div>
  );
}