# ADR-140: Agent Workforce Model — Pre-Scaffolded Roster

> **Status**: Proposed
> **Date**: 2026-03-25
> **Authors**: KVK, Claude
> **Evolves**: ADR-130 (Type Registry → workforce roster), ADR-138 (Agent/Task separation)
> **Requires update**: FOUNDATIONS.md (Axiom 3), ESSENCE.md (System Shape), CLAUDE.md (Agent Types), agent-framework.md

---

## Context

ADR-138 established the three-entity model: **Agents** (WHO) → **Tasks** (WHAT) → **Workfloor** (WHERE). But the agent type registry still reflects the old task-derived model — archetypes like "monitor", "researcher", "producer" describe what an agent does (task behavior), not what an agent IS (identity and capabilities).

This creates confusion: when a user says "I need a competitor watch," should the system create a "monitor" agent? A "researcher"? The archetype names blur identity, capabilities, and tasks into one axis.

### The three-axis separation

An agent has three independent properties:

1. **Identity** (AGENT.md) — name, domain description, accumulated expertise. Evolves with use. User-configurable.
2. **Capabilities** (type registry) — tool access. Fixed at creation. Deterministic. "What this agent CAN do."
3. **Tasks** (TASK.md) — work assignments. Come and go. Multiple per agent. "What this agent IS DOING."

The old system collapsed all three into "agent type." ADR-138 separated axis 3 (tasks). This ADR separates axis 1 (identity) from axis 2 (capabilities) by defining agent types as **capability bundles with user-facing names** — not as task descriptions or domain labels.

### The workforce metaphor

A solo founder doesn't hire "a monitor" or "a producer." They hire:
- A **Research Agent** who can investigate anything
- A **Content Agent** who can produce any deliverable
- A **Slack Bot** that handles their Slack

The agent type determines capabilities. The task determines what work gets done. The agent's identity (name, expertise) develops over time through accumulated memory and feedback.

---

## Decision

### 1. Pre-scaffolded workforce at sign-up

Every new workspace gets a standing agent roster created automatically. The user sees their "team" immediately — no empty state, no inference needed.

### 2. Agent types are capability bundles

| Type key | Display name | Class | Capabilities | Hire for |
|---|---|---|---|---|
| `research` | Research Agent | agent | web_search, read_workspace, read_platforms, chart | Investigation, analysis, competitive intel, market research |
| `content` | Content Agent | agent | read_workspace, compose_html, runtime_dispatch, chart | Reports, presentations, blog posts, investor updates |
| `marketing` | Marketing Agent | agent | web_search, read_workspace, read_platforms, compose_html | GTM tracking, social content, campaign analysis, positioning |
| `crm` | CRM Agent | agent | read_platforms, read_workspace, compose_html | Client updates, relationship tracking, meeting prep, follow-ups |
| `slack_bot` | Slack Bot | bot | read_platforms(slack), write_slack | Recaps, channel summaries, post messages, alerts |
| `notion_bot` | Notion Bot | bot | read_platforms(notion), write_notion | Knowledge base updates, page syncs, meeting notes |

### 3. Agent vs Bot distinction

**Agents** (domain-cognitive):
- Reason about their domain across multiple steps
- Accumulate deep expertise through memory
- Can use multiple tools per task execution
- Handle complex multi-step work (research → analyze → produce)
- Identity develops with tenure

**Bots** (platform-mechanical):
- Scoped to one platform's API
- Read and write to that platform
- Less reasoning, more execution
- Closer to an integration than an intelligence
- Platform writes require explicit user authorization (default: read-only)

Both are stored in the `agents` table. The `class` field in the type registry distinguishes them. Bots use the same workspace infrastructure (AGENT.md, memory/) but their execution is simpler.

### 4. Sign-up creates the roster

On workspace creation (triggered by first auth):

```python
DEFAULT_ROSTER = [
    {"title": "Research Agent", "role": "research"},
    {"title": "Content Agent", "role": "content"},
    {"title": "Marketing Agent", "role": "marketing"},
    {"title": "CRM Agent", "role": "crm"},
    {"title": "Slack Bot", "role": "slack_bot"},
    {"title": "Notion Bot", "role": "notion_bot"},
]
```

Each agent gets:
- AGENT.md with default identity (display name, default expertise description)
- memory/ folder (empty, seeds on first run)
- Status: `active` (agents), `paused` (bots — activated when platform connected)

Bots start paused until the user connects the relevant platform. When Slack is connected, Slack Bot activates. When Notion is connected, Notion Bot activates.

### 5. Onboarding becomes context enrichment

Onboarding no longer creates agents. It:
1. Collects user identity (name, role)
2. Collects brand context (company, tone)
3. Accepts uploaded documents → enriches `/knowledge/`
4. Accepts work description → TP auto-suggests tasks
5. Connects platforms → activates relevant bots

Task creation is downstream — via TP chat ("I need weekly competitor intel" → TP creates task, assigns to Research Agent) or via workfloor UI.

### 6. Task assignment logic

When a task is created (via TP or UI), the system or TP selects the right agent based on:
- Task objective matches agent capabilities
- Research tasks → Research Agent
- Content production → Content Agent
- Platform monitoring → relevant Bot
- GTM/positioning → Marketing Agent
- Relationship/pipeline → CRM Agent

TP uses `DiscoverAgents` to see the roster and `CreateTask` to assign work.

### 7. Users can customize

- **Rename agents**: "Research Agent" → "Competitive Intelligence" (identity evolves)
- **Adjust expertise**: update AGENT.md with domain-specific instructions
- **Create additional agents**: "Add another Research Agent for financial analysis"
- **Archive unused agents**: hide CRM Agent if not needed
- **Cannot change capabilities**: type is fixed at creation (ADR-130 Derived Principle 5)

---

## Type registry (code)

```python
AGENT_TYPES = {
    "research": {
        "class": "agent",
        "display_name": "Research Agent",
        "tagline": "Investigates and analyzes",
        "description": "Deep investigation across web and workspace. Produces structured analysis with evidence.",
        "capabilities": ["web_search", "read_workspace", "read_platforms", "chart", "compose_html"],
        "default_instructions": "Investigate assigned topics with depth. Use web search and workspace context. Produce structured analysis with evidence. Prioritize insights the user hasn't seen elsewhere.",
    },
    "content": {
        "class": "agent",
        "display_name": "Content Agent",
        "tagline": "Creates deliverables",
        "description": "Produces polished deliverables from workspace context. Reports, presentations, documents.",
        "capabilities": ["read_workspace", "compose_html", "runtime_dispatch", "chart"],
        "default_instructions": "Produce polished deliverables for the target audience. Use charts and visuals where they add clarity. Structure for readability. Focus on quality and completeness.",
    },
    "marketing": {
        "class": "agent",
        "display_name": "Marketing Agent",
        "tagline": "Handles go-to-market",
        "description": "GTM tracking, content distribution, competitive positioning, campaign analysis.",
        "capabilities": ["web_search", "read_workspace", "read_platforms", "compose_html"],
        "default_instructions": "Track go-to-market activities and competitive positioning. Monitor market signals. Produce actionable GTM insights and content.",
    },
    "crm": {
        "class": "agent",
        "display_name": "CRM Agent",
        "tagline": "Manages relationships",
        "description": "Client tracking, relationship management, follow-ups, meeting preparation.",
        "capabilities": ["read_platforms", "read_workspace", "compose_html"],
        "default_instructions": "Track client relationships and interactions. Prepare meeting briefs. Flag follow-ups and action items. Summarize relationship health.",
    },
    "slack_bot": {
        "class": "bot",
        "display_name": "Slack Bot",
        "tagline": "Reads and writes Slack",
        "description": "Platform bot for Slack. Recaps, summaries, alerts, and message posting.",
        "capabilities": ["read_platforms", "write_slack", "summarize"],
        "platform": "slack",
        "default_instructions": "Monitor Slack channels. Summarize key discussions. Post updates when directed. Flag action items and decisions.",
    },
    "notion_bot": {
        "class": "bot",
        "display_name": "Notion Bot",
        "tagline": "Reads and writes Notion",
        "description": "Platform bot for Notion. Knowledge base management, page syncing, content updates.",
        "capabilities": ["read_platforms", "write_notion", "summarize"],
        "platform": "notion",
        "default_instructions": "Manage Notion workspace. Sync meeting notes. Update knowledge base pages. Track document changes.",
    },
}
```

---

## What changes

### Database
- `agents.role` CHECK constraint: update to include `research`, `content`, `marketing`, `crm`, `slack_bot`, `notion_bot` (keep legacy values for migration mapping)
- No new tables needed

### Backend
- `agent_framework.py`: replace AGENT_TYPES with new roster-based registry
- `agent_creation.py`: update to use new type keys + default_instructions from registry
- Sign-up hook: create 6 agents per new workspace (in `handle_new_user()` or equivalent)
- `onboarding_bootstrap.py`: rewrite — context enrichment only, no agent creation
- `routes/memory.py` onboarding endpoint: remove agent creation, keep context collection
- `project_inference.py` → rename to `task_inference.py`: infer tasks only (not agents), suggest agent assignment

### Frontend
- Agent page: shows full roster as team gallery (identity, capabilities, task count)
- Agent cards: display name from registry, archetype icon, assigned task count
- Bot agents: show platform connection status (connected/disconnected)
- Onboarding: remove agent creation step, focus on context + platform connection

### Prompts
- TP prompt: knows the roster exists, uses DiscoverAgents to see team
- CreateTask: TP selects agent from existing roster, doesn't create new agents for tasks
- CHANGELOG.md entry for all prompt changes

---

## Migration from current state

Since we're clean-slate (ADR-138), no data migration needed. Just:
1. Update AGENT_TYPES registry
2. Update role CHECK constraint (migration 131)
3. Implement sign-up roster creation
4. Update onboarding endpoint

---

## What stays unchanged

- Task model (ADR-138) — tasks are WHAT, assigned to agents
- Workspace filesystem — /agents/{slug}/ with AGENT.md, memory/
- Agent pulse system — Tier 1 + Tier 2
- Feedback distillation — edits → preferences.md
- Self-assessment — per-agent cognitive files
- Compose engine — per-task output rendering
- Delivery — per-task delivery config

---

## Future considerations

### Additional agent types
As the platform matures, new capability bundles can be added:
- **Finance Agent** — read_platforms, spreadsheet, chart (financial analysis)
- **HR Agent** — read_platforms, compose_html (people ops)
- **Engineering Agent** — read_platforms(github), compose_html (dev updates)

### User-created custom agents
Power users may want agents with custom capability bundles. This is a v2 feature — for now, the 6-type roster covers the solo founder use case.

### Multi-instance agents
A user might want two Research Agents — one for competitive intel, one for market trends. Support this by allowing multiple agents of the same type, differentiated by identity (AGENT.md name and expertise).
