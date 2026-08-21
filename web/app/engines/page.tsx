import Link from "next/link";
import { ArrowUpRight, Gauge, Scale, Wallet } from "lucide-react";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

/**
 * The engines page — a reference for members choosing an engine.
 *
 * WHY THIS PAGE EXISTS: the chat door offers engines by name and availability
 * only (`/api/lanes` → `models[]`: id, label, vision, available). A member
 * deciding between Claude Sonnet, GPT-5 and Gemini Flash has no basis in the
 * product to choose. This is that basis.
 *
 * ⭐ THE MAINTENANCE CONTRACT — the reason this page is shaped the way it is:
 * it names NO model, quotes NO price, and ranks NOTHING. Every volatile fact
 * is behind an outbound link to a source that maintains it professionally.
 * What stays here is the SHAPE of the tradeoff, which does not change when a
 * provider ships a model or cuts a price. A page that ranked engines would be
 * wrong within weeks and would rot INVISIBLY — nothing breaks, it just quietly
 * becomes false. Do not add a comparison table, a "best for X" list, or a
 * price. If you want the reader to know a number, link to whoever keeps it.
 *
 * ADR-490 §1② (as amended): no surface advertises "cost + α". This page does
 * not — it neither states the platform margin nor positions yarnnn on price.
 * It points outward at capability and cost, which is the question a member
 * actually has, and inward at their own usage, which is the only benchmark
 * that reflects their real work.
 *
 * The provider list is the four in `LANE_MODELS` (lane_runner.py). If an
 * engine from a new provider is offered, add it here; the list is providers,
 * not models, precisely so a model release does not touch this file.
 */

export const metadata = getMarketingMetadata({
  title: "Choosing an engine",
  description:
    "yarnnn runs your work on engines from several providers. How to think about the cost-versus-capability tradeoff, and where to find the current numbers.",
  path: "/engines",
  keywords: [
    "AI model comparison",
    "cost vs intelligence LLM",
    "choose an AI model",
    "multi-model AI workspace",
    "LLM pricing comparison",
  ],
});

// The axes a member actually trades off. Deliberately not a ranking — these
// are the questions to ask, not the answers, because the answers expire.
const AXES = [
  {
    icon: Scale,
    label: "Capability",
    detail:
      "How well an engine handles reasoning, long context, and nuance. Matters most on judgment work; matters least on routine extraction.",
  },
  {
    icon: Wallet,
    label: "Cost",
    detail:
      "What a provider charges per token, in and out. The spread between the cheapest and most capable engines is large — often more than an order of magnitude.",
  },
  {
    icon: Gauge,
    label: "Speed",
    detail:
      "How fast the first and last token arrive. A faster engine can be worth more than a smarter one on work you are waiting on.",
  },
];

// Third-party source that MAINTAINS these numbers. We link rather than
// paraphrase: a paraphrase is a snapshot that rots silently, and this is
// maintained by people whose job it is.
//
// Deliberately ONE benchmark, not a shortlist. A leaderboard we neither run
// nor audit is a claim we cannot stand behind; naming several implies we
// vetted the set. One source that plots capability against price answers the
// member's actual question, and the provider rate cards below are primary.
const SOURCES = [
  {
    name: "Artificial Analysis",
    href: "https://artificialanalysis.ai/",
    detail:
      "Independent benchmarks plotting intelligence against price and speed, across providers. The closest thing to a direct cost-to-intelligence chart.",
  },
];

// Providers whose engines yarnnn offers — the set in LANE_MODELS. Providers,
// not models: a model release must never require an edit here, but a new
// PROVIDER must (gate-enforced in engines-page-providers.test.mjs). Never
// hand-count them in this comment — a written tally goes stale the next time
// the roster grows and reads as correct while it lies.
const PROVIDERS = [
  { name: "Anthropic", href: "https://www.anthropic.com/pricing#api" },
  { name: "OpenAI", href: "https://openai.com/api/pricing/" },
  { name: "Google", href: "https://ai.google.dev/pricing" },
  { name: "DeepSeek", href: "https://api-docs.deepseek.com/quick_start/pricing" },
  { name: "xAI", href: "https://docs.x.ai/docs/models" },
];

export default function EnginesPage() {
  const schema = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: "Choosing an engine",
    url: `${BRAND.url}/engines`,
    description: metadata.description,
    dateModified: "2026-08-19",
  };

  return (
    <div className="min-h-screen bg-[#faf8f5] text-[#1a1a1a]">
      <LandingHeader />

      <main>
        {/* Hero */}
        <section className="px-6 pt-20 pb-16 md:pt-28">
          <div className="mx-auto max-w-3xl text-center">
            <h1 className="text-3xl font-medium leading-[1.15] tracking-tight md:text-5xl">
              Choosing an engine.
            </h1>
            <p className="mx-auto mt-6 max-w-xl text-lg leading-8 text-[#1a1a1a]/55 font-light">
              yarnnn runs your work on engines from several providers, and lets you pick
              per conversation. Here is how to think about the choice — and where to find
              the current numbers, which we don&apos;t keep ourselves.
            </p>
          </div>

          <div className="mx-auto mt-14 grid max-w-4xl gap-4 sm:grid-cols-3">
            {AXES.map((axis) => {
              const Icon = axis.icon;
              return (
                <div
                  key={axis.label}
                  className="rounded-xl border border-[#1a1a1a]/[0.08] bg-white/70 p-5 text-center"
                >
                  <div className="mx-auto mb-4 flex h-11 w-11 items-center justify-center rounded-full bg-[#1a1a1a]/[0.04]">
                    <Icon className="h-5 w-5 text-[#1a1a1a]/70" aria-hidden="true" />
                  </div>
                  <p className="text-sm font-medium">{axis.label}</p>
                  <p className="mt-1.5 text-xs leading-5 text-[#1a1a1a]/45">{axis.detail}</p>
                </div>
              );
            })}
          </div>
        </section>

        {/* The prose */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-16 md:py-20">
          <div className="mx-auto max-w-2xl space-y-12">
            <div>
              <h2 className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-[#de5a2b]">
                Why we don&apos;t rank them here
              </h2>
              <p className="leading-7 text-[#1a1a1a]/70">
                Any ranking we published would be out of date within weeks, and it would
                go out of date quietly — a stale comparison table looks exactly like a
                current one. Providers ship new models and change prices on their own
                schedule. So we point you at the people who track this properly, and keep
                this page to the part that doesn&apos;t move.
              </p>
            </div>

            <div>
              <h2 className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-[#de5a2b]">
                The part that doesn&apos;t move
              </h2>
              <p className="mb-5 leading-7 text-[#1a1a1a]/70">
                More capable engines cost more per token. That much is stable. What
                surprises people is that the cheapest engine is not always the cheapest
                outcome:
              </p>
              <ul className="space-y-4 text-[#1a1a1a]/70">
                <li className="leading-7">
                  <strong className="font-medium text-[#1a1a1a]">
                    A weaker engine can cost more.
                  </strong>{" "}
                  If it needs three attempts, or produces work you rewrite by hand, the
                  cheaper per-token rate buys you a more expensive result. Difficulty is
                  what should pick the engine, not the price list.
                </li>
                <li className="leading-7">
                  <strong className="font-medium text-[#1a1a1a]">
                    Length drives cost more than choice of engine.
                  </strong>{" "}
                  A long conversation on a cheap engine can outspend a short one on an
                  expensive engine. What you send matters as much as who you send it to.
                </li>
                <li className="leading-7">
                  <strong className="font-medium text-[#1a1a1a]">
                    Routine work rarely needs the top engine.
                  </strong>{" "}
                  Extracting fields, reformatting, summarising something short — the gap
                  between engines narrows as the task gets more mechanical, while the
                  price gap stays wide.
                </li>
              </ul>
            </div>

            <div>
              <h2 className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-[#de5a2b]">
                Where the current numbers live
              </h2>
              <p className="mb-5 leading-7 text-[#1a1a1a]/70">
                This is independent of us. We don&apos;t reproduce their figures, because
                a copy is a snapshot and theirs are maintained.
              </p>
              <div className="space-y-3">
                {SOURCES.map((source) => (
                  <a
                    key={source.name}
                    href={source.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group flex items-start gap-3 rounded-xl border border-[#1a1a1a]/[0.08] bg-white/70 p-5 transition-colors hover:border-[#1a1a1a]/20"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium">
                        {source.name}
                        <ArrowUpRight
                          className="ml-1 inline h-3.5 w-3.5 text-[#1a1a1a]/40 transition-transform group-hover:-translate-y-0.5"
                          aria-hidden="true"
                        />
                      </p>
                      <p className="mt-1.5 text-xs leading-5 text-[#1a1a1a]/45">
                        {source.detail}
                      </p>
                    </div>
                  </a>
                ))}
              </div>
              <p className="mt-5 leading-7 text-[#1a1a1a]/70">
                For rates straight from the source, each provider publishes its own:{" "}
                {PROVIDERS.map((p, i) => (
                  <span key={p.name}>
                    <a
                      href={p.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline underline-offset-4 decoration-[#1a1a1a]/20 hover:decoration-[#1a1a1a]/60"
                    >
                      {p.name}
                    </a>
                    {i < PROVIDERS.length - 2 ? ", " : i === PROVIDERS.length - 2 ? " and " : "."}
                  </span>
                ))}
              </p>
            </div>

            <div>
              <h2 className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-[#de5a2b]">
                Your own workspace is the better benchmark
              </h2>
              <p className="leading-7 text-[#1a1a1a]/70">
                Benchmarks tell you how engines compare in general. They can&apos;t tell you
                what <em>your</em> work costs, which depends on how you write, how long
                your conversations run, and what you ask for. Your Usage screen breaks
                spending down by engine over your own history — for deciding what to use
                tomorrow, that beats any leaderboard.
              </p>
              <p className="mt-5 leading-7 text-[#1a1a1a]/70">
                You can change engine per conversation, so the cost of guessing wrong is
                one conversation. See{" "}
                <Link
                  href="/pricing"
                  className="underline underline-offset-4 decoration-[#1a1a1a]/20 hover:decoration-[#1a1a1a]/60"
                >
                  pricing
                </Link>{" "}
                for how usage draws your balance.
              </p>
            </div>
          </div>
        </section>
      </main>

      <LandingFooter />

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
      />
    </div>
  );
}
