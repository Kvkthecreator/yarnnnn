import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";

export const metadata: Metadata = {
  title: "About",
  description: "yarnnn writes the recurring things you send—status reports, investor updates, client briefs—so you can just review and approve.",
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

          {/* The Idea */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">The idea</h2>

              <div className="space-y-12">
                <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">The context is already there</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      Your Slack channels have the updates. Your inbox has the client threads.
                      Your Notion has the project notes. The raw material for your weekly report?
                      It already exists.
                    </p>
                    <p className="text-white/30 text-sm">
                      You&apos;re just reassembling it into a different shape.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">It follows a pattern</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      Status reports look roughly the same every week. Investor updates follow
                      a format. Client briefs have a structure. The content changes, but the
                      shape stays familiar.
                    </p>
                    <p className="text-white/30 text-sm">
                      Patterns are learnable. That&apos;s what yarnnn does.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Your time is for judgment calls</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      Should you mention the delayed timeline? Is this the right level of detail?
                      Does this sound like you? Those are the decisions that matter.
                      The drafting is just setup.
                    </p>
                    <p className="text-white/30 text-sm">
                      yarnnn handles the setup. You make the calls.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* How It's Different */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">How it&apos;s different</h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                <div>
                  <h3 className="text-lg font-medium mb-3">It connects to your tools</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    yarnnn links to Slack, Gmail, and Notion—wherever your work lives.
                    When it&apos;s time to draft, it pulls fresh context automatically.
                    No copy-pasting, no manual updates.
                  </p>
                  <p className="text-white/30 text-xs mt-3">
                    Technical: OAuth connections with scoped access. Your credentials are never stored.
                  </p>
                </div>

                <div>
                  <h3 className="text-lg font-medium mb-3">It learns from your edits</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Every time you tweak a draft and approve it, yarnnn picks up on what
                    you changed. Structure preferences. Tone. Which details matter.
                    The tenth draft needs fewer edits than the first.
                  </p>
                  <p className="text-white/30 text-xs mt-3">
                    Technical: Your edits become training signal—implicit feedback that shapes future drafts.
                  </p>
                </div>

                <div>
                  <h3 className="text-lg font-medium mb-3">It runs on a schedule</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Set it up once—every Monday, first of the month, whatever cadence you need.
                    yarnnn drafts it when the time comes and pings you when it&apos;s ready.
                    You just review and approve.
                  </p>
                  <p className="text-white/30 text-xs mt-3">
                    Technical: Scheduled production with delta context extraction—only pulling what&apos;s new since last time.
                  </p>
                </div>

                <div>
                  <h3 className="text-lg font-medium mb-3">It&apos;s always up to date</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Because yarnnn pulls from your tools every time, the context is fresh.
                    Not stale. Not based on what you pasted last month.
                    What happened this week is what goes in this week&apos;s draft.
                  </p>
                  <p className="text-white/30 text-xs mt-3">
                    Technical: Real-time context fetch at execution, not cached from initial setup.
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

          {/* What It's Not */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">What it&apos;s not</h2>
              <p className="text-white/50 mb-12 max-w-xl">
                yarnnn does one thing well. Here&apos;s what it doesn&apos;t try to be.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="text-white/50 text-sm">
                  <span className="text-white/30">Not a chatbot.</span> You don&apos;t prompt it
                  with questions. You set up deliverables and review drafts.
                </div>
                <div className="text-white/50 text-sm">
                  <span className="text-white/30">Not a writing app.</span> You&apos;re not typing
                  in yarnnn. You&apos;re reviewing what it wrote.
                </div>
                <div className="text-white/50 text-sm">
                  <span className="text-white/30">Not a template tool.</span> It doesn&apos;t fill
                  in blanks. It synthesizes fresh content from current context.
                </div>
                <div className="text-white/50 text-sm">
                  <span className="text-white/30">Not a generic AI.</span> It&apos;s specifically
                  for recurring deliverables that pull from your existing tools.
                </div>
              </div>
            </div>
          </section>

          {/* CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Ready to spend less time on updates?
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Connect your tools. Set up your first deliverable. See what yarnnn drafts.
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
