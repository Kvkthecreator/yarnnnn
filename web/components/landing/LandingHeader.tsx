"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Menu, X } from "lucide-react";
import { Wordmark } from "@/components/shared/Wordmark";
import { DEFAULT_LOCALE, type Locale } from "@/i18n/config";
import { localePath, isTranslatedPath } from "@/lib/marketing/locale";
import { MarketingLanguageToggle } from "@/components/marketing/MarketingLanguageToggle";

/**
 * The marketing header.
 *
 * ⚠️ This component calls NO translation hook, deliberately. It is rendered by
 * every marketing page, including the ones that stay English by ruling
 * (`/privacy`, `/terms`, `/invest`, `/developers`, the blog), and those render
 * OUTSIDE `MarketingIntlScope`. `useTranslations` throws outside a provider, so
 * a hook here would be a runtime crash on pages that every static check passes
 * — the ADR-660 D8 hazard exactly, one layer out.
 *
 * So its words arrive as `nav`, and `locale` decides where its links point. An
 * untranslated page simply omits both and gets the English it always had.
 */

export interface LandingHeaderNav {
  howItWorks: string;
  pricing: string;
  faq: string;
  blog: string;
  about: string;
  signIn: string;
  menu: string;
}

const EN: LandingHeaderNav = {
  howItWorks: "How it works",
  pricing: "Pricing",
  faq: "FAQ",
  blog: "Blog",
  about: "About",
  signIn: "Sign In",
  menu: "Toggle menu",
};

interface LandingHeaderProps {
  inverted?: boolean;
  /** The locale this page renders in. Absent → English, unprefixed links. */
  locale?: Locale;
  /** Worded nav labels. Absent → the English defaults above. */
  nav?: LandingHeaderNav;
  /** This page's canonical (English) path, for the language toggle. */
  path?: string;
}

export default function LandingHeader({
  inverted,
  locale = DEFAULT_LOCALE,
  nav = EN,
  path,
}: LandingHeaderProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const linkClass = inverted
    ? "text-white/70 hover:text-white"
    : "text-muted-foreground hover:text-foreground";

  // A link points into this page's language only where that language HAS the
  // page. `/blog` and `/about` are English-only by ruling, so they stay bare
  // rather than becoming a `/ko/blog` that does not exist.
  const to = (href: string) => (isTranslatedPath(href) ? localePath(href, locale) : href);

  const navLinks = [
    { href: "/how-it-works", label: nav.howItWorks },
    { href: "/pricing", label: nav.pricing },
    { href: "/faq", label: nav.faq },
    { href: "/blog", label: nav.blog },
    { href: "/about", label: nav.about },
  ];

  return (
    <header
      className={`relative w-full py-4 px-6 flex justify-between items-center border-b ${
        inverted ? "border-white/10" : "border-border"
      }`}
    >
      <Link href={localePath("/", locale)} className="flex items-center gap-2">
        <Image
          src="/assets/logos/circleonly_yarnnn.png"
          alt="yarnnn"
          width={32}
          height={32}
          className={inverted ? "invert" : ""}
        />
        <Wordmark className={`text-xl ${inverted ? "text-white" : ""}`} />
      </Link>

      {/* Desktop nav */}
      <nav className="hidden md:flex items-center gap-6">
        {navLinks.map((link) => (
          <Link
            key={link.href}
            href={to(link.href)}
            className={`transition-colors ${linkClass}`}
          >
            {link.label}
          </Link>
        ))}
        {path && (
          <MarketingLanguageToggle locale={locale} path={path} inverted={inverted} />
        )}
        <Link
          href="/auth/login"
          className={`px-4 py-2 rounded-full transition-colors ${
            inverted
              ? "bg-white text-black hover:bg-white/90"
              : "bg-primary text-primary-foreground hover:bg-primary/90"
          }`}
        >
          {nav.signIn}
        </Link>
      </nav>

      {/* Mobile menu button */}
      <button
        className={`md:hidden p-2 ${inverted ? "text-white" : "text-[#1a1a1a]"}`}
        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        aria-label={nav.menu}
      >
        {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
      </button>

      {/* Mobile nav overlay */}
      {mobileMenuOpen && (
        <div
          className={`absolute top-full left-0 right-0 z-50 border-b ${
            inverted
              ? "bg-[#0f1419] border-white/10"
              : "bg-[#faf8f5] border-border"
          }`}
        >
          <nav className="flex flex-col p-6 gap-4">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={to(link.href)}
                className={`transition-colors text-lg ${linkClass}`}
                onClick={() => setMobileMenuOpen(false)}
              >
                {link.label}
              </Link>
            ))}
            {path && (
              <MarketingLanguageToggle
                locale={locale}
                path={path}
                inverted={inverted}
                className="pt-2"
              />
            )}
            <Link
              href="/auth/login"
              className={`mt-2 px-4 py-3 rounded-full text-center transition-colors ${
                inverted
                  ? "bg-white text-black hover:bg-white/90"
                  : "bg-primary text-primary-foreground hover:bg-primary/90"
              }`}
              onClick={() => setMobileMenuOpen(false)}
            >
              {nav.signIn}
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}
