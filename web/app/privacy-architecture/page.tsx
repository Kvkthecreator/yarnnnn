import Link from "next/link";
import { FileSignature, KeyRound, Ban, DownloadCloud } from "lucide-react";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

/**
 * The data page — ADR-561.
 *
 * Discipline: every line here is a claim the code supports, and the claims we
 * cannot make are named rather than implied. The "what we don't have" section
 * is load-bearing, not an apology — the audited comparables (x.ai in
 * particular) let the reader assume certifications that don't exist, and
 * saying it plainly is the differentiator a small team can actually hold.
 *
 * The trust marks are MECHANISMS, not certifications. No badge, seal, or
 * third-party logo may appear on this page until an actual audit backs it:
 * a badge reads as externally verified in a way prose does not.
 *
 * The closing section splits deliberately (ADR-561 D2 as amended 2026-08-13).
 * "Planned" is only sayable where a plan exists, so the four gaps are NOT one
 * list:
 *   - blob persistence + the private-body read policy ARE scheduled — both are
 *     named in ADR-561 §7 as owed work, so "on the roadmap" is a fact.
 *   - SOC 2 / ISO 27001 have NO roadmap in canon. They read "not yet started"
 *     with a condition (when customers need them), never "planned" — an
 *     invented timeline is the same defect as an invented badge.
 *   - DPA / BAA are neither: they are signable agreements, not audits, so they
 *     route to a conversation rather than a status.
 * Do not collapse these back into a single sentence.
 */

export const metadata = getMarketingMetadata({
  title: "Your data, plainly",
  description:
    "Where your work goes when you ask an AI to do something, what we never do with it, what you can take with you, and what we don't have.",
  path: "/privacy-architecture",
  keywords: [
    "yarnnn data handling",
    "AI workspace privacy",
    "MCP connector privacy",
    "AI training data policy",
    "workspace export",
  ],
});

// Mechanisms, not certifications. Each maps to a specific enforced behavior.
const TRUST_MARKS = [
  {
    label: "Never trained on",
    detail: "Not by us, and not by default by the models we call",
    icon: Ban,
  },
  {
    label: "Signed at the write path",
    detail: "Every change carries its author — enforced, not conventional",
    icon: FileSignature,
  },
  {
    label: "No retention timer",
    detail: "Nothing expires on a schedule; trash holds until you empty it",
    icon: KeyRound,
  },
  {
    label: "Exports as plain git",
    detail: "Full revision history as real commits, walkable offline",
    icon: DownloadCloud,
  },
];

const RECIPIENTS = [
  {
    name: "Anthropic · OpenAI · Google · DeepSeek",
    role: "Run the AI task you asked for",
    data: "The files needed for that task, depending on the model chosen",
  },
  {
    name: "OpenAI (search indexing)",
    role: "Builds the index that makes your workspace searchable",
    data: "File text, as files are written",
  },
  {
    name: "Supabase",
    role: "Database and authentication",
    data: "Your workspace contents and account",
  },
  {
    name: "Render · Vercel",
    role: "Application hosting",
    data: "Traffic in transit",
  },
  {
    name: "Sentry",
    role: "Crash and error reporting",
    data: "Configured to collect no personal data",
  },
  { name: "Resend", role: "Transactional email", data: "Recipients and message contents" },
  { name: "Lemon Squeezy", role: "Payments", data: "Billing details" },
];

export default function DataPage() {
  const schema = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: "Your data, plainly",
    url: `${BRAND.url}/privacy-architecture`,
    description: metadata.description,
    dateModified: "2026-08-13",
  };

  return (
    <div className="min-h-screen bg-[#faf8f5] text-[#1a1a1a]">
      <LandingHeader />

      <main>
        {/* Hero + trust marks */}
        <section className="px-6 pt-20 pb-16 md:pt-28">
          <div className="mx-auto max-w-3xl text-center">
            <h1 className="text-3xl font-medium leading-[1.15] tracking-tight md:text-5xl">
              Your data, plainly.
            </h1>
            <p className="mx-auto mt-6 max-w-xl text-lg leading-8 text-[#1a1a1a]/55 font-light">
              We don&apos;t train on your work, we don&apos;t delete it on a timer, and you
              can take all of it with you. Here are the details — including the parts
              still being tightened.
            </p>
          </div>

          <div className="mx-auto mt-14 grid max-w-4xl gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {TRUST_MARKS.map((mark) => {
              const Icon = mark.icon;
              return (
                <div
                  key={mark.label}
                  className="rounded-xl border border-[#1a1a1a]/[0.08] bg-white/70 p-5 text-center"
                >
                  <div className="mx-auto mb-4 flex h-11 w-11 items-center justify-center rounded-full bg-[#1a1a1a]/[0.04]">
                    <Icon className="h-5 w-5 text-[#1a1a1a]/70" aria-hidden="true" />
                  </div>
                  <p className="text-sm font-medium">{mark.label}</p>
                  <p className="mt-1.5 text-xs leading-5 text-[#1a1a1a]/45">{mark.detail}</p>
                </div>
              );
            })}
          </div>
        </section>

        {/* The prose */}
        <section className="border-t border-[#1a1a1a]/10 px-6 py-16 md:py-20">
          <div className="mx-auto max-w-2xl space-y-12">
            <div>
              <h2 className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-[#de5a2b]">
                Training
              </h2>
              <p className="leading-7 text-[#1a1a1a]/70">
                We never use your workspace content to train any model of ours. We
                don&apos;t operate models at all — we call other companies&apos; APIs, and
                under each one&apos;s published API terms, content sent that way
                isn&apos;t used for training by default. To be precise about the
                mechanism: we rely on those standard terms, not on a separately
                negotiated contract of our own. If that distinction matters to you, read
                their terms directly — we&apos;d rather point you there than paraphrase
                them.
              </p>
            </div>

            <div>
              <h2 className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-[#de5a2b]">
                Who can receive your content
              </h2>
              <p className="mb-5 leading-7 text-[#1a1a1a]/70">
                When you ask an AI to work, the files it needs go to the provider running
                that task. This is the complete list of third parties that can receive
                your content or personal data. If we add one, we&apos;ll update this page.
              </p>
              <div className="overflow-x-auto rounded-lg border border-[#1a1a1a]/[0.08] bg-white/60">
                <table className="w-full min-w-[520px] text-sm">
                  <thead>
                    <tr className="border-b border-[#1a1a1a]/[0.08]">
                      <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-[#1a1a1a]/40">
                        Who
                      </th>
                      <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-[#1a1a1a]/40">
                        Why
                      </th>
                      <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-[#1a1a1a]/40">
                        What
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {RECIPIENTS.map((r) => (
                      <tr
                        key={r.name}
                        className="border-b border-[#1a1a1a]/[0.06] last:border-0"
                      >
                        <td className="px-4 py-3 font-medium">{r.name}</td>
                        <td className="px-4 py-3 text-[#1a1a1a]/60">{r.role}</td>
                        <td className="px-4 py-3 text-[#1a1a1a]/60">{r.data}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div>
              <h2 className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-[#de5a2b]">
                Deletion
              </h2>
              <p className="leading-7 text-[#1a1a1a]/70">
                Nothing expires on a schedule. Trash holds until you empty it —
                deliberately, because a timer means the system destroying your work with
                nobody watching. When you delete something permanently, or delete your
                account, removal is immediate rather than queued.
              </p>
            </div>

            <div>
              <h2 className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-[#de5a2b]">
                Access
              </h2>
              <p className="leading-7 text-[#1a1a1a]/70">
                Who can read a file is a grant you make and can revoke — not a property of
                what kind of principal is asking. Connected assistants reach your workspace
                through OAuth you approve, and every write they make is signed with their
                name. A connected assistant can read, write, move, delete, and share files
                on your behalf — the same reach you have — so connect ones you trust.
              </p>
            </div>

            <div>
              <h2 className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-[#de5a2b]">
                What you can take
              </h2>
              <p className="leading-7 text-[#1a1a1a]/70">
                The whole workspace exports as a standard git repository, with the full
                revision history as real commits — readable with tools you already have,
                on a machine we have nothing to do with. Conversations aren&apos;t
                included yet.
              </p>
              <p className="mt-4 leading-7 text-[#1a1a1a]/70">
                It&apos;s in Workspace Settings, under Danger Zone — available any day,
                not just on the way out. The download names anything it couldn&apos;t
                include, so you always know what you have.
              </p>
            </div>

            <div className="rounded-xl border border-[#1a1a1a]/[0.1] bg-white/70 p-6">
              <h2 className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-[#1a1a1a]/50">
                What&apos;s not done yet
              </h2>
              <p className="leading-7 text-[#1a1a1a]/70">
                <strong className="font-medium text-[#1a1a1a]/85">On the roadmap.</strong>{" "}
                Two things we&apos;re tightening, both scheduled work rather than
                someday-maybe: some stored file contents can persist in backing storage
                after deletion, and reads of private file bodies still lean on
                application-layer checks rather than database-level rules. We name them
                here because you&apos;d have no way to find them otherwise.
              </p>
              <p className="mt-4 leading-7 text-[#1a1a1a]/70">
                <strong className="font-medium text-[#1a1a1a]/85">
                  Not yet started.
                </strong>{" "}
                We hold no SOC 2 or ISO 27001 certification. Those are third-party
                audits, and we&apos;d rather tell you we haven&apos;t done one than let a
                badge imply we have — we&apos;ll pursue them when our customers need
                them, and we&apos;ll say so here when that work begins. A DPA or BAA
                isn&apos;t an audit but a signed agreement: we don&apos;t offer one off
                the shelf today, so if you need either,{" "}
                <a
                  href="mailto:admin@yarnnn.com"
                  className="underline underline-offset-4 hover:text-[#1a1a1a]"
                >
                  talk to us
                </a>{" "}
                and we&apos;ll tell you honestly where we stand.
              </p>
            </div>

            <p className="border-t border-[#1a1a1a]/10 pt-8 text-sm text-[#1a1a1a]/50">
              The formal version is our{" "}
              <Link href="/privacy" className="underline underline-offset-4 hover:text-[#1a1a1a]">
                privacy policy
              </Link>
              . Questions:{" "}
              <a
                href="mailto:admin@yarnnn.com"
                className="underline underline-offset-4 hover:text-[#1a1a1a]"
              >
                admin@yarnnn.com
              </a>
              .
            </p>
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
