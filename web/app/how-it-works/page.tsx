import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";

export const metadata: Metadata = {
  title: "How It Works",
  description: "Learn how yarnnn helps you build context, schedule agents, and get work delivered.",
};

export default function HowItWorksPage() {
  return (
    <div className="relative min-h-screen flex flex-col bg-[#0a0a0a] text-white overflow-x-hidden">
      <GrainOverlay />
      <ShaderBackgroundDark />

      {/* Content layer */}
      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted />

        <main className="flex-1">
          {/* Hero */}
          <section className="max-w-4xl mx-auto px-6 py-24 md:py-32">
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-10 tracking-tight leading-[1.1]">
              How yarnnn works
            </h1>
            <p className="max-w-2xl text-white/50 text-lg">
              Build context once. Let agents handle recurring work.
              Focus on what actually needs you.
            </p>
          </section>

          {/* Step by Step */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">The workflow</h2>

              <div className="space-y-16">
                {/* Step 1 */}
                <div className="grid grid-cols-1 md:grid-cols-[120px_1fr] gap-6">
                  <div className="text-5xl font-light text-white/20">01</div>
                  <div>
                    <h3 className="text-xl font-medium mb-4">Create projects</h3>
                    <p className="text-white/50 leading-relaxed mb-4">
                      Each client, initiative, or domain gets its own context space.
                      Your thinking partner can also create projects as conversations evolve.
                    </p>
                    <p className="text-white/50 leading-relaxed">
                      Projects are boundaries. Client A never sees Client B. Switch between
                      contexts without cross-contamination.
                    </p>
                  </div>
                </div>

                {/* Step 2 */}
                <div className="grid grid-cols-1 md:grid-cols-[120px_1fr] gap-6">
                  <div className="text-5xl font-light text-white/20">02</div>
                  <div>
                    <h3 className="text-xl font-medium mb-4">Accumulate knowledge</h3>
                    <p className="text-white/50 leading-relaxed mb-4">
                      Chat naturally with your thinking partner. Upload documents.
                      Memories form automatically and stay with the project.
                    </p>
                    <p className="text-white/50 leading-relaxed">
                      No manual tagging required. Important context is extracted from
                      conversations and stored. The more you use it, the smarter it gets.
                    </p>
                  </div>
                </div>

                {/* Step 3 */}
                <div className="grid grid-cols-1 md:grid-cols-[120px_1fr] gap-6">
                  <div className="text-5xl font-light text-white/20">03</div>
                  <div>
                    <h3 className="text-xl font-medium mb-4">Schedule agents</h3>
                    <p className="text-white/50 leading-relaxed mb-4">
                      Set up recurring work: weekly reports, research digests, content drafts.
                      Agents run on your schedule, not when you remember to ask.
                    </p>
                    <p className="text-white/50 leading-relaxed">
                      Research, writing, analysis—each agent specialized for its task,
                      all reading from shared project context.
                    </p>
                  </div>
                </div>

                {/* Step 4 */}
                <div className="grid grid-cols-1 md:grid-cols-[120px_1fr] gap-6">
                  <div className="text-5xl font-light text-white/20">04</div>
                  <div>
                    <h3 className="text-xl font-medium mb-4">Work arrives</h3>
                    <p className="text-white/50 leading-relaxed mb-4">
                      Outputs delivered on schedule, grounded in your project context.
                      Not chat responses—actual deliverables.
                    </p>
                    <p className="text-white/50 leading-relaxed">
                      Every output traces back to source memories. See exactly what context
                      informed each report, draft, or summary. Full provenance.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Key Capabilities */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">Built for multi-project work</h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-3">Isolated project context</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Switch between clients without cross-contamination. Each project has its own
                    memories, agents, and outputs. Perfect for agencies and consultants.
                  </p>
                </div>

                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-3">Scheduled execution</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Not chat. Work that runs without you. Weekly summaries, daily digests,
                    research on cadence—delivered, not requested.
                  </p>
                </div>

                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-3">Multi-agent orchestration</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Research, writing, analysis—each agent specialized for its task,
                    all reading from shared project context.
                  </p>
                </div>

                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-3">Full provenance</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Every output traces back to source memories. Know exactly what context
                    informed each report, draft, or summary.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* The Difference */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">Push vs Pull</h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                <div>
                  <h3 className="text-lg font-medium mb-4 text-white/40">Traditional AI (Pull)</h3>
                  <ul className="space-y-3 text-white/40 text-sm">
                    <li>You ask, it responds</li>
                    <li>You forget, it waits</li>
                    <li>Context resets each conversation</li>
                    <li>Interactive prompting required</li>
                    <li>Work happens when you remember</li>
                  </ul>
                </div>

                <div>
                  <h3 className="text-lg font-medium mb-4">yarnnn (Push)</h3>
                  <ul className="space-y-3 text-white/70 text-sm">
                    <li>Work arrives on schedule</li>
                    <li>Agents run autonomously</li>
                    <li>Context accumulates over time</li>
                    <li>Scheduled execution beats prompting</li>
                    <li>Work happens on cadence</li>
                  </ul>
                </div>
              </div>
            </div>
          </section>

          {/* CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Ready to put AI to work?
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Start with one project. Build context. Schedule your first agent.
              </p>
              <Link
                href="/auth/login"
                className="inline-block px-8 py-4 bg-white text-black text-lg font-medium rounded-full hover:bg-white/90 transition-colors"
              >
                Get started
              </Link>
            </div>
          </section>
        </main>

        <LandingFooter inverted />
      </div>
    </div>
  );
}
