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
    <div className="min-h-screen flex flex-col bg-[#0a0a0a] text-white">
      <LandingHeader inverted />

      <main className="flex-1">
        {/* Hero */}
        <section className="max-w-4xl mx-auto px-6 py-24 md:py-32">
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-10 tracking-tight leading-[1.1]">
            AI is interactive.
            <br />
            Work is not.
          </h1>
          <div className="max-w-2xl space-y-6 text-white/50">
            <p>
              Every AI tool today is pull-based. You ask, it responds. You forget, it waits.
              Even with memory, you&apos;re still the one driving every conversation.
            </p>
            <p>
              But real work doesn&apos;t wait for prompts. Reports are due weekly. Research needs
              to happen continuously. Content has a cadence. The best employees don&apos;t wait
              to be asked—they know the context, they know the schedule, they deliver.
            </p>
            <p className="text-white font-medium">
              yarnnn is AI that works like that.
            </p>
          </div>
        </section>

        {/* The Model */}
        <section className="border-t border-white/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-16">The model</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
              <div>
                <h3 className="text-lg font-medium mb-3">Projects hold context</h3>
                <p className="text-white/50 text-sm leading-relaxed">
                  Each project is an isolated context space. Client work, product initiatives,
                  research domains—each gets its own memories, agents, and outputs.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-medium mb-3">Conversations become memories</h3>
                <p className="text-white/50 text-sm leading-relaxed">
                  When you chat with your thinking partner, important context is automatically
                  extracted and stored. No manual entry. No tagging.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-medium mb-3">Agents run on schedule</h3>
                <p className="text-white/50 text-sm leading-relaxed">
                  Set up recurring work: weekly summaries, research digests, content drafts.
                  Agents execute on schedule, delivering outputs without you asking.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-medium mb-3">Outputs trace back to sources</h3>
                <p className="text-white/50 text-sm leading-relaxed">
                  Every deliverable shows exactly what memories informed it. Full provenance.
                  You trust the output because you see the input.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Who It's For */}
        <section className="border-t border-white/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-16">Who it&apos;s for</h2>

            <div className="space-y-6">
              <div className="border border-white/10 p-6">
                <h3 className="text-base font-medium mb-2">Agencies and consultants</h3>
                <p className="text-white/50 text-sm leading-relaxed">
                  Managing multiple clients means constant context-switching. Each client
                  gets a project with isolated context. Weekly status reports write themselves.
                </p>
              </div>

              <div className="border border-white/10 p-6">
                <h3 className="text-base font-medium mb-2">Solo operators and founders</h3>
                <p className="text-white/50 text-sm leading-relaxed">
                  You&apos;re running five things at once. Product, marketing, sales, ops.
                  Each is a project. Each accumulates context over months.
                </p>
              </div>

              <div className="border border-white/10 p-6">
                <h3 className="text-base font-medium mb-2">Research and analysis roles</h3>
                <p className="text-white/50 text-sm leading-relaxed">
                  Tracking competitors, markets, trends is tedious recurring work.
                  Research agents run on schedule, accumulating findings into project memory.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Principles */}
        <section className="border-t border-white/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-16">Principles</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
              <div>
                <h3 className="text-base font-medium mb-2">Push over pull</h3>
                <p className="text-white/50 text-sm">
                  Work arrives, not waits. Scheduled execution beats interactive prompting.
                </p>
              </div>

              <div>
                <h3 className="text-base font-medium mb-2">Context over conversation</h3>
                <p className="text-white/50 text-sm">
                  Chat is ephemeral. Memories persist. We optimize for accumulated knowledge.
                </p>
              </div>

              <div>
                <h3 className="text-base font-medium mb-2">Isolation over mixing</h3>
                <p className="text-white/50 text-sm">
                  Projects are boundaries. Client A never sees Client B.
                </p>
              </div>

              <div>
                <h3 className="text-base font-medium mb-2">Transparency over magic</h3>
                <p className="text-white/50 text-sm">
                  Every output traces to sources. See what the AI saw.
                </p>
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
              className="inline-block px-8 py-4 bg-white text-black text-lg font-medium hover:bg-white/90 transition-colors"
            >
              Get started
            </Link>
          </div>
        </section>
      </main>

      <LandingFooter inverted />
    </div>
  );
}
