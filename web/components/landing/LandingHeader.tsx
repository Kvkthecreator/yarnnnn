"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Menu, X } from "lucide-react";

interface LandingHeaderProps {
  inverted?: boolean;
}

export default function LandingHeader({ inverted }: LandingHeaderProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const linkClass = inverted
    ? "text-background/60 hover:text-background"
    : "text-muted-foreground hover:text-foreground";

  const navLinks = [
    { href: "/how-it-works", label: "How it works" },
    { href: "/pricing", label: "Pricing" },
    { href: "/about", label: "About" },
  ];

  return (
    <header
      className={`relative w-full py-4 px-6 flex justify-between items-center border-b ${
        inverted ? "border-background/10" : "border-border"
      }`}
    >
      <Link href="/" className="flex items-center gap-2">
        <Image
          src="/assets/logos/circleonly_yarnnn.png"
          alt="yarnnn"
          width={32}
          height={32}
          className={inverted ? "invert" : ""}
        />
        <span className="text-xl font-brand">yarnnn</span>
      </Link>

      {/* Desktop nav */}
      <nav className="hidden md:flex items-center gap-6">
        {navLinks.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`transition-colors ${linkClass}`}
          >
            {link.label}
          </Link>
        ))}
        <Link
          href="/auth/login"
          className={`px-4 py-2 rounded-full transition-colors ${
            inverted
              ? "bg-background text-foreground hover:bg-background/90"
              : "bg-primary text-primary-foreground hover:bg-primary/90"
          }`}
        >
          Sign In
        </Link>
      </nav>

      {/* Mobile menu button */}
      <button
        className={`md:hidden p-2 ${inverted ? "text-background" : "text-foreground"}`}
        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        aria-label="Toggle menu"
      >
        {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
      </button>

      {/* Mobile nav overlay */}
      {mobileMenuOpen && (
        <div
          className={`absolute top-full left-0 right-0 z-50 border-b ${
            inverted
              ? "bg-[#0f1419] border-background/10"
              : "bg-[#faf8f5] border-border"
          }`}
        >
          <nav className="flex flex-col p-6 gap-4">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`transition-colors text-lg ${linkClass}`}
                onClick={() => setMobileMenuOpen(false)}
              >
                {link.label}
              </Link>
            ))}
            <Link
              href="/auth/login"
              className={`mt-2 px-4 py-3 rounded-full text-center transition-colors ${
                inverted
                  ? "bg-background text-foreground hover:bg-background/90"
                  : "bg-primary text-primary-foreground hover:bg-primary/90"
              }`}
              onClick={() => setMobileMenuOpen(false)}
            >
              Sign In
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}
