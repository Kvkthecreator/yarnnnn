import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";

export const metadata: Metadata = {
  title: "About",
  description: "yarnnn is a supervision layer between your work platforms and your recurring outputs. Connect, configure, approve.",
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
              A supervision layer
              <br />
              <span className="text-white/50">for recurring work.</span>
            </h1>
            <div className="max-w-2xl space-y-6 text-white/50">
              <p>
                Your work happens in Slack, Gmail, and Notion. Your deliverables go to
                clients, investors, and teams. The space between is filled with manual labor—
                reading, summarizing, reformatting. Every week.
              </p>
              <p>
                What if you could connect your platforms once, configure what you need to produce,
                and just... approve?
              </p>
              <p className="text-white font-medium">
                That&apos;s what we built yarnnn to do.
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
                    <h3 className="text-lg font-medium text-white">Your platforms hold the signal</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      The Slack threads, email chains, and Notion docs you accumulate every week—
                      that&apos;s the raw material for your deliverables. You just have to extract it.
                      Again. And again.
                    </p>
                    <p className="text-white/30 text-sm">
                      The context is already there. It just needs to be synthesized.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Gathering is worker-level labor</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      Reading through channels. Summarizing threads. Reformatting for different audiences.
                      This is work that doesn&apos;t require your judgment—just your time.
                    </p>
                    <p className="text-white/30 text-sm">
                      You should be supervising, not gathering.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6">
                  <div>
                    <h3 className="text-lg font-medium text-white">Approval is supervision</h3>
                  </div>
                  <div className="text-white/50">
                    <p className="mb-4">
                      When you review a draft and approve it, you&apos;re exercising judgment.
                      That&apos;s high-value work. The synthesis that preceded it? That should be automatic.
                    </p>
                    <p className="text-white/30 text-sm">
                      Connect once. Configure once. Approve repeatedly.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* What Makes yarnnn Different */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">What makes yarnnn different</h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                <div>
                  <h3 className="text-lg font-medium mb-3">Platforms, not prompts</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    yarnnn connects to where your work happens. You don&apos;t describe what you want—
                    you point to where the context lives. Slack channels. Gmail threads. Notion docs.
                    yarnnn pulls fresh context every cycle.
                  </p>
                </div>

                <div>
                  <h3 className="text-lg font-medium mb-3">Synthesis, not templates</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Every draft is built from current context. Not a template filled in.
                    Not a prompt re-run. The content changes because your platforms changed.
                    The structure stays consistent because yarnnn learned what works.
                  </p>
                </div>

                <div>
                  <h3 className="text-lg font-medium mb-3">Approval, not editing</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    The goal is light-touch review. Not heavy rewriting. Every approval teaches
                    yarnnn what you want. Over time, the drafts get closer. Your edits get smaller.
                    Approval becomes routine.
                  </p>
                </div>

                <div>
                  <h3 className="text-lg font-medium mb-3">Learning that compounds</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    yarnnn learns what to extract. What structure works. What tone fits.
                    Which sources matter. Every approval is a signal. The 10th draft is better
                    than the 1st because yarnnn has learned from 9 approvals.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* The Supervision Model */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">The supervision model</h2>

              <div className="border border-white/10 rounded-2xl p-8 mb-12">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div>
                    <div className="text-white/30 text-xs uppercase tracking-wider mb-2">Traditional AI</div>
                    <h3 className="text-lg font-medium mb-3">You operate, AI assists</h3>
                    <p className="text-white/50 text-sm">
                      You gather context. You write prompts. You edit outputs heavily.
                      AI is a tool you wield. The work is still yours.
                    </p>
                  </div>
                  <div>
                    <div className="text-white/30 text-xs uppercase tracking-wider mb-2">yarnnn</div>
                    <h3 className="text-lg font-medium mb-3">AI operates, you supervise</h3>
                    <p className="text-white/50 text-sm">
                      yarnnn gathers context. yarnnn synthesizes drafts. You review and approve.
                      You&apos;re the supervisor. The work is delegated.
                    </p>
                  </div>
                </div>
              </div>

              <p className="text-white/50 text-center max-w-xl mx-auto">
                This isn&apos;t about AI getting smarter. It&apos;s about changing the relationship.
                You decide what matters. You check that it&apos;s right. You give the go-ahead.
                That&apos;s supervision.
              </p>
            </div>
          </section>

          {/* Who yarnnn Is For */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">Who yarnnn is for</h2>

              <div className="space-y-6">
                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-2">Professionals with recurring deliverables</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Weekly status reports. Monthly investor updates. Client briefs.
                    If you produce it regularly and your platforms hold the context,
                    yarnnn can supervise it.
                  </p>
                </div>

                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-2">People who work across platforms</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Slack for team communication. Gmail for clients. Notion for documentation.
                    The more scattered your work, the more valuable automatic synthesis becomes.
                  </p>
                </div>

                <div className="border border-white/10 rounded-2xl p-6">
                  <h3 className="text-base font-medium mb-2">Anyone tired of manual gathering</h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    If you spend hours every week reading through channels, summarizing threads,
                    and reformatting content—that&apos;s time yarnnn can give back to you.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* What yarnnn Is Not */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">What yarnnn is not</h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="text-white/50 text-sm">
                  <span className="text-white/30">Not a chat assistant.</span> You&apos;re not prompting.
                  You&apos;re configuring scope and approving outputs.
                </div>
                <div className="text-white/50 text-sm">
                  <span className="text-white/30">Not a writing tool.</span> You&apos;re not drafting.
                  You&apos;re reviewing drafts yarnnn produces.
                </div>
                <div className="text-white/50 text-sm">
                  <span className="text-white/30">Not a template system.</span> It doesn&apos;t repeat.
                  It synthesizes fresh context every cycle.
                </div>
                <div className="text-white/50 text-sm">
                  <span className="text-white/30">Not a document editor.</span> The draft is the output.
                  Not a workspace for you to write in.
                </div>
              </div>
            </div>
          </section>

          {/* CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Ready to stop gathering?
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Connect your platforms. Configure your first deliverable. Start supervising.
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
