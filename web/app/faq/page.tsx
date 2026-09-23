import type { Metadata } from "next";
import { getMarketingMetadata } from "@/lib/metadata";
import { MarketingIntlScope } from "@/components/marketing/MarketingIntlScope";
import { FaqPageBody } from "@/components/marketing/FaqPageBody";

/** The English FAQ — `/faq`, unprefixed and unmoved. Korean twin at `/ko/faq`. */

export const metadata: Metadata = getMarketingMetadata({
  title: "FAQ — your true AI-first workspace",
  description:
    "How yarnnn differs from ChatGPT and Claude's built-in memory, what 'trace' is, how co-work with your AIs and your team actually lands, pricing, and how to get started.",
  path: "/faq",
  locale: "en",
  keywords: [
    "yarnnn faq",
    "shared ai memory faq",
    "cross-llm memory faq",
    "portable ai memory",
    "ai memory pricing faq",
  ],
});

export default function FaqPage() {
  return (
    <MarketingIntlScope locale="en">
      <FaqPageBody locale="en" />
    </MarketingIntlScope>
  );
}
