# ADR-124: Project Meeting Room — Unified Project Surface

**Status**: Phase 1 Implemented (ChatAgent class, agent_chat mode, routing, attribution)
**Date**: 2026-03-19
**Authors**: KVK, Claude
**Supersedes**: None (evolves ADR-119 Phase 4b project detail page)
**Implements**: FOUNDATIONS.md Axioms 1, 2, 3, 4 (personification of agents as developing entities; conversation as project perception layer)

---

## Context

The current `projects/[slug]` page uses a three-tab layout (Timeline | Outputs | Contributors) where:
- Timeline merges activity events + TP chat messages chronologically
- TP is the only conversational participant — all chat goes through TP
- Agents are listed as "contributors" — data objects, not participants
- PM intelligence (quality assessments, contributor briefs) surfaces as static panels
- Agent progress, outputs, and status are split across separate tabs

This creates a conceptual gap: agents are persistent entities with identity and development (Axiom 3), but the project surface treats them as inert data rows. The user cannot talk to agents directly; they talk to TP, which proxies. The PM's coordination intelligence is buried in a Contributors tab instead of being visible as part of the project's living conversation.

### The Personification Insight

Agents are not configurations — they are participants. A project is not a dashboard — it is a working room where participants collaborate. Applying this analogy:

- The **user** is present (they can see, chat, direct)
- The **PM agent** is present (it coordinates, assesses, steers)
- **Contributing agents** are present (they produce, respond, report)
- **TP** is infrastructure — it routes, enriches, mediates — but is not a visible "person in the room" (the user already has PM + contributors as interlocutors)

This maps directly to a **group chat** model where each participant has identity, messages appear attributed to their author, and structured events (assemblies, quality assessments, contribution deliveries) surface as cards within the conversation stream.

---

## Decision

Redesign `projects/[slug]` as a **Meeting Room** — a unified conversational surface where agents are visible participants, not abstract data.

### Three-Tab Architecture

| Tab | Purpose | Content |
|-----|---------|---------|
| **Meeting Room** | Primary surface — group chat with structured cards | Chat messages (user ↔ agents), activity event cards, output cards, PM assessments |
| **Context** | Project filesystem browser | Workspace files (`/projects/{slug}/`), contribution files, output folders, PROJECT.md |
| **Settings** | Configuration & metadata | Objective editing, contributor management, schedule, archive, delivery preferences |

### Agent Chat Participation Model

**Users can talk to any agent in the meeting room, not just PM/TP.**

The chat input supports `@agent-slug` mentions to direct messages. Without an `@` prefix, messages route to the PM by default (as project coordinator). The routing model:

| User action | Routes to | Why |
|------------|-----------|-----|
| Plain message | PM agent | PM is the project coordinator — default interlocutor |
| `@agent-slug message` | Specific agent | Direct address — user wants that agent's perspective |
| `/command` | TP (implicit) | Slash commands are system-level, TP handles them |
| System events | No routing | Activity cards render inline, not conversational |

### Message Attribution

Every message in the stream is attributed to its author:

- **User**: Right-aligned bubble (current pattern)
- **PM agent**: Left-aligned with PM avatar/badge + name
- **Contributing agents**: Left-aligned with agent avatar/badge + name
- **TP**: Only visible when executing slash commands or system-level operations (subtle, differentiated styling)
- **System events**: Compact inline cards (heartbeats, assemblies, quality assessments) — not bubbles

### Structured Event Cards

Activity events that currently render as timeline items become **inline cards** in the meeting room stream, interleaved chronologically with chat messages:

| Event | Card type | Content |
|-------|-----------|---------|
| `project_heartbeat` | Status card | PM check-in summary, contributor freshness |
| `project_assembled` | Output card | Assembly preview, file links, delivery status |
| `project_quality_assessed` | Assessment card | Quality verdict, expandable detail |
| `project_contributor_steered` | Directive card | What PM asked of contributor, why |
| `project_contributor_advanced` | Action card | Early run request + reason |
| `project_escalated` | Alert card | Escalation with reason, action needed |

### Participant Panel

A compact sidebar or collapsible panel shows "who's in the room":

- **PM agent**: Role badge, last check-in time, health indicator
- **Each contributor**: Role badge, last contribution time, contribution count
- **User**: Always present (implicit)

Each participant card links to `/agents/{id}` for full agent detail. The panel replaces the current Contributors tab's list view.

---

## Architecture

### Phase 1: Agent Chat Infrastructure (Backend)

**Problem**: Agents are fundamentally headless-only today. They have no chat-mode class, no streaming capability, and no conversational prompt.

**Solution**: Create a `ChatAgent` base that enables agents to participate in conversations.

#### 1.1 ChatAgent Class

New file: `api/agents/chat_agent.py`

```python
class ChatAgent:
    """
    Enables an agent to participate in chat conversations.

    Unlike TP (full meta-cognitive, all primitives), ChatAgent is:
    - Domain-scoped (has agent identity, instructions, memory)
    - Read-heavy primitives (workspace read, search, query knowledge)
    - Limited write (WriteWorkspace for own workspace only)
    - Streaming (SSE, same transport as TP)
    """

    async def execute_stream_with_tools(
        self, task, agent, auth, history, ...
    ):
        # Build agent-specific system prompt
        # Load agent workspace context (AGENT.md, memory/, thesis.md)
        # Stream response with agent-appropriate primitives
        pass
```

Key constraints:
- ChatAgent gets **its own** primitives, not TP's full set
- No `CreateAgent`, `Execute`, `AdvanceAgentSchedule` — those are TP/coordinator-level
- Yes to `ReadWorkspace`, `SearchWorkspace`, `QueryKnowledge`, `ReadAgentContext`
- Yes to `WriteWorkspace` (own workspace only — for observations, memory updates)
- PM agents additionally get `CheckContributorFreshness`, `ReadProjectStatus`, `RequestContributorAdvance`, `UpdateWorkPlan`

#### 1.2 New Primitive Mode: `"agent_chat"`

Extend `PRIMITIVE_MODES` in `registry.py`:

```python
PRIMITIVE_MODES = {
    # ... existing modes ...
    "ReadWorkspace":     ["headless", "agent_chat"],
    "WriteWorkspace":    ["headless", "agent_chat"],
    "SearchWorkspace":   ["headless", "agent_chat"],
    "QueryKnowledge":    ["headless", "agent_chat"],
    "ReadAgentContext":  ["headless", "agent_chat"],
    # PM-specific: also available in agent_chat for PM role
    "CheckContributorFreshness":  ["headless", "agent_chat"],
    "ReadProjectStatus":          ["headless", "agent_chat"],
    "RequestContributorAdvance":  ["headless", "agent_chat"],
    "UpdateWorkPlan":             ["headless", "agent_chat"],
}
```

#### 1.3 Chat Routing Extension

Extend `chat.py` to support agent-targeted messages within project sessions:

```python
class ChatRequest(BaseModel):
    content: str
    target_agent_id: Optional[str] = None  # ADR-124: direct message to specific agent
    # ... existing fields ...
```

When `target_agent_id` is set and within a project session:
1. Load the target agent's identity, instructions, workspace context
2. Instantiate `ChatAgent` instead of `ThinkingPartnerAgent`
3. Use the same SSE streaming transport
4. Store messages with `metadata.target_agent_id` for attribution

When `target_agent_id` is None in a project session → route to PM agent (default).

#### 1.4 Session Model

Project sessions (already persistent, no 4h rotation) become multi-participant:
- All messages in one session, attributed by `metadata.author_agent_id` or `role=user`
- Agent responses include `metadata.agent_slug` and `metadata.agent_role` for frontend attribution
- TP messages (slash commands) include `metadata.author = "tp"` to distinguish from agent responses

No schema change needed — `session_messages.metadata` JSONB already supports this.

### Phase 2: Meeting Room Frontend

#### 2.1 Meeting Room Component

Replace `TimelineTab` with `MeetingRoom`:

```typescript
// Unified stream: chat messages + activity events + output cards
type MeetingRoomItem =
  | { kind: 'message'; data: ProjectMessage }     // Chat message with attribution
  | { kind: 'event'; data: ProjectActivityItem }   // Structured event card
  | { kind: 'output'; data: OutputManifest }        // Assembly output card

interface ProjectMessage extends TPMessage {
  authorType: 'user' | 'agent' | 'tp';
  agentSlug?: string;
  agentRole?: string;
  agentDisplayName?: string;
}
```

#### 2.2 Chat Input with @-mentions

Extend the chat input with agent mention support:
- `@` trigger opens autocomplete with project participants (PM + contributors)
- Selected agent sets `target_agent_id` on the request
- Visual indicator shows who you're talking to
- Default (no mention) → PM

#### 2.3 Participant Panel

Collapsible right-side panel (or top bar on mobile):
- Lists PM + all contributors with avatar, role badge, last active time
- Click → navigates to `/agents/{id}`
- Compact: just avatars in a row; expanded: cards with details

#### 2.4 Data Migration from Tabs

| Current location | Meeting Room treatment |
|-----------------|----------------------|
| Timeline activity events | Inline event cards in stream |
| Timeline TP chat | Migrates to attributed messages (author = PM or agent) |
| Outputs tab content | Output cards appear inline when assemblies complete; full browse moves to Context tab |
| Contributors tab list | Participant panel (sidebar/header) |
| Contributors tab PM intelligence | PM assessment cards in stream + PM brief on participant hover |
| Objective editing | Moves to Settings tab |

### Phase 3: Agent System Prompts for Chat

Each agent needs a conversational prompt when participating in chat (distinct from its headless generation prompt).

#### 3.1 PM Chat Prompt

```
You are {agent_name}, the Project Manager for "{project_title}".

Your domain is coordinating this project's execution. You have deep knowledge of:
- The project objective and what the user wants
- Each contributor's role, recent work, and quality trajectory
- The work plan, budget status, and assembly schedule

When the user talks to you:
- Answer from your PM perspective — you know this project intimately
- Reference specific contributor work, quality assessments, timeline status
- You can take PM actions (check freshness, advance schedules, update work plan)
- Be concise and direct — you're a domain expert, not a general assistant
```

#### 3.2 Contributor Chat Prompt

```
You are {agent_name}, a {role} agent contributing to project "{project_title}".

Your domain expertise is {scope_description}. You have accumulated:
- Your workspace: AGENT.md (identity), thesis.md (domain understanding), memory/ (observations)
- Your contribution history to this project
- Knowledge from your connected platforms

When the user talks to you:
- Answer from your domain perspective — what you know about your area
- Reference your recent work, observations, and domain thesis
- You can read workspace files and search knowledge, but you don't coordinate — PM does that
- Be concise — you're a specialist, not a generalist
```

### Phase 4: Context Tab (Workspace Browser)

Replace the Outputs tab with a full workspace file browser for the project:
- Tree view of `/projects/{slug}/` filesystem
- Contribution files grouped by agent
- Output folders with manifest + file previews
- PROJECT.md viewable (read-only from this surface)
- Quick links to agent workspaces (`/agents/{slug}/`)

### Phase 5: Settings Tab Consolidation

Move non-chat concerns here:
- Editable Objective (from current header)
- Contributor management (add/remove agents)
- Assembly configuration
- Delivery preferences
- Schedule settings
- Archive action

---

## Data Handling: Three Scopes (First Principles)

The meeting room creates a new data scope that doesn't exist today. Before classifying existing fields, we need to define the scopes themselves.

### The Three Data Scopes

**1. Agent scope** — data that belongs to the agent as a persistent, autonomous entity. This data exists whether or not the agent is in any project. It is the agent's *self*.

**2. Group scope** — data that belongs to the meeting room as a shared conversational space. This data exists *because* multiple participants are in the same room. It is the *relationship* between participants and the shared context they build together.

**3. Project scope** — data that belongs to the project as an organizational unit. Charter, configuration, filesystem. This data is structural and persists across sessions.

The key insight: **today, group scope doesn't exist.** Everything is either agent-level or project-level. The meeting room introduces group data that is neither.

### The Conversation as Project Context (Axiom 2 Extension)

FOUNDATIONS Axiom 2 defines three perception layers: external (platform_content), internal (workspace_files/knowledge), and reflexive (user feedback + TP assessment). The meeting room conversation is a **fourth perception layer** — project-scoped conversational perception.

```
External platforms → platform_content → agent execution → agent output →
  /knowledge/ (workspace_files) → next agent execution → ...
                              ↑                           |
                              └── user feedback ──────────┘
                              └── TP assessment ──────────┘
                              └── MEETING ROOM TRANSCRIPT ─┘  ← NEW
```

The conversation transcript becomes the **unified context for the project** — the single place where TP, PM, user, and contributors all read to understand what's happening. This is the same filesystem analogy applied to conversation:

- **Workspace files** are the filesystem for agent work. Reading a file = fetching content.
- **The meeting room transcript** is the filesystem for project coordination. Reading the room = understanding the project's current state.

When PM needs to decide whether to assemble, it reads the room — has the user given new directives? What did contributors report? When TP's Composer checks project health, it reads the room — is the user satisfied? Is PM stuck? When a contributor is @-mentioned, it reads the room — what context does the user's question carry from prior discussion?

#### What goes INTO the conversation (first-order vs second-order)

This is the critical design question. Not everything should be in the transcript.

**First-order data** (belongs in the conversation stream):
- User messages and directives
- Agent responses (PM assessments, contributor observations, answers to questions)
- Delivery events (assembly completed → output card with preview + download links)
- PM coordination events (heartbeat results, steering decisions, escalations)
- Group decisions ("let's change format to PDF" → visible to all subsequent responses)

**Second-order data** (referenced from the conversation, fetched on demand):
- Full contribution file contents → the stream shows "Slack Recap contributed 3 files" as a card. Clicking expands or navigates to the Context tab. Like how a chat message saying "here's the report" links to a PDF — the mention is first-order, the document is second-order.
- Full assembly output → the stream shows an output card with version, status, and a brief preview. Full markdown render or file downloads are a click away. Same as how Slack shows a file preview thumbnail, not the entire document inline.
- Agent run details (token usage, source snapshots, edit scores) → operational metrics. If the user asks "how did that run go?" they @-mention the agent or click through to `/agents/{id}`.
- Raw workspace files (AGENT.md, memory/*.md, thesis.md) → these are the agent's private cognition. The *effect* surfaces in how the agent speaks in the room. The raw files are second-order, accessible via Context tab or agent detail page.

The principle: **the conversation carries decisions, assessments, and summaries. Files carry the full content.** This matches how a real meeting works — you discuss the report in the meeting, you don't read the entire 50-page document aloud. But you can pull it up.

#### How this maps to existing structural setups

| Existing structure | Meeting room role |
|-------------------|-------------------|
| **PROJECT.md** (objective, contributors, assembly_spec, delivery) | The project's charter. PM reads it as reference when responding in the room. Edits happen in Settings tab, but the *effect* of the charter is visible in PM's coordination behavior. |
| **PM's `memory/work_plan.md`** | PM's operational plan. PM references it when answering questions or making coordination decisions in the room. If the user says "what's the plan?", PM reads its work plan and summarizes in conversation. The plan itself is second-order (viewable in Context tab). |
| **`/contributions/{agent}/`** | What agents have produced. Contribution events surface as first-order cards in the stream. File contents are second-order. |
| **`/outputs/{date}/`** | What PM has assembled. Assembly events surface as first-order cards. Full output is second-order. |
| **`activity_log` events** | Project activity history. These become first-order event cards in the stream — they ARE the conversation's structural backbone alongside chat messages. |
| **PM intelligence** (quality assessments, briefs) | PM's assessments of contributors. When PM assesses quality, it's a first-order event in the stream — visible to all. Briefs are relational data visible on participant cards. |

#### The meta-awareness implication

This is where it gets powerful. If the conversation is the project context:

- **PM** reads the room to understand what the user wants, what contributors have reported, and what decisions have been made. Its coordination intelligence is *informed by the conversation*. Today PM operates on workspace files alone (heartbeat reads contribution freshness, work plan, etc.). With the meeting room, PM also has conversational context — user directives, contributor responses, prior assessments.

- **TP/Composer** reads the room to understand project health at a meta level. Today Composer reads PM's workspace files to check project status. With the meeting room, Composer can also read the transcript to understand *the dynamic* — is the user frustrated? Has the project stalled conversationally? Is PM responsive?

- **Contributors** read the room when @-mentioned. They see what PM assessed about them, what the user is asking, and what other contributors have said. This gives them natural context without requiring explicit cross-agent workspace reads.

The meeting room transcript becomes **the single source of truth for "what's happening in this project right now"** — complementing the workspace files which are "what has been produced."

### Group Scope: What Emerges from Shared Presence

#### Shared Conversation Context

When PM tells the user "Slack Recap's contribution is stale," and the user then @-mentions Slack Recap to ask about it, Slack Recap needs to see PM's assessment. This is **conversation history as shared context** — not agent memory, not project files, not TP session state.

Today: `session_messages` stores messages in a session scoped to `project_slug`. But all messages are user ↔ TP. There's no multi-participant context.

Meeting room: The session becomes a **shared transcript**. Every agent responding in the room receives the full conversation history (up to the context window budget) as input. This means:

- PM sees what the user said to a contributor
- A contributor sees PM's quality assessment delivered in the stream
- The user's directive "let's change the format to PDF" is visible to all subsequent agent responses
- An agent's clarification question and the user's answer are visible to other agents

**This is not cross-agent workspace reading** (ADR-116, which is about reading files). This is **conversational co-presence** — the transcript itself is the shared medium.

Implementation: `session_messages` with `metadata.author_agent_id` (or `null` for user). When building history for a ChatAgent call, include the full project session transcript with author attribution. The agent sees "PM said: ...", "User said: ...", "Slack Recap said: ..." as context.

#### Attribution as Structural Data

Today: `session_messages.role` is `"user"` or `"assistant"`. `metadata` is a JSONB bag.

Meeting room: **Who said it** is as important as what was said. Attribution drives:
- Frontend rendering (different bubble styles per author)
- Context injection (agents see who said what)
- PM meta-awareness (PM can see what contributors told the user)

This demands either:
- (a) A `metadata.author_agent_id` + `metadata.author_agent_slug` convention on every message (soft schema), or
- (b) A new `author_agent_id` column on `session_messages` (hard schema)

Decision: Start with (a) — metadata convention. Migrate to (b) if query patterns demand it (e.g., "show me all messages from PM in this project").

#### Participant State

Data that describes a participant's relationship to the room *right now*:

| Participant state | What it means | Where it comes from |
|------------------|---------------|---------------------|
| **Last spoke** | When this participant last sent a message in the room | Computed from `session_messages` WHERE `author_agent_id = X` |
| **Last contributed** | When this agent's latest contribution file was written | `workspace_files.updated_at` for `/projects/{slug}/contributions/{agent}/` |
| **Currently responding** | This agent is streaming a response right now | Frontend ephemeral state (SSE stream in progress) |
| **Contribution count** | How many contribution files this agent has written | `contributions: Record<string, string[]>` (already exists in API) |
| **Health status** | Active, paused, or stale | Derived: agent.status + contribution freshness from PM heartbeat |

This is **group-level derived state** — it exists because the agent is a participant in this room, not because it's an intrinsic property of the agent.

#### Group Decisions and Directives

When the user says in the meeting room: "Let's pivot to a PDF format instead of PPTX" — this is a group-level decision. Today it would disappear into the chat transcript. But it should be:

1. **Visible to all agents** in subsequent responses (via conversation history injection — covered above)
2. **Potentially persistent** — if it changes the project objective or delivery format, PM should pick it up and act on it

How: PM, as default interlocutor, is the natural recipient of such directives. PM can:
- Update the work plan (`UpdateWorkPlan` primitive) based on conversation context
- Surface the change as a SteerCard or AdvanceCard in the stream
- Let the user confirm before modifying PROJECT.md (via TP/system-level `/` command)

This means **the conversation itself is a write surface for the project** — not through direct edits, but through PM-mediated interpretation of group discussion. The meeting room is where the user and PM negotiate the project's direction, and agents observe.

#### Cross-Participant Awareness

PM's intelligence (quality assessments, contributor briefs) is currently stored as workspace files (`memory/quality_assessment.md`, `contributions/{slug}/brief.md`). In the meeting room, this intelligence becomes **relational data between participants**:

- PM's assessment of Slack Recap → a relationship between PM and Slack Recap, visible to the user
- PM's brief for Revenue Analyst → guidance from PM to Revenue Analyst, visible because they're in the same room
- A contributor's response to PM's steering → observable progress visible to the user and PM

This is not just "surface PM files as cards." The meeting room creates a context where **one participant's output about another participant** is naturally visible because they share the space. The group chat makes inter-agent relationships legible without requiring the user to visit separate pages and mentally connect the dots.

### Agent Scope: What Stays Private

An agent's private self — the data that is intrinsic to its identity and exists regardless of project membership. This is what `/agents/{id}` surfaces.

| Data | Why it stays agent-level |
|------|------------------------|
| **Instructions** (AGENT.md) | Behavioral identity. Editing instructions is a deliberate act — like rewriting someone's job description. Not a meeting room conversation. |
| **Memory** (observations, preferences, supervisor notes, goals) | Internal cognition. The agent's responses in the meeting room *reflect* its memory without exposing raw state. You don't read a colleague's private notes — you hear the effect in what they say. |
| **Schedule** (frequency, day, time) | Global trigger configuration. Pausing an agent affects all its projects, not just this one. |
| **Sources** (platforms, channels, labels) | Data pipeline config. Where the agent gets its raw input. |
| **Destination** (email, format) | Delivery config. May differ per-project vs standalone. |
| **Full run history** | All runs across all contexts — most are irrelevant to this project. |
| **Non-project sessions** | Direct user ↔ agent chat from `/agents/{id}`. Different conversational context. |
| **Prompt composition** | The system prompt preview in the Instructions tab. Implementation detail. |
| **Token usage, source snapshots per run** | Operational metrics. |
| **Edit distance, feedback scores per run** | Raw feedback data. PM's assessment is the group-level abstraction. |

**What crosses the boundary**: The agent's *identity card* — title, role, platform icon, status, expected contribution, description — is visible in the participant panel. This is the public face of the agent in the room, analogous to a name badge.

### Project Scope: What is Structural

The project's persistent configuration and filesystem. Survives across sessions, across meeting room conversations, across PM heartbeats.

| Data | Surface |
|------|---------|
| **PROJECT.md** (title, objective, contributors, assembly_spec, delivery) | Settings tab (editable) + read-only header summary in meeting room |
| **Work plan** (PM's `memory/work_plan.md`) | Context tab (read-only from this surface; PM writes via primitives) |
| **Contribution files** (`/projects/{slug}/contributions/{agent}/`) | Context tab (file browser, grouped by agent) |
| **Output folders** (`/projects/{slug}/outputs/{date}/`) | Context tab (manifest + files + preview) |
| **Assembly spec, delivery config** | Settings tab (currently fetched but not displayed) |
| **Activity log** (`activity_log` events) | Structural history — the sequence of heartbeats, assemblies, escalations. Surfaces as event cards in the meeting room stream. |

### Scope Interaction Diagram

```
┌─────────────────────────────────────────────────────────┐
│ MEETING ROOM (Group Scope)                              │
│                                                         │
│  Shared transcript (all participants see all messages)  │
│  Participant state (last spoke, health, contribution #) │
│  Event cards (activity log rendered inline)             │
│  Group decisions (user directives via PM mediation)     │
│  Cross-participant awareness (PM briefs visible to all) │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │  User    │  │   PM     │  │ Contrib  │  ...         │
│  │ (present)│  │ (present)│  │ (present)│              │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘             │
│       │              │              │                    │
└───────┼──────────────┼──────────────┼────────────────────┘
        │              │              │
        │         ┌────┴─────┐  ┌────┴─────┐
        │         │ PM Agent │  │ Agent    │ ← Agent Scope
        │         │ (private)│  │ (private)│   (instructions,
        │         │ memory,  │  │ memory,  │    memory, runs,
        │         │ runs,    │  │ runs,    │    schedule, etc.)
        │         │ schedule │  │ schedule │
        │         └────┬─────┘  └────┬─────┘
        │              │              │
   ┌────┴──────────────┴──────────────┴────┐
   │ PROJECT (Project Scope)                │
   │ PROJECT.md, work plan, contributions/, │
   │ outputs/, activity_log, assembly_spec  │
   └────────────────────────────────────────┘
```

The meeting room sits *above* both agent scope and project scope. It reads from both but owns its own data: the shared transcript, participant state, and the conversational context that emerges from co-presence.

### Field-Level Audit (Grounded in Codebase)

With the three scopes defined, here is the exhaustive field mapping from the actual `agents/[id]` right panel (6 tabs) and `projects/[slug]` page.

#### From Agent Detail Page → Meeting Room

**Source: `Agent` type, `AgentWorkspacePage`, `AgentRunDisplay`, `AgentOutputsPanel`, `AgentDrawerPanels`, `AgentSettingsPanel`, `AgentChatArea`**

| Field | Current Panel | Scope | Meeting Room Treatment |
|-------|-------------|-------|----------------------|
| `title` | Header | Agent → Group (identity card) | Participant name in stream + panel |
| `scope`, `role` | Header (platform icon) | Agent → Group (identity card) | Role badge on participant card |
| `status` (active/paused/archived) | Header toggle | Agent (private) → Group (read-only badge) | Badge on participant card. Pause/resume stays at `/agents/{id}`. |
| `mode` (recurring/goal/reactive/proactive/coordinator) | Settings | Agent (private) | Informational on participant card only |
| `description` | Not displayed | Agent (private) | Participant card subtitle if present |
| `sources[]` (provider, resource_id) | Settings (list + add/remove) | Agent (private) | Platform icon on participant card. Config stays agent-level. |
| `schedule` (frequency, day, time) | Settings + header | Agent (private) | Not surfaced. Schedule is agent-global. |
| `destination` (platform, target, format) | Settings (read-only) | Agent (private) | Not surfaced. Delivery config is agent-global. |
| `agent_instructions` | Instructions tab (monospace) | Agent (private) | Not surfaced. Visit `/agents/{id}` to view/edit. |
| `recipient_context` (name, role, priorities) | Instructions tab | Agent (private) | Not surfaced. Informs agent's chat responses implicitly. |
| `agent_memory` (observations, goal, review_log, preferences, supervisor_notes) | Memory tab (multiple card types) | Agent (private) | Not surfaced. Agent's chat responses reflect memory. "You hear the effect, not the raw notes." |
| `AgentRun[]` (version_number, status, content, delivery_*, source_snapshots, tokens, edit_distance) | Runs tab (list + full preview) | Agent (private, full history) → Group (project contributions only) | **Contribution runs only** appear as output cards in stream. Full run detail stays at `/agents/{id}`. |
| `RenderedOutput[]` (filename, url, content_type, size_bytes) | Runs tab (download list) | Agent → Group (when part of project contribution) | Download links on output cards + context tab |
| `OutputManifest[]` (folder, version, status, files, sources) | Outputs tab (collapsible) | Agent → Project (context tab) | Context tab file browser. Output card in stream on delivery. |
| `AgentSession[]` (created_at, message_count, summary) | Sessions tab | Agent (private) → Group (replaced) | Project sessions become the meeting room. Non-project sessions stay agent-level. |
| `ProjectMembership[]` (project_slug, title, expected_contribution) | Header chips | Agent ↔ Project (bidirectional) | `expected_contribution` on participant card. Link to `/agents/{id}`. |
| `quality_score`, `quality_trend`, `avg_edit_distance` | Not displayed (exists on Agent type) | Agent (private) | PM assessment is the group-level abstraction. Trend sparkline possible on participant card (Phase 3+). |
| `origin` (user_configured/composer/etc) | Not displayed | Agent (private) | Not surfaced. |
| **"Run now" button** | Runs tab header | Agent (action) → Group (PM-mediated) | In meeting room: ask PM to `RequestContributorAdvance`, or `@agent run now`. No direct button. |
| **"Edit in chat" button** (instructions) | Instructions tab | Agent (action) | Stays at `/agents/{id}`. Meeting room doesn't modify agent identity. |
| **Settings form** (title, schedule, sources, archive) | Settings tab | Agent (action) | Stays at `/agents/{id}`. Agent config is agent-global. |

#### From Project Detail Page → Meeting Room

**Source: `ProjectDetail` type, `ProjectDetailPage` (Timeline/Outputs/Contributors tabs)**

| Field | Current Tab | Scope | Meeting Room Treatment |
|-------|-----------|-------|----------------------|
| `project.title` | Header | Project | Meeting room page header |
| `project.objective` (deliverable, audience, format, purpose) | Header (`EditableObjective`) | Project | Read-only summary in meeting room header (purpose as subtitle). Edit in Settings tab. |
| `project.contributors[]` | Contributors tab | Project → Group (participant panel) | **Participant panel.** Contributors ARE participants. |
| `project.assembly_spec` | Not displayed (fetched) | Project | Settings tab |
| `project.delivery` | Not displayed (fetched) | Project | Settings tab |
| `ProjectActivityItem[]` (event_type, metadata, summary) | Timeline tab (compact rows) | Project → Group (stream events) | Inline event cards in meeting room stream |
| TP chat messages (role, content, blocks, toolResults) | Timeline tab (merged, labeled "Thinking Partner") | ~~TP session~~ → Group (attributed) | **Attributed to PM or target agent.** Not "Thinking Partner." |
| `pm_intelligence.quality_assessment` | Contributors tab (purple panel) | PM workspace → Group (stream card) | AssessmentCard in stream + PM participant card summary |
| `pm_intelligence.briefs[agent_slug]` | Contributors tab (amber panel per contributor) | PM workspace → Group (relational) | Expandable on target contributor's participant card |
| `OutputManifest[]` | Outputs tab (collapsible list with preview) | Project | Context tab (full browse). Output card in stream on assembly. |
| `ContributionFile[]` (path, content, updated_at) | Contributors tab (per-agent expansion) | Project | Context tab (file browser grouped by agent) |
| `contributions: Record<string, string[]>` | Contributors tab (file count) | Project → Group (participant state) | Contribution count on participant card |
| Clarification UI (question, options) | Timeline tab | TP session → Group | Same UI, attributed to responding agent, not TP |
| `surface_context: { projectSlug }` | Sent on every message | TP routing | Extended with `target_agent_id` for @-mentions |

### Data That Doesn't Exist Today (New Group-Level Data)

| New data | Description | Storage | Notes |
|----------|-------------|---------|-------|
| `metadata.author_agent_id` on session messages | Who said this message | `session_messages.metadata` JSONB | Null = user, UUID = agent, `"tp"` = system |
| `metadata.author_agent_slug` on session messages | Human-readable author | `session_messages.metadata` JSONB | For frontend display without join |
| `metadata.author_role` on session messages | Agent's role at time of message | `session_messages.metadata` JSONB | For styling (PM vs contributor) |
| Participant "last spoke" | Derived from session messages | Computed (no storage) | `MAX(created_at) WHERE metadata.author_agent_id = X` |
| Participant "last contributed" | Last contribution file write | Computed from `workspace_files.updated_at` | Already available via contributions endpoint |
| Participant "currently responding" | Agent is streaming right now | Frontend ephemeral state | Not persisted — SSE stream indicator |
| Participant "health status" | Active + fresh, active + stale, paused | Derived from agent.status + PM heartbeat freshness | Computed, not stored |

### Loading Strategy

| Data | When Loaded | Lazy? |
|------|-------------|-------|
| Project detail + contributors + PM intelligence | Page mount | No |
| Activity events | Page mount | No |
| Chat history (project-scoped session, with author attribution) | Meeting Room tab mount | No |
| Participant "last spoke" | Derived from chat history on load | No |
| Participant "last contributed" + contribution count | From project detail response | No |
| Output manifests | Context tab click | Yes |
| Output detail (markdown preview) | Folder expand in Context tab | Yes |
| Contribution file contents | Participant card expand or Context tab browse | Yes |

---

## Slash Commands & Meeting Room

### Existing Commands (from `api/services/commands.py`)

Current commands and their meeting room behavior:

| Command | Current Behavior | Meeting Room Behavior | Route To |
|---------|-----------------|----------------------|----------|
| `/create` | TP guides agent creation flow | Available — creating a contributor for this project is natural | TP (system-level) |
| `/summary` | TP creates work summary agent | Available — could create a synthesis contributor | TP (system-level) |
| `/recap` | TP creates platform recap agent | Available — could add a digest contributor | TP (system-level) |
| `/prep` | TP sets up meeting prep | Available | TP (system-level) |
| `/research` | TP sets up proactive insights | Available — could add a research contributor | TP (system-level) |
| `/search` | TP searches platform content | Available — useful in project context | TP (system-level) |
| `/sync` | TP refreshes platform data | Available | TP (system-level) |
| `/memory` | TP saves to user memory | Available | TP (system-level) |
| `/web` | TP does web search | Available | TP (system-level) |

**Key insight**: All slash commands route to TP (implicit, system-level), not to agents. The `CommandPicker` autocomplete component works unchanged — it detects `/` and shows the command list. TP handles the command expansion via `system_prompt_addition`, and the response renders with system styling (not agent attribution).

### New Project-Specific Commands (Phase 2+)

| Command | Description | Routes To |
|---------|-------------|----------|
| `/assemble` | Trigger assembly now (asks PM to assemble) | PM agent |
| `/status` | Ask PM for project status summary | PM agent |
| `/budget` | Show work budget status | PM agent |
| `/plan` | Show/update work plan | PM agent |
| `/contributors` | List contributors with status | PM agent |

These are **project-scoped** — they only appear in the `CommandPicker` when the surface context is a project meeting room. They route to the PM agent, not TP, because they're domain-specific to this project.

### Command Detection in Meeting Room

```
User types:    Route:
/search ...    → TP (system command)
/assemble      → PM agent (project command)
@slack-recap   → Slack Recap agent (direct mention)
Hello          → PM agent (default, no prefix)
```

---

## Inline Components & Chat Surface Design

### Message Bubbles by Author Type

| Author | Alignment | Avatar | Name Label | Styling |
|--------|-----------|--------|------------|---------|
| **User** | Right | None (or user initial) | "You" | `bg-primary/10`, current pattern |
| **PM agent** | Left | PM badge icon | Agent title | `bg-muted`, purple accent border-left |
| **Contributor agent** | Left | Platform icon (from `getAgentPlatformIcon()`) | Agent title | `bg-muted`, role-colored accent |
| **TP (system)** | Center/subtle | System icon | "System" | `bg-muted/50`, muted text, compact — not a full bubble |

### Inline Tool Use Display

Agents in `agent_chat` mode can use primitives. When they do, the existing `InlineToolCall` component renders their tool use inline in their message bubble. The `TOOL_ICONS` map already covers all workspace primitives (`ReadWorkspace`, `SearchWorkspace`, `QueryKnowledge`, etc.).

For PM-specific tool use, add to `TOOL_ICONS`:
```typescript
// PM project execution (ADR-120)
CheckContributorFreshness: HeartPulse,
ReadProjectStatus: ClipboardCheck,
RequestContributorAdvance: FastForward,
UpdateWorkPlan: FileText,
```

### Structured Event Cards (replacing `ACTIVITY_EVENT_CONFIG` timeline items)

Current event types map to inline cards:

| Event Type | Card Component | Content |
|-----------|---------------|---------|
| `project_heartbeat` | `HeartbeatCard` | Contributor freshness summary, stale count badge |
| `project_assembled` | `AssemblyCard` | Version number, file list, download links, delivery status badge, inline markdown preview (expandable) |
| `project_quality_assessed` | `AssessmentCard` | Verdict badge, expandable markdown detail (from `PMIntelligencePanel` purple panel) |
| `project_contributor_steered` | `SteerCard` | Target agent name + link, guidance summary (from `PMIntelligencePanel` amber panel) |
| `project_contributor_advanced` | `AdvanceCard` | Target agent + reason |
| `project_escalated` | `AlertCard` | Reason, suggested action |
| `duty_promoted` | `PromotionCard` | Agent name, new duty |

These cards render at their chronological position in the stream, interleaved with chat messages. They are **not** chat bubbles — they use a distinct compact card style (bordered, icon-left, muted background) similar to how GitHub renders event entries in a PR timeline.

### PlusMenu Actions (Project Meeting Room)

The `PlusMenu` component (contextual `+` button in chat input) gets project-specific actions:

| Action | Verb | Effect |
|--------|------|--------|
| Attach image | `attach` | Opens file picker (existing behavior) |
| Run contributor | `prompt` | Prefills `@{agent} run now` — user picks which contributor |
| Check status | `prompt` | Prefills `/status` |
| View files | `show` | Switches to Context tab |
| Project settings | `show` | Switches to Settings tab |

### WorkspaceLayout Reuse

The meeting room uses `WorkspaceLayout` with:
- **Main panel** (left): Meeting room chat stream + input
- **Side panel** (right): Participant panel (collapsible, default open on desktop)

This matches the existing `agents/[id]` pattern exactly — `WorkspaceLayout` already handles responsive collapse, panel toggle, and tab switching. The participant panel replaces the 6-tab drawer with a single "Participants" view (agent cards with role badges, contribution counts, last active timestamps, links to agent detail pages).

---

## Resolved Decisions

### RD-1: Is TP a visible participant?

**No.** TP is implicit infrastructure. Rationale:
- The meeting room already has user + PM + contributors as participants
- TP's meta-cognitive role (composition, supervision) is above the project scope
- Slash commands that invoke TP capabilities surface with system styling, not as a "person"
- This avoids the confusing "who am I talking to?" problem when TP and PM both respond

TP still handles: slash commands, system-level operations (create agent, refresh platform content), and conversation routing. But it doesn't present as a chat participant.

### RD-2: How does @-mention routing work technically?

Frontend sends `target_agent_id` in the ChatRequest. Backend:
1. Validates agent is a participant in this project
2. Loads agent's ChatAgent instance with appropriate context
3. Streams response attributed to that agent
4. Stores message with `metadata.author_agent_id`

If no target specified → defaults to PM agent (project coordinator).

### RD-3: What about existing TP project sessions?

Migration: existing project session messages retain `author = "tp"` attribution. New messages route to PM by default. No data loss — old TP messages display with system styling.

### RD-4: Can agents see each other's messages in the meeting room?

**Yes, via context injection.** When an agent responds in the meeting room, the conversation history (including other agents' messages) is included in its context window. This gives agents natural awareness of the project conversation — the PM sees what a contributor said, contributors see PM directives. This is the "meta-awareness through conversation context" insight.

### RD-5: Does this replace the agent detail page chat?

**No.** The agent detail page (`/agents/{id}`) retains its own agent-scoped chat for direct user-agent conversation outside of project context. The meeting room is project-scoped — a different conversational context with different participants.

---

## Implications

### For FOUNDATIONS.md

- **Axiom 2 extension**: The meeting room transcript is a **fourth perception layer** — project-scoped conversational perception, alongside external (platform_content), internal (workspace_files/knowledge), and reflexive (user feedback). The conversation accumulates project-specific context that workspace files alone don't capture: directives, assessments delivered in context, group decisions, and the dynamic between participants. FOUNDATIONS' recursive perception diagram gains a new feedback loop.
- **Axiom 1 evolution**: Agents gain a third mode — `agent_chat` — alongside `chat` (TP) and `headless` (background). This is not a new intelligence layer; it's agents exercising their domain expertise conversationally.
- **Axiom 3 alignment**: Agents as participants reinforces the "developing entity" model — they have presence, can be addressed, respond from accumulated knowledge.
- **Axiom 4 deepening**: "Value comes from accumulated attention." The meeting room conversation is itself an accumulation — the longer a project runs, the richer the conversational context. PM that has 50 messages of history with the user and contributors has more project-specific intelligence than one reading workspace files cold.
- **Derived Principle 3 refinement**: "Agents are the write path" extends naturally — in the meeting room, agents write (respond) to the user from their domain perspective.

### For ADR-080 (Unified Agent Modes)

Extends from two modes to three:
- `chat` — TP, full meta-cognitive, all primitives
- `headless` — background generation, curated read-only + domain primitives
- `agent_chat` — conversational, domain-scoped, read-heavy + limited write

### For ADR-109 (Agent Framework)

`role` now determines not just headless prompt but also chat prompt personality. PM role gets coordinator-flavored chat; digest role gets domain-specialist chat.

### For ADR-111 (Agent Composer) and ADR-120 (Project Execution)

The Composer and PM's headless heartbeat can now optionally read the meeting room transcript as additional project context. This is not required in Phase 1 but becomes powerful as conversations accumulate:
- **Composer**: When assessing project health, can check "has the user engaged with this project recently?" by scanning the transcript.
- **PM headless heartbeat**: When deciding whether to assemble, can check if the user gave new directives in the room since last heartbeat. Today PM only reads workspace files; with the transcript, PM has conversational context too.

This is deferred to Phase 3+ to avoid coupling the headless pipeline to the meeting room prematurely.

### For Frontend Architecture

- `WorkspaceLayout` dual-panel pattern is reusable for Meeting Room (chat panel + participant sidebar)
- `InlineToolCall` and `ToolResultCard` components work directly for agent tool use display
- `CommandPicker` (slash commands) stays — routes through TP implicitly
- New component: `ParticipantPanel`, `AgentMessage` (attributed bubble), `EventCard` variants

### For the Accumulation Thesis

The meeting room conversation is a new compounding asset. Like agent memory and workspace files, it gets more valuable over time. A project with months of meeting room history contains:
- The full decision history (why the format changed, when the objective shifted)
- PM's coordination narrative (assessments, steers, escalations in context)
- User intent evolution (what they asked for initially vs what they refined toward)
- Cross-agent interaction patterns (which contributors are responsive, which need nudging)

This data is currently ephemeral (session messages with no long-term strategy). A future ADR should address **meeting room compaction and summarization** — analogous to ADR-067's session compaction for TP, but at the project scope. The summary would become another workspace file (e.g., `/projects/{slug}/meeting_summary.md`) feeding back into the recursive loop.

---

## Non-Goals

- **Agent-to-agent direct messaging**: Agents don't chat with each other. Cross-agent awareness happens through workspace reads (ADR-116) and conversation context injection.
- **Real-time multi-agent streaming**: Only one agent responds at a time. No parallel agent responses.
- **Voice/video**: Text-only meeting room.
- **Agent detail page redesign**: `/agents/{id}` stays as-is. This ADR only addresses the project surface.

---

## Phasing

| Phase | Scope | Prerequisite |
|-------|-------|-------------|
| **1** | ChatAgent class, `agent_chat` mode, routing in `chat.py` | None |
| **2** | Meeting Room frontend: attributed messages, event cards, @-mentions, participant panel | Phase 1 |
| **3** | Agent chat prompts (PM + contributor role-specific) | Phase 1 |
| **4** | Context tab (workspace browser) | None (parallel with 1-3) |
| **5** | Settings tab consolidation | Phase 2 (needs tab restructure) |

Estimated complexity: Phase 1 is the critical path — it establishes the backend capability. Phases 2-3 depend on it. Phase 4 is independent. Phase 5 is a frontend reshuffle.

---

## Related ADRs

| ADR | Relationship |
|-----|-------------|
| ADR-080 | Extended: two modes → three modes (`agent_chat`) |
| ADR-087 | Builds on: agent-scoped sessions, surface context routing |
| ADR-106 | Uses: agent workspace for chat context injection |
| ADR-109 | Extends: role determines chat prompt personality |
| ADR-116 | Leverages: cross-agent workspace reading for context |
| ADR-119 | Evolves: Phase 4b project detail page → Meeting Room |
| ADR-120 | Integrates: PM primitives available in agent_chat mode |
| ADR-123 | Absorbs: PM intelligence panels → inline stream cards |
