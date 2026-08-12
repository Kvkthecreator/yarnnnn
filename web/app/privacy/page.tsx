import Link from "next/link";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata = getMarketingMetadata({
  title: "Privacy Policy",
  description:
    "How yarnnn collects, uses, and protects your data — including how connected LLM assistants (via the MCP connector) access your memory, encryption, data retention, and your rights.",
  path: "/privacy",
});

export default function PrivacyPage() {
  const legalSchema = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: "Privacy Policy",
    url: `${BRAND.url}/privacy`,
    description: metadata.description,
    dateModified: "2026-07-08",
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border py-4 px-6">
        <Link href="/" className="text-xl font-brand">
          yarnnn
        </Link>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-12 prose prose-neutral dark:prose-invert">
        <h1 className="text-3xl font-bold mb-2">Privacy Policy</h1>
        <p className="text-muted-foreground mb-8">
          <strong>Effective Date: July 8, 2026</strong>
        </p>

        <p>
          This Privacy Policy outlines how yarnnn (&quot;we&quot;, &quot;our&quot;, or &quot;us&quot;)
          collects, uses, and protects your information when you use our
          services.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-4">1. Information We Collect</h2>
        <p>We collect the following types of information:</p>
        <ul className="list-disc pl-6 space-y-2">
          <li>
            <strong>Account Information:</strong> Email address, name, and
            profile data from authentication providers (Google, etc.)
          </li>
          <li>
            <strong>Content:</strong> Documents you upload, notes and memories
            you save, workspace files you store, and tasks you manage —
            including anything you choose to save through a connected LLM
            assistant (see §5)
          </li>
          <li>
            <strong>Provenance &amp; metadata:</strong> For each saved item, we
            record when it was written, which source contributed it (you, a
            connected assistant, or YARNNN itself), and its revision history.
            This attribution is core to the product
          </li>
          <li>
            <strong>Usage Data:</strong> How you interact with our services,
            features used, and work requests made
          </li>
          <li>
            <strong>Work Outputs:</strong> AI-generated content created through
            our agents and recurring tasks
          </li>
        </ul>

        <h2 className="text-xl font-semibold mt-8 mb-4">2. How We Use Your Data</h2>
        <ul className="list-disc pl-6 space-y-2">
          <li>Provide and improve our AI work platform services</li>
          <li>Generate context-aware outputs through autonomous agents and tasks</li>
          <li>Send service-related communications (e.g., daily updates or account notices)</li>
          <li>Maintain security and prevent abuse</li>
        </ul>
        <p>
          We do not sell your personal data or share it with third parties for
          marketing purposes.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-4">3. Data Storage & Security</h2>
        <p>
          Your data is stored using Supabase (PostgreSQL) with application and
          database access controls. All data transmission is encrypted via HTTPS.
          Connector credentials are encrypted where stored as credentials, and
          we continue to harden credential rotation, retention, and deletion
          coverage. For a plain-English overview of the architecture and its
          current limits, see our {" "}
          <Link href="/privacy-architecture" className="text-primary hover:underline">
            Privacy Architecture
          </Link>
          .
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-4">4. Third-Party Services</h2>
        <p>We use the following third-party services as data processors:</p>
        <ul className="list-disc pl-6 space-y-2">
          <li>
            <strong>Supabase:</strong> Authentication and database (PostgreSQL)
          </li>
          <li>
            <strong>Render:</strong> Application and connector hosting
          </li>
          <li>
            <strong>Vercel:</strong> Web hosting and analytics
          </li>
          <li>
            <strong>AI providers (Anthropic, OpenAI, Google, DeepSeek):</strong>{" "}
            when you ask an AI to work, the files needed for that task are sent
            to the provider running it. Which provider depends on the model
            chosen for the task. Content sent this way is processed under each
            provider&apos;s API terms, which do not use API content for training
            by default. We rely on those standard published terms — we do not
            hold a separately negotiated training prohibition with them
          </li>
          <li>
            <strong>OpenAI (search indexing):</strong> separately from the
            above, the text of your files is sent to OpenAI to build the
            embeddings that make your workspace searchable. This happens as
            files are written, not only when you ask an AI to do something
          </li>
          <li>
            <strong>Sentry:</strong> crash and error reporting, configured not
            to collect personal data
          </li>
          <li>
            <strong>Resend:</strong> transactional email delivery
          </li>
          <li>
            <strong>Lemon Squeezy:</strong> payments and billing
          </li>
        </ul>
        <p>
          This list is the complete set of third parties that can receive your
          content or personal data. If we add one, we will update this page.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-4">
          5. Connected LLM Assistants (MCP Connector)
        </h2>
        <p>
          YARNNN can be connected to LLM assistants you already use — such as
          ChatGPT, Claude, and others — through the open Model Context Protocol
          (MCP). This connection is established by you, through your assistant,
          using OAuth; you authenticate as yourself and the connection is scoped
          to your own workspace.
        </p>
        <p>
          When a connected assistant is authorized, it acts on your behalf with
          the same reach over your workspace that you have. It can:
        </p>
        <ul className="list-disc pl-6 space-y-2">
          <li>
            <strong>Read</strong> your files, list and search your workspace,
            and view how any file changed over time
          </li>
          <li>
            <strong>Write</strong> new files and edit existing ones (attributed
            to that assistant)
          </li>
          <li>
            <strong>Move, rename, and delete</strong> files
          </li>
          <li>
            <strong>Share</strong> — mint a link to a file or the workspace,
            including links that grant full member access to whoever opens them
          </li>
        </ul>
        <p>
          We state this plainly because it is a larger authority than
          &quot;save and recall.&quot; Connect assistants you trust. Every
          action an assistant takes is signed with its name and kept in the
          file&apos;s revision history, so you can see what it did and walk it
          back.
        </p>
        <p>
          What this means for your data: content you save through one assistant
          becomes part of your durable YARNNN memory and is therefore available
          to you through any other assistant you have connected, as well as in
          the YARNNN web app. The assistant&apos;s provider (e.g. OpenAI for
          ChatGPT) processes the request under its own privacy terms; YARNNN
          stores the resulting content and its attribution. We record which
          assistant contributed each item so this provenance is transparent to
          you. You can disconnect any assistant at any time from within that
          assistant&apos;s settings, which revokes its access to your workspace.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-4">6. Your Rights</h2>
        <p>You have the right to:</p>
        <ul className="list-disc pl-6 space-y-2">
          <li>Access your personal data</li>
          <li>Request deletion of your account and data</li>
          <li>Export your content</li>
          <li>Opt out of non-essential communications</li>
        </ul>

        <h2 className="text-xl font-semibold mt-8 mb-4">7. Data Retention</h2>
        <p>
          <strong>Nothing expires on a schedule.</strong> We do not run a
          retention timer: trash holds until you empty it, and no background
          process deletes your work after a fixed period. This is deliberate —
          a timer means the system destroying your work with nobody watching.
          If a timer is ever offered it will be a setting you turn on, not a
          default.
        </p>
        <p>
          When you delete a file permanently, reset your workspace, or delete
          your account, removal is immediate rather than queued. Deleting your
          account removes your workspace files, their full revision history,
          and your account record. Some stored file contents may persist in
          backing storage after account deletion; completing that cleanup is
          named in our{" "}
          <Link href="/privacy-architecture" className="text-primary hover:underline">
            data page
          </Link>{" "}
          as current work. We retain what the law requires us to retain.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-4">8. Changes to This Policy</h2>
        <p>
          We may update this policy and will notify you of material changes.
          Continued use after changes constitutes acceptance.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-4">9. Contact Us</h2>
        <p>
          Questions about privacy? Contact us at{" "}
          <a
            href="mailto:admin@yarnnn.com"
            className="text-primary hover:underline"
          >
            admin@yarnnn.com
          </a>
        </p>
      </main>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(legalSchema) }}
      />
    </div>
  );
}
