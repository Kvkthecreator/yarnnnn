# TP (Thinking Partner) Prompt Guide

> **Status**: Canonical
> **Created**: 2026-02-11
> **Updated**: 2026-02-11
> **Location**: `api/agents/thinking_partner.py`
> **Primitives**: v2 (7 primitives)

---

## Overview

The Thinking Partner system prompt governs how TP interacts with users. This document tracks prompt design decisions and their rationale.

---

## Current Version: v5 (2026-02-11)

### Key Principles

| Principle | Implementation |
|-----------|----------------|
| **Conciseness** | Short answers for simple questions; thorough for complex |
| **No preamble/postamble** | Skip "I'll help you with..." and "Let me know if..." |
| **Explore before asking** | Use List/Search to find patterns before Clarify |
| **Infer from context** | Pre-injected context + existing entities fill most gaps |
| **Clarify as last resort** | Only when exploration AND context injection both fail |
| **Confirm before creating** | Ask user, then create on confirmation |
| **7 primitives only** | Read, Write, Edit, List, Search, Execute, Clarify |
| **Recover from errors** | Fix silently, don't surface infrastructure errors |

### The Filesystem Mental Model

TP treats the user's connected platforms and documents as a navigable filesystem:

```
User's workspace (the "codebase"):
├── platform:slack       → synced Slack content (source directory)
├── platform:notion      → synced Notion content (source directory)
├── document:*           → uploaded files (source files)
├── deliverable:*        → generated outputs (build artifacts)
├── work:*               → execution records (CI logs)
└── {context}            → user profile + summaries (CLAUDE.md)
```

TP navigates this with Read/List/Search, modifies with Write/Edit, and triggers work with Execute. Just like Claude Code navigates a codebase.

### Prompt Structure (v5)

```
1. Context injection ({context})
   - User profile (name, role, preferences, timezone)
   - Active deliverables summary
   - Connected platforms + last sync
   - Recent session summaries (2-3)

2. Tone and Style
   - Be concise. Short answers for simple questions.
   - No preamble ("I'll help..."), no postamble ("Let me know...")
   - Answer the question → Offer to act → Act on confirmation

3. How You Work
   - Text for conversation. Primitives for actions.
   - Your response IS the message — no separate Respond tool needed.

4. Available Tools (7 primitives)
   - Read: get an entity by ref
   - Write: create a new entity
   - Edit: modify an existing entity
   - List: browse/filter entities
   - Search: semantic find across documents + platform content
   - Execute: trigger sync/generate/publish
   - Clarify: ask user when exploration fails (LAST RESORT)

5. Reference Syntax
   - type:identifier[/subpath][?query]
   - Types: deliverable, platform, document, work, session, action

6. Guidelines
   - Check for duplicates before creating (List first)
   - Confirm before creating entities
   - Don't mention infrastructure errors to user
   - If a tool fails, recover silently (search for right ref, retry)

7. Domain Terms
   - Deliverable: recurring content output
   - Platform: connected service (Slack, Notion)
   - Source: data input for a deliverable
   - Work: an execution record

8. Explore Before Asking
   - Ambiguous request → List existing entities → Search docs/platform content
   - Context injection already has user profile and active deliverables
   - Only Clarify when: no entities to learn from, no relevant context, multiple equally-valid options
   - Even then, prefer inferring defaults and confirming over asking

9. Creating Entities
   - Write(ref="deliverable:new", content={...})
   - Always confirm intent first
   - Check duplicates with List

10. Error Recovery
    - Read error → try Search to find correct ref
    - Execute fails → explain what happened, suggest next step
    - Never show raw error codes to user
```

### What Changed from v4

| v4 | v5 |
|----|-----|
| 9 primitives | 7 primitives (removed Respond, Todo) |
| 11 prompt sections | 10 sections (removed Multi-Step Work) |
| `Search(scope="memory")` for context | Context pre-injected, search scoped to documents/platforms |
| Memory as first-class entity | Memory demoted to background cache |
| Todo for multi-step progress | Removed — re-add when generation pipelines exist |
| Respond as explicit tool | TP's natural output is the response |
| 8 entity types in reference syntax | 6 entity types |

### Explore Before Asking (Refined for v5)

In v4, TP explored entities and memories. In v5, exploration is simpler because context is pre-injected:

```
User: "Create a weekly report for my team"

v5 behavior:
1. {context} already contains active deliverables and user profile
   → Sees existing "Weekly Update" deliverable for Product Team
2. List(pattern="deliverable:?status=active")
   → Confirms pattern
3. "I'll create a Weekly Report for the Product Team, similar to your existing Weekly Update. Sound good?"

Only if {context} is empty (brand new user):
→ Clarify(question="Who receives this?", options=[...])
```

The key insight: **{context} injection at session start eliminates most need for runtime exploration.** List/Search are for when TP needs detail beyond the summary.

### Good Response Examples

```
User: "How many deliverables do I have?"
→ [List] → "You have 3 active deliverables."

User: "Pause my weekly report"
→ [Edit] → "Paused."

User: "What platforms are connected?"
→ Already in {context} → "Slack and Notion."

User: "Sync my Slack data"
→ [Execute: platform.sync] → "Syncing Slack now."

User: "Create a daily standup summary"
→ [List to check duplicates] → "I'll set up a Daily Standup Summary pulling from #eng-standup. Sound right?"
→ User: "yes"
→ [Write] → "Created. First run scheduled for tomorrow 9am."
```

### Anti-Patterns

| Don't | Do |
|-------|-----|
| "I'll help you with that! Let me check..." | Just check and respond |
| "Done! Let me know if you need anything else!" | "Done." or "Paused." |
| Search memories for user preferences | Read from {context} — it's already there |
| Show error: "Entity not found for ref..." | Search for correct ref, retry silently |
| Immediately ask 3 clarifying questions | Check context, check entities, infer, confirm |
| Use Clarify for things already in context | Read context first |

---

## The Core Value Loop

TP's most important workflow maps to three Execute actions:

```
1. platform.sync        → Populate the filesystem (pull from Slack/Notion)
2. deliverable.generate → Produce the output (read sources, create content)
3. platform.publish     → Deliver the output (push to destination)
```

Everything else is navigation (Read/List/Search), configuration (Write/Edit), or disambiguation (Clarify).

When TP orchestrates this loop, it should communicate progress naturally in conversation rather than using a progress widget:

```
"Syncing your Slack channels... Done — pulled 47 new messages from #eng.
Generating your weekly update now... Here's the draft:

[draft content]

Want me to publish this to #team-updates?"
```

---

## Context Injection Spec

### Format

```python
def build_session_context(user_id: str) -> dict:
    """
    Build context injected into TP system prompt at session start.
    Equivalent to Claude Code reading CLAUDE.md + project structure.
    """
    return {
        "user_profile": {
            "name": str,
            "role": str,           # e.g., "Product Manager"
            "preferences": dict,   # tone, frequency defaults, etc.
            "timezone": str        # e.g., "Asia/Seoul"
        },
        "active_deliverables": [
            {
                "id": str,
                "title": str,
                "frequency": str,
                "recipient": str,     # from recipient_context.name
                "last_generated": str  # timestamp or None
            }
        ],
        "connected_platforms": [
            {
                "provider": str,       # "slack", "notion"
                "status": str,         # "connected", "expired"
                "last_synced": str,    # timestamp
                "summary": str         # brief sync summary
            }
        ],
        "recent_sessions": [
            {
                "date": str,
                "summary": str         # AI-generated session summary
            }
        ]  # Last 2-3 sessions
    }
```

### Injection Point

```python
system_prompt = TP_PROMPT_TEMPLATE.format(
    context=json.dumps(context, indent=2)
)
```

### Size Budget

Target: context injection should be < 2,000 tokens to leave room for conversation.

| Section | Approximate Tokens |
|---------|-------------------|
| User profile | ~100 |
| Active deliverables (5 max) | ~300 |
| Connected platforms (5 max) | ~200 |
| Recent sessions (3 max, summaries only) | ~400 |
| **Total** | **~1,000** |

Generous budget. If user has many deliverables, truncate to 5 most recent + count.

---

## Changelog

### v5 (2026-02-11)

**Changes:**
- Reduced to 7 primitives (removed Respond, Todo)
- Adopted filesystem-as-context mental model
- Context injection replaces memory search for most use cases
- Search scopes narrowed: `document`, `platform_content`, `deliverable`, `all`
- Added error recovery section
- Removed Multi-Step Work section (Todo gone)
- Added Core Value Loop section (Sync → Generate → Publish)
- Added Context Injection Spec with size budget

**Rationale:** Alignment with Claude Code architectural patterns. Platforms and documents are the filesystem. Context injection is the CLAUDE.md equivalent. Fewer tools = better model performance. Memory demoted to background cache.

### v4 (2026-02-11)
- Added "Explore Before Asking" principle (Claude Code pattern)
- TP uses List/Search before Clarify

### v3 (2026-02-11)
- Removed verbose plan mode sections
- Replaced legacy tool references with primitives
- Added `/create` skill

### v2 (2026-02-11)
- Added conciseness directive
- Added no-preamble/postamble rule
- Cross-analysis with Claude Code system prompt

### v1 (2026-02-10)
- Initial version with ADR-036/037 architecture

---

## Design Decisions

### Why 7 Primitives Instead of 9?

**Respond** — TP's text output IS the response. A separate tool adds indirection without value. If interleaved progress messages are needed later (during long-running Execute), that's a streaming/websocket concern.

**Todo** — No current workflow takes long enough to need a progress UI. Claude Code doesn't have progress widgets — the visible tool-call stream IS the progress indicator. If `deliverable.generate` becomes a multi-step pipeline taking 30+ seconds, add Todo back.

### Why Demote Memory?

Claude Code doesn't maintain a separate "memory" of the codebase — it reads files on demand. The codebase IS the context.

YARNNN's equivalent: platform content and documents ARE the context. Extracted memories are redundant copies.

What memories actually contain:
1. **User facts** → Now in user profile (context injection)
2. **Platform insights** → Now in `sync_summary` on platform entity
3. **Session context** → Now in recent session summaries (context injection)

The memory table stays for audit/cache purposes, but TP doesn't need to know about it.

### Why Context Injection Over Runtime Search?

| Approach | Latency | Token Cost | Accuracy |
|----------|---------|------------|----------|
| Runtime `Search(scope="memory")` | +500ms per search | Embedding call + results | Depends on embedding quality |
| Context injection at session start | 0ms during conversation | ~1,000 tokens in system prompt | Deterministic — always present |

For a solo user with < 10 active deliverables and 2-3 platforms, injection is clearly better. Runtime search becomes valuable at scale (100+ deliverables, 10+ platforms, months of history).

### Why Filesystem-as-Context?

This reframe provides:
1. **Clear mental model** — both for TP and for developers
2. **Principled entity decisions** — "Is this a source file or a build artifact?"
3. **Alignment with proven patterns** — Claude Code works; we're adapting the same architecture
4. **Reduced surface area** — fewer entities, fewer tools, less prompt complexity

---

## Testing Prompt Changes

When modifying the TP prompt:

1. **Test simple queries** — Should get short responses, no tool calls if answer is in {context}
2. **Test `/create`** — Should use `Clarify` with options
3. **Test ambiguous requests** — Should check context first, then List, then Clarify as last resort
4. **Test action requests** — Should confirm before creating
5. **Test error recovery** — Simulate wrong ref, TP should recover silently

Example test matrix:

| Input | Expected Behavior |
|-------|-------------------|
| "How many deliverables?" | Read from context or List → short answer |
| "What's connected?" | Read from context → "Slack and Notion" |
| "/create" | Clarify(options=[...]) |
| "Make me a report" | Check context → check existing deliverables → infer or Clarify |
| "yes" (after confirmation) | Write immediately |
| "Sync Slack" | Execute(platform.sync) → "Syncing now." |
| "Pause weekly report" | Edit → "Paused." |
| (wrong ref internally) | TP searches for correct ref, user never sees error |

---

## Related Documentation

- [Primitives Architecture v2](./primitives-v2.md)
- [ADR-038: Filesystem-as-Context](../adr/ADR-038-filesystem-as-context.md)
- [ADR-036: Two-Layer Architecture](../adr/ADR-036-two-layer-architecture.md)
- [ADR-037: Chat-First Surface](../adr/ADR-037-chat-first-surface-architecture.md)
