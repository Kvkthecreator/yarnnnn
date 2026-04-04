# Agent Types — Feature Reference

**Status:** Living document
**Date:** 2026-03-31 (updated: v4 domain-steward model)
**Related:** [Registry Matrix](../architecture/registry-matrix.md), [ADR-140: Agent Workforce](../adr/ADR-140-agent-workforce-model.md), [ADR-145: Task Type Registry](../adr/ADR-145-task-type-registry.md)

YARNNN agents are organized into three classes: **domain stewards** (own a
context domain), **synthesizers** (read across all domains), and
**platform bots** (own temporal context directories, platform-scoped observation). All agents
are pre-scaffolded at sign-up. Users enrich agent identity through use — they do
not create agents from scratch.

**Key principle:** Each domain-steward agent owns one context domain. The synthesizer (Executive) reads all domains. Templates (`AGENT_TEMPLATES`) are bootstrapping — `AGENT.md` is the runtime source of truth.

---

## Three Agent Classes

| Class | Count | Role | Behavior |
|-------|-------|------|----------|
| **domain-steward** | 5 | Own one context domain, maintain knowledge, produce domain-scoped deliverables | Domain-cognitive, multi-step reasoning, web research |
| **synthesizer** | 1 | Read across all domains, produce cross-domain deliverables | Cross-domain composition, reads everything, writes nothing to context |
| **platform-bot** | 3 | Own temporal context directory, platform-scoped observation (ADR-158) | Platform-specific, activated on platform connect |

---

## Domain Stewards (5)

### Competitive Intelligence

- **Domain owned:** `competitors/`
- **Capabilities:** web_search, investigate, chart
- **What it maintains:** Competitor entity files, competitive landscape analysis, market positioning data in `/workspace/context/competitors/`
- **What it produces:** Competitive briefs, market reports, GTM intelligence
- **Typical tasks:** track-competitors, competitive-brief

### Market Research

- **Domain owned:** `market/`
- **Capabilities:** web_search, investigate, chart
- **What it maintains:** Market trends, industry analysis, sector data in `/workspace/context/market/`
- **What it produces:** Market reports, launch materials, GTM reports
- **Typical tasks:** track-market, market-report

### Business Development

- **Domain owned:** `relationships/`
- **Capabilities:** read_slack, read_notion, read_github, investigate
- **What it maintains:** Stakeholder profiles, relationship context, meeting history in `/workspace/context/relationships/`
- **What it produces:** Meeting prep briefs, stakeholder updates
- **Typical tasks:** track-relationships, meeting-prep, stakeholder-update

### Operations

- **Domain owned:** `projects/`
- **Capabilities:** read_slack, read_notion, read_github, chart
- **What it maintains:** Project status, internal initiative tracking, team activity in `/workspace/context/projects/`
- **What it produces:** Project status reports, stakeholder updates
- **Typical tasks:** track-projects, project-status

### Marketing & Creative

- **Domain owned:** `content/`
- **Capabilities:** web_search, chart, image, video_render, compose_html
- **What it maintains:** Content research, topic analysis, creative assets in `/workspace/context/content/`
- **What it produces:** Content briefs, launch materials, creative outputs
- **Typical tasks:** research-topics, content-brief, launch-material

---

## Synthesizer (1)

### Executive Reporting

- **Domain owned:** (cross-domain) — reads all context domains, owns none
- **Capabilities:** compose_html, chart
- **What it maintains:** Nothing — synthesizer reads, does not accumulate context
- **What it produces:** Cross-domain executive summaries, stakeholder updates, composed HTML reports that draw from all agent domains
- **Typical tasks:** stakeholder-update, market-report (cross-domain variants)

---

## Platform Bots (3)

ADR-158: Platform bots own temporal context directories — one bot, one platform, one directory. Per-source subfolders (channel/page/repo) with `_tracker.md` for freshness. These directories are temporal awareness for TP, not canonical context for domain stewards. Cross-pollination into canonical domains is explicitly out of scope.

### Slack Bot

- **Domain owned:** `slack/` (temporal — `/workspace/context/slack/`)
- **Capabilities:** read_slack, write_slack
- **What it maintains:** Per-channel observation files in `/workspace/context/slack/{channel}/latest.md`
- **What it produces:** Slack activity digests with decisions, action items, key discussions
- **Typical tasks:** slack-digest
- **Activation:** Activated when Slack platform connected

### Notion Bot

- **Domain owned:** `notion/` (temporal — `/workspace/context/notion/`)
- **Capabilities:** read_notion, write_notion
- **What it maintains:** Per-page observation files in `/workspace/context/notion/{page}/latest.md`
- **What it produces:** Notion change digests with content updates, staleness flags
- **Typical tasks:** notion-digest
- **Activation:** Activated when Notion platform connected

### GitHub Bot

- **Domain owned:** `github/` (temporal — `/workspace/context/github/`)
- **Capabilities:** read_github
- **What it maintains:** Per-repo observation files in `/workspace/context/github/{repo}/latest.md`
- **What it produces:** GitHub activity digests with issues, PRs, and repo activity
- **Typical tasks:** github-digest
- **Activation:** Activated when GitHub platform connected

---

## Agent Reflections (ADR-128, ADR-149)

All agents now produce **reflections** as part of their output. During headless execution, agents append a `## Agent Reflection` block to their generated content. This block is extracted, appended to `memory/reflections.md` (rolling 5 recent entries), and stripped before delivery. The user never sees it; the agent and TP do.

Reflections capture the agent's self-awareness after each run: mandate fitness, context currency, output confidence, and observations about what could improve next cycle.

---

## Key Files (shared across all skills)

| Concern | Location |
|---------|----------|
| Skill prompts | `api/services/agent_pipeline.py` (TYPE_PROMPTS → SKILL_PROMPTS) |
| Default instructions | `api/services/agent_pipeline.py` (DEFAULT_INSTRUCTIONS) |
| Execution strategies | `api/services/execution_strategies.py` |
| Primitive registry | `api/services/primitives/registry.py` |
| Platform tools | `api/services/platform_tools.py` |
| Generation pipeline | `api/services/agent_execution.py` |
| Framework reference | [docs/architecture/agent-framework.md](../architecture/agent-framework.md) |
| Targeting architecture | [ADR-104](../adr/ADR-104-agent-instructions-unified-targeting.md) |
| Quality testing | `docs/development/agent-quality-testing.md` |
