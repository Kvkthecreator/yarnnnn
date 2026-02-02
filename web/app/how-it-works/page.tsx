import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";

export const metadata: Metadata = {
  title: "How It Works",
  description: "Set up once, review when ready, watch it learn. See how yarnnn turns your recurring work into deliverables that improve themselves.",
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
              yarnnn turns your recurring work into deliverables that improve themselves.
              Set it up once, review when ready, watch it learn from your edits.
            </p>
          </section>

          {/* The Three Steps */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <div className="space-y-24">
                {/* Step 1: Set Up */}
                <div className="grid grid-cols-1 md:grid-cols-[120px_1fr] gap-6">
                  <div className="text-5xl font-light text-white/20">01</div>
                  <div>
                    <h3 className="text-xl font-medium mb-4">Set up your deliverable</h3>
                    <p className="text-white/50 leading-relaxed mb-6">
                      Tell yarnnn what you deliver regularly. A weekly client update?
                      Monthly investor report? Research digest? Describe it once:
                      what it is, who receives it, when it&apos;s due.
                    </p>
                    <div className="border border-white/10 rounded-xl p-5 bg-white/5 space-y-4">
                      <div>
                        <div className="text-xs text-white/30 uppercase tracking-wider mb-1">Title</div>
                        <div className="text-white/70">Weekly Client Status — Acme Corp</div>
                      </div>
                      <div>
                        <div className="text-xs text-white/30 uppercase tracking-wider mb-1">Recipient</div>
                        <div className="text-white/70">Sarah Chen, VP Marketing</div>
                      </div>
                      <div>
                        <div className="text-xs text-white/30 uppercase tracking-wider mb-1">Schedule</div>
                        <div className="text-white/70">Every Monday at 8am</div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Step 2: Add Examples */}
                <div className="grid grid-cols-1 md:grid-cols-[120px_1fr] gap-6">
                  <div className="text-5xl font-light text-white/20">02</div>
                  <div>
                    <h3 className="text-xl font-medium mb-4">Upload examples of good work</h3>
                    <p className="text-white/50 leading-relaxed mb-6">
                      Show yarnnn what &quot;good&quot; looks like. Upload past deliverables,
                      reference documents, or templates you like. The more examples,
                      the better yarnnn understands your preferences.
                    </p>
                    <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                      <p className="text-white/30 text-sm italic">
                        &quot;I uploaded three of my best client updates from last quarter.
                        yarnnn picked up my format, my tone, even the metrics I always include.&quot;
                      </p>
                    </div>
                  </div>
                </div>

                {/* Step 3: Review Drafts */}
                <div className="grid grid-cols-1 md:grid-cols-[120px_1fr] gap-6">
                  <div className="text-5xl font-light text-white/20">03</div>
                  <div>
                    <h3 className="text-xl font-medium mb-4">Review and refine</h3>
                    <p className="text-white/50 leading-relaxed mb-6">
                      When it&apos;s time, yarnnn produces a draft and notifies you.
                      Review it, make edits, add feedback. When you&apos;re happy,
                      approve it and copy it out.
                    </p>
                    <div className="border border-white/10 rounded-xl p-5 bg-white/5 space-y-3">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-white/50">Version 5 — Staged for review</span>
                        <span className="px-2 py-1 bg-amber-500/20 text-amber-400 rounded text-xs">Ready</span>
                      </div>
                      <div className="flex gap-3">
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
                    <h3 className="text-xl font-medium mb-4">Watch it get better</h3>
                    <p className="text-white/50 leading-relaxed mb-6">
                      Here&apos;s the magic: every edit you make teaches yarnnn what you want.
                      It stores your corrections, learns your preferences, and applies
                      them to future drafts. Over time, you edit less.
                    </p>
                    <div className="border border-white/10 rounded-xl p-5 bg-white/5">
                      <div className="text-xs text-white/30 uppercase tracking-wider mb-4">Quality trend</div>
                      <div className="space-y-3">
                        <div className="flex items-center gap-4">
                          <span className="text-white/50 text-sm w-16">v1</span>
                          <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                            <div className="h-full bg-white/30 rounded-full" style={{ width: "60%" }} />
                          </div>
                          <span className="text-white/50 text-sm w-12">60%</span>
                        </div>
                        <div className="flex items-center gap-4">
                          <span className="text-white/50 text-sm w-16">v5</span>
                          <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                            <div className="h-full bg-white/50 rounded-full" style={{ width: "78%" }} />
                          </div>
                          <span className="text-white/50 text-sm w-12">78%</span>
                        </div>
                        <div className="flex items-center gap-4">
                          <span className="text-white/70 text-sm w-16">v10</span>
                          <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                            <div className="h-full bg-white/80 rounded-full" style={{ width: "92%" }} />
                          </div>
                          <span className="text-white text-sm w-12">92%</span>
                        </div>
                      </div>
                      <p className="text-white/30 text-xs mt-4">
                        Quality score = how close the draft is to your final version
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* The Feedback Loop */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">The feedback loop</h2>
              <p className="text-white/50 leading-relaxed mb-12 max-w-2xl">
                Most AI tools forget everything between sessions. yarnnn is different.
                When you edit a draft, yarnnn doesn&apos;t just save your changes—it learns from them.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="border border-white/10 rounded-xl p-5">
                  <div className="text-lg font-medium mb-2">You edit</div>
                  <p className="text-white/50 text-sm">
                    Change the opening paragraph, add a metric, fix the tone.
                  </p>
                </div>
                <div className="border border-white/10 rounded-xl p-5">
                  <div className="text-lg font-medium mb-2">yarnnn learns</div>
                  <p className="text-white/50 text-sm">
                    Stores what you changed and categorizes the type of edit.
                  </p>
                </div>
                <div className="border border-white/10 rounded-xl p-5">
                  <div className="text-lg font-medium mb-2">Next draft improves</div>
                  <p className="text-white/50 text-sm">
                    Future versions incorporate your preferences automatically.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* What You Can Deliver */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">What you can deliver</h2>
              <p className="text-white/50 leading-relaxed mb-12">
                If you produce it regularly, yarnnn can learn it.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="border border-white/10 rounded-xl p-4 text-white/70 text-sm">
                  Weekly client status reports
                </div>
                <div className="border border-white/10 rounded-xl p-4 text-white/70 text-sm">
                  Monthly investor updates
                </div>
                <div className="border border-white/10 rounded-xl p-4 text-white/70 text-sm">
                  Bi-weekly competitive briefs
                </div>
                <div className="border border-white/10 rounded-xl p-4 text-white/70 text-sm">
                  Daily team standups
                </div>
                <div className="border border-white/10 rounded-xl p-4 text-white/70 text-sm">
                  Research digests
                </div>
                <div className="border border-white/10 rounded-xl p-4 text-white/70 text-sm">
                  Newsletter drafts
                </div>
                <div className="border border-white/10 rounded-xl p-4 text-white/70 text-sm">
                  Meeting summaries
                </div>
                <div className="border border-white/10 rounded-xl p-4 text-white/70 text-sm">
                  Anything with a pattern
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
                Create your first deliverable for free. Upload some examples,
                set a schedule, and see the first draft within minutes.
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
