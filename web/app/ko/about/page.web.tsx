import type { Metadata } from "next";
import { getMarketingMetadata } from "@/lib/metadata";
import { MarketingIntlScope } from "@/components/marketing/MarketingIntlScope";
import { AboutPageBody } from "@/components/marketing/AboutPageBody";

/** Korean — `/ko/about`. No ` | yarnnn` suffix: the root template adds it. */

export const metadata: Metadata = getMarketingMetadata({
  title: "소개 — AI 회사는 만들 수 없는 AI 중심 워크스페이스",
  description:
    "이제 진짜 일은 AI와 하고, 그 일에는 흘러가는 대화창이 아니라 진짜 워크스페이스가 필요해요. 모든 AI를 가로지르는 워크스페이스는 그중 어느 하나의 것일 수 없어요. 그래서 저희가 만들었어요.",
  path: "/about",
  locale: "ko",
  keywords: ["yarnnn 소개", "AI 중심 워크스페이스", "중립 AI 워크스페이스", "내가 소유하는 AI 워크스페이스"],
});

export default function KoreanAboutPage() {
  return (
    <MarketingIntlScope locale="ko">
      <AboutPageBody locale="ko" />
    </MarketingIntlScope>
  );
}
