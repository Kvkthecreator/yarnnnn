import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";

export const metadata: Metadata = {
  title: "Pricing",
  description: "Simple, transparent pricing for yarnnn.",
};

export default function PricingPage() {
  return (
    <div className="relative min-h-screen flex flex-col bg-[#0a0a0a] text-white overflow-x-hidden">
      <GrainOverlay />
      <ShaderBackgroundDark />

      {/* Content layer */}
      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted />

        <main className="flex-1 flex flex-col items-center justify-center px-6 py-24 md:py-32">
          <div className="max-w-2xl mx-auto text-center">
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-8 tracking-tight">
              Pricing
            </h1>

            <div className="border border-white/10 rounded-2xl p-12 mb-12">
              <p className="text-white/50 text-lg mb-6">
                We&apos;re currently in early access.
              </p>
              <p className="text-2xl font-medium mb-8">
                Coming soon
              </p>
              <p className="text-white/50 text-sm leading-relaxed max-w-md mx-auto">
                We&apos;re working on pricing that makes sense for individuals,
                teams, and agencies. Simple, transparent, and built around
                how you actually use the platform.
              </p>
            </div>

            <p className="text-white/40 text-sm mb-8">
              Want early access or have questions about pricing?
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                href="/auth/login"
                className="inline-block px-8 py-4 bg-white text-black font-medium rounded-full hover:bg-white/90 transition-colors"
              >
                Get early access
              </Link>
              <a
                href="mailto:contactus@yarnnn.com"
                className="inline-block px-8 py-4 border border-white/20 text-white font-medium rounded-full hover:bg-white/10 transition-colors"
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
