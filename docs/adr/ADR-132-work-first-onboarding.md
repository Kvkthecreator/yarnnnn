# ADR-132: Work-First Onboarding & Project Scaffolding

> **Status**: Partially Implemented. Infrastructure ready (charter files, file upload, PM handoff). **Onboarding flow itself needs redesign** — inference not firing, template-only charter content, single/multi step is wrong mental model. See `docs/design/ONBOARDING-REDESIGN.md` for issue list + proposed fix.
> **Date**: 2026-03-23
> **Authors**: KVK, Claude
> **Extends**: ADR-122 (Project Type Registry), ADR-130 (Agent Capability Substrate)
> **Supersedes**: ADR-110 (Onboarding Bootstrap — platform-first scaffolding), ADR-113 (Auto Source Selection — onboarding path)
> **Affects**: ADR-057 (Streamlined Onboarding), docs/design/USER_FLOW_ONBOARDING_V4.md

---

## Context

### The current onboarding model is platform-first

Today, YARNNN's onboarding asks users to connect a platform (Slack/Notion), then auto-scaffolds a generic digest project. The flow:

```
Sign up → Orchestrator → Connect Slack → Auto-sync → scaffold_project("slack_digest") → Done
```

This produces a "Slack Digest" project with one digest agent watching all auto-selected channels. The user gets a generic recap of everything, scoped by platform — not by what they actually care about.

### Why platform-first fails for solo founders

A solo founder who connects Slack has channels for 3 different clients, internal ops, and product development. A single "Slack Digest" agent watching everything produces noise, not value. What the founder actually needs:

- A project per client (scoped to that client's channels + Notion pages)
- An ops monitor (watching #hiring, #finance, #ops)
- A product development tracker (watching #engineering, #product, relevant Notion specs)

The platform connection is a data source. The **work description** is what determines project structure. We have the data source first and the work description never.

### What we actually need to know

The single most valuable input at onboarding is: **"What are you working on?"**

This question directly determines:
- What projects to scaffold (each work unit = a project)
- What agents to create (derived from work type)
- What platforms matter (derived, not asked)
- What cadence makes sense (derived from work type, not user preference)
- How to scope platform sources when they connect (channels/pages mapped to work units)

Role, cadence preferences, focus areas, and platform configuration are all **derived** from the work description. They should not be asked.

### Axiomatic grounding

**Axiom 6** (Autonomy is the product direction): "Sign up, connect, watch it work for you." The system must know *what* to work on before it can work autonomously. A platform connection without work context produces autonomous noise.

**Axiom 1** (Two layers of intelligence): TP owns attention allocation. The user's work description tells TP what attention to allocate. Each piece of work becomes an agent's domain.

**Axiom 3** (Agents are developing entities): Agent = Type + Instructions. The work description determines both — "monitor Client X's Slack for escalations" implies monitor type + client-X-scoped instructions.

**Axiom 4** (Accumulated attention): Value compounds when attention is persistent and scoped. Right scoping comes from understanding the work structure, not from platform topology.

---

## Decision

### 1. Structured work collection is the primary onboarding input

A new user is guided through a two-step structured onboarding — not a free-text field, not a wizard. The page loads after signup (before the Orchestrator), is completable in under 60 seconds, and redirects to `/orchestrator` on completion.

#### Step 1: Work structure

The user is asked: **"How is your work structured?"**

Two options (cards, not a dropdown):

| Option | Description | What it implies |
|---|---|---|
| **"I focus on one thing"** | Single product, single company, single domain | 1 project, potentially multiple agents by function |
| **"I juggle multiple things"** | Multiple clients, multiple projects, separate workstreams | N projects, each with its own scoped agents |

This is the fork that resolves the persistent ambiguity: is this user building one deep workspace or managing several parallel scopes?

#### Step 2: Define work scopes

**If single-focus**: One input card:
```
┌─────────────────────────────────────┐
│ What are you working on?            │
│ ┌─────────────────────────────────┐ │
│ │ e.g., "My SaaS startup —       │ │
│ │ product dev and team ops"       │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

**If multi-scope**: Repeatable input cards (add more):
```
┌─────────────────────────────────────┐
│ Name each one                       │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ e.g., "Acme Corp project"      │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ e.g., "Sales pipeline"         │ │
│ └─────────────────────────────────┘ │
│                                     │
│ [+ Add another]                     │
└─────────────────────────────────────┘
```

The placeholder examples rotate or vary to reflect diverse users: "Acme Corp project", "Sales pipeline", "Product development", "Marketing", "Client onboarding", "Fundraising". No prescribed format — the user names their scopes however they think about them.

Each scope becomes a work unit. No LLM parsing needed — the structure is explicit from user input.

#### Additional fields (both paths)

| Field | Type | Purpose |
|---|---|---|
| **Name** | Text | Pre-filled from auth if available. Stored in `/memory/MEMORY.md`. |

**What is NOT collected**: Role, cadence, platform preferences, delivery format. These are all derived downstream — cadence from work type, delivery from project type, platforms from connection.

**Why structured input, not free text**: A free-text field ("What are you working on?") optimizes for the articulate user but fails for the user who has a clear mental model but needs structure to express it. The two-step structured approach captures the fundamental decision (single vs. multi-scope) explicitly, then collects discrete work units without requiring the user to compose a paragraph that an LLM must parse. Each scope entry maps 1:1 to a project — no ambiguity, no extraction errors.

**Why a dedicated page, not orchestrator cards**: The work structure decision has qualitative downstream implications — it determines project count, agent scoping, and the entire first-run experience. Collecting it in a structured input (dedicated page) ensures reliability and completeness. The page is 2 steps, not a wizard — it's faster than typing a chat message and produces better data.

### 2. Work scopes become work units directly

Each scope entry from onboarding becomes a **work unit** — a discrete scope of recurring attention that maps 1:1 to a project. No LLM extraction step needed.

**Single-focus examples:**

| User enters | Work units | Project scaffolding |
|---|---|---|
| "My SaaS startup — product dev and team ops" | 1 work unit (the startup) | 1 project with digest + monitor agents |
| "Marketing agency — campaigns and client reporting" | 1 work unit (the agency) | 1 project with monitoring + synthesis agents |

**Multi-scope examples:**

| User enters | Work units | Project scaffolding |
|---|---|---|
| "Acme Corp project" / "BetaCo project" / "Product development" | 3 work units | 3 projects, each scoped to its domain |
| "Sales pipeline" / "Marketing" / "Hiring" | 3 work units | 3 function projects |
| "Q2 board deck" / "Competitor analysis" / "Weekly team updates" | 3 work units | 2 bounded + 1 persistent project |

Work units are stored in `/memory/WORK.md` (workspace filesystem, agent-accessible). Format:

```markdown
# Work Structure

structure: single | multi

## Work Units

- **{scope_name}**: {description}
  - lifecycle: persistent | bounded
  - implied_platforms: [slack, notion] (derived)
  - project_slug: {slug} (populated after scaffolding)
```

The system determines work unit lifecycle (persistent vs. bounded) from the scope name using lightweight heuristics or a single Haiku call. This selects the project type from the registry (`workspace` for persistent, `bounded_deliverable` for finite work). The work units themselves come directly from user input — no LLM parsing needed for extraction, only for lifecycle classification.

### 3. Work units carry implicit lifecycle

The persistent-vs-bounded tension resolves naturally from the work description:

| Work scope pattern | Implied lifecycle | PM model |
|---|---|---|
| "Acme Corp project" | **Persistent** — ongoing relationship/workstream | Full PM (coordination, assembly, delivery) |
| "Marketing" / "Sales pipeline" | **Persistent** — function is ongoing | Full PM |
| "Q2 board deck" | **Bounded** — deliverable with end state | Lightweight PM (task tracking, dissolves on completion) |
| "Competitor analysis" | **Ambiguous** — default persistent, user can correct | Full PM, downgradeable |

Lifecycle is a property of the **project**, inferred from the work description. The user does not configure it. The system infers, the user corrects if wrong.

### 4. Project type registry evolves from platform-first to work-first

The current `PROJECT_TYPE_REGISTRY` has 4 types: `slack_digest`, `notion_digest`, `cross_platform_synthesis`, `custom`. These are platform-scoped or generic.

The registry evolves to include **work-scoped types**:

```python
PROJECT_TYPE_REGISTRY = {
    # ── Work-scoped types (new — scaffolded from work scopes) ──

    "workspace": {
        "display_name": "Workspace",
        "category": "work",
        "platform": None,
        "lifecycle": "persistent",
        "description": "Recurring monitoring, tracking, and reporting for an ongoing workstream.",
        "objective_template": {
            "deliverable": "Weekly {scope_name} update",
            "audience": "You",
            "format": "email",
            "purpose": "Stay on top of {scope_name} activity and surface what needs attention",
        },
        "contributors_template": [
            {
                "title_template": "{scope_name} Digest",
                "role": "digest",
                "scope": "cross_platform",
                "frequency": "daily",
                "sources_from": "work_unit",  # scoped to work unit's platform sources
            },
        ],
        "pm": True,
        "assembly_spec": "Coordinate {scope_name} updates and deliver summary.",
        "delivery_default": {"platform": "email"},
    },

    "bounded_deliverable": {
        "display_name": "Deliverable",
        "category": "work",
        "platform": None,
        "lifecycle": "bounded",
        "description": "A specific deliverable with a defined end state.",
        "objective_template": None,  # fully specified by work unit
        "contributors_template": [
            {
                "title_template": "{scope_name} Agent",
                "role": "research",  # or synthesize — classified from description
                "scope": "knowledge",
                "frequency": "on_demand",
                "sources_from": "work_unit",
            },
        ],
        "pm": True,
        "pm_lightweight": True,  # dissolves on completion
        "assembly_spec": "Produce {scope_name} and deliver when ready.",
        "delivery_default": {"platform": "email"},
    },

    # ── Platform digest types (preserved — bootstrap fallback) ──

    "slack_digest": { ... },   # unchanged, used when no work description
    "notion_digest": { ... },  # unchanged, used when no work description

    # ── Legacy ──
    "cross_platform_synthesis": { ... },  # subsumed by workspace type
    "custom": { ... },  # preserved for TP-driven creation
}
```

The registry consolidates to two work-scoped types: `workspace` (persistent, ongoing) and `bounded_deliverable` (finite, dissolves on completion). The previous `client_workspace` and `function_workspace` distinction was a false taxonomy — the user's scope name ("Acme Corp project" vs. "Marketing") already carries the identity. The system doesn't need to classify *what kind* of persistent work it is — it just needs to know it's persistent.

**Key**: `sources_from: "work_unit"` is the new source resolution mode. When a work unit is named "Acme Corp project" and the user later connects Slack, the system maps relevant Slack channels to this project's agents. Platform sources become scoped by work context, not platform topology.

### 5. Bootstrap evolves from platform-first to work-aware

**If work description exists** (onboarding completed):
- Platform connection enriches existing projects — Slack channels get mapped to work units
- `maybe_bootstrap_project()` checks for work units that need platform sources
- Each work unit project gets its agents' sources populated with matching channels/pages
- No generic "Slack Digest" project created — the work-scoped projects already exist

**If no work description** (user skips onboarding):
- Falls back to current behavior — generic platform digest project
- When user later provides work description, projects get rescoped

This is a soft migration — existing behavior preserved as fallback, new behavior activated by work description presence.

### 6. Onboarding page design

A new route: `/onboarding` — shown once after signup, before first Orchestrator visit.

**Step 1: Work structure**

```
┌──────────────────────────────────────────────┐
│                                              │
│  Welcome to YARNNN                           │
│                                              │
│  How is your work structured?                │
│                                              │
│  ┌──────────────────┐  ┌──────────────────┐  │
│  │                  │  │                  │  │
│  │  I focus on      │  │  I juggle        │  │
│  │  one thing       │  │  multiple things │  │
│  │                  │  │                  │  │
│  │  One product,    │  │  Multiple        │  │
│  │  one company,    │  │  clients,        │  │
│  │  one domain      │  │  projects, or    │  │
│  │                  │  │  workstreams     │  │
│  └──────────────────┘  └──────────────────┘  │
│                                              │
│  ─── or ───                                  │
│                                              │
│  Skip and explore on your own                │
│                                              │
└──────────────────────────────────────────────┘
```

**Step 2a: Single-focus**

```
┌──────────────────────────────────────────────┐
│                                              │
│  What are you working on?                    │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │ e.g., "My SaaS startup — product dev  │  │
│  │ and team coordination"                 │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  Your name                                   │
│  ┌────────────────────────────────────────┐  │
│  │                                        │  │
│  └────────────────────────────────────────┘  │
│                                              │
│           [Get Started →]                    │
│                                              │
└──────────────────────────────────────────────┘
```

**Step 2b: Multi-scope**

```
┌──────────────────────────────────────────────┐
│                                              │
│  What are the things you're juggling?        │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │ e.g., "Acme Corp project"             │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │ e.g., "Sales pipeline"                │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  [+ Add another]                             │
│                                              │
│  Your name                                   │
│  ┌────────────────────────────────────────┐  │
│  │                                        │  │
│  └────────────────────────────────────────┘  │
│                                              │
│           [Get Started →]                    │
│                                              │
└──────────────────────────────────────────────┘
```

**On submit**:
1. Store work structure + scopes + name in `/memory/WORK.md` and `/memory/MEMORY.md`
2. Each scope entry becomes a work unit directly (no LLM parsing needed for extraction)
3. Classify each work unit's lifecycle (persistent vs. bounded) — lightweight heuristics or single Haiku call
4. Scaffold projects for each work unit (deterministic, via `scaffold_project()`)
5. Redirect to `/orchestrator` with projects visible in panel
6. Orchestrator shows informed action cards: "Connect Slack to enrich your {project_name} agents"

**On skip**:
- Redirect to `/orchestrator` with current empty state (platform connect cards)
- Work description can be provided later via chat ("I'm working on...")
- TP/Composer can prompt for work description during first conversation

### 7. Orchestrator empty state evolves

**With work description** (projects exist):
- Projects panel shows scaffolded projects
- Action cards shift to: "Connect Slack to power your agents" / "Connect Notion"
- Chat input hint: "Talk to your orchestrator — refine projects, ask questions, or create new work"

**Without work description** (skipped onboarding):
- Current empty state preserved (platform connect buttons + "New Project" card)
- Additional subtle prompt: "Tell me what you're working on and I'll set up the right team"

### 8. Data model

**No new tables.** Work state stored in workspace filesystem:

- `/memory/WORK.md` — living work index (see section 9)
- `/memory/MEMORY.md` — name, timezone (existing, extended with work context summary)

**New fields on `PROJECT_TYPE_REGISTRY` entries:**
- `lifecycle`: `"persistent" | "bounded"` — inferred from work scope
- `objective_template` / `contributors_template`: Templatized versions for work-scoped types (vs. static for platform types)
- `sources_from: "work_unit"`: New source resolution mode (maps platform sources by work scope context)
- `pm_lightweight`: Boolean — bounded projects get a simpler PM that dissolves on completion

**New field on agent `type_config` JSONB:**
- `work_unit`: Reference to the work scope this agent serves (for source mapping on platform connection)

### 9. `/memory/WORK.md` is a living work index

`/memory/WORK.md` is not onboarding output that sits unused after project creation. It is the **canonical index of the user's work landscape** — the single file that answers "what is this user working on right now?"

#### Format

```markdown
# Work Structure

structure: single | multi

## Work Units

- **Acme Corp project**
  - lifecycle: persistent
  - project_slug: acme-corp-project
  - status: active

- **Sales pipeline**
  - lifecycle: persistent
  - project_slug: sales-pipeline
  - status: active

- **Q2 board deck**
  - lifecycle: bounded
  - project_slug: q2-board-deck
  - status: completed
```

#### Who reads it

| Consumer | When | Why |
|---|---|---|
| **TP** | User says "I have a new project" or "I'm done with X" | Knows current work landscape, scaffolds/dissolves accordingly |
| **Composer** | Heartbeat assessment | Sees full work landscape for gap detection ("3 scopes but only 2 have platform sources") |
| **Bootstrap** | Platform connection | Maps new platform sources to existing work-scoped projects instead of creating generic digests |
| **Settings / Memory UI** | User views their work | Read-only display of current work state under the existing Memory tab |

#### Who writes it

| Writer | When | What |
|---|---|---|
| **Onboarding page** | First setup | Initial work structure + scopes |
| **TP** | User adds/removes/completes work via chat | Updates scopes, status, structure |
| **Composer** | Scaffolds or dissolves a project | Backfills `project_slug`, updates `status` |
| **PM** | Bounded project completes | Marks work unit `status: completed` |

#### Management model

The onboarding page is **one-time** — it collects the initial work structure and is not revisited as a settings page. After onboarding, work state evolves through conversation:

- **Add scope**: User tells TP "I just took on a new project — fundraising." TP updates `/memory/WORK.md`, scaffolds the project.
- **Remove scope**: User tells TP "I'm done with the board deck." TP marks it completed, PM dissolves.
- **Restructure**: User tells TP "I'm consolidating to focus on one thing." TP can merge/dissolve projects.
- **View current state**: The existing Settings page (Memory tab) shows work scopes as a read-only section — the user sees their work landscape without needing a separate surface.

This follows the same pattern as agent memory, preferences, and directives: **workspace files as the persistence layer, conversation as the write path, UI as the read path.**

---

## Interaction with ADR-130 (Agent Capability Substrate)

ADR-130 defines agent types as deterministic capability bundles. ADR-132 determines *which* agent types get instantiated and *how they're scoped*:

| ADR-130 concern | ADR-132 input |
|---|---|
| Which agent type to create? | Work unit description → type inference |
| What instructions to give? | Work unit context → scoped instructions |
| What sources to assign? | Work unit → platform source mapping |
| What pulse cadence? | Work type lifecycle → cadence (persistent = daily, bounded = on_demand) |

ADR-130's type registry provides the capability definitions. ADR-132's work description provides the instantiation context. They are complementary — ADR-130 is "what kinds of agents exist," ADR-132 is "what agents does this user need."

### Agent type reframing for user-facing identity

Work-first onboarding changes how agent types are presented. The user doesn't see "digest role, platform scope." They see team members:

| ADR-130 type | User-facing identity | Example |
|---|---|---|
| `digest` | "{scope_name} Digest" | "Acme Corp Digest", "Marketing Digest" |
| `monitor` | "{scope_name} Watch" | "Sales Pipeline Watch", "Hiring Watch" |
| `research` | "{scope_name} Researcher" | "Q2 Board Deck Researcher" |
| `synthesize` | "{scope_name} Analyst" | "Product Development Analyst" |
| `pm` | (invisible — infrastructure) | Coordination scoped to the project |

The display name is derived: `{scope_name} + {type_display_name}`. The scope name comes directly from the user's onboarding input — their words, not our categories. Stored in agent `title`, not in the type registry.

---

## Interaction with Onboarding Bootstrap (ADR-110/122)

Bootstrap (platform → auto-scaffold) is preserved as a **fallback path**, not the primary path:

| Scenario | What happens |
|---|---|
| Work description provided, then platform connected | Platform sources mapped to existing work-unit projects. No generic digest created. |
| Platform connected, no work description | Current bootstrap: generic `slack_digest` / `notion_digest` project created. |
| Work description provided, no platform connected | Projects scaffolded with placeholder agents. Sources populated when platform connects. |
| Work description provided later (via chat) | Existing generic projects rescoped, or new work-unit projects created alongside. |

---

## Phases

### Phase 1: Onboarding page + work index — IMPLEMENTED
- `/onboarding` route with two-step structured form (structure → scopes + name)
- `POST /api/memory/user/work` saves `/memory/WORK.md` as living work index
- `GET /api/memory/user/work` reads and parses work index
- Auth callback gate: `cold_start` users without work index → redirect to `/onboarding`
- Skip option preserves current flow (redirects to `/orchestrator`)
- `has_work_index` field added to onboarding state endpoint

### Phase 2: Lifecycle classification + project scaffolding — IMPLEMENTED
- `workspace` + `bounded_deliverable` types added to `PROJECT_TYPE_REGISTRY`
- `scaffold_project()` extended with `scope_name` param + `{scope_name}` template interpolation
- `objective_template`, `contributors_template`, `assembly_spec_template` on work-scoped types
- Projects created on onboarding submit, `project_slug` backfilled to WORK.md
- Orchestrator + projects page updated with new type labels

### Phase 3: Platform source mapping — PARTIALLY IMPLEMENTED
- Bootstrap (`maybe_bootstrap_project()`) checks work index — skips generic digest when WORK.md exists
- `sources_from: "work_unit"` defined in registry but source resolution deferred (requires TP-assisted channel→scope mapping)
- Channel/page → work scope mapping deferred to future iteration

### Phase 4: Orchestrator + TP integration — PARTIALLY IMPLEMENTED
- Work index injected into TP working memory (`build_working_memory()` reads WORK.md, `format_for_prompt()` renders "Your work" section)
- TP sees active scopes + project links in system prompt → can reference work context in conversation
- Remaining: Composer heartbeat integration, chat-based work setup for skip-onboarding users, informed action cards

---

## What This Does NOT Change

- **Agent execution pipeline**: Unchanged. Agents still pulse, generate, deliver.
- **Workspace filesystem**: Unchanged. Work description is a new file, not a new abstraction.
- **Meeting Room**: Unchanged. Users still interact with projects in `/projects/{slug}`.
- **Composer**: Reads `/memory/WORK.md` during heartbeat for gap detection (Phase 4). Core logic unchanged.
- **Tier limits**: Unchanged. Work units create projects within tier constraints.
- **PM model**: Mostly unchanged. Bounded projects get a lighter PM (future — Phase 2+).

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Work description too vague → poor scaffolding | TP asks clarifying follow-up in Orchestrator before scaffolding. Phase 1 captures without scaffolding. |
| Work description too specific → over-scaffolding | Cap work units at tier agent limit. TP prioritizes the most impactful units first. |
| User doesn't want to type → drops off | Skip option is prominent. Current flow preserved entirely as fallback. |
| Work unit → platform source mapping is hard | Phase 3 can use TP-assisted mapping (show user: "I found #acme-project — is this for your Acme client?"). Not fully automated. |
| Existing users with generic digest projects | No migration needed. New onboarding only applies to new signups. Existing users can provide work description via chat for future rescoping. |

---

## Resolved Questions

1. ~~**Work unit cap**: Should we limit work units per user?~~ → Let tier agent limits naturally constrain. Each work scope creates agents; tier limits (Free=2, Pro=10) bound the total. No separate scope limit needed.

2. ~~**Reonboarding**: Can existing users access the onboarding page to re-describe their work?~~ → No. Onboarding page is one-time. After first visit, work state evolves through conversation with TP. Current state visible in Settings → Memory tab (read-only).

3. ~~**Work description evolution**: How does `/memory/WORK.md` evolve?~~ → TP updates it on user request ("I have a new project", "I'm done with X"). Composer updates it when scaffolding/dissolving projects. PM updates it when bounded work completes. Conversation is the write path; UI is the read path.

4. ~~**Template interpolation**: How sophisticated should scope → project-type mapping be?~~ → Binary: persistent (`workspace`) vs. bounded (`bounded_deliverable`). Classification via lightweight heuristics or single Haiku call. No need for finer categories — user's scope name carries the identity.

## Open Questions

1. **Settings UI placement**: Where exactly in the Memory tab does the work index appear? As a top-level section, or nested under a "Work" subsection?
2. **Scope-to-source mapping confidence**: When a user connects Slack after onboarding, how aggressively should the system auto-map channels to work scopes? Full auto (risk wrong mapping) vs. TP asks for confirmation?

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-23 | v1 — Initial proposal: work-first onboarding, work units, lifecycle inference, platform source mapping |
| 2026-03-23 | v1.1 — Structured two-step onboarding (single vs. multi-scope) replaces free-text field. User-agnostic language (no "client" assumptions). Registry simplified to `workspace` + `bounded_deliverable`. |
| 2026-03-23 | v1.2 — `/memory/WORK.md` as living work index (not just onboarding output). Management model: conversation as write path, Settings/Memory as read path. Onboarding page is one-time, not revisitable. TP/Composer/PM read and write the work index. Resolved open questions 1-4. |
| 2026-03-23 | v1.3 — Phases 1+2 implemented. Frontend: `/onboarding` page, auth callback gate, type labels. Backend: `/api/memory/user/work` GET/POST, `workspace` + `bounded_deliverable` registry types, `scaffold_project()` scope_name interpolation, project scaffolding on submit with WORK.md backfill. |
| 2026-03-23 | v1.4 — Phases 3+4 partially implemented. Bootstrap skips generic digest when work index exists. TP working memory reads WORK.md and injects "Your work" section into system prompt. Source mapping (channel→scope) and Composer integration deferred. |
