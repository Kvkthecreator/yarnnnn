import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackground } from "@/components/landing/ShaderBackground";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { CustomCursor } from "@/components/landing/CustomCursor";

export default function LandingPage() {
  return (
    <main className="landing-page relative min-h-screen w-full overflow-x-hidden bg-[#0a0a0a] text-white">
      <CustomCursor />
      <GrainOverlay />
      <ShaderBackground />

      {/* Content layer */}
      <div className="relative z-10">
        <LandingHeader inverted />

        {/* Hero Section */}
        <section className="flex flex-col items-center justify-center px-6 py-32 md:py-44 min-h-[80vh]">
          <div className="max-w-4xl mx-auto text-center">
            <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-medium tracking-tight leading-[1.1] mb-8">
              Your AI team
              <br />
              runs on autopilot
            </h1>
            <p className="text-lg md:text-xl text-white/50 mb-12 max-w-xl mx-auto font-light">
              Build context. Schedule agents. Get work delivered.
            </p>
            <Link
              href="/auth/login"
              className="inline-block px-8 py-4 glass text-white text-lg font-medium hover:bg-white/20 transition-colors"
            >
              Start your first project
            </Link>
          </div>
        </section>

        {/* How It Works */}
        <section className="border-t border-white/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-16">
              How it works
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-16 gap-y-12">
              <div>
                <div className="text-sm text-white/30 mb-3 font-mono">01</div>
                <h3 className="text-lg font-medium mb-2">Create projects</h3>
                <p className="text-white/50 leading-relaxed text-sm">
                  Each client, initiative, or domain gets its own context space.
                  Your thinking partner can also create projects as conversations evolve.
                </p>
              </div>

              <div>
                <div className="text-sm text-white/30 mb-3 font-mono">02</div>
                <h3 className="text-lg font-medium mb-2">Accumulate knowledge</h3>
                <p className="text-white/50 leading-relaxed text-sm">
                  Chat naturally. Upload documents. Memories form automatically
                  and stay with the project. No manual tagging required.
                </p>
              </div>

              <div>
                <div className="text-sm text-white/30 mb-3 font-mono">03</div>
                <h3 className="text-lg font-medium mb-2">Schedule agents</h3>
                <p className="text-white/50 leading-relaxed text-sm">
                  Set up recurring work: weekly reports, research digests, content drafts.
                  Agents run on your schedule, not when you remember to ask.
                </p>
              </div>

              <div>
                <div className="text-sm text-white/30 mb-3 font-mono">04</div>
                <h3 className="text-lg font-medium mb-2">Work arrives</h3>
                <p className="text-white/50 leading-relaxed text-sm">
                  Outputs delivered on schedule, grounded in your project context.
                  See exactly what memories informed each deliverable.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Key Differentiators */}
        <section className="border-t border-white/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-16">
              Built for multi-project work
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div className="glass-dark p-6">
                <h3 className="text-base font-medium mb-2">Isolated project context</h3>
                <p className="text-white/50 text-sm leading-relaxed">
                  Switch between clients without cross-contamination. Each project has its own
                  memories, agents, and outputs.
                </p>
              </div>

              <div className="glass-dark p-6">
                <h3 className="text-base font-medium mb-2">Scheduled execution</h3>
                <p className="text-white/50 text-sm leading-relaxed">
                  Not chat. Work that runs without you. Weekly summaries, daily digests,
                  research on cadence—delivered, not requested.
                </p>
              </div>

              <div className="glass-dark p-6">
                <h3 className="text-base font-medium mb-2">Multi-agent orchestration</h3>
                <p className="text-white/50 text-sm leading-relaxed">
                  Research, writing, analysis—each agent specialized for its task,
                  all reading from shared project context.
                </p>
              </div>

              <div className="glass-dark p-6">
                <h3 className="text-base font-medium mb-2">Full provenance</h3>
                <p className="text-white/50 text-sm leading-relaxed">
                  Every output traces back to source memories. Know exactly what context
                  informed each report, draft, or summary.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="border-t border-white/10 px-6 py-24 md:py-32">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-2xl md:text-3xl font-medium mb-6">
              Stop driving every conversation
            </h2>
            <p className="text-white/50 mb-10 max-w-lg mx-auto">
              Build the context once. Let agents do the recurring work.
              Focus on what actually needs you.
            </p>
            <Link
              href="/auth/login"
              className="inline-block px-8 py-4 glass text-white text-lg font-medium hover:bg-white/20 transition-colors"
            >
              Start your first project
            </Link>
          </div>
        </section>

        <LandingFooter inverted />
      </div>
    </main>
  );
}
