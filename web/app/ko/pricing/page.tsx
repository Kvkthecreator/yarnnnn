import type { Metadata } from "next";
import { getMarketingMetadata } from "@/lib/metadata";
import { MarketingIntlScope } from "@/components/marketing/MarketingIntlScope";
import { PricingPageBody } from "@/components/marketing/PricingPageBody";

/** Korean — `/ko/pricing`. No ` | yarnnn` suffix: the root template adds it. */

export const metadata: Metadata = getMarketingMetadata({
  title: "요금제 — 두 명까지 무료, 그 다음부터 좌석제",
  description:
    "워크스페이스와 메모리는 회원님과 동료 한 명까지 무료예요. 세 번째 사람부터 좌석마다 요금이 붙고, 사용량은 소유자가 채우는 공용 잔액에서 쓴 만큼 나가요. AI 연결은 언제나 무료예요.",
  path: "/pricing",
  locale: "ko",
  keywords: ["yarnnn 요금제", "AI 워크스페이스 요금", "AI 협업 툴 가격", "좌석제 요금", "사용량 기반 요금"],
});

export default function KoreanPricingPage() {
  return (
    <MarketingIntlScope locale="ko">
      <PricingPageBody locale="ko" />
    </MarketingIntlScope>
  );
}
