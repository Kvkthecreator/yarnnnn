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
    "We built yarnnn because useful AI work requires persistent context and supervised autonomy. Specialists should improve over time, not restart every session.",
  path: "/about",
  keywords: [
    "about yarnnn",
    "autonomous ai",
    "context accumulation",
    "deliverable intelligence",
    "supervision model",
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
              We built yarnnn because
              <br />
              <span className="text-white/50">AI should compound, not reset.</span>
            </h1>
            <div className="max-w-2xl space-y-6 text-white/50">
              <p>
                Most AI products are powerful in a single interaction but weak over time.
                They do not retain the right work context, and they rarely run meaningful work autonomously.
              </p>
              <p>
                Real knowledge work is recurring and context-heavy. Good automation needs memory,
                source grounding, and supervision loops that improve quality each cycle.
              </p>
              <p className="text-white font-medium">
                yarnnn is our answer: a system of deliverable specialists that learns from your world and your approvals.
              </p>
            </div>
          </section>

          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">What we believe</h2>

              <div className="space-y-16">
                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Context creates utility</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      Intelligence without context produces generic output. Useful AI needs grounded awareness of
                      decisions, relationships, timing, and source history.
                    </p>
                    <p className="text-white/30 text-sm">
                      yarnnn connects directly to work platforms and accumulates evidence that improves future runs.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Supervision beats prompting</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      The goal is not faster prompting. The goal is reliable autonomous output that can be reviewed,
                      refined, and approved with clear control points.
                    </p>
                    <p className="text-white/30 text-sm">
                      In yarnnn, users supervise specialists instead of manually rebuilding the same deliverables.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Modeled autonomy matters</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      Different work needs different behaviors. Some deliverables should run on cadence.
                      Others should react to events, review proactively, or coordinate downstream work.
                    </p>
                    <p className="text-white/30 text-sm">
                      That is why yarnnn supports recurring, goal, reactive, proactive, and coordinator modes.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Compounding is the moat</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      Persistent source context plus specialist memory creates durable performance gains.
                      Over time, approval effort drops while quality rises.
                    </p>
                    <p className="text-white/30 text-sm">
                      The longer a specialist runs, the harder its accumulated intelligence is to replicate elsewhere.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">What yarnnn is not</h2>
              <p className="text-white/50 mb-12 max-w-xl">
                We intentionally avoid broad, vague product surface area.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                  <h3 className="text-lg font-medium mb-2">Not just a chat UI</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    TP is an interface into a running system of specialists, not the product itself.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-medium mb-2">Not template fill-in automation</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Deliverables generate from live context and memory, not static form fields.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-medium mb-2">Not context-free agent tooling</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    We do not optimize for isolated one-off tasks disconnected from source systems.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-medium mb-2">Not uncontrolled automation</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    The model is supervised autonomy with versioning, review states, and explicit user control.
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-12">Who yarnnn is for</h2>

              <div className="space-y-6">
                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-2">Operators with recurring high-context work</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Founders, consultants, chiefs of staff, and team leads who repeatedly synthesize across tools.
                  </p>
                </div>

                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-2">Teams that run on multiple platforms</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    If your workflow spans Slack, Gmail, Notion, and Calendar, yarnnn turns that sprawl into coherent output.
                  </p>
                </div>

                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-2">People shifting from execution to supervision</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    If you want fewer repetitive drafting cycles and more high-quality approvals, yarnnn is built for that transition.
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Build your first specialist.
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Connect your stack, define one deliverable, and run the supervision loop.
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
