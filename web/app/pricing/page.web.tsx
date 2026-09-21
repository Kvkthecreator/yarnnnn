import type { Metadata } from "next";
import { getMarketingMetadata } from "@/lib/metadata";
import { MarketingIntlScope } from "@/components/marketing/MarketingIntlScope";
import { PricingPageBody } from "@/components/marketing/PricingPageBody";

/** English — `/pricing`, unprefixed. Korean twin at `/ko/pricing`. */

export const metadata: Metadata = getMarketingMetadata({
  title: "Pricing — free for two people, a paid seat for every extra teammate",
  description:
    "Your workspace and memory are free for you and a teammate. From the 3rd person, each extra seat is paid; usage is pay-as-you-go from one shared balance the owner funds. AI connections are always free. See every action; never a surprise bill.",
  path: "/pricing",
  locale: "en",
  keywords: ["yarnnn pricing", "ai workspace pricing", "shared ai workspace", "per seat ai pricing", "team ai plan", "usage-based ai pricing", "transparent ai usage"],
});

export default function PricingPage() {
  return (
    <MarketingIntlScope locale="en">
      <PricingPageBody locale="en" />
    </MarketingIntlScope>
  );
}
