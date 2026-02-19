# TP (Thinking Partner) Prompt Guide

> **Status**: Canonical
> **Created**: 2026-02-11
> **Updated**: 2026-02-19
> **Location**: `api/agents/thinking_partner.py`
> **Primitives**: 9 (ADR-038 + ADR-045 + list_integrations)
> **Platform Tools**: Slack, Notion, Gmail, Calendar (ADR-046, ADR-050)
> **Related**: [ADR-038: Filesystem-as-Context](../adr/ADR-038-filesystem-as-context.md), [ADR-050: MCP Gateway](../adr/ADR-050-mcp-gateway-architecture.md), [ADR-065: Live-First Platform Context](../adr/ADR-065-live-first-platform-context.md)

---

## Overview

The Thinking Partner system prompt governs how TP interacts with users. This document tracks prompt design decisions and their rationale.

**Prompt Versioning**: See `api/services/platform_tools.py` for `PROMPT_VERSIONS` dict.

---

## Current Version: v6.1 (2026-02-19)

### Key Principles

| Principle | Implementation |
|-----------|----------------|
| **Conciseness** | Short answers for simple questions; thorough for complex |
| **No preamble/postamble** | Skip "I'll help you with..." and "Let me know if..." |
| **Context-first** | Check `{context}` injection before exploring or asking |
| **Explore before asking** | Use List/Search to find patterns before using Clarify |
| **One clarifying question** | Use `Clarify` only when context + exploration don't resolve ambiguity |
| **Confirm before creating** | Ask user, then create on confirmation |
| **9 primitives** | Read, Write, Edit, List, Search, Execute, WebSearch, list_integrations, Clarify (no Respond, no Todo) |
| **Live tools first** | For platform content queries, call live platform tools before searching the cache (ADR-065) |
| **Disclose cache use** | When `filesystem_items` fallback is used, tell the user the data age (ADR-065) |
| **Sync hand-off** | After triggering sync, inform user and stop — sync is async, no in-conversation polling tool available (ADR-065) |

### Platform Content Access (ADR-065)

This is the most significant v6 change. Prior to v6, TP used `Search(scope="platform_content")` as the primary path for conversational platform queries. This was wrong: TP has direct live platform tools and should use them first.

**Access order:**

```
1. LIVE (primary) — platform_slack_*, platform_gmail_*, platform_notion_*, platform_calendar_*
   → Direct API call. Always current. Use this first.

2. CACHE FALLBACK — Search(scope="platform_content")
   → Queries filesystem_items (ILIKE). May be hours old.
   → Use only when live tools can't serve the query (cross-platform aggregation, tool unavailable).
   → MUST disclose cache age: "Based on content synced 3 hours ago..."

3. EMPTY CACHE → SYNC → HAND OFF TO USER
   → Execute(action="platform.sync", target="platform:slack")
   → Inform user: "I've started syncing — takes ~30–60 seconds. Ask again once it's done."
   → STOP. No in-conversation polling tool available. Sync is async.
   → User re-engages after sync completes; cache will be populated then.
```

**Why this matters:** The empty-query bug (`Search(query="")` after triggering sync) was caused by TP not having this model. It hit an empty cache, triggered sync, then immediately re-queried — getting nothing — because the job is async. With live tools as primary, the sync loop is only ever the last resort.

**Memory is not a search domain.** `scope="memory"` is removed from valid Search scopes. Memory is injected into the system prompt at session start (working memory block). TP already has it. Searching it mid-conversation is redundant and architecturally wrong (ADR-065).

### The Filesystem Mental Model (ADR-038)

TP treats the user's connected platforms and documents as a navigable filesystem:

```
User's workspace (the "codebase"):
├── platform:slack       → synced Slack content (source directory)
├── platform:notion      → synced Notion content (source directory)
├── document:*           → uploaded files (source files)
├── deliverable:*        → generated outputs (build artifacts)
├── work:*               → execution records (CI logs)
└── {context}            → user profile + summaries (CLAUDE.md equivalent)
```

TP navigates this with Read/List/Search, modifies with Write/Edit, and triggers work with Execute.

### Context Injection

At session start, TP receives pre-loaded context (eliminating most runtime searches):

```python
{context} = {
    "user_profile": { name, role, preferences, timezone },
    "active_deliverables": [ { title, frequency, recipient, next_run } ],
    "connected_platforms": [ { provider, status, last_synced, freshness } ],
    "recent_sessions": [ { date, summary } ]
}
```

**Check `{context}` first** before using List/Search. The answer is often already there.

### The "Grep Before Ask" Pattern

**Claude Code approach:** When facing ambiguity, Claude Code explores the codebase (Grep, Glob, Read) to find evidence before asking the user. It infers from existing patterns.

**YARNNN equivalent:** TP should check context, then explore entities, before asking clarifying questions.

```
User: "Create a weekly report for my team"

✅ v5.1 behavior:
1. Check {context} → sees existing deliverables for "Product Team"
2. List(pattern="deliverable:?status=active") → confirms pattern
3. "I'll create a Weekly Report for the Product Team. Sound good?"

Only if {context} is empty AND exploration finds nothing:
→ Clarify(question="Who receives this?", options=[...])
```

### Prompt Structure (9 Primitives + Platform Tools)

```
1. Context injection ({context}) - user profile, deliverables, platforms, sessions
2. Tone and Style - conciseness rules
3. How You Work - text primary, tools for actions
4. Available Tools - 9 primitives (Read, Write, Edit, List, Search, Execute, WebSearch, list_integrations, Clarify)
5. Platform Tools - platform_slack_*, platform_notion_*, platform_gmail_*, platform_calendar_* (ADR-046, ADR-050)
   (dynamically loaded; tool descriptions carry full workflow docs — no separate prompt layer)
6. Reference Syntax - type:identifier
7. Guidelines - behavioral rules
8. Domain Terms - vocabulary
9. Explore Before Asking - context → List/Search → Clarify (last resort)
10. Confirming Before Acting - when to confirm vs just do it
11. Creating Entities - Write examples
```

**v5.2 changes:**
- Added platform tools with prompt versioning (see `PROMPT_VERSIONS`)
- Slack: streamlined for personal DM pattern (send to `authed_user_id`)
- Notion: fixed MCP server tool names (`notion-search`, `notion-create-comment`)
- Gmail: Direct API tools (`search`, `get_thread`, `send`, `create_draft`)
- Calendar: Direct API tools (`list_events`, `get_event`, `create_event`)

**v5.1 changes:**
- Removed Respond primitive (TP's text output IS the response)
- Removed Todo primitive (streaming tool calls ARE the progress indicator)
- Added context injection as primary information source

### Platform Tools (ADR-046, ADR-050)

Platform tools are dynamically added based on user's connected integrations:

| Provider | Tools | Backend |
|----------|-------|---------|
| **Slack** | `platform_slack_send_message`, `platform_slack_list_channels`, `platform_slack_get_channel_history` | MCP Gateway |
| **Notion** | `platform_notion_search`, `platform_notion_get_page`, `platform_notion_create_comment` | Direct API |
| **Gmail** | `platform_gmail_search`, `platform_gmail_get_thread`, `platform_gmail_send`, `platform_gmail_create_draft` | Direct API |
| **Calendar** | `platform_calendar_list_events`, `platform_calendar_get_event`, `platform_calendar_create_event` | Direct API |

**Default Landing Zones** (ADR-050):

Each platform has a "default landing zone" so user owns the output:

| Platform | Default Destination | Metadata Key | User Action |
|----------|---------------------|--------------|-------------|
| **Slack** | User's DM to self | `authed_user_id` | User forwards from DM |
| **Notion** | User's designated page | `designated_page_id` | User moves from YARNNN page |
| **Gmail** | Draft to user's email | `user_email` | User reviews & sends draft |
| **Calendar** | User's designated calendar | `designated_calendar_id` | Events on their calendar |

**Workflow for platform actions:**
1. Call `list_integrations` to get metadata
2. Use the returned IDs in tool calls (default to self)
3. Confirm with clear destination: "I've drafted that to your email." or "I've sent that to your Slack DM."

**Why "default to self"?** Work done by YARNNN should be owned by the user. Sending to self lets user review, edit, and scaffold before sharing with others.

### Good Response Examples

```
User: "How many deliverables do I have?"
→ [List] → "You have 3 active deliverables."

User: "Pause my weekly report"
→ [Edit] → "Paused."

User: "What platforms are connected?"
→ [List] → "Slack and Notion."
```

### Anti-Patterns

| Don't | Do |
|-------|-----|
| "I'll help you with that! Let me check..." | Just check and respond |
| "Done! Let me know if you need anything else!" | "Done." or "Paused." |
| Immediately create deliverable on request | Confirm intent first |
| Ask 3 clarifying questions | Ask ONE, infer the rest |

---

## Changelog

### v6.1 (2026-02-19)

**Changes:**
- `list_integrations` wired as a real PRIMITIVES entry (`registry.py`); previously a ghost tool documented in the prompt but not in schema
- `platforms.py` PLATFORMS_SECTION slimmed from ~130 to ~30 lines — per-tool workflow docs moved to tool `description` fields
- `platform_slack_get_channel_history` added to Slack tools table (was missing; MCP name bug also fixed in `platform_tools.py`)
- Primitive count updated to 9 (was 7): adds WebSearch (already shipped) and list_integrations

**Rationale:** Claude Code's pattern — tool `description` fields carry all model-facing workflow docs; no separate prompt layer. The `get_channel_history` MCP name mismatch was caused by a prompt layer that could diverge from execution silently. Tool descriptions co-located with handler mappings in `registry.py` and `platform_tools.py` cannot drift independently.

**Files changed:**
- `api/services/primitives/registry.py` — LIST_INTEGRATIONS_TOOL added; handler wired
- `api/agents/tp_prompts/platforms.py` — PLATFORMS_SECTION reduced to behavioral framing
- `api/services/platform_tools.py` — `get_channel_history` → `slack_get_channel_history` mapping added (CHANGELOG `[2026.02.19.4]`)

### v6 (2026-02-19)

**Changes:**
- Reframed platform content access as live-first: live platform tools are primary, `filesystem_items` is fallback
- Added explicit fallback disclosure requirement: TP must tell the user when a response uses cached content, including cache age
- Added sync hand-off pattern: after `Execute(action="platform.sync")`, TP informs the user and stops — sync is async, no in-conversation polling tool; user re-engages after sync completes
- Removed `scope="memory"` from valid Search scopes: Memory is injected at session start, not searched mid-conversation

**Rationale:** ADR-065. TP had live platform tools available but was hitting the `filesystem_items` cache first. Cache empty → trigger sync → immediate re-query → still empty (async race). With live tools as primary, this failure mode is eliminated. Fallback cache is valid for aggregation queries but must be disclosed to the user.

**Files changed:**
- `api/agents/tp_prompts/behaviors.py` — Added "Platform Content Access" section
- `api/services/primitives/search.py` — Removed silent `scope="memory"` redirect; added `synced_at` to platform_content results

### v5.2 (2026-02-12)

**Changes:**
- Added platform tools: `platform_slack_*`, `platform_notion_*`, `platform_gmail_*`, `platform_calendar_*`
- Added prompt versioning (`PROMPT_VERSIONS` dict in `platform_tools.py`)
- Slack streamlined for personal DM pattern (send to `authed_user_id`)
- Notion streamlined for designated page pattern (write to `designated_page_id`)
- Notion fixed for official MCP server (`notion-search`, `notion-create-comment`)
- Gmail/Calendar via Direct API (not MCP) per ADR-046
- `list_integrations` now exposes landing zone IDs: `authed_user_id` (Slack), `designated_page_id` (Notion), `user_email` (Gmail), `designated_calendar_id` (Calendar)

**Rationale:** ADR-050 MCP Gateway enables direct platform access. ADR-046 adds Gmail/Calendar. Streamlined patterns ensure user owns their outputs (DM to self, designated page for Notion, drafts for review).

**Prompt Versioning:**
```python
PROMPT_VERSIONS = {
    "platform_tools": {"version": "2026-02-12", "adr_refs": ["ADR-046", "ADR-050"]},
    "slack": {"version": "2026-02-12", "adr_refs": ["ADR-050"]},
    "notion": {"version": "2026-02-12", "adr_refs": ["ADR-050"]},
    "gmail": {"version": "2026-02-12", "adr_refs": ["ADR-046"]},
    "calendar": {"version": "2026-02-12", "adr_refs": ["ADR-046"]},
}
```

### v5.1 (2026-02-11)

**Changes:**
- Removed Respond primitive (TP's text IS the response)
- Added context injection (`build_session_context()`)
- Added filesystem mental model documentation (ADR-038)
- Reduced to 7 primitives: Read, Write, Edit, List, Search, Execute, Clarify
- Updated exploration pattern: context → List/Search → Clarify

**Rationale:** ADR-038 establishes that platforms and documents are YARNNN's "filesystem". Context injection eliminates most runtime searches. Respond was redundant with TP's natural output.

### v5 (2026-02-11)

**Changes:**
- Removed Todo primitive from TP tools
- Streaming tool calls ARE the progress indicator (Claude Code pattern)
- Simplified prompt: 8 primitives instead of 9

**Rationale:** Claude Code doesn't have a "todo" primitive because the conversation itself is the progress tracker. Users see tool calls happening in sequence. Adding a separate Todo primitive is redundant - it's over-engineering for a problem that doesn't exist when you have streaming output.

### v4 (2026-02-11)

**Changes:**
- Added "Explore Before Asking" principle (Claude Code pattern)
- TP now uses List/Search to find existing patterns before Clarify
- Infer recipient, frequency, type from existing deliverables and memories
- Clarify is last resort, not first action

**Rationale:** Claude Code doesn't ask clarifying questions about intent - it explores to find the answer. For YARNNN, this means checking existing deliverables and memories before asking "Who receives this?" or "What type?"

**Pattern:**
```
Ambiguous request → List existing entities → Search memories → Infer → Confirm
                                                            ↘ (if no patterns found) → Clarify
```

### v3 (2026-02-11)

**Changes:**
- Removed verbose plan mode/gate/assumption sections (300+ lines → 90 lines)
- Replaced all legacy tool references with primitives
- Simplified multi-step work guidance
- Added explicit `Clarify` tool examples
- Added `/create` skill

**Rationale:** Audit revealed TP prompt referenced non-existent tools (`list_deliverables`, `create_deliverable`). Streamlined to use only the 9 primitives consistently.

**Breaking:** Skills completely rewritten to use primitives

### v2 (2026-02-11)

**Changes:**
- Added "Tone and Style" section with conciseness directive
- Added explicit no-preamble/postamble rule
- Added proactiveness balance guidance
- Added concrete good/bad examples
- Streamlined Guidelines section
- Added security note (no secrets in code)

**Rationale:** Cross-analysis with Claude Code system prompt revealed opportunity for more concise, direct responses without losing helpfulness.

### v1 (2026-02-10)

**Initial version** with ADR-036/037 primitive-based architecture:
- Primitives: Read, Write, Edit, List, Search, Execute, Todo, Respond, Clarify
- Reference syntax: `type:identifier`
- Gate/approval pattern for multi-step work
- Assumption checking before major actions
- Plan mode for complex requests

---

## Design Decisions

### Why Conciseness?

Users interact via chat. Verbose responses:
- Slow down interaction
- Bury key information
- Feel less like conversation, more like documentation

Claude Code's "4 lines max unless asked for detail" is aggressive but directionally correct.

### Why No Preamble/Postamble?

Phrases like "I'll help you with that!" and "Let me know if you need anything else!" are:
- Filler that adds no value
- Slower to read
- Repetitive across interactions

The action itself communicates helpfulness.

### Why Proactiveness Balance?

Users sometimes ask "how should I..." expecting advice, not immediate action. Taking action without confirmation can feel presumptuous.

Pattern: Answer the question → Offer to act → Act on confirmation

### Why Confirm Before Creating?

Creating entities (deliverables, work) without confirmation leads to:
- Duplicates when user meant something else
- Wrong parameters from misunderstood intent
- User feeling loss of control

Simple pattern: Check duplicates → Confirm → Create (no verbose gate phases needed)

### Why Explore Before Asking? (v4)

The key insight from Claude Code: **the filesystem is explorable**. When Claude Code faces ambiguity ("Where are errors handled?"), it doesn't ask - it searches.

YARNNN's entity space is also explorable:
- Existing deliverables show patterns (recipient roles, frequency preferences)
- Memories contain facts about the user's workflow
- Platform data reveals context

**The difference:**
| Claude Code | YARNNN |
|-------------|--------|
| Grep/Glob existing code | List/Search existing entities |
| Read to understand patterns | Read memories for workflow facts |
| Infer from evidence | Infer from user history |
| Ask only when stuck | Clarify only when exploration fails |

**When YARNNN must ask (no exploration possible):**
- Brand new user with no history
- Request has no patterns to match (completely novel entity type)
- Multiple equally-valid options with no preference signal

Even then, prefer inferring defaults and confirming ("I'll set this up weekly for your team - adjust if needed") over asking ("How often? Who receives it?").

---

## Testing Prompt Changes

When modifying the TP prompt:

1. **Test simple queries** - Should get short responses, NO todos
2. **Test `/create`** - Should use `Clarify` tool with options
3. **Test ambiguous requests** - Should use `Clarify` with options
4. **Test action requests** - Should confirm before creating

Example test cases:
- "How many deliverables?" → `List` → Short answer (no todos)
- "/create" → `Clarify(options=[...])` → User picks → Create
- "Make me a report" → `Clarify` asking what type
- "yes" (after confirmation) → `Write` immediately

---

## Related Documentation

- [Primitives Architecture](./primitives.md)
- [ADR-025: Claude Code Agentic Alignment](../adr/ADR-025-claude-code-agentic-alignment.md)
- [ADR-036: Two-Layer Architecture](../adr/ADR-036-two-layer-architecture.md)
- [ADR-037: Chat-First Surface](../adr/ADR-037-chat-first-surface-architecture.md)
- [ADR-038: Filesystem-as-Context](../adr/ADR-038-filesystem-as-context.md)
