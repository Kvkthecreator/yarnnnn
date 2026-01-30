import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";

export const metadata: Metadata = {
  title: "About",
  description: "AI that actually knows your work. Never explain yourself twice.",
};

export default function AboutPage() {
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
              Your AI forgets everything.
              <br />
              <span className="text-white/50">That&apos;s the problem.</span>
            </h1>
            <div className="max-w-2xl space-y-6 text-white/50">
              <p>
                You&apos;ve explained your business model to ChatGPT fifty times.
                You&apos;ve watched it mix up Client A with Client B. You&apos;ve started
                from scratch in every conversation.
              </p>
              <p>
                AI is supposed to help. But how can it help if it doesn&apos;t
                remember anything? If it can&apos;t keep your clients straight?
                If it only works when you&apos;re actively asking questions?
              </p>
              <p className="text-white font-medium">
                We built Yarn to fix this.
              </p>
            </div>
          </section>

          {/* The Three Problems */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">The problems we solve</h2>

              <div className="space-y-12">
                <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Context Chaos</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      &quot;I asked ChatGPT to draft an email for my consulting client, and it
                      used details from a completely different project.&quot;
                    </p>
                    <p className="text-white/30 text-sm">
                      Yarn keeps every project in its own world. Client A never sees Client B.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Groundhog Day</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      &quot;I&apos;ve explained my business model to ChatGPT probably 50 times.
                      Every. Single. Time.&quot;
                    </p>
                    <p className="text-white/30 text-sm">
                      Tell Yarn once. Upload your docs once. It builds memory that grows over time.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Reactive Treadmill</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      &quot;I realized I forgot to follow up with a client for three weeks.
                      If only something had reminded me.&quot;
                    </p>
                    <p className="text-white/30 text-sm">
                      Yarn works while you sleep. Schedule work. Get proactive insights.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* How Yarn is Different */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">How Yarn is different</h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                <div>
                  <h3 className="text-lg font-medium mb-3">Projects keep context separate</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Each client, initiative, or domain gets its own isolated space.
                    Ask about Client A, get only Client A context. Always.
                  </p>
                </div>

                <div>
                  <h3 className="text-lg font-medium mb-3">Memory that actually persists</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Conversations become memories. Documents get understood.
                    The more you use it, the more it knows about your work.
                  </p>
                </div>

                <div>
                  <h3 className="text-lg font-medium mb-3">Work that happens without asking</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Schedule research. Get weekly digests. Set up recurring work.
                    Yarn delivers—you don&apos;t have to remember to prompt.
                  </p>
                </div>

                <div>
                  <h3 className="text-lg font-medium mb-3">Shows where answers come from</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Every output traces back to your context. &quot;Based on your notes from
                    January...&quot; You trust it because you see what it saw.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Who It's For */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">Who Yarn is for</h2>

              <div className="space-y-6">
                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-2">Consultants juggling clients</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Keep every client separate. Never mix up context again.
                    Each client is a project with its own memory.
                  </p>
                </div>

                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-2">Freelancers managing projects</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Context compounds over months. Never start from scratch.
                    Your AI knows every project&apos;s history.
                  </p>
                </div>

                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-2">Founders running everything</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Product, marketing, sales, ops—each gets its own AI that knows
                    the full history. Switch contexts without switching brains.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Ready for AI that actually knows you?
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Start with one project. See the difference.
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
