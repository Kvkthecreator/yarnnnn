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
  name: "YARNNN",
  tagline: "Context-aware AI work platform",
  description:
    "Your AI agents understand your world because they read from your accumulated context.",
  url: process.env.NEXT_PUBLIC_SITE_URL || "https://yarnnn.com",
};

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
      icon: "/favicon.svg",
      shortcut: "/favicon.ico",
      apple: "/assets/logos/circleonly_yarnnn.png",
    },
    openGraph: {
      title: BRAND.name,
      description: BRAND.tagline,
      url: BRAND.url,
      siteName: BRAND.name,
      locale: "en_US",
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title: BRAND.name,
      description: BRAND.tagline,
    },
    robots: {
      index: true,
      follow: true,
    },
  };
}

/**
 * Helper to create page-specific metadata
 * Usage: export const metadata = getPageMetadata("Dashboard");
 */
export function getPageMetadata(title: string, description?: string): Metadata {
  return {
    title,
    description: description || BRAND.description,
  };
}
