import type { Metadata } from "next";
import { getMarketingMetadata } from "@/lib/metadata";
import { MarketingIntlScope } from "@/components/marketing/MarketingIntlScope";
import { SupportPageBody } from "@/components/marketing/SupportPageBody";

/** Korean — `/ko/support`. No ` | yarnnn` suffix: the root template adds it. */

export const metadata: Metadata = getMarketingMetadata({
  title: "지원 — yarnnn 도움받기",
  description:
    "yarnnn에 연락하는 방법이에요. 이메일 지원, 의견 보내기 양식, 자주 묻는 질문, 개발자 문서까지. 첫 답장에서 바로 도와드릴 수 있도록 무엇을 적어주시면 좋은지도 안내해요.",
  path: "/support",
  locale: "ko",
  keywords: ["yarnnn 지원", "yarnnn 문의", "yarnnn 도움말"],
});

export default function KoreanSupportPage() {
  return (
    <MarketingIntlScope locale="ko">
      <SupportPageBody locale="ko" />
    </MarketingIntlScope>
  );
}
