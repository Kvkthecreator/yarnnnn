import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";

export const metadata: Metadata = {
  title: "How It Works",
  description: "Connect your work platforms, configure your deliverables, approve the drafts. See how yarnnn turns where you work into what you deliver.",
};

export default function HowItWorksPage() {
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
              How yarnnn works
            </h1>
            <p className="max-w-2xl text-white/50 text-lg">
              yarnnn is a supervision layer between your work platforms and your recurring outputs.
              You connect, configure, and approve. yarnnn does the rest.
            </p>
          </section>

          {/* The Flow */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <div className="space-y-24">
                {/* Step 1: Connect */}
                <div className="grid grid-cols-1 md:grid-cols-[120px_1fr] gap-6">
                  <div className="text-5xl font-light text-white/20">01</div>
                  <div>
                    <h3 className="text-xl font-medium mb-4">Connect your platforms</h3>
                    <p className="text-white/50 leading-relaxed mb-6">
                      Link the tools where your work already happens. Slack, Gmail, Notion.
                      One-time OAuth sign-in. yarnnn can now see what you see.
                    </p>
                    <div className="border border-white/10 rounded-xl p-5 bg-white/5">
                      <div className="grid grid-cols-3 gap-4">
                        <div className="text-center">
                          <div className="text-2xl mb-2">💬</div>
                          <div className="text-white/70 text-sm">Slack</div>
                          <div className="text-white/30 text-xs">Channels, threads, DMs</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl mb-2">📧</div>
                          <div className="text-white/70 text-sm">Gmail</div>
                          <div className="text-white/30 text-xs">Inbox, threads, sent</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl mb-2">📝</div>
                          <div className="text-white/70 text-sm">Notion</div>
                          <div className="text-white/30 text-xs">Pages, databases</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Step 2: Configure */}
                <div className="grid grid-cols-1 md:grid-cols-[120px_1fr] gap-6">
                  <div className="text-5xl font-light text-white/20">02</div>
                  <div>
                    <h3 className="text-xl font-medium mb-4">Configure your deliverables</h3>
                    <p className="text-white/50 leading-relaxed mb-6">
                      Tell yarnnn what you need to produce. Who receives it. When it&apos;s due.
                      Then select which channels, threads, or docs should inform it.
                      This is scope configuration—you decide what matters.
                    </p>
                    <div className="border border-white/10 rounded-xl p-5 bg-white/5 space-y-4">
                      <div>
                        <div className="text-xs text-white/30 uppercase tracking-wider mb-1">Deliverable</div>
                        <div className="text-white/70">Weekly Status Report for Sarah</div>
                      </div>
                      <div>
                        <div className="text-xs text-white/30 uppercase tracking-wider mb-1">Schedule</div>
                        <div className="text-white/70">Every Monday at 9am</div>
                      </div>
                      <div>
                        <div className="text-xs text-white/30 uppercase tracking-wider mb-1">Context sources</div>
                        <div className="flex flex-wrap gap-2 mt-1">
                          <span className="px-2 py-1 bg-white/10 rounded text-white/70 text-xs">Slack #engineering</span>
                          <span className="px-2 py-1 bg-white/10 rounded text-white/70 text-xs">Slack #product</span>
                          <span className="px-2 py-1 bg-white/10 rounded text-white/70 text-xs">Last 7 days</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Step 3: Approve */}
                <div className="grid grid-cols-1 md:grid-cols-[120px_1fr] gap-6">
                  <div className="text-5xl font-light text-white/20">03</div>
                  <div>
                    <h3 className="text-xl font-medium mb-4">Review and approve</h3>
                    <p className="text-white/50 leading-relaxed mb-6">
                      On schedule, yarnnn pulls fresh context from your connected platforms,
                      synthesizes a draft, and notifies you. Review it. Make light edits if needed.
                      Approve when ready.
                    </p>
                    <div className="border border-white/10 rounded-xl p-5 bg-white/5 space-y-3">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-white/50">Weekly Status Report — Draft ready</span>
                        <span className="px-2 py-1 bg-amber-500/20 text-amber-400 rounded text-xs">Review</span>
                      </div>
                      <div className="text-white/30 text-xs">
                        Context pulled from: #engineering (23 messages), #product (12 messages)
                      </div>
                      <div className="flex gap-3 pt-2">
                        <button className="px-3 py-1.5 bg-white/10 text-white/70 text-sm rounded hover:bg-white/20 transition-colors">
                          View Draft
                        </button>
                        <button className="px-3 py-1.5 bg-white text-black text-sm rounded hover:bg-white/90 transition-colors">
                          Approve
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Step 4: Watch It Learn */}
                <div className="grid grid-cols-1 md:grid-cols-[120px_1fr] gap-6">
                  <div className="text-5xl font-light text-white/20">04</div>
                  <div>
                    <h3 className="text-xl font-medium mb-4">Watch it learn</h3>
                    <p className="text-white/50 leading-relaxed mb-6">
                      Every approval teaches yarnnn. What to extract. What to emphasize.
                      What tone fits the recipient. Over time, your role shifts from editing
                      to approving. The less you change, the better yarnnn is working.
                    </p>
                    <div className="border border-white/10 rounded-xl p-5 bg-white/5">
                      <div className="text-xs text-white/30 uppercase tracking-wider mb-4">Approval confidence over time</div>
                      <div className="space-y-3">
                        <div className="flex items-center gap-4">
                          <span className="text-white/50 text-sm w-16">Week 1</span>
                          <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                            <div className="h-full bg-white/30 rounded-full" style={{ width: "40%" }} />
                          </div>
                          <span className="text-white/50 text-sm w-24">Heavy edits</span>
                        </div>
                        <div className="flex items-center gap-4">
                          <span className="text-white/50 text-sm w-16">Week 4</span>
                          <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                            <div className="h-full bg-white/50 rounded-full" style={{ width: "70%" }} />
                          </div>
                          <span className="text-white/50 text-sm w-24">Light edits</span>
                        </div>
                        <div className="flex items-center gap-4">
                          <span className="text-white/70 text-sm w-16">Week 8</span>
                          <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                            <div className="h-full bg-white/80 rounded-full" style={{ width: "92%" }} />
                          </div>
                          <span className="text-white text-sm w-24">Approve</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* What yarnnn Learns */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">What yarnnn learns</h2>
              <p className="text-white/50 leading-relaxed mb-12 max-w-2xl">
                Every approval is a signal. yarnnn doesn&apos;t just save your changes—it learns
                what they mean for future drafts.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="border border-white/10 rounded-xl p-5">
                  <div className="text-lg font-medium mb-2">Which sources matter</div>
                  <p className="text-white/50 text-sm">
                    If you keep adding context from #design but never use #random,
                    yarnnn adjusts what it pulls.
                  </p>
                </div>
                <div className="border border-white/10 rounded-xl p-5">
                  <div className="text-lg font-medium mb-2">What structure works</div>
                  <p className="text-white/50 text-sm">
                    The sections you keep, the order you prefer, the level of detail
                    that fits.
                  </p>
                </div>
                <div className="border border-white/10 rounded-xl p-5">
                  <div className="text-lg font-medium mb-2">What tone fits</div>
                  <p className="text-white/50 text-sm">
                    Formal for investors, casual for team updates, direct for
                    busy stakeholders.
                  </p>
                </div>
                <div className="border border-white/10 rounded-xl p-5">
                  <div className="text-lg font-medium mb-2">What to emphasize</div>
                  <p className="text-white/50 text-sm">
                    Metrics you always include, topics you always mention,
                    patterns that matter to your recipient.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Your Role as Supervisor */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">Your role as supervisor</h2>
              <p className="text-white/50 leading-relaxed mb-12 max-w-2xl">
                You&apos;re not writing. You&apos;re not gathering. You&apos;re overseeing.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="border border-white/10 rounded-xl p-5">
                  <div className="text-lg font-medium mb-2">Decide what matters</div>
                  <p className="text-white/50 text-sm">
                    Configure which platforms, channels, and time ranges feed
                    each deliverable.
                  </p>
                </div>
                <div className="border border-white/10 rounded-xl p-5">
                  <div className="text-lg font-medium mb-2">Check that it&apos;s right</div>
                  <p className="text-white/50 text-sm">
                    Review drafts with context of where the content came from.
                    Adjust if needed.
                  </p>
                </div>
                <div className="border border-white/10 rounded-xl p-5">
                  <div className="text-lg font-medium mb-2">Give the go-ahead</div>
                  <p className="text-white/50 text-sm">
                    Approve when ready. Your approval teaches yarnnn for next time.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Platform to Deliverable Examples */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">Platform to deliverable</h2>
              <p className="text-white/50 leading-relaxed mb-12">
                If your platforms hold the context and you produce it regularly, yarnnn can synthesize it.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="border border-white/10 rounded-xl p-4">
                  <div className="text-white/30 text-xs uppercase tracking-wider mb-2">Slack #engineering</div>
                  <div className="text-white/50 mb-2">→</div>
                  <div className="text-white/70 text-sm">Weekly status reports</div>
                </div>
                <div className="border border-white/10 rounded-xl p-4">
                  <div className="text-white/30 text-xs uppercase tracking-wider mb-2">Gmail inbox</div>
                  <div className="text-white/50 mb-2">→</div>
                  <div className="text-white/70 text-sm">Client follow-up summaries</div>
                </div>
                <div className="border border-white/10 rounded-xl p-4">
                  <div className="text-white/30 text-xs uppercase tracking-wider mb-2">Notion project docs</div>
                  <div className="text-white/50 mb-2">→</div>
                  <div className="text-white/70 text-sm">Investor updates</div>
                </div>
                <div className="border border-white/10 rounded-xl p-4">
                  <div className="text-white/30 text-xs uppercase tracking-wider mb-2">Slack + Gmail + Notion</div>
                  <div className="text-white/50 mb-2">→</div>
                  <div className="text-white/70 text-sm">Cross-channel stakeholder briefs</div>
                </div>
                <div className="border border-white/10 rounded-xl p-4">
                  <div className="text-white/30 text-xs uppercase tracking-wider mb-2">Notion research database</div>
                  <div className="text-white/50 mb-2">→</div>
                  <div className="text-white/70 text-sm">Research digests</div>
                </div>
                <div className="border border-white/10 rounded-xl p-4">
                  <div className="text-white/30 text-xs uppercase tracking-wider mb-2">Gmail sent folder</div>
                  <div className="text-white/50 mb-2">→</div>
                  <div className="text-white/70 text-sm">Communication logs</div>
                </div>
              </div>
            </div>
          </section>

          {/* Alternative Path */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">Don&apos;t want to connect platforms?</h2>
              <p className="text-white/50 leading-relaxed mb-8 max-w-2xl">
                You can also describe your deliverable and paste examples. yarnnn will work with
                what you provide. But you&apos;ll update context manually as things change.
              </p>
              <p className="text-white/30 text-sm">
                Most users start here and connect platforms later when they see the value of fresh,
                automatic context.
              </p>
            </div>
          </section>

          {/* CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Ready to stop gathering?
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Connect your platforms. Configure your first deliverable.
                See a draft within minutes.
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