"""
Tool Documentation - Core YARNNN primitives.

Includes:
- Data Operations (Read, Write, Edit, List, Search)
- External Operations (Execute)
- Web Operations (WebSearch)
- Reference Syntax
"""

TOOLS_SECTION = """---

## Available Tools

### Data Operations

**Read(ref)** - Retrieve entity by reference
- `Read(ref="agent:uuid-123")` - specific agent
- `Read(ref="platform:slack")` - platform by provider

**Write(ref, content)** - Create new memory or document
- `Write(ref="memory:new", content={content: "User prefers bullet points", tags: ["preference"]})`
- `Write(ref="document:new", content={name: "Q2 Report", url: "..."})`
- For agents, use CreateAgent instead

**Edit(ref, changes)** - Modify existing entity
- `Edit(ref="agent:uuid", changes={status: "paused"})`

**List(pattern)** - Find entities by pattern
- `List(pattern="agent:*")` - all agents
- `List(pattern="agent:?status=active")` - filtered
- `List(pattern="platform:*")` - connected platforms
- `List(pattern="memory:*")` - all memories (read-only)

**Search(query, scope?)** - Search synced platform content, documents, agents
- `Search(query="Q2 budget", scope="platform_content", platform="slack")` - search Slack content
- `Search(query="roadmap", scope="document")` - search uploaded documents
- `Search(query="weekly report", scope="all")` - search everything

### Platform Refresh

**RefreshPlatformContent(platform)** - Sync latest platform data into cache
- `RefreshPlatformContent(platform="slack")` - refresh Slack content
- `RefreshPlatformContent(platform="notion")` - refresh Notion content
- Use when Search returns stale/empty results. Then re-query with Search.

### External Operations

**Execute(action, target, params?)** - Trigger YARNNN orchestration operations
- `Execute(action="agent.generate", target="agent:uuid")` - generate content
- `Execute(action="agent.acknowledge", target="agent:uuid", params={note: "..."})` - lightweight observation
- `Execute(action="platform.publish", target="agent:uuid", via="platform:slack")` - publish agent

### Web Operations

**WebSearch(query, context?, max_results?)** - Search the web for external information
- `WebSearch(query="latest React 19 features")` - current technical info
- `WebSearch(query="Acme Corp funding", context="competitor research")` - with context
- `WebSearch(query="kubernetes best practices 2026", max_results=3)` - limit results

**When to use WebSearch vs Search:**
- **WebSearch**: External/internet info (news, docs, research, competitors)
- **Search**: User's own data (Slack messages, Gmail, uploaded documents, memories)

WebSearch is ideal for:
- Current events or news
- Latest documentation or release notes
- Competitor/market research
- Technical information not in user's synced data

---

## Reference Syntax

Format: `<type>:<identifier>`

**Types:** agent, version, platform, document, action

**Special:** `new` (create), `latest` (most recent), `*` (all), `?key=val` (filter)

---

## Domain Terms (ADR-138)

- **agent** = persistent domain expert (WHO — identity, expertise, memory)
- **task** = defined work unit (WHAT — objective, cadence, delivery, output spec)
- **run** = a single execution of a task (output produced by an agent)
- **memory** = context/knowledge about user (read-only; updated implicitly)
- **platform** = connected integration (Slack, Notion)
- **workspace** = shared filesystem (knowledge, identity, agent workspaces, task outputs)

---

## Creating Agents (ADR-138)

**CreateAgent(title, role)** — Create a persistent domain expert.
Agents are WHO — they have identity, domain expertise, and accumulated memory.
They don't have schedules or delivery targets. Those belong to tasks.

```
CreateAgent(
  title: "Market Intelligence",
  role: "researcher",
  agent_instructions: "Expert in AI agent platform competitive landscape"
)
```

**Archetypes:** monitor, researcher, producer, operator
**Optional:** agent_instructions (domain expertise description)

Always confirm the agent identity with the user before calling CreateAgent.

---

## Creating Tasks (ADR-138)

**CreateTask(title, agent_slug)** — Create a work unit assigned to an agent.
Tasks are WHAT — they define objective, cadence, delivery, and success criteria.

```
CreateTask(
  title: "Weekly Competitive Briefing",
  agent_slug: "market-intelligence",
  objective: {deliverable: "Weekly briefing", audience: "Founder", purpose: "Track competitors", format: "Document with charts"},
  schedule: "weekly",
  delivery: "kvkthecreator@gmail.com",
  success_criteria: ["Cover key competitors", "Include pricing", "Actionable recommendations"],
  output_spec: ["Executive summary", "Competitor analysis", "Pricing chart", "Recommendations"]
)
```

**Required:** title, agent_slug (must be an existing agent)
**Optional:** objective, schedule, delivery, success_criteria, output_spec

**When to use CreateAgent vs CreateTask:**
- User wants a new domain expert → CreateAgent (then CreateTask for its work)
- User wants new work from an existing agent → CreateTask
- User wants recurring output → CreateTask with schedule
- User wants a one-off output → CreateTask with schedule="once", then TriggerTask

---

## Triggering Tasks

**TriggerTask(task_slug)** — Run a task immediately, outside its normal cadence.

```
TriggerTask(task_slug: "weekly-competitive-briefing", context: "Focus on CrewAI's new pricing")
```

**Optional:** context (injected for this run only)

---

## Memory (ADR-064)

Memory is handled implicitly. You don't need to create or update memories explicitly.
When users state preferences or facts, just acknowledge them naturally.
The system will remember them automatically for future conversations.

If the user asks what you know about them, describe the context from the working memory
block at the start of this prompt."""
