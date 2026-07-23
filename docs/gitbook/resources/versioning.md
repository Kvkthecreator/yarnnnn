# Documentation Layers

## Where things live

YARNNN keeps documentation in separate layers on purpose:

| Layer | What it is |
|---|---|
| `docs/gitbook/` | These public product docs |
| `docs/ESSENCE.md` | The canonical product narrative |
| `docs/architecture/` | Canonical internal architecture — FOUNDATIONS, GLOSSARY, service model |
| `docs/adr/` | Decision records; the implementation history |
| `docs/analysis/` | Exploratory work and open questions |

Public docs may simplify. They should never contradict the canonical layer. Where these pages describe something as not-yet-running, that reflects the shipped state rather than the intended one — the goal is that a reader is never surprised.

<!-- GITBOOK_VERSIONING_START -->
## Current snapshot

| Field | Value |
|---|---|
| Last reviewed (UTC) | `2026-07-23` |
| Docs version | `v7.0.0-docs.20260723` |
| Source commit | `4f18b2a` |
| Basis | Full rewrite against ESSENCE v16 (ADR-457 Think · Make), ADR-414, ADR-445 |
<!-- GITBOOK_VERSIONING_END -->

## What the 7.0 rewrite changed

The docs had drifted roughly four months behind the product. Everything describing the previous service model was replaced:

- **Thinking Partner** — retired as a concept; the roster is now named colleagues, and orchestration isn't personified
- **Tasks, agents-as-workforce, multi-agent pipelines** — the task abstraction was dissolved; work happens in Chat and Studio
- **Slack/Notion-first onboarding** — no longer the entry path; the workspace is useful from signup with nothing connected
- **Platform bots, projects, meeting rooms, rendered PDF/PPTX/XLSX deliverables** — all removed from the product
- **Plans** — replaced with the current two-axis model (seats + a pooled meter)
- **MCP tools** — `work_on_this`/`pull_context`/`remember_this` are gone; the surface is `remember`/`recall`/`trace`
- **MCP URL** — now `https://mcp.yarnnn.com`

New pages cover the five apps, the record, Freddie, and team use.

## Auto-sync

A helper script refreshes the changelog and this snapshot from git history:

```bash
python3 scripts/sync_gitbook.py
```

It updates the auto-generated sections only. The narrative pages are maintained by hand against the canonical docs.
