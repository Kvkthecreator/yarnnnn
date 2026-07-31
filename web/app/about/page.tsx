import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { SpotlightCard } from "@/components/landing/SpotlightCard";
import { ScrollReveal } from "@/components/landing/ScrollReveal";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";
import { CTA, PRIMARY_CTA_LABEL } from "@/lib/cta";

/**
 * About — the thesis page (CANON-LOCK-2026-07-30, re-cut 2026-07-31).
 *
 * Reframed off the memory-layer era: yarnnn is a workspace — file system,
 * documents, agents, chat — not a memory plugin. This page absorbs the
 * "why it's different" argument that used to live on /how-it-works; that
 * page now carries product mechanics only.
 */

export const metadata: Metadata = getMarketingMetadata({
  title: "About — the AI-first workspace no AI company can build",
  description:
    "The real work happens with AI now, and it deserves a real workspace — not a chat scroll. One that works across every AI can't be owned by any one of them. So we built it.",
  path: "/about",
  keywords: [
    "about yarnnn",
    "ai-first workspace",
    "ai workspace you own",
    "neutral ai workspace",
    "cross-llm workspace",
    "shared workspace for ai and humans",
  ],
});

const BELIEFS = [
  {
    title: "Work made with AI is real work",
    body: "Drafts, decisions, analysis — the actual thinking happens in AI chats now. But a chat scroll is where work goes to disappear. Real work deserves a real place to land: files you can open next week, organize, build on, and hand to someone else.",
    sub: "A workspace, not a chat log.",
  },
  {
    title: "Every change signed, human or not",
    body: "You, your teammates, your agents, and every AI you connect write into the same place — and every change carries the name of whoever made it. Not as a compliance feature: it's what makes co-working with AI trustworthy at all.",
    sub: "If you can't see who wrote it, you can't build on it.",
  },
  {
    title: "Neutral across every AI",
    body: "Each AI company's workspace is sealed to its own models — that's the business model. A workspace where all of them work as first-class participants can't belong to any one of them. Being neutral across rivals is the one thing a rival can't do.",
    sub: "So nobody builds it. That's why we did.",
  },
  {
    title: "Yours to keep, yours to take",
    body: "The files are yours. The history is yours. Models improve every few months — what compounds is the signed record of the work, kept in one place you own. Every new model makes your workspace more valuable, not less.",
    sub: "The AI will change. Your record shouldn't.",
  },
  {
    title: "A room, not an org tree",
    body: "yarnnn is built for small teams — a few people and their AIs around the same work. No admin console, no procurement, no rollout. You start alone, invite one person, and it's already doing its job.",
    sub: "Two people work free. The product does the selling.",
  },
  {
    title: "Receipts, not claims",
    body: "Nearly four hundred numbered architecture decisions written down in the open. Every change in every workspace tracked at the source. Built for real use, and run daily on our own work.",
    sub: "The record is the proof.",
  },
];

const NOT_LIST = [
  {
    title: "Not another AI chat app",
    desc: "Chat is one app inside the workspace, grounded in your files. The product is the workspace itself — where the work lands, not where it scrolls by.",
  },
  {
    title: "Not a memory plugin",
    desc: "Memory layers remember things about you. yarnnn holds the work itself — documents, files, decisions — with memory as a byproduct of a record you own.",
  },
  {
    title: "Not AI bolted onto a doc tool",
    desc: "Retrofitted workspaces treat AI as a feature for humans to click. Here AI works in the same file system you do, under its own name — a participant, not a button.",
  },
  {
    title: "Not an enterprise suite",
    desc: "No SSO checklist, no admin hierarchy, no pilot program. A workspace is a room. If your team needs an org tree, we're honestly not for you.",
  },
];

const WHO_ITEMS = [
  {
    title: "You work with AI every day",
    desc: "The AI output is the work, not a garnish. You want it to land somewhere real the moment it's made — not ferried out of a chat window by hand.",
  },
  {
    title: "Someone else needs to see it",
    desc: "A co-founder, a client, a teammate — or just your own AI on another device. The moment work is shared, who-wrote-what starts to matter.",
  },
  {
    title: "You'd rather own than rent",
    desc: "You've watched tools come and go. You want the work you've built up — files, decisions, history — in a place that outlasts any one model or vendor.",
  },
];

export default function AboutPage() {
  const aboutSchema = {
    "@context": "https://schema.org",
    "@type": "AboutPage",
    name: "About yarnnn",
    description: metadata.description ?? undefined,
    url: `${BRAND.url}/about`,
    isPartOf: {
      "@type": "WebSite",
      name: BRAND.name,
      url: BRAND.url,
    },
  };

  return (
    <div className="relative min-h-screen flex flex-col bg-[#0f1419] text-white overflow-x-hidden">
      <GrainOverlay variant="dark" />
      <ShaderBackgroundDark />

      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted />

        <main className="flex-1">
          {/* Hero — the neutrality thesis, workspace-era */}
          <section className="max-w-4xl mx-auto px-6 py-24 md:py-32">
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-10 tracking-tight leading-[1.1]">
              We built the <span className="text-[#de5a2b]">AI-first workspace</span>
              <br />
              <span className="text-white/50">no AI company can.</span>
            </h1>
            <div className="max-w-2xl space-y-6 text-white/50">
              <p>
                The real work moved into AI chats — the drafts, the decisions, the analysis.
                And chats are where work disappears: scrolled past, unfindable next week,
                invisible to the people it was made for.
              </p>
              <p>
                Every AI company would love to be where that work lives. But each one&apos;s
                workspace is sealed to its own models, by design. A workspace where{" "}
                <em className="not-italic text-white/70">all</em> of them work — alongside you
                and your team — can&apos;t belong to any one of them. It has to be neutral,
                and neutral across rivals is the one thing a rival can&apos;t be.
              </p>
              <p>
                So we built it: a real workspace — a shared file system, documents you build
                with AI, agents ready out of the box — where everything lands as a signed,
                versioned file you own, whoever made it.
              </p>
              <p className="text-white font-medium">
                We run our own company on it, and we write down every decision in the open.
              </p>
            </div>
          </section>

          {/* What we believe */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">What we believe</h2>

              <div className="space-y-16">
                {BELIEFS.map((b) => (
                  <div key={b.title} className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
                    <div>
                      <h3 className="text-lg font-medium text-white">{b.title}</h3>
                    </div>
                    <div className="text-white/50">
                      <p className="mb-4">{b.body}</p>
                      <p className="text-white/30 text-sm">{b.sub}</p>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollReveal>
          </section>

          {/* What yarnnn is not */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-8">What yarnnn is not</h2>
              <p className="text-white/50 mb-12 max-w-xl">
                We&apos;re focused. These are things we intentionally chose not to be.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {NOT_LIST.map((item) => (
                  <SpotlightCard key={item.title} variant="dark" spotlightSize={300}>
                    <div className="p-6">
                      <h3 className="text-lg font-medium mb-2">{item.title}</h3>
                      <p className="text-white/50 text-sm leading-relaxed">{item.desc}</p>
                    </div>
                  </SpotlightCard>
                ))}
              </div>
            </ScrollReveal>
          </section>

          {/* Who it's for */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">Who yarnnn is for</h2>
              <p className="text-white/50 mb-12 max-w-xl">
                Small teams — starting at one — who already work with AI every day, and are
                tired of being the bridge between their AI and everyone else.
              </p>

              <div className="space-y-4">
                {WHO_ITEMS.map((item) => (
                  <SpotlightCard key={item.title} variant="dark" spotlightSize={400}>
                    <div className="p-6">
                      <h3 className="text-base font-medium mb-2">{item.title}</h3>
                      <p className="text-white/50 text-sm leading-relaxed">{item.desc}</p>
                    </div>
                  </SpotlightCard>
                ))}
              </div>

              {/* The recognition sentence (canon Slot 4) */}
              <blockquote className="mt-12 border-l-2 border-[#de5a2b]/50 pl-6">
                <p className="text-xl md:text-2xl font-light text-white/70 italic">
                  &ldquo;I&apos;m the human clipboard between my AI and my team.&rdquo;
                </p>
                <p className="mt-3 text-sm text-white/35">If that&apos;s you, this is the fix.</p>
              </blockquote>
            </ScrollReveal>
          </section>

          {/* CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">Stop being the clipboard.</h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Start free — you and a teammate, your files, and every AI you already use,
                working in one place.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link
                  href={CTA.signup}
                  className="inline-block px-8 py-4 bg-white text-black text-lg font-medium rounded-full hover:bg-white/90 transition-colors"
                >
                  {PRIMARY_CTA_LABEL}
                </Link>
                <Link
                  href={CTA.howItWorks}
                  className="inline-block px-8 py-4 border border-white/20 text-white text-lg font-medium rounded-full hover:bg-white/10 transition-colors"
                >
                  See how it works
                </Link>
              </div>
            </ScrollReveal>
          </section>
        </main>

        <LandingFooter inverted />
      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(aboutSchema) }}
      />
    </div>
  );
}
