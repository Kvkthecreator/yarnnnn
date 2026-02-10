# TP (Thinking Partner) Prompt Guide

> **Status**: Canonical
> **Created**: 2026-02-11
> **Updated**: 2026-02-11
> **Location**: `api/agents/thinking_partner.py`

---

## Overview

The Thinking Partner system prompt governs how TP interacts with users. This document tracks prompt design decisions and their rationale.

---

## Current Version: v3 (2026-02-11)

### Key Principles

| Principle | Implementation |
|-----------|----------------|
| **Conciseness** | Short answers for simple questions; thorough for complex |
| **No preamble/postamble** | Skip "I'll help you with..." and "Let me know if..." |
| **Proactiveness balance** | Answer questions before taking action |
| **One clarifying question** | Use `Clarify` tool with 2-4 options |
| **Confirm before creating** | Ask user, then create on confirmation |
| **Primitives only** | All tools are primitives (no legacy tool names) |

### Prompt Structure (Streamlined)

```
1. Context injection ({context})
2. Tone and Style - conciseness rules
3. How You Work - text primary, tools for actions
4. Available Tools - 9 primitives
5. Reference Syntax - type:identifier
6. Guidelines - behavioral rules
7. Domain Terms - vocabulary
8. Multi-Step Work - when to use Todo (simplified)
9. Asking for Clarification - Clarify tool usage
10. Creating Entities - Write examples
11. Checking Before Acting - List for duplicates
```

**Removed in v3:** Verbose plan mode, gate phases, assumption checking sections (300+ lines → 90 lines)

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
