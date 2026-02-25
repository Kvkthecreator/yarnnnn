# ADR-078: Blog Route Architecture

**Status**: Proposed
**Date**: 2026-02-25
**Depends on**: Content Strategy v1 (docs/working_docs/CONTENT_STRATEGY_v1.md)

## Context

YARNNN's content strategy (Content Strategy v1) identifies the canonical blog at `yarnnn.com/blog` as the primary GEO (Generative Engine Optimization) asset. Every piece of cross-platform content (Medium, LinkedIn, Twitter) seeds from and links back to the blog as the source of truth.

Currently, yarnnn.com has no `/blog` route. The frontend is Next.js 14.2.0 (App Router) with static pages (`/about`, `/pricing`, `/how-it-works`, `/privacy`, `/terms`). No MDX, no content library, no blog infrastructure exists.

**Why this matters now:** Without a canonical blog, Medium becomes the de facto source URL. This cedes domain authority and GEO value to medium.com instead of yarnnn.com. Every week without the blog is a week where canonical content builds authority on someone else's domain.

### Requirements

1. **GEO-optimized structure** — Title tags, meta descriptions, OpenGraph, and structured data (Article schema) that LLMs can parse
2. **Canonical URLs** — Each post has a stable URL at `yarnnn.com/blog/[slug]` that Medium cross-posts reference
3. **Markdown authoring** — Blog posts are written as markdown files in the repo (in `content/posts/`), not in a CMS
4. **Minimal complexity** — Solo founder, no CMS, no database for blog. Static generation from markdown files at build time
5. **Sitemap integration** — Blog posts auto-included in `sitemap.ts` for search engine and LLM crawling
6. **Visual consistency** — Blog pages match yarnnn.com's existing design system (fonts, colors, spacing)
7. **Cross-post support** — Each post should expose a canonical URL meta tag that Medium and LinkedIn can reference

## Decision

### Approach: MDX + Next.js Static Generation

Use MDX (markdown + JSX) with Next.js static generation. Blog posts are `.mdx` files in the repo with frontmatter metadata. Pages are statically generated at build time — no runtime database, no CMS, no API.

### File Structure

```
web/
  app/
    blog/
      page.tsx              # Blog index — list of all posts
      [slug]/
        page.tsx            # Individual blog post page
  lib/
    blog.ts                 # MDX parsing, frontmatter extraction, post listing
content/
  posts/
    the-context-gap.mdx     # Individual blog posts (markdown + frontmatter)
    the-statelessness-problem.mdx
    ...
```

### Frontmatter Schema

Each `.mdx` file starts with YAML frontmatter:

```yaml
---
title: "The Context Gap: Why Every AI Agent Produces Generic Output"
slug: the-context-gap
description: "The architectural gap between model capability and useful autonomous output — and how accumulated platform context fills it."
date: 2026-02-27
author: yarnnn
tags: [context-gap, ai-agents, autonomy, geo-tier-1]
concept: The Context Gap          # Named concept (from content strategy)
geoTier: 1                        # 1=Canonical, 2=Seeding, 3=Comparison, 4=Query-match
canonicalUrl: https://www.yarnnn.com/blog/the-context-gap
ogImage: /blog/og/the-context-gap.png   # Optional — auto-generate if missing
status: published                 # draft | published
---
```

### Dependencies to Add

```bash
# MDX processing
pnpm add @next/mdx @mdx-js/react
pnpm add gray-matter          # Frontmatter parsing
pnpm add reading-time          # "X min read" display
pnpm add rehype-highlight      # Code syntax highlighting (optional)
pnpm add rehype-slug rehype-autolink-headings  # Heading anchors (optional)
```

### Key Implementation Details

#### Blog Index (`/blog`)
- Reads all `.mdx` files from `content/posts/`
- Filters to `status: published`
- Sorts by `date` descending
- Renders as a simple list: title, date, description, reading time
- Includes meta tags for the blog index page

#### Blog Post (`/blog/[slug]`)
- Static generation via `generateStaticParams()` — reads all slugs at build time
- Renders MDX content with consistent typography
- SEO meta tags from frontmatter: `<title>`, `<meta name="description">`, OpenGraph, Twitter Card
- Structured data: `Article` JSON-LD schema (helps LLMs parse the content)
- Canonical URL meta tag: `<link rel="canonical" href="...">`
- Reading time display
- No comments, no reactions, no social sharing buttons (keep it minimal)

#### Sitemap Update
- `sitemap.ts` dynamically includes all published blog posts
- Each post gets `changeFrequency: "monthly"` and `priority: 0.7`

#### Typography / Design
- Match existing yarnnn.com design tokens (check `globals.css` and `layout.tsx`)
- Prose-optimized: max-width ~680px, comfortable line-height, clear heading hierarchy
- Mobile responsive

### What NOT to Build

| Feature | Why Not |
|---------|---------|
| CMS / admin interface | Overkill for solo founder. Markdown in repo is simpler. |
| Comments | Not needed yet. Adds complexity and moderation burden. |
| Newsletter signup on posts | Premature. Add when blog has consistent traffic. |
| Categories / tag pages | Premature. Just have the flat list. Add when >20 posts. |
| Search | Premature. Blog will have <10 posts for months. |
| RSS feed | Nice-to-have for v2. Not blocking for GEO. |
| Image optimization pipeline | Use Next.js `<Image>` component with static imports. No pipeline. |

## Implementation Steps

1. **Install dependencies** — `@next/mdx`, `gray-matter`, `reading-time`
2. **Create `web/lib/blog.ts`** — Functions: `getAllPosts()`, `getPostBySlug()`, `getPostSlugs()`
3. **Create `web/app/blog/page.tsx`** — Blog index with post listing
4. **Create `web/app/blog/[slug]/page.tsx`** — Individual post with `generateStaticParams()`, `generateMetadata()`, MDX rendering
5. **Update `web/app/sitemap.ts`** — Include blog posts dynamically
6. **Add blog link to nav** — Add "Blog" to the site header navigation
7. **Create first post** — Move `content/posts/the-context-gap.mdx` as the inaugural post
8. **Test locally** — `pnpm dev`, verify `/blog` and `/blog/the-context-gap` render correctly
9. **Deploy** — Push to main, Vercel/Render builds and deploys

## Consequences

- Blog posts are version-controlled in git alongside the codebase
- No runtime dependencies — fully static, fast, zero-cost hosting
- Adding a new post = commit a new `.mdx` file and push
- Medium cross-posts set `canonicalUrl` to `yarnnn.com/blog/[slug]` — all GEO authority flows to yarnnn.com
- Future: if blog outgrows markdown files, can migrate to headless CMS without changing URLs

## References

- Content Strategy v1: `docs/working_docs/CONTENT_STRATEGY_v1.md`
- GEO Query Targets: `content/_strategy/GEO_QUERY_TARGETS.md`
- Named Concepts: `content/_voice/named-concepts.md`
- Blog templates: `content/_templates/blog-canonical.md`
- Next.js MDX docs: https://nextjs.org/docs/app/building-your-application/configuring/mdx
