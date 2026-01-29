import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col bg-foreground text-background">
      <LandingHeader inverted />

      {/* Hero Section */}
      <section className="flex-1 flex flex-col items-center justify-center px-6 py-32 md:py-40">
        <div className="max-w-5xl mx-auto text-center">
          <h1 className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tighter leading-[0.9] mb-8">
            Your AI team
            <br />
            runs on autopilot
          </h1>
          <p className="text-xl md:text-2xl text-background/60 mb-12 max-w-2xl mx-auto font-light">
            Build context. Schedule agents. Get work delivered.
          </p>
          <Link
            href="/auth/login"
            className="inline-block px-8 py-4 bg-background text-foreground text-lg font-medium hover:bg-background/90 transition-colors"
          >
            Start your first project
          </Link>
        </div>
      </section>

      {/* How It Works */}
      <section className="border-t border-background/10 px-6 py-24 md:py-32">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold mb-16 tracking-tight">
            How it works
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-16 gap-y-12">
            <div>
              <div className="text-sm text-background/40 mb-2 font-mono">01</div>
              <h3 className="text-xl font-semibold mb-3">Create projects</h3>
              <p className="text-background/60 leading-relaxed">
                Each client, initiative, or domain gets its own context space.
                Your thinking partner can also create projects as conversations evolve.
              </p>
            </div>

            <div>
              <div className="text-sm text-background/40 mb-2 font-mono">02</div>
              <h3 className="text-xl font-semibold mb-3">Accumulate knowledge</h3>
              <p className="text-background/60 leading-relaxed">
                Chat naturally. Upload documents. Memories form automatically
                and stay with the project. No manual tagging required.
              </p>
            </div>

            <div>
              <div className="text-sm text-background/40 mb-2 font-mono">03</div>
              <h3 className="text-xl font-semibold mb-3">Schedule agents</h3>
              <p className="text-background/60 leading-relaxed">
                Set up recurring work: weekly reports, research digests, content drafts.
                Agents run on your schedule, not when you remember to ask.
              </p>
            </div>

            <div>
              <div className="text-sm text-background/40 mb-2 font-mono">04</div>
              <h3 className="text-xl font-semibold mb-3">Work arrives</h3>
              <p className="text-background/60 leading-relaxed">
                Outputs delivered on schedule, grounded in your project context.
                See exactly what memories informed each deliverable.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Key Differentiators */}
      <section className="border-t border-background/10 px-6 py-24 md:py-32">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold mb-16 tracking-tight">
            Built for multi-project work
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-8">
            <div className="border border-background/10 p-6">
              <h3 className="text-lg font-semibold mb-2">Isolated project context</h3>
              <p className="text-background/60 text-sm leading-relaxed">
                Switch between clients without cross-contamination. Each project has its own
                memories, agents, and outputs.
              </p>
            </div>

            <div className="border border-background/10 p-6">
              <h3 className="text-lg font-semibold mb-2">Scheduled execution</h3>
              <p className="text-background/60 text-sm leading-relaxed">
                Not chat. Work that runs without you. Weekly summaries, daily digests,
                research on cadence—delivered, not requested.
              </p>
            </div>

            <div className="border border-background/10 p-6">
              <h3 className="text-lg font-semibold mb-2">Multi-agent orchestration</h3>
              <p className="text-background/60 text-sm leading-relaxed">
                Research, writing, analysis—each agent specialized for its task,
                all reading from shared project context.
              </p>
            </div>

            <div className="border border-background/10 p-6">
              <h3 className="text-lg font-semibold mb-2">Full provenance</h3>
              <p className="text-background/60 text-sm leading-relaxed">
                Every output traces back to source memories. Know exactly what context
                informed each report, draft, or summary.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="border-t border-background/10 px-6 py-24 md:py-32">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-6 tracking-tight">
            Stop driving every conversation
          </h2>
          <p className="text-lg text-background/60 mb-10 max-w-xl mx-auto">
            Build the context once. Let agents do the recurring work.
            Focus on what actually needs you.
          </p>
          <Link
            href="/auth/login"
            className="inline-block px-8 py-4 bg-background text-foreground text-lg font-medium hover:bg-background/90 transition-colors"
          >
            Start your first project
          </Link>
        </div>
      </section>

      <LandingFooter inverted />
    </div>
  );
}
