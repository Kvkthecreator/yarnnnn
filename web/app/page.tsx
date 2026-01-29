import Link from "next/link";
import Image from "next/image";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <LandingHeader />

      {/* Hero Section */}
      <section className="flex-1 flex flex-col items-center justify-center px-6 py-24 md:py-32">
        <div className="max-w-3xl mx-auto text-center">
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-6">
            Your AI team runs on autopilot
          </h1>
          <p className="text-xl md:text-2xl text-muted-foreground mb-8 max-w-2xl mx-auto">
            Build context. Schedule agents. Get work delivered.
          </p>
          <Link
            href="/auth/login"
            className="inline-block px-8 py-4 bg-primary text-primary-foreground rounded-lg text-lg font-medium hover:bg-primary/90 transition-colors"
          >
            Start your first project
          </Link>
        </div>
      </section>

      {/* How It Works */}
      <section className="border-t border-border px-6 py-24">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold mb-16 text-center">
            How it works
          </h2>

          <div className="space-y-16">
            {/* Step 1 */}
            <div className="flex flex-col md:flex-row gap-6 md:gap-12 items-start">
              <div className="flex-shrink-0 w-12 h-12 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold text-xl">
                1
              </div>
              <div>
                <h3 className="text-xl font-semibold mb-3">Create projects</h3>
                <p className="text-muted-foreground text-lg">
                  Each client, initiative, or domain gets its own context space.
                  Your thinking partner can also create projects for you as conversations evolve.
                </p>
              </div>
            </div>

            {/* Step 2 */}
            <div className="flex flex-col md:flex-row gap-6 md:gap-12 items-start">
              <div className="flex-shrink-0 w-12 h-12 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold text-xl">
                2
              </div>
              <div>
                <h3 className="text-xl font-semibold mb-3">Accumulate knowledge</h3>
                <p className="text-muted-foreground text-lg">
                  Chat naturally. Upload documents. Memories form automatically from your conversations
                  and stay with the project. No manual tagging or organization required.
                </p>
              </div>
            </div>

            {/* Step 3 */}
            <div className="flex flex-col md:flex-row gap-6 md:gap-12 items-start">
              <div className="flex-shrink-0 w-12 h-12 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold text-xl">
                3
              </div>
              <div>
                <h3 className="text-xl font-semibold mb-3">Schedule agents</h3>
                <p className="text-muted-foreground text-lg">
                  Set up recurring work: weekly reports, research digests, content drafts.
                  Agents run on your schedule, not when you remember to ask.
                </p>
              </div>
            </div>

            {/* Step 4 */}
            <div className="flex flex-col md:flex-row gap-6 md:gap-12 items-start">
              <div className="flex-shrink-0 w-12 h-12 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold text-xl">
                4
              </div>
              <div>
                <h3 className="text-xl font-semibold mb-3">Work arrives</h3>
                <p className="text-muted-foreground text-lg">
                  Outputs delivered on schedule, grounded in your project context.
                  See exactly what memories informed each deliverable.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Key Differentiators */}
      <section className="border-t border-border px-6 py-24 bg-muted/30">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold mb-16 text-center">
            Built for multi-project work
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-12">
            <div className="p-6 bg-background rounded-lg border border-border">
              <h3 className="text-lg font-semibold mb-3">Isolated project context</h3>
              <p className="text-muted-foreground">
                Switch between clients without cross-contamination. Each project has its own
                memories, its own agents, its own outputs.
              </p>
            </div>

            <div className="p-6 bg-background rounded-lg border border-border">
              <h3 className="text-lg font-semibold mb-3">Scheduled execution</h3>
              <p className="text-muted-foreground">
                Not chat. Work that runs without you. Weekly summaries, daily digests,
                research on cadence—delivered, not requested.
              </p>
            </div>

            <div className="p-6 bg-background rounded-lg border border-border">
              <h3 className="text-lg font-semibold mb-3">Multi-agent orchestration</h3>
              <p className="text-muted-foreground">
                Research, writing, analysis—each agent specialized for its task,
                all reading from shared project context.
              </p>
            </div>

            <div className="p-6 bg-background rounded-lg border border-border">
              <h3 className="text-lg font-semibold mb-3">Full provenance</h3>
              <p className="text-muted-foreground">
                Every output traces back to source memories. Know exactly what context
                informed each report, draft, or summary.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="border-t border-border px-6 py-20">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-2xl md:text-3xl font-bold mb-4">
            Stop driving every conversation
          </h2>
          <p className="text-lg text-muted-foreground mb-8 max-w-xl mx-auto">
            Build the context once. Let agents do the recurring work.
            Focus on what actually needs you.
          </p>
          <Link
            href="/auth/login"
            className="inline-block px-8 py-4 bg-primary text-primary-foreground rounded-lg text-lg font-medium hover:bg-primary/90 transition-colors"
          >
            Start your first project
          </Link>
        </div>
      </section>

      <LandingFooter />
    </div>
  );
}
