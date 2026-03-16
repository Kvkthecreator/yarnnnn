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
          "yarnnn is an autonomous AI platform for recurring knowledge work. It connects to Slack, Gmail, Notion, and Calendar, then runs agents that produce real output in the background and improve with every cycle.",
      },
      {
        question: "What is the Orchestrator?",
        answer:
          "The Orchestrator is yarnnn's conversational interface. You use it to create agents, refine their output, and direct the system. It shares the same context and intelligence as your background agents.",
      },
      {
        question: "How is yarnnn different from ChatGPT or Claude?",
        answer:
          "Chat tools are session-centric — they reset every time. yarnnn is system-centric: it maintains synced work context, runs agents on schedule, and improves them over time through supervised feedback loops.",
      },
      {
        question: "Is yarnnn an AI agent platform?",
        answer:
          "yarnnn is focused on supervised autonomous work, not generic task automation. The core unit is the agent — a persistent entity with its own instructions, memory, sources, schedule, and run history.",
      },
    ],
  },
  {
    category: "Platforms & Data",
    items: [
      {
        question: "Which platforms does yarnnn connect to?",
        answer:
          "Slack, Gmail, Google Calendar, and Notion. You authorize via OAuth and choose which channels, labels, or pages to include.",
      },
      {
        question: "Is my data safe?",
        answer:
          "Yes. Data is encrypted in transit and at rest. OAuth tokens are encrypted. Access is user-scoped. You can change source selections or disconnect any integration at any time.",
      },
      {
        question: "What does yarnnn sync?",
        answer:
          "Only selected source content and metadata needed for context-aware generation. Sync behavior and cadence depend on your plan.",
      },
      {
        question: "Can yarnnn post or edit things in my tools?",
        answer:
          "No. Integrations are read-only for context ingestion. You stay in control of all output and delivery decisions.",
      },
    ],
  },
  {
    category: "Agents",
    items: [
      {
        question: "What are agents?",
        answer:
          "Agents are autonomous entities that produce output on a schedule. Each has its own instructions, memory, and sources. You supervise their runs from the dashboard.",
      },
      {
        question: "What kinds of agents can I create?",
        answer:
          "Common agent types include Recap (channel/label summaries), Meeting Prep (briefings from your calendar), Watch (monitoring for themes), Research (topic tracking with web search), and Summary (cross-platform synthesis).",
      },
      {
        question: "Do I have to create agents manually?",
        answer:
          "No. When you connect a platform, yarnnn automatically creates a matching agent — like a Slack Recap or Gmail Digest. You can also create agents through conversation with the Orchestrator.",
      },
      {
        question: "How do agents improve over time?",
        answer:
          "Each approved or edited run becomes signal for future execution. Agents learn your preferred structure, emphasis, and tone as they accumulate feedback.",
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
        question: "What are current agent limits?",
        answer:
          "Free supports 2 active agents. Pro supports 10.",
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
          "Sign up and connect one platform. yarnnn creates your first agent automatically. You can also ask the Orchestrator to create agents for topics or tasks — no platform needed.",
      },
      {
        question: "Do I need to configure everything up front?",
        answer:
          "No. Start with one platform and one agent. Expand as you build confidence in the output quality.",
      },
      {
        question: "What is the best first agent?",
        answer:
          "Most users start with a Slack Recap or Gmail Digest — these give fast value and create clean feedback signal for future improvements.",
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
