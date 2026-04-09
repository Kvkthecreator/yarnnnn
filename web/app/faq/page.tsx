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
          "yarnnn is an autonomous agent platform for recurring knowledge work. It keeps shared workspace context, a scaffolded workforce, Thinking Partner, and recurring task execution inside one system.",
      },
      {
        question: "How is yarnnn different from ChatGPT or Claude?",
        answer:
          "Chat tools are session-based — they help in the moment but reset when you close the tab. yarnnn is system-based: you have persistent agents with memory that run tasks on schedule, sync context from your work tools, and learn from your feedback over time. The output gets better the longer it runs.",
      },
      {
        question: "What does \"autonomous\" mean here?",
        answer:
          "Tasks run on schedule or by trigger without you re-prompting from zero. Agents pull fresh context, execute the work, and deliver outputs. You review and redirect when needed.",
      },
      {
        question: "What's the difference between agents, bots, and tasks?",
        answer:
          "Agents are persistent specialists that deepen over time. Platform bots are agents shaped around a specific system such as Slack, Notion, or GitHub. Tasks are the work units: an objective, cadence, delivery target, and assignment. Thinking Partner is the meta-cognitive agent that manages the system.",
      },
    ],
  },
  {
    category: "Workforce",
    items: [
      {
        question: "Do I have to create agents manually?",
        answer:
          "No. yarnnn scaffolds a workforce at signup. Most of the time you create tasks, not agents. Thinking Partner turns plain-language requests into recurring work.",
      },
      {
        question: "What agents do I get?",
        answer:
          "The current scaffolded roster includes five domain stewards (Competitive Intelligence, Market Research, Business Development, Operations, Marketing), one synthesizer (Reporting), three platform bots (Slack, Notion, GitHub), and Thinking Partner.",
      },
      {
        question: "How do agents improve over time?",
        answer:
          "Every task run, review, and edit becomes signal for future work. Agents learn your preferred structure, emphasis, and tone. They also accumulate domain knowledge — understanding your team, competitive landscape, and communication patterns more deeply with each cycle.",
      },
      {
        question: "Can multiple agents work together on a task?",
        answer:
          "Yes. Most tasks use one agent. For bigger jobs, multiple agents contribute domain expertise to a single task. For example, Slack Bot can keep internal context fresh, Competitive Intelligence can add external signals, and Reporting can synthesize one deliverable.",
      },
      {
        question: "How do I steer the system?",
        answer:
          "Thinking Partner is the main control surface. Use it to create work, change priorities, refine objectives, and ask why something ran. The Work and Agents surfaces let you inspect outputs, history, and the specialists involved.",
      },
    ],
  },
  {
    category: "Tasks",
    items: [
      {
        question: "What kinds of tasks can I assign?",
        answer:
          "Common tasks include: weekly team recaps from Slack, competitor intelligence briefs, status reports as PDF, Notion page summaries, research deep dives, meeting prep briefs, and cross-platform synthesis reports. Tasks can produce plain text, email, PDFs, slides (PPTX), spreadsheets (XLSX), and charts.",
      },
      {
        question: "What are the different task modes?",
        answer:
          "Three modes: Recurring (runs on a cadence indefinitely — daily, weekly, monthly), Goal (bounded, runs until success criteria are met), and Reactive (on-demand or event-triggered, like a meeting prep brief you request before a specific meeting).",
      },
      {
        question: "How do I create a task?",
        answer:
          "Describe what you need in plain language — for example, \"Give me a weekly competitor brief\" or \"Summarize #engineering every Friday as a PDF.\" TP creates the task definition, assigns the right agent or process, sets the cadence, and starts executing.",
      },
    ],
  },
  {
    category: "Platforms & Data",
    items: [
      {
        question: "Which platforms does yarnnn connect to?",
        answer:
          "Slack and Notion are the main public integrations today, with GitHub also represented in the scaffolded workforce model. You authorize via OAuth and choose which sources to include, or let yarnnn start with sensible defaults.",
      },
      {
        question: "Do I need to connect a platform to start?",
        answer:
          "No. Your agents can work with web research and documents alone. Platform connections enrich context but aren't required. You can connect Slack or Notion anytime and your agents will immediately start benefiting from the synced data.",
      },
      {
        question: "Is my data safe?",
        answer:
          "Yes. Data is encrypted in transit and at rest. OAuth tokens are encrypted. Access is user-scoped. yarnnn reads from your tools — it does not post, edit, or modify anything in them. You can change source selections or disconnect any integration at any time.",
      },
    ],
  },
  {
    category: "Pricing & Plans",
    items: [
      {
        question: "What plans are available?",
        answer:
          "yarnnn has Free and Pro plans. Both include the scaffolded workforce, Thinking Partner, and platform integrations. Free gives you 2 active tasks, 20 work credits/month, 150 messages/month, and daily sync. Pro gives you 10 active tasks, 500 work credits/month, unlimited messages, hourly sync, and unlimited sources — $19/mo (Early Bird: $9/mo).",
      },
      {
        question: "What does \"active tasks\" mean?",
        answer:
          "Tasks are the recurring work contracts the system keeps alive at once. Your scaffolded workforce is still there, but the tier determines how many active loops you can keep running simultaneously.",
      },
      {
        question: "What are work credits?",
        answer:
          "Work credits meter autonomous execution and rendering. They are separate from messages with Thinking Partner. Free includes 20 credits/month, Pro includes 500.",
      },
      {
        question: "How does sync frequency differ by plan?",
        answer:
          "Free: once daily. Pro: hourly. Faster sync means agents work with fresher context from your connected platforms.",
      },
    ],
  },
  {
    category: "Getting Started",
    items: [
      {
        question: "How do I get started?",
        answer:
          "Sign up, connect context if you want it, and describe the first recurring task. TP turns that into a standing loop and the rest of the system starts compounding from there.",
      },
      {
        question: "What's the best first task?",
        answer:
          "A weekly team recap or stakeholder brief is usually the fastest way to see value. It creates an obvious review loop, gives TP something concrete to refine, and quickly shows whether the system is grounding itself well.",
      },
      {
        question: "How quickly do I see results?",
        answer:
          "Your first task output is typically ready within minutes. From there, quality improves with every cycle as agents accumulate context and learn from your feedback.",
      },
    ],
  },
];

const allFaqItems = faqSections.flatMap((s) => s.items);

export const metadata = getMarketingMetadata({
  title: "FAQ",
  description:
    "Frequently asked questions about yarnnn: persistent agents, Thinking Partner, recurring tasks, platform integrations, pricing, and getting started.",
  path: "/faq",
  keywords: [
    "yarnnn faq",
    "autonomous ai faq",
    "ai workforce faq",
    "ai agent faq",
    "ai task faq",
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
              Persistent agents, Thinking Partner, tasks, integrations, pricing, and how to get started.
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
              <p className="text-white/50 mb-8">Start with one recurring task and let the system show you how it compounds.</p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  href="/auth/login"
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
