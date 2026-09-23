import type { Metadata } from "next";
import { getMarketingMetadata } from "@/lib/metadata";
import { MarketingIntlScope } from "@/components/marketing/MarketingIntlScope";
import { HowItWorksPageBody } from "@/components/marketing/HowItWorksPageBody";

/** Korean — `/ko/how-it-works`. No ` | yarnnn` suffix: the root template adds it. */

export const metadata: Metadata = getMarketingMetadata({
  title: "yarnnn 작동 방식 — AI와 만든 일이 실제로 쌓이는 파일 시스템",
  description:
    "함께 쓰는 파일 시스템, 앱과 함께 오는 에이전트, 회원님 것으로 남는 문서. 사람이든 AI든 모든 변경에 이름이 남아요. 그리고 일이 진짜 파일이기 때문에, 어디로든 함께 갈 수 있어요.",
  path: "/how-it-works",
  locale: "ko",
  keywords: ["yarnnn 작동 방식", "AI 워크스페이스", "AI 파일 시스템", "AI와 협업", "MCP 연결"],
});

export default function KoreanHowItWorksPage() {
  return (
    <MarketingIntlScope locale="ko">
      <HowItWorksPageBody locale="ko" />
    </MarketingIntlScope>
  );
}
