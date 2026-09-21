import type { Metadata } from "next";
import { getMarketingMetadata } from "@/lib/metadata";
import { MarketingIntlScope } from "@/components/marketing/MarketingIntlScope";
import { FaqPageBody } from "@/components/marketing/FaqPageBody";

/**
 * The Korean FAQ — `/ko/faq`.
 *
 * No ` | yarnnn` suffix in the title: a nested route inherits the root
 * layout's `title.template`, and spelling the suffix here doubles it.
 */

export const metadata: Metadata = getMarketingMetadata({
  title: "자주 묻는 질문 — 진짜 AI 중심 워크스페이스",
  description:
    "yarnnn이 ChatGPT나 Claude의 내장 메모리와 어떻게 다른지, 'trace'가 무엇인지, AI·팀과의 협업이 실제로 어떻게 남는지, 요금과 시작하는 방법까지 정리했어요.",
  path: "/faq",
  locale: "ko",
  keywords: ["yarnnn 자주 묻는 질문", "AI 워크스페이스 요금", "AI 메모리 공유", "MCP 연결"],
});

export default function KoreanFaqPage() {
  return (
    <MarketingIntlScope locale="ko">
      <FaqPageBody locale="ko" />
    </MarketingIntlScope>
  );
}
