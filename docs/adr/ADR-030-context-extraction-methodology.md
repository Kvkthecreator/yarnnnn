# ADR-030: Context Extraction Methodology

> **Status**: Draft
> **Created**: 2026-02-06
> **Related**: ADR-027 (Integration Read Architecture), ADR-029 (Email Integration)

---

## Context

ADR-027 established that integration reads are agent-mediated. However, it didn't address:

1. **Scope Definition**: What exactly do we extract? Full history is infinite.
2. **Platform Semantics**: Each platform has different data shapes and access patterns.
3. **Time/Cost Characteristics**: How long does extraction take? What are realistic bounds?
4. **Async Considerations**: When does extraction run? How do we handle long-running jobs?
5. **Visibility**: What does the user know that YARNNN knows? What's covered vs. not?

Context extraction is fundamentally a **scoped data crawling problem** - analogous to:
- Search engine web crawling (depth limits, recency, domain scoping)
- Deep research agents (Claude Code's multi-step investigation)
- Data pipeline ETL jobs (batch processing, incremental sync)

We cannot do "full sweeps" - that's infinite scope. We need principled constraints.

### The User's Mental Model

Even users don't look at everything on their platforms:
- **Gmail**: Only certain folders matter, most promotional/social is noise
- **Slack**: Only team channels, maybe 3-5 active ones at any time
- **Notion**: Only their team's workspace section, specific project pages

Users already have a mental map of "my relevant slice." YARNNN needs to:
1. Help users define that slice explicitly
2. Show clearly what's covered vs. not covered
3. Make it easy to expand coverage when needed

---

## Decision

**Context extraction is bounded by explicit scope parameters per platform, with sensible defaults that balance coverage vs. cost.**

### Core Principle: Recency-First, Relevance-Filtered

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     EXTRACTION SCOPE HIERARCHY                               │
└─────────────────────────────────────────────────────────────────────────────┘

1. TEMPORAL BOUND (Primary)
   - How far back? (7 days, 30 days, 90 days)
   - Most recent first (reverse chronological)

2. VOLUME BOUND (Safety)
   - Max items to fetch per resource (100, 500, 1000)
   - Prevents runaway jobs on large channels/inboxes

3. RESOURCE BOUND (Focus)
   - Which channels/folders/pages to include
   - User-selected or smart defaults

4. SEMANTIC BOUND (Agent-Applied)
   - Agent filters noise during extraction
   - Decisions > logistics > small talk
```

---

## Platform-Specific Extraction Models

### Gmail

**Data Shape**: Messages organized in threads, labels (folders), search queryable

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GMAIL EXTRACTION MODEL                             │
└─────────────────────────────────────────────────────────────────────────────┘

RESOURCE TYPES:
├── inbox         → Primary inbox (excludes promotions/social/updates)
├── label:{id}    → Specific label/folder
├── sent          → User's sent messages
├── starred       → Starred messages
└── query:{q}     → Gmail search query (e.g., "from:boss@company.com")

SCOPE PARAMETERS:
┌──────────────────┬──────────────────┬──────────────────┬──────────────────┐
│ Parameter        │ Min              │ Default          │ Max              │
├──────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ recency          │ 1 day            │ 7 days           │ 90 days          │
│ max_messages     │ 10               │ 100              │ 500              │
│ max_threads      │ 5                │ 50               │ 200              │
│ include_sent     │ false            │ true             │ true             │
└──────────────────┴──────────────────┴──────────────────┴──────────────────┘

EXTRACTION MODES:
1. "summary" (default)
   - Fetch message list → get full content for top N by recency
   - Threads collapsed (get thread, extract key messages)
   - ~30 sec for 50 messages

2. "thorough"
   - Fetch all messages in range
   - Full thread expansion
   - ~2-5 min for 200+ messages

3. "targeted"
   - Search query first, then extract matches
   - Best for specific topics ("project X", "from:ceo")
   - Time depends on match count
```

**Gmail API Characteristics**:
- List messages: ~500ms per 100 messages
- Get message (full): ~200ms per message
- Get thread: ~300ms per thread
- Rate limit: 250 quota units/user/sec (1 get = 5 units)

**Realistic Time Estimates**:
| Scope | Messages | Est. Time | API Calls |
|-------|----------|-----------|-----------|
| Last 7 days, 50 msgs | 50 | 15-30 sec | ~60 |
| Last 30 days, 200 msgs | 200 | 1-2 min | ~220 |
| Last 90 days, 500 msgs | 500 | 3-5 min | ~550 |

---

### Slack

**Data Shape**: Channels (public/private), threads, direct messages

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SLACK EXTRACTION MODEL                             │
└─────────────────────────────────────────────────────────────────────────────┘

RESOURCE TYPES:
├── channel:{id}  → Specific channel by ID
├── channels:joined → All channels user has joined
├── channels:active → Channels with recent activity (last 7 days)
└── dm:{user_id}  → Direct message thread (requires explicit consent)

SCOPE PARAMETERS:
┌──────────────────┬──────────────────┬──────────────────┬──────────────────┐
│ Parameter        │ Min              │ Default          │ Max              │
├──────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ recency          │ 1 day            │ 7 days           │ 30 days          │
│ max_messages     │ 50               │ 200              │ 1000             │
│ max_channels     │ 1                │ 5                │ 20               │
│ include_threads  │ false            │ true             │ true             │
└──────────────────┴──────────────────┴──────────────────┴──────────────────┘

EXTRACTION MODES:
1. "single_channel" (default)
   - One channel, last N days
   - Threads expanded for context
   - ~20 sec for 200 messages

2. "multi_channel"
   - Multiple channels (user selected or active)
   - Per-channel limits apply
   - ~1-3 min for 5 channels

3. "project_focused"
   - Channels matching project keywords
   - Cross-channel thread following
   - ~2-5 min depending on matches
```

**Slack API Characteristics**:
- conversations.history: ~200ms per 100 messages
- conversations.replies: ~150ms per thread
- Rate limit: Tier 3 = 50 req/min
- Pagination: cursor-based, 100 items/page

**Realistic Time Estimates**:
| Scope | Messages | Est. Time | API Calls |
|-------|----------|-----------|-----------|
| 1 channel, 7 days | 200 | 15-30 sec | ~15-25 |
| 5 channels, 7 days | 1000 | 1-2 min | ~75-100 |
| 10 channels, 30 days | 2000+ | 3-5 min | ~150-200 |

---

### Notion

**Data Shape**: Pages in hierarchical workspaces, databases with records

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           NOTION EXTRACTION MODEL                            │
└─────────────────────────────────────────────────────────────────────────────┘

RESOURCE TYPES:
├── page:{id}       → Single page (includes blocks)
├── page_tree:{id}  → Page + all child pages (recursive)
├── database:{id}   → Database records
├── search:{query}  → Full-text search across workspace
└── recent          → Recently edited pages

SCOPE PARAMETERS:
┌──────────────────┬──────────────────┬──────────────────┬──────────────────┐
│ Parameter        │ Min              │ Default          │ Max              │
├──────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ max_depth        │ 1 (page only)    │ 2 (+ children)   │ 5                │
│ max_pages        │ 1                │ 10               │ 50               │
│ max_db_records   │ 10               │ 50               │ 200              │
│ recency_filter   │ none             │ 30 days          │ 365 days         │
└──────────────────┴──────────────────┴──────────────────┴──────────────────┘

EXTRACTION MODES:
1. "single_page" (default)
   - One page, full content
   - ~5-10 sec

2. "page_with_children"
   - Root page + direct children
   - ~20-40 sec for 10 pages

3. "full_tree"
   - Recursive traversal up to max_depth
   - ~1-3 min depending on tree size

4. "database_scan"
   - Query database, extract records
   - ~30 sec for 50 records
```

**Notion API Characteristics**:
- Get page: ~300ms
- Get block children: ~200ms per 100 blocks (paginated)
- Search: ~500ms per query
- Rate limit: 3 requests/sec average

**Realistic Time Estimates**:
| Scope | Pages | Est. Time | API Calls |
|-------|-------|-----------|-----------|
| Single page | 1 | 5-10 sec | 3-5 |
| Page + children | 5 | 20-40 sec | 15-25 |
| Project tree (depth 3) | 20 | 1-2 min | 60-80 |
| Database (50 records) | 50 items | 30-60 sec | 55-60 |

---

## Coverage Visibility: The "Landscape" Model

### The Problem: Unknown Unknowns

If YARNNN only shows what it extracted, users don't know:
- What else exists that wasn't extracted
- Whether their coverage is sufficient
- What they might be missing

This is like using a map that only shows roads you've driven - you don't know what other roads exist.

### The Solution: Platform Landscape Discovery

Before extraction, YARNNN should **discover** the user's platform landscape:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PLATFORM LANDSCAPE DISCOVERY                             │
└─────────────────────────────────────────────────────────────────────────────┘

For each connected platform, we fetch metadata (not content):

GMAIL LANDSCAPE:
├── Labels: [Primary, Social, Promotions, Updates, Work, Personal, ...]
├── Total messages: ~15,000
├── Unread: 47
└── Recent activity: 12 messages today

SLACK LANDSCAPE:
├── Workspace: "Acme Corp"
├── Channels joined: 23
│   ├── #general (1.2k members, 50 msgs/day)
│   ├── #engineering (45 members, 120 msgs/day)  ← High activity
│   ├── #product (30 members, 40 msgs/day)
│   └── ... 20 more
└── DMs: 8 active conversations

NOTION LANDSCAPE:
├── Workspace: "Acme Corp"
├── Top-level pages accessible: 12
│   ├── "Engineering Wiki" (47 subpages)
│   ├── "Product Roadmap" (23 subpages)
│   ├── "Team Directory" (12 subpages)
│   └── ... 9 more
└── Recently edited: 5 pages this week
```

**Key insight**: Landscape discovery is fast (metadata only) and gives users the full picture.

### Coverage State Model

For each resource in the landscape, track coverage state:

```
┌──────────────┬────────────────────────────────────────────────────────────┐
│ State        │ Meaning                                                    │
├──────────────┼────────────────────────────────────────────────────────────┤
│ uncovered    │ Resource exists, never extracted                           │
│ partial      │ Extracted with constraints (e.g., last 7 days only)        │
│ covered      │ Fully extracted within defined scope                       │
│ stale        │ Covered, but last sync > threshold (e.g., 7 days ago)      │
│ excluded     │ User explicitly marked as not relevant                     │
└──────────────┴────────────────────────────────────────────────────────────┘
```

### Coverage Visualization

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     INTEGRATION COVERAGE VIEW                                │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ Gmail ─────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  Coverage: ████████░░ 80%                          Last sync: 2 hours ago   │
│                                                                              │
│  ✓ Primary Inbox      [Last 7 days, 47 msgs]      ● Covered                 │
│  ✓ Sent               [Last 7 days, 23 msgs]      ● Covered                 │
│  ○ Work Label         [Not imported]              ○ Uncovered  [Import →]   │
│  ○ Social             [Excluded by user]          ◌ Excluded                │
│  ○ Promotions         [Excluded by user]          ◌ Excluded                │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌─ Slack ─────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  Coverage: ██████░░░░ 60%                          Last sync: 1 day ago     │
│                                                                              │
│  ✓ #engineering       [Last 7 days, 156 msgs]     ● Covered                 │
│  ✓ #product           [Last 7 days, 89 msgs]      ● Covered                 │
│  ✓ #standups          [Last 7 days, 42 msgs]      ● Covered                 │
│  ○ #general           [Not imported]              ○ Uncovered  [Import →]   │
│  ○ #random            [Not imported]              ○ Uncovered               │
│  ... 18 more channels                             [Show all →]              │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### "Known vs. Unknown" Transparency

The UI should always communicate:

| What YARNNN Knows | How to Show It |
|-------------------|----------------|
| Extracted context | "47 messages processed, 12 context blocks created" |
| Scope constraints | "Last 7 days only" / "Primary inbox only" |
| What's uncovered | "18 more channels not imported" |
| Freshness | "Last synced 2 hours ago" |
| Exclusions | "Social/Promotions excluded by you" |

**The goal**: User should never wonder "does YARNNN know about X?" They can see the full landscape and their coverage choices.

---

## Async Architecture

Context extraction is inherently async due to:
1. **Variable duration** (5 sec to 5+ min)
2. **External API dependencies** (rate limits, network latency)
3. **Agent processing** (LLM calls for interpretation)

### Job States

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           JOB STATE MACHINE                                  │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌──────────┐     ┌────────────┐     ┌───────────┐     ┌───────────┐
  │ pending  │────>│ fetching   │────>│ processing│────>│ completed │
  └──────────┘     └────────────┘     └───────────┘     └───────────┘
       │                 │                  │
       │                 ▼                  ▼
       │           ┌──────────┐       ┌──────────┐     ┌──────────┐
       └──────────>│  failed  │<──────│  failed  │     │  partial │
                   └──────────┘       └──────────┘     └──────────┘

States:
- pending: Job created, waiting for scheduler
- fetching: Actively calling external APIs
- processing: Agent interpreting/structuring data
- completed: All blocks stored successfully
- failed: Unrecoverable error
- partial: Some data extracted, some failed (retryable)
```

### Progress Tracking

```python
# integration_import_jobs table additions
{
    "id": "uuid",
    "status": "fetching",
    "progress": {
        "phase": "fetching",           # fetching | processing | storing
        "items_total": 150,            # Total items to process
        "items_completed": 47,         # Items completed so far
        "current_resource": "#engineering",  # Current channel/page
        "eta_seconds": 45,             # Estimated time remaining
        "started_at": "2026-02-06T..."
    },
    "result": null  # Populated on completion
}
```

### Scheduler Integration

```python
# unified_scheduler.py additions

async def process_import_jobs():
    """Process pending import jobs with progress tracking."""

    pending = await get_pending_import_jobs()

    for job in pending:
        # Update to fetching
        await update_job_status(job.id, "fetching", progress={
            "phase": "fetching",
            "items_total": estimate_total(job),
            "items_completed": 0
        })

        try:
            # Fetch with progress callbacks
            raw_data = await fetch_with_progress(
                job,
                on_progress=lambda p: update_job_progress(job.id, p)
            )

            # Update to processing
            await update_job_status(job.id, "processing")

            # Agent extraction
            result = await extract_context(raw_data, job)

            # Store results
            await store_memories(result.blocks)

            # Complete
            await update_job_status(job.id, "completed", result=result)

        except Exception as e:
            await update_job_status(job.id, "failed", error=str(e))
```

---

## Scope Configuration UI

### User-Facing Controls

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     IMPORT CONFIGURATION MODAL                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ Import from Gmail ─────────────────────────────────────────────────────────┐
│                                                                              │
│  Source: [Inbox ▼]  [Primary only] [Include Sent ✓]                         │
│                                                                              │
│  Time Range:                                                                 │
│  ○ Last 7 days (recommended) ── ~30 seconds                                 │
│  ○ Last 30 days ── ~2 minutes                                               │
│  ○ Last 90 days ── ~5 minutes                                               │
│  ○ Custom: [___] days                                                       │
│                                                                              │
│  Max Messages: [100 ▼]                                                      │
│                                                                              │
│  ┌─ Advanced ─────────────────────────────────────────────────────────────┐ │
│  │ □ Include threads (expand full conversations)                          │ │
│  │ □ Learn my writing style from sent messages                            │ │
│  │ □ Focus: [_________________________________] (optional keywords)       │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│                                        [Cancel]  [Start Import]             │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Smart Defaults by Use Case

| Use Case | Recommended Scope | Rationale |
|----------|-------------------|-----------|
| Onboarding | 7 days, 100 msgs | Quick time-to-value |
| Project kickoff | 30 days, selected channels | Capture relevant history |
| Full context build | 90 days, multiple sources | Comprehensive but slow |
| Refresh/update | 7 days since last sync | Incremental, fast |

---

## Cost Considerations

### LLM Processing Costs

Context extraction uses Claude for interpretation. Cost factors:

| Stage | Input Tokens | Output Tokens | Est. Cost |
|-------|--------------|---------------|-----------|
| 50 messages | ~25K | ~2K | ~$0.08 |
| 200 messages | ~100K | ~5K | ~$0.35 |
| 500 messages | ~250K | ~10K | ~$0.85 |

**Mitigation**:
- Use Haiku for extraction (cheaper, fast)
- Batch messages into chunks (reduce calls)
- Cache extracted blocks (don't re-process)

### API Rate Limits

| Platform | Rate Limit | Burst | Recovery |
|----------|------------|-------|----------|
| Gmail | 250 units/sec | 1M/day | Exponential backoff |
| Slack | 50 req/min | Tier 3 | 429 retry |
| Notion | 3 req/sec | 100 req burst | Retry-After header |

**Handling**:
- Implement per-platform rate limiters
- Queue requests with delays
- Surface rate limit errors to user

---

## Comparison: Deep Research Analogy

Context extraction is similar to Claude Code's deep research flow:

| Aspect | Deep Research | Context Extraction |
|--------|---------------|-------------------|
| **Scope** | Query-driven exploration | Platform/time/volume bounds |
| **Duration** | Minutes to hours | Seconds to minutes |
| **Progress** | "Searching...", "Found X files" | "Fetching...", "Processing X/Y" |
| **Output** | Synthesized answer | Structured memory blocks |
| **Iteration** | May refine query | May need scope adjustment |

**Key Insight**: Users tolerate longer waits when they see meaningful progress.

```
✗ Bad: "Importing..." (spinner for 3 minutes)

✓ Good:
  "Fetching emails from inbox..."
  "Retrieved 127 messages (30 sec remaining)"
  "Extracting context with AI..."
  "Found 12 decisions, 8 action items"
  "Import complete! View summary →"
```

---

## Deliverable-Specific Context Handling

### The Two Context Modes

Deliverables need context from integrations, but the timing and scope differ:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONTEXT MODES FOR DELIVERABLES                            │
└─────────────────────────────────────────────────────────────────────────────┘

MODE 1: USER-IMPORTED CONTEXT (Pre-extracted)
─────────────────────────────────────────────
User explicitly imports → Stored as memories → Deliverable uses cached context

Flow:
  User clicks "Import #engineering"
    → Background job extracts
    → Memories created (source_type='import')
    → Deliverable retrieves relevant memories at runtime

Characteristics:
  ✓ Fast at deliverable runtime (no API calls)
  ✓ User has full control over what's included
  ✗ Can become stale
  ✗ Requires user action to set up


MODE 2: DELIVERABLE-SCOPED FETCH (On-demand)
────────────────────────────────────────────
Deliverable configured with sources → Fresh fetch at each run

Flow:
  Deliverable runs
    → Gather step fetches from Gmail/Slack/Notion
    → Agent processes fresh data
    → Content generated with current context

Characteristics:
  ✓ Always fresh
  ✓ Scope tied to deliverable purpose
  ✗ Slower (API + processing at runtime)
  ✗ Unpredictable duration
```

### Recurring Deliverables: Special Considerations

Recurring deliverables (daily status report, weekly digest) have different needs:

| Aspect | One-time Deliverable | Recurring Deliverable |
|--------|---------------------|----------------------|
| **Context freshness** | "Now" is fine | Need "since last run" |
| **Scope** | User-defined once | Should be consistent |
| **Duration tolerance** | User waits | Should be predictable |
| **Failure impact** | User retries | Missed delivery = problem |

### Delta Extraction for Recurring Deliverables

For recurring deliverables, we should fetch **only what's new since last run**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DELTA EXTRACTION MODEL                                    │
└─────────────────────────────────────────────────────────────────────────────┘

Deliverable: "Daily Inbox Summary"
Schedule: Every day at 8am
Sources: Gmail inbox

RUN 1 (Monday 8am):
  last_run_at: null
  fetch: "last 24 hours" (or last 7 days for first run)
  result: 47 messages → summary generated

RUN 2 (Tuesday 8am):
  last_run_at: Monday 8am
  fetch: "since Monday 8am" (delta only)
  result: 23 messages → summary generated

RUN 3 (Wednesday 8am):
  last_run_at: Tuesday 8am
  fetch: "since Tuesday 8am"
  result: 31 messages → summary generated
```

**Implementation**:
```python
# In deliverable sources config
{
    "type": "integration_import",
    "provider": "gmail",
    "source": "inbox",
    "scope": {
        "mode": "delta",           # "delta" or "fixed_window"
        "fallback_days": 7,        # If no last_run, go back 7 days
        "max_items": 200           # Safety cap
    }
}
```

### Deliverable Source Configuration UI

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DELIVERABLE SOURCES                                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ Daily Inbox Summary ───────────────────────────────────────────────────────┐
│                                                                              │
│  Sources:                                                                    │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ ✉ Gmail - Primary Inbox                                                │ │
│  │   Scope: Since last run (delta)                                        │ │
│  │   Fallback: Last 7 days if first run                                   │ │
│  │   Max: 200 messages                                                    │ │
│  │                                                                        │ │
│  │   Coverage: ● Using your imported context                              │ │
│  │   Last fetch: 47 messages (Tuesday 8:00am)                             │ │
│  │                                                      [Configure →]     │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  [+ Add Source]                                                             │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Estimated fetch time per run: ~15-30 seconds                               │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Context Freshness Indicators

For deliverables using pre-imported context, show freshness:

```
┌─ Context Status ────────────────────────────────────────────────────────────┐
│                                                                              │
│  This deliverable uses context from:                                         │
│                                                                              │
│  ✓ Gmail inbox         Last synced: 2 hours ago       ● Fresh               │
│  ✓ #engineering        Last synced: 1 day ago         ◐ Getting stale       │
│  ⚠ #product            Last synced: 8 days ago        ○ Stale [Refresh →]   │
│                                                                              │
│  [Refresh All Context]                                                      │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Runtime Behavior: Pre-imported vs. On-demand

| Deliverable Type | Context Mode | Behavior |
|------------------|--------------|----------|
| **Daily Inbox Summary** | On-demand delta | Fetches new emails since last run |
| **Weekly Status Report** | Mixed | On-demand for Slack, pre-imported for Notion |
| **Project Brief** | Pre-imported | Uses cached context from imports |
| **Reply Draft** | On-demand | Fetches specific thread fresh |

### Failure Handling for Recurring Deliverables

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    RECURRING DELIVERABLE FAILURE MODES                       │
└─────────────────────────────────────────────────────────────────────────────┘

SCENARIO: Daily Inbox Summary, Gmail fetch fails

OPTION A: Skip and Notify
  - Mark this run as failed
  - Notify user: "Daily summary failed - Gmail unavailable"
  - Next run fetches since last successful run (catches up)

OPTION B: Retry with Backoff
  - Retry 3x with exponential backoff (1min, 5min, 15min)
  - If all fail, fall back to Option A

OPTION C: Partial Generation
  - If Slack works but Gmail fails
  - Generate partial deliverable with available context
  - Note: "Gmail context unavailable for this run"

RECOMMENDATION: Option B with fallback to A
```

---

## Implementation Phases

### Phase 1: Scope Parameters & Validation

- [ ] Add scope parameters to import job schema
- [ ] Implement per-platform scope validation
- [ ] Update import endpoints with scope options
- [ ] Add time/volume estimation logic

### Phase 2: Platform Landscape Discovery

- [ ] Implement landscape fetch for each platform (metadata only)
- [ ] Store landscape snapshot in user_integrations metadata
- [ ] Create coverage state model (uncovered/partial/covered/stale/excluded)
- [ ] Landscape refresh on OAuth reconnect

### Phase 3: Coverage Visibility UI

- [ ] Integration coverage view component
- [ ] Per-resource coverage state indicators
- [ ] "Import" action on uncovered resources
- [ ] Freshness/staleness indicators

### Phase 4: Progress Tracking

- [ ] Add progress fields to import_jobs table
- [ ] Implement progress callbacks in fetch logic
- [ ] Create progress polling endpoint
- [ ] Frontend progress indicator component

### Phase 5: Deliverable Source Configuration

- [ ] Delta extraction mode for recurring deliverables
- [ ] Source scope configuration UI
- [ ] Freshness indicators on deliverable sources
- [ ] Failure handling for recurring deliverables

### Phase 6: Optimization

- [ ] Haiku for extraction (cost reduction)
- [ ] Parallel fetching where safe
- [ ] Incremental/delta extraction
- [ ] Caching layer for repeated imports

---

## Open Questions

1. **Should landscape discovery auto-run on OAuth connect?**
   - Pro: User immediately sees their platform overview
   - Con: Additional API calls, slight delay

2. **How granular should coverage tracking be?**
   - Per-label/channel/page level?
   - Or just per-platform summary?

3. **Should we recommend what to import?**
   - "We noticed #engineering has high activity - import it?"
   - Based on activity levels, recent edits, etc.

4. **How do we handle partial failures?**
   - Some messages fetched, API fails mid-job
   - Store partial results? Retry from checkpoint?

5. **Delta extraction: what if user misses runs?**
   - Deliverable scheduled daily but user is offline for 3 days
   - Should we catch up with 3 days of context or just last 24h?

6. **Cross-platform context for single deliverable?**
   - "Weekly update" pulls from Gmail + Slack + Notion
   - Unified progress? Parallel or sequential fetches?

---

## References

- [ADR-027: Integration Read Architecture](./ADR-027-integration-read-architecture.md)
- [ADR-029: Email Integration Platform](./ADR-029-email-integration-platform.md)
- [Gmail API Quotas](https://developers.google.com/gmail/api/reference/quota)
- [Slack Rate Limits](https://api.slack.com/docs/rate-limits)
- [Notion Rate Limits](https://developers.notion.com/reference/request-limits)
