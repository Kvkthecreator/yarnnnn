# ADR-078: Blog Route Architecture

**Status**: Implemented  
**Date**: 2026-02-25  
**Updated**: 2026-03-11  
**Depends on**: Content Strategy v1 (`docs/working_docs/strategy/CONTENT_STRATEGY_v1.md`)

## Context

YARNNN uses `yarnnn.com/blog` as the canonical GEO surface for long-form thesis content. Medium, LinkedIn, and other channels amplify distribution, but canonical authority must live on the first-party domain.

Initial route implementation shipped in February. On 2026-03-11, the blog was upgraded with collective GEO/SEO packaging so all posts benefit from the same extraction and discoverability scaffolding without per-post manual work.

## Decision

Use static markdown (`.md`) in-repo authoring with Next.js App Router pages, gray-matter frontmatter parsing, and shared rendering logic for metadata, schema, series navigation, and related reading.

### Implemented architecture

```text
web/
  app/
    blog/
      page.tsx                 # blog index
      [slug]/page.tsx          # post page + metadata + JSON-LD
      rss.xml/route.ts         # RSS feed
    sitemap.ts                 # includes blog URLs
  lib/
    blog.ts                    # frontmatter parse + sorting + related scoring
content/
  posts/
    *.md                       # canonical blog sources
```

### Authoring model (frontmatter)

**Required**
- `title`
- `slug`
- `description`
- `date`
- `canonicalUrl`
- `status` (`published` to render)

**Supported optional**
- `metaTitle` (SEO title override)
- `metaDescription` (SEO description override)
- `tags`
- `author`
- `category` (`core` or `opinion`)
- `concept`
- `series`
- `seriesPart`
- `image`
- `lastModified` / `updatedAt`

### Collective GEO/SEO behavior (all posts)

1. Metadata and social cards generated from frontmatter with canonical URL, OG/Twitter fields, and author normalization.
2. Structured data includes `BlogPosting` + `BreadcrumbList`.
3. Post page injects an `At a Glance` summary block using `metaDescription || description`.
4. Post page auto-extracts up to 5 `##` headings into a quick coverage list.
5. Series posts get automatic `Series Navigation`.
6. All posts get automatic `Related Reading` via shared scoring logic:
   - same series (highest weight)
   - same concept
   - same category
   - shared tags
7. Blog URLs are included in `sitemap.xml` and `rss.xml`.

## Consequences

### Positive
- Canonical GEO authority remains on `yarnnn.com` while cross-post channels point back to source.
- SEO/GEO packaging quality is consistent across all posts by default.
- Editorial load is lower: post-level metadata can be tuned with optional frontmatter instead of template rewrites.
- Internal-link graph is generated systematically (series + related), improving crawlability and LLM retrieval surface.

### Negative
- Top-level-only post loading (`content/posts/*.md`) means nested markdown files are excluded from the canonical index until loader logic is expanded.
- `At a Glance` and heading extraction are generic and may occasionally duplicate author-written intros.

### Neutral
- Still no CMS, comments, tag pages, or in-site blog search by design.

## Alternatives Considered

| Option | Pros | Cons | Why Not |
|--------|------|------|---------|
| MDX-first authoring | Rich embed capability | Higher complexity and dependency footprint | Not required for current content format |
| CMS-managed blog | Non-technical editing | Operational overhead + vendor coupling | Repo-authored markdown is sufficient |
| Per-post manual GEO sections only | Full copy control | Inconsistent quality across posts | Collective template behavior is higher leverage |

## References

- `web/lib/blog.ts`
- `web/app/blog/[slug]/page.tsx`
- `web/app/blog/page.tsx`
- `web/app/blog/rss.xml/route.ts`
- `web/app/sitemap.ts`
- `docs/features/blog.md`
