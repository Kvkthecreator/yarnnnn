"use client";

import Link from "next/link";
import { useEffect } from "react";
import { Wordmark } from "@/components/shared/Wordmark";
import { FEEDBACK_FORM } from "@/lib/cta";
import { DEFAULT_LOCALE, type Locale } from "@/i18n/config";
import { localePath, isTranslatedPath } from "@/lib/marketing/locale";

/**
 * The marketing footer.
 *
 * ⚠️ Calls NO translation hook, for the same reason `LandingHeader` does not:
 * it renders on every marketing page, including the ones that stay English by
 * ruling and therefore render OUTSIDE `MarketingIntlScope`, where
 * `useTranslations` throws. Words arrive as props; `locale` steers the links.
 */

export interface LandingFooterWords {
  product: string;
  resources: string;
  company: string;
  legal: string;
  howItWorks: string;
  pricing: string;
  faq: string;
}

const EN: LandingFooterWords = {
  product: "Product",
  resources: "Resources",
  company: "Company",
  legal: "Legal",
  howItWorks: "How it works",
  pricing: "Pricing",
  faq: "FAQ",
};

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
  // Only a path that EXISTS in this locale is prefixed; everything else stays
  // bare rather than becoming a /ko URL that 404s.
  const to = (href: string) => (isTranslatedPath(href) ? localePath(href, locale) : href);
  const mutedClass = inverted ? "text-white/50" : "text-muted-foreground";
  const hoverClass = inverted ? "hover:text-white" : "hover:text-foreground";
  const headingClass = inverted ? "text-white/40" : "opacity-40";

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
      className={`border-t py-12 px-6 ${
        inverted ? "border-white/10" : "border-border"
      }`}
    >
      <div className="max-w-6xl mx-auto">
        {/* Column grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-10 md:gap-8 mb-10">
          {/* Product */}
          <div>
            <div className={`text-xs uppercase tracking-widest mb-4 ${headingClass}`}>
              {words.product}
            </div>
            <ul className={`space-y-2.5 text-sm ${mutedClass}`}>
              <li>
                <Link href={to("/how-it-works")} className={`${hoverClass} transition-colors`}>
                  {words.howItWorks}
                </Link>
              </li>
              <li>
                <Link href={to("/pricing")} className={`${hoverClass} transition-colors`}>
                  {words.pricing}
                </Link>
              </li>
              <li>
                <Link href="/engines" className={`${hoverClass} transition-colors`}>
                  Choosing an engine
                </Link>
              </li>
              <li>
                <Link href={to("/faq")} className={`${hoverClass} transition-colors`}>
                  {words.faq}
                </Link>
              </li>
            </ul>
          </div>

          {/* Resources */}
          <div>
            <div className={`text-xs uppercase tracking-widest mb-4 ${headingClass}`}>
              {words.resources}
            </div>
            <ul className={`space-y-2.5 text-sm ${mutedClass}`}>
              <li>
                <Link href="/blog" className={`${hoverClass} transition-colors`}>
                  Blog
                </Link>
              </li>
              <li>
                <Link href="/developers" className={`${hoverClass} transition-colors`}>
                  Developers
                </Link>
              </li>
              <li>
                <Link
                  href="https://yarnnn.gitbook.io/docs"
                  className={`${hoverClass} transition-colors`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Docs
                </Link>
              </li>
              <li>
                <Link href="/support" className={`${hoverClass} transition-colors`}>
                  Support
                </Link>
              </li>
              <li>
                <button
                  data-tally-open={FEEDBACK_FORM.id}
                  data-tally-width="400"
                  data-tally-overlay="1"
                  data-tally-emoji-animation="none"
                  className={`${hoverClass} transition-colors`}
                >
                  Share feedback
                </button>
              </li>
            </ul>
          </div>

          {/* Company */}
          <div>
            <div className={`text-xs uppercase tracking-widest mb-4 ${headingClass}`}>
              {words.company}
            </div>
            <ul className={`space-y-2.5 text-sm ${mutedClass}`}>
              <li>
                <Link href="/about" className={`${hoverClass} transition-colors`}>
                  About
                </Link>
              </li>
              <li>
                <Link href="/invest" className={`${hoverClass} transition-colors`}>
                  Investors
                </Link>
              </li>
              <li>
                <Link href="/support" className={`${hoverClass} transition-colors`}>
                  Contact
                </Link>
              </li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <div className={`text-xs uppercase tracking-widest mb-4 ${headingClass}`}>
              {words.legal}
            </div>
            <ul className={`space-y-2.5 text-sm ${mutedClass}`}>
              <li>
                <Link href="/privacy-architecture" className={`${hoverClass} transition-colors`}>
                  Your data
                </Link>
              </li>
              <li>
                <Link href="/privacy" className={`${hoverClass} transition-colors`}>
                  Privacy
                </Link>
              </li>
              <li>
                <Link href="/terms" className={`${hoverClass} transition-colors`}>
                  Terms
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div
          className={`border-t pt-6 flex flex-col md:flex-row items-center justify-between gap-4 ${
            inverted ? "border-white/10" : "border-border"
          }`}
        >
          <Link href={localePath("/", locale)} className={`hover:opacity-80 transition-opacity ${inverted ? "text-white" : ""}`}>
            <Wordmark className="text-lg" />
          </Link>
          <div className={`text-xs ${mutedClass}`}>
            Donggyo-Ro 272-8 3F, Seoul, Korea
          </div>
        </div>
      </div>
    </footer>
  );
}
