import { MetadataRoute } from "next";
import { BRAND } from "@/lib/metadata";
import { getAllPosts } from "@/lib/blog";

// Google Search Console, 2026-09-17 — every static page carried
// `lastModified: new Date()`, i.e. BUILD time. The sitemap therefore told
// Google that all fifteen pages changed on every deploy, several times a day,
// while their content had not moved since July. A `lastmod` that is always
// "now" is not a freshness signal, it is noise: Google learns the field is
// uncorrelated with real change and discounts it, which costs crawl scheduling
// on the pages that DID change.
//
// The date is declared here rather than read from git: Vercel builds from a
// shallow clone, so `git log` at build time is not reliably available, and a
// silent fallback to `new Date()` would reintroduce the same defect invisibly.
// Declared means it is wrong only if someone edits a page and does not touch
// this line — the same discipline the blog's front-matter `lastModified`
// already carries. Blog posts keep deriving theirs from front-matter.
const STATIC_LAST_MODIFIED: Record<string, string> = {
  "": "2026-09-12",
  about: "2026-07-31",
  "how-it-works": "2026-09-16",
  pricing: "2026-08-19",
  engines: "2026-08-21",
  faq: "2026-09-12",
  support: "2026-09-17",
  download: "2026-09-23",
  developers: "2026-09-16",
  "openapi.json": "2026-09-16",
  ".well-known/mcp.json": "2026-09-16",
  "llms.txt": "2026-09-16",
  blog: "2026-09-16",
  invest: "2026-07-30",
  privacy: "2026-09-23",
  "privacy-architecture": "2026-09-16",
  terms: "2026-09-12",
};

function lastModifiedFor(path: string): Date {
  const declared = STATIC_LAST_MODIFIED[path];
  if (!declared) {
    throw new Error(
      `sitemap: no declared lastModified for static page "${path}" — ` +
        `add it to STATIC_LAST_MODIFIED rather than falling back to build time.`,
    );
  }
  return new Date(`${declared}T00:00:00.000Z`);
}

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = BRAND.url;

  // Static pages
  const staticPages = [
    {
      url: baseUrl,
      lastModified: lastModifiedFor(""),
      changeFrequency: "weekly" as const,
      priority: 1,
    },
    {
      url: `${baseUrl}/about`,
      lastModified: lastModifiedFor("about"),
      changeFrequency: "monthly" as const,
      priority: 0.8,
    },
    {
      url: `${baseUrl}/how-it-works`,
      lastModified: lastModifiedFor("how-it-works"),
      changeFrequency: "monthly" as const,
      priority: 0.8,
    },
    {
      url: `${baseUrl}/pricing`,
      lastModified: lastModifiedFor("pricing"),
      changeFrequency: "weekly" as const,
      priority: 0.85,
    },
    {
      url: `${baseUrl}/engines`,
      lastModified: lastModifiedFor("engines"),
      changeFrequency: "monthly" as const,
      priority: 0.75,
    },
    {
      url: `${baseUrl}/faq`,
      lastModified: lastModifiedFor("faq"),
      changeFrequency: "monthly" as const,
      priority: 0.75,
    },
    {
      url: `${baseUrl}/support`,
      lastModified: lastModifiedFor("support"),
      changeFrequency: "monthly" as const,
      priority: 0.6,
    },
    {
      url: `${baseUrl}/download`,
      lastModified: lastModifiedFor("download"),
      changeFrequency: "monthly" as const,
      priority: 0.7,
    },
    {
      url: `${baseUrl}/developers`,
      lastModified: lastModifiedFor("developers"),
      changeFrequency: "monthly" as const,
      priority: 0.8,
    },
    // Machine-readable developer resources — listed so crawlers and agents
    // surface them for name-based queries.
    {
      url: `${baseUrl}/openapi.json`,
      lastModified: lastModifiedFor("openapi.json"),
      changeFrequency: "monthly" as const,
      priority: 0.7,
    },
    {
      url: `${baseUrl}/.well-known/mcp.json`,
      lastModified: lastModifiedFor(".well-known/mcp.json"),
      changeFrequency: "monthly" as const,
      priority: 0.6,
    },
    {
      url: `${baseUrl}/llms.txt`,
      lastModified: lastModifiedFor("llms.txt"),
      changeFrequency: "weekly" as const,
      priority: 0.6,
    },
    {
      url: `${baseUrl}/blog`,
      lastModified: lastModifiedFor("blog"),
      changeFrequency: "weekly" as const,
      priority: 0.9,
    },
    {
      url: `${baseUrl}/invest`,
      lastModified: lastModifiedFor("invest"),
      changeFrequency: "monthly" as const,
      priority: 0.7,
    },
    {
      url: `${baseUrl}/privacy`,
      lastModified: lastModifiedFor("privacy"),
      changeFrequency: "yearly" as const,
      priority: 0.3,
    },
    {
      url: `${baseUrl}/privacy-architecture`,
      lastModified: lastModifiedFor("privacy-architecture"),
      changeFrequency: "monthly" as const,
      priority: 0.65,
    },
    {
      url: `${baseUrl}/terms`,
      lastModified: lastModifiedFor("terms"),
      changeFrequency: "yearly" as const,
      priority: 0.3,
    },
  ];

  // Blog posts
  const posts = getAllPosts();
  const blogPages = posts.map((post) => ({
    url: post.canonicalUrl,
    lastModified: new Date(post.lastModified || post.date),
    changeFrequency: "monthly" as const,
    priority: 0.7,
  }));

  return [...staticPages, ...blogPages];
}
