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
      className={`border-t py-8 px-6 ${
        inverted ? "border-background/10" : "border-border"
      }`}
    >
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        {/* Brand */}
        <div className="flex flex-col items-start gap-2">
          <div className="font-brand text-lg">yarnnn</div>
          <div className={`flex gap-4 text-sm ${mutedClass}`}>
            <Link href="/privacy" className={`${hoverClass} transition-colors`}>
              Privacy
            </Link>
            <Link href="/terms" className={`${hoverClass} transition-colors`}>
              Terms
            </Link>
          </div>
        </div>

        {/* Feedback - Tally Form */}
        <div className="flex flex-col items-center md:items-start gap-2">
          <button
            data-tally-open="pbD88B"
            data-tally-width="400"
            data-tally-overlay="1"
            data-tally-emoji-animation="none"
            className={`text-sm font-medium ${hoverClass} transition-colors underline underline-offset-4`}
          >
            Share feedback
          </button>
        </div>

        {/* Contact */}
        <div className="flex flex-col md:flex-row md:items-center gap-4 md:gap-12 text-sm">
          <div>
            <div className="font-medium mb-1">Office</div>
            <div className={mutedClass}>
              Donggyo-Ro 272-8 3F, Seoul, Korea
            </div>
          </div>
          <div>
            <div className="font-medium mb-1">Contact</div>
            <div className={mutedClass}>
              contactus@yarnnn.com
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
