# ADR-119: Workspace Filesystem Architecture

> **Status**: Phase 1 Implemented, Phase 2-4 Proposed
> **Date**: 2026-03-17
> **Authors**: KVK, Claude
> **Extends**: ADR-106 (Agent Workspace Architecture), ADR-118 (Skills as Capability Layer)
> **Related**: ADR-116 (Inter-Agent Knowledge), ADR-117 (Feedback Substrate), ADR-111 (Composer)

---

## Context

ADR-106 established the virtual filesystem over Postgres — agents interact via path-based operations, the path structure IS the schema, `workspace_files` replaces opaque JSONB blobs. ADR-118 extended this with `content_url` for binary outputs and proposed `/assets/` for shared creative resources.

But the current implementation is functionally a **key-value store with path-shaped keys**. Paths exist, but folders don't. There's no concept of a folder as a boundary, a folder as a unit of work, or a folder as a scoping mechanism. The problems this creates:

1. **No grouping.** An agent run that produces a PPTX + 4 chart PNGs + 1 data source writes 6 independent rows. Nothing says "these files belong together." Another agent reading the workspace sees loose files, not a coherent output.

2. **No scoped context.** When multiple agents need to collaborate on a shared outcome (a product review, a launch package), there's no bounded space for that collaboration. Each agent writes to its own `/agents/{slug}/` namespace. Cross-agent work has nowhere to live.

3. **No temporal organization.** An agent that's run weekly for 6 months has 26 outputs, but they're either overwritten (latest only) or manually versioned via path hacks (`/runs/v{N}.md`). There's no natural way to see "what did this agent produce on March 3rd" vs "what's its current state."

4. **No lifecycle distinction.** Working scratch files from a single run get the same treatment as canonical outputs. Over time the workspace accumulates noise that pollutes search and discovery.

**The Cowork insight**: Cowork's folder selection creates a bounded context. Claude works within a folder — and that folder IS the scope. Everything inside it is the workspace. The folder boundary means Claude can have 12 related files that together constitute one deliverable, organized naturally. yarnnn needs the same concept, but persistent: agents aren't session-bound, the workspace accumulates across the agent's entire lifetime, and it's shared across a workforce of agents.

**The key principle**: Folders are boundaries. Folders are context. Folders are the organizational primitive. Not tables, not graphs, not relational abstractions — folders. The path hierarchy in `workspace_files` already supports hierarchical paths. What's missing is treating folders as first-class concepts with conventions that create structure.

## Decision

Evolve `workspace_files` into a proper folder-based filesystem through **path conventions, folder-aware operations, and minimal schema additions**. The folder hierarchy IS the architecture. No new relational tables for grouping or dependency tracking — folders and co-location handle what those tables would have done.

### 1. Folder Hierarchy as Architecture

The folder structure is the single source of truth for organization, scoping, and relationships. Every organizational concept maps to a folder:

```
/                                            ← workspace root (user-scoped)
│
├── /agents/{slug}/                          ← agent workspace (bounded context per agent)
│   ├── AGENT.md                             ← identity + behavioral directives
│   ├── thesis.md                            ← evolving domain understanding (versioned)
│   ├── /memory/                             ← accumulated state
│   │   ├── observations.md
│   │   ├── preferences.md                   ← learned from user edits
│   │   └── {topic}.md
│   ├── /working/                            ← ephemeral scratch (cleaned after run)
│   │   └── review-2026-03-17.md
│   ├── /outputs/                            ← delivered outputs, organized by date
│   │   ├── /2026-03-17/                     ← one folder per run = one coherent output
│   │   │   ├── manifest.json               ← what's in this folder, metadata, delivery status
│   │   │   ├── report.md                    ← text output
│   │   │   ├── report.pdf                   ← rendered binary (content_url → S3)
│   │   │   ├── chart-revenue.png            ← supporting asset
│   │   │   └── data-export.xlsx             ← supporting asset
│   │   └── /2026-03-10/
│   │       └── ...                          ← previous run's output folder
│   └── /references/                         ← content this agent found valuable
│       └── {ref}.md
│
├── /knowledge/                              ← shared knowledge substrate (all agents read)
│   ├── /digests/
│   │   └── slack-engineering-recap-2026-03-17.md
│   ├── /analyses/
│   ├── /briefs/
│   ├── /research/
│   └── /insights/
│
├── /projects/{slug}/                        ← cross-agent collaboration space
│   ├── PROJECT.md                           ← project identity (like AGENT.md for agents)
│   ├── /memory/                             ← project-level accumulated state
│   │   ├── preferences.md                   ← distilled from feedback on assembled outputs
│   │   └── observations.md                  ← cross-contribution patterns
│   ├── /contributions/                      ← each agent writes to its own subfolder
│   │   ├── {agent-slug-a}/
│   │   │   ├── chart-q2-revenue.png
│   │   │   └── data-export.xlsx
│   │   └── {agent-slug-b}/
│   │       └── executive-summary.md
│   ├── /assembly/                           ← composed outputs (like agent's /outputs/)
│   │   └── /{date}/
│   │       ├── manifest.json
│   │       ├── q2-review-deck.pptx
│   │       └── q2-review-report.pdf
│   ├── /working/                            ← ephemeral scratch for assembly
│   └── /assets/                             ← project-specific resources
│       ├── product-screenshot.png
│       └── team-photo.jpg
│
├── /assets/                                 ← shared creative resources (ADR-118)
│   ├── /brand/                              ← logos, colors, fonts, guidelines
│   ├── /images/                             ← reusable images, icons
│   └── /templates/                          ← output templates by type
│       ├── /report/
│       ├── /presentation/
│       └── /video/
│
└── /memory/                                 ← user-level memory (ADR-106, unchanged)
    ├── MEMORY.md
    ├── preferences.md
    └── notes.md
```

### 2. The Folder IS the Bundle

An agent run's output folder (`/agents/{slug}/outputs/2026-03-17/`) replaces any concept of a "bundle table." All files in that folder are one coherent output — the PPTX, its charts, its data source, its rendered PDF. The folder boundary IS the atomic grouping.

**`manifest.json`** at the root of each output folder carries the metadata that a bundle table would have held:

```json
{
  "run_id": "uuid",
  "agent_id": "uuid",
  "created_at": "2026-03-17T09:00:00Z",
  "status": "delivered",
  "files": [
    {"path": "report.md", "type": "text/markdown", "role": "primary"},
    {"path": "report.pdf", "type": "application/pdf", "role": "rendered", "content_url": "s3://..."},
    {"path": "chart-revenue.png", "type": "image/png", "role": "asset"},
    {"path": "data-export.xlsx", "type": "application/xlsx", "role": "asset", "content_url": "s3://..."}
  ],
  "delivery": {"channel": "email", "sent_at": "2026-03-17T09:05:00Z"},
  "sources": ["//knowledge/digests/slack-engineering-recap-2026-03-17.md"],
  "feedback": {"approved": true, "edits": 0}
}
```

**Why this over a table**: The manifest is a file in the filesystem, not a row in a separate table. It follows the same access pattern as every other workspace file. Agents can read manifests from other agents' output folders (via `ReadAgentContext`) to understand what was produced, when, and from what sources. The folder + manifest pattern means "list this agent's outputs" is just a path prefix query, not a join across tables.

**What `sources` provides**: The `sources` array in the manifest replaces a formal dependency graph table. It records what knowledge files or other agent outputs were consumed during this run. Staleness detection = compare source file's `updated_at` against the manifest's `created_at`. If the source is newer, the output may be stale. Simple timestamp comparison, no graph traversal needed.

### 3. Versioning Through Folder Accumulation

Instead of a `workspace_file_versions` table, versioning happens naturally through the folder structure:

**For outputs**: Each run gets its own dated folder. `/agents/{slug}/outputs/2026-03-17/` and `/agents/{slug}/outputs/2026-03-10/` coexist. The history IS the folder listing. "What did this agent produce last month" = list folders under `/outputs/` with date prefix `2026-02-*`.

**For evolving files** (thesis, memory, AGENT.md): Add a `version` column to `workspace_files` and a lightweight history mechanism. When an evolving file is overwritten:
1. The previous content is preserved (either in a `workspace_file_versions` table or as a dated copy in a `/history/` subfolder — implementation choice)
2. The `version` counter increments on the main row
3. Latest is always the hot path (read the main row, no join)

The key distinction: **outputs version by folder accumulation** (each run = new folder). **Identity/state files version by overwrite history** (thesis.md evolves in place, previous versions accessible). Two versioning strategies for two different file categories, both folder-native.

**Schema addition** (minimal):

```sql
ALTER TABLE workspace_files
    ADD COLUMN version INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN lifecycle TEXT NOT NULL DEFAULT 'active';
    -- lifecycle: 'ephemeral' | 'active' | 'delivered' | 'archived'
```

**`version`** — tracks how many times an evolving file has been overwritten. The execution layer decides whether to preserve previous versions (for high-value files like thesis.md, memory/*.md) or just increment (for low-value files).

**`lifecycle`** — governs visibility and cleanup:
- `ephemeral` — scratch files in `/working/`. Auto-cleaned after run or after 24h TTL.
- `active` — current, live files. Default state. Always returned in queries.
- `delivered` — output sent to user. Kept for feedback window.
- `archived` — superseded. Excluded from default queries but accessible explicitly.

### 4. Projects as Shared Folders (Recursive Pattern)

A project is a folder at `/projects/{slug}/`. The folder IS the bounded context for cross-agent collaboration. The project folder structure mirrors the agent folder structure because the same management pattern applies at both levels.

**The recursive pattern**: Every managed entity in yarnnn follows the same shape:

| Concept | Agent | Project |
|---|---|---|
| Identity | `AGENT.md` | `PROJECT.md` |
| Memory | `/memory/preferences.md`, `/memory/observations.md` | `/memory/preferences.md`, `/memory/observations.md` |
| Outputs | `/outputs/{date}/manifest.json` + files | `/assembly/{date}/manifest.json` + files |
| Scratch | `/working/` (ephemeral) | `/working/` (ephemeral) |
| Created by | TP (CreateAgent) or Composer | TP (CreateProject) or Composer |
| Instructed by | User (via TP editing AGENT.md) | User (via TP editing PROJECT.md) |
| Feedback | User edits → distilled to preferences.md | User edits assembled output → distilled to project preferences.md |
| Supervised by | Composer (heartbeat, lifecycle) | Composer (heartbeat, lifecycle) |

**`PROJECT.md`** at the folder root serves as the project's identity document — what this project produces, which agents contribute, what the assembled output should look like, and the coordination contract that individual AGENT.md files can't express because they're scoped to one agent's concerns. Written by TP or Composer at creation, editable by user via TP — same as AGENT.md.

**When does a project exist vs. agents just reading each other?** A project exists when the assembled output is greater than the sum of contributions — when agents A, B, and C each contribute pieces that get assembled into something none of them could produce alone (a deck with data + narrative + visuals). If agent B just reads agent A's output as input, that's cross-agent reading (ADR-116, already works). The boundary is qualitative: a project is needed when the combination requires coordination.

**Project creation triggers** (same decision logic as agent creation):

1. **User-initiated via TP**: "Create a project for the Q2 review that combines the analyst's data with the recap agent's summaries into a presentation." TP calls `CreateProject` (analogous to `CreateAgent`). Most common early path.

2. **Composer-initiated**: Heartbeat detects that two mature agents' outputs are consistently consumed together (via `memory/references.json` consumption tracking, ADR-116 Phase 5). Pattern: agent A's output appears as source in agent B's manifest, agent B's output is delivered + approved. Composer proposes a project to formalize this relationship. Same signal logic as "create synthesis from mature digests."

3. **Agent-initiated signal** (future, earned): A coordinator-skill agent notices during execution that its output would benefit from another agent's work. It writes to `memory/observations.md`: "My weekly report would be stronger with the analyst's revenue chart." Composer picks this up in heartbeat and considers project creation. The agent surfaces the need, Composer acts.

**Write scoping**: Each contributing agent writes only to `/projects/{slug}/contributions/{own-slug}/`. The assembly subfolder (`/assembly/`) is written by Composer — it reads contributions, invokes output gateway skills as needed, and writes the composed output. No dedicated coordinator agent required; Composer already manages the agent workforce (ADR-111) and extending it to manage project assembly preserves the single-surface model. Agent isolation is maintained within the shared space — agents contribute to their folder, they don't edit other agents' contributions.

**Project lifecycle**: PROJECT.md carries status (draft/active/delivered/archived). Composer manages lifecycle via the same signals it uses for agents — approval rate of assembled outputs, staleness of contributions, user engagement. Projects are dissolved (archived) when the Composer determines they're no longer producing value.

**Project-level feedback loop**: When a user edits or approves an assembled project output, feedback distillation runs at the project level (same cron, same logic as agent-level). Distilled preferences are written to `/projects/{slug}/memory/preferences.md`. Contributing agents can read these to understand what the project needs from them — same as an agent reading its own preferences to improve.

### 5. Folder-Aware Operations

The existing primitives evolve to be folder-aware:

| Primitive | Change | Description |
|---|---|---|
| `WriteWorkspace` | Extended | `lifecycle` parameter. Writes to `/working/` default to ephemeral. |
| `ReadWorkspace` | Extended | `version` parameter for evolving files. Folder path returns manifest if it exists. |
| `ListWorkspace` | Extended | `lifecycle` filter (default excludes ephemeral/archived). Folder listing returns structure. |
| `SearchWorkspace` | Extended | `lifecycle` filter. Excludes ephemeral/archived by default. |
| `WriteOutput` | New | Writes file(s) to a run's output folder, auto-creates dated folder + manifest. |
| `ReadProject` | New | Reads `PROJECT.md` + lists contributions from a `/projects/` path. |

**`WriteOutput`** is the key new primitive. When an agent run produces its final output:
1. Creates `/agents/{slug}/outputs/{date}/` folder
2. Writes each output file into it
3. Creates `manifest.json` with file listing, metadata, source references
4. Marks all files as `active` (or `delivered` once sent)

This replaces the current pattern where outputs are written to scattered paths. The output folder convention means "everything from this run" is always co-located and discoverable.

### 6. Cross-Agent Composition via Folders

Folders make cross-agent composition natural:

**An agent reading another agent's work**: `ReadAgentContext` already provides read-only access. With output folders, the reading agent can see structured output history — not just the latest thesis, but the dated output folders with manifests describing what was produced and from what sources.

**Multiple agents contributing to a project**: Each writes to its scoped subfolder within the project. The assembling agent (or Composer) reads all contributions, composes the final output into `/assembly/`, and the project folder IS the deliverable package.

**Recursive composition**: An analyst produces data (in its output folder) → a chart agent reads that data and produces a PNG (in its output folder, manifest lists the analyst's output as source) → a presenter reads both and produces a PPTX (in the project's assembly folder, manifest lists both as sources). Each step is a folder operation. Staleness = compare timestamps between source references and current state. No graph database needed.

### 7. Folder Conventions Summary

| Folder | Scope | Who writes | Lifecycle | Purpose |
|---|---|---|---|---|
| `/agents/{slug}/` | Single agent | That agent | Persistent | Agent's bounded workspace |
| `/agents/{slug}/working/` | Single agent, single run | That agent | Ephemeral (auto-clean) | Scratch/intermediate files |
| `/agents/{slug}/outputs/{date}/` | Single agent, single run | That agent | Active → Delivered | Coherent run output |
| `/agents/{slug}/memory/` | Single agent, accumulated | That agent + system | Persistent | Versioned state files |
| `/knowledge/` | All agents | Any agent via KnowledgeBase | Retention-based | Shared knowledge substrate |
| `/projects/{slug}/` | Multiple agents | Agents + Composer | Project lifecycle | Cross-agent collaboration |
| `/projects/{slug}/contributions/{agent}/` | Single agent within project | That agent | Project lifecycle | Agent's project contribution |
| `/projects/{slug}/assembly/` | Project-level | Coordinator agent | Project lifecycle | Composed final output |
| `/assets/` | Global | Users + engineering | Persistent | Creative resources, templates |
| `/memory/` | User-level | System + user | Persistent | User identity + preferences |

### 8. Schema Changes (Minimal)

**Modified table** — `workspace_files`:
```sql
ALTER TABLE workspace_files
    ADD COLUMN version INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN lifecycle TEXT NOT NULL DEFAULT 'active';
```

Two columns. No new tables. The folder conventions and `manifest.json` files handle everything else.

**Optional** (if version history for evolving files proves valuable):
```sql
CREATE TABLE workspace_file_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id UUID NOT NULL REFERENCES workspace_files(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    content_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(file_id, version)
);
```

This is the ONE table that might be needed — and only for evolving files (thesis.md, memory/*.md, AGENT.md) where overwrite history matters. Output versioning is handled entirely by date-folders. If the version history table proves unnecessary (e.g., we can just keep dated copies in a `/history/` subfolder), it gets dropped.

## The Filesystem as Coordination Substrate

The thesis: **folders are boundaries, and boundaries are all you need for coordination.**

1. **Agent isolation** = folder boundary. `/agents/{slug}/` is the agent's world. It can't write outside it (except to `/knowledge/` and its own project contribution folder).

2. **Run atomicity** = output folder. `/agents/{slug}/outputs/2026-03-17/` is one coherent output. The folder IS the bundle.

3. **Cross-agent collaboration** = project folder. `/projects/{slug}/` is the shared space. Each agent gets a contribution subfolder. The assembly subfolder is the composed result.

4. **Temporal history** = folder accumulation. Output folders accumulate by date. "Show me this agent's history" = list the output folders.

5. **Context scoping** = folder targeting. Just as Cowork scopes to a selected folder, yarnnn agents scope to their workspace folder. A project scopes to its project folder. The folder selection IS the context boundary.

6. **Lifecycle** = folder convention + file metadata. `/working/` = ephemeral. `/outputs/` = delivered. `/memory/` = persistent. The path tells you the lifecycle intent; the `lifecycle` column confirms the state.

This is simpler, more intuitive, and more extensible than relational tables for grouping and dependencies. Adding a new organizational concept = adding a new folder convention. No schema migrations, no new tables, no new primitives.

## Implementation Phases

### Phase 1: Output Folders + Lifecycle (Implemented)
- ✅ Add `version`, `lifecycle` columns to `workspace_files` (migration 116)
- ✅ `AgentWorkspace.save_output()` — creates dated output folder (`/outputs/{date}/`) with `output.md` + `manifest.json`
- ✅ Execution pipeline calls `save_output()` after successful agent generation (alongside existing knowledge write)
- ✅ `write()` auto-infers `lifecycle='ephemeral'` for `/working/` paths
- ✅ Cleanup job in unified scheduler: deletes ephemeral files >24h old (hourly)
- ✅ `list()` excludes ephemeral/archived by default (lifecycle filter)
- ✅ Tool descriptions updated: ReadWorkspace, WriteWorkspace, ListWorkspace, SearchWorkspace

### Phase 2: Project Folders + Cross-Agent Writing (After Phase 1)
- Establish `/projects/` path convention
- Implement `ReadProject` primitive
- Write permission scoping for project contribution folders
- Composer heuristics for project creation
- `PROJECT.md` convention with status tracking

### Phase 3: Version History for Evolving Files (After Phase 2)
- Version history via `/history/` subfolder for evolving files (thesis.md, memory/*.md, AGENT.md)
- On overwrite of high-value file: copy previous to `/agents/{slug}/history/{filename}-v{N}.md`
- `ReadWorkspace(version=N)` resolves to history subfolder
- `FileHistory` primitive lists versions from history subfolder
- Migrate `KnowledgeBase._archive_if_exists()` to use history subfolder convention
- Migrate `AgentWorkspace.save_run()` from `/runs/v{N}.md` to output folders

### Phase 4: Frontend + Composer Integration (After Phase 3)
- Dashboard: agent output history as folder timeline
- Dashboard: project view with contributions + assembly
- Download: "Download all" = zip the output folder
- Composer heartbeat: filesystem health (stale outputs, orphaned projects, cleanup metrics)

### Deferred
- External sync (workspace folders ↔ Google Drive, Dropbox)
- **Workspace quotas and tiered storage** — requires separate economics and pricing model analysis. Storage accumulates across output folders, version history, project contributions, and S3 binaries. Per-agent pricing may conflict with multi-agent project value. See Resolved Decision #8.
- Real-time collaboration (multiple agents writing to same project concurrently)
- Folder-level permissions beyond the current convention-based model

## Interaction with ADR-118 Phase D

ADR-118 Phase D proposes all agent outputs flow through `workspace_files` as the single output substrate. ADR-119 provides the folder semantics that make this clean:

- **Output folders** replace `agent_runs` as the delivery unit — the folder + manifest IS the atomic output
- **Date-based accumulation** replaces the `/runs/v{N}.md` path hack — each run gets its own folder
- **Manifests** give the output gateway everything it needs for delivery — what files, what format, what delivery channel, what sources were used
- **Lifecycle column** tells the delivery layer what state each output is in

**Implementation order**: ADR-119 Phase 1 (output folders + lifecycle) should land before or concurrent with ADR-118 Phase D Step 1 (writing all outputs to workspace_files). The output folder convention gives Phase D a clean landing zone.

**Existing mechanisms to migrate**: `KnowledgeBase._archive_if_exists()` (path-based `v{N}.md` copies) and `AgentWorkspace.save_run()` (writes to `/runs/v{N}.md`) both migrate to the output folder pattern in Phase 3.

## Resolved Decisions

1. **Manifest as workspace_file.** `manifest.json` is a row in `workspace_files` with `content_type='application/json'`. Searchable, discoverable by other agents via `QueryKnowledge`, carries metadata like any other file. Text search indexes skip non-markdown content types, so no noise.

2. **Output folder date granularity: truncated to hour.** Format: `2026-03-17T0900`. Handles agents that run multiple times per day. Clean enough for display. The `WriteOutput` primitive generates this from the run's timestamp.

3. **Version history via `/history/` subfolder.** Folder-native, no new table. On overwrite of a high-value file (thesis.md, memory/*.md, AGENT.md), previous version is copied to `/agents/{slug}/history/{filename}-v{N}.md`. `ReadWorkspace(version=N)` resolves to the history subfolder. `FileHistory` primitive lists versions by path prefix. Same pattern as `KnowledgeBase._archive_if_exists()` already uses, just formalized as a convention.

4. **Project creation follows the same recursive pattern as agent creation.** Three triggers, same decision logic: (a) user-initiated via TP (`CreateProject`, analogous to `CreateAgent`), (b) Composer-initiated from consumption tracking signals (agent A's output consistently appears as source in agent B's manifest → formalize as project), (c) agent-initiated signal (future, earned — agent surfaces need in observations.md, Composer acts). The project folder mirrors agent folder structure: PROJECT.md (identity), memory/ (preferences, observations), assembly/ (outputs), working/ (ephemeral), contributions/ (per-agent scoped inputs). Feedback distillation runs at project level using the same cron and logic as agent-level.

5. **Cross-user projects: deferred.** Single-user workspace for now.

6. **Project-level feedback distillation supplements, not replaces.** Distillation is a pattern that runs at different scopes: agent-level (user edits → agent's preferences.md), user-level (cross-agent patterns → /memory/ files), project-level (user edits assembled output → project's preferences.md). Same mechanism, different bounded context. The project's preferences.md captures what the assembly needs; contributing agents' preferences.md files capture their individual feedback. Both run in the same distillation cron, same query logic, different path prefix.

7. **Composer writes to `/assembly/`, not a dedicated coordinator agent.** Composer already manages the agent workforce (creates, assesses, pauses, promotes — ADR-111). Assembly is a Composer action: read contributions, invoke output gateway skills (pptx, pdf, etc.), write assembled output. No new agent entity needed. This preserves the single-surface model — user talks to Composer, Composer manages both agents and projects. Individual agents write to their contribution folders autonomously (on schedule). The assembly step is Composer-initiated.

8. **Workspace quotas require separate economics and pricing model analysis.** Storage accumulates with output folders, version history, project contributions, and binary assets (S3). Current subscription model may need to evolve — potentially higher pricing tiers, or per-agent pricing, or storage-based tiers. Note: per-agent pricing could conflict with multi-agent project value (the value IS the composition, not individual agents). This tension needs its own analysis — not in scope for this ADR, but flagged as a dependency for product/pricing decisions.

9. **Projects are ongoing, not schedule-sensitive.** Projects are not scheduled entities — they don't have cron expressions or run cycles. They trail indefinitely, like an open chat session or an ongoing collaboration. Contributing agents run on their own schedules and write to their contribution folders whenever they produce. Composer assembles when it determines contributions have meaningfully changed (new files, updated files since last assembly) — not on a fixed cadence. Projects are archived only by external force: user request, Composer lifecycle assessment (no new contributions + no user engagement for extended period), or explicit dissolution. This matches the personification: a team collaboration doesn't have a schedule — it has participants who each work at their own pace, and someone (Composer) periodically pulls it together.

10. **Contributing agents read project context.** Agents that contribute to a project can read the project's `PROJECT.md` and `memory/preferences.md` via `ReadAgentContext` extended to project paths. This gives contributing agents shared context — they understand what the project needs, what feedback has been given on assembled outputs, and how their contributions fit. Each agent remains specialized via its own AGENT.md and prompt configuration, but the shared project context leads to more consistent and better-aligned contributions. More shared context + specialized agents = better composition.
