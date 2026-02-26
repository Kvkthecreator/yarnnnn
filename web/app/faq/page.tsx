import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { BRAND } from "@/lib/metadata";

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
          "yarnnn is an autonomous AI work platform. It connects to your existing work platforms—Slack, Gmail, Notion, Calendar—accumulates context from them, and produces recurring deliverables on your behalf. The longer you use it, the smarter it gets.",
      },
      {
        question: "What is TP (Thinking Partner)?",
        answer:
          "TP is yarnnn's intelligent interface. It's not a chatbot—it's a partner you talk to in plain language to set up deliverables, ask questions about your work, and manage what yarnnn does autonomously. You describe what you need, and TP figures out the rest.",
      },
      {
        question: "How is yarnnn different from ChatGPT or Claude?",
        answer:
          "ChatGPT and Claude are stateless—they forget everything between sessions. yarnnn accumulates context continuously from your connected platforms. It doesn't just answer questions; it produces work autonomously on a schedule. After 90 days, the accumulated context makes it irreplaceable.",
      },
      {
        question: "Is yarnnn an AI agent?",
        answer:
          "yarnnn is autonomous AI, not a generic agent platform. The difference is context. Agent platforms execute tasks without understanding your world. yarnnn's autonomy is meaningful because it's powered by your actual work context—your Slack conversations, email threads, documents, and calendar.",
      },
    ],
  },
  {
    category: "Platforms & Data",
    items: [
      {
        question: "Which platforms does yarnnn connect to?",
        answer:
          "yarnnn connects to Slack, Gmail, Google Calendar, and Notion. You authorize access via OAuth—a standard, secure authorization flow. yarnnn reads from these platforms to build context. It never posts, sends, or modifies anything on your behalf.",
      },
      {
        question: "Is my data safe?",
        answer:
          "Yes. All data is encrypted in transit and at rest. OAuth tokens are encrypted with a dedicated key. yarnnn only reads the sources you explicitly select—specific Slack channels, Gmail labels, Notion pages. You control exactly what yarnnn can see, and you can disconnect any platform at any time.",
      },
      {
        question: "What does yarnnn actually sync from my platforms?",
        answer:
          "From Slack: messages from channels you select. From Gmail: emails from labels you choose. From Notion: pages and databases you pick. From Calendar: your events from the past week through the next two weeks. Content is retained with time-based limits and refreshed on each sync cycle.",
      },
      {
        question: "Do I need to connect platforms to use yarnnn?",
        answer:
          "No. You can start talking to TP right away without connecting anything. But yarnnn gets dramatically more useful with platform connections—that's where your work context lives. You can also upload documents directly if you prefer.",
      },
    ],
  },
  {
    category: "Deliverables",
    items: [
      {
        question: "What are autonomous deliverables?",
        answer:
          "Deliverables are recurring pieces of work that yarnnn produces on a schedule—weekly status reports, monthly investor updates, client briefs, meeting prep summaries. You define what you need through a conversation with TP, and yarnnn produces drafts autonomously.",
      },
      {
        question: "How do deliverables improve over time?",
        answer:
          "Every time you edit a deliverable before approving it, yarnnn learns from your changes. It picks up your tone, your structure preferences, what you emphasize, what you cut. By the 10th version, the drafts closely match what you'd write yourself.",
      },
      {
        question: "What kinds of deliverables can yarnnn produce?",
        answer:
          "Weekly status reports, client follow-up summaries, investor updates, meeting prep briefs, stakeholder updates, team digests—anything recurring that draws from your platform context. If you produce it regularly and it's based on information from your connected platforms, yarnnn can handle it.",
      },
      {
        question: "Can I edit deliverables before they go out?",
        answer:
          "Absolutely—that's the model. yarnnn produces the draft, you review and refine it. You're the supervisor, not the operator. Every edit teaches yarnnn your preferences so future drafts need fewer changes.",
      },
    ],
  },
  {
    category: "Pricing & Plans",
    items: [
      {
        question: "Is yarnnn free to use?",
        answer:
          "Yes. The Free plan includes 1 autonomous deliverable, unlimited platform connections, context accumulation, and 10 TP conversations per month. It's fully functional—not a trial.",
      },
      {
        question: "What does the Pro plan include?",
        answer:
          "Pro is $19/month and includes unlimited autonomous deliverables, unlimited TP conversations, and priority support. Same price as ChatGPT Plus, but yarnnn actually accumulates your context and works autonomously.",
      },
      {
        question: "Why are platform connections free for everyone?",
        answer:
          "The more platforms you connect, the deeper yarnnn's context becomes. More context means better autonomy. We don't want pricing to get in the way of that. Connect everything—it's all included on every plan.",
      },
    ],
  },
  {
    category: "Getting Started",
    items: [
      {
        question: "How do I get started?",
        answer:
          "Sign up for free, then start a conversation with TP. Tell it what recurring work you need help with. TP will guide you through connecting your platforms and setting up your first deliverable. The whole process takes a few minutes.",
      },
      {
        question: "Do I need to configure anything?",
        answer:
          "No. There are no configuration screens, templates, or setup wizards. You describe what you need to TP in plain language, and it handles the rest. If TP needs clarification, it asks.",
      },
      {
        question: "How quickly does yarnnn start working?",
        answer:
          "Immediately. Once you connect a platform and set up a deliverable, yarnnn syncs your context and can produce a first draft right away. The quality improves with each cycle as context accumulates and yarnnn learns from your edits.",
      },
    ],
  },
];

const allFaqItems = faqSections.flatMap((s) => s.items);

export const metadata: Metadata = {
  title: "FAQ",
  description:
    "Frequently asked questions about yarnnn—autonomous AI that connects to your work platforms, accumulates context, and produces recurring deliverables on your behalf.",
  alternates: {
    canonical: `${BRAND.url}/faq`,
  },
  openGraph: {
    title: "FAQ | yarnnn",
    description:
      "Frequently asked questions about yarnnn—autonomous AI that connects to your work platforms, accumulates context, and produces recurring deliverables on your behalf.",
    url: `${BRAND.url}/faq`,
    images: [
      {
        url: new URL(BRAND.ogImage, BRAND.url).toString(),
        width: 1200,
        height: 630,
        alt: "yarnnn FAQ",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "FAQ | yarnnn",
    description:
      "Frequently asked questions about yarnnn—autonomous AI that connects to your work platforms, accumulates context, and produces recurring deliverables on your behalf.",
    images: [new URL(BRAND.ogImage, BRAND.url).toString()],
  },
};

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
              Everything you need to know about yarnnn, TP, and how autonomous
              AI works for you.
            </p>

            <div className="space-y-16">
              {faqSections.map((section) => (
                <div key={section.category}>
                  <h2 className="text-xs text-white/30 uppercase tracking-widest mb-8">
                    {section.category}
                  </h2>

                  <div className="space-y-8">
                    {section.items.map((item) => (
                      <div
                        key={item.question}
                        className="border-b border-white/5 pb-8 last:border-0"
                      >
                        <h3 className="text-lg font-medium mb-3">
                          {item.question}
                        </h3>
                        <p className="text-white/50 leading-relaxed">
                          {item.answer}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* CTA */}
            <div className="mt-24 text-center">
              <h2 className="text-2xl font-medium mb-4">
                Still have questions?
              </h2>
              <p className="text-white/50 mb-8">
                Talk to TP directly, or reach out to us.
              </p>
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