import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { getMarketingMetadata } from "@/lib/metadata";

interface FaqItem {
  question: string;
  answer: string;
}

interface FaqSection {
  category: string;
  items: FaqItem[];
}

const faqSections: FaqSection[] = [
  {
    category: "General",
    items: [
      {
        question: "What is yarnnn?",
        answer:
          "yarnnn is an autonomous AI work platform. It connects to Slack, Gmail, Notion, and Calendar, then runs deliverable specialists that produce real output for you in the background.",
      },
      {
        question: "What is TP (Thinking Partner)?",
        answer:
          "TP is yarnnn's interactive interface. You use TP to define deliverables, refine outputs, and supervise the system. TP and background execution share the same underlying context and intelligence.",
      },
      {
        question: "How is yarnnn different from ChatGPT or Claude?",
        answer:
          "Chat tools are primarily session-centric. yarnnn is system-centric: it maintains synced work context, runs scheduled or trigger-based deliverables, and improves those specialists over time through versioned supervision.",
      },
      {
        question: "Is yarnnn an AI agent platform?",
        answer:
          "yarnnn is focused on supervised autonomous work, not generic task automation. The core unit is the deliverable specialist with explicit type, mode, source scope, and version history.",
      },
    ],
  },
  {
    category: "Platforms & Data",
    items: [
      {
        question: "Which platforms does yarnnn connect to?",
        answer:
          "Slack, Gmail, Google Calendar, and Notion. You authorize via OAuth and choose source scope where applicable (channels, labels, pages).",
      },
      {
        question: "Is my data safe?",
        answer:
          "Yes. Data is encrypted in transit and at rest. OAuth tokens are encrypted. Access is user-scoped. You can change source selections or disconnect any integration at any time.",
      },
      {
        question: "What does yarnnn sync?",
        answer:
          "Only selected source content and metadata needed for context-aware generation. Sync behavior and cadence depend on your tier.",
      },
      {
        question: "Can yarnnn post or edit things in my tools?",
        answer:
          "No. Core integrations are read-oriented for context ingestion. You stay in control of approvals and delivery decisions.",
      },
    ],
  },
  {
    category: "Deliverables",
    items: [
      {
        question: "What are deliverables?",
        answer:
          "Deliverables are autonomous specialists that generate versioned outputs for recurring or triggered work. Each has its own instructions, memory, and source scope.",
      },
      {
        question: "Which deliverable types are supported?",
        answer:
          "Current intent-first types are: digest, brief, status, watch, deep_research, coordinator, and custom.",
      },
      {
        question: "Which execution modes are supported?",
        answer:
          "Modes are recurring, goal, reactive, proactive, and coordinator. Mode controls how and when a deliverable decides to run.",
      },
      {
        question: "How do deliverables improve over time?",
        answer:
          "Each approved/edit-reviewed version becomes signal for future runs. Specialists learn your preferred structure, emphasis, and tone as they execute.",
      },
    ],
  },
  {
    category: "Pricing & Plans",
    items: [
      {
        question: "What plans are available?",
        answer:
          "yarnnn has Free, Starter, and Pro plans. All plans include Slack, Gmail, Notion, and Calendar integration support.",
      },
      {
        question: "What are current deliverable limits?",
        answer:
          "Free supports 2 active deliverables, Starter supports 5, and Pro is unlimited.",
      },
      {
        question: "How does sync frequency scale by tier?",
        answer:
          "Free: 1x daily. Starter: 4x daily. Pro: hourly.",
      },
      {
        question: "How does source capacity scale by tier?",
        answer:
          "Limits scale by provider. For example: Slack sources are 5 (Free), 15 (Starter), unlimited (Pro). Similar scaling applies to Gmail and Notion.",
      },
    ],
  },
  {
    category: "Getting Started",
    items: [
      {
        question: "How do I get started?",
        answer:
          "Sign up, connect one platform, then define your first deliverable through TP or the deliverable UI. You can usually have a first run quickly.",
      },
      {
        question: "Do I need to configure everything up front?",
        answer:
          "No. Start with one specialist and one high-signal source. Expand type coverage and mode sophistication as you build confidence.",
      },
      {
        question: "What is the best first deliverable?",
        answer:
          "Most teams start with a recurring digest or status update. These give fast value and create clean supervision signal for future improvements.",
      },
    ],
  },
];

const allFaqItems = faqSections.flatMap((s) => s.items);

export const metadata = getMarketingMetadata({
  title: "FAQ",
  description:
    "Frequently asked questions about yarnnn: product model, integrations, deliverable types and modes, pricing, and getting started.",
  path: "/faq",
  keywords: [
    "yarnnn faq",
    "autonomous ai faq",
    "deliverable modes",
    "thinking partner faq",
    "context powered ai",
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
              Product model, integrations, pricing, and how to get meaningful autonomous output quickly.
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
              <p className="text-white/50 mb-8">Start with one deliverable, then expand from real usage signal.</p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  href="/auth/login"
                  className="inline-block px-8 py-3 bg-white text-black font-medium rounded-full hover:bg-white/90 transition-colors"
                >
                  Start for free
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
