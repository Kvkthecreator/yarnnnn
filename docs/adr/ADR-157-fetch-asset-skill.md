# ADR-157: Fetch-Asset Skill — External Asset Acquisition for Context Substrate

**Status:** Proposed
**Date:** 2026-04-03
**Supersedes:** None
**Extends:** ADR-118 (Skills as Capability Layer), ADR-151 (Shared Context Domains), ADR-152 (Unified Directory Registry), ADR-155 (Workspace Inference & Onboarding)

## Context

The workspace context substrate (ADR-151/152) accumulates entity intelligence as markdown files: competitor profiles, market analyses, contact records. But the substrate is **text-only** — no visual assets.

When synthesis tasks produce deliverables (competitive briefs, stakeholder updates), they lack visual identity: no competitor logos, no brand marks, no entity icons. The outputs feel hollow.

Meanwhile, external visual assets for most entities are trivially available — company favicons are deterministic URLs, logos available via free APIs. The cost to acquire them is near-zero compared to the text research agents already perform.

## Decision

### Single capability, all lifecycle moments

A new `fetch-asset` render skill acquires external images (favicons, logos) and stores them in Supabase Storage. The same skill serves three callers:

1. **ScaffoldDomains** (initialization) — when entities are first created, fetch their favicon alongside the text stubs. Same skill, same interface.
2. **Agents during update-context** (bootstrap/steady-state) — when agents discover new entities or detect stale assets, they call `fetch-asset` via RuntimeDispatch.
3. **Agents during derive-output** (synthesis) — agents reference stored asset URLs from context when composing HTML deliverables.

**No separate initialization path.** ScaffoldDomains calls the same render service skill that agents call. One capability, one interface.

### Favicon-first

The initial implementation supports `type: "favicon"` only — deterministic, free, consistent:
- Google Favicon API: `https://www.google.com/s2/favicons?domain={domain}&sz={size}`
- Always available for any domain with a website
- Consistent format/quality across all entities
- Zero search cost, zero LLM overhead

Future types (`logo`, `screenshot`) use the same interface but different acquisition strategies.

### Storage in context substrate

Fetched assets are stored as workspace files with `content_url` pointing to Supabase Storage. They live alongside entity text files:

```
/workspace/context/competitors/cursor/
  profile.md          ← text intelligence
  signals.md          ← dated findings
  favicon.png         ← visual asset (content_url → storage)
```

The `favicon.png` workspace file has:
- `content`: Brief description ("Favicon for cursor.com")
- `content_url`: Supabase Storage URL
- `content_type`: "image/png"

This makes favicons **part of the context substrate** — they're read by synthesis agents alongside text files, referenced in HTML output, and versioned with the entity.

### Deduplication

Content-hash dedup prevents re-fetching. If `cursor.com` favicon was fetched during scaffolding, a subsequent agent call returns the existing URL without re-fetching.

## Architecture

### Render skill interface

```
POST /render
{
  "type": "fetch-asset",
  "input": {
    "url": "cursor.com",           // domain or full URL
    "asset_type": "favicon",       // favicon | logo (future)
    "size": 64                     // pixel size (favicon only)
  },
  "output_format": "png",
  "user_id": "..."
}

Response:
{
  "success": true,
  "output_url": "https://storage.../user/2026/04/03/favicon-cursor.png",
  "content_type": "image/png",
  "size_bytes": 1234
}
```

### Callers

**ScaffoldDomains** (initialization):
- Entity input gains optional `domain` field: `{"domain": "competitors", "slug": "cursor", "name": "Cursor", "url": "cursor.com"}`
- When `url` is provided, ScaffoldDomains calls the render service to fetch the favicon
- Writes workspace file at `{domain_path}/{slug}/favicon.png` with `content_url`
- Non-blocking: favicon fetch failure doesn't fail entity scaffolding

**Agents via RuntimeDispatch** (bootstrap/steady-state):
- `RuntimeDispatch(type="fetch-asset", input={url: "anthropic.com", asset_type: "favicon"}, output_format="png")`
- Works exactly like existing chart/mermaid dispatch
- Agent decides when to call based on domain intelligence

### Entity metadata convention

Entity `profile.md` files gain an optional `url` field in the source comment:

```markdown
<!-- source: researched | date: 2026-04-02 | url: cursor.com -->
# Cursor
```

This url is:
- Written by agents during research (part of normal profile creation)
- Read by ScaffoldDomains for favicon fetching at initialization
- Available to synthesis agents for inline favicon references

## Phases

### Phase 1: Skill + ScaffoldDomains integration
1. Create `render/skills/fetch-asset/` (SKILL.md + scripts/render.py)
2. Add `fetch-asset` to RuntimeDispatch allowed types
3. Add `url` field to ScaffoldDomains entity input
4. ScaffoldDomains calls render service for entities with `url`
5. Writes workspace file with `content_url` for favicon

### Phase 2: Agent prompt integration
1. Update `update-context` step instructions: "capture entity domain URLs"
2. Update `derive-output` step instructions: "reference entity favicons in HTML output"
3. SKILL.md injection for `fetch-asset` into agent context

### Phase 3: Future asset types (deferred)
- `logo`: Clearbit Logo API or web search
- `screenshot`: Headless browser capture
- `hero-image`: Stock/generated images for content topics

## Cost analysis

| Activity | LLM tokens | External cost | Notes |
|----------|-----------|---------------|-------|
| Favicon fetch | 0 | $0 | Deterministic URL, no LLM |
| Storage upload | 0 | ~$0 | Supabase free tier |
| Agent calling fetch-asset | ~500 | $0 | 1 tool round |
| Text research (for comparison) | ~10,000-15,000 | $0 | 5-10x more expensive |

Favicon fetching during ScaffoldDomains is **zero LLM cost** — it's mechanical code, not agent-directed. During agent runs, it adds one tool round (~500 tokens) to an already 10,000+ token cycle.

## Constraints

- Favicon-only in Phase 1 (no logo search, no screenshots)
- Max asset size: 1MB per fetch
- Fetch timeout: 10s (favicons are tiny and fast)
- Non-blocking: asset fetch failure never fails the parent operation
- Dedup by domain+type+size hash — no redundant storage
