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
        question: "What is yarnnn in simple terms?",
        answer:
          "yarnnn is an AI assistant that does recurring work for you. You connect your tools, it prepares drafts, and you approve them.",
      },
      {
        question: "What is TP (Thinking Partner)?",
        answer:
          "TP is the chat interface inside yarnnn. You talk to it like a teammate to set things up, ask questions, and improve drafts.",
      },
      {
        question: "How is this different from ChatGPT or Claude?",
        answer:
          "Those tools are great for one-off prompts. yarnnn is built for recurring work. It uses your connected tools and keeps improving from your edits over time.",
      },
      {
        question: "Do I need to understand technical AI concepts?",
        answer:
          "No. Most people just describe the task they want done and review the output. Advanced settings are optional.",
      },
    ],
  },
  {
    category: "Platforms & Data",
    items: [
      {
        question: "Which tools can I connect?",
        answer:
          "Slack, Gmail, Google Calendar, and Notion.",
      },
      {
        question: "Can yarnnn send emails or post messages for me?",
        answer:
          "No. Core integrations are read-focused for context. You stay in control of final approval and sending.",
      },
      {
        question: "Is my data secure?",
        answer:
          "Yes. Data is encrypted in transit and at rest. Access is tied to your account, and you can disconnect tools anytime.",
      },
      {
        question: "Can I choose what yarnnn reads?",
        answer:
          "Yes. You can choose channels, labels, and pages so yarnnn only uses relevant content.",
      },
    ],
  },
  {
    category: "Workflows",
    items: [
      {
        question: "What kind of work can yarnnn do?",
        answer:
          "Weekly updates, meeting prep, status reports, and other repeated writing tasks based on your work tools.",
      },
      {
        question: "Do I need to set up complicated rules?",
        answer:
          "No. Start with a simple schedule like once a week. You can add more control later if needed.",
      },
      {
        question: "How does it get better over time?",
        answer:
          "When you edit or approve drafts, yarnnn learns your style and priorities. Future drafts are closer to what you want.",
      },
      {
        question: "Can I always review before anything is final?",
        answer:
          "Yes. The default model is supervised: yarnnn drafts, you review and approve.",
      },
    ],
  },
  {
    category: "Pricing",
    items: [
      {
        question: "What plans are available?",
        answer:
          "Free, Starter, and Pro.",
      },
      {
        question: "What are current workflow limits?",
        answer:
          "Free: 2 active workflows. Starter: 5 active workflows. Pro: unlimited.",
      },
      {
        question: "How often does yarnnn sync my tools?",
        answer:
          "Free: once daily. Starter: four times daily. Pro: hourly.",
      },
      {
        question: "Do all plans include tool connections?",
        answer:
          "Yes. Slack, Gmail, Notion, and Calendar are available on all plans.",
      },
    ],
  },
  {
    category: "Getting Started",
    items: [
      {
        question: "What should I do first?",
        answer:
          "Connect one tool, then ask for one weekly draft. Start small and build from there.",
      },
      {
        question: "How fast will I see value?",
        answer:
          "Usually right away. You can get a first draft quickly after setup.",
      },
      {
        question: "Best first use case?",
        answer:
          "A weekly update is the easiest place to start because it is simple, recurring, and easy to review.",
      },
    ],
  },
];

const allFaqItems = faqSections.flatMap((s) => s.items);

export const metadata = getMarketingMetadata({
  title: "FAQ",
  description:
    "Simple answers about how yarnnn works, what it connects to, pricing, and how to get started quickly.",
  path: "/faq",
  keywords: [
    "yarnnn faq",
    "ai for work faq",
    "workflow automation faq",
    "thinking partner faq",
    "autonomous ai faq",
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
              Straight answers on setup, pricing, and what yarnnn can do for you.
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
              <p className="text-white/50 mb-8">Start with one weekly workflow and adjust from real usage.</p>
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
