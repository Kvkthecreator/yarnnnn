import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata = getMarketingMetadata({
  title: "Privacy Architecture — how yarnnn handles AI memory",
  description:
    "A plain-English look at yarnnn's privacy architecture: workspace ownership, provenance, connected AI assistants, model-provider processing, deletion, and hardening work in progress.",
  path: "/privacy-architecture",
  keywords: [
    "yarnnn privacy architecture",
    "AI memory privacy",
    "MCP privacy",
    "cross-LLM memory privacy",
    "AI workspace security",
  ],
});

const PRINCIPLES = [
  {
    title: "Your workspace is the boundary",
    body: "Memory, files, tasks, and revision history are organized around your workspace. Product reads and writes are designed to be scoped to that workspace, not mixed into a global memory pool.",
  },
  {
    title: "Every saved memory has provenance",
    body: "YARNNN records who or what contributed a saved item — you, YARNNN, a teammate, or a connected assistant — plus when it changed and why. The point is not just storage; it is accountability.",
  },
  {
    title: "Connected AIs are authorized, not invisible",
    body: "If you connect ChatGPT, Claude, or another MCP-capable assistant, it gets access through an OAuth connection you approve. Its contributions are attributed, and you can revoke the connection.",
  },
  {
    title: "AI work requires explicit data flow",
    body: "When you ask YARNNN or a connected assistant to use your workspace, relevant context may be sent to AI model providers so the work can be done. We disclose that flow rather than pretending durable AI memory never leaves the app.",
  },
];

const CONTROLS = [
  "Account and workspace scoping for the core product data model.",
  "HTTPS in transit and database-backed access controls for application data.",
  "Application-layer encryption for OAuth tokens and most connector credentials.",
  "Sentry configured without default PII collection.",
  "Visible revision history so important changes can be inspected instead of silently overwritten.",
  "Layered data controls for clearing work history, workspace state, integrations, or the account.",
];

const HARDENING = [
  "Tightening the content-addressed blob store so private file bodies are readable only through workspace-scoped authorization paths.",
  "Adding blob garbage collection so account deletion and workspace resets remove unreferenced private content bodies, not only their revision rows.",
  "Expanding database row-level security coverage for user-scoped tables that still rely on application-layer filters.",
  "Moving remaining API-key-like connector metadata into encrypted credential storage and adding key-rotation support.",
  "Adding clearer retention controls for operational telemetry and historical revisions.",
  "Building optional minimization and redaction controls for context sent to AI providers.",
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
    <div className="min-h-screen bg-background text-foreground">
      <LandingHeader />

      <main>
        <section className="max-w-5xl mx-auto px-6 py-20 md:py-28">
          <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground mb-5">
            Privacy Architecture
          </p>
          <h1 className="max-w-4xl text-4xl md:text-6xl font-medium tracking-tight leading-[1.05] mb-8">
            Durable AI memory only works if the boundaries are legible.
          </h1>
          <p className="max-w-3xl text-lg md:text-xl text-muted-foreground leading-8">
            YARNNN is built to remember across AI tools. That means privacy is not just a policy
            link — it is an architecture question: what gets stored, who can read it, which AI
            providers process it, and what happens when you disconnect or delete.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/privacy"
              className="inline-flex items-center rounded-full bg-foreground px-5 py-3 text-sm font-medium text-background hover:opacity-90"
            >
              Read the privacy policy
            </Link>
            <Link
              href="/developers"
              className="inline-flex items-center rounded-full border border-border px-5 py-3 text-sm font-medium hover:bg-muted"
            >
              Developer docs
            </Link>
          </div>
        </section>

        <section className="border-y border-border bg-muted/30">
          <div className="max-w-5xl mx-auto px-6 py-16 grid md:grid-cols-2 gap-5">
            {PRINCIPLES.map((principle) => (
              <article key={principle.title} className="rounded-2xl border border-border bg-background p-6">
                <h2 className="text-xl font-semibold mb-3">{principle.title}</h2>
                <p className="text-muted-foreground leading-7">{principle.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="max-w-5xl mx-auto px-6 py-16 md:py-24 grid lg:grid-cols-[0.9fr_1.1fr] gap-12">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-muted-foreground mb-4">
              Controls in place
            </p>
            <h2 className="text-3xl md:text-4xl font-medium tracking-tight mb-5">
              What we rely on today.
            </h2>
            <p className="text-muted-foreground leading-7">
              These are the product and infrastructure controls that already shape how user data
              is handled. They are deliberately concrete because privacy claims should be
              inspectable.
            </p>
          </div>
          <ul className="space-y-3">
            {CONTROLS.map((control) => (
              <li key={control} className="rounded-xl border border-border p-4 text-muted-foreground">
                {control}
              </li>
            ))}
          </ul>
        </section>

        <section className="border-y border-border bg-[#0f1419] text-white">
          <div className="max-w-5xl mx-auto px-6 py-16 md:py-24 grid lg:grid-cols-[0.9fr_1.1fr] gap-12">
            <div>
              <p className="text-sm uppercase tracking-[0.2em] text-white/40 mb-4">
                Honest limits
              </p>
              <h2 className="text-3xl md:text-4xl font-medium tracking-tight mb-5">
                Durable memory has real privacy tradeoffs.
              </h2>
              <p className="text-white/60 leading-7">
                YARNNN keeps history so you can inspect and trust the record. That same durability
                means retention and deletion have to be engineered carefully. We would rather name
                the work than make vague claims.
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
              <h3 className="text-xl font-semibold mb-4">Hardening roadmap</h3>
              <ul className="space-y-3 text-white/65">
                {HARDENING.map((item) => (
                  <li key={item} className="flex gap-3">
                    <span className="mt-2 h-1.5 w-1.5 rounded-full bg-white/50 shrink-0" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        <section className="max-w-5xl mx-auto px-6 py-16 md:py-24">
          <div className="rounded-3xl border border-border bg-muted/30 p-8 md:p-10">
            <p className="text-sm uppercase tracking-[0.2em] text-muted-foreground mb-4">
              Plain-English promise
            </p>
            <h2 className="text-3xl font-medium tracking-tight mb-5">
              We will make the data flow visible.
            </h2>
            <p className="max-w-3xl text-muted-foreground leading-7">
              If an assistant writes something, it should say so. If a provider processes context,
              the policy should say so. If a deletion control has limits, those limits should be
              fixed or stated. Trust in AI memory comes from receipts, not from magic.
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
