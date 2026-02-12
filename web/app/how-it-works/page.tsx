import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";

export const metadata: Metadata = {
  title: "Meet TP",
  description: "Meet your Thinking Partner. TP connects to your work platforms, understands your context, and produces your recurring deliverables.",
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
            <p className="text-white/40 text-sm uppercase tracking-widest mb-4">How It Works</p>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-10 tracking-tight leading-[1.1]">
              Meet TP,
              <br />
              <span className="text-white/50">your Thinking Partner.</span>
            </h1>
            <p className="max-w-2xl text-white/50 text-lg">
              TP is who you talk to. Not a form to fill out. Not a prompt to craft.
              Just a conversation about what you need—and TP handles the rest.
            </p>
          </section>

          {/* The Conversation Model */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">You talk. TP listens.</h2>
              <p className="text-white/50 leading-relaxed mb-12 max-w-2xl">
                No wizards. No forms. Just describe what you need in plain language,
                and TP asks the right follow-up questions.
              </p>

              {/* Chat Example */}
              <div className="border border-white/10 rounded-2xl p-6 bg-white/5 max-w-2xl">
                <div className="space-y-6">
                  {/* User message */}
                  <div className="flex justify-end">
                    <div className="bg-white/10 rounded-2xl rounded-br-sm px-4 py-3 max-w-[85%]">
                      <p className="text-white/90 text-sm">I need to send a weekly update to Sarah</p>
                    </div>
                  </div>

                  {/* TP response */}
                  <div className="flex justify-start">
                    <div className="bg-white/5 border border-white/10 rounded-2xl rounded-bl-sm px-4 py-3 max-w-[85%]">
                      <p className="text-white/70 text-sm mb-2">
                        Got it. I see you have #engineering and #product connected.
                      </p>
                      <p className="text-white/70 text-sm">
                        Should I pull from both for your updates?
                      </p>
                    </div>
                  </div>

                  {/* User message */}
                  <div className="flex justify-end">
                    <div className="bg-white/10 rounded-2xl rounded-br-sm px-4 py-3 max-w-[85%]">
                      <p className="text-white/90 text-sm">Just engineering for now</p>
                    </div>
                  </div>

                  {/* TP response */}
                  <div className="flex justify-start">
                    <div className="bg-white/5 border border-white/10 rounded-2xl rounded-bl-sm px-4 py-3 max-w-[85%]">
                      <p className="text-white/70 text-sm mb-2">
                        Perfect. When does Sarah need this?
                      </p>
                    </div>
                  </div>

                  {/* User message */}
                  <div className="flex justify-end">
                    <div className="bg-white/10 rounded-2xl rounded-br-sm px-4 py-3 max-w-[85%]">
                      <p className="text-white/90 text-sm">Monday mornings</p>
                    </div>
                  </div>

                  {/* TP final response */}
                  <div className="flex justify-start">
                    <div className="bg-white/5 border border-white/10 rounded-2xl rounded-bl-sm px-4 py-3 max-w-[85%]">
                      <p className="text-white/70 text-sm mb-3">
                        I&apos;ll have your first draft ready Sunday evening.
                      </p>
                      <p className="text-white/70 text-sm">
                        Based on this week&apos;s #engineering activity, here&apos;s what I&apos;d include...
                      </p>
                      <div className="mt-3 pt-3 border-t border-white/10">
                        <p className="text-white/40 text-xs">Draft preview loading...</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <p className="text-white/30 text-xs mt-6 max-w-xl">
                That&apos;s it. No configuration screens. TP figures out what you need
                and sets everything up through conversation.
              </p>
            </div>
          </section>

          {/* What TP Does */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">What TP does for you</h2>
              <p className="text-white/50 leading-relaxed mb-12 max-w-2xl">
                TP isn&apos;t just a chatbot. It&apos;s a partner that understands your work,
                connects to your tools, and produces deliverables on your behalf.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="border border-white/10 rounded-xl p-6">
                  <div className="text-lg font-medium mb-3">Connects to your platforms</div>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Slack, Gmail, Notion, Calendar. TP guides you through connecting them,
                    then pulls context automatically every cycle.
                  </p>
                </div>

                <div className="border border-white/10 rounded-xl p-6">
                  <div className="text-lg font-medium mb-3">Understands your work</div>
                  <p className="text-white/50 text-sm leading-relaxed">
                    TP reads your channels, threads, and docs. It knows what happened
                    this week—so you don&apos;t have to summarize it yourself.
                  </p>
                </div>

                <div className="border border-white/10 rounded-xl p-6">
                  <div className="text-lg font-medium mb-3">Drafts in your voice</div>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Status reports, investor updates, client briefs. TP synthesizes
                    your context into deliverables that sound like you wrote them.
                  </p>
                </div>

                <div className="border border-white/10 rounded-xl p-6">
                  <div className="text-lg font-medium mb-3">Learns from your feedback</div>
                  <p className="text-white/50 text-sm leading-relaxed">
                    Every edit, every approval teaches TP. Over time, drafts need
                    fewer tweaks. Eventually, you just approve.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* The Flow */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">The flow</h2>
              <p className="text-white/50 leading-relaxed mb-16 max-w-2xl">
                From first conversation to recurring drafts.
              </p>

              <div className="space-y-16">
                {/* Step 1 */}
                <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6">
                  <div className="text-4xl font-light text-white/20">01</div>
                  <div>
                    <h3 className="text-xl font-medium mb-3">Tell TP what you need</h3>
                    <p className="text-white/50 leading-relaxed">
                      &ldquo;I need a weekly status report for my manager&rdquo; or
                      &ldquo;Monthly investor update, first Tuesday&rdquo;.
                      Just say it. TP asks clarifying questions.
                    </p>
                  </div>
                </div>

                {/* Step 2 */}
                <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6">
                  <div className="text-4xl font-light text-white/20">02</div>
                  <div>
                    <h3 className="text-xl font-medium mb-3">Connect your sources</h3>
                    <p className="text-white/50 leading-relaxed">
                      TP guides you through connecting Slack, Gmail, Notion—wherever
                      your work lives. One-time OAuth. After that, TP can see what you see.
                    </p>
                  </div>
                </div>

                {/* Step 3 */}
                <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6">
                  <div className="text-4xl font-light text-white/20">03</div>
                  <div>
                    <h3 className="text-xl font-medium mb-3">Review when ready</h3>
                    <p className="text-white/50 leading-relaxed">
                      On schedule, TP pulls fresh context and drafts your deliverable.
                      You get pinged. Read through it. Tweak if needed. Approve when it&apos;s right.
                    </p>
                  </div>
                </div>

                {/* Step 4 */}
                <div className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-6">
                  <div className="text-4xl font-light text-white/20">04</div>
                  <div>
                    <h3 className="text-xl font-medium mb-3">Watch it improve</h3>
                    <p className="text-white/50 leading-relaxed">
                      Every approval teaches TP. Structure preferences. Tone. What to highlight.
                      By week 8, you&apos;re approving with barely a glance.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* TP Learns */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">TP remembers everything</h2>
              <p className="text-white/50 leading-relaxed mb-12 max-w-2xl">
                Unlike other AI tools that reset every session, TP builds a persistent
                understanding of your work and preferences.
              </p>

              <div className="border border-white/10 rounded-xl p-6 bg-white/5">
                <div className="text-xs text-white/30 uppercase tracking-wider mb-6">What TP learns from you</div>
                <div className="space-y-4">
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">
                      Which Slack channels have the signal, which are noise
                    </p>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">
                      How you structure updates—sections, order, level of detail
                    </p>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">
                      The tone that fits each recipient—formal for board, casual for team
                    </p>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-white/30 mt-2 shrink-0" />
                    <p className="text-white/70 text-sm">
                      What metrics matter, what wins to call out, what context to include
                    </p>
                  </div>
                </div>
              </div>

              <p className="text-white/30 text-sm mt-6">
                The goal: your approval becomes a rubber stamp.
                Not because TP is guessing—because TP knows.
              </p>
            </div>
          </section>

          {/* Examples */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-4">What you can say to TP</h2>
              <p className="text-white/50 leading-relaxed mb-12">
                No magic phrases. Just tell TP what you need.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;I need a weekly status report for Sarah&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Summarize my client emails from this week&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Create a monthly investor update&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;What happened in #engineering this week?&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Make this draft more concise&rdquo;</p>
                </div>
                <div className="border border-white/10 rounded-xl p-4 bg-white/5">
                  <p className="text-white/70 text-sm italic">&ldquo;Add the metrics from our Notion dashboard&rdquo;</p>
                </div>
              </div>
            </div>
          </section>

          {/* CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Ready to meet TP?
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Start a conversation. Tell TP what you need.
                See your first draft in minutes.
              </p>
              <Link
                href="/auth/login"
                className="inline-block px-8 py-4 bg-white text-black text-lg font-medium rounded-full hover:bg-white/90 transition-colors"
              >
                Start talking to TP
              </Link>
            </div>
          </section>
        </main>

        <LandingFooter inverted />
      </div>
    </div>
  );
}
