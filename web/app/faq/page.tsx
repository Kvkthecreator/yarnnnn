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
          "yarnnn is an AI workforce platform for recurring knowledge work. You sign up and get a pre-built team of specialist agents — Research, Content, Marketing, CRM — plus Slack and Notion bots. You assign tasks, they execute on schedule, and they get better every cycle.",
      },
      {
        question: "How is yarnnn different from ChatGPT or Claude?",
        answer:
          "Chat tools are session-based — they help in the moment but reset when you close the tab. yarnnn is system-based: you have persistent agents with memory that run tasks on schedule, sync context from your work tools, and learn from your feedback over time. The output gets better the longer it runs.",
      },
      {
        question: "What does \"autonomous\" mean here?",
        answer:
          "Tasks run on schedule without you. Your agents pull fresh context from connected tools, execute the task, and deliver the output. You review and redirect when needed. Over time, they require less supervision as they learn your preferences.",
      },
      {
        question: "What's the difference between agents, bots, and tasks?",
        answer:
          "Agents are persistent specialists (Research, Content, Marketing, CRM) — they reason across multiple steps and accumulate domain expertise. Bots are platform-mechanical (Slack Bot, Notion Bot) — they read and sync data from one platform. Tasks are defined work units — an objective, schedule, delivery format, and success criteria assigned to the right agent.",
      },
    ],
  },
  {
    category: "Your Team",
    items: [
      {
        question: "Do I have to create agents manually?",
        answer:
          "No. When you sign up, your team is already built — 4 specialist agents and 2 platform bots. You don't need to configure anything. Just describe the work you need done and yarnnn assigns it as a task to the right agent.",
      },
      {
        question: "What agents do I get?",
        answer:
          "Research Agent (web research, competitive intelligence, topic monitoring), Content Agent (drafts, reports, briefs, summaries), Marketing Agent (market signals, positioning, campaigns), CRM Agent (relationships, clients, stakeholders), Slack Bot (syncs channels and threads), and Notion Bot (syncs pages and databases).",
      },
      {
        question: "How do agents improve over time?",
        answer:
          "Every task run, review, and edit becomes signal for future work. Agents learn your preferred structure, emphasis, and tone. They also accumulate domain knowledge — understanding your team, competitive landscape, and communication patterns more deeply with each cycle.",
      },
      {
        question: "Can multiple agents work together on a task?",
        answer:
          "Yes. Most tasks need one agent handling the full chain — gather context, reason about it, produce output. For bigger jobs, multiple agents contribute their domain expertise to a single task. For example, Research Agent investigates competitors while Content Agent synthesizes Slack activity, and the task combines their work into one deliverable.",
      },
      {
        question: "Can I talk to agents directly?",
        answer:
          "Yes. Each agent can receive direction from you — adjust focus, change tone, redirect priorities. Your instructions persist across sessions and carry forward to every task that agent runs.",
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
          "Describe what you need in plain language — \"Give me a weekly competitor brief\" or \"Summarize #engineering every Friday as a PDF.\" yarnnn creates the task, assigns the right agent, sets the cadence, and starts executing.",
      },
    ],
  },
  {
    category: "Platforms & Data",
    items: [
      {
        question: "Which platforms does yarnnn connect to?",
        answer:
          "Slack and Notion. You authorize via OAuth and choose which channels or pages to include — or let yarnnn auto-select based on your activity. Bots activate automatically when you connect a platform.",
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
          "yarnnn has Free and Pro plans. Both include the full 6-agent roster and all platform integrations. Free gives you 2 active agents, 60 task runs/month, 50 messages/month, and daily sync. Pro gives you 10 active agents, 1,000 task runs/month, unlimited messages, hourly sync, and unlimited sources — $19/mo (Early Bird: $9/mo).",
      },
      {
        question: "What does \"active agents\" mean?",
        answer:
          "Your full roster (4 agents + 2 bots) is always available. \"Active agents\" means agents that have tasks assigned to them. Free lets you have 2 agents actively running tasks. Pro lets you have up to 10 — including new agents you create beyond the default roster.",
      },
      {
        question: "What are task runs?",
        answer:
          "Task runs measure the autonomous work your agents do — each scheduled task execution and rendered output (PDF, slides, etc.) costs one run. This is separate from messages (your conversations with agents). Free includes 60 runs/month, Pro includes 1,000.",
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
          "Sign up and your team is ready immediately — 4 specialist agents and 2 platform bots. Describe your first task, connect a platform if you want richer context, and your agents start working. No configuration required.",
      },
      {
        question: "What's the best first task?",
        answer:
          "A weekly Slack recap is the fastest way to see value — connect Slack, assign a \"weekly team recap\" task, and your Content Agent delivers a synthesized summary on your schedule. Quick feedback signal, immediate utility.",
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
    "Frequently asked questions about yarnnn: your AI workforce, agents and bots, task modes, platform integrations, pricing, and getting started.",
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
              Your AI workforce, agents and tasks, platforms, pricing, and how to get started.
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
              <p className="text-white/50 mb-8">Your team is ready — assign your first task in minutes.</p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  href="/auth/login"
                  className="inline-block px-8 py-3 bg-white text-black font-medium rounded-full hover:bg-white/90 transition-colors"
                >
                  Meet your team
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
