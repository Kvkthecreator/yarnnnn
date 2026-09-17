import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { getMarketingMetadata } from "@/lib/metadata";
import { FEEDBACK_FORM } from "@/lib/cta";

/**
 * /support — the one support surface.
 *
 * 2026-09-17: /support, /contact and /help all 404'd (verified live at
 * www.yarnnn.com; the apex 308 is only the www redirect, /faq returned 200
 * through the same hop). A support page is a REQUIRED FIELD on two external
 * listings, so the absence was a submission blocker, not a nicety.
 *
 * One canonical page, two redirect stubs (/contact, /help → here, ADR-308
 * pure server redirect). Three near-duplicate pages would split the SEO and
 * give the required field three answers.
 *
 * The address is admin@yarnnn.com because it is the only one the product
 * actually publishes today — the privacy policy and the landing footer both
 * carry it. A dedicated support@ alias would read better and was declined:
 * publishing an address whose routing is unverified on a required field is
 * worse than publishing a plainer one that demonstrably reaches someone.
 *
 * The feedback door is FEEDBACK_FORM (lib/cta.ts) — the same Tally form the
 * footer and the in-app account menu open, so a visitor's report and a
 * member's land in the same place. One form, now three doors.
 */

export const metadata = getMarketingMetadata({
  title: "Support — get help with yarnnn",
  description:
    "How to reach yarnnn: email support, the feedback form, the FAQ, and the developer docs. What to include so we can help on the first reply.",
  path: "/support",
  keywords: ["yarnnn support", "yarnnn contact", "yarnnn help", "contact yarnnn"],
});

const SUPPORT_EMAIL = "admin@yarnnn.com";

export default function SupportPage() {
  return (
    <div className="relative min-h-screen flex flex-col bg-[#0f1419] text-white overflow-x-hidden">
      <GrainOverlay variant="dark" />
      <ShaderBackgroundDark />

      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted />

        <main className="flex-1">
          <section className="max-w-3xl mx-auto px-6 py-24 md:py-32">
            <h1 className="text-4xl md:text-5xl font-medium mb-4 tracking-tight leading-[1.1]">
              Support
            </h1>
            <p className="text-white/50 mb-16 max-w-xl">
              Email us, or start with the answers below. We read everything that
              comes in and reply within two working days.
            </p>

            <div className="space-y-16">
              <div>
                <h2 className="text-xs text-white/30 uppercase tracking-widest mb-8">
                  Reach a person
                </h2>

                <div className="border-b border-white/5 pb-8">
                  <h3 className="text-lg font-medium mb-3">Email</h3>
                  <p className="text-white/50 leading-relaxed mb-4">
                    Write to{" "}
                    <a
                      href={`mailto:${SUPPORT_EMAIL}`}
                      className="text-white underline underline-offset-4 hover:text-white/80 transition-colors"
                    >
                      {SUPPORT_EMAIL}
                    </a>{" "}
                    for anything — an account or billing question, something
                    broken, a privacy or data request, or a question before you
                    sign up. It reaches the people who build yarnnn, not a queue.
                  </p>
                  <p className="text-white/50 leading-relaxed">
                    So we can help on the first reply, tell us the email address
                    on your account, what you expected to happen, and what
                    happened instead. If it involves a specific file, its name
                    helps — never send us a password.
                  </p>
                </div>

                <div className="border-b border-white/5 py-8">
                  <h3 className="text-lg font-medium mb-3">Report something</h3>
                  <p className="text-white/50 leading-relaxed">
                    The{" "}
                    <a
                      href={FEEDBACK_FORM.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-white underline underline-offset-4 hover:text-white/80 transition-colors"
                    >
                      feedback form
                    </a>{" "}
                    is the fastest way to send a bug or a request without
                    writing an email. It lands in the same place, and you can
                    leave an address if you want a reply.
                  </p>
                </div>

                <div className="py-8">
                  <h3 className="text-lg font-medium mb-3">Your data</h3>
                  <p className="text-white/50 leading-relaxed">
                    To export, correct or delete your workspace, email the
                    address above from your account address and say what you
                    want done. What we hold and who can receive it is set out on
                    the{" "}
                    <Link
                      href="/privacy"
                      className="text-white underline underline-offset-4 hover:text-white/80 transition-colors"
                    >
                      privacy page
                    </Link>
                    .
                  </p>
                </div>
              </div>

              <div>
                <h2 className="text-xs text-white/30 uppercase tracking-widest mb-8">
                  Answer it yourself
                </h2>

                <div className="space-y-8">
                  <div className="border-b border-white/5 pb-8">
                    <h3 className="text-lg font-medium mb-3">
                      <Link href="/faq" className="underline underline-offset-4 decoration-white/25 hover:decoration-white/60 transition-colors">
                        FAQ
                      </Link>
                    </h3>
                    <p className="text-white/50 leading-relaxed">
                      How yarnnn differs from built-in AI memory, what happens
                      to your work, what pricing costs, and how to start.
                    </p>
                  </div>

                  <div className="border-b border-white/5 pb-8">
                    <h3 className="text-lg font-medium mb-3">
                      <Link href="/how-it-works" className="underline underline-offset-4 decoration-white/25 hover:decoration-white/60 transition-colors">
                        How it works
                      </Link>
                    </h3>
                    <p className="text-white/50 leading-relaxed">
                      The shape of the product — connecting an AI, putting work
                      in, and getting it back out.
                    </p>
                  </div>

                  <div className="pb-8">
                    <h3 className="text-lg font-medium mb-3">
                      <a
                        href="https://yarnnn.gitbook.io/docs"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="underline underline-offset-4 decoration-white/25 hover:decoration-white/60 transition-colors"
                      >
                        Documentation
                      </a>
                    </h3>
                    <p className="text-white/50 leading-relaxed">
                      Setup guides and reference, including the MCP connector.
                      Building against yarnnn? Start at{" "}
                      <Link
                        href="/developers"
                        className="text-white underline underline-offset-4 hover:text-white/80 transition-colors"
                      >
                        developers
                      </Link>
                      .
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-24 text-center">
              <h2 className="text-2xl font-medium mb-4">Still stuck?</h2>
              <p className="text-white/50 mb-8">
                Send us the details and we'll take a look.
              </p>
              <a
                href={`mailto:${SUPPORT_EMAIL}`}
                className="inline-block px-8 py-3 bg-white text-black font-medium rounded-full hover:bg-white/90 transition-colors"
              >
                Email support
              </a>
            </div>
          </section>
        </main>

        <LandingFooter inverted />
      </div>
    </div>
  );
}
