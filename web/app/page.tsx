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
              Your work platforms,
              <br />
              <span className="text-[#1a1a1a]">turned into deliverables.</span>
            </h1>

            {/* Supporting headline */}
            <p className="text-lg md:text-xl text-[#1a1a1a]/50 mb-12 max-w-xl mx-auto font-light">
              Connect. Configure. Approve.
            </p>

            <Link
              href="/auth/login"
              className="inline-block px-8 py-4 glass-light text-[#1a1a1a] text-lg font-medium hover:bg-white/80 transition-all"
            >
              Start for free
            </Link>
          </div>
        </section>

        {/* The Gap */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <div>
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">The gap</div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
                  Work happens here.
                  <br />
                  <span className="text-[#1a1a1a]/50">Deliverables go there.</span>
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed mb-6">
                  Your Slack threads, email chains, and Notion docs hold everything you need.
                  But every week, you manually read, summarize, and reformat it into what
                  you owe someone. Status reports. Investor updates. Client briefs.
                </p>
                <p className="text-[#1a1a1a]/50 leading-relaxed">
                  The space between your platforms and your deliverables is filled with
                  repetitive labor.
                </p>
              </div>
              <div className="glass-card-light p-6">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">yarnnn closes the gap</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Connect once, deliver forever</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  yarnnn connects to where your work happens. It extracts what matters,
                  synthesizes it into what you owe someone, and delivers drafts on schedule.
                  You review and approve.
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
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Connect</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Link the platforms where your work happens.
                  Slack, Gmail, Notion. One-time sign-in.
                </p>
              </div>

              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">02</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Configure</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Tell yarnnn what to produce, who receives it, and when.
                  Select which channels or docs should inform it.
                </p>
              </div>

              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">03</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Approve</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  yarnnn pulls fresh context, synthesizes a draft, and notifies you.
                  Review, adjust if needed, approve.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Your Role */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <div className="md:order-2">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">Your role</div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
                  You&apos;re the supervisor.
                  <br />
                  <span className="text-[#1a1a1a]/50">Not the writer.</span>
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed mb-6">
                  Supervisors don&apos;t do the work. They decide what matters,
                  check that it&apos;s right, and give the go-ahead. That&apos;s your job with yarnnn.
                </p>
                <p className="text-[#1a1a1a]/50 leading-relaxed">
                  The less you edit, the better yarnnn is working.
                </p>
              </div>
              <div className="glass-card-light p-6 md:order-1">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">The learning loop</div>
                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/10 flex items-center justify-center text-xs text-[#1a1a1a]/50 shrink-0 mt-0.5">1</div>
                    <p className="text-[#1a1a1a]/70 text-sm">yarnnn pulls context from your platforms</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/10 flex items-center justify-center text-xs text-[#1a1a1a]/50 shrink-0 mt-0.5">2</div>
                    <p className="text-[#1a1a1a]/70 text-sm">You review and approve (with light edits if needed)</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/10 flex items-center justify-center text-xs text-[#1a1a1a]/50 shrink-0 mt-0.5">3</div>
                    <p className="text-[#1a1a1a]/70 text-sm">yarnnn learns what to extract and how you approve</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/20 flex items-center justify-center text-xs text-[#1a1a1a]/70 shrink-0 mt-0.5">4</div>
                    <p className="text-[#1a1a1a] text-sm font-medium">Over time, approval becomes a rubber stamp</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* What You Deliver */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-12 text-[#1a1a1a]">
              Platform to deliverable
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Slack #engineering</div>
                <div className="text-[#1a1a1a]/30 text-lg mb-3">&darr;</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Weekly Status Report</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Team updates, blockers, and progress synthesized into
                  what your manager needs to see.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Gmail inbox</div>
                <div className="text-[#1a1a1a]/30 text-lg mb-3">&darr;</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Client Follow-up Summary</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Open threads, pending responses, and action items
                  compiled for your review.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Notion project docs</div>
                <div className="text-[#1a1a1a]/30 text-lg mb-3">&darr;</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Investor Update</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Metrics, milestones, and narrative pulled from
                  your existing documentation.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Slack #product + Gmail</div>
                <div className="text-[#1a1a1a]/30 text-lg mb-3">&darr;</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Stakeholder Brief</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Cross-channel context synthesized into a single
                  coherent update.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Notion research database</div>
                <div className="text-[#1a1a1a]/30 text-lg mb-3">&darr;</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Research Digest</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Your notes and highlights turned into an actionable
                  summary for your team.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">Any connected source</div>
                <div className="text-[#1a1a1a]/30 text-lg mb-3">&darr;</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Anything recurring</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  If you deliver it regularly and your platforms hold the context,
                  yarnnn can produce it.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Two Ways to Start */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-12 text-[#1a1a1a] text-center">
              Two ways to start
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="glass-card-light p-8">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-2">Recommended</div>
                <h3 className="text-xl font-medium mb-4 text-[#1a1a1a]">Connect your platforms</h3>
                <ul className="space-y-3 mb-6">
                  <li className="flex items-start gap-3 text-sm text-[#1a1a1a]/70">
                    <span className="text-[#1a1a1a]/40">+</span>
                    Always fresh context every cycle
                  </li>
                  <li className="flex items-start gap-3 text-sm text-[#1a1a1a]/70">
                    <span className="text-[#1a1a1a]/40">+</span>
                    Less work over time
                  </li>
                  <li className="flex items-start gap-3 text-sm text-[#1a1a1a]/70">
                    <span className="text-[#1a1a1a]/40">+</span>
                    yarnnn discovers patterns automatically
                  </li>
                </ul>
                <p className="text-xs text-[#1a1a1a]/40">Requires one-time sign-in per platform</p>
              </div>

              <div className="glass-card-light p-8 opacity-80">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-2">Alternative</div>
                <h3 className="text-xl font-medium mb-4 text-[#1a1a1a]">Describe it yourself</h3>
                <ul className="space-y-3 mb-6">
                  <li className="flex items-start gap-3 text-sm text-[#1a1a1a]/70">
                    <span className="text-[#1a1a1a]/40">+</span>
                    Start immediately
                  </li>
                  <li className="flex items-start gap-3 text-sm text-[#1a1a1a]/70">
                    <span className="text-[#1a1a1a]/40">+</span>
                    No permissions needed
                  </li>
                  <li className="flex items-start gap-3 text-sm text-[#1a1a1a]/70">
                    <span className="text-[#1a1a1a]/40">+</span>
                    You control exactly what yarnnn sees
                  </li>
                </ul>
                <p className="text-xs text-[#1a1a1a]/40">You&apos;ll update context manually as things change</p>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
              Stop gathering. Start supervising.
            </h2>
            <p className="text-[#1a1a1a]/50 mb-4">
              Free: 1 deliverable, unlimited integrations
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