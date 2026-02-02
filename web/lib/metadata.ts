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
  tagline: "Recurring work that gets better every time",
  description:
    "Set up your recurring deliverables once. yarnnn learns from every edit you make. Your 10th delivery is better than your 1st.",
  url: process.env.NEXT_PUBLIC_SITE_URL || "https://yarnnn.com",
  ogImage: "/assets/logos/yarn-logo-light.png",
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
 * Usage: export const metadata = getPageMetadata("Dashboard", "Your deliverables dashboard");
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
