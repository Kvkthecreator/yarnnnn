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

        {/* Hero Section - Pain-first */}
        <section className="flex flex-col items-center justify-center px-6 py-32 md:py-44 min-h-[80vh]">
          <div className="max-w-4xl mx-auto text-center">
            {/* Brand name */}
            <div className="font-brand text-4xl md:text-5xl mb-8 text-[#1a1a1a]">
              yarnnn
            </div>

            {/* Pain-first headline */}
            <h1 className="text-2xl sm:text-3xl md:text-4xl font-medium tracking-wide text-[#1a1a1a]/90 mb-6">
              Your AI keeps mixing things up.
              <br />
              <span className="text-[#1a1a1a]">Yarn doesn&apos;t.</span>
            </h1>

            {/* Supporting headline */}
            <p className="text-lg md:text-xl text-[#1a1a1a]/50 mb-12 max-w-xl mx-auto font-light">
              Tell it once. It remembers forever.
            </p>

            <Link
              href="/auth/login"
              className="inline-block px-8 py-4 glass-light text-[#1a1a1a] text-lg font-medium hover:bg-white/80 transition-all"
            >
              Start for free
            </Link>
          </div>
        </section>

        {/* Pain Point 1: Context Chaos */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <div>
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">The problem</div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
                  Working on multiple clients?
                  <br />
                  <span className="text-[#1a1a1a]/50">ChatGPT puts them all in one bucket.</span>
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed mb-6">
                  You asked ChatGPT to draft an email for Client A, and it used details
                  from Client B. You caught it—barely. How long until something slips through?
                </p>
              </div>
              <div className="glass-card-light p-6">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">Yarn&apos;s approach</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Every project stays separate</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Ask about Client A, get only Client A context. Always.
                  Switch between clients without cross-contamination.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Pain Point 2: Groundhog Day */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <div className="md:order-2">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">The problem</div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
                  Tired of explaining yourself?
                  <br />
                  <span className="text-[#1a1a1a]/50">Every chat starts from scratch.</span>
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed mb-6">
                  You&apos;ve explained your business model to ChatGPT probably 50 times.
                  Every. Single. Time. That&apos;s hours of your life, repeating yourself.
                </p>
              </div>
              <div className="glass-card-light p-6 md:order-1">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">Yarn&apos;s approach</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">Tell it once. It remembers.</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Upload your docs once. Chat naturally. Yarn builds a memory of you
                  that grows over time. &quot;Based on what you told me in January...&quot;
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Pain Point 3: Reactive Treadmill */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <div>
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">The problem</div>
                <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
                  Your AI only works when you do.
                  <br />
                  <span className="text-[#1a1a1a]/50">Nothing happens while you sleep.</span>
                </h2>
                <p className="text-[#1a1a1a]/50 leading-relaxed mb-6">
                  You realized you forgot to follow up with a client for three weeks.
                  If only something had reminded you. Your AI waits—it never initiates.
                </p>
              </div>
              <div className="glass-card-light p-6">
                <div className="text-sm text-[#1a1a1a]/30 mb-4 font-mono uppercase tracking-wider">Yarn&apos;s approach</div>
                <h3 className="text-lg font-medium mb-3 text-[#1a1a1a]">AI that works while you sleep</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Schedule research. Get weekly digests. Wake up to insights
                  you didn&apos;t have to ask for. Work arrives on your schedule.
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

            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-[#1a1a1a]/10">
                    <th className="py-4 pr-4 text-sm font-medium text-[#1a1a1a]/50"></th>
                    <th className="py-4 px-4 text-sm font-medium text-[#1a1a1a]/50">ChatGPT</th>
                    <th className="py-4 px-4 text-sm font-medium text-[#1a1a1a]/50">Claude</th>
                    <th className="py-4 pl-4 text-sm font-medium text-[#1a1a1a]">Yarn</th>
                  </tr>
                </thead>
                <tbody className="text-sm">
                  <tr className="border-b border-[#1a1a1a]/5">
                    <td className="py-4 pr-4 text-[#1a1a1a]">Remembers across sessions</td>
                    <td className="py-4 px-4 text-[#1a1a1a]/40">Barely</td>
                    <td className="py-4 px-4 text-[#1a1a1a]/40">No</td>
                    <td className="py-4 pl-4 text-[#1a1a1a] font-medium">Yes</td>
                  </tr>
                  <tr className="border-b border-[#1a1a1a]/5">
                    <td className="py-4 pr-4 text-[#1a1a1a]">Keeps projects separate</td>
                    <td className="py-4 px-4 text-[#1a1a1a]/40">No</td>
                    <td className="py-4 px-4 text-[#1a1a1a]/40">Kinda</td>
                    <td className="py-4 pl-4 text-[#1a1a1a] font-medium">Yes</td>
                  </tr>
                  <tr className="border-b border-[#1a1a1a]/5">
                    <td className="py-4 pr-4 text-[#1a1a1a]">Works proactively</td>
                    <td className="py-4 px-4 text-[#1a1a1a]/40">No</td>
                    <td className="py-4 px-4 text-[#1a1a1a]/40">No</td>
                    <td className="py-4 pl-4 text-[#1a1a1a] font-medium">Yes</td>
                  </tr>
                  <tr>
                    <td className="py-4 pr-4 text-[#1a1a1a]">Shows where answers come from</td>
                    <td className="py-4 px-4 text-[#1a1a1a]/40">No</td>
                    <td className="py-4 px-4 text-[#1a1a1a]/40">No</td>
                    <td className="py-4 pl-4 text-[#1a1a1a] font-medium">Yes</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* Who It's For */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium mb-12 text-[#1a1a1a]">
              Built for people juggling multiple things
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="glass-card-light p-6">
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Consultants</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Keep your clients straight. Each client = separate project.
                  Never mix up context again.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Freelancers</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Remember every project. Context compounds over months.
                  Never start from scratch.
                </p>
              </div>

              <div className="glass-card-light p-6">
                <h3 className="text-base font-medium mb-2 text-[#1a1a1a]">Founders</h3>
                <p className="text-[#1a1a1a]/50 text-sm leading-relaxed">
                  Running five things at once? Each gets its own AI
                  that knows the full history.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-24 md:py-32">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-2xl md:text-3xl font-medium mb-6 text-[#1a1a1a]">
              Same price as ChatGPT Plus.
              <br />
              <span className="text-[#1a1a1a]/50">But Yarn actually remembers.</span>
            </h2>
            <p className="text-[#1a1a1a]/50 mb-4">
              Free tier: 1 project, 50 memories
            </p>
            <p className="text-[#1a1a1a]/50 mb-10">
              Pro: Unlimited everything — $19/mo
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
