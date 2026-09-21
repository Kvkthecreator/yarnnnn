import type { Metadata } from "next";
import { getMarketingMetadata } from "@/lib/metadata";
import { MarketingIntlScope } from "@/components/marketing/MarketingIntlScope";
import { SupportPageBody } from "@/components/marketing/SupportPageBody";

/**
 * English — `/support`, unprefixed. Korean twin at `/ko/support`.
 *
 * 2026-09-17: /support, /contact and /help all 404'd on production, and a
 * support page is a REQUIRED FIELD on two external listings — the absence was
 * a submission blocker, not a nicety. One canonical page, two redirect stubs
 * (/contact, /help → here, ADR-308 pure server redirect); three near-duplicate
 * pages would split the SEO and give the required field three answers.
 */

export const metadata: Metadata = getMarketingMetadata({
  title: "Support — get help with yarnnn",
  description:
    "How to reach yarnnn: email support, the feedback form, the FAQ, and the developer docs. What to include so we can help on the first reply.",
  path: "/support",
  locale: "en",
  keywords: ["yarnnn support", "yarnnn contact", "yarnnn help", "contact yarnnn"],
});

export default function SupportPage() {
  return (
    <MarketingIntlScope locale="en">
      <SupportPageBody locale="en" />
    </MarketingIntlScope>
  );
}
