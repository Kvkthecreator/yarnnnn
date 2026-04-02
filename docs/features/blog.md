# Blog

> **Updated**: 2026-03-11 — collective SEO/GEO optimization applied at template level

---

## What it is

The blog is YARNNN's canonical long-form GEO surface at `/blog`. Posts are repo-authored markdown files rendered statically by Next.js.

The system is designed so discoverability packaging is mostly automatic:
- metadata
- structured data
- summary block
- series navigation
- related internal links

---

## Source of truth

- Content files: `content/posts/*.md`
- Loader and scoring: `web/lib/blog.ts`
- Blog index route: `web/app/blog/page.tsx`
- Blog post route: `web/app/blog/[slug]/page.tsx`
- RSS feed: `web/app/blog/rss.xml/route.ts`
- Sitemap inclusion: `web/app/sitemap.ts`

---

## Frontmatter schema

### Required for published posts

| Field | Purpose |
|---|---|
| `title` | H1 + default metadata title |
| `slug` | Route path (`/blog/[slug]`) |
| `description` | Post summary fallback |
| `date` | Publish date |
| `canonicalUrl` | Canonical URL tag and feed URL |
| `status` | Must be `published` to render |

### Optional SEO/editorial fields

| Field | Purpose |
|---|---|
| `metaTitle` | SEO title override without changing on-page title |
| `metaDescription` | SEO description override |
| `tags` | Keywords + related-post scoring |
| `category` | Reader-facing taxonomy: `how-it-works`, `where-its-going`, or `what-were-seeing` |
| `author` | Byline + schema author |
| `concept` | Related-post scoring signal |
| `series` | Enables series navigation |
| `seriesPart` | Ordered series rendering |
| `image` | OG image override |
| `lastModified` / `updatedAt` | Modified time for metadata/sitemap |

---

## Collective SEO/GEO behavior (all posts)

### Metadata + canonical

- `generateMetadata()` uses `metaTitle || title` and `metaDescription || description`.
- Canonical link is always set from `canonicalUrl`.
- Open Graph and Twitter tags are generated per post.

### Structured data

- `BlogPosting` JSON-LD on every post page.
- `BreadcrumbList` JSON-LD on every post page.

### On-page extraction helpers

- `At a Glance` block is auto-rendered at top of each post body.
- Up to 5 `##` headings are extracted and listed as quick coverage bullets.

### Internal-link scaffolding

- `Series Navigation` appears automatically for posts sharing the same `series`.
- `Related Reading` appears automatically on all posts using weighted similarity scoring:
  - same series: +6
  - same concept: +4
  - same category: +2

### Category guidance

- `how-it-works`: explanatory posts about how the product, architecture, or AI-work mechanics function
- `where-its-going`: forward-looking essays about the future of work, organizations, and economic change
- `what-were-seeing`: timely commentary on current events, product launches, company moves, or market signals
  - shared tags: +2 each (capped)

---

## Constraints

1. Only top-level `content/posts/*.md` files are indexed. Nested markdown files are ignored by the current loader.
2. Content is rendered via `react-markdown` (markdown, not MDX). Inline JSX in posts is not supported.
3. `status: draft` posts are excluded from blog index, sitemap, RSS, and route generation.

---

## Authoring checklist

1. Add or update frontmatter (`slug`, `canonicalUrl`, `status`).
2. Write clear `description`; add `metaTitle`/`metaDescription` when snippet control matters.
3. Use descriptive `##` section headings so quick coverage extraction remains useful.
4. Add meaningful `tags` and `series` fields to improve automatic related-link quality.
5. Keep at least one explicit internal link in body copy for key related concepts.

---

## Related

- [ADR-078](../adr/ADR-078-blog-route-architecture.md)
- [Content Strategy v1](../working_docs/strategy/CONTENT_STRATEGY_v1.md)
