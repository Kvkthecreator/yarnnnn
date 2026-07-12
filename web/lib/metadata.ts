/**
 * YARNNN Metadata Configuration
 *
 * Centralized brand and metadata settings for SEO and social sharing.
 */

import type { Metadata } from "next";

// =============================================================================
// BRAND CONFIGURATION
// =============================================================================

export const BRAND = {
  name: "yarnnn",
  tagline: "Shared memory for AI + human work",
  description:
    "One shared workspace for your team's humans and AIs. Tell ChatGPT today, and Claude knows it tomorrow — everything lives in one place you own, every change carries its author's name, and the full history is yours to trace.",
  url: process.env.NEXT_PUBLIC_SITE_URL || "https://yarnnn.com",
  ogImage: "/assets/logos/og-card.png",
};

interface MarketingMetadataOptions {
  title: string;
  description: string;
  path: string;
  keywords?: string[];
  type?: "website" | "article";
}

function absoluteUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return new URL(normalized, BRAND.url).toString();
}

// =============================================================================
// METADATA HELPERS
// =============================================================================

export function getBaseMetadata(): Metadata {
  return {
    title: {
      default: `${BRAND.name} — ${BRAND.tagline}`,
      template: `%s | ${BRAND.name}`,
    },
    description: BRAND.description,
    metadataBase: new URL(BRAND.url),
    icons: {
      icon: [
        { url: "/favicon.ico", sizes: "any" },
        { url: "/favicon.svg", type: "image/svg+xml" },
      ],
      apple: "/assets/logos/circleonly_yarnnn.png",
    },
    openGraph: {
      title: `${BRAND.name} — ${BRAND.tagline}`,
      description: BRAND.description,
      url: BRAND.url,
      siteName: BRAND.name,
      locale: "en_US",
      type: "website",
      images: [
        {
          url: BRAND.ogImage,
          width: 1200,
          height: 630,
          alt: `${BRAND.name} - ${BRAND.tagline}`,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: `${BRAND.name} — ${BRAND.tagline}`,
      description: BRAND.description,
      images: [BRAND.ogImage],
    },
    manifest: "/manifest.json",
    robots: {
      index: true,
      follow: true,
    },
  };
}

/**
 * Helper to create page-specific metadata
 * Usage: export const metadata = getPageMetadata("Dashboard", "Your agents at a glance");
 */
export function getPageMetadata(title: string, description?: string): Metadata {
  return {
    title,
    description: description || BRAND.description,
    openGraph: {
      title: `${title} | ${BRAND.name}`,
      description: description || BRAND.description,
    },
  };
}

export function getMarketingMetadata({
  title,
  description,
  path,
  keywords,
  type = "website",
}: MarketingMetadataOptions): Metadata {
  const canonical = absoluteUrl(path);
  const image = absoluteUrl(BRAND.ogImage);

  return {
    title,
    description,
    ...(keywords && keywords.length > 0 ? { keywords } : {}),
    alternates: {
      canonical,
    },
    openGraph: {
      title: `${title} | ${BRAND.name}`,
      description,
      url: canonical,
      type,
      images: [
        {
          url: image,
          width: 1200,
          height: 630,
          alt: `${BRAND.name} - ${title}`,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: `${title} | ${BRAND.name}`,
      description,
      images: [image],
    },
  };
}

// =============================================================================
// STRUCTURED DATA (JSON-LD)
//
// These schemas let AI agents and search engines identify yarnnn's product and
// organization programmatically. The homepage emits Organization +
// SoftwareApplication (so agents can parse "what is this product") alongside
// the WebSite schema. Centralized here so any page can reuse the same canonical
// identity.
// =============================================================================

const LOGO_URL = "/assets/logos/circleonly_yarnnn.png";

function absoluteLogoUrl(): string {
  return new URL(LOGO_URL, BRAND.url).toString();
}

/** schema.org Organization — who publishes yarnnn. */
export function getOrganizationSchema() {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    "@id": `${BRAND.url}/#organization`,
    name: BRAND.name,
    url: BRAND.url,
    logo: absoluteLogoUrl(),
    description: BRAND.description,
    email: "admin@yarnnn.com",
    sameAs: [] as string[],
  };
}

/**
 * schema.org SoftwareApplication — what yarnnn is, so agents can identify the
 * product itself (not just the website). Includes the MCP interop surface and
 * the freemium offer.
 */
export function getSoftwareApplicationSchema() {
  return {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "@id": `${BRAND.url}/#software`,
    name: BRAND.name,
    url: BRAND.url,
    applicationCategory: "BusinessApplication",
    applicationSubCategory: "AI memory layer",
    operatingSystem: "Web, MCP (Model Context Protocol)",
    description: BRAND.description,
    featureList: [
      "Durable, attributed memory shared across every AI tool",
      "Model Context Protocol (MCP) connector for ChatGPT, Claude, and others",
      "Full provenance — trace who changed any fact, when, and what changed",
      "One shared workspace for a team's humans and AIs",
    ],
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "USD",
      description:
        "Free for one person; a paid seat ($20/mo) per teammate plus a shared monthly usage pool. AI connections are always free.",
    },
    publisher: {
      "@id": `${BRAND.url}/#organization`,
    },
  };
}

/** schema.org WebSite — the marketing site itself. */
export function getWebSiteSchema() {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "@id": `${BRAND.url}/#website`,
    name: BRAND.name,
    url: BRAND.url,
    description: BRAND.description,
    publisher: {
      "@id": `${BRAND.url}/#organization`,
    },
  };
}
