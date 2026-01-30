import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";

export const metadata: Metadata = {
  title: "How It Works",
  description: "Learn how Yarn keeps your clients separate and remembers everything.",
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
              How Yarn works
            </h1>
            <p className="max-w-2xl text-white/50 text-lg">
              Three things make Yarn different: separate projects,
              persistent memory, and proactive work.
            </p>
          </section>

          {/* The Three Differentiators */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <div className="space-y-24">
                {/* Differentiator 1: Separate Projects */}
                <div className="grid grid-cols-1 md:grid-cols-[120px_1fr] gap-6">
                  <div className="text-5xl font-light text-white/20">01</div>
                  <div>
                    <h3 className="text-xl font-medium mb-4">Every project stays separate</h3>
                    <p className="text-white/50 leading-relaxed mb-6">
                      Create a project for each client, initiative, or domain.
                      When you ask about Client A, you get only Client A context.
                      No mixing. No cross-contamination.
                    </p>
                    <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                      <p className="text-white/30 text-sm italic">
                        &quot;I have 5 consulting clients. Each one is a separate project.
                        When I switch between them, Yarn switches context automatically.
                        Never worried about mixing things up again.&quot;
                      </p>
                    </div>
                  </div>
                </div>

                {/* Differentiator 2: Persistent Memory */}
                <div className="grid grid-cols-1 md:grid-cols-[120px_1fr] gap-6">
                  <div className="text-5xl font-light text-white/20">02</div>
                  <div>
                    <h3 className="text-xl font-medium mb-4">Tell it once. It remembers forever.</h3>
                    <p className="text-white/50 leading-relaxed mb-6">
                      Chat naturally. Upload documents. Important context gets
                      extracted and stored automatically. The more you use Yarn,
                      the more it knows about your work.
                    </p>
                    <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                      <p className="text-white/30 text-sm italic">
                        &quot;I uploaded my proposal template once. Now Yarn references
                        it every time I&apos;m drafting a new proposal. &apos;Based on your
                        template from January...&apos; — I love seeing that.&quot;
                      </p>
                    </div>
                  </div>
                </div>

                {/* Differentiator 3: Proactive Work */}
                <div className="grid grid-cols-1 md:grid-cols-[120px_1fr] gap-6">
                  <div className="text-5xl font-light text-white/20">03</div>
                  <div>
                    <h3 className="text-xl font-medium mb-4">AI that works while you sleep</h3>
                    <p className="text-white/50 leading-relaxed mb-6">
                      Schedule recurring work: weekly reports, research digests,
                      content drafts. Yarn executes on your schedule—you don&apos;t
                      have to remember to ask.
                    </p>
                    <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                      <p className="text-white/30 text-sm italic">
                        &quot;Every Monday morning I wake up to a summary of what happened
                        with each client last week. I didn&apos;t ask for it—Yarn just delivers.&quot;
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* The Comparison */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">Yarn vs. other AI tools</h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                <div>
                  <h3 className="text-lg font-medium mb-4 text-white/40">ChatGPT / Claude</h3>
                  <ul className="space-y-3 text-white/40 text-sm">
                    <li>One big memory bucket (everything mixes)</li>
                    <li>Forgets after a few conversations</li>
                    <li>Only works when you prompt it</li>
                    <li>No way to see what informed answers</li>
                    <li>$20/month</li>
                  </ul>
                </div>

                <div>
                  <h3 className="text-lg font-medium mb-4">Yarn</h3>
                  <ul className="space-y-3 text-white/70 text-sm">
                    <li>Separate memory per project</li>
                    <li>Remembers forever</li>
                    <li>Works proactively on schedule</li>
                    <li>&quot;Based on your notes from...&quot;</li>
                    <li>$19/month (same price, actually remembers)</li>
                  </ul>
                </div>
              </div>
            </div>
          </section>

          {/* Quick Start */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">Getting started</h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div className="border border-white/10 rounded-2xl p-6">
                  <div className="text-sm text-white/30 mb-3 font-mono">Step 1</div>
                  <h3 className="text-base font-medium mb-2">Create a project</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Sign up and create your first project. Name it after a client,
                    initiative, or domain you&apos;re working on.
                  </p>
                </div>

                <div className="border border-white/10 rounded-2xl p-6">
                  <div className="text-sm text-white/30 mb-3 font-mono">Step 2</div>
                  <h3 className="text-base font-medium mb-2">Add context</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Chat naturally. Upload relevant documents.
                    Yarn builds memory automatically.
                  </p>
                </div>

                <div className="border border-white/10 rounded-2xl p-6">
                  <div className="text-sm text-white/30 mb-3 font-mono">Step 3</div>
                  <h3 className="text-base font-medium mb-2">See the difference</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Ask a question about your project. Watch Yarn pull
                    from exactly the right context. That&apos;s it.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Ready to try it?
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Start with one project. The free tier gives you
                1 project and 50 memories. See the difference.
              </p>
              <Link
                href="/auth/login"
                className="inline-block px-8 py-4 bg-white text-black text-lg font-medium rounded-full hover:bg-white/90 transition-colors"
              >
                Start for free
              </Link>
            </div>
          </section>
        </main>

        <LandingFooter inverted />
      </div>
    </div>
  );
}
