import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";

export const metadata: Metadata = {
  title: "About",
  description: "Learn how YARNNN helps your AI understand your world through persistent context.",
};

export default function AboutPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <LandingHeader />

      <main className="flex-1">
        {/* Hero */}
        <section className="max-w-4xl mx-auto px-6 py-24">
          <h1 className="text-4xl md:text-5xl font-bold mb-6">
            Context that compounds, not conversations that vanish.
          </h1>
          <p className="text-lg text-muted-foreground mb-6">
            In the age of AI, our greatest challenge isn&apos;t generating ideas—it&apos;s maintaining
            context. Every conversation with ChatGPT or Claude starts from zero. You&apos;re forced
            to re-explain your business, your goals, your constraints, over and over.
          </p>
          <p className="text-lg text-muted-foreground">
            YARNNN ends that cycle. It&apos;s a platform where your knowledge accumulates,
            and AI agents read from that knowledge to produce real work. Not chat—work outputs
            that understand your world because they&apos;ve read everything you&apos;ve built.
          </p>
        </section>

        {/* How It Works */}
        <section className="border-t border-border px-6 py-24">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-3xl font-bold mb-12">How It Works</h2>

            <div className="space-y-12">
              {/* Step 1 */}
              <div className="flex gap-6">
                <div className="flex-shrink-0 w-12 h-12 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold text-xl">
                  1
                </div>
                <div>
                  <h3 className="text-xl font-semibold mb-2">Build Your Context</h3>
                  <p className="text-muted-foreground">
                    Add knowledge blocks—text, insights, decisions. Upload documents that get
                    parsed into structured context. Everything lives in your project, growing
                    over time.
                  </p>
                </div>
              </div>

              {/* Step 2 */}
              <div className="flex gap-6">
                <div className="flex-shrink-0 w-12 h-12 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold text-xl">
                  2
                </div>
                <div>
                  <h3 className="text-xl font-semibold mb-2">Request Work</h3>
                  <p className="text-muted-foreground">
                    Create a work ticket: research a topic, draft content, generate a report.
                    Choose the agent type and describe what you need. The agent will read your
                    entire context before executing.
                  </p>
                </div>
              </div>

              {/* Step 3 */}
              <div className="flex gap-6">
                <div className="flex-shrink-0 w-12 h-12 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold text-xl">
                  3
                </div>
                <div>
                  <h3 className="text-xl font-semibold mb-2">Receive Outputs</h3>
                  <p className="text-muted-foreground">
                    Get deliverables that actually understand your business. Research summaries
                    that reference your goals. Content that matches your voice. Reports built
                    on your data. Every output traces back to source context.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Core Principles */}
        <section className="border-t border-border px-6 py-24 bg-muted/30">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-3xl font-bold mb-12">Core Principles</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="p-6 bg-background rounded-lg border border-border">
                <h3 className="text-lg font-semibold mb-2">Context Over Conversation</h3>
                <p className="text-muted-foreground text-sm">
                  Chat is ephemeral. Context is persistent. We optimize for accumulated knowledge,
                  not conversation length.
                </p>
              </div>

              <div className="p-6 bg-background rounded-lg border border-border">
                <h3 className="text-lg font-semibold mb-2">Work Outputs, Not Chat Responses</h3>
                <p className="text-muted-foreground text-sm">
                  Agents produce deliverables: reports, research, content. Structured outputs
                  you can use, not conversations you have to parse.
                </p>
              </div>

              <div className="p-6 bg-background rounded-lg border border-border">
                <h3 className="text-lg font-semibold mb-2">Provenance & Trust</h3>
                <p className="text-muted-foreground text-sm">
                  Every output traces back to source blocks. You always know what information
                  informed each deliverable.
                </p>
              </div>

              <div className="p-6 bg-background rounded-lg border border-border">
                <h3 className="text-lg font-semibold mb-2">Simple by Default</h3>
                <p className="text-muted-foreground text-sm">
                  No complex workflows unless you need them. Add context, request work, get output.
                  That&apos;s the core loop.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="border-t border-border px-6 py-16">
          <div className="max-w-4xl mx-auto text-center">
            <h2 className="text-2xl font-bold mb-4">
              Ready to build context that compounds?
            </h2>
            <p className="text-muted-foreground mb-8">
              Start accumulating knowledge today. Your AI agents will finally understand your world.
            </p>
            <Link
              href="/auth/login"
              className="inline-block px-8 py-3 bg-primary text-primary-foreground rounded-lg text-lg font-medium hover:bg-primary/90 transition-colors"
            >
              Get Started
            </Link>
          </div>
        </section>
      </main>

      <LandingFooter />
    </div>
  );
}
