import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy Policy",
};

export default function PrivacyPage() {
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
          <strong>Effective Date: January 28, 2026</strong>
        </p>

        <p>
          This Privacy Policy outlines how Yarn (&quot;we&quot;, &quot;our&quot;, or &quot;us&quot;)
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
            <strong>Content:</strong> Documents you upload, text blocks you
            create, and projects you manage
          </li>
          <li>
            <strong>Usage Data:</strong> How you interact with our services,
            features used, and work requests made
          </li>
          <li>
            <strong>Work Outputs:</strong> AI-generated content created through
            our agents
          </li>
        </ul>

        <h2 className="text-xl font-semibold mt-8 mb-4">2. How We Use Your Data</h2>
        <ul className="list-disc pl-6 space-y-2">
          <li>Provide and improve our AI work platform services</li>
          <li>Generate context-aware outputs through AI agents</li>
          <li>Send service-related communications (e.g., weekly digests)</li>
          <li>Maintain security and prevent abuse</li>
        </ul>
        <p>
          We do not sell your personal data or share it with third parties for
          marketing purposes.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-4">3. Data Storage & Security</h2>
        <p>
          Your data is stored securely using Supabase (PostgreSQL) with
          row-level security. All data transmission is encrypted via HTTPS. We
          use industry-standard security practices to protect your information.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-4">4. Third-Party Services</h2>
        <p>We use the following third-party services:</p>
        <ul className="list-disc pl-6 space-y-2">
          <li>
            <strong>Supabase:</strong> Authentication and database
          </li>
          <li>
            <strong>Vercel:</strong> Hosting and analytics
          </li>
          <li>
            <strong>AI Providers:</strong> (Claude, GPT) for generating work
            outputs
          </li>
        </ul>

        <h2 className="text-xl font-semibold mt-8 mb-4">5. Your Rights</h2>
        <p>You have the right to:</p>
        <ul className="list-disc pl-6 space-y-2">
          <li>Access your personal data</li>
          <li>Request deletion of your account and data</li>
          <li>Export your content</li>
          <li>Opt out of non-essential communications</li>
        </ul>

        <h2 className="text-xl font-semibold mt-8 mb-4">6. Data Retention</h2>
        <p>
          We retain your data for as long as your account is active. Upon
          account deletion, we will remove your personal data within 30 days,
          except where required by law.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-4">7. Changes to This Policy</h2>
        <p>
          We may update this policy and will notify you of material changes.
          Continued use after changes constitutes acceptance.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-4">8. Contact Us</h2>
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
    </div>
  );
}
