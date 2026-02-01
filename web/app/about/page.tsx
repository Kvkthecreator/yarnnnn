import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";

export const metadata: Metadata = {
  title: "About",
  description: "Yarn is AI for recurring work that learns from your edits and improves over time.",
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
              AI that gets better
              <br />
              <span className="text-white/50">the more you use it.</span>
            </h1>
            <div className="max-w-2xl space-y-6 text-white/50">
              <p>
                You produce the same types of work over and over. Weekly client updates.
                Monthly investor reports. Research digests every Friday. It follows a pattern—
                but every time you use AI, you start from scratch.
              </p>
              <p>
                What if your AI learned from every correction you made? What if your
                10th delivery was measurably better than your 1st?
              </p>
              <p className="text-white font-medium">
                That&apos;s what we built Yarn to do.
              </p>
            </div>
          </section>

          {/* The Insight */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">The insight</h2>

              <div className="space-y-12">
                <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Most AI forgets</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      You fix the same issues every time. &quot;Make it shorter.&quot;
                      &quot;Don&apos;t include the revenue numbers.&quot; &quot;Start with the key takeaway.&quot;
                      And next week, you&apos;re saying it all again.
                    </p>
                    <p className="text-white/30 text-sm">
                      ChatGPT, Claude, Gemini—they all reset. Your corrections evaporate.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Your edits are gold</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      When you change &quot;We achieved strong results&quot; to &quot;Revenue grew 23%,&quot;
                      that&apos;s not just a one-time fix. It&apos;s a signal about what you value:
                      specificity over vagueness, numbers over adjectives.
                    </p>
                    <p className="text-white/30 text-sm">
                      Yarn stores these corrections. Categorizes them. Applies them next time.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Learning compounds</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      After 10 versions, Yarn knows your preferences. Your format.
                      Your tone. The metrics you always include. The phrases you always cut.
                    </p>
                    <p className="text-white/30 text-sm">
                      The quality score shows it: draft quality improves over time.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* What Makes Yarn Different */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">What makes Yarn different</h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                <div>
                  <h3 className="text-lg font-medium mb-3">Deliverables, not chats</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Yarn isn&apos;t another chat interface. It&apos;s built around recurring work—
                    things you produce regularly that follow a pattern. Set it up once,
                    review the drafts, approve when ready.
                  </p>
                </div>

                <div>
                  <h3 className="text-lg font-medium mb-3">A feedback loop that works</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    When you edit a draft, Yarn doesn&apos;t just save the final version.
                    It analyzes what you changed, categorizes the type of edit, and uses
                    that to improve future drafts.
                  </p>
                </div>

                <div>
                  <h3 className="text-lg font-medium mb-3">Quality you can measure</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    See a quality trend for each deliverable. Track how close each draft
                    gets to your final version. Watch the number go up over time.
                    That&apos;s Yarn working.
                  </p>
                </div>

                <div>
                  <h3 className="text-lg font-medium mb-3">Production on schedule</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Set a schedule: every Monday, first of the month, bi-weekly Fridays.
                    Yarn produces a draft and notifies you. You review, refine, approve.
                    Done.
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
                  <h3 className="text-base font-medium mb-2">Consultants with recurring client work</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Weekly status reports for multiple clients. Each one learns your
                    format, your recipient&apos;s preferences, the metrics they care about.
                  </p>
                </div>

                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-2">Founders writing investor updates</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Monthly updates that get better over time. Same structure,
                    continually refined to match what your investors actually want to see.
                  </p>
                </div>

                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-2">Anyone with patterned work</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    If you produce something regularly that follows a pattern,
                    Yarn can learn it. Research digests. Team standups. Newsletter drafts.
                    The format is yours—Yarn just gets better at producing it.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Ready to see the difference?
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Start with one deliverable. Watch it improve.
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
