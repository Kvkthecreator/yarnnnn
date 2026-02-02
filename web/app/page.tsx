import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackground } from "@/components/landing/ShaderBackground";
import { GrainOverlay } from "@/components/landing/GrainOverlay";

export default function LandingPage() {
  return (
    <main className="relative min-h-screen w-full overflow-x-hidden bg-[#faf8f5] text-[#1a1a1a]">
      <GrainOverlay />
      <ShaderBackground />

      {/* Content layer */}
      <div className="relative z-10">
        <LandingHeader />

        {/* Hero Section */}
        <section className="flex flex-col items-center justify-center px-6 py-32 md:py-44 min-h-[80vh]">
          <div className="max-w-4xl mx-auto text-center">
            {/* Brand name */}
            <div className="font-brand text-4xl md:text-5xl mb-8 text-[#1a1a1a]">
              yarnnn
            </div>

            {/* Hero headline */}
            <h1 className="text-2xl sm:text-3xl md:text-4xl font-medium tracking-wide text-[#1a1a1a]/90 mb-6">
              Recurring work that gets better
              <br />
              <span className="text-[#1a1a1a]">every single time.</span>
            </h1>

            {/* Supporting headline */}
            <p className="text-lg md:text-xl text-[#1a1a1a]/50 mb-12 max-w-xl mx-auto font-light">
              Set it up once. Review when it&apos;s ready. Watch it learn.
            </p>

            <Link
              href="/auth/login"
              className="inline-block px-8 py-4 glass-light text-[#1a1a1a] text-lg font-medium hover:bg-white/80 transition-all"
            >
              Start for free
            </Link>
          </div>
        </section>

        {/* The Problem */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <div>
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">The problem</div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
                  You deliver the same things
                  <br />
                  <span className="text-[#1a1a1a]/50">over and over again.</span>
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed mb-6">
                  Weekly client updates. Monthly investor reports. Status emails every Monday.
                  You spend hours every week producing content that follows the same pattern—
                  but your AI can&apos;t remember what worked last time.
                </p>
              </div>
              <div className="glass-card-light p-6">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">yarnnn&apos;s approach</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Deliverables that improve themselves</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Set up a recurring deliverable once. yarnnn learns from every edit you make.
                  Your 10th version is better than your 1st—automatically.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* How It Works - Visual */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-16 text-[#1a1a1a] text-center">
              How it works
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">01</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Set up once</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Describe what you deliver, who receives it, and when it&apos;s due.
                  Upload examples of good work.
                </p>
              </div>

              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">02</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Review & refine</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  yarnnn produces a draft on schedule. Edit it, add feedback,
                  approve when it&apos;s ready.
                </p>
              </div>

              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">03</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Watch it learn</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Every edit teaches yarnnn what you want. Over time,
                  drafts need fewer changes.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* The Key Insight */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <div className="md:order-2">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">The insight</div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
                  Your edits are the training data.
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed mb-6">
                  Most AI forgets everything between sessions. yarnnn treats your corrections
                  like gold—storing what you changed, why you changed it, and applying those
                  lessons to future drafts.
                </p>
                <p className="text-[#1a1a1a]/50 leading-relaxed">
                  The result? Deliverables that sound more like you every time.
                </p>
              </div>
              <div className="glass-card-light p-6 md:order-1">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">Quality trend</div>
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-[#1a1a1a]/50">Version 1</span>
                    <span className="text-[#1a1a1a]/70">65% match</span>
                  </div>
                  <div className="h-2 bg-[#1a1a1a]/10 rounded-full overflow-hidden">
                    <div className="h-full bg-[#1a1a1a]/30 rounded-full" style={{ width: "65%" }} />
                  </div>
                  <div className="flex justify-between text-sm pt-2">
                    <span className="text-[#1a1a1a]/50">Version 5</span>
                    <span className="text-[#1a1a1a]/70">82% match</span>
                  </div>
                  <div className="h-2 bg-[#1a1a1a]/10 rounded-full overflow-hidden">
                    <div className="h-full bg-[#1a1a1a]/50 rounded-full" style={{ width: "82%" }} />
                  </div>
                  <div className="flex justify-between text-sm pt-2">
                    <span className="text-[#1a1a1a]/50">Version 10</span>
                    <span className="text-[#1a1a1a]">94% match</span>
                  </div>
                  <div className="h-2 bg-[#1a1a1a]/10 rounded-full overflow-hidden">
                    <div className="h-full bg-[#1a1a1a]/80 rounded-full" style={{ width: "94%" }} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Use Cases */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-12 text-[#1a1a1a]">
              What people deliver with yarnnn
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="glass-card-light p-6">
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Weekly client updates</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Status reports that actually sound like you wrote them.
                  Consistent format, personalized tone.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Investor updates</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Monthly metrics, narrative, and outlook—
                  drafted and waiting for your review.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Competitive briefs</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Regular industry roundups pulling from your sources,
                  formatted how you like them.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Team standups</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Summaries of what happened, what&apos;s next,
                  and what&apos;s blocked—ready every morning.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Research digests</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Curated insights from your reading list,
                  synthesized into actionable briefs.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Anything recurring</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  If you deliver it regularly, yarnnn can learn it.
                  Your patterns, your format, your voice.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Comparison */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-12 text-[#1a1a1a] text-center">
              The difference
            </h2>

            {/* Mobile: Card layout */}
            <div className="md:hidden space-y-4">
              {[
                { feature: "Learns from your edits", chatgpt: "No", templates: "No", yarn: "Yes" },
                { feature: "Produces on schedule", chatgpt: "No", templates: "Manual", yarn: "Automatic" },
                { feature: "Improves over time", chatgpt: "No", templates: "No", yarn: "Yes" },
                { feature: "Shows quality trend", chatgpt: "No", templates: "No", yarn: "Yes" },
              ].map((row) => (
                <div key={row.feature} className="glass-card-light p-4">
                  <div className="font-medium text-[#1a1a1a] mb-3">{row.feature}</div>
                  <div className="grid grid-cols-3 gap-2 text-sm">
                    <div>
                      <div className="text-[#1a1a1a]/40 text-xs mb-1">ChatGPT</div>
                      <div className="text-[#1a1a1a]/50">{row.chatgpt}</div>
                    </div>
                    <div>
                      <div className="text-[#1a1a1a]/40 text-xs mb-1">Templates</div>
                      <div className="text-[#1a1a1a]/50">{row.templates}</div>
                    </div>
                    <div>
                      <div className="text-[#1a1a1a]/80 text-xs mb-1">yarnnn</div>
                      <div className="text-[#1a1a1a] font-medium">{row.yarn}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Desktop: Table layout */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-[#1a1a1a]/10">
                    <th className="py-4 pr-4 text-sm font-medium text-[#1a1a1a]/50"></th>
                    <th className="py-4 px-4 text-sm font-medium text-[#1a1a1a]/50">ChatGPT</th>
                    <th className="py-4 px-4 text-sm font-medium text-[#1a1a1a]/50">Templates</th>
                    <th className="py-4 pl-4 text-sm font-medium text-[#1a1a1a]">yarnnn</th>
                  </tr>
                </thead>
                <tbody className="text-sm">
                  <tr className="border-b border-[#1a1a1a]/5">
                    <td className="py-4 pr-4 text-[#1a1a1a]">Learns from your edits</td>
                    <td className="py-4 px-4 text-[#1a1a1a]/40">No</td>
                    <td className="py-4 px-4 text-[#1a1a1a]/40">No</td>
                    <td className="py-4 pl-4 text-[#1a1a1a] font-medium">Yes</td>
                  </tr>
                  <tr className="border-b border-[#1a1a1a]/5">
                    <td className="py-4 pr-4 text-[#1a1a1a]">Produces on schedule</td>
                    <td className="py-4 px-4 text-[#1a1a1a]/40">No</td>
                    <td className="py-4 px-4 text-[#1a1a1a]/40">Manual</td>
                    <td className="py-4 pl-4 text-[#1a1a1a] font-medium">Automatic</td>
                  </tr>
                  <tr className="border-b border-[#1a1a1a]/5">
                    <td className="py-4 pr-4 text-[#1a1a1a]">Improves over time</td>
                    <td className="py-4 px-4 text-[#1a1a1a]/40">No</td>
                    <td className="py-4 px-4 text-[#1a1a1a]/40">No</td>
                    <td className="py-4 pl-4 text-[#1a1a1a] font-medium">Yes</td>
                  </tr>
                  <tr>
                    <td className="py-4 pr-4 text-[#1a1a1a]">Shows quality trend</td>
                    <td className="py-4 px-4 text-[#1a1a1a]/40">No</td>
                    <td className="py-4 px-4 text-[#1a1a1a]/40">No</td>
                    <td className="py-4 pl-4 text-[#1a1a1a] font-medium">Yes</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
              Your 10th delivery is better than your 1st.
            </h2>
            <p className="text-[#1a1a1a]/50 mb-4">
              Free tier: 1 deliverable, unlimited versions
            </p>
            <p className="text-[#1a1a1a]/50 mb-10">
              Pro: Unlimited deliverables — $19/mo
            </p>
            <Link
              href="/auth/login"
              className="inline-block px-8 py-4 glass-light text-[#1a1a1a] text-lg font-medium hover:bg-white/80 transition-all"
            >
              Start for free
            </Link>
          </div>
        </section>

        <LandingFooter />
      </div>
    </main>
  );
}
