import type { Metadata } from "next";
import Link from "next/link";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { SpotlightCard } from "@/components/landing/SpotlightCard";
import { ScrollReveal } from "@/components/landing/ScrollReveal";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

const MCP_URL = "https://mcp.yarnnn.com";

export const metadata: Metadata = getMarketingMetadata({
  title: "yarnnn developer resources — API, MCP server, OpenAPI, auth",
  description:
    "Build with yarnnn. The MCP connector, OpenAPI specification, OAuth 2.1 authentication, and discovery endpoints — everything an AI agent or developer needs to read and write durable, attributed memory.",
  path: "/developers",
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

// Each resource is a named, predictable, linkable URL — the thing an agent (or
// a name-based search) surfaces when it looks for "yarnnn" developer resources.
const RESOURCES = [
  {
    name: "MCP connector",
    href: MCP_URL,
    external: true,
    what: "The Model Context Protocol server. Connect any MCP-capable assistant — ChatGPT, Claude, and others — to read and write yarnnn memory directly.",
    detail: "Transport: streamable-http · Auth: OAuth 2.1",
  },
  {
    name: "OpenAPI specification",
    href: "/openapi.json",
    external: false,
    what: "The machine-readable API contract (OpenAPI 3.1). Describes yarnnn's agent-facing verbs — remember, recall, trace — with request and response schemas.",
    detail: "GET /openapi.json",
  },
  {
    name: "MCP discovery card",
    href: "/.well-known/mcp.json",
    external: false,
    what: "The website→server breadcrumb. Advertises the MCP server, its transport, OAuth metadata location, and tool list so agents can auto-discover the connector.",
    detail: "GET /.well-known/mcp.json",
  },
  {
    name: "OAuth 2.1 authorization metadata",
    href: `${MCP_URL}/.well-known/oauth-authorization-server`,
    external: true,
    what: "The authorization-server metadata for the MCP connector. Standard OAuth 2.1 discovery — endpoints, supported grants, and scopes.",
    detail: "GET /.well-known/oauth-authorization-server",
  },
  {
    name: "llms.txt",
    href: "/llms.txt",
    external: false,
    what: "A plain-text summary of yarnnn for language models — what the product is, how to connect over MCP, and where the key resources live.",
    detail: "GET /llms.txt",
  },
  {
    name: "Product docs",
    href: "https://yarnnn.gitbook.io/docs",
    external: true,
    what: "Human-facing documentation — concepts, the substrate model, and guides for getting the most out of yarnnn.",
    detail: "GitBook",
  },
];

const VERBS = [
  {
    name: "remember",
    signature: "remember(content, about?)",
    what: "Save something worth keeping — a decision, fact, or preference. The write is synchronous and durable: the moment it returns, the memory is stored, attributed, and retrievable.",
  },
  {
    name: "recall",
    signature: "recall(subject, question?, domain?, limit?)",
    what: "Pull what the user already knows about a subject. Returns the stored material plus a confidence signal; the host assistant explains it.",
  },
  {
    name: "trace",
    signature: "trace(subject, limit?)",
    what: "Show how a recorded fact changed over time — who changed it, when, and what changed. The capability a plain storage connector cannot show.",
  },
];

export default function DevelopersPage() {
  // TechArticle + SoftwareApplication reference so this page is identifiable as
  // yarnnn's developer resource hub programmatically.
  const structuredData = {
    "@context": "https://schema.org",
    "@type": "TechArticle",
    headline: "yarnnn developer resources — API, MCP server, OpenAPI, auth",
    description: metadata.description ?? undefined,
    url: `${BRAND.url}/developers`,
    author: { "@type": "Organization", name: BRAND.name, url: BRAND.url },
    publisher: { "@id": `${BRAND.url}/#organization` },
    about: { "@id": `${BRAND.url}/#software` },
  };

  return (
    <div className="relative min-h-screen flex flex-col bg-[#0f1419] text-white overflow-x-hidden">
      <GrainOverlay variant="dark" />
      <ShaderBackgroundDark />

      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted />

        <main className="flex-1">
          {/* Hero */}
          <section className="max-w-4xl mx-auto px-6 py-24 md:py-32">
            <div className="text-xs uppercase tracking-widest text-white/40 mb-6">
              yarnnn for developers
            </div>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-medium mb-10 tracking-tight leading-[1.1]">
              Build on <span className="text-[#de5a2b]">durable, attributed memory</span>
            </h1>
            <div className="max-w-2xl space-y-6 text-white/50">
              <p>
                yarnnn exposes a Model Context Protocol (MCP) server so any
                MCP-capable assistant can read and write a user&apos;s shared
                memory — with full provenance. Everything you need to connect an
                agent is below, at predictable URLs.
              </p>
              <p>
                Authentication is OAuth 2.1. The machine-readable contract lives
                at{" "}
                <Link href="/openapi.json" className="text-white underline underline-offset-4 hover:text-[#de5a2b]">
                  yarnnn.com/openapi.json
                </Link>
                .
              </p>
            </div>
          </section>

          {/* Resources */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-16">
                Developer resources
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {RESOURCES.map((r) => {
                  const inner = (
                    <div className="p-6 h-full">
                      <div className="flex items-baseline justify-between gap-3 mb-2">
                        <h3 className="text-lg font-medium text-white">{r.name}</h3>
                        <span className="text-white/30 text-xs shrink-0">
                          {r.external ? "↗" : "→"}
                        </span>
                      </div>
                      <p className="text-white/50 text-sm leading-relaxed mb-3">
                        {r.what}
                      </p>
                      <code className="text-white/40 text-xs font-mono break-all">
                        {r.detail}
                      </code>
                    </div>
                  );
                  return (
                    <SpotlightCard key={r.name} variant="dark" spotlightSize={300}>
                      {r.external ? (
                        <a href={r.href} target="_blank" rel="noopener noreferrer" className="block h-full">
                          {inner}
                        </a>
                      ) : (
                        <Link href={r.href} className="block h-full">
                          {inner}
                        </Link>
                      )}
                    </SpotlightCard>
                  );
                })}
              </div>
            </ScrollReveal>
          </section>

          {/* The three verbs */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                The memory API — three verbs
              </h2>
              <p className="text-white/50 mb-16 max-w-xl">
                The whole surface an agent calls. Documented in full in the{" "}
                <Link href="/openapi.json" className="text-white underline underline-offset-4 hover:text-[#de5a2b]">
                  OpenAPI spec
                </Link>
                .
              </p>

              <div className="space-y-12">
                {VERBS.map((v) => (
                  <div
                    key={v.name}
                    className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6"
                  >
                    <div>
                      <h3 className="text-lg font-medium text-white mb-1">{v.name}</h3>
                      <code className="text-white/40 text-xs font-mono break-all">
                        {v.signature}
                      </code>
                    </div>
                    <div className="text-white/50">
                      <p>{v.what}</p>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollReveal>
          </section>

          {/* Connect CTA */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Connect an agent to yarnnn
              </h2>
              <p className="text-white/50 mb-10 max-w-lg mx-auto">
                Point your MCP-capable assistant at the connector and authorize
                over OAuth 2.1. It can read and write memory immediately.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <a
                  href={MCP_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-block px-8 py-4 bg-white text-black text-lg font-medium rounded-full hover:bg-white/90 transition-colors"
                >
                  MCP connector
                </a>
                <Link
                  href="/openapi.json"
                  className="inline-block px-8 py-4 border border-white/20 text-white text-lg font-medium rounded-full hover:bg-white/10 transition-colors"
                >
                  View the OpenAPI spec
                </Link>
              </div>
            </ScrollReveal>
          </section>
        </main>

        <LandingFooter inverted />
      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
      />
    </div>
  );
}
