# ADR-158: External Context Access — Platform Bot Ownership Model

**Status:** Accepted (Phase 1)  
**Date:** 2026-04-03 (proposed), 2026-04-04 (resolved decisions)  
**Related:** ADR-140, ADR-141, ADR-151, ADR-152, ADR-153, ADR-154, ADR-156, ADR-157

---

## Context

YARNNN has moved away from the old platform-sync architecture:

- `platform_content` is sunset (ADR-153)
- platform sync workers and sync cron are deleted
- tasks are the execution unit (ADR-141)
- `/workspace/context/` is the durable knowledge substrate (ADR-151, ADR-152)

Three ambiguities remained:

1. **Access**: Should external platform data be read live, cached, or task-scoped?
2. **Authority**: Can any platform-reading task write canonical context directly?
3. **Source types**: Slack (stream), Notion (document), GitHub (artifacts+code) behave differently.

The older model (connect → sync → cache) is dead. The replacement model is:
**Tasks are how work happens. Platforms are observation surfaces. Workspace is truth.**

---

## Decision

### One bot, one platform, one directory.

Each platform gets a dedicated bot agent (already in the ADR-140 roster). Each bot owns
a per-source context directory. The mapping is 1:1:1.

```
Slack Bot   → /workspace/context/slack/    (per-channel subfolders)
Notion Bot  → /workspace/context/notion/   (per-page subfolders)
GitHub Bot  → /workspace/context/github/   (per-repo subfolders, deferred)
```

### Resolved Decisions

**RD-1: Platform directories are context domains, per-source structured.**

Each platform gets its own directory in the directory registry with `type: "context"` and
`temporal: true`. Entity type is the platform's natural unit: channel (Slack), page (Notion),
repo (GitHub). Per-source subfolders enable freshness tracking via `_tracker.md` — TP can
see "the #general channel was last observed 3 days ago" and qualify its answers accordingly.

**RD-2: Bots own their directories (domain assignment).**

Platform bots in `agent_framework.py` get `domain` assignment (was `None`). This follows
the same axis-1 relationship as domain stewards: Competitive Intel owns `competitors/`,
Slack Bot owns `slack/`. Bots are agents with a narrow, platform-scoped responsibility.

**RD-3: Platform reading is an agent tool, not TP infrastructure.**

Platform tools (`read_slack`, `read_notion`, `read_github`) are capabilities for work
agents — same class as `web_search`. TP does not call platform tools directly. TP gets
temporal awareness via working memory injection of bot directories.

Separation: bots perceive → bots write to their directory → TP reads directory summaries.

**RD-4: Platform directories are temporal awareness for TP, not cross-agent context.**

Bot directories are consumed by:
- **TP** — as injected awareness (what's happening outside the system)
- **The bot's own tasks** — for continuity across runs

They are **not** primary input for domain steward tasks. Cross-pollination (e.g., "take
Slack signals and update competitor profiles") is explicitly out of scope — it's a separate
task design conversation requiring its own architectural framing.

**RD-5: Task types named by what they do.**

- `slack-digest` — read selected channels, produce digest, write to `/workspace/context/slack/`
- `notion-digest` — read selected pages, produce digest, write to `/workspace/context/notion/`
- `github-digest` — read selected repos (issues/PRs), write to `/workspace/context/github/` (deferred)

Write-back task types (`slack-respond`, `notion-update`) can be added later as distinct
task types on the same bot. This avoids overloading one task with read+write.

**RD-6: Source selection is user-managed per task.**

Initial source selection uses existing `landscape.py` + `compute_smart_defaults()`.
Users can refine which channels/pages/repos via task management UI. No broad workspace
mirroring — user opts into the specific external surfaces worth recurring attention.

**RD-7: GitHub is architecturally consistent but implementation-deferred.**

GitHub Bot gets a directory entry (`github`, entity_type: "repo") and domain assignment
for architectural consistency. The `github-digest` task type (issues/PRs from selected
repos) follows the same pattern as Slack/Notion. Repository-as-reference (reading code/docs)
is a different capability — closer to "research" than "platform monitoring" — and deferred.

**RD-8: Soft TTL, no cleanup jobs.**

Temporal directories use soft TTL — readers deprioritize stale entries, nothing is
automatically deleted. Hard cleanup only if directories become noisy. This does not
require bringing back backend sync jobs.

**RD-9: Cross-pollination is out of scope.**

Automatic promotion from platform directories to canonical domains is explicitly deferred.
If/when addressed, it should be its own architectural conversation — not embedded in
platform access work.

---

## Epistemic Model

External reads default to **temporal**. Canon must be earned.

Three epistemic classes:

| Class | Description | Examples |
|---|---|---|
| **Temporal** | Event truth — what changed, what happened, what is active now | Slack debate, Notion page change, PR in review |
| **Reference** | Trusted external source material — usable during execution, not auto-canon | Selected Notion spec page, repo structure, uploaded doc |
| **Workspace Canon** | YARNNN's curated understanding — durable, steward-owned | `competitors/{entity}/profile.md`, synthesis files |

Default rule: External read → temporal or reference. Distilled conclusion → eligible for canon.

---

## Source Taxonomy

### 1. Stream Surfaces (Slack)

High volume, high noise, context-fragmented. Useful for signals, decisions, urgency,
relationship movement. Weak as direct durable truth.

Handling: read live → extract signals → write to `/workspace/context/slack/{channel}/` →
canonical promotion only through separate curation task (out of scope).

### 2. Document / Reference Surfaces (Notion)

More durable than streams. Can act as direct source material. Still mutable.

Handling: monitor what changed → write observations to `/workspace/context/notion/{page}/` →
selected pages usable as direct task input → promote distilled conclusions selectively.

### 3. Work / Artifact Surfaces (GitHub)

Issues/PRs contain operational truth. Repositories contain product/system truth.
Not well-described by the stream model.

Handling: issues/PRs → temporal observation in `/workspace/context/github/{repo}/` →
repository-as-reference deferred (separate capability conversation).

---

## Authority Model

Two write layers, but enforcement is architectural (bot ownership) not code-enforced:

| Layer | Who writes | Properties | Examples |
|---|---|---|---|
| **Observation** | Platform bots (via their tasks) | Temporal, append-oriented, lower-trust | Channel digests, page change summaries, issue/PR observations |
| **Canonical** | Domain stewards (via their tasks) | Curated, durable, steward-owned | Entity profiles, synthesis files, domain assessments |

Default rule: Bots observe and write to their platform directory. Stewards curate and
write to their canonical domain. TP sees both through working memory injection.

---

## Directory Structure

### Per-source subfolders with tracker

```text
/workspace/context/slack/
  _tracker.md              # | Channel | Last Updated | Status |
  general/
    latest.md              # Most recent observation
  engineering/
    latest.md
  announcements/
    latest.md

/workspace/context/notion/
  _tracker.md              # | Page | Last Updated | Status |
  product-roadmap/
    latest.md
  meeting-notes/
    latest.md

/workspace/context/github/          # (deferred — directory exists, no task type yet)
  _tracker.md              # | Repo | Last Updated | Status |
```

Per-source freshness via `_tracker.md` gives TP temporal awareness:
- "The #general channel was last observed yesterday — I can speak to recent Slack activity."
- "The product-roadmap page hasn't been checked in 2 weeks — my Notion context may be stale."

---

## Sunk-Cost Check

This model passes the sunk-cost test because it:

- **Is task-driven** — no background sync, no cache jobs
- **Is source-bounded** — user selects channels/pages/repos per task
- **Is explicitly temporal** — directories are awareness, not canon
- **Respects existing architecture** — bots are already in the roster, directories follow registry patterns
- **Does not recreate platform_content** — no bulk ingestion, no retention policies, no platform worker

It would fail if it became: broad ingestion, a hidden cache, or automatic canon for other agents.

---

## Implementation Phases

### Phase 1: Registry + Ownership (this commit)

- Add `slack`, `notion`, `github` to directory registry (`temporal: true`)
- Assign `domain` to platform bots in agent framework
- Rename task types: `monitor-slack` → `slack-digest`, `monitor-notion` → `notion-digest`
- Update step instructions for platform-specific writing
- Update TP working memory injection for temporal platform awareness
- Update all downstream docs

### Phase 2: Source Selection (this commit)

- `**Sources:**` field in TASK.md — serialized as `platform:id1,id2; platform:id3`
- `parse_task_md()` extracts sources into `task_info["sources"]`
- `CreateTask` auto-populates from `platform_connections.selected_sources`
- `ManageTask(action="update", sources={...})` for user refinement via TP
- `gather_task_context()` injects "Selected Sources" section with resolved names
- TP prompts updated with source selection guidance
- Frontend source selection UI deferred — TP is the current UX surface

### Phase 3: Write-back Task Types (this commit)

- `slack-respond` (reactive) — post to Slack from workspace context
- `notion-update` (reactive) — comment on Notion page from workspace context
- Separate from digest — read+write not overloaded into one task
- Both are `task_class: "synthesis"` (produce output, don't accumulate context)
- Platform-specific step instructions for compose → deliver workflow

### Phase 4: GitHub Bot + Temporal Digest (complete)

- `github_bot` agent template + DEFAULT_ROSTER entry + DB migration 140
- `github-digest` task type (recurring, daily) — issues/PRs from selected repos
- Platform-specific step instructions for GitHub observation workflow

### Phase 5: GitHub Inward Reference (this commit)

GitHub is fundamentally different from Slack/Notion. It is both inward-facing
(what your team is building) and outward-facing (what the market is shipping).
For technical teams, GitHub is the system of record — not Slack (opinions), not
Notion (aspirations), but code, releases, and architecture (reality).

**YARNNN's boundary:** GitHub as an information surface (what exists, what changed,
what shipped), NOT as a development tool (code review, debugging, CI/CD). Agents
understand *what* is being built and *how it's going*, not implementation details.

Three layers of GitHub context, phased:

| Layer | Type | Content | Phase |
|---|---|---|---|
| Issues/PRs | Temporal | What's in motion, who's blocked, what merged | P4 (done) |
| README/releases/metadata | Reference | What the product is, what shipped, tech stack | P5 (this) |
| External repos | Outward | Competitor activity, ecosystem shifts, OSS signals | P6 (next) |

Phase 5 expands GitHub client and `github-digest` step instruction:
- New client methods: `get_readme()`, `get_releases()`, `get_repo_metadata()`
- New tool definitions exposed to headless agents
- `github-digest` writes reference files alongside temporal observations
- Per-repo directory gains: `readme.md`, `releases.md`, `metadata.md`
- No new primitives, no new task types — same bot, richer output

### Phase 6: GitHub Outward Observation (this commit)

Same `github-digest` task type, but source selection accepts any public repo
(not just user-owned). The bot doesn't need to know the difference between own
and external repos — source selection and directory structure handle it:

```text
/workspace/context/github/
  my-company/my-product/        # inward — your repo
    latest.md                   # issues/PRs (temporal)
    readme.md                   # README (reference)
    releases.md                 # what shipped (temporal)
    metadata.md                 # stack, description (reference)
  competitor/their-product/     # outward — public repo
    latest.md
    readme.md
    releases.md
    metadata.md
```

No code reading. No implementation analysis. Metadata, docs, and activity only.

---

## What This ADR Does Not Decide

- Cross-pollination: how/whether platform observations feed into canonical domains
- Hard TTL: cleanup jobs for temporal directories (only if needed)
- Source selection UX: exact UI for channel/page/repo management
- GitHub code reading: implementation-level analysis is IDE territory, explicitly out of scope
- GitHub CI/CD: build status, deployment state — not an information surface YARNNN tracks

---

## Consequences

### Positive

- Restores trust boundary between observation and durable truth
- 1:1:1 mapping (bot → platform → directory) is simple and auditable
- TP gets temporal awareness without calling platform tools
- Tasks remain the single scheduling model
- No new infrastructure — bots already exist, directories follow registry patterns

### Negative

- More scaffolding (3 new directories, domain assignments, task type renames)
- Cross-pollination requires separate task design (can't just read Slack and write to competitors/)
- GitHub is architecturally present but functionally deferred

### Risks

- Platform directories could grow noisy without source selection discipline
- Users may expect bots to automatically enrich canonical domains (requires UX education)
- Naming change (monitor-* → *-digest) requires frontend + doc updates
