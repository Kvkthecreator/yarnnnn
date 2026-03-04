import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata: Metadata = getMarketingMetadata({
  title: "About — Why we built yarnnn",
  description:
    "We built yarnnn to reduce repetitive writing work. Connect your tools, get better drafts, and stay in control through review.",
  path: "/about",
  keywords: [
    "about yarnnn",
    "ai for work",
    "work automation",
    "weekly reporting",
    "supervised ai",
  ],
});

export default function AboutPage() {
  const aboutSchema = {
    "@context": "https://schema.org",
    "@type": "AboutPage",
    name: "About yarnnn",
    description: metadata.description,
    url: `${BRAND.url}/about`,
    isPartOf: {
      "@type": "WebSite",
      name: BRAND.name,
      url: BRAND.url,
    },
  };

  return (
    <div className="relative min-h-screen flex flex-col bg-[#0f1419] text-white overflow-x-hidden">
      <GrainOverlay variant="dark" />
      <ShaderBackgroundDark />

      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted />

        <main className="flex-1">
          <section className="max-w-4xl mx-auto px-6 py-24 md:py-32">
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-10 tracking-tight leading-[1.1]">
              Why we built yarnnn
            </h1>
            <div className="max-w-2xl space-y-6 text-white/50">
              <p>
                Most people use AI by starting from a blank chat every time.
                That works for one-off tasks, but it is painful for recurring work.
              </p>
              <p>
                We wanted something simpler: connect your tools once,
                get drafts automatically, and improve them through normal review.
              </p>
              <p className="text-white font-medium">
                yarnnn is built to save time on repeated writing work while keeping you in control.
              </p>
            </div>
          </section>

          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">What we care about</h2>

              <div className="space-y-16">
                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Make setup easy</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      You should not need a long training manual to get value.
                      Start with one weekly workflow and improve from there.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Use real work context</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      Good drafts need real information. yarnnn reads from the tools
                      where your work already happens.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Keep humans in control</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      yarnnn drafts first. You review and approve.
                      The system helps you move faster without removing your judgment.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Improve over time</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      Every edit teaches yarnnn your style.
                      Draft quality should rise as you keep using it.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">What yarnnn is not</h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                  <h3 className="text-lg font-medium mb-2">Not a one-off prompt toy</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    It is built for repeated, real work, not just quick novelty outputs.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-medium mb-2">Not autopilot without review</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    You stay in charge. Approval is part of the workflow.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-medium mb-2">Not hard to set up</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    You can start with one simple use case and expand later.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-medium mb-2">Not tied to one app</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    It works across Slack, Gmail, Notion, and Calendar together.
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">Try your first workflow</h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Start with one weekly draft and adjust as you go.
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
        dangerouslySetInnerHTML={{ __html: JSON.stringify(aboutSchema) }}
      />
    </div>
  );
}
