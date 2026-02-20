# ADR-062: Platform Context Architecture — Live Reads, Internal Mirror, and the Role of filesystem_items

**Status**: ⚠️ SUPERSEDED by ADR-072
**Superseded by**: [ADR-072: Unified Content Layer and TP Execution Pipeline](ADR-072-unified-content-layer-tp-execution-pipeline.md)
**Date**: 2026-02-18
**Relates to**: ADR-038 (Filesystem-as-Context), ADR-049 (Context Freshness), ADR-059 (Simplified Context Model)

---

## Supersession Note (2026-02-20)

**This ADR is superseded by ADR-072.** The decisions made here created architectural tensions:

1. `filesystem_items` as "cache only" created a provenance gap — deliverables couldn't link back to source content
2. "Do not expand the mirror's role" prevented accumulation of significant content
3. Separate "live reads for execution, cache for search" created two parallel pipelines with a quality gap

**What changed (ADR-072):**
- `filesystem_items` is replaced by `platform_content` — a unified content layer with retention semantics
- Content that proves significant is retained indefinitely (accumulation moat)
- Deliverable execution uses TP in headless mode (same primitives as live sessions)
- `source_snapshots` now includes `platform_content_ids` for provenance

**The three-layer model defined here (Memory / Context / Work) evolves into the four-layer model (Memory / Activity / Context / Work) documented in ADR-063 and updated in ADR-072.**

---

## Original ADR (Historical Context)

---

## Context

This ADR was prompted by a first-principles re-examination of whether Yarnnn needs an internal mirror of platform content (`filesystem_items`) at all, and if so, what its precise role is. The question arose from the same intuition that drove ADR-038 and ADR-059: if platforms are the source of truth, and TP has live API access to them, why maintain a parallel internal representation?

The investigation also surfaced a terminology problem that was causing architectural confusion: the words "context" and "memory" were being used interchangeably across the codebase, documentation, and ADRs. This ADR resolves that.

---

## Finding: Scheduled Deliverables Already Do Live Reads

The most important finding from this review: **`filesystem_items` is not used by the deliverable execution pipeline at all.**

When a scheduled deliverable runs (via `unified_scheduler.py` → `execute_deliverable_generation()` → `fetch_integration_source_data()`), it:

1. Decrypts OAuth credentials from `platform_connections` at execution time
2. Makes live API calls to Slack, Gmail, Notion, Calendar
3. Passes that live data directly to the LLM for generation
4. Never reads from `filesystem_items`

This means the concern that motivated the question — "do we need the mirror to run background work?" — is already answered: **no, we do not. Background work already runs on live data.**

`filesystem_items` and the deliverable execution pipeline are two independent systems that happen to target the same upstream platforms.

---

## What filesystem_items Actually Does

`filesystem_items` is a **conversational search cache**. Its single load-bearing purpose is to serve `Search(scope="platform_content")` calls that TP makes during a conversation when the user asks about platform content ("what was discussed in #general this week?").

Without the mirror, TP would need to fan out to platform APIs live during a streaming response — slower, and not composable across platforms in a single search query.

| | With filesystem_items | Without (live only) |
|---|---|---|
| `Search(scope="platform_content")` | Fast local text query | Requires live calls to each platform |
| Scheduled deliverable execution | Not used | Already live |
| Conversational TP platform tools | Not used (separate tool path) | Already live |
| Notion sync reliability | Currently broken (known bug) | N/A |

The mirror is only meaningful if it's reliably populated. The known Notion sync bug (`_sync_notion()` using MCPClientManager with internal tokens rather than OAuth) means the mirror is currently unreliable for Notion.

---

## Decision

### Keep filesystem_items, but with a clarified mandate

`filesystem_items` is retained as the **conversational search index** — the cache that makes `Search(scope="platform_content")` possible within a conversation turn. It is not a source-of-truth mirror. It is not used for deliverable execution. Its purpose is narrow and specific.

The fix for Notion sync (switching to direct `NotionAPIClient.get_page_content()` calls, the same approach used for landscape discovery) should be applied to `platform_worker.py`. This is the correct fix; it does not change the architecture.

### Do not expand the mirror's role

The mirror should not be the primary data source for any critical path. Deliverable execution remains on live reads. This is correct and should be documented explicitly to prevent future drift.

### Future option: replace conversational search with live fan-out

If platform API latency is acceptable (or improves), conversational search could be replaced with direct platform tool calls, eliminating the need for the mirror entirely. This is deferred — the mirror is working for Gmail/Calendar/Slack; the cost of fixing Notion is lower than re-architecting conversational search.

---

## Terminology Decision

The prior architecture used "context" and "memory" interchangeably. From this ADR forward, Yarnnn uses the following definitions:

### Memory
Things that are *about the user* — stable, explicit, user-owned. Name, role, how they prefer to work, facts and instructions TP has noted during conversation. Analogous to CLAUDE.md.

- **Table**: `user_context` (ADR-059)
- **Written by**: User directly (Context page), TP during conversation (via `create_memory` tool)
- **Read by**: Working memory builder — injected into every TP session as the system prompt context block
- **Size**: Small. Tens to low hundreds of entries.

### Context
The current working material for a task — what's in their platforms right now. Platform-synced. Ephemeral. The "filesystem" in the Claude Code analogy.

- **Table**: `filesystem_items` (search cache), live API calls for execution
- **Written by**: Background sync worker (`platform_worker.py`) for the cache; live at execution time for deliverables
- **Read by**: TP `Search(scope="platform_content")` calls during conversation; `fetch_integration_source_data()` during deliverable execution
- **Size**: Large and TTL-bounded.

### Work
What TP produces. Structured, versioned, deliverable to a platform destination.

- **Table**: `deliverables` + `deliverable_versions`
- **Written by**: Execution pipeline, always from live reads
- **Read by**: User review, platform export

---

## The Three-Layer Model

```
┌─────────────────────────────────────────────────────────────┐
│  MEMORY (user_context)                                       │
│  What TP knows about you — stable, explicit, small          │
│  Injected into every session (working memory)               │
└─────────────────────────────────────────────────────────────┘
                           ↑ user states / TP notes

┌─────────────────────────────────────────────────────────────┐
│  CONTEXT (filesystem_items + live platform APIs)            │
│  What's in your platforms right now — ephemeral, large      │
│  Accessed on demand: Search (cache) or live fetch           │
└─────────────────────────────────────────────────────────────┘
                           ↑ synced by platform_worker

┌─────────────────────────────────────────────────────────────┐
│  WORK (deliverables + deliverable_versions)                  │
│  What TP produces — structured, versioned, exported         │
│  Always generated from live Context reads                   │
└─────────────────────────────────────────────────────────────┘
```

This maps cleanly to both reference models:

| Concept | Claude Code | Clawdbot | Yarnnn |
|---|---|---|---|
| **Memory** | CLAUDE.md | SOUL.md / USER.md | `user_context` |
| **Context** | Source files (read on demand) | Local filesystem | `filesystem_items` + live API |
| **Work** | Build output | Script output | `deliverable_versions` |
| **Execution** | Shell commands | Skills | Deliverable pipeline (live reads) |

---

## On Document-Sourced Memory

An intentional oversight: uploaded documents currently populate `filesystem_chunks` (searchable via the document search scope) but do **not** extract into `user_context` (Memory). This is correct under the clean separation defined above — documents are Context, not Memory.

There is a legitimate future use case: a user uploads a style guide, a company brief, or a set of standing instructions and explicitly wants TP to treat them as permanent Memory (always present, not just searchable). This is a distinct feature — "promote document to memory" — and should be implemented as an explicit user action rather than automatic extraction, which was the prior approach and was too implicit to be reliable.

This is deferred pending the above architectural hardening.

---

## What This ADR Does Not Change

- `filesystem_items` schema — unchanged
- Platform sync pipeline — unchanged (except the Notion bug fix is now clearly prioritised)
- Deliverable execution pipeline — unchanged (already on live reads; this ADR documents it)
- `user_context` table (ADR-059) — unchanged
- Working memory builder — unchanged

---

## Related

- [ADR-038](ADR-038-filesystem-as-context.md) — original filesystem-as-context decision
- [ADR-059](ADR-059-simplified-context-model.md) — Memory table consolidation
- [context-pipeline.md](../architecture/context-pipeline.md) — updated to reflect three-layer model
- [ADR-049](ADR-049-context-freshness-model.md) — TTL and freshness policy for filesystem_items
