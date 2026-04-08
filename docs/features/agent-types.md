# Agent Types — Feature Reference

**Status:** Living document
**Date:** 2026-04-08 (updated: v4 domain-steward model + ADR-164 meta-cognitive)
**Related:** [Registry Matrix](../architecture/registry-matrix.md), [ADR-140: Agent Workforce](../adr/ADR-140-agent-workforce-model.md), [ADR-145: Task Type Registry](../adr/ADR-145-task-type-registry.md), [ADR-164: TP as Agent](../adr/ADR-164-back-office-tasks-tp-as-agent.md)

YARNNN agents are organized into four classes: **domain stewards** (own a
context domain), **synthesizers** (read across all domains),
**platform bots** (own temporal context directories, platform-scoped observation), and
**meta-cognitive** (TP, owns orchestration itself per ADR-164). All agents
are pre-scaffolded at sign-up (10 total). Users enrich agent identity through use — they do
not create agents from scratch.

**Key principles:**
- Each domain-steward agent owns one context domain. The synthesizer reads all.
- TP (meta-cognitive) owns orchestration work itself — no context domain. Back office tasks (agent hygiene, workspace cleanup) are owned by TP.
- Templates (`AGENT_TEMPLATES`) are bootstrapping — `AGENT.md` is the runtime source of truth.
- **Playbooks** (`_playbook-*.md`) define agent methodology — seeded from type registry, evolve with feedback. Loaded selectively by task class. See [Agent Playbook Framework](agent-playbook-framework.md).
- **Visual production** (image/video) is Marketing's specialization. Other agents use charts/mermaid for data visualization only.

---

## Four Agent Classes (ADR-140 + ADR-164)

| Class | Count | Role | Behavior |
|-------|-------|------|----------|
| **domain-steward** | 5 | Own one context domain, maintain knowledge, produce domain-scoped deliverables | Domain-cognitive, multi-step reasoning, web research |
| **synthesizer** | 1 | Read across all domains, produce cross-domain deliverables | Cross-domain composition, reads everything, writes nothing to context |
| **platform-bot** | 3 | Own temporal context directory, platform-scoped observation (ADR-158) | Platform-specific, activated on platform connect |
| **meta-cognitive** (ADR-164) | 1 | Own orchestration itself — attention allocation, workforce health, back office maintenance | Two runtime modes: chat (user-present, streaming) and task (scheduler-dispatched, declarative executor) |

---

## Domain Stewards (5)

### Competitive Intelligence

- **Domain owned:** `competitors/`
- **Capabilities:** web_search, investigate, chart, mermaid
- **Playbooks:** outputs, research
- **What it maintains:** Competitor entity files, competitive landscape analysis, market positioning data in `/workspace/context/competitors/`
- **What it produces:** Competitive briefs, market reports, GTM intelligence
- **Typical tasks:** track-competitors, competitive-brief

### Market Research

- **Domain owned:** `market/`
- **Capabilities:** web_search, investigate, chart, mermaid
- **Playbooks:** outputs, research
- **What it maintains:** Market trends, industry analysis, sector data in `/workspace/context/market/`
- **What it produces:** Market reports, launch materials, GTM reports
- **Typical tasks:** track-market, market-report

### Business Development

- **Domain owned:** `relationships/`
- **Capabilities:** read_slack, read_notion, read_github, investigate
- **Playbooks:** outputs
- **What it maintains:** Stakeholder profiles, relationship context, meeting history in `/workspace/context/relationships/`
- **What it produces:** Meeting prep briefs, stakeholder updates
- **Typical tasks:** track-relationships, meeting-prep, stakeholder-update

### Operations

- **Domain owned:** `projects/`
- **Capabilities:** read_slack, read_notion, read_github, chart
- **Playbooks:** outputs
- **What it maintains:** Project status, internal initiative tracking, team activity in `/workspace/context/projects/`
- **What it produces:** Project status reports, stakeholder updates
- **Typical tasks:** track-projects, project-status

### Marketing & Creative

- **Domain owned:** `content/`
- **Capabilities:** web_search, chart, mermaid, **image, video** (visual production specialist)
- **Playbooks:** outputs, formats, **visual**
- **What it maintains:** Content research, topic analysis, creative assets in `/workspace/context/content/`
- **What it produces:** Content briefs, launch materials, creative outputs
- **Typical tasks:** research-topics, content-brief, launch-material

---

## Synthesizer (1)

### Reporting

- **Domain owned:** (cross-domain) — reads all context domains, owns none
- **Capabilities:** compose_html, chart, mermaid
- **Playbooks:** outputs, formats
- **What it maintains:** Nothing — synthesizer reads, does not accumulate context
- **What it produces:** Daily operational updates, cross-domain executive summaries, stakeholder reports
- **Typical tasks:** daily-update (daily, operational), stakeholder-update (monthly, strategic)

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
- **Capabilities:** read_github (issues, PRs, README, releases, metadata)
- **What it maintains:** Per-repo files: `latest.md` (activity), `readme.md` (project summary), `releases.md` (what shipped), `metadata.md` (repo identity). Works for own repos AND external public repos.
- **What it produces:** GitHub activity + reference digests
- **Typical tasks:** github-digest
- **Activation:** Activated when GitHub platform connected
- **Unique:** Can track any public repo (competitors, ecosystem) — not limited to user's own repos

---

## Meta-Cognitive (1) — ADR-164

### Thinking Partner

- **Class:** `meta-cognitive`
- **Slug:** `thinking-partner`
- **Workspace folder:** `/agents/thinking-partner/AGENT.md`
- **Domain owned:** None — TP does not own a context domain. Its domain is orchestration itself: attention allocation, workforce health, back office maintenance.
- **Capabilities:** read_workspace, write_workspace, search_knowledge, produce_markdown
- **What it maintains:** Workspace-level coherence. The health of the rest of the workforce. The scheduling rhythm of back office maintenance.
- **What it produces:** Orchestration signals (agent hygiene reports, workspace cleanup reports, future task freshness reports). Never produces domain content.
- **Typical tasks (back office):** `back-office-agent-hygiene` (daily), `back-office-workspace-cleanup` (daily). Future: `back-office-task-freshness`.

**Two runtime modes (same identity):**

1. **Chat runtime** — invoked from `routes/chat.py` via `ThinkingPartnerAgent` class. Full conversation, streaming, all chat primitives (CHAT_PRIMITIVES). This is where TP makes judgment calls with the user present.
2. **Task runtime** — invoked from `task_pipeline.execute_task()` when the scheduler dispatches a back office task owned by TP. Control handed off to `_execute_tp_task()`, which reads the TASK.md ## Process section's `executor: <dotted.path>` directive, imports the module, calls its `run(client, user_id, task_slug)` async function, and writes the returned output to the standard task outputs folder. No LLM generation — deterministic executors.

**Key principle**: TP's task outputs serve the coherence of the system itself (not any segment of the user's work). Everything else about TP — workspace folder, task ownership, agent row — is structurally identical to domain agents.

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
| Task execution pipeline | `api/services/task_pipeline.py` (ADR-141) |
| Primitive registry | `api/services/primitives/registry.py` |
| Platform tools | `api/services/platform_tools.py` |
| Back office executors (TP task runtime) | `api/services/back_office/` (ADR-164) |
| Agent execution (legacy helpers) | `api/services/agent_execution.py` |
| Framework reference | [docs/architecture/agent-framework.md](../architecture/agent-framework.md) |
| Targeting architecture | [ADR-104](../adr/ADR-104-agent-instructions-unified-targeting.md) |
| Quality testing | `docs/development/agent-quality-testing.md` |
