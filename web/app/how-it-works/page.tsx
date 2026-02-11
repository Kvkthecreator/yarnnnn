import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";

export const metadata: Metadata = {
  title: "How It Works",
  description: "Connect your tools, set up what you send, review and approve. See how yarnnn writes your recurring updates for you.",
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
              You connect your tools. You tell yarnnn what you need to send.
              Then you just review and approve—yarnnn handles the rest.
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
                    <h3 className="text-xl font-medium mb-4">Connect your tools</h3>
                    <p className="text-white/50 leading-relaxed mb-6">
                      Link the apps where your work already lives—Slack, Gmail, Notion, Calendar.
                      It&apos;s a one-time sign-in. After that, yarnnn can see what you see.
                    </p>
                    <div className="border border-white/10 rounded-xl p-5 bg-white/5">
                      <div className="grid grid-cols-4 gap-4">
                        <div className="text-center">
                          <div className="text-2xl mb-2">💬</div>
                          <div className="text-white/70 text-sm">Slack</div>
                          <div className="text-white/30 text-xs">Channels and threads</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl mb-2">📧</div>
                          <div className="text-white/70 text-sm">Gmail</div>
                          <div className="text-white/30 text-xs">Your inbox</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl mb-2">📝</div>
                          <div className="text-white/70 text-sm">Notion</div>
                          <div className="text-white/30 text-xs">Pages and databases</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl mb-2">📅</div>
                          <div className="text-white/70 text-sm">Calendar</div>
                          <div className="text-white/30 text-xs">Meetings and events</div>
                        </div>
                      </div>
                    </div>
                    <p className="text-white/30 text-xs mt-4">
                      Technical note: yarnnn uses secure OAuth connections. Your credentials are never stored.
                    </p>
                  </div>
                </div>

                {/* Step 2: Set Up */}
                <div className="grid grid-cols-1 md:grid-cols-[120px_1fr] gap-6">
                  <div className="text-5xl font-light text-white/20">02</div>
                  <div>
                    <h3 className="text-xl font-medium mb-4">Set up what you send</h3>
                    <p className="text-white/50 leading-relaxed mb-6">
                      Tell yarnnn what you need to produce. A weekly status report?
                      A monthly investor update? Describe it, say who it&apos;s for,
                      and pick which channels or docs should feed into it.
                    </p>
                    <div className="border border-white/10 rounded-xl p-5 bg-white/5 space-y-4">
                      <div>
                        <div className="text-xs text-white/30 uppercase tracking-wider mb-1">What you&apos;re sending</div>
                        <div className="text-white/70">Weekly Status Report</div>
                      </div>
                      <div>
                        <div className="text-xs text-white/30 uppercase tracking-wider mb-1">Who it&apos;s for</div>
                        <div className="text-white/70">Sarah (my manager)</div>
                      </div>
                      <div>
                        <div className="text-xs text-white/30 uppercase tracking-wider mb-1">When it&apos;s due</div>
                        <div className="text-white/70">Every Monday at 9am</div>
                      </div>
                      <div>
                        <div className="text-xs text-white/30 uppercase tracking-wider mb-1">Where yarnnn looks</div>
                        <div className="flex flex-wrap gap-2 mt-1">
                          <span className="px-2 py-1 bg-white/10 rounded text-white/70 text-xs">#engineering</span>
                          <span className="px-2 py-1 bg-white/10 rounded text-white/70 text-xs">#product</span>
                          <span className="px-2 py-1 bg-white/10 rounded text-white/70 text-xs">Last 7 days</span>
                        </div>
                      </div>
                    </div>
                    <p className="text-white/30 text-xs mt-4">
                      Technical note: yarnnn uses scoped context extraction—only pulling from the sources you specify, within the time range you set.
                    </p>
                  </div>
                </div>

                {/* Step 3: Review */}
                <div className="grid grid-cols-1 md:grid-cols-[120px_1fr] gap-6">
                  <div className="text-5xl font-light text-white/20">03</div>
                  <div>
                    <h3 className="text-xl font-medium mb-4">Review and approve</h3>
                    <p className="text-white/50 leading-relaxed mb-6">
                      When it&apos;s time, yarnnn pulls fresh context from your tools,
                      writes a draft, and pings you. You read through it, make any tweaks,
                      and approve when it looks good.
                    </p>
                    <div className="border border-white/10 rounded-xl p-5 bg-white/5 space-y-3">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-white/50">Weekly Status Report — Draft ready</span>
                        <span className="px-2 py-1 bg-amber-500/20 text-amber-400 rounded text-xs">Ready to review</span>
                      </div>
                      <div className="text-white/30 text-xs">
                        Built from: 23 messages in #engineering, 12 in #product
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

                {/* Step 4: It Learns */}
                <div className="grid grid-cols-1 md:grid-cols-[120px_1fr] gap-6">
                  <div className="text-5xl font-light text-white/20">04</div>
                  <div>
                    <h3 className="text-xl font-medium mb-4">It gets better over time</h3>
                    <p className="text-white/50 leading-relaxed mb-6">
                      Here&apos;s the part that feels like magic: every time you approve a draft—or
                      tweak it first—yarnnn learns a little more about what you want.
                      The tenth draft needs fewer edits than the first.
                    </p>
                    <div className="border border-white/10 rounded-xl p-5 bg-white/5">
                      <div className="text-xs text-white/30 uppercase tracking-wider mb-4">Your editing over time</div>
                      <div className="space-y-3">
                        <div className="flex items-center gap-4">
                          <span className="text-white/50 text-sm w-16">Week 1</span>
                          <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                            <div className="h-full bg-white/30 rounded-full" style={{ width: "60%" }} />
                          </div>
                          <span className="text-white/50 text-sm w-28">Lots of edits</span>
                        </div>
                        <div className="flex items-center gap-4">
                          <span className="text-white/50 text-sm w-16">Week 4</span>
                          <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                            <div className="h-full bg-white/50 rounded-full" style={{ width: "25%" }} />
                          </div>
                          <span className="text-white/50 text-sm w-28">A few tweaks</span>
                        </div>
                        <div className="flex items-center gap-4">
                          <span className="text-white/70 text-sm w-16">Week 8</span>
                          <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                            <div className="h-full bg-white/80 rounded-full" style={{ width: "8%" }} />
                          </div>
                          <span className="text-white text-sm w-28">Just approve</span>
                        </div>
                      </div>
                    </div>
                    <p className="text-white/30 text-xs mt-4">
                      Technical note: yarnnn uses your edits as training signal—learning your preferred structure, tone, and emphasis without requiring explicit feedback.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* What yarnnn Learns */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">What yarnnn picks up on</h2>
              <p className="text-white/50 leading-relaxed mb-12 max-w-2xl">
                Every time you approve (or edit, then approve), yarnnn learns something.
                It&apos;s not just saving your changes—it&apos;s understanding why you made them.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="border border-white/10 rounded-xl p-5">
                  <div className="text-lg font-medium mb-2">Which sources matter most</div>
                  <p className="text-white/50 text-sm">
                    If you always add details from #design but never reference #random,
                    yarnnn starts prioritizing accordingly.
                  </p>
                </div>
                <div className="border border-white/10 rounded-xl p-5">
                  <div className="text-lg font-medium mb-2">How you like things structured</div>
                  <p className="text-white/50 text-sm">
                    The sections you keep, the order you prefer, how much detail
                    feels right.
                  </p>
                </div>
                <div className="border border-white/10 rounded-xl p-5">
                  <div className="text-lg font-medium mb-2">The tone that fits</div>
                  <p className="text-white/50 text-sm">
                    Formal for the board, casual for your team, direct and brief
                    for busy stakeholders.
                  </p>
                </div>
                <div className="border border-white/10 rounded-xl p-5">
                  <div className="text-lg font-medium mb-2">What to highlight</div>
                  <p className="text-white/50 text-sm">
                    The metrics you always include, the wins worth calling out,
                    the context your recipient cares about.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Examples */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">Things people use yarnnn for</h2>
              <p className="text-white/50 leading-relaxed mb-12">
                If it&apos;s recurring and your tools have the raw material, yarnnn can probably write it.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="border border-white/10 rounded-xl p-4">
                  <div className="text-white/30 text-xs uppercase tracking-wider mb-2">Slack → Manager</div>
                  <div className="text-white/70 text-sm">Weekly status reports</div>
                </div>
                <div className="border border-white/10 rounded-xl p-4">
                  <div className="text-white/30 text-xs uppercase tracking-wider mb-2">Gmail → You</div>
                  <div className="text-white/70 text-sm">Client follow-up summaries</div>
                </div>
                <div className="border border-white/10 rounded-xl p-4">
                  <div className="text-white/30 text-xs uppercase tracking-wider mb-2">Notion → Investors</div>
                  <div className="text-white/70 text-sm">Monthly investor updates</div>
                </div>
                <div className="border border-white/10 rounded-xl p-4">
                  <div className="text-white/30 text-xs uppercase tracking-wider mb-2">Calendar → You</div>
                  <div className="text-white/70 text-sm">Meeting prep briefs</div>
                </div>
                <div className="border border-white/10 rounded-xl p-4">
                  <div className="text-white/30 text-xs uppercase tracking-wider mb-2">Multiple → Stakeholders</div>
                  <div className="text-white/70 text-sm">Cross-team briefs</div>
                </div>
                <div className="border border-white/10 rounded-xl p-4">
                  <div className="text-white/30 text-xs uppercase tracking-wider mb-2">Notion → Team</div>
                  <div className="text-white/70 text-sm">Research digests</div>
                </div>
                <div className="border border-white/10 rounded-xl p-4">
                  <div className="text-white/30 text-xs uppercase tracking-wider mb-2">Anywhere → Anyone</div>
                  <div className="text-white/70 text-sm">Anything recurring</div>
                </div>
              </div>
            </div>
          </section>

          {/* Alternative Path */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">Don&apos;t want to connect your tools?</h2>
              <p className="text-white/50 leading-relaxed mb-6 max-w-2xl">
                That&apos;s okay too. You can describe what you need or paste in an example,
                and yarnnn will work with that. You&apos;ll just update the context yourself
                when things change.
              </p>
              <p className="text-white/30 text-sm">
                Most people start this way to try it out, then connect their tools
                once they see how it works.
              </p>
            </div>
          </section>

          {/* CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Ready to try it?
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Connect your tools. Set up your first deliverable.
                See a draft in minutes.
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
