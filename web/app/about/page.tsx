import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";

export const metadata: Metadata = {
  title: "About",
  description: "yarnnn is a supervision layer between your work platforms and your recurring deliverables. Connect, configure, approve.",
};

export default function AboutPage() {
  return (
    <div className="relative min-h-screen flex flex-col bg-[#0f1419] text-white overflow-x-hidden">
      <GrainOverlay variant="dark" />
      <ShaderBackgroundDark />

      {/* Content layer */}
      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted />

        <main className="flex-1">
          {/* Hero */}
          <section className="max-w-4xl mx-auto px-6 py-24 md:py-32">
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-10 tracking-tight leading-[1.1]">
              We built yarnnn because
              <br />
              <span className="text-white/50">writing updates is a chore.</span>
            </h1>
            <div className="max-w-2xl space-y-6 text-white/50">
              <p>
                You know the feeling. It&apos;s Monday morning and you need to send a status
                report. All the information is there—in Slack, in your inbox, in your notes.
                But you still have to pull it together, format it, and make it sound right.
              </p>
              <p>
                It&apos;s not hard. It&apos;s just... time. Time you could spend on actual work.
              </p>
              <p className="text-white font-medium">
                So we made yarnnn to do that part for you.
              </p>
            </div>
          </section>

          {/* The Philosophy */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">What we believe</h2>

              <div className="space-y-16">
                <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">You&apos;re a supervisor, not a writer</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      The information already exists in your tools. Synthesizing it into
                      a deliverable shouldn&apos;t require you to do the manual labor of reading,
                      copying, and reformatting.
                    </p>
                    <p className="text-white/30 text-sm">
                      Your job is to decide what matters and approve when it&apos;s right.
                      Not to reassemble the same information week after week.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">AI should remember</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      Most AI tools forget everything between sessions. Your corrections
                      evaporate. You explain the same preferences again and again.
                    </p>
                    <p className="text-white/30 text-sm">
                      yarnnn builds a persistent understanding of your work and your style.
                      Every approval makes the next draft better.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Platforms have the context</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      Your Slack channels, email threads, and Notion docs already contain
                      everything needed for your weekly report. The raw material is there.
                    </p>
                    <p className="text-white/30 text-sm">
                      yarnnn connects directly to where your work happens—so you never
                      have to paste, summarize, or manually update context again.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Recurring work should be automatic</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      If you owe someone something on a regular cadence—weekly, monthly,
                      quarterly—the system should produce it on schedule.
                    </p>
                    <p className="text-white/30 text-sm">
                      Set it up once. Review when ready. That&apos;s supervision.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* What yarnnn Is Not */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">What yarnnn is not</h2>
              <p className="text-white/50 mb-12 max-w-xl">
                yarnnn does one thing well. Here&apos;s what it doesn&apos;t try to be.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                  <h3 className="text-lg font-medium mb-2">Not a chatbot</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    You don&apos;t prompt yarnnn with endless questions.
                    You set up deliverables, and your Thinking Partner
                    produces them on schedule.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-medium mb-2">Not a writing app</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    You&apos;re not typing in yarnnn. You&apos;re reviewing
                    what it wrote. The draft is the output, not the workspace.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-medium mb-2">Not a template tool</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    yarnnn doesn&apos;t fill in blanks. It synthesizes fresh
                    content from current context, every time.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-medium mb-2">Not a generic AI</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    yarnnn is specifically for recurring deliverables that
                    pull from your existing work platforms. That&apos;s it.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Who It's For */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-12">Who it&apos;s for</h2>

              <div className="space-y-6">
                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-2">People who send recurring things</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Weekly status reports. Monthly investor updates. Client check-ins.
                    If you owe someone something on a regular cadence, yarnnn can help.
                  </p>
                </div>

                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-2">People whose work is spread across tools</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Slack for team chat. Gmail for clients. Notion for docs.
                    The more scattered the context, the more time yarnnn saves you.
                  </p>
                </div>

                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-2">People who&apos;d rather review than write</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Not everyone likes drafting. If you&apos;d rather skim, tweak, and approve
                    than stare at a blank page, yarnnn is built for you.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Ready to supervise instead of write?
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Connect your tools. Tell TP what you need.
                See your first draft in minutes.
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
