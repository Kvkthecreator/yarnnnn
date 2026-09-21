import type { Metadata } from "next";
import { getMarketingMetadata } from "@/lib/metadata";
import { MarketingIntlScope } from "@/components/marketing/MarketingIntlScope";
import { DevelopersPageBody } from "@/components/marketing/DevelopersPageBody";

/** English — `/developers`, unprefixed. Korean twin at `/ko/developers`. */

export const metadata: Metadata = getMarketingMetadata({
  title: "yarnnn developer resources — API, MCP server, OpenAPI, auth",
  description:
    "Build with yarnnn. The MCP connector, OpenAPI specification, OAuth 2.1 authentication, and discovery endpoints — everything an AI agent or developer needs to read and write a workspace where every change is signed.",
  path: "/developers",
  locale: "en",
  keywords: [
    "yarnnn api",
    "yarnnn developer docs",
    "yarnnn openapi",
    "yarnnn mcp server",
    "yarnnn mcp connector",
    "yarnnn oauth",
    "ai memory api",
    "mcp memory connector",
    "model context protocol memory",
  ],
});

export default function DevelopersPage() {
  return (
    <MarketingIntlScope locale="en">
      <DevelopersPageBody locale="en" />
    </MarketingIntlScope>
  );
}
