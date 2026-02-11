# TP (Thinking Partner) Prompt Guide

> **Status**: Canonical
> **Created**: 2026-02-11
> **Updated**: 2026-02-11
> **Location**: `api/agents/thinking_partner.py`
> **Primitives**: 7 (ADR-038)
> **Related**: [ADR-038: Filesystem-as-Context](../adr/ADR-038-filesystem-as-context.md)

---

## Overview

The Thinking Partner system prompt governs how TP interacts with users. This document tracks prompt design decisions and their rationale.

---

## Current Version: v5.1 (2026-02-11)

### Key Principles

| Principle | Implementation |
|-----------|----------------|
| **Conciseness** | Short answers for simple questions; thorough for complex |
| **No preamble/postamble** | Skip "I'll help you with..." and "Let me know if..." |
| **Context-first** | Check `{context}` injection before exploring or asking |
| **Explore before asking** | Use List/Search to find patterns before using Clarify |
| **One clarifying question** | Use `Clarify` only when context + exploration don't resolve ambiguity |
| **Confirm before creating** | Ask user, then create on confirmation |
| **7 primitives** | Read, Write, Edit, List, Search, Execute, Clarify (no Respond, no Todo) |

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

### Prompt Structure (7 Primitives)

```
1. Context injection ({context}) - user profile, deliverables, platforms, sessions
2. Tone and Style - conciseness rules
3. How You Work - text primary, tools for actions
4. Available Tools - 7 primitives (Read, Write, Edit, List, Search, Execute, Clarify)
5. Reference Syntax - type:identifier
6. Guidelines - behavioral rules
7. Domain Terms - vocabulary
8. Explore Before Asking - context → List/Search → Clarify (last resort)
9. Confirming Before Acting - when to confirm vs just do it
10. Creating Entities - Write examples
```

**v5.1 changes:**
- Removed Respond primitive (TP's text output IS the response)
- Removed Todo primitive (streaming tool calls ARE the progress indicator)
- Added context injection as primary information source

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
