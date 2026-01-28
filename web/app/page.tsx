import Link from "next/link";
import Image from "next/image";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <LandingHeader />

      {/* Hero Section */}
      <section className="flex-1 flex flex-col items-center justify-center px-6 py-24">
        <div className="max-w-4xl mx-auto text-center">
          <Image
            src="/assets/logos/circleonly_yarnnn.png"
            alt="YARNNN"
            width={80}
            height={80}
            className="mx-auto mb-8"
          />
          <h1 className="text-4xl md:text-6xl font-bold mb-6">
            Your AI understands your world
          </h1>
          <p className="text-xl md:text-2xl text-muted-foreground mb-4">
            Context-aware AI work platform
          </p>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-8">
            Accumulate knowledge. Let AI agents read from your context.
            Get work outputs that actually understand your business.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/auth/login"
              className="px-8 py-3 bg-primary text-primary-foreground rounded-lg text-lg font-medium hover:bg-primary/90 transition-colors"
            >
              Get Started
            </Link>
            <Link
              href="/about"
              className="px-8 py-3 border border-border rounded-lg text-lg font-medium hover:bg-muted transition-colors"
            >
              Learn More
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="border-t border-border px-6 py-24">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold mb-4 text-center">
            Why YARNNN?
          </h2>
          <p className="text-lg text-muted-foreground text-center max-w-2xl mx-auto mb-16">
            In the age of AI, brilliant insights from chats and meetings are lost in digital noise.
            YARNNN gives you persistent, intelligent context that grows with your work.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
            {/* Feature 1 */}
            <div>
              <h3 className="text-xl font-semibold mb-3 flex items-center gap-2">
                <span className="text-2xl">🧠</span> End AI Amnesia
              </h3>
              <p className="text-muted-foreground">
                Stop re-explaining your business to AI every conversation. YARNNN maintains
                persistent context that your agents read from, so every output reflects
                your accumulated knowledge.
              </p>
            </div>

            {/* Feature 2 */}
            <div>
              <h3 className="text-xl font-semibold mb-3 flex items-center gap-2">
                <span className="text-2xl">🔗</span> Structured Knowledge
              </h3>
              <p className="text-muted-foreground">
                Not just notes—blocks of knowledge that connect. Upload documents, add insights,
                and watch your context grow into an interconnected web your AI can navigate.
              </p>
            </div>

            {/* Feature 3 */}
            <div>
              <h3 className="text-xl font-semibold mb-3 flex items-center gap-2">
                <span className="text-2xl">🤖</span> Specialized Agents
              </h3>
              <p className="text-muted-foreground">
                Research agents for deep investigation. Content agents for creation.
                Reporting agents for structured deliverables. Each reads your context
                and produces real work outputs.
              </p>
            </div>

            {/* Feature 4 */}
            <div>
              <h3 className="text-xl font-semibold mb-3 flex items-center gap-2">
                <span className="text-2xl">📋</span> Provenance & Trust
              </h3>
              <p className="text-muted-foreground">
                Every output traces back to source context. Know exactly what information
                informed each report, research summary, or content draft. Full transparency.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="border-t border-border px-6 py-16 bg-muted/30">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-2xl md:text-3xl font-bold mb-4">
            Ready to give your AI real context?
          </h2>
          <p className="text-muted-foreground mb-8">
            Start building your knowledge base today. Your AI agents will thank you.
          </p>
          <Link
            href="/auth/login"
            className="inline-block px-8 py-3 bg-primary text-primary-foreground rounded-lg text-lg font-medium hover:bg-primary/90 transition-colors"
          >
            Start Free
          </Link>
        </div>
      </section>

      <LandingFooter />
    </div>
  );
}
