import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <LandingHeader />

      {/* Hero Section */}
      <section className="relative flex-1 flex flex-col items-center justify-center px-6 py-28 md:py-36 overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 hero-gradient" />

        <div className="relative max-w-4xl mx-auto text-center">
          <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight mb-6">
            <span className="text-gradient">Your AI team</span>
            <br />
            runs on autopilot
          </h1>
          <p className="text-xl md:text-2xl text-muted-foreground mb-10 max-w-2xl mx-auto">
            Build context. Schedule agents. Get work delivered.
          </p>
          <Link
            href="/auth/login"
            className="inline-block px-8 py-4 bg-primary text-primary-foreground rounded-full text-lg font-medium hover:bg-primary/90 transition-all glow-button"
          >
            Start your first project
          </Link>
        </div>
      </section>

      {/* How It Works */}
      <section className="border-t border-border px-6 py-28">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold mb-20 text-center">
            How it works
          </h2>

          <div className="space-y-20">
            {/* Step 1 */}
            <div className="flex flex-col md:flex-row gap-8 md:gap-16 items-start">
              <div className="step-number flex-shrink-0 w-14 h-14 rounded-full flex items-center justify-center font-bold text-xl">
                1
              </div>
              <div className="flex-1">
                <h3 className="text-2xl font-semibold mb-3">Create projects</h3>
                <p className="text-muted-foreground text-lg leading-relaxed">
                  Each client, initiative, or domain gets its own context space.
                  Your thinking partner can also create projects for you as conversations evolve.
                </p>
              </div>
            </div>

            {/* Step 2 */}
            <div className="flex flex-col md:flex-row gap-8 md:gap-16 items-start">
              <div className="step-number flex-shrink-0 w-14 h-14 rounded-full flex items-center justify-center font-bold text-xl">
                2
              </div>
              <div className="flex-1">
                <h3 className="text-2xl font-semibold mb-3">Accumulate knowledge</h3>
                <p className="text-muted-foreground text-lg leading-relaxed">
                  Chat naturally. Upload documents. Memories form automatically from your conversations
                  and stay with the project. No manual tagging or organization required.
                </p>
              </div>
            </div>

            {/* Step 3 */}
            <div className="flex flex-col md:flex-row gap-8 md:gap-16 items-start">
              <div className="step-number flex-shrink-0 w-14 h-14 rounded-full flex items-center justify-center font-bold text-xl">
                3
              </div>
              <div className="flex-1">
                <h3 className="text-2xl font-semibold mb-3">Schedule agents</h3>
                <p className="text-muted-foreground text-lg leading-relaxed">
                  Set up recurring work: weekly reports, research digests, content drafts.
                  Agents run on your schedule, not when you remember to ask.
                </p>
              </div>
            </div>

            {/* Step 4 */}
            <div className="flex flex-col md:flex-row gap-8 md:gap-16 items-start">
              <div className="step-number flex-shrink-0 w-14 h-14 rounded-full flex items-center justify-center font-bold text-xl">
                4
              </div>
              <div className="flex-1">
                <h3 className="text-2xl font-semibold mb-3">Work arrives</h3>
                <p className="text-muted-foreground text-lg leading-relaxed">
                  Outputs delivered on schedule, grounded in your project context.
                  See exactly what memories informed each deliverable.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Key Differentiators */}
      <section className="border-t border-border px-6 py-28 bg-muted/30">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold mb-16 text-center">
            Built for multi-project work
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="feature-card p-8 bg-background rounded-2xl border border-border">
              <h3 className="text-xl font-semibold mb-3">Isolated project context</h3>
              <p className="text-muted-foreground leading-relaxed">
                Switch between clients without cross-contamination. Each project has its own
                memories, its own agents, its own outputs.
              </p>
            </div>

            <div className="feature-card p-8 bg-background rounded-2xl border border-border">
              <h3 className="text-xl font-semibold mb-3">Scheduled execution</h3>
              <p className="text-muted-foreground leading-relaxed">
                Not chat. Work that runs without you. Weekly summaries, daily digests,
                research on cadence—delivered, not requested.
              </p>
            </div>

            <div className="feature-card p-8 bg-background rounded-2xl border border-border">
              <h3 className="text-xl font-semibold mb-3">Multi-agent orchestration</h3>
              <p className="text-muted-foreground leading-relaxed">
                Research, writing, analysis—each agent specialized for its task,
                all reading from shared project context.
              </p>
            </div>

            <div className="feature-card p-8 bg-background rounded-2xl border border-border">
              <h3 className="text-xl font-semibold mb-3">Full provenance</h3>
              <p className="text-muted-foreground leading-relaxed">
                Every output traces back to source memories. Know exactly what context
                informed each report, draft, or summary.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative border-t border-border px-6 py-28 overflow-hidden">
        <div className="absolute inset-0 hero-gradient rotate-180" />
        <div className="relative max-w-3xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-6">
            Stop driving every conversation
          </h2>
          <p className="text-lg text-muted-foreground mb-10 max-w-xl mx-auto">
            Build the context once. Let agents do the recurring work.
            Focus on what actually needs you.
          </p>
          <Link
            href="/auth/login"
            className="inline-block px-8 py-4 bg-primary text-primary-foreground rounded-full text-lg font-medium hover:bg-primary/90 transition-all glow-button"
          >
            Start your first project
          </Link>
        </div>
      </section>

      <LandingFooter />
    </div>
  );
}
