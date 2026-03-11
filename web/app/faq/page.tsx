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
          "yarnnn is an autonomous AI work platform. It connects to Slack, Gmail, Notion, and Calendar, then runs agent specialists that produce real output for you in the background.",
      },
      {
        question: "What is TP Chat?",
        answer:
          "TP Chat is yarnnn's interactive surface — your single contact point for all work. You use it to define work-agents, refine their output, and supervise the system. TP Chat and background work-agents share the same underlying context and intelligence.",
      },
      {
        question: "How is yarnnn different from ChatGPT or Claude?",
        answer:
          "Chat tools are session-centric — they reset every time. yarnnn is system-centric: it maintains synced work context, runs scheduled or trigger-based work-agents, and improves those specialists over time through supervised runs.",
      },
      {
        question: "Is yarnnn an AI agent platform?",
        answer:
          "yarnnn is focused on supervised autonomous work, not generic task automation. The core unit is the work-agent — a specialist with explicit type, mode, source scope, and run history.",
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
    category: "Work-Agents",
    items: [
      {
        question: "What are work-agents?",
        answer:
          "Work-agents are autonomous specialists that produce output on a schedule or trigger. Each has its own instructions, memory, and source scope. You supervise their runs through TP Chat.",
      },
      {
        question: "Which agent types are supported?",
        answer:
          "Current intent-first types are: digest, brief, status, watch, deep_research, coordinator, and custom.",
      },
      {
        question: "Which execution modes are supported?",
        answer:
          "Modes are recurring, goal, reactive, proactive, and coordinator. Mode controls how and when an agent decides to run.",
      },
      {
        question: "How do work-agents improve over time?",
        answer:
          "Each approved or edited run becomes signal for future execution. Work-agents learn your preferred structure, emphasis, and tone as they accumulate feedback.",
      },
    ],
  },
  {
    category: "Pricing & Plans",
    items: [
      {
        question: "What plans are available?",
        answer:
          "yarnnn has Free and Pro plans. Both include Slack, Gmail, Notion, and Calendar integration. Pro adds unlimited messages, more agents, faster sync, and unlimited sources.",
      },
      {
        question: "What are current work-agent limits?",
        answer:
          "Free supports 2 active work-agents. Pro supports 10.",
      },
      {
        question: "How does sync frequency differ by plan?",
        answer:
          "Free: 1x daily. Pro: hourly.",
      },
      {
        question: "How does source capacity differ by plan?",
        answer:
          "Free: 5 Slack channels, 5 Gmail labels, 10 Notion pages. Pro: unlimited across all platforms.",
      },
    ],
  },
  {
    category: "Getting Started",
    items: [
      {
        question: "How do I get started?",
        answer:
          "Sign up, connect one platform, then define your first work-agent through TP Chat or the work-agents UI. You can usually have a first run quickly.",
      },
      {
        question: "Do I need to configure everything up front?",
        answer:
          "No. Start with one specialist and one high-signal source. Expand type coverage and mode sophistication as you build confidence.",
      },
      {
        question: "What is the best first work-agent?",
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
    "Frequently asked questions about yarnnn: product model, integrations, agent types and modes, pricing, and getting started.",
  path: "/faq",
  keywords: [
    "yarnnn faq",
    "autonomous ai faq",
    "agent modes",
    "work agents faq",
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
              <p className="text-white/50 mb-8">Start with one agent, then expand from real usage signal.</p>
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
