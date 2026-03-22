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
          "yarnnn is an AI agent platform for recurring knowledge work. It connects to Slack, Gmail, Notion, and Calendar, then runs persistent agents in the background that deliver real work on schedule — recaps, briefs, research, reports — and improve with every cycle.",
      },
      {
        question: "How is yarnnn different from ChatGPT or Claude?",
        answer:
          "Chat tools are session-based — they help in the moment but reset when you close the tab. yarnnn is system-based: it maintains synced context from your work tools, runs agents on schedule without you, and learns from your feedback over time. The output gets better the longer it runs.",
      },
      {
        question: "What does \"autonomous\" mean here?",
        answer:
          "Agents run in the background on schedule — you don't need to prompt them. They pull fresh context from your connected tools, produce work, and deliver it. You review and redirect when needed. Over time, they require less supervision.",
      },
      {
        question: "What kind of work can agents do?",
        answer:
          "Common jobs include: weekly team updates from Slack, email triage and digests, meeting prep briefings, competitor monitoring, research tracking, and cross-platform status reports. Agents can also produce rich output like PDFs, slides, and spreadsheets.",
      },
    ],
  },
  {
    category: "Platforms & Data",
    items: [
      {
        question: "Which platforms does yarnnn connect to?",
        answer:
          "Slack, Gmail, Google Calendar, and Notion. You authorize via OAuth and choose which channels, labels, or pages to include — or let yarnnn auto-select based on your activity.",
      },
      {
        question: "Is my data safe?",
        answer:
          "Yes. Data is encrypted in transit and at rest. OAuth tokens are encrypted. Access is user-scoped. You can change source selections or disconnect any integration at any time.",
      },
      {
        question: "What does yarnnn sync?",
        answer:
          "Only selected source content and metadata needed for context-aware work. yarnnn reads from your tools — it does not post, edit, or modify anything in them. Delivery is separate and controlled by you.",
      },
    ],
  },
  {
    category: "Agents & How They Work",
    items: [
      {
        question: "Do I have to create agents manually?",
        answer:
          "No. When you connect a platform, yarnnn automatically creates agents matched to your workflow and starts running them. You can also create agents through conversation — just describe what you need in plain language.",
      },
      {
        question: "How do agents improve over time?",
        answer:
          "Every delivered, reviewed, or edited output becomes signal for future runs. Agents learn your preferred structure, emphasis, and tone. They also accumulate domain knowledge — understanding your team, projects, and communication patterns more deeply with each cycle.",
      },
      {
        question: "Can multiple agents work together?",
        answer:
          "Yes. For bigger jobs, multiple agents can collaborate — one pulls from Slack, another from Gmail, another does research. A coordinator agent assembles their work into one polished deliverable. You get a finished product, not fragments.",
      },
      {
        question: "Can I talk to agents directly?",
        answer:
          "Yes. Each agent has a meeting room where you can give direction, ask questions, or redirect their focus. Your instructions persist across sessions — agents remember what you told them.",
      },
      {
        question: "What output formats are available?",
        answer:
          "Agents can produce plain text, email-ready content, PDFs, slide decks (PPTX), spreadsheets (XLSX), charts, and more. The format depends on the job — a weekly digest might be email, while a leadership report might be a PDF or slides.",
      },
    ],
  },
  {
    category: "Pricing & Plans",
    items: [
      {
        question: "What plans are available?",
        answer:
          "yarnnn has Free and Pro plans. Both include all four platform integrations. Free gives you 2 agents, 50 messages/month, and daily sync. Pro gives you 10 agents, unlimited messages, hourly sync, and unlimited sources — $19/mo (Early Bird: $9/mo).",
      },
      {
        question: "What are work units?",
        answer:
          "Work units measure autonomous work — agent runs, report assemblies, and rendered output. Free includes 60 work units/month, Pro includes 1,000. This is separate from messages (your conversations with agents).",
      },
      {
        question: "How does sync frequency differ by plan?",
        answer:
          "Free: once daily. Pro: hourly. Faster sync means agents work with fresher context.",
      },
    ],
  },
  {
    category: "Getting Started",
    items: [
      {
        question: "How do I get started?",
        answer:
          "Sign up and connect one platform. yarnnn creates your first agents automatically and starts working. No configuration required — you can refine later.",
      },
      {
        question: "What is the best first agent?",
        answer:
          "Most users start with a Slack or Gmail recap. These give fast, visible value and create clean feedback signal for the system to learn from.",
      },
      {
        question: "How quickly do I see results?",
        answer:
          "Your first agent output is typically ready within minutes of connecting a platform. From there, quality improves with every cycle as agents accumulate context and learn from your feedback.",
      },
    ],
  },
];

const allFaqItems = faqSections.flatMap((s) => s.items);

export const metadata = getMarketingMetadata({
  title: "FAQ",
  description:
    "Frequently asked questions about yarnnn: how agents work, platform integrations, pricing, output formats, and getting started.",
  path: "/faq",
  keywords: [
    "yarnnn faq",
    "autonomous ai faq",
    "ai agent faq",
    "work agents faq",
    "ai employee faq",
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
              How agents work, what they can do, pricing, and how to get useful output fast.
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
              <p className="text-white/50 mb-8">Start with one agent — you&apos;ll see results in minutes.</p>
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
