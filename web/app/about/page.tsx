import type { Metadata } from "next";
import { getMarketingMetadata } from "@/lib/metadata";
import { MarketingIntlScope } from "@/components/marketing/MarketingIntlScope";
import { AboutPageBody } from "@/components/marketing/AboutPageBody";

/** English — `/about`, unprefixed. Korean twin at `/ko/about`. */

export const metadata: Metadata = getMarketingMetadata({
  title: "About — the AI-first workspace no AI company can build",
  description:
    "The real work happens with AI now, and it deserves a real workspace — not a chat scroll. One that works across every AI can't be owned by any one of them. So we built it.",
  path: "/about",
  locale: "en",
  keywords: [
    "about yarnnn",
    "ai-first workspace",
    "ai workspace you own",
    "neutral ai workspace",
    "cross-llm workspace",
    "shared workspace for ai and humans",
  ],
});

export default function AboutPage() {
  return (
    <MarketingIntlScope locale="en">
      <AboutPageBody locale="en" />
    </MarketingIntlScope>
  );
}
