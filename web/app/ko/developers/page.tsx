import type { Metadata } from "next";
import { getMarketingMetadata } from "@/lib/metadata";
import { MarketingIntlScope } from "@/components/marketing/MarketingIntlScope";
import { DevelopersPageBody } from "@/components/marketing/DevelopersPageBody";

/** Korean — `/ko/developers`. No ` | yarnnn` suffix: the root template adds it. */

export const metadata: Metadata = getMarketingMetadata({
  title: "yarnnn 개발자 리소스 — API, MCP 서버, OpenAPI, 인증",
  description:
    "yarnnn 위에 만들어 보세요. MCP 커넥터, OpenAPI 명세, OAuth 2.1 인증, 디스커버리 엔드포인트까지 — AI 에이전트나 개발자가 모든 변경에 이름이 남는 워크스페이스를 읽고 쓰는 데 필요한 모든 것이에요.",
  path: "/developers",
  locale: "ko",
  keywords: ["yarnnn API", "yarnnn MCP 서버", "MCP 커넥터", "OpenAPI 명세", "AI 메모리 API"],
});

export default function KoreanDevelopersPage() {
  return (
    <MarketingIntlScope locale="ko">
      <DevelopersPageBody locale="ko" />
    </MarketingIntlScope>
  );
}
