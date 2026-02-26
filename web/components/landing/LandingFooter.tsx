"use client";

import Link from "next/link";
import { useEffect } from "react";

interface LandingFooterProps {
  inverted?: boolean;
}

export default function LandingFooter({ inverted }: LandingFooterProps) {
  const mutedClass = inverted ? "text-background/50" : "text-muted-foreground";
  const hoverClass = inverted ? "hover:text-background" : "hover:text-foreground";

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
        inverted ? "border-background/10" : "border-border"
      }`}
    >
      <div className="max-w-6xl mx-auto">
        {/* Column grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-10 md:gap-8 mb-10">
          {/* Product */}
          <div>
            <div className="text-xs uppercase tracking-widest mb-4 opacity-40">
              Product
            </div>
            <ul className={`space-y-2.5 text-sm ${mutedClass}`}>
              <li>
                <Link href="/how-it-works" className={`${hoverClass} transition-colors`}>
                  How it works
                </Link>
              </li>
              <li>
                <Link href="/pricing" className={`${hoverClass} transition-colors`}>
                  Pricing
                </Link>
              </li>
              <li>
                <Link href="/faq" className={`${hoverClass} transition-colors`}>
                  FAQ
                </Link>
              </li>
            </ul>
          </div>

          {/* Resources */}
          <div>
            <div className="text-xs uppercase tracking-widest mb-4 opacity-40">
              Resources
            </div>
            <ul className={`space-y-2.5 text-sm ${mutedClass}`}>
              <li>
                <Link href="/blog" className={`${hoverClass} transition-colors`}>
                  Blog
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
                <button
                  data-tally-open="pbD88B"
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
            <div className="text-xs uppercase tracking-widest mb-4 opacity-40">
              Company
            </div>
            <ul className={`space-y-2.5 text-sm ${mutedClass}`}>
              <li>
                <Link href="/about" className={`${hoverClass} transition-colors`}>
                  About
                </Link>
              </li>
              <li>
                <a
                  href="mailto:admin@yarnnn.com"
                  className={`${hoverClass} transition-colors`}
                >
                  Contact
                </a>
              </li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <div className="text-xs uppercase tracking-widest mb-4 opacity-40">
              Legal
            </div>
            <ul className={`space-y-2.5 text-sm ${mutedClass}`}>
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
            inverted ? "border-background/10" : "border-border"
          }`}
        >
          <Link href="/" className="font-brand text-lg hover:opacity-80 transition-opacity">
            yarnnn
          </Link>
          <div className={`text-xs ${mutedClass}`}>
            Donggyo-Ro 272-8 3F, Seoul, Korea
          </div>
        </div>
      </div>
    </footer>
  );
}
