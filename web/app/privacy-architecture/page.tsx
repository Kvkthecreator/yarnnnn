import Link from "next/link";
import {
  Database,
  FileClock,
  KeyRound,
  LockKeyhole,
  Route,
  ShieldCheck,
  SlidersHorizontal,
} from "lucide-react";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata = getMarketingMetadata({
  title: "Privacy Architecture — how yarnnn handles AI memory",
  description:
    "How yarnnn keeps durable AI memory scoped, attributable, revocable, and visible across your workspace and connected assistants.",
  path: "/privacy-architecture",
  keywords: [
    "yarnnn privacy architecture",
    "AI memory privacy",
    "MCP privacy",
    "cross-LLM memory privacy",
    "AI workspace security",
  ],
});

const TRUST_MARKS = [
  {
    label: "OAuth",
    detail: "Authorized access",
    icon: KeyRound,
  },
  {
    label: "Scoped",
    detail: "Workspace boundary",
    icon: LockKeyhole,
  },
  {
    label: "Provenance",
    detail: "Attributed changes",
    icon: FileClock,
  },
];

const FEATURE_CARDS = [
  {
    title: "Scoped by workspace",
    body: "Core product data is shaped around account and workspace boundaries, with application and database controls protecting the main user tables.",
    icon: ShieldCheck,
  },
  {
    title: "Not our training data",
    body: "We do not use your workspace data to train yarnnn-owned models. When you ask AI to work, relevant context may be sent to model providers under their API terms.",
    icon: LockKeyhole,
  },
  {
    title: "Revocable access",
    body: "Connected assistants require authorization, carry attribution, and can be revoked. Deletion and retention controls are being expanded where durable history still has limits.",
    icon: SlidersHorizontal,
  },
];

const ARCHITECTURE_POINTS = [
  {
    title: "Memory stays workspace-shaped",
    body: "Files, tasks, saved memories, and revision history are organized around your workspace instead of a loose global memory pool.",
  },
  {
    title: "Assistant access is explicit",
    body: "ChatGPT, Claude, or another MCP-capable assistant can connect only through an OAuth grant you approve and can revoke.",
  },
  {
    title: "Changes are attributable",
    body: "Saved items record whether they came from you, yarnnn, a teammate, or a connected assistant, so durable memory has a visible source.",
  },
  {
    title: "AI data flow is named",
    body: "When you ask AI to use workspace context, relevant context may be sent to model providers so the work can be done. The privacy policy states that flow plainly.",
  },
];

const CONTROL_POINTS = [
  "Most connector credentials are encrypted at rest where stored as credentials.",
  "Crash telemetry is configured without default PII collection.",
  "The purge model has explicit levels for work history, workspace state, integrations, and account deletion.",
  "Revision history is durable by design so users can inspect what changed and who changed it.",
];

const HARDENING = [
  "Tightening private file-body reads so content is reachable only through workspace-scoped authorization paths.",
  "Adding garbage collection for unreferenced private content bodies after workspace resets and account deletion.",
  "Expanding row-level security coverage for user-scoped tables that still depend on application-layer filters.",
  "Normalizing remaining API-key-like connector metadata into encrypted credential storage with rotation support.",
  "Adding clearer retention controls for operational telemetry, historical revisions, and AI-context minimization.",
];

export default function PrivacyArchitecturePage() {
  const schema = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: "Privacy Architecture",
    url: `${BRAND.url}/privacy-architecture`,
    description: metadata.description,
    dateModified: "2026-07-08",
  };

  return (
    <div className="min-h-screen bg-[#f8ead7] text-[#262626]">
      <LandingHeader />

      <main>
        <section className="px-6 py-20 md:py-28">
          <div className="mx-auto max-w-5xl text-center">
            <p className="mb-5 text-sm font-medium uppercase tracking-[0.24em] text-[#7d6d5c]">
              Privacy Architecture
            </p>
            <h1 className="mx-auto max-w-4xl text-4xl font-semibold leading-[1.05] tracking-tight md:text-6xl">
              Built for confidential AI work.
              <br />
              Designed to show where memory goes.
            </h1>
            <p className="mx-auto mt-7 max-w-2xl text-lg leading-8 text-[#6f6255] md:text-xl">
              See how yarnnn keeps durable memory scoped, attributable, revocable, and honest about
              the places AI context is processed.
              {" "}
              <Link href="/privacy" className="font-medium text-[#2f2a25] underline underline-offset-4">
                Read the policy
              </Link>
            </p>

            <div className="mt-16 flex flex-wrap items-start justify-center gap-8 md:gap-12">
              {TRUST_MARKS.map((mark) => {
                const Icon = mark.icon;
                return (
                  <div key={mark.label} className="flex w-32 flex-col items-center">
                    <div className="flex h-28 w-28 items-center justify-center rounded-full border border-[#2f2a25]/10 bg-white/70 shadow-sm">
                      <Icon className="h-10 w-10 text-[#2f2a25]" aria-hidden="true" />
                    </div>
                    <p className="mt-4 text-lg font-semibold">{mark.label}</p>
                    <p className="mt-1 text-sm text-[#75695e]">{mark.detail}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        <section className="bg-[#f5dfc0] px-6 py-10 md:py-14">
          <div className="mx-auto grid max-w-7xl gap-5 md:grid-cols-3">
            {FEATURE_CARDS.map((card) => {
              const Icon = card.icon;
              return (
                <article key={card.title} className="min-h-[260px] rounded-lg bg-[#fffaf1] p-8 shadow-sm">
                  <div className="mb-14 flex h-16 w-16 items-center justify-center rounded-full bg-white shadow-sm">
                    <Icon className="h-7 w-7 text-[#2f2a25]" aria-hidden="true" />
                  </div>
                  <h2 className="text-2xl font-semibold tracking-tight md:text-3xl">{card.title}</h2>
                  <p className="mt-6 text-lg leading-8 text-[#645a51]">{card.body}</p>
                </article>
              );
            })}
          </div>
        </section>

        <section className="bg-[#fffaf1] px-6 py-16 md:py-24">
          <div className="mx-auto grid max-w-6xl gap-12 lg:grid-cols-[0.8fr_1.2fr]">
            <div>
              <p className="mb-4 text-sm font-medium uppercase tracking-[0.2em] text-[#8a7764]">
                How it works
              </p>
              <h2 className="text-3xl font-semibold leading-tight tracking-tight md:text-5xl">
                Private by structure, not just by policy.
              </h2>
              <p className="mt-6 text-lg leading-8 text-[#6f6255]">
                yarnnn is built around durable memory, so privacy has to be mechanical: what is
                stored, who can read it, who wrote it, when it leaves yarnnn, and what can be
                revoked.
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              {ARCHITECTURE_POINTS.map((point) => (
                <article key={point.title} className="rounded-lg border border-[#e7d8c6] bg-white p-6">
                  <h3 className="text-xl font-semibold tracking-tight">{point.title}</h3>
                  <p className="mt-4 leading-7 text-[#645a51]">{point.body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="bg-[#f8ead7] px-6 py-16 md:py-24">
          <div className="mx-auto grid max-w-6xl gap-12 lg:grid-cols-[0.85fr_1.15fr]">
            <div>
              <p className="mb-4 text-sm font-medium uppercase tracking-[0.2em] text-[#8a7764]">
                What holds today
              </p>
              <h2 className="text-3xl font-semibold leading-tight tracking-tight md:text-5xl">
                The trust story is concrete.
              </h2>
              <p className="mt-6 text-lg leading-8 text-[#6f6255]">
                This is the part that is strong enough to say plainly: scoped product data,
                credential encryption where credentials are stored, low-PII telemetry defaults, and
                visible provenance.
              </p>
            </div>
            <div className="rounded-lg bg-[#fffaf1] p-6 shadow-sm md:p-8">
              <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-full bg-white shadow-sm">
                <Route className="h-7 w-7 text-[#2f2a25]" aria-hidden="true" />
              </div>
              <ul className="space-y-4 text-[#645a51]">
                {CONTROL_POINTS.map((item) => (
                  <li key={item} className="flex gap-3 leading-7">
                    <span className="mt-3 h-1.5 w-1.5 shrink-0 rounded-full bg-[#2f2a25]/45" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        <section className="bg-[#151719] px-6 py-16 text-white md:py-24">
          <div className="mx-auto grid max-w-6xl gap-12 lg:grid-cols-[0.85fr_1.15fr]">
            <div>
              <p className="mb-4 text-sm font-medium uppercase tracking-[0.2em] text-white/45">
                Current hardening
              </p>
              <h2 className="text-3xl font-semibold leading-tight tracking-tight md:text-5xl">
                The roadmap is part of the promise.
              </h2>
              <p className="mt-6 text-lg leading-8 text-white/65">
                Durable AI memory creates real privacy tradeoffs. We name the work still being
                tightened, especially around private content bodies, deletion completeness,
                credential rotation, and retention.
              </p>
            </div>
            <div className="rounded-lg border border-white/10 bg-white/[0.04] p-6 md:p-8">
              <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-full bg-white/10">
                <Database className="h-7 w-7 text-white" aria-hidden="true" />
              </div>
              <ul className="space-y-4 text-white/70">
                {HARDENING.map((item) => (
                  <li key={item} className="flex gap-3 leading-7">
                    <span className="mt-3 h-1.5 w-1.5 shrink-0 rounded-full bg-white/50" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      </main>

      <LandingFooter />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
      />
    </div>
  );
}
