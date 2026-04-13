# Agent Types — Feature Reference

**Status:** Living document
**Date:** 2026-04-13 (updated: v5 universal specialists — ADR-176)
**Related:** [Registry Matrix](../architecture/registry-matrix.md), [ADR-176: Work-First Agent Model](../adr/ADR-176-work-first-agent-model.md), [ADR-145: Task Type Registry](../adr/ADR-145-task-type-registry.md), [ADR-164: TP as Agent](../adr/ADR-164-back-office-tasks-tp-as-agent.md)

YARNNN agents are organized into three classes: **specialists** (universal roles that
describe *how* agents contribute, not what domain they work in), **platform bots**
(own temporal context directories, platform-scoped observation), and
**meta-cognitive** (TP, owns orchestration itself per ADR-164). All agents are
pre-scaffolded at sign-up (9 total). Users enrich agent identity through use — they do
not create agents from scratch.

**Key principles (ADR-176):**
- **Universal specialists, not ICP-specific personas.** Researcher, Analyst, Writer, Tracker, Designer — names that pass the instinct test for any user in any industry.
- **Capability split:** Accumulation agents (Researcher, Analyst, Writer, Tracker) accumulate knowledge and produce markdown. Production agent (Designer) generates visual assets. These phases never overlap within a single agent.
- **No domain ownership.** Specialists are assigned to tasks; tasks read/write context domains. The same Researcher can work on competitors one task and market another. Domain expertise develops through accumulated work, not a pre-assigned label.
- **Hospital principle:** The 9-agent roster is fixed and non-configurable. These are the roles that all knowledge work requires.
- TP (meta-cognitive) owns orchestration work itself — no context domain. Back office tasks (agent hygiene, workspace cleanup) are owned by TP.
- Templates (`AGENT_TEMPLATES`) are bootstrapping — `AGENT.md` is the runtime source of truth.
- **Playbooks** (`_playbook-*.md`) define agent methodology — seeded from type registry, evolve with feedback. Loaded selectively by task output_kind. See [Agent Playbook Framework](agent-playbook-framework.md).

---

## Three Agent Classes (ADR-176)

| Class | Count | Role | Behavior |
|-------|-------|------|----------|
| **specialist** | 6 | Universal roles: Researcher, Analyst, Writer, Tracker, Designer, TP | Capability-defined, assigned to tasks by TP based on work intent |
| **platform-bot** | 3 | Own temporal context directory, platform-scoped observation (ADR-158) | Platform-specific, activated on platform connect |
| **meta-cognitive** | 1 (TP) | Own orchestration itself — attention allocation, workforce health, back office maintenance | Two runtime modes: chat (user-present, streaming) and task (scheduler-dispatched, declarative executor) |

---

## Specialists — Accumulation Phase (4)

These agents accumulate knowledge and produce markdown. They have no visual production capabilities and never call RuntimeDispatch.

### Researcher

- **Role key:** `researcher`
- **What they do:** Web search, investigate topics, find and evaluate sources, build knowledge files from primary research
- **What they never do:** Write final deliverables, generate visual assets
- **Capabilities:** web_search, investigate, read_workspace, search_knowledge, produce_markdown
- **Playbooks:** outputs, research
- **Typical tasks:** track-competitors (research step), track-market, research-topics

### Analyst

- **Role key:** `analyst`
- **What they do:** Read accumulated context, identify patterns, synthesize meaning across sources and time, produce insight summaries
- **What they never do:** Primary research, image/chart generation
- **Capabilities:** read_workspace, search_knowledge, produce_markdown
- **Playbooks:** outputs
- **Typical tasks:** competitive-brief (analysis step), market-report, stakeholder-update

### Writer

- **Role key:** `writer`
- **What they do:** Draft deliverables from synthesized context, edit for audience and tone, produce polished final output
- **What they never do:** Research, analysis, visual production
- **Capabilities:** read_workspace, produce_markdown
- **Playbooks:** outputs, formats
- **Typical tasks:** competitive-brief (writing step), content-brief, launch-material, daily-update

### Tracker

- **Role key:** `tracker`
- **What they do:** Monitor signals, maintain entity profiles, log temporal changes, watch platforms and sources for updates
- **What they never do:** Analysis, writing, production
- **Capabilities:** read_slack, read_notion, read_github, read_workspace, produce_markdown
- **Playbooks:** outputs
- **Typical tasks:** track-competitors, track-relationships, track-projects, track-market

---

## Specialist — Production Phase (1)

This agent generates visual assets. It holds all RuntimeDispatch capabilities.

### Designer

- **Role key:** `designer`
- **What they do:** Generate images, charts, diagrams, visual assets via RuntimeDispatch
- **What they never do:** Research, writing, analysis
- **Capabilities:** chart, mermaid, image, video_render, compose_html
- **Playbooks:** visual
- **Typical tasks:** Added to teams by TP when deliverables need visual assets (charts, images, diagrams)

---

## Platform Bots (3)

ADR-158: Platform bots own temporal context directories — one bot, one platform, one directory. Per-source subfolders (channel/page/repo) with `_tracker.md` for freshness. These directories are temporal awareness for TP, not canonical context for specialists. Cross-pollination into canonical domains is explicitly out of scope.

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
- **Role key:** `thinking_partner`
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

**Key principle**: TP's task outputs serve the coherence of the system itself (not any segment of the user's work). Everything else about TP — workspace folder, task ownership, agent row — is structurally identical to specialist agents.

---

## Team Composition (ADR-176 Decision 2)

TP has full authority over team composition for every task. The task type registry provides suggested defaults per work intent — inputs to TP's reasoning, not constraints on its output.

**TP's composition criteria (applied to every task):**
- Does the work require finding new information? → Researcher
- Does the work require synthesizing across multiple sources or time periods? → Analyst
- Does the work require a polished deliverable for an audience? → Writer
- Does the work require ongoing monitoring or signal capture? → Tracker
- Does the work require visual assets (charts, images, diagrams)? → Designer
- Is the scope narrow enough that a specialist is redundant? → remove them

TP writes its team reasoning in the `## Team` section of TASK.md alongside the team list. This makes the decision observable and correctable by the user.

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
