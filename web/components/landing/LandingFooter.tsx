"use client";

import Link from "next/link";
import { useEffect } from "react";
import { Download } from "lucide-react";
import { Wordmark } from "@/components/shared/Wordmark";
import { FEEDBACK_FORM } from "@/lib/cta";
import { DEFAULT_LOCALE, type Locale } from "@/i18n/config";
import { localePath } from "@/lib/marketing/locale";

/**
 * The marketing footer.
 *
 * ⚠️ Calls NO translation hook, for the same reason `LandingHeader` does not:
 * it renders on every marketing page, including the ones that stay English by
 * ruling and therefore render OUTSIDE `MarketingIntlScope`, where
 * `useTranslations` throws. Words arrive as props; `locale` steers the links.
 *
 * EVERY label is a prop and EVERY internal link goes through `localePath`,
 * which prefixes only a path that has a Korean page. The first version worded
 * five links and hard-coded the rest, so the Korean footer was half English
 * and sent /about, /developers and /support to their English pages beside
 * Korean twins. `EN` below mirrors `marketing.footer` + `marketing.nav` in
 * `messages/en.json` (the catalog is too large to import into a client
 * bundle); the ADR-660 gate holds the two equal.
 */

export interface LandingFooterWords {
  tagline: string;
  desktopApp: string;
  product: string;
  resources: string;
  company: string;
  legal: string;
  howItWorks: string;
  pricing: string;
  engines: string;
  faq: string;
  download: string;
  blog: string;
  developers: string;
  docs: string;
  support: string;
  feedback: string;
  about: string;
  invest: string;
  yourData: string;
  privacy: string;
  terms: string;
  rights: string;
}

const EN: LandingFooterWords = {
  tagline: "One workspace for you, your people, and the AI you already use.",
  desktopApp: "Get the desktop app",
  product: "Product",
  resources: "Resources",
  company: "Company",
  legal: "Legal",
  howItWorks: "How it works",
  pricing: "Pricing",
  engines: "Choosing an engine",
  faq: "FAQ",
  download: "Download",
  blog: "Blog",
  developers: "Developers",
  docs: "Docs",
  support: "Support",
  feedback: "Share feedback",
  about: "About",
  invest: "Investors",
  yourData: "Your data",
  privacy: "Privacy",
  terms: "Terms",
  rights: "All rights reserved.",
};

const DOCS_URL = "https://yarnnn.gitbook.io/docs";

interface LandingFooterProps {
  inverted?: boolean;
  /** The locale this page renders in. Absent → English, unprefixed links. */
  locale?: Locale;
  /** Worded labels. Absent → the English defaults above. */
  words?: LandingFooterWords;
}

export default function LandingFooter({
  inverted,
  locale = DEFAULT_LOCALE,
  words = EN,
}: LandingFooterProps) {
  const mutedClass = inverted ? "text-white/50" : "text-muted-foreground";
  const hoverClass = inverted ? "hover:text-white" : "hover:text-foreground";
  const headingClass = inverted ? "text-white/35" : "opacity-40";
  const linkClass = `${hoverClass} transition-colors`;

  // `href: null` is the feedback form: a Tally overlay, not a page.
  const columns: { heading: string; links: { href: string | null; label: string }[] }[] = [
    {
      heading: words.product,
      links: [
        { href: "/how-it-works", label: words.howItWorks },
        { href: "/pricing", label: words.pricing },
        { href: "/engines", label: words.engines },
        { href: "/faq", label: words.faq },
        { href: "/download", label: words.download },
      ],
    },
    {
      heading: words.resources,
      links: [
        { href: "/blog", label: words.blog },
        { href: "/developers", label: words.developers },
        { href: DOCS_URL, label: words.docs },
        { href: "/support", label: words.support },
        { href: null, label: words.feedback },
      ],
    },
    {
      heading: words.company,
      links: [
        { href: "/about", label: words.about },
        { href: "/invest", label: words.invest },
      ],
    },
    {
      heading: words.legal,
      links: [
        { href: "/privacy-architecture", label: words.yourData },
        { href: "/privacy", label: words.privacy },
        { href: "/terms", label: words.terms },
      ],
    },
  ];

  // Load Tally embed script
  useEffect(() => {
    const script = document.createElement("script");
    script.src = "https://tally.so/widgets/embed.js";
    script.async = true;
    document.body.appendChild(script);

    return () => {
      document.body.removeChild(script);
    };
  }, []);

  return (
    <footer
      className={`border-t pt-14 pb-10 px-6 ${
        inverted ? "border-white/10" : "border-border"
      }`}
    >
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-6 gap-x-8 gap-y-10 mb-12">
          {/* The brand, and the one door that is not a page */}
          <div className="col-span-2">
            <Link
              href={localePath("/", locale)}
              className={`inline-block hover:opacity-80 transition-opacity ${inverted ? "text-white" : ""}`}
            >
              <Wordmark className="text-2xl" />
            </Link>
            <p className={`mt-3 text-sm leading-relaxed max-w-xs ${mutedClass}`}>{words.tagline}</p>
            <Link
              href={localePath("/download", locale)}
              className={`mt-5 inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm transition-colors ${
                inverted
                  ? "border-white/15 text-white/80 hover:bg-white/10 hover:text-white"
                  : "border-border text-foreground/75 hover:bg-foreground/[0.04] hover:text-foreground"
              }`}
            >
              <Download className="h-3.5 w-3.5" aria-hidden="true" />
              {words.desktopApp}
            </Link>
          </div>

          {columns.map((col) => (
            <div key={col.heading}>
              <div className={`text-xs uppercase tracking-widest mb-4 ${headingClass}`}>
                {col.heading}
              </div>
              <ul className={`space-y-2.5 text-sm ${mutedClass}`}>
                {col.links.map((link) => (
                  <li key={link.href ?? "feedback"}>
                    {link.href === null ? (
                      <button
                        data-tally-open={FEEDBACK_FORM.id}
                        data-tally-width="400"
                        data-tally-overlay="1"
                        data-tally-emoji-animation="none"
                        className={linkClass}
                      >
                        {link.label}
                      </button>
                    ) : link.href.startsWith("http") ? (
                      <a href={link.href} className={linkClass} target="_blank" rel="noopener noreferrer">
                        {link.label}
                      </a>
                    ) : (
                      <Link href={localePath(link.href, locale)} className={linkClass}>
                        {link.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div
          className={`border-t pt-6 flex flex-col md:flex-row items-center justify-between gap-3 text-xs ${mutedClass} ${
            inverted ? "border-white/10" : "border-border"
          }`}
        >
          <div>
            © {new Date().getFullYear()} yarnnn. {words.rights}
          </div>
          <div>Donggyo-Ro 272-8 3F, Seoul, Korea</div>
        </div>
      </div>
    </footer>
  );
}
