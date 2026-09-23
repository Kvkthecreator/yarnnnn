import type { Metadata } from "next";
import { getMarketingMetadata } from "@/lib/metadata";
import { MarketingIntlScope } from "@/components/marketing/MarketingIntlScope";
import { DownloadPageBody } from "@/components/marketing/DownloadPageBody";

/** Korean — `/ko/download`. No ` | yarnnn` suffix: the root template adds it. */

export const metadata: Metadata = getMarketingMetadata({
  title: "yarnnn 다운로드 — Mac과 Windows용",
  description:
    "Mac과 Windows용 yarnnn 데스크톱 앱이에요. 브라우저에서 쓰던 워크스페이스를 별도의 창에서 그대로 써요. 모든 요금제에서 무료예요.",
  path: "/download",
  locale: "ko",
  keywords: ["yarnnn 다운로드", "yarnnn 데스크톱 앱", "yarnnn 맥", "yarnnn 윈도우"],
});

export default function KoreanDownloadPage() {
  return (
    <MarketingIntlScope locale="ko">
      <DownloadPageBody locale="ko" />
    </MarketingIntlScope>
  );
}
