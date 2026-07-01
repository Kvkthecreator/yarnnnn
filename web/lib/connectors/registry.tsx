/**
 * Connector registry — the FE-side presentation metadata for every platform
 * connector (ADR-392 FE Phase A).
 *
 * WHY a FE-side registry: connector presentation (brand colour, glyph, tagline,
 * auth kind, resource noun) is view-only chrome that can't be backend-served —
 * the exact same reason `WorkspaceMembersCard`'s ROLE_META const map lives
 * FE-side. The backend knows a connection's `provider` + `status`; the operator-
 * facing name, brand chip, and copy are the frontend's job. This registry is the
 * SINGLE source of that metadata — the Nth connector is one more entry here, not
 * one more hardcoded card block (Singular Implementation).
 *
 * This REPLACES the 5 hardcoded per-platform card IIFEs that previously lived in
 * `ConnectedIntegrationsSection.tsx`. The universal `ConnectorCard` renders one
 * entry; the section maps over `CONNECTOR_REGISTRY`.
 *
 * Precedent / pattern match: `web/components/workspace-concepts/WorkspaceMembersCard.tsx`
 * (its `ROLE_META` const map — role → { label, icon, tone }).
 *
 * Scoping doc: ADR-392 (Connector FE Universalization).
 */

import type { ReactNode } from "react";

export type ConnectorAuthKind = "oauth" | "apikey";

export interface ConnectorMeta {
  provider: string;
  displayName: string;
  tagline: string;
  authKind: ConnectorAuthKind;
  /** For OAuth connectors with a Phase-2 Select subsurface: the resource noun
   *  ("channels" / "pages" / "repos"). Undefined for api-key connectors. */
  resourceNoun?: string;
  /** True when the connector exposes the ConnectorSelectionPanel (OAuth only). */
  supportsSelection?: boolean;
  brand: {
    /** Tailwind class(es) for the brand chip background. */
    chipClass: string;
    icon: ReactNode;
  };
}

// ---------------------------------------------------------------------------
// Brand glyphs — lifted VERBATIM from the prior inline SVGs in
// ConnectedIntegrationsSection.tsx (pixel-identical, so icons don't shift).
// ---------------------------------------------------------------------------

const SlackIcon = (
  <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="currentColor">
    <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z" />
  </svg>
);

const NotionIcon = (
  <svg className="w-6 h-6 text-white dark:text-black" viewBox="0 0 24 24" fill="currentColor">
    <path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.98-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466l1.823 1.447zm.793 3.08v13.904c0 .747.373 1.027 1.213.98l14.523-.84c.84-.046.934-.56.934-1.166V6.354c0-.606-.234-.933-.746-.886l-15.177.887c-.56.046-.747.326-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952l1.448.327s0 .84-1.168.84l-3.222.186c-.093-.186 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.14c-.093-.513.28-.886.747-.933l3.222-.187zM2.87.119l13.449-.933c1.634-.14 2.055-.047 3.082.7l4.249 2.986c.7.513.934.653.934 1.213v16.378c0 1.026-.373 1.634-1.68 1.726l-15.458.934c-.98.046-1.448-.093-1.962-.747L1.945 18.79c-.56-.747-.793-1.306-.793-1.958V2.005C1.152.933 1.525.212 2.87.119z" />
  </svg>
);

const GithubIcon = (
  <svg className="w-6 h-6 text-white dark:text-black" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
  </svg>
);

const CommerceIcon = (
  <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="9" cy="21" r="1" /><circle cx="20" cy="21" r="1" />
    <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
  </svg>
);

const TradingIcon = (
  <svg className="w-6 h-6 text-black" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
    <polyline points="16 7 22 7 22 13" />
  </svg>
);

// ---------------------------------------------------------------------------
// The registry — order is the render order. Add the Nth connector here.
// ---------------------------------------------------------------------------

export const CONNECTOR_REGISTRY: ConnectorMeta[] = [
  {
    provider: "slack",
    displayName: "Slack",
    tagline: "Team collaboration and context",
    authKind: "oauth",
    resourceNoun: "channels",
    supportsSelection: true,
    brand: { chipClass: "bg-[#4A154B]", icon: SlackIcon },
  },
  {
    provider: "notion",
    displayName: "Notion",
    tagline: "Documentation and knowledge base",
    authKind: "oauth",
    resourceNoun: "pages",
    supportsSelection: true,
    brand: { chipClass: "bg-black dark:bg-white", icon: NotionIcon },
  },
  {
    provider: "github",
    displayName: "GitHub",
    tagline: "Repositories, issues, and pull requests",
    authKind: "oauth",
    resourceNoun: "repos",
    supportsSelection: true,
    brand: { chipClass: "bg-gray-900 dark:bg-white", icon: GithubIcon },
  },
  {
    provider: "commerce",
    displayName: "Lemon Squeezy",
    tagline: "Subscriptions, revenue, and customer data",
    authKind: "apikey",
    brand: { chipClass: "bg-[#7C3AED]", icon: CommerceIcon },
  },
  {
    provider: "trading",
    displayName: "Alpaca Trading",
    tagline: "Market data, portfolio tracking, and trade execution",
    authKind: "apikey",
    brand: { chipClass: "bg-[#FFDC00]", icon: TradingIcon },
  },
];

// ADR-377: which providers have a sync registry (OAuth platforms with
// synced_resources). Api-key connectors authenticate by key and have no
// per-resource sync freshness — they are skipped in the freshness fan-out.
// Derived from the registry so it can never drift from the auth kinds above.
export const FRESHNESS_PROVIDERS = CONNECTOR_REGISTRY.filter(
  (c) => c.authKind === "oauth",
).map((c) => c.provider);

/** Lookup a connector's presentation metadata by provider slug. */
export function connectorMeta(provider: string): ConnectorMeta | undefined {
  return CONNECTOR_REGISTRY.find((c) => c.provider === provider);
}
