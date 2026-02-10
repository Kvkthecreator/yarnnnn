# TP (Thinking Partner) Prompt Guide

> **Status**: Canonical
> **Created**: 2026-02-11
> **Location**: `api/agents/thinking_partner.py`

---

## Overview

The Thinking Partner system prompt governs how TP interacts with users. This document tracks prompt design decisions and their rationale.

---

## Current Version: v2 (2026-02-11)

### Key Principles

| Principle | Implementation |
|-----------|----------------|
| **Conciseness** | Short answers for simple questions; thorough for complex |
| **No preamble/postamble** | Skip "I'll help you with..." and "Let me know if..." |
| **Proactiveness balance** | Answer questions before taking action |
| **One clarifying question** | Don't over-ask; gather what's needed, then act |
| **Gates before execution** | `[GATE]` phase requires user confirmation |

### Prompt Structure

```
1. Context injection ({context})
2. Tone and Style - conciseness rules
3. How You Work - text primary, tools for actions
4. Available Tools - primitives reference
5. Reference Syntax - entity addressing
6. Guidelines - behavioral rules
7. Domain Terms - vocabulary
8. Task Progress - todo/gate patterns (ADR-025)
9. Plan Mode - when to plan vs act
10. Assumption Checking - verify before major actions
11. Deliverable Creation - parse → confirm → create flow
12. Memory Routing - ADR-034 domain scoping
```

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

### v2 (2026-02-11)

**Changes:**
- Added "Tone and Style" section with conciseness directive
- Added explicit no-preamble/postamble rule
- Added proactiveness balance guidance
- Added concrete good/bad examples
- Streamlined Guidelines section
- Added security note (no secrets in code)

**Rationale:** Cross-analysis with Claude Code system prompt revealed opportunity for more concise, direct responses without losing helpfulness.

**Source:** Claude Code prompt patterns (conciseness, no preamble, proactiveness balance)

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

### Why Gates?

Creating entities (deliverables, work) without confirmation leads to:
- Duplicates when user meant something else
- Wrong parameters from misunderstood intent
- User feeling loss of control

The `[GATE]` pattern ensures user approval before any `[EXEC]` phase.

---

## Testing Prompt Changes

When modifying the TP prompt:

1. **Test simple queries** - Should get short responses
2. **Test complex requests** - Should see todo/gate pattern
3. **Test ambiguous requests** - Should ask ONE clarifying question
4. **Test action requests** - Should confirm before creating

Example test cases:
- "How many deliverables?" → Short answer
- "Set up monthly board updates" → Plan with gate
- "Make me a report" → One clarifying question
- "yes" (after confirmation) → Immediate action

---

## Related Documentation

- [Primitives Architecture](./primitives.md)
- [ADR-025: Claude Code Agentic Alignment](../adr/ADR-025-claude-code-agentic-alignment.md)
- [ADR-036: Two-Layer Architecture](../adr/ADR-036-two-layer-architecture.md)
- [ADR-037: Chat-First Surface](../adr/ADR-037-chat-first-surface-architecture.md)
