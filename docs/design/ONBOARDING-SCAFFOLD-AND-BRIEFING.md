# Onboarding Scaffold & Daily Briefing

**Date:** 2026-04-05
**Status:** Proposed
**Depends on:** [ADR-138](../adr/ADR-138-agents-as-work-units.md), [ADR-140](../adr/ADR-140-agent-workforce-model.md), [ADR-145](../adr/ADR-145-task-type-registry.md), [ADR-154](../adr/ADR-154-execution-boundary-reform.md)
**Related design docs:** [SURFACE-ARCHITECTURE.md](SURFACE-ARCHITECTURE.md) v4, [ONBOARDING-TP-AWARENESS.md](ONBOARDING-TP-AWARENESS.md) v2

---

## 1. Design Thesis: Day One Should Feel Like Week Two

When a user signs up, they should see a populated workspace — not empty agents and a prompt to "assign tasks." The onboarding flow scaffolds everything (directories, entities, tasks) and triggers immediate execution so the user gets their first round of intelligence in the same session.

The product is "hiring a team." A hired team arrives with a plan, learns your context, and starts producing on day one.

---

## 2. Onboarding Scaffold Sequence

**Existing flow** (implemented):
1. User lands on `/chat` (new user redirect)
2. ContextSetup renders — user provides URLs, files, notes
3. TP calls `UpdateContext(target="identity")` + `UpdateContext(target="brand")`
4. TP calls `ManageDomains(action="scaffold")` — bulk entity creation
5. TP presents scaffolded entities for user confirmation (accuracy gate)
6. **STOPS HERE** — TP suggests task types, user must ask

**Extended flow** (proposed):
1-5. Same as above
6. **TP auto-scaffolds default tasks** for each agent whose domain has entities
7. **TP triggers immediate execution** of all context tasks (run-now)
8. TP informs user: "Your team is working. First results in ~5 minutes."
9. Context tasks complete → **TP triggers synthesis tasks** (Reporting)
10. Synthesis completes → delivery fires (email, if configured)
11. **TP generates first daily briefing** on the Home page

### Scaffolding rules

- Only scaffold tasks for agents whose domains were populated in step 4
- Use default task types from registry (agent → type mapping below)
- All scaffolded tasks start as `status: active` (not paused)
- First run is immediate (`ManageTask(action="trigger")`)
- Platform bot tasks (Slack/Notion/GitHub) only scaffolded if platform is connected

### Agent → Default Task Mapping

| Agent | Default Task Type | Only If |
|-------|-------------------|---------|
| Competitive Intelligence | `track-competitors` | competitors/ has entities |
| Market Research | `track-market` | market/ has entities |
| Business Development | `track-relationships` | relationships/ has entities |
| Operations | `track-projects` | projects/ has entities |
| Marketing & Creative | `research-topics` | content_research/ has entities |
| Reporting | `executive-summary` (synthesis) | At least 1 context task active |
| Slack Bot | `slack-digest` | Slack connected |
| Notion Bot | `notion-digest` | Notion connected |
| GitHub Bot | `github-digest` | GitHub connected |

### Execution order (TP-orchestrated, not deterministic pipeline)

TP uses existing primitives in sequence. No new pipeline mechanism:

```
ManageTask(action="create", type_key="track-competitors", ...) × N context tasks
  → ManageTask(action="trigger") × N
  → [wait for completion — TP checks working memory on next turn]
  → ManageTask(action="create", type_key="executive-summary", ...)
  → ManageTask(action="trigger")
  → [delivery fires automatically]
```

TP judges which tasks to scaffold based on context quality. If the user only provided competitor info, only track-competitors gets scaffolded. TP doesn't create tasks for empty domains.

### Implementation: TP onboarding prompt extension

Add to `api/agents/tp_prompts/onboarding.py` CONTEXT_AWARENESS section:

```
## After scaffolding confirmation

Once the user confirms the scaffolded entities, proceed to task activation:

1. For each domain with entities, create the default context task:
   - ManageTask(action="create", type_key="track-competitors", title="Track Competitors") for competitors/
   - ManageTask(action="create", type_key="track-market", title="Track Market") for market/
   - etc. (see agent-to-task mapping in your knowledge)

2. Trigger all created context tasks immediately:
   - ManageTask(task_slug="...", action="trigger") for each

3. Tell the user: "Your agents are working on their first round of research.
   You'll see results appear in each agent's knowledge base within a few minutes."

4. If synthesis task conditions are met (2+ context tasks active),
   create and trigger the executive summary task after context tasks complete.

Do NOT wait for the user to ask for tasks. The scaffolding flow is:
context → entities → confirmation → tasks → trigger → briefing.
```

### Gating: accuracy gate verification

The existing accuracy gate (onboarding.py line 119) presents entities for user confirmation before proceeding. Verify it gates task creation — TP must not scaffold tasks until entities are confirmed.

Check: `onboarding.py` line 119-136 — the prompt says "present grouped list for confirmation" then "only after confirmation, suggest tasks." We change "suggest" to "create and trigger."

---

## 3. Home Page (Renamed from Chat)

### Navigation rename

```
Before: Chat | Agents | Context | Activity
After:  Home | Agents | Context | Activity
```

`HOME_ROUTE` stays as `/agents` for returning users with tasks. The `/chat` route becomes `/home` (or keeps `/chat` internally with the nav label changed to "Home").

### Home page layout (returning user with tasks)

The daily briefing is a **persistent collapsible header** — always rendered above the chat, never hidden by messages. This ensures workspace-level signals are always accessible, not buried after the first message.

**Expanded state** (default on page load, or when user clicks expand):

```
┌──────────────────────────────────────────────────────────┐
│  DAILY BRIEFING                     Apr 5  [▲ Collapse] │
│                                                           │
│  What happened                                            │
│  · Competitive Intelligence: 2 profiles updated           │
│  · Slack Bot: 3 channels digested, 1 decision captured    │
│  · Market Research: no run today (weekly, next Mon)       │
│                                                           │
│  Coming up                                                │
│  · Tomorrow: Slack Digest, GitHub Digest                   │
│  · Monday: Competitive Intelligence, Biz Dev              │
│  · Apr 15: Market Research                                │
│                                                           │
│  Needs attention                                          │
│  · Operations: 0 entities — needs project context         │
│                                                           │
│  3 platforms · 12 entities · 5 active tasks               │
├──────────────────────────────────────────────────────────┤
│  Chat messages...                                         │
│  ...                                                      │
│  [+]  Ask anything or type / ...                 [Send]  │
└──────────────────────────────────────────────────────────┘
```

**Collapsed state** (auto-collapses after user sends first message, or manual toggle):

```
┌──────────────────────────────────────────────────────────┐
│  DAILY BRIEFING  3 ran · 2 coming up · 1 attention  [▼] │
├──────────────────────────────────────────────────────────┤
│  Chat messages...                                         │
│  ...                                                      │
│  [+]  Ask anything or type / ...                 [Send]  │
└──────────────────────────────────────────────────────────┘
```

**Behavior rules:**
- Briefing header always renders (never hidden by messages)
- Starts expanded on page load
- Auto-collapses to one-line summary when user sends first message
- User can manually toggle expand/collapse at any time
- Collapse state persists across page navigation (localStorage)
- Briefing data refreshes on page load and every 60s

### Home page layout (new user, no tasks)

ContextSetup renders as full-page overlay above the chat input (existing behavior). The briefing header does not render when there are no tasks — it only appears once the workspace has active tasks.

### Daily briefing data source

The briefing is rendered from **working memory** data that TP already has access to:
- Agent roster with task counts → `GET /api/agents`
- Task list with schedules and last_run_at → `GET /api/tasks`
- Recent activity → `GET /api/activity` (filtered to last 24h)

This is a **frontend component**, not a TP-generated artifact. The Home page fetches the data and renders the briefing card. No LLM cost.

### Workspace signals

Compact row showing workspace health at a glance:
- Platform connection count
- Entity count across all domains
- Active task count
- Identity richness (from `workspace.getNav().readiness`)

---

## 4. Agent Work Rhythm (UI Framing)

### Principle: "Agents work, tasks don't"

The user thinks: "My Competitive Intelligence agent works weekly." Not: "The track-competitors task runs weekly."

### UI changes

**Agent tab status line:**
```
Before: ● Active · Updated 2h ago · Weekly
After:  ● Works weekly · Updated 2h ago
```

**Left panel metadata:**
```
Before: competitors/ · 1 task
After:  competitors/ · works weekly
```

**Setup tab:**
Show agent work rhythm at top, tasks inherit:
```
Work rhythm: Weekly (Mon 9am)
Tasks run on this schedule unless overridden.
```

### Data model: no change

`schedule` remains on the `tasks` table. The agent's "work rhythm" is derived from its most frequent active task's schedule. This is a display-only concept — no new field needed.

Derivation:
```typescript
const agentRhythm = activeTasks.length > 0
  ? activeTasks.sort(byFrequency)[0].schedule  // most frequent
  : null;
```

---

## 5. Task Naming Convention (Reinforced)

Task names are freeform. Default names come from the type registry `display_name` field. Schedule, mode, and type classification are separate fields — never in the name.

When TP auto-scaffolds tasks during onboarding, it uses the registry defaults:
- "Track Competitors" (not "Weekly Competitor Tracking")
- "Slack Digest" (not "Daily Slack Recap")
- "Executive Summary" (not "Weekly Executive Report")

---

## 6. Implementation Plan

### Phase 1: Home page + briefing

| Step | What | Files |
|------|------|-------|
| 1 | Rename nav label "Chat" → "Home" | `web/components/layout/AuthenticatedLayout.tsx` |
| 2 | Build DailyBriefing component | `web/components/home/DailyBriefing.tsx` (new) |
| 3 | Build WorkspaceSignals component | `web/components/home/WorkspaceSignals.tsx` (new) |
| 4 | Update chat/home page with briefing + signals above chat | `web/app/(authenticated)/chat/page.tsx` |
| 5 | Conditional: ContextSetup (new user) vs Briefing (returning) | Same file |

### Phase 2: Onboarding task scaffold

| Step | What | Files |
|------|------|-------|
| 6 | Extend TP onboarding prompt with task scaffold recipe | `api/agents/tp_prompts/onboarding.py` |
| 7 | Add agent-to-task-type mapping constant | `api/agents/tp_prompts/onboarding.py` or `api/services/agent_framework.py` |
| 8 | Verify accuracy gate blocks task creation until confirmed | `api/agents/tp_prompts/onboarding.py` |
| 9 | Test: full onboarding flow scaffolds entities → tasks → trigger | Manual E2E |

### Phase 3: Agent work rhythm framing

| Step | What | Files |
|------|------|-------|
| 10 | Update AgentContentView status line wording | `web/components/agents/AgentContentView.tsx` |
| 11 | Update agent roster card metadata line | `web/components/agents/AgentRosterSurface.tsx` (was `AgentTreeNav.tsx`, ADR-167) |
| 12 | Update Setup tab to show rhythm at agent level | `web/components/agents/AgentContentView.tsx` |

### Phase 4: Synthesis roll-up

| Step | What | Files |
|------|------|-------|
| 13 | Add TP prompt guidance for post-context synthesis trigger | `api/agents/tp_prompts/onboarding.py` |
| 14 | Verify synthesis task waits for context tasks to complete | Working memory signals + TP judgment |

---

## 7. Consistency Check

### Existing framework alignment

| Mechanism | Exists? | Consistent? |
|-----------|---------|-------------|
| Playbook loading (selective by task class) | Yes | N/A — this is TP prompt, not agent playbook |
| ManageTask(action="create") primitive | Yes | Uses type_key → auto-pipeline. ADR-168 Commit 3 folded CreateTask into ManageTask. |
| ManageTask trigger action | Yes | Existing, fully functional |
| ManageDomains scaffold action | Yes | Existing, used in onboarding |
| Working memory (agent health, task status) | Yes | Already injected into TP prompt |
| Accuracy gate in onboarding | Yes | Needs "create tasks" added after gate |
| Daily briefing data | Yes | API endpoints exist, frontend render only |

### No new primitives needed

All orchestration uses existing TP primitives. The only change is prompt text in `onboarding.py` — adding the task scaffold recipe after the accuracy gate.

### No new data model changes

- `schedule` stays on tasks table
- Agent "work rhythm" is derived display-only
- Daily briefing is frontend-rendered from existing API data
- No new tables, columns, or migrations

---

## Revision History

| Date | Change |
|------|--------|
| 2026-04-05 | v1 — Initial proposal. Onboarding scaffold, daily briefing, Home page rename, agent work rhythm framing. |
