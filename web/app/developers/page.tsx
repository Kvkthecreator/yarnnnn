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
    "Build with yarnnn. The MCP connector, OpenAPI specification, OAuth 2.1 authentication, and discovery endpoints — everything an AI agent or developer needs to read and write an attributed workspace.",
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
    what: "The machine-readable API contract (OpenAPI 3.1). Describes the file-native verbs an agent calls over MCP, with request and response shapes.",
    detail: "GET /openapi.json",
  },
  {
    name: "MCP discovery card",
    href: "/.well-known/mcp.json",
    external: false,
    what: "The website→server breadcrumb. Advertises the MCP server, its transport and where to find its OAuth metadata, so agents can auto-discover the connector.",
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

// The published verb roster. Mirrors `_INTEROP_VERBS` (api/mcp_server/server.py),
// which is the source of truth; `test_gitbook_docs_current.py` asserts the two
// are the same set. ADR-543 retired remember/recall/trace with no aliases, and
// this page kept advertising them — the same drift ADR-635 D9 removed from the
// discovery card. A new verb is a row there plus its @mcp.tool, then a row here.
const VERBS = [
  {
    name: "whoami",
    kind: "read",
    what: "Name where you are standing — which workspace this connection is bound to, who your writes will be signed as, and which verbs your token authorizes. Call it before writing somewhere the user assumed.",
  },
  {
    name: "open",
    kind: "read",
    what: "Read one exact file: its current content, who last changed it, when, and its recent attributed revisions. An unknown path says so — open never guesses.",
  },
  {
    name: "list",
    kind: "read",
    what: "Enumerate the files under a folder. Takes a timestamp for the change feed — what moved since you were last here — and pages through large subtrees.",
  },
  {
    name: "search",
    kind: "read",
    what: "Find files by meaning. Returns ranked matches with excerpts and a confidence signal, so an ambiguous result can be asked about rather than guessed at.",
  },
  {
    name: "history",
    kind: "read",
    what: "Show how one exact file changed over time — who authored each revision, when, what changed, and a diff against its predecessor. The capability a plain storage connector cannot show.",
  },
  {
    name: "save",
    kind: "write",
    what: "Write a file back as an attributed revision. Pass the revision you opened and a concurrent change is refused rather than clobbered; every prior version stays on the chain.",
  },
  {
    name: "edit",
    kind: "write",
    what: "Change part of a file by anchoring on its exact current text. Only the change travels, so content you never read is never at risk — the right verb for large files.",
  },
  {
    name: "delete",
    kind: "write",
    what: "Remove a file from the live workspace. Nothing is lost: the chain keeps the content and the file can be restored.",
  },
  {
    name: "move",
    kind: "write",
    what: "Move or rename a file. Refuses to overwrite an existing destination — that has to be deleted by intent first.",
  },
  {
    name: "request_upload",
    kind: "write",
    what: "Get a short-lived URL for content that arrives as bytes rather than text — an image, a PDF, an export. It lands as an attributed file like any other.",
  },
  {
    name: "share",
    kind: "write",
    what: "Mint a link to one file or the whole workspace, as full access or read-only. Whoever opens it sees the work and who made it.",
  },
];

// The scope tiers, enforced per-verb at the server (ADR-563,
// services/mcp_scopes.py). Additive and ordered: write satisfies read, share
// satisfies both. The sentences are the operator-facing ones from the consent
// screen — a developer and the person approving them should read the same words.
const SCOPES = [
  {
    name: "files:read",
    what: "Read your files — open, list, search, and view their history.",
  },
  {
    name: "files:write",
    what: "Create, edit, move, and delete files. Every change is signed and revertible.",
  },
  {
    name: "files:share",
    what: "Create share links, which can give whoever opens them full member access.",
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
              One workspace, <span className="text-[#de5a2b]">every AI you use</span>
            </h1>
            <div className="max-w-2xl space-y-6 text-white/50">
              <p>
                yarnnn is a Model Context Protocol server. Point any MCP-capable
                assistant at{" "}
                <code className="text-white/70 font-mono text-sm">{MCP_URL.replace("https://", "")}</code>{" "}
                and it reads and writes the same files a person sees — no
                separate memory store, no sync step.
              </p>
              <p>
                Every write is signed by the client that made it and lands on a
                revision chain you can walk. A connection is its own principal in
                the ledger, not a key acting as the user — so{" "}
                <span className="text-white/70">
                  &ldquo;who changed this?&rdquo;
                </span>{" "}
                has a real answer even when the answer is another AI. That is the
                thing a plain storage connector cannot do.
              </p>
              <p>
                Authentication is OAuth 2.1 with dynamic client registration, and
                access is scoped per verb. Everything below is at a predictable
                URL.
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
                          {r.external ? "↗︎" : "→"}
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

          {/* The verb roster */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                The verbs an agent calls
              </h2>
              <p className="text-white/50 mb-16 max-w-xl">
                File-native: they read and write the same files a person sees,
                and every write lands attributed. Documented in full in the{" "}
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
                      <span className="text-white/40 text-xs font-mono">
                        {v.kind === "read" ? "a read" : "a write"}
                      </span>
                    </div>
                    <div className="text-white/50">
                      <p>{v.what}</p>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollReveal>
          </section>

          {/* Scopes */}
          <section className="border-t border-white/10 px-6 py-24 md:py-32">
            <ScrollReveal className="max-w-4xl mx-auto">
              <h2 className="text-2xl md:text-3xl font-medium mb-6">
                Ask for what you need
              </h2>
              <p className="text-white/50 mb-16 max-w-xl">
                Access is scoped per verb and enforced on every call — a token
                holding <code className="text-white/70 font-mono text-sm">files:read</code>{" "}
                is refused when it tries to save. The tiers are additive, and a
                registration that names none gets read-only.
              </p>

              <div className="space-y-8">
                {SCOPES.map((sc) => (
                  <div
                    key={sc.name}
                    className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6"
                  >
                    <code className="text-white font-mono text-sm">{sc.name}</code>
                    <p className="text-white/50">{sc.what}</p>
                  </div>
                ))}
              </div>

              <p className="text-white/40 text-sm mt-12 max-w-xl">
                The person approving your connection sees these same sentences
                before they authorise it, and can narrow or revoke the grant at
                any time.
              </p>
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
                over OAuth 2.1. It can read and write the workspace's files
                immediately, every change signed as that connection.
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
