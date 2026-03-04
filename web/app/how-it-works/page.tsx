import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata: Metadata = getMarketingMetadata({
  title: "How yarnnn works",
  description:
    "Tell yarnnn what recurring work you need, connect your tools, and review the drafts it prepares for you. It gets better every cycle.",
  path: "/how-it-works",
  keywords: [
    "how yarnnn works",
    "ai for work",
    "automated reports",
    "ai assistant",
    "work automation",
  ],
});

export default function HowItWorksPage() {
  const howToSchema = {
    "@context": "https://schema.org",
    "@type": "HowTo",
    name: "How yarnnn works",
    description: metadata.description,
    url: `${BRAND.url}/how-it-works`,
    step: [
      {
        "@type": "HowToStep",
        name: "Tell yarnnn what recurring work you want done",
      },
      {
        "@type": "HowToStep",
        name: "Connect Slack, Gmail, Notion, and Calendar",
      },
      {
        "@type": "HowToStep",
        name: "Review and approve the drafts yarnnn prepares",
      },
      {
        "@type": "HowToStep",
        name: "Keep using it and watch quality improve",
      },
    ],
  };

  return (
    <div className="relative min-h-screen flex flex-col bg-[#0f1419] text-white overflow-x-hidden">
      <GrainOverlay variant="dark" />
      <ShaderBackgroundDark />

      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted />

        <main className="flex-1">
          <section className="max-w-4xl mx-auto px-6 py-24 md:py-32">
            <p className="text-white/40 text-sm uppercase tracking-widest mb-4">How It Works</p>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-10 tracking-tight leading-[1.1]">
              You describe the work.
              <br />
              <span className="text-white/50">yarnnn does the first draft.</span>
            </h1>
            <p className="max-w-2xl text-white/50 text-lg">
              No complex setup required. Just explain what you need each week,
              connect your tools, and review what yarnnn prepares.
            </p>
          </section>

          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="border border-white/10 rounded-xl p-6 bg-white/5">
                <h2 className="text-xl font-medium mb-3">What you do</h2>
                <p className="text-white/50 text-sm leading-relaxed">
                  Tell yarnnn what output you want, choose which tools to connect,
                  and approve drafts before they are used.
                </p>
              </div>
              <div className="border border-white/10 rounded-xl p-6 bg-white/5">
                <h2 className="text-xl font-medium mb-3">What yarnnn does</h2>
                <p className="text-white/50 text-sm leading-relaxed">
                  Collects the right context from your tools, writes the draft,
                  and learns from your edits so next time needs less work.
                </p>
              </div>
            </div>
          </section>

          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">The simple 3-step flow</h2>
              <p className="text-white/50 leading-relaxed mb-16 max-w-2xl">
                Think of yarnnn like a teammate you train once, then supervise.
              </p>

              <div className="space-y-14">
                <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6">
                  <div className="text-4xl font-light text-white/20">01</div>
                  <div>
                    <h3 className="text-xl font-medium mb-3">Ask for the output you want</h3>
                    <p className="text-white/50 leading-relaxed">
                      Example: &ldquo;Every Monday, give me a short update from #engineering and customer emails.&rdquo;
                      yarnnn can ask a few follow-up questions, then saves that as your workflow.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6">
                  <div className="text-4xl font-light text-white/20">02</div>
                  <div>
                    <h3 className="text-xl font-medium mb-3">Connect the tools where your work lives</h3>
                    <p className="text-white/50 leading-relaxed">
                      Connect Slack, Gmail, Notion, and Calendar. yarnnn reads selected content so
                      it can draft with real context instead of guessing.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6">
                  <div className="text-4xl font-light text-white/20">03</div>
                  <div>
                    <h3 className="text-xl font-medium mb-3">Review drafts and click approve</h3>
                    <p className="text-white/50 leading-relaxed">
                      You stay in control. yarnnn writes the first draft,
                      you edit if needed, and each edit teaches it how to do better next time.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">What people use it for</h2>
              <p className="text-white/50 leading-relaxed mb-12">
                Common examples of recurring work yarnnn can handle.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm">Weekly team update from Slack + Notion</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm">Meeting prep from email + calendar</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm">Client follow-up summary every Friday</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm">Leadership status report with key risks first</p>
                </div>
              </div>
            </div>
          </section>

          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Start simple.
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Begin with one weekly workflow. Once it feels good, add more.
              </p>
              <Link
                href="/auth/login"
                className="inline-block px-8 py-4 bg-white text-black text-lg font-medium rounded-full hover:bg-white/90 transition-colors"
              >
                Start with yarnnn
              </Link>
            </div>
          </section>
        </main>

        <LandingFooter inverted />
      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(howToSchema) }}
      />
    </div>
  );
}
