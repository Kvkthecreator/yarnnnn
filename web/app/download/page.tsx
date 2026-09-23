import type { Metadata } from "next";
import { getMarketingMetadata } from "@/lib/metadata";
import { MarketingIntlScope } from "@/components/marketing/MarketingIntlScope";
import { DownloadPageBody } from "@/components/marketing/DownloadPageBody";

/**
 * English — `/download`, unprefixed. Korean twin at `/ko/download`.
 *
 * The desktop app's one public page: every download and every "how do I open
 * it" link in the product lands here (lib/shell/desktop-app.ts). The files
 * themselves are served through `/download/{platform}`.
 */

export const metadata: Metadata = getMarketingMetadata({
  title: "Download yarnnn for Mac and Windows",
  description:
    "The yarnnn desktop app for Mac and Windows. The same workspace you use in the browser, in its own window. Free on every plan.",
  path: "/download",
  locale: "en",
  keywords: ["yarnnn download", "yarnnn desktop app", "yarnnn mac", "yarnnn windows"],
});

export default function DownloadPage() {
  return (
    <MarketingIntlScope locale="en">
      <DownloadPageBody locale="en" />
    </MarketingIntlScope>
  );
}
