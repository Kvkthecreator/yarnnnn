# ADR-176: Work-First Agent Model

**Date:** 2026-04-13
**Status:** Implemented (2026-04-13)
**Authors:** KVK, Claude
**Supersedes:** ADR-140 (Agent Workforce Model — pre-scaffolded ICP roster), ADR-175 (Generic Roster Model — never implemented)
**Amends:** ADR-152 (Directory Registry — canonical domains demoted to scaffold library), ADR-138 (Agents as Work Units — agent taxonomy updated)
**Extends:** ADR-174 (Filesystem-Native Workspace), ADR-173 (Accumulation-First Execution)

---

## The Problem With the Current Model

ADR-140 established a pre-scaffolded roster of 10 agents — 5 domain-stewards named after business functions (Competitive Intelligence, Market Research, Business Development, Operations, Marketing & Creative) — created at signup for every user.

Two compounding errors:

**Error 1: Agent-first framing.** The model asked users to think about "who to hire" before knowing "what they want done." This inverts the natural human decision sequence. Nobody staffs a team before defining the project. The pre-scaffolded roster forced every new user to encounter five opinionated agents before they'd expressed a single work intent. The agents answered a question the user hadn't asked.

**Error 2: ICP specificity baked into the universal layer.** "Competitive Intelligence" and "Market Research" encode a specific user archetype — a startup founder doing broad strategic work. An agency owner, an investor, a product manager, a researcher — none of them recognize their work in those names. The roster looked like it was built for someone else, because it was.

The deeper error underneath both: **domain ownership was conflated with role specialization.** A "Market Research" agent was simultaneously responsible for knowing things (the domain) and being capable of doing things (research, synthesis, visual production). These are orthogonal. An agent's domain is what work they're assigned. An agent's role is how they contribute to that work. Collapsing them created agents that were too wide in capability and too narrow in applicability.

---

## The Axiom

**Work exists first. Agents serve work.**

A user's first question is never "what kind of agent do I want?" It is "what am I trying to accomplish?" The system must answer that question before introducing any agent concept. Agents are the how. Work is the what. The what comes first, always.

This axiom has consequences at every layer:

- Onboarding begins with work intent, not agent configuration
- Agents are assembled for tasks, not assigned tasks after creation
- Domain context directories are created when work demands them, not pre-scaffolded at signup
- The agent roster is a set of universal specialists, not a set of ICP-specific personas

---

## Decision 1: Universal Specialist Roster

Six specialist roles replace the current 10-agent ICP roster. These roles are universal — correct for any user, any industry, any workflow — because they describe *how* agents contribute, not *what domain* they work in.

### The Six Roles

| Role | Internal key | What they do | What they never do |
|------|-------------|-------------|-------------------|
| **Researcher** | `researcher` | Web search, investigate topics, find and evaluate sources, build knowledge files from primary research | Write final deliverables, generate visual assets |
| **Analyst** | `analyst` | Read accumulated context, identify patterns, synthesize meaning across sources and time, produce insight summaries | Primary research, image/chart generation |
| **Writer** | `writer` | Draft deliverables from synthesized context, edit for audience and tone, produce polished final output | Research, analysis, visual production |
| **Tracker** | `tracker` | Monitor signals, maintain entity profiles, log temporal changes, watch platforms and sources for updates | Analysis, writing, production |
| **Designer** | `designer` | Generate images, charts, diagrams, visual assets via RuntimeDispatch | Research, writing, analysis |
| **Thinking Partner** | `thinking_partner` | Orchestrate teams, manage work, converse with user, coordinate multi-agent execution | Specialized domain work itself |

**Naming rationale:** Each name passes the instinct test — a non-technical user reads the name and immediately knows what that agent does to their work. Researcher finds things. Analyst makes sense of things. Writer produces documents. Tracker watches things. Designer makes visuals. No explanation required.

**Why not Producer, Coordinator, Domain Steward?** These names fail the instinct test. "Producer" maps to music and film. "Coordinator" is corporate-abstract. "Domain Steward" requires a definition before it's useful. Names that require a glossary are wrong names.

### The Hospital Principle (Why the Roster Is Fixed)

The specialist roster is fixed at signup — same six roles for every workspace — and cannot be configured by the user. This is deliberate, not a limitation.

Every hospital surgery has a mandatory team composition: surgeon, anesthesiologist, scrub nurse. This minimum team is non-negotiable because it reflects what the work requires, not what a particular patient prefers. The team composition is determined by the procedure, not by the patient's opinion about staffing.

The same principle applies here. A research task requires a Researcher. A monitoring task requires a Tracker. These aren't preferences — they're what the work demands. Letting users configure the roster before they've expressed work intent is like letting patients design surgical teams. The expertise to make that decision sits with the system, not the user.

This also future-proofs the model. When a new work pattern emerges that the current six roles can't serve, a new role is added to the roster. The roster grows from observed work patterns, not from ICP assumptions made at design time.

### Roster at Signup

| Agent | Role | Created at | Notes |
|-------|------|-----------|-------|
| Thinking Partner | `thinking_partner` | Signup | Meta-cognitive, orchestration, TP. ADR-164. |
| Researcher | `researcher` | Signup | Universal — domain assigned by task |
| Analyst | `analyst` | Signup | Universal — reads all context domains |
| Writer | `writer` | Signup | Universal — produces deliverables |
| Tracker | `tracker` | Signup | Universal — monitors, maintains profiles |
| Designer | `designer` | Signup | Universal — visual production only |
| Slack Bot | `slack_bot` | Signup, activates on connect | Platform-bot, temporal context |
| Notion Bot | `notion_bot` | Signup, activates on connect | Platform-bot, temporal context |
| GitHub Bot | `github_bot` | Signup, activates on connect | Platform-bot, temporal context |

9 agents at signup. No ICP-specific agents. No domain names in agent identities.

**The ICP-specific templates (competitive_intel, market_research, business_dev, operations, marketing) are deleted from AGENT_TEMPLATES.** They are not demoted to a scaffold library — they are removed. Their methodology playbooks are redistributed into the universal specialist templates. The competitive intelligence *methodology* lives in the Researcher's playbook. The market research *output format* lives in the Writer's playbook. Craft is preserved; ICP naming is removed.

---

## Decision 2: Team Composition — TP Owns Full Judgment, Registry Provides Defaults

TP has full authority over team composition for every task. The registry provides **suggested defaults** per work intent — inputs to TP's reasoning, not constraints on its output.

### Why Full TP Judgment (Not a Registry Floor)

**Registry floor** was considered and rejected. A non-removable floor trades flexibility for testability, but creates the wrong failure mode: a reactive one-off task gets a full Researcher + Analyst + Writer team because the registry says so, even though TP knows the work only needs a Tracker. The registry override produces a worse team than TP's judgment would. Code constraints that make agents dumber are wrong constraints.

**The hospital analogy applies differently here:** The hospital's mandatory team composition is non-negotiable because liability and patient safety require it — the cost of a wrong omission is catastrophic and irreversible. Task team composition has no equivalent downside. If TP under-staffs a team, the output is worse — observable, correctable, and the user can ask TP to add a specialist. That feedback loop is the right protection mechanism.

**The protection against composition mistakes** is not a code gate. It is:
1. TP's prompt quality — documented defaults give TP a strong starting point
2. Visibility — the `## Team` section in TASK.md is readable by the user
3. Correctability — the user can ask TP to change the team at any time

TP reads the registry defaults, applies judgment for this specific work intent and context, and documents its reasoning. The default is an informed suggestion. TP's judgment is the decision.

### Registry Defaults by Work Intent

Work intent is determined by two axes in the data model: `mode` (recurring/goal/reactive) and `output_kind` (accumulates_context/produces_deliverable/external_action/system_maintenance).

| Work Intent | Mode | Output Kind | Registry Default | When TP Deviates |
|------------|------|-------------|-----------------|-----------------|
| Monitor & inform | recurring | accumulates_context | Tracker + Analyst | Drop Analyst if domain is simple/narrow; add Researcher if domain needs active investigation |
| Recurring report | recurring | produces_deliverable | Researcher + Analyst + Writer | Add Designer if visual output needed; drop Analyst if single-source synthesis |
| One-time deliverable | goal | produces_deliverable | Researcher + Writer | Add Analyst for multi-domain synthesis; add Designer if presentation format |
| Platform digest | recurring | accumulates_context | Tracker (bot) | Add Analyst if cross-channel synthesis needed |
| Reactive response | reactive | external_action | Tracker + Writer | Simplify to Writer only if trigger is well-defined |
| Research task | goal | accumulates_context | Researcher | Add Analyst if synthesis is the primary output |

**TP's composition criteria (applied to every task):**
- Does the work require finding new information? → Researcher
- Does the work require synthesizing across multiple sources or time periods? → Analyst
- Does the work require a polished deliverable for an audience? → Writer
- Does the work require ongoing monitoring or signal capture? → Tracker
- Does the work require visual assets (charts, images, diagrams)? → Designer
- Is the scope narrow enough that a specialist is redundant? → remove them

TP writes its team reasoning in one sentence in the `## Team` section of TASK.md alongside the team list. This makes the decision observable and correctable.

---

## Decision 3: Work-First Onboarding — Two Entry Points

Onboarding is not a configuration step. It is the user's first work session. Two equivalent entry points:

**Entry 1: "I want this output" (reverse-engineering from deliverable)**

> User: "I want a weekly competitive briefing"
> System: recurring, produces_deliverable → minimum team: Researcher + Analyst + Writer
> TP: infers domain → creates `/workspace/context/competitors/` → schedules weekly
> First run executes immediately

**Entry 2: "Here's my context" (forward from what the user knows)**

> User: uploads pitch deck or pastes company description
> System: infers work intents from content → suggests tasks → user confirms
> Same team assembly and domain creation follows

Both paths converge on the same place: a task with a team, a schedule, and a context domain that grows with every run. The user configured nothing except what they want done.

**This onboarding principle applies to all future task creation, not just first-session.** The mechanism for creating a new task mid-workspace is identical to onboarding: user states work intent, system resolves team and domain, execution begins. There is no special onboarding mode — just the first instance of a universal pattern.

---

## Decision 4: Capability Split — Accumulation vs. Production

Agent capabilities are divided by phase, not by agent identity. This resolves the fundamental confusion in the prior model where a single agent had both research capabilities and visual production capabilities.

### Accumulation Phase (domain agents: Researcher, Analyst, Writer, Tracker)

```
web_search          — find things on the internet
read_workspace      — read from /workspace/context/ and task workspace
search_knowledge    — semantic + BM25 search over accumulated context
read_slack          — read from Slack bot context
read_notion         — read from Notion bot context
read_github         — read from GitHub bot context
investigate         — multi-step research loop
produce_markdown    — write structured markdown for context files and drafts
```

No visual production capabilities. No RuntimeDispatch calls. These agents accumulate and write.

### Production Phase (Designer + TP via RuntimeDispatch)

```
chart               — generate charts from data
mermaid             — generate diagrams
image               — generate images via AI image generation
video_render        — generate video summaries
compose_html        — compose HTML deliverables from markdown + assets
```

Designer holds these capabilities as a specialist. TP can call RuntimeDispatch directly when orchestrating output composition (assembling a deliverable from accumulated context + produced assets).

**Why this separation matters:** A Researcher assigned to a competitors task should not also be generating images. These are fundamentally different cognitive modes — accumulation (build knowledge over time) vs. production (create an artifact for delivery). Collapsing them creates agents that are hard to reason about and harder to test. Clean separation means: if a deliverable needs a chart, TP adds Designer to the team. The Researcher's quality is measured by the knowledge they accumulate, not by the visuals they generate.

**Writer produces_markdown only during the accumulation phase.** The final HTML composition is TP's job via compose_html. The Writer produces the prose; TP assembles the deliverable.

---

## Decision 5: Workspace Directory Model — Knowledge by Subject, Created by Work

### The Two-Namespace Rule

The workspace has exactly two knowledge namespaces with different lifecycles:

```
/workspace/context/{domain}/     ← accumulated intelligence
                                   grows indefinitely, shared across all tasks,
                                   structured by subject, maintained by agents

/tasks/{slug}/outputs/            ← task-produced deliverables
                                   versioned, dated, task-scoped,
                                   read by delivery layer and TP
```

These must never be mixed. Context domain files are knowledge. Task output files are deliverables. A blog post draft is a task output (it gets delivered). The research that informed the blog post is context (it accumulates).

### Domain Directories — Created by Work, Not Pre-Scaffolded

Context domains are created when work first demands them. At signup, only two things exist in `/workspace/context/`:

1. `signals/` — the cross-domain temporal log. Present from day one because signals can arrive before any specific domain exists. It is the universal inbox for temporal observations.
2. Platform bot directories (`slack/`, `notion/`, `github/`) — created when the respective platform connects.

Everything else — `competitors/`, `market/`, `relationships/`, `clients/`, `portfolio/`, any domain — is created by TP when the first task that needs it is created. The domain name comes from the user's language, not from a pre-declared registry key.

**The directory registry (ADR-152)** retains its role as a scaffold library: it provides entity structure templates (what files to create inside a domain), synthesis file conventions, and tracker patterns for known domain archetypes. When TP creates a new domain, it checks the registry for a matching archetype and uses its template if found. If no match, TP creates the domain with a minimal `landscape.md` and lets structure emerge from the work.

### Stress Test: Hard Scenarios

**Scenario 1: Concurrent writes to the same context file**

Two tasks both update `/workspace/context/competitors/openai/profile.md` in the same hour. Current behavior: last-write-wins via database upsert. The first write is silently destroyed.

**Mitigation in this ADR:** Context domain files follow strict write-mode discipline enforced by conventions:

- **Entity profile files** (`profile.md`, `strategy.md`, `product.md`): overwrite — these are "current best state" files. Only one task should update an entity profile per cycle. TP's team composition prevents two tasks from being assigned the same entity tracking work simultaneously.
- **Signal files** (`signals.md`, `_tracker.md`): append-newest-first — temporal logs. Concurrent appends may interleave but don't destroy prior content.
- **Synthesis files** (`landscape.md`, `_synthesis.md`): overwrite — full rewrite each cycle by the Analyst. Only one Analyst per workspace; concurrent synthesis is not expected.

The deeper protection: task scheduling is sequential per domain. If two tasks both read `context_reads: ["competitors"]`, the scheduler does not run them concurrently. This is not yet enforced in code — it is a scheduling discipline to be added as a gate in the unified scheduler.

**Scenario 2: Multiple tasks reading the same context domain**

A `track-competitors` task and a `competitive-brief` task both read `/workspace/context/competitors/`. This is correct and expected — sharing is the point. The accumulation model only works if multiple tasks can read the same context. Reads are never destructive.

**Scenario 3: File versioning and recovery**

Context domain entity files currently have no version history (unlike `AGENT.md` and `memory/*.md` which archive to `/history/`). An overwritten `openai/profile.md` is unrecoverable.

**Resolution:** Extend the archive-to-history mechanism to entity profile files in context domains. Before any overwrite of a `profile.md`, `strategy.md`, or `product.md`, the prior version is archived to `/workspace/context/{domain}/{entity}/history/profile-v{N}.md`. Cap at 5 versions. This brings context entity files into alignment with the existing agent workspace versioning convention (ADR-119 Phase 3).

**Scenario 4: Domain name collision — user creates "clients" domain, registry has "relationships"**

TP creates `/workspace/context/clients/` from user work intent. The registry has a `relationships` archetype that is semantically similar. These are two different domains — do not merge them. Domain names come from user language. The registry archetype is available as a structural template (entity_structure, synthesis_file) but the domain key is whatever TP named it. No aliasing, no merging.

**Scenario 5: Stale knowledge / dirty context**

A `competitors/openai/profile.md` written in January may be factually wrong by April. No current mechanism detects this. This is the "workspace rot" concern documented in ADR-174.

**Resolution in this ADR:** Each entity profile file gets a `<!-- last-researched: {date} -->` HTML comment in the frontmatter section. The Tracker's playbook requires updating this timestamp on every write. The pipeline can surface "researched >90 days ago" as a staleness flag in the generation brief. This is a lightweight signal, not a full freshness scoring system — full freshness scoring is a future ADR.

**Scenario 6: Deduplication — same content written twice**

Current behavior: identical content still triggers a write, version increment, and embedding regeneration. Wasteful at scale.

**Resolution:** Before writing to a context domain file, compare content hash against current row. If identical, skip the write entirely. This is a cheap SHA-256 comparison in the write path. Save the embedding call, the version increment, the DB write.

**Scenario 7: Multiple users (future)**

Current model: `workspace_files` is scoped by `user_id`. Each user's workspace is fully isolated. No cross-user context sharing exists or is planned.

When multi-user workspaces arrive (teams), the correct model is: context domains are workspace-scoped (not user-scoped), with write attribution (`written_by_agent_slug`) on each file. The `user_id` column becomes `workspace_id`. This is a schema migration, not an architectural change — the directory model above already supports it because domain directories are subject-organized, not user-organized.

**Scenario 8: Embedding staleness after overwrite**

A context file gets overwritten → new content has no embedding until the async job completes. During that window, semantic search returns stale results for that file.

**Resolution:** This is acceptable given the fire-and-forget architecture (ADR-174 Phase 2). The window is typically <5 seconds. For cases where immediate semantic availability is required, the write can set `embedding = NULL` synchronously and trigger a priority re-embedding. In practice, context files are written by background tasks, not in real-time user sessions, so the staleness window is not user-visible.

---

## Architecture Integration

### Relationship to Existing ADRs

| ADR | Relationship |
|-----|-------------|
| ADR-138 (Agents as Work Units) | Amended — agent taxonomy updated from 8 ICP types to 6 universal specialist roles. The three-axis model (identity/capabilities/tasks) preserved. |
| ADR-140 (Agent Workforce Model) | Superseded — pre-scaffolded ICP domain-steward roster replaced by universal specialist roster. |
| ADR-141 (Unified Execution Architecture) | Compatible — task pipeline unchanged. Team composition is expressed in TASK.md `## Team` section, parsed at execution time. |
| ADR-149 (Task Lifecycle Architecture) | Extended — `## Team` section added to TASK.md schema. DELIVERABLE.md and steering.md unchanged. |
| ADR-151 (Shared Context Domains) | Amended — canonical domains are not pre-declared. Domain keys are user-language names created by work. Registry provides structural templates, not scope enforcement. |
| ADR-152 (Directory Registry) | Amended — canonical domain entries demoted from "pre-scaffolded at signup" to "scaffold library archetype." `scaffold_all_directories()` simplified: creates `signals/` only at signup. |
| ADR-174 (Filesystem-Native Workspace) | Extended — entity profile versioning added to context domain files. Content hash dedup added to write path. Staleness timestamp convention added to entity profiles. |
| ADR-175 (Generic Roster Model) | Superseded before implementation. The specialist roster model is a deeper solution to the same problem ADR-175 was attempting to solve. |

### What Does Not Change

**The task data model.** `tasks` table schema, TASK.md format, `mode` and `output_kind` fields, task pipeline execution — all unchanged. `## Team` is an additive section.

**The primitives matrix (ADR-168).** ManageAgent, ManageTask, WriteFile, ReadFile, QueryKnowledge — no changes to primitive names or signatures.

**Platform bots.** Slack Bot, Notion Bot, GitHub Bot own temporal context directories. Unchanged.

**The compose substrate (ADR-170).** `sys_manifest.json`, `page_structure`, HTML assembly — unchanged.

**The accumulation-first principle (ADR-173).** Unchanged and reinforced: the specialist roster makes the separation between accumulation (Researcher, Tracker, Analyst) and production (Designer, Writer) explicit at the agent level.

---

## Implementation Phases

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | Implemented | `AGENT_TEMPLATES` rewritten: 5 ICP domain-steward templates deleted, 6 universal specialist templates added. `DEFAULT_ROSTER` updated: 9 agents (6 specialists + 3 bots). Capability sets split: accumulation caps for Researcher/Analyst/Tracker, production caps for Designer only. Methodology playbooks redistributed. |
| Phase 2 | Implemented | `TASK_TYPES` updated: `registry_default_team` field added per task type (list of specialist role keys). `parse_task_md()` updated to parse `## Team` section. Task creation writes team to TASK.md. **2026-04-14 fix:** `build_task_md_from_type()` gains `team_override` param — TP's composition judgment now wires into `## Process` execution steps (not only `## Team` record). `_handle_create()` passes `team_override` through. `track-market` schedule corrected `monthly` → `weekly`. |
| Phase 3 | Implemented | TP prompt updated: work-first framing, team composition guidance, specialist capability discipline. All ICP domain-steward references removed from TP-facing prompts (base.py, tools.py, onboarding.py, behaviors.py). |
| Phase 4 | Implemented | Directory registry: `scaffold_all_directories()` simplified to `signals/` only at signup. `scaffold_context_domain()` added for on-demand domain creation by TP. Entity profile versioning for `profile.md`/`strategy.md`/`product.md` in WriteFile context path. Content hash SHA-256 dedup on context write path. Staleness timestamp instruction in Tracker default_instructions and playbook. |
| Phase 5 | Implemented | Clean-slate migration: 10 ICP agent rows deleted (competitive_intel, market_research, business_dev, operations, marketing × 2 users). ICP agent workspace files deleted. ICP context domain files deleted (competitors, market, relationships, projects, content_research). New specialist agents scaffolded for both test workspaces (researcher, analyst, writer, tracker, designer × 2 users). Migration 146: agents_role_check constraint updated to include tracker and designer. |

---

## Consequences

**Positive:**
- Any user — regardless of industry or ICP — gets a roster that serves their work. No "built for someone else" feeling.
- Work intent drives everything. Users never configure agents; they state what they want done.
- Capability split (accumulation vs. production) eliminates the agent identity confusion. Roles are narrow, testable, observable.
- Domain directories emerge from actual work. No empty `/workspace/context/market/` folder for a user who never does market research.
- The hospital principle makes the roster stable and explainable: "you always get these six roles because they're what every type of knowledge work requires."

**Constraints:**
- Phase 1 requires a clean-slate migration (test data only — acceptable pre-launch).
- TP's additive judgment on team composition must be well-prompted. The registry floor is testable; the additive layer is prompt-dependent. Prompt quality gates are required before Phase 3 ships.
- The `## Team` section in TASK.md is a new parsing requirement. Backward compat: tasks without `## Team` fall back to single-agent execution (current behavior).
- Onboarding is now a conversation, not a form. The quality of the onboarding experience depends on TP's work-intent inference. This must be evaluated with real user sessions before treating it as complete.

**Deferred:**
- Full freshness scoring for context domain files (staleness detection beyond the timestamp convention) — future ADR.
- Multi-user workspace support (workspace_id replacing user_id) — future ADR.
- Sequential scheduling enforcement for tasks sharing a context domain — added to unified scheduler as a future gate.
- Designer agent's visual asset management conventions (how assets are named, where they land, how they're referenced across tasks) — to be hardened alongside Phase 4 implementation.
