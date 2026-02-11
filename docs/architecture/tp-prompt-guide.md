# TP (Thinking Partner) Prompt Guide

> **Status**: Canonical
> **Created**: 2026-02-11
> **Updated**: 2026-02-11
> **Location**: `api/agents/thinking_partner.py`

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
| **Explore before asking** | Use List/Search to find patterns before using Clarify |
| **Infer from context** | Use existing entities and memories to fill gaps |
| **One clarifying question** | Use `Clarify` only when exploration doesn't resolve ambiguity |
| **Confirm before creating** | Ask user, then create on confirmation |
| **Stream is progress** | No Todo primitive - visible tool calls ARE the progress indicator |

### The "Grep Before Ask" Pattern

**Claude Code approach:** When facing ambiguity, Claude Code explores the codebase (Grep, Glob, Read) to find evidence before asking the user. It infers from existing patterns.

**YARNNN equivalent:** TP should explore entities and memories before asking clarifying questions.

```
User: "Create a weekly report for my team"

❌ v3 behavior (ask immediately):
→ Clarify(question="Who receives this?", options=["Manager", "Team", ...])

✅ v4 behavior (explore first):
→ List(pattern="deliverable:*")           // Check existing patterns
→ Search(query="team reports recipient")  // Check memories
→ // Found: User usually sends reports to "Product Team"
→ "I'll create a Weekly Report for the Product Team. Sound good?"
```

**When exploration doesn't help:**
- No existing deliverables to learn from
- No relevant memories
- Multiple equally-valid options exist

Then use `Clarify` - but only after exploring.

### Prompt Structure (Streamlined)

```
1. Context injection ({context})
2. Tone and Style - conciseness rules
3. How You Work - text primary, tools for actions
4. Available Tools - 8 primitives (Read, Write, Edit, List, Search, Execute, Respond, Clarify)
5. Reference Syntax - type:identifier
6. Guidelines - behavioral rules
7. Domain Terms - vocabulary
8. Explore Before Asking - List/Search before Clarify
9. Confirming Before Acting - when to confirm vs just do it
10. Creating Entities - Write examples
```

**v5 change:** Removed Todo primitive - the streaming conversation IS the progress indicator (Claude Code pattern)

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
