import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackground } from "@/components/landing/ShaderBackground";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { IntegrationHub } from "@/components/landing/IntegrationHub";

export default function LandingPage() {
  return (
    <main className="relative min-h-screen w-full overflow-x-hidden bg-[#faf8f5] text-[#1a1a1a]">
      <GrainOverlay />
      <ShaderBackground />

      {/* Content layer */}
      <div className="relative z-10">
        <LandingHeader />

        {/* Hero Section */}
        <section className="flex flex-col items-center justify-center px-6 py-32 md:py-40 min-h-[80vh]">
          <div className="max-w-6xl mx-auto w-full">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-12 lg:gap-20">
              {/* Left side - Text content */}
              <div className="text-center lg:text-left flex-1 max-w-2xl mx-auto lg:mx-0">
                {/* Brand name */}
                <div className="font-brand text-4xl md:text-5xl mb-8 text-[#1a1a1a]">
                  yarnnn
                </div>

                {/* Hero headline */}
                <h1 className="text-2xl sm:text-3xl md:text-4xl font-medium tracking-wide text-[#1a1a1a]/90 mb-6">
                  The things you send every week—
                  <br />
                  <span className="text-[#1a1a1a]">written for you, getting better each time.</span>
                </h1>

                {/* Supporting headline */}
                <p className="text-lg md:text-xl text-[#1a1a1a]/50 mb-12 max-w-xl mx-auto lg:mx-0 font-light">
                  Connect your Slack, Gmail, Notion, and Calendar. yarnnn turns what&apos;s happening
                  into the updates you owe people. You just review and hit send.
                </p>

                <Link
                  href="/auth/login"
                  className="inline-block px-8 py-4 glass-light text-[#1a1a1a] text-lg font-medium hover:bg-white/80 transition-all"
                >
                  Start for free
                </Link>
              </div>

              {/* Right side - Animated Integration Hub (hidden on mobile/tablet) */}
              <div className="flex-shrink-0 pb-16">
                <IntegrationHub />
              </div>
            </div>
          </div>
        </section>

        {/* The Gap */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <div>
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">The problem</div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
                  You already know what happened.
                  <br />
                  <span className="text-[#1a1a1a]/50">Writing it up is the chore.</span>
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed mb-6">
                  The conversations are in Slack. The emails are in your inbox. The notes
                  are in Notion. But every week, you still spend hours pulling it together
                  into a status report, a client update, or an investor email.
                </p>
                <p className="text-[#1a1a1a]/50 leading-relaxed">
                  It&apos;s not thinking work. It&apos;s just... assembly.
                </p>
              </div>
              <div className="glass-card-light p-6">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">How yarnnn helps</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">You review. yarnnn does the rest.</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Connect your tools once. Tell yarnnn what you need to send and when.
                  It pulls fresh context, writes a draft, and pings you when it&apos;s ready.
                  You review, tweak if needed, and approve.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* How It Works - Visual */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a] text-center">
              How it works
            </h2>
            <p className="text-[#1a1a1a]/50 text-center mb-16 max-w-xl mx-auto">
              Three steps. Then it just runs.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">01</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Connect your tools</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Link Slack, Gmail, Notion, or Calendar—wherever your work happens.
                  One-time sign-in, and yarnnn can see what you see.
                </p>
              </div>

              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">02</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Set up what you send</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Describe what you need—a weekly status report, a monthly update.
                  Pick which channels or threads should feed into it.
                </p>
              </div>

              <div className="glass-card-light p-6 text-center">
                <div className="text-4xl font-light text-[#1a1a1a]/20 mb-4">03</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Review and send</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  On schedule, yarnnn drafts it for you. You review, make any tweaks,
                  and approve. Done.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* The Learning Loop */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <div className="md:order-2">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">The magic</div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
                  It gets better
                  <br />
                  <span className="text-[#1a1a1a]/50">the more you use it.</span>
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed mb-6">
                  Every time you approve a draft—or tweak it first—yarnnn learns a little more
                  about what you like. Which details matter. What tone fits. How you phrase things.
                </p>
                <p className="text-[#1a1a1a]/50 leading-relaxed">
                  Your tenth draft needs fewer edits than your first. Eventually, you&apos;re
                  just skimming and hitting approve.
                </p>
              </div>
              <div className="glass-card-light p-6 md:order-1">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">How it learns</div>
                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/10 flex items-center justify-center text-xs text-[#1a1a1a]/50 shrink-0 mt-0.5">1</div>
                    <p className="text-[#1a1a1a]/70 text-sm">yarnnn pulls context from your connected tools</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/10 flex items-center justify-center text-xs text-[#1a1a1a]/50 shrink-0 mt-0.5">2</div>
                    <p className="text-[#1a1a1a]/70 text-sm">You review the draft and make any changes</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/10 flex items-center justify-center text-xs text-[#1a1a1a]/50 shrink-0 mt-0.5">3</div>
                    <p className="text-[#1a1a1a]/70 text-sm">Your edits teach yarnnn what you prefer</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#1a1a1a]/20 flex items-center justify-center text-xs text-[#1a1a1a]/70 shrink-0 mt-0.5">4</div>
                    <p className="text-[#1a1a1a] text-sm font-medium">Next time, the draft is closer to what you want</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* What You Can Create */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a]">
              Things people use yarnnn for
            </h2>
            <p className="text-[#1a1a1a]/50 mb-12 max-w-xl">
              If you send it regularly and your tools have the context, yarnnn can write it.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">From Slack</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Weekly status reports</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Team updates, blockers, wins—pulled from your channels and
                  formatted for your manager or stakeholders.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">From Gmail</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Client follow-ups</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Open threads, pending items, next steps—summarized so you
                  know exactly where things stand.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">From Notion</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Investor updates</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Metrics, milestones, and narrative—drafted from your
                  existing docs and project notes.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">From Calendar</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Meeting prep briefs</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Context on attendees, past interactions, and relevant docs—ready
                  before your next meeting.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">From multiple sources</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Stakeholder briefs</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Cross-channel context combined into one coherent update
                  for execs or partners.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">From Notion</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Research digests</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Your notes and highlights distilled into something
                  actionable for your team.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-3">From anywhere</div>
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Anything recurring</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  If it follows a pattern and you send it regularly,
                  yarnnn can learn it.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Two Ways to Start */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-4 text-[#1a1a1a] text-center">
              Two ways to get started
            </h2>
            <p className="text-[#1a1a1a]/50 text-center mb-12 max-w-xl mx-auto">
              Most people connect their tools for the full experience.
              But you can also start by just describing what you need.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="glass-card-light p-8">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-2">Recommended</div>
                <h3 className="text-xl font-medium mb-4 text-[#1a1a1a]">Connect your tools</h3>
                <p className="text-[#1a1a1a]/50 text-sm mb-6 leading-relaxed">
                  Link Slack, Gmail, Notion, or Calendar. yarnnn pulls fresh context automatically
                  every time—no copy-pasting, no manual updates.
                </p>
                <ul className="space-y-2 text-sm text-[#1a1a1a]/70">
                  <li className="flex items-start gap-2">
                    <span className="text-[#1a1a1a]/40">+</span>
                    Always up-to-date context
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[#1a1a1a]/40">+</span>
                    Less work each week
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[#1a1a1a]/40">+</span>
                    yarnnn finds patterns you might miss
                  </li>
                </ul>
              </div>

              <div className="glass-card-light p-8 opacity-80">
                <div className="text-xs text-[#1a1a1a]/30 uppercase tracking-wider mb-2">Also works</div>
                <h3 className="text-xl font-medium mb-4 text-[#1a1a1a]">Describe it yourself</h3>
                <p className="text-[#1a1a1a]/50 text-sm mb-6 leading-relaxed">
                  Paste an example or describe what you need. yarnnn works with
                  whatever you give it—you just update it manually over time.
                </p>
                <ul className="space-y-2 text-sm text-[#1a1a1a]/70">
                  <li className="flex items-start gap-2">
                    <span className="text-[#1a1a1a]/40">+</span>
                    Start right away
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[#1a1a1a]/40">+</span>
                    No permissions needed
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[#1a1a1a]/40">+</span>
                    You control exactly what yarnnn sees
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
              Spend less time writing updates.
              <br />
              <span className="text-[#1a1a1a]/50">More time on the work that matters.</span>
            </h2>
            <p className="text-[#1a1a1a]/50 mb-4">
              Free: 1 deliverable, unlimited tool connections
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
