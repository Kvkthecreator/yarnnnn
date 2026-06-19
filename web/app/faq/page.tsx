import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { getMarketingMetadata } from "@/lib/metadata";
import { CTA } from "@/lib/cta";

interface FaqItem {
  question: string;
  answer: string;
}

interface FaqSection {
  category: string;
  items: FaqItem[];
}

// ≤12 entries per SITE-COPY-SPEC-v1 §4. Competitive lines are GTM v4 §4 verbatim.
const faqSections: FaqSection[] = [
  {
    category: "The difference",
    items: [
      {
        question: "How is this different from ChatGPT, Claude, or Cowork?",
        answer:
          "Concede the capability parity plainly: they have scheduled delegates, persistent workspaces, and memory marketed as improvement. What they structurally lack is owned, attributed substrate and an independent judgment seat — because the vendor that builds the delegate also grades it. They grade their own homework. Your seat here has a track record you can read.",
      },
      {
        question: "Is my data mine?",
        answer:
          "Yes, structurally. Every file is attributed; every revision is kept; the workspace is exportable and reachable from other AIs via MCP. The workspace is the asset — and we never train on it. Memory remembers; this owns, attributes, and answers for what it produces.",
      },
      {
        question: "What's an operation? What's a program?",
        answer:
          "An operation is an activated program running on your workspace — your newsletter operation, your portfolio operation. A program declares what the operation watches, produces, and counts as ground truth. Each operation runs on its own seat with its own delegation dial. The workspace itself is never paid.",
      },
      {
        question: "What does the Reviewer actually do?",
        answer:
          "It's the judgment seat. It evaluates consequential actions against the principles you authored, returns a verdict with reasoning, and reconciles past calls against what actually happened — the trail is the proof. Not a content filter. An approval button isn't judgment; judgment has a track record.",
      },
    ],
  },
  {
    category: "The work",
    items: [
      {
        question: "Can it write my newsletter for me?",
        answer:
          "It drafts, researches, and runs the operation around the work — but what ships under your name is yours to approve. For work where being you is the product, it's the desk, not the byline. The value it adds is the cumulative substrate underneath: provenance, consistency, and corrections that carry forward.",
      },
      {
        question: "Which model powers it?",
        answer:
          "Model-agnostic by design. The seat's value depends on its independence — a platform refereeing its own model's agents has a self-audit problem a neutral seat doesn't. Judgments are calibrated against outcomes, not against a vendor's say-so.",
      },
      {
        question: "Is this autonomous trading? Is this financial advice?",
        answer:
          "No, and no. There are no performance claims and no advice here. You author the rules; the seat enforces them; execution is paper-first. You decide how much it may do without you, and the trail shows you everything.",
      },
    ],
  },
  {
    category: "Pricing & lifecycle",
    items: [
      {
        question: "What does it cost?",
        answer:
          "The workspace is free forever — your files, your context, reachable from any AI. It's pay-as-you-go: when you run an operation, you pay only the usage it draws, metered at transparent rates and read line by line, with a hard stop at zero. No seats, no subscription, no feature gates. Every workspace starts with a $3 balance; top up from $10 when you need more.",
      },
      {
        question: "What happens when my balance hits zero, or I stop running an operation?",
        answer:
          "Nothing is deleted. If the balance hits zero, the operation pauses — top up to resume. If you stop running an operation, it simply stops drawing usage. In every case the workspace and every file remain yours, free.",
      },
    ],
  },
  {
    category: "Getting started",
    items: [
      {
        question: "How do I start?",
        answer:
          "Start free on the bare workspace. Pick a program (or stay bare), write the constitution — what it's for, the rules it judges by, how much it may do alone — connect your platforms and bring in your reality, and watch the first artifact synthesize from your context with full provenance.",
      },
      {
        question: "What's the best first move?",
        answer:
          "Author your context and run one artifact, so you see the provenance and the correction loop firsthand — or bring an existing history and watch the seat reconcile it into a calibration trail. Either way, the asset exists on day one and compounds from there.",
      },
    ],
  },
];

const allFaqItems = faqSections.flatMap((s) => s.items);

export const metadata = getMarketingMetadata({
  title: "FAQ — the accountable, cumulative AI workspace",
  description:
    "How yarnnn differs from ChatGPT, Claude, and Cowork; what an operation is; what the judgment seat does; pricing; and how to get started.",
  path: "/faq",
  keywords: [
    "yarnnn faq",
    "accountable ai faq",
    "ai judgment seat faq",
    "cumulative ai workspace faq",
    "ai operation pricing faq",
  ],
});

export default function FaqPage() {
  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: allFaqItems.map((item) => ({
      "@type": "Question",
      name: item.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: item.answer,
      },
    })),
  };

  return (
    <div className="relative min-h-screen flex flex-col bg-[#0f1419] text-white overflow-x-hidden">
      <GrainOverlay variant="dark" />
      <ShaderBackgroundDark />

      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted />

        <main className="flex-1">
          <section className="max-w-3xl mx-auto px-6 py-24 md:py-32">
            <h1 className="text-4xl md:text-5xl font-medium mb-4 tracking-tight leading-[1.1]">
              Frequently asked questions
            </h1>
            <p className="text-white/50 mb-16 max-w-xl">
              The difference, the work, pricing and lifecycle, and how to get started.
            </p>

            <div className="space-y-16">
              {faqSections.map((section) => (
                <div key={section.category}>
                  <h2 className="text-xs text-white/30 uppercase tracking-widest mb-8">{section.category}</h2>

                  <div className="space-y-8">
                    {section.items.map((item) => (
                      <div key={item.question} className="border-b border-white/5 pb-8 last:border-0">
                        <h3 className="text-lg font-medium mb-3">{item.question}</h3>
                        <p className="text-white/50 leading-relaxed">{item.answer}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-24 text-center">
              <h2 className="text-2xl font-medium mb-4">Still have questions?</h2>
              <p className="text-white/50 mb-8">Start free on the workspace and watch the first artifact compound.</p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  href={CTA.signup}
                  className="inline-block px-8 py-3 bg-white text-black font-medium rounded-full hover:bg-white/90 transition-colors"
                >
                  Start free
                </Link>
                <a
                  href="mailto:admin@yarnnn.com"
                  className="inline-block px-8 py-3 border border-white/20 text-white font-medium rounded-full hover:bg-white/10 transition-colors"
                >
                  Contact us
                </a>
              </div>
            </div>
          </section>
        </main>

        <LandingFooter inverted />
      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }}
      />
    </div>
  );
}
