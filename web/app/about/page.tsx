import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";

export const metadata: Metadata = {
  title: "About",
  description: "AI agents that work on schedule, grounded in your project context.",
};

export default function AboutPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <LandingHeader />

      <main className="flex-1">
        {/* Hero */}
        <section className="max-w-3xl mx-auto px-6 py-24">
          <h1 className="text-4xl md:text-5xl font-bold mb-8 tracking-tight">
            AI is interactive.<br />
            Work is not.
          </h1>
          <p className="text-lg text-muted-foreground mb-6">
            Every AI tool today is pull-based. You ask, it responds. You forget, it waits.
            Even with memory, you&apos;re still the one driving every conversation.
          </p>
          <p className="text-lg text-muted-foreground mb-6">
            But real work doesn&apos;t wait for prompts. Reports are due weekly. Research needs
            to happen continuously. Content has a cadence. The best employees don&apos;t wait
            to be asked—they know the context, they know the schedule, they deliver.
          </p>
          <p className="text-lg text-foreground font-medium">
            yarnnn is AI that works like that.
          </p>
        </section>

        {/* The Model */}
        <section className="border-t border-border px-6 py-24">
          <div className="max-w-3xl mx-auto">
            <h2 className="text-3xl font-bold mb-12">The model</h2>

            <div className="space-y-8">
              <div>
                <h3 className="text-xl font-semibold mb-3">Projects hold context</h3>
                <p className="text-muted-foreground">
                  Each project is an isolated context space. Client work, product initiatives,
                  research domains—each gets its own memories, its own agents, its own outputs.
                  Switch between them without bleeding context.
                </p>
              </div>

              <div>
                <h3 className="text-xl font-semibold mb-3">Conversations become memories</h3>
                <p className="text-muted-foreground">
                  When you chat with your thinking partner, important context is automatically
                  extracted and stored. No manual entry. No tagging. Memories accumulate
                  naturally from the work you&apos;re already doing.
                </p>
              </div>

              <div>
                <h3 className="text-xl font-semibold mb-3">Agents run on schedule</h3>
                <p className="text-muted-foreground">
                  Set up recurring work: weekly project summaries, daily research digests,
                  content drafts on cadence. Agents execute on schedule, pulling from
                  accumulated context, delivering outputs without you asking.
                </p>
              </div>

              <div>
                <h3 className="text-xl font-semibold mb-3">Outputs trace back to sources</h3>
                <p className="text-muted-foreground">
                  Every deliverable shows exactly what memories informed it. Full provenance.
                  You can trust the output because you can see the input.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Who It's For */}
        <section className="border-t border-border px-6 py-24 bg-muted/30">
          <div className="max-w-3xl mx-auto">
            <h2 className="text-3xl font-bold mb-12">Who it&apos;s for</h2>

            <div className="space-y-8">
              <div className="p-6 bg-background rounded-lg border border-border">
                <h3 className="text-lg font-semibold mb-2">Agencies and consultants</h3>
                <p className="text-muted-foreground">
                  Managing multiple clients means constant context-switching. Each client
                  gets a project with isolated context. Set up weekly status reports
                  that write themselves. Stop repeating the same work across accounts.
                </p>
              </div>

              <div className="p-6 bg-background rounded-lg border border-border">
                <h3 className="text-lg font-semibold mb-2">Solo operators and founders</h3>
                <p className="text-muted-foreground">
                  You&apos;re running five things at once. Product, marketing, sales, ops.
                  Each is a project. Each accumulates context over months. Your AI
                  understands your business better than a new hire ever could.
                </p>
              </div>

              <div className="p-6 bg-background rounded-lg border border-border">
                <h3 className="text-lg font-semibold mb-2">Research and analysis roles</h3>
                <p className="text-muted-foreground">
                  Tracking competitors, markets, trends is tedious recurring work.
                  Research agents run on schedule, accumulating findings into project
                  memory. Insights compound instead of getting lost in one-off chats.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Principles */}
        <section className="border-t border-border px-6 py-24">
          <div className="max-w-3xl mx-auto">
            <h2 className="text-3xl font-bold mb-12">Principles</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div>
                <h3 className="text-lg font-semibold mb-2">Push over pull</h3>
                <p className="text-muted-foreground text-sm">
                  Work should arrive, not wait to be requested.
                  Scheduled execution beats interactive prompting.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-semibold mb-2">Context over conversation</h3>
                <p className="text-muted-foreground text-sm">
                  Chat is ephemeral. Memories persist.
                  We optimize for accumulated knowledge.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-semibold mb-2">Isolation over mixing</h3>
                <p className="text-muted-foreground text-sm">
                  Projects are boundaries. Client A never sees Client B.
                  Clean separation enables trust.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-semibold mb-2">Transparency over magic</h3>
                <p className="text-muted-foreground text-sm">
                  Every output traces to sources. See what the AI saw.
                  Provenance builds confidence.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="border-t border-border px-6 py-20">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-2xl font-bold mb-4">
              Ready to put AI to work?
            </h2>
            <p className="text-muted-foreground mb-8">
              Start with one project. Build context. Schedule your first agent.
              See what happens when AI actually runs.
            </p>
            <Link
              href="/auth/login"
              className="inline-block px-8 py-4 bg-primary text-primary-foreground rounded-lg text-lg font-medium hover:bg-primary/90 transition-colors"
            >
              Get started
            </Link>
          </div>
        </section>
      </main>

      <LandingFooter />
    </div>
  );
}
