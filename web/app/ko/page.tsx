import type { Metadata } from "next";
import { getMarketingMetadata } from "@/lib/metadata";
import { MarketingIntlScope } from "@/components/marketing/MarketingIntlScope";
import { LandingPageBody } from "@/components/marketing/LandingPageBody";

/**
 * The Korean landing page — `/ko`.
 *
 * A route, not a runtime branch: the locale is in the PATH, so this page
 * prerenders statically exactly like its English twin. That is the whole
 * reason marketing uses a prefix where the app refuses one (ADR-660 D1) —
 * a cookie read here would make every marketing route dynamic.
 */

export const metadata: Metadata = getMarketingMetadata({
  // No ` | yarnnn` suffix: `/ko` is NESTED under the root layout, whose
  // `title.template` (`%s | yarnnn`) applies to it. The root page `/` is the
  // template's own level so it must spell the suffix itself — the asymmetry is
  // Next's, and writing the suffix here produced `… | yarnnn | yarnnn`.
  title: "진짜 AI 중심 워크스페이스",
  description:
    "회원님과 동료, 그리고 이미 쓰고 있는 AI가 함께 일하는 하나의 워크스페이스. 설정할 것은 없고, 모든 변경에는 사람이든 AI든 만든 주체의 이름이 남아요.",
  path: "/",
  locale: "ko",
  keywords: [
    "AI 워크스페이스",
    "AI 협업 툴",
    "챗GPT 클로드 함께 쓰기",
    "AI와 함께 일하는 워크스페이스",
    "팀 AI 협업",
  ],
});

export default function KoreanLandingPage() {
  return (
    <MarketingIntlScope locale="ko">
      <LandingPageBody locale="ko" />
    </MarketingIntlScope>
  );
}
