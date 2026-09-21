import type { Metadata } from "next";
import { getMarketingMetadata } from "@/lib/metadata";
import { MarketingIntlScope } from "@/components/marketing/MarketingIntlScope";
import { LandingPageBody } from "@/components/marketing/LandingPageBody";

/**
 * The English landing page — `/`, unprefixed and unmoved.
 *
 * The page itself is `components/marketing/LandingPageBody`, rendered here in
 * English and at `/ko` in Korean. One component, two routes: the CANON-LOCK
 * hero arc cannot drift between languages because there is only one of it.
 *
 * English stays at the bare path deliberately (see `lib/marketing/locale.ts`):
 * no live URL moves, so no redirect is introduced and no ranking is disturbed.
 */

export const metadata: Metadata = getMarketingMetadata({
  title: "your true AI-first workspace | yarnnn",
  description:
    "One workspace for you, your people, and the AI you already use. Nothing to set up — and every change signed by whoever made it, human or not.",
  path: "/",
  locale: "en",
  keywords: [
    "ai workspace",
    "ai-first workspace",
    "shared ai workspace",
    "co-work with ai",
    "work with chatgpt and claude together",
    "shared workspace for ai and humans",
    "ai collaboration workspace",
    "ai workspace you own",
    "cross-llm workspace",
  ],
});

export default function LandingPage() {
  return (
    <MarketingIntlScope locale="en">
      <LandingPageBody locale="en" />
    </MarketingIntlScope>
  );
}
