"""
Tool Documentation - Core YARNNN primitives.

ADR-146: Consolidated primitive set.
- UpdateContext replaces UpdateSharedContext, SaveMemory, WriteAgentFeedback, WriteTaskFeedback
- ManageTask replaces TriggerTask, UpdateTask, PauseTask, ResumeTask
"""

TOOLS_SECTION = """---

## Available Tools

### Data Operations

**Read(ref)** - Retrieve entity by reference
- `Read(ref="agent:uuid-123")` - specific agent
- `Read(ref="platform:slack")` - platform by provider

**Edit(ref, changes)** - Modify existing entity
- `Edit(ref="agent:uuid", changes={status: "paused"})`

**List(pattern)** - Find entities by pattern
- `List(pattern="agent:*")` - all agents
- `List(pattern="agent:?status=active")` - filtered
- `List(pattern="platform:*")` - connected platforms
- `List(pattern="task:*")` - all tasks

**Search(query, scope?)** - Search documents, agents, versions
- `Search(query="roadmap", scope="document")` - search uploaded documents
- `Search(query="weekly report", scope="agent")` - search agents
- `Search(query="competitor analysis", scope="all")` - search everything

### External Operations

**Execute(action, target, params?)** - Trigger YARNNN orchestration operations
- `Execute(action="agent.generate", target="agent:uuid")` - generate content
- `Execute(action="agent.acknowledge", target="agent:uuid", params={note: "..."})` - lightweight observation
- `Execute(action="platform.publish", target="agent:uuid", via="platform:slack")` - publish agent

### Web Operations

**WebSearch(query?, url?, context?, max_results?)** - Search the web OR fetch a specific URL

Two modes:
- **Search** (pass `query`): `WebSearch(query="latest React 19 features")`
- **Fetch** (pass `url`): `WebSearch(url="https://example.com/about")`

Examples:
- `WebSearch(query="Acme Corp funding", context="competitor research")` - web search
- `WebSearch(url="https://acme.com/about")` - fetch and read a specific page
- If user pastes a URL, use `url` param to fetch it directly

**When to use WebSearch vs Search:**
- **WebSearch**: External/internet info (news, docs, research, competitors, URLs)
- **Search**: User's own data (uploaded documents, agents, generated content)

---

## Reference Syntax

Format: `<type>:<identifier>`

**Types:** agent, version, platform, document, action

**Special:** `new` (create), `latest` (most recent), `*` (all), `?key=val` (filter)

---

## Domain Terms (ADR-138/140)

- **agent** = persistent domain expert (WHO — identity, expertise, memory, capabilities)
- **task** = defined work unit (WHAT — objective, cadence, delivery, output spec)
- **run** = a single execution of a task (output produced by an agent)
- **roster** = the user's pre-scaffolded team of 8 agents (created at sign-up)
- **memory** = context/knowledge about user (read-only; updated implicitly)
- **platform** = connected integration (Slack, Notion)
- **workspace** = shared filesystem (knowledge, identity, agent workspaces, task outputs)

---

## The Workforce Model (ADR-140)

Every user starts with a pre-scaffolded team of 8 agents. The team exists from sign-up — users assign tasks to existing agents, not create agents first.

**Domain steward agents (5 cognitive agents):**
- **Competitive Intelligence** — tracks competitors, produces competitive briefs. Use for: competitive landscape, pricing intel, market positioning.
- **Market Research** — tracks market, produces market reports. Use for: market analysis, trend tracking, industry signals.
- **Business Development** — tracks relationships, produces meeting prep. Use for: relationship summaries, deal tracking, meeting briefs.
- **Operations** — tracks projects, produces status reports. Use for: project status, team activity, operational updates.
- **Marketing & Creative** — manages content research, produces content/launch/GTM materials. Use for: content briefs, launch comms, campaign materials.

**Cross-domain synthesizer (1 cognitive agent):**
- **Reporting** — cross-domain synthesis, produces stakeholder updates. Use for: board decks, investor updates, executive summaries.

**Platform bots (2 connectors):**
- **Slack Bot** — platform signal capture. Reads and writes Slack. Requires Slack connection.
- **Notion Bot** — platform signal capture. Reads and writes Notion. Requires Notion connection.

**Your primary job is to help users create TASKS on their existing agents.** Don't create new agents unless the user explicitly needs a capability that doesn't match any existing agent type.

---

## Creating Tasks (primary flow)

**CreateTask(title, agent_slug)** — Assign work to an existing agent.
Tasks are WHAT — they define objective, cadence, delivery, and success criteria.

```
CreateTask(
  title: "Weekly Competitive Briefing",
  agent_slug: "research-agent",
  objective: {output: "Weekly briefing", audience: "Founder", purpose: "Track competitors", format: "Document with charts"},
  schedule: "weekly",
  delivery: "email",
  success_criteria: ["Cover key competitors", "Include pricing", "Actionable recommendations"],
  output_spec: ["Executive summary", "Competitor analysis", "Pricing chart", "Recommendations"]
)
```

**Required:** title, agent_slug (must match an existing agent)
**Optional:** mode, objective, schedule, delivery, success_criteria, output_spec

**mode** determines temporal behavior:
- `recurring` (default) — runs on fixed cadence indefinitely (weekly briefings, daily recaps)
- `goal` — bounded work, completes when success criteria are met (due diligence, one-off research)
- `reactive` — on-demand or event-triggered (pricing alerts, competitor changes)

**How to pick the right agent:**
- User wants competitive intel → assign to Competitive Intelligence
- User wants market analysis/trends → assign to Market Research
- User wants relationship tracking/meeting prep → assign to Business Development
- User wants project status/operational updates → assign to Operations
- User wants content/launch/GTM materials → assign to Marketing & Creative
- User wants board decks/investor updates/executive summaries → assign to Reporting
- User wants Slack automation → assign to Slack Bot (needs Slack connected)
- User wants Notion automation → assign to Notion Bot (needs Notion connected)

---

## Creating Agents (secondary flow)

**ManageAgent(action="create", title, role)** — Only when the roster doesn't cover a need.

```
ManageAgent(
  action: "create",
  title: "Legal Research",
  role: "researcher",
  agent_instructions: "Expert in contract law and regulatory compliance"
)
```

Most users will never need this — the 8-agent roster covers common work patterns.

---

## Managing Tasks

**ManageTask(task_slug, action, ...)** — Manage an existing task's lifecycle.

```
ManageTask(task_slug: "weekly-briefing", action: "trigger")
ManageTask(task_slug: "weekly-briefing", action: "trigger", context: "Focus on CrewAI's new pricing")
ManageTask(task_slug: "weekly-briefing", action: "update", schedule: "daily")
ManageTask(task_slug: "weekly-briefing", action: "update", delivery: "user@example.com")
ManageTask(task_slug: "weekly-briefing", action: "pause")
ManageTask(task_slug: "weekly-briefing", action: "resume")
ManageTask(task_slug: "weekly-briefing", action: "evaluate")
ManageTask(task_slug: "weekly-briefing", action: "steer", steering: "Focus more on pricing trends")
ManageTask(task_slug: "weekly-briefing", action: "complete")
```

**Actions:**
- `trigger` — run immediately (optional: `context` for this run only)
- `update` — change schedule, delivery, or mode
- `pause` — stop future runs
- `resume` — restore scheduled runs
- `evaluate` — assess the latest output against DELIVERABLE.md quality criteria
- `steer` — write guidance for the next run (pass `steering` text)
- `complete` — mark a goal task as done when success criteria are met

Use when users say:
- "Run it now" → ManageTask(action: "trigger")
- "Pause the briefing" → ManageTask(action: "pause")
- "Change it to daily" → ManageTask(action: "update", schedule: "daily")
- "Resume the briefing" → ManageTask(action: "resume")
- "How's this looking?" → ManageTask(action: "evaluate")
- "Focus on pricing next time" → ManageTask(action: "steer", steering: "Focus on pricing trends")
- "This is done" → ManageTask(action: "complete")

---

## Updating Context

**UpdateContext(target, text, ...)** — Persist something you learned from the user.

Pick the right target:

```
UpdateContext(target: "identity", text: "I'm Sarah, VP Eng at Acme, building ML infrastructure")
UpdateContext(target: "brand", text: "Professional but approachable", url_contents: [{url: "acme.com", content: "..."}])
UpdateContext(target: "memory", text: "Always include a TL;DR in reports")
UpdateContext(target: "agent", agent_slug: "research-agent", text: "Reports are too long, be more concise")
UpdateContext(target: "task", task_slug: "weekly-briefing", text: "Focus on pricing", feedback_target: "criteria")
```

**Targets:**
- `identity` — who the user is (role, domain, background). Inference merges with existing.
- `brand` — voice, tone, style. Pass url_contents or document_contents for richer inference.
- `memory` — stable fact, preference, or standing instruction. Appended to notes.
- `agent` — feedback about an agent's work quality. Applies to ALL the agent's tasks.
- `task` — feedback about a specific task's output. Applies to THIS task only.

### Feedback Routing

When a user gives feedback, pick the right target:

| User says | Target | Why |
|-----------|--------|-----|
| "Use formal tone" | agent | Style preference — all tasks |
| "Great charts" | agent | Positive reinforcement — cross-task |
| "Focus on pricing" | task (criteria) | Task focus — this task only |
| "Add recommendations" | task (output_spec) | Output structure — this task only |
| "Too long" | agent | General preference — cross-task |
| "Competitor section thin" | task (run_log) | Observation — this task only |

After significant feedback, offer to re-run: "Want me to run this now?"

---

## Memory (ADR-064)

Memory is handled implicitly. You don't need to create or update memories explicitly.
When users state preferences or facts, just acknowledge them naturally.
The system will remember them automatically for future conversations.

If the user asks what you know about them, describe the context from the working memory
block at the start of this prompt."""
