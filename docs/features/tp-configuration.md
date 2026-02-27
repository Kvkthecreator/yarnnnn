# Thinking Partner (TP) Configuration

> **Status**: Archived (2026-02-27)
> **Superseded by**: [TP Prompt Guide](../architecture/tp-prompt-guide.md) (canonical, current through v6.1)
> **Previous version**: [../architecture/previous_versions/tp-configuration.md](../architecture/previous_versions/tp-configuration.md)

---

## Why this was archived

This document tracked TP configuration changes from January–February 2025 (v1–v2). It references:
- Removed tools (`list_deliverables`, `create_deliverable`)
- Removed workflow phases (`[PLAN]`, `[GATE]`, `[EXEC]`, `[VALIDATE]`)
- Outdated session limits (30 messages vs current 50,000 token budget)
- The `skills.py` system which has been simplified

The [TP Prompt Guide](../architecture/tp-prompt-guide.md) is the canonical reference for all prompt design decisions from v1 through v6.1.

## Current references

- [TP Prompt Guide](../architecture/tp-prompt-guide.md) — prompt versioning, design decisions, changelog
- [Primitives Architecture](../architecture/primitives.md) — the 9 primitives TP uses
- [Agent Execution Model](../architecture/agent-execution-model.md) — chat vs headless modes (ADR-080)
- [Sessions](./sessions.md) — session lifecycle and cross-session continuity
