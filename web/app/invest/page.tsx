import type { Metadata } from "next";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { SpotlightCard, BentoGrid } from "@/components/landing/SpotlightCard";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata: Metadata = getMarketingMetadata({
  title: "Invest — the accountability layer the platforms can't build",
  description:
    "Platforms build delegates; they won't build the layer that holds delegates accountable. yarnnn is the cumulative, accountable workspace with a neutral judgment seat — premium, high-ACV, expansion-led.",
  path: "/invest",
  keywords: [
    "yarnnn invest",
    "ai accountability layer",
    "ai judgment seat",
    "cumulative ai workspace",
    "model-agnostic ai infrastructure",
    "high-acv ai",
  ],
});

export default function InvestPage() {
  const investSchema = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: "Invest in yarnnn",
    description: metadata.description ?? undefined,
    url: `${BRAND.url}/invest`,
    isPartOf: {
      "@type": "WebSite",
      name: BRAND.name,
      url: BRAND.url,
    },
  };

  return (
    <div className="relative min-h-screen flex flex-col bg-[#0f1419] text-white overflow-x-hidden">
      <GrainOverlay variant="dark" />
      <ShaderBackgroundDark />

      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted />

        <main className="flex-1">
          {/* Hero — self-audit thesis */}
          <section className="max-w-4xl mx-auto px-6 py-24 md:py-32">
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-10 tracking-tight leading-[1.1]">
              Platforms build delegates.
              <br />
              <span className="text-white/50">
                They won&apos;t build the layer that holds them accountable.
              </span>
            </h1>
            <div className="max-w-2xl space-y-6 text-white/50">
              <p>
                For the same structural reason ratings agencies aren&apos;t run by the banks they
                rate: a platform judging its own model&apos;s agents has a self-audit problem. A
                neutral, model-agnostic judgment seat does not. Their economics want more autonomy
                with less friction; accountable autonomy <em>is</em> friction, productized.
              </p>
              <p>
                yarnnn is the workspace where the work you run is cumulative and every consequential
                call passes through a judgment seat with a track record. The substrate is the asset,
                the agents are the labor, the seat is the management, the artifacts are the
                dividends.
              </p>
              <p className="text-white font-medium">
                The composition is unoccupied: the memory category is funded but has no judgment
                layer; the agent category is exploding but has no owned substrate. The window for
                &ldquo;the accountable one&rdquo; is open now.
              </p>
            </div>
          </section>

          {/* Stage & traction (replaces the $500K/$5M/SAM raise card — no hard $ figures) */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">Stage &amp; traction</h2>

              <BentoGrid className="mb-12">
                <SpotlightCard variant="dark" className="md:col-span-3" spotlightColor="rgba(255,255,255,0.05)">
                  <div className="p-6 md:p-8">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Stage</div>
                    <p className="text-2xl md:text-3xl font-medium mb-3">Alpha — running on its own operations</p>
                    <p className="text-white/50 text-sm leading-relaxed">
                      Built operator-first and dogfooded against live programs. The calibration
                      loop is live in the alpha programs; the workspace, the judgment seat, the
                      delegation dial, and the attributed substrate all ship today.
                    </p>
                  </div>
                </SpotlightCard>
                <SpotlightCard variant="dark" className="md:col-span-3" spotlightColor="rgba(99,102,241,0.06)">
                  <div className="p-6 md:p-8">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Diligence surface</div>
                    <p className="text-2xl md:text-3xl font-medium mb-3">300+ decisions, in the open</p>
                    <p className="text-white/50 text-sm leading-relaxed">
                      Every architectural decision is recorded. The receipts culture is the
                      identity — and the diligence surface. Attribution is enforced at the write
                      path, not claimed in copy.
                    </p>
                  </div>
                </SpotlightCard>
              </BentoGrid>

              <p className="max-w-2xl text-white/40 text-sm">
                Raise terms and figures shared under the deck on request — the case here is
                structural: a composition the platforms face for reasons of incentive and position,
                not capability.
              </p>
            </div>
          </section>

          {/* The bifurcation — recast to the self-audit / cumulative-vs-episodic frame */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">The bifurcation</h2>
              <p className="text-white/50 mb-16 max-w-2xl">
                The platforms moved up the stack into work context in 2026 — scheduled delegates,
                persistent workspaces, memory marketed as improvement. That move <em>creates</em>{" "}
                the accountability gap rather than closing it: the more delegates ship, the bigger
                the question gets — who approved that, against what rules, and was the judgment any
                good?
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-12">
                <SpotlightCard variant="dark" spotlightColor="rgba(255,255,255,0.03)" spotlightSize={400}>
                  <div className="p-6 md:p-8">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-4">Grades its own homework</div>
                    <h3 className="text-xl font-medium mb-4">Platform delegates</h3>
                    <div className="space-y-3 text-white/50 text-sm">
                      <p>
                        The vendor that builds the delegate also grades it. Memory you can&apos;t
                        read; actions with no attributed trail; improvement on faith. And the work
                        stays episodic — every artifact generated fresh.
                      </p>
                      <div className="pt-3 border-t border-white/[0.06] text-white/30 text-xs">
                        <p>Capability parity is real and arrives in waves. Structure doesn&apos;t wash out.</p>
                      </div>
                    </div>
                  </div>
                </SpotlightCard>

                <SpotlightCard variant="dark" spotlightColor="rgba(99,102,241,0.08)" spotlightSize={400}>
                  <div className="p-6 md:p-8">
                    <div className="text-xs text-indigo-400/60 uppercase tracking-wider mb-4">Answers for what ships</div>
                    <h3 className="text-xl font-medium mb-4">The cumulative, accountable workspace</h3>
                    <div className="space-y-3 text-white/50 text-sm">
                      <p>
                        Owned, attributed substrate. Corrections compound. A neutral judgment seat
                        whose calls are reconciled against what actually happened. Work is
                        monotonically improving; the trail reads like a track record.
                      </p>
                      <div className="pt-3 border-t border-white/[0.06] text-xs">
                        <p className="text-white/60 font-medium">yarnnn — substrate, agents, the seat, the dial</p>
                        <p className="text-white/30">Model-agnostic neutrality by construction; theirs by impossibility.</p>
                      </div>
                    </div>
                  </div>
                </SpotlightCard>
              </div>

              <div className="max-w-2xl text-white/40 text-sm">
                <p>
                  Memory startups have the opposite problem: substrate ambitions but no operation —
                  context with no action loop is a wiki. Remove any one commitment from the
                  composition and it degrades to a known-inferior form.
                </p>
              </div>
            </div>
          </section>

          {/* The four properties — moat, enforced in code (Beat 5) */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">Enforced in code, not claimed in copy</h2>
              <p className="text-white/50 mb-12 max-w-2xl">
                Four properties give the moat its shape. The platforms face them for reasons of
                incentive and position, not capability.
              </p>

              <BentoGrid>
                {([
                  { title: "The loop closes against ground truth", desc: "Outcomes, costs, and calibration are written by the kernel, mechanically. The agent can't grade its own homework.", col: "md:col-span-3" },
                  { title: "Total attribution", desc: "Substrate can't be mutated anonymously — every revision is authored, parent-pointered, content-addressed. No incumbent context layer exposes this.", col: "md:col-span-3" },
                  { title: "The governance boundary holds", desc: "The agent can tune its cadence but cannot raise its own budget or loosen its own delegation. DIY stacks and platform agents have no equivalent.", col: "md:col-span-3" },
                  { title: "Per-workspace sovereignty", desc: "Your asset is yours; no cross-workspace learning; the blast radius is one operator.", col: "md:col-span-3" },
                ] as const).map((item) => (
                  <SpotlightCard key={item.title} variant="dark" className={item.col} spotlightSize={300}>
                    <div className="p-6">
                      <h3 className="text-base font-medium mb-2">{item.title}</h3>
                      <p className="text-white/40 text-sm leading-relaxed">{item.desc}</p>
                    </div>
                  </SpotlightCard>
                ))}
              </BentoGrid>
            </div>
          </section>

          {/* What's live — current canon */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-5xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">What&apos;s live</h2>

              <BentoGrid>
                <SpotlightCard variant="dark" className="md:col-span-4" spotlightColor="rgba(99,102,241,0.05)">
                  <div className="p-6 md:p-8">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Core product</div>
                    <h3 className="text-xl font-medium mb-3">The cumulative workspace + the judgment seat</h3>
                    <p className="text-white/50 text-sm leading-relaxed">
                      Authored substrate with attribution enforced at the write path; agents you own
                      that produce from it; a neutral Reviewer seat that evaluates consequential
                      actions and reconciles its calls against outcomes. The operation lives in the
                      cockpit; external distribution is the derivative last mile.
                    </p>
                  </div>
                </SpotlightCard>

                <SpotlightCard variant="dark" className="md:col-span-2" spotlightColor="rgba(14,165,233,0.05)">
                  <div className="p-6 h-full">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">The dial</div>
                    <h3 className="text-base font-medium mb-2">Delegation, priced and earned</h3>
                    <p className="text-white/50 text-xs leading-relaxed">
                      Manual → bounded → autonomous. The trust dial the operator controls is the
                      pricing axis — pay more as you delegate more. The governance boundary is held
                      in code.
                    </p>
                  </div>
                </SpotlightCard>

                <SpotlightCard variant="dark" className="md:col-span-2" spotlightColor="rgba(16,185,129,0.05)">
                  <div className="p-6 h-full">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">The loop</div>
                    <h3 className="text-base font-medium mb-2">Calibration against ground truth</h3>
                    <p className="text-white/50 text-xs leading-relaxed">
                      Outcomes reconcile against reality the agent cannot author; corrections and
                      calibration flow back into the substrate. Live in the alpha programs today.
                    </p>
                  </div>
                </SpotlightCard>

                <SpotlightCard variant="dark" className="md:col-span-2" spotlightColor="rgba(245,158,11,0.05)">
                  <div className="p-6 h-full">
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-3">Interoperability</div>
                    <h3 className="text-base font-medium mb-2">Model-agnostic, MCP-native</h3>
                    <p className="text-white/50 text-xs leading-relaxed">
                      The owned, attributed workspace is the system of record other agents read and
                      write through. The seat&apos;s jurisdiction grows with the ecosystem, not
                      against it.
                    </p>
                  </div>
                </SpotlightCard>
              </BentoGrid>
            </div>
          </section>

          {/* Investment thesis */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">Investment thesis</h2>
              <div className="max-w-2xl space-y-6 text-white/50">
                <p>
                  Work is shifting from human-first to agent-first — that&apos;s no longer a
                  prediction, it&apos;s the product news of 2026. As execution gets delegated, the
                  human contribution concentrates into exactly two things: the context only you have
                  and the judgment only you can authorize. Execution commoditizes; context and
                  judgment compound.
                </p>
                <p>
                  So the durable product isn&apos;t a better delegate — delegates are the commodity
                  layer now. It&apos;s the system where your context is an owned asset every delegate
                  draws from, and your judgment is an installed seat every consequential action
                  passes through, with a track record that proves whether it&apos;s any good.
                </p>
                <p className="text-white font-medium">
                  Positioning windows at platform velocity close in months, not years. The agent
                  flood is creating the accountability gap faster than anyone is filling it.
                </p>
              </div>
            </div>
          </section>

          {/* Motion (replaces "Market" / removes SAM/TAM) */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">Motion</h2>
              <p className="text-white/50 mb-12 max-w-2xl">
                The buyer is a psychographic, not an occupation: someone with something that&apos;s
                theirs to run, that they can&apos;t be continuously present for, and who refuses to
                let it reset — the operator of a bounded operation with a repeating consequential
                decision and a track record they&apos;re not learning from.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-12">
                {([
                  { title: "Premium, high-ACV", desc: "Priced per running operation, tiered by delegation level. The value is the call made correctly and the asset that compounds — not compute." },
                  { title: "Land narrow", desc: "Bounded operations with fast feedback loops — a portfolio, a channel, a pipeline, a shop, a book of business." },
                  { title: "Expansion-led", desc: "Grow through tight communities that talk to themselves. Hundreds of operators paying real money is a real business — never a volume play." },
                ] as const).map((item) => (
                  <SpotlightCard key={item.title} variant="dark" spotlightSize={280}>
                    <div className="p-6">
                      <h3 className="text-base font-medium mb-2">{item.title}</h3>
                      <p className="text-white/40 text-sm leading-relaxed">{item.desc}</p>
                    </div>
                  </SpotlightCard>
                ))}
              </div>

              <p className="text-white/50 max-w-2xl">
                The psychographic is senior, consequence-bearing, and scarce — low volume is the
                correct shape, not a limitation. The trust dial the operator already controls is the
                expansion path: pay more as you delegate more.
              </p>
            </div>
          </section>

          {/* Founder — operator biography, refreshed off retired product framing */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">Founder</h2>

              <div className="max-w-2xl space-y-6 text-white/50">
                <p className="text-white font-medium text-lg">
                  Kevin Kim &mdash; Solo Founder &amp; CEO
                </p>
                <p>
                  Korean-born, US-based. A decade of work spanning enterprise systems, cross-border
                  operations, and context architecture &mdash; from deploying CRM for Japan Tobacco in
                  post-military Myanmar to building GTM systems for cross-border sales teams.
                </p>
                <p>
                  Shipped the entire product solo: full-stack application (Next.js + FastAPI +
                  Supabase), platform integrations, the authored-substrate write path, the judgment
                  seat, and the calibration loop &mdash; documented across 300+ Architecture Decision
                  Records and run on its own operations before raising a dollar.
                </p>
              </div>
            </div>
          </section>

          {/* CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Let&apos;s talk.
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                If you&apos;re investing in AI infrastructure, the accountability layer, or the
                future of agent-first work &mdash; I&apos;d love to share the deck and walk through
                the architecture.
              </p>
              <a
                href="mailto:kvkthecreator@gmail.com"
                className="inline-block px-8 py-4 bg-white text-black text-lg font-medium rounded-full hover:bg-white/90 transition-colors"
              >
                kvkthecreator@gmail.com
              </a>
            </div>
          </section>
        </main>

        <LandingFooter inverted />
      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(investSchema) }}
      />
    </div>
  );
}
