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

// ≤12 entries per SITE-COPY-SPEC-v1 §4.
const faqSections: FaqSection[] = [
  {
    category: "The difference",
    items: [
      {
        question: "How is this different from ChatGPT or Claude's memory?",
        answer:
          "Their memory is walled to their own app — you can't read inside it, version it, or take it with you. yarnnn is one memory that lives outside any single AI: every model reads and writes it, every change is signed and dated, and it's yours to export. Write it in Claude, and it's there in ChatGPT.",
      },
      {
        question: "Is my data mine?",
        answer:
          "Yes. Every file is attributed, every version is kept, and the whole thing is exportable and reachable from any AI over MCP. It's yours to own — and we never train on it.",
      },
      {
        question: "What is 'trace'?",
        answer:
          "Trace shows how any fact changed over time — who changed it, when, and what it was before. It's the thing a plain storage connector or an app's built-in memory can't show you: the full history behind what your AI knows.",
      },
      {
        question: "Does it work across my team, not just me?",
        answer:
          "Yes — the same memory can be written to by you, your teammates, your tools, and even your own AI agents, and you can always see who added what. Working solo is just the simplest case.",
      },
    ],
  },
  {
    category: "The work",
    items: [
      {
        question: "How do I put things in, and get them out?",
        answer:
          "Connect your tools (Slack, Notion, your files), or just tell any connected AI to remember something. Any other AI can then recall it on the next session — no copy-paste, no re-explaining who you are.",
      },
      {
        question: "Which AI models does it work with?",
        answer:
          "Any that speak MCP — ChatGPT, Claude, and others. It's neutral on purpose: it isn't tied to any one model, which is exactly why it can sit across all of them.",
      },
      {
        question: "What's the 'second set of eyes' I've seen mentioned?",
        answer:
          "That's the optional checker (in beta): an assistant that reviews important work before it goes out, against rules you set, and keeps a record of every call it makes. The memory is valuable on its own; the checker is an upgrade you turn on when you're ready.",
      },
    ],
  },
  {
    category: "Pricing & lifecycle",
    items: [
      {
        question: "What does it cost?",
        answer:
          "Your memory is free forever — your files, your context, reachable from any AI. You only pay when the optional assistant is working: pay-as-you-go, metered at transparent rates, drawn from a balance, with a hard stop at zero. No seats, no subscription, no feature gates. Every workspace starts with a $3 balance; top up from $10 when you need more.",
      },
      {
        question: "Can I cap what it spends?",
        answer:
          "Yes. Set a monthly ceiling (most start around $50; $100 and $150+ suit busier use), and the assistant paces itself to stay under it. It's a cap you set, not a charge we bill — you're only ever charged for what actually runs. Two guardrails: a ceiling you plan, and a floor (zero balance) that never lets anything break.",
      },
      {
        question: "What if my balance hits zero, or I turn the assistant off?",
        answer:
          "Nothing is deleted. At zero, the assistant pauses — top up to resume. Turn it off and it simply stops drawing usage. Either way, your memory and every file stay yours, free.",
      },
    ],
  },
  {
    category: "Getting started",
    items: [
      {
        question: "How do I start?",
        answer:
          "Start free. Connect an AI tool over MCP (or upload files, or just start typing), tell it something worth keeping, and watch it show up in the next AI you open — with the full history intact.",
      },
      {
        question: "What's the best first move?",
        answer:
          "Connect the two AIs you use most, and save one thing in one of them. Open the other and recall it. That round-trip — write once, there everywhere, fully traceable — is the whole idea in about thirty seconds.",
      },
    ],
  },
];

const allFaqItems = faqSections.flatMap((s) => s.items);

export const metadata = getMarketingMetadata({
  title: "FAQ — shared memory for AI + human work",
  description:
    "How yarnnn differs from ChatGPT and Claude memory, what 'trace' is, how it works across your AIs and your team, pricing, and how to get started.",
  path: "/faq",
  keywords: [
    "yarnnn faq",
    "shared ai memory faq",
    "cross-llm memory faq",
    "portable ai memory",
    "ai memory pricing faq",
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
              <p className="text-white/50 mb-8">Start free — save one thing in one AI and watch it show up in the next.</p>
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
