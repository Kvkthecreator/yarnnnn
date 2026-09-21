import type { Metadata } from "next";
import { getMarketingMetadata } from "@/lib/metadata";
import { MarketingIntlScope } from "@/components/marketing/MarketingIntlScope";
import { HowItWorksPageBody } from "@/components/marketing/HowItWorksPageBody";

/** English — `/how-it-works`, unprefixed. Korean twin at `/ko/how-it-works`. */

export const metadata: Metadata = getMarketingMetadata({
  title: "How yarnnn works — a real file system for work made with AI",
  description:
    "A shared file system, agents that come with the apps, documents you build and own — every change signed, human or not. And because the work is real files you own, it goes wherever you go.",
  path: "/how-it-works",
  locale: "en",
  keywords: [
    "how yarnnn works",
    "ai workspace",
    "ai file system",
    "co-work with ai",
    "ai agents in your workspace",
    "documents you own",
    "shared workspace for ai and humans",
  ],
});

export default function HowItWorksPage() {
  return (
    <MarketingIntlScope locale="en">
      <HowItWorksPageBody locale="en" />
    </MarketingIntlScope>
  );
}
