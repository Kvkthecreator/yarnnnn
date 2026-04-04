# ADR-158: External Context Access and Authority Model

**Status:** Proposed  
**Date:** 2026-04-03  
**Related:** ADR-141, ADR-151, ADR-152, ADR-153, ADR-154, ADR-156, ADR-157

---

## Context

YARNNN has already moved away from the old platform-sync architecture:

- `platform_content` is sunset
- platform sync workers and sync cron are deleted
- tasks are the execution unit
- `/workspace/context/` is the durable knowledge substrate

But the replacement model is not yet conceptually settled.

Three ambiguities remain:

1. **Access ambiguity**
   - Should external platform data be read live, cached, or task-scoped?
   - What role should `platform_connections` and `sync_registry` still play?

2. **Authority ambiguity**
   - If a task reads Slack, Notion, or GitHub, can it update canonical context directly?
   - Is every platform-reading task a valid writer to durable workspace truth?

3. **Source-type ambiguity**
   - Slack is a stream of events, not a durable knowledge base
   - Notion is both a document source and a change surface
   - GitHub is different again: issues/PRs are work artifacts, while repositories may be direct system/reference context

This creates a trust problem.

Observation is not the same as workspace truth. A platform-reading task may detect something useful, but that does not mean it should automatically mutate canonical domain state.

There is also a broader product-level reframe underway.

The older service philosophy was closer to:

- connect user platforms
- read/sync them in the background
- sometimes write back there

That is no longer an adequate model for "autonomous recurring work."

The current architecture suggests a different center of gravity:

- recurring tasks, not background sync, are how work happens
- external platforms are observation/reference surfaces
- durable knowledge lives in the workspace
- write-back to third-party tools is a delivery/action surface, not the core substrate

There is a live proposal to introduce a **separate temporal platform-observation folder inside `/workspace/context/`** rather than forcing all external observations into either:

- canonical context domains, or
- purely task-local working state

This needs to be evaluated carefully against sunk-cost risk. A dedicated temporal folder could clarify the service model, or it could accidentally recreate the old sync/cache philosophy in a new filesystem shape.

---

## Decision

Adopt a task-first, authority-layered model for external context.

### 1. Tasks are the only scheduled execution unit

No generic platform sync/cache jobs.

External platform reads happen in only two modes:

- **Interactive live read**: explicit TP/user/tool action
- **Task live read**: recurring or on-demand task execution

### 2. External platform access is a read capability, not default write authority

Reading Slack, Notion, or GitHub does **not** by itself grant authority to rewrite canonical context domains.

Observation and curation are separate responsibilities.

### 3. Workspace context is the sole accumulated substrate, but not all context is canon

`/workspace/context/` may contain:

- **canonical context domains** — durable, curated, steward-owned
- **temporal observation domains** — time-bound, lower-trust, not canon by default

External platforms are not mirrored wholesale into YARNNN.

### 4. Write authority is layered

There are two write layers:

- **Observation layer**
  - multi-writer
  - provisional
  - append-oriented
  - lower-trust

- **Canonical layer**
  - curated
  - durable
  - higher-trust
  - steward-owned by default

### 5. External sources are not treated as one class

Platforms are classified by the type of truth they provide:

- stream surfaces
- document/reference surfaces
- work/artifact/system surfaces

This taxonomy is preferable to forcing Slack, Notion, and GitHub into one generic "platform integration" model.

### 6. Current directional leaning: dedicated temporal platform observation domain

If this proposal proceeds, the favored variant is:

- a **separate folder at the context level**
- explicitly **temporal**, not canonical
- used for platform observation artifacts
- eligible for downstream promotion, but not canon by default

Initial shape under consideration:

```text
/workspace/context/platforms/
  README.md                  # explicit policy + trust boundary
  slack/
  notion/
  github/
```

This is **not** a return to the old `/platforms/` root.

It is a bounded, context-level temporal observation layer whose purpose is:

- keep external awareness visible and structured
- support recurring observer tasks
- avoid forcing all external observations directly into canonical domain files
- avoid burying all external state inside task-local directories

---

## Epistemic Model

External reads should default to **temporal**. Canon must be earned.

Three epistemic classes:

### Temporal

Event truth. What changed, what happened, what is active now.

Examples:
- a Slack debate happened
- a Notion page changed yesterday
- a PR is currently in review

### Reference

Trusted external source material. Can be used directly during execution, but is not automatically workspace-owned canon.

Examples:
- a selected Notion spec page
- a repository structure or implementation reality
- a user-uploaded reference doc

### Workspace Canon

YARNNN's own curated, stewarded understanding. Durable state owned by the workspace itself.

Examples:
- `projects/{entity}/status.md`
- `relationships/{entity}/profile.md`
- `competitors/{entity}/profile.md`
- domain synthesis files such as `landscape.md`, `overview.md`, `portfolio.md`

Default rule:

- External read -> temporal or reference
- Distilled conclusion -> eligible for workspace canon

---

## Source Taxonomy

### 1. Stream Surfaces

Examples: Slack

Properties:

- high volume
- high noise
- context-fragmented
- useful for emerging signals, decisions, urgency, and relationship movement
- weak as direct durable truth

Default handling:

- read live
- extract signals
- write to observation layer
- promote to canonical state only through curation

### 2. Document / Reference Surfaces

Examples: Notion pages, selected external docs

Properties:

- more durable than streams
- can act as direct source material
- still mutable and uneven in reliability

Default handling:

- use directly as task input when relevant
- monitor changes when needed
- promote distilled conclusions into workspace canon selectively

### 3. Work / Artifact / System Surfaces

Examples: GitHub issues, PRs, repositories

Properties:

- work artifacts contain operational/project truth
- repositories can contain direct product/system truth
- not well-described by the same model as Slack

Default handling:

- issues / PRs / discussions -> temporal/workstream observation
- repositories -> reference/system understanding
- persist only derived summaries and durable conclusions

---

## Authority Model

### Observation Writes

Allowed from multiple tasks/agents.

Properties:

- append-oriented or provisional
- lower-trust
- reversible or supersedable
- may include candidate interpretations

Examples:

- dated signal summaries
- task-local notes
- candidate updates
- extracted action items
- source observations

### Canonical Writes

Restricted by default to the steward for the target domain.

Properties:

- curated
- durable
- intended as workspace truth

Examples:

- `competitors/{entity}/profile.md`
- `relationships/{entity}/profile.md`
- `projects/{entity}/status.md`
- domain synthesis files

### Default Rule

Non-steward tasks may observe, append, and stage candidate updates.

Steward tasks own canonical mutation by default.

This creates a trust boundary:

- many readers
- many observers
- few curators

---

## Directory Implications

### Durable Context

`/workspace/context/`

Purpose:

- canonical knowledge
- curated domain state
- steward-owned entity files
- steward-owned synthesis files

### Temporal Observation Layer

Current proposed variant:

`/workspace/context/platforms/`

Purpose:

- temporal platform observation
- lower-trust, non-canonical external awareness
- recurring task continuity for platform-observer tasks
- source-specific summaries and candidate findings

Properties:

- not canon by default
- not read as equal to steward-owned domain files
- promotion into canon is explicit or steward-mediated
- bounded by source selection and TTL policy

Example shape:

```text
/workspace/context/platforms/
  README.md
  slack/
    _policy.md
    2026-04-03.md
  notion/
    _policy.md
    2026-04-03.md
  github/
    _policy.md
    2026-04-03.md
```

The policy file exists to make the trust boundary explicit:

- this folder is temporal
- contents are observational, not canonical
- entries may expire or be ignored once stale
- promotion into canonical domains is separate

### Task-Local Observation State

Two initial forms:

- task-local staging under the task workspace
- append-only dated observations in `signals/`

Task-local state remains useful even if a dedicated temporal platform folder exists.

The likely split is:

- task-local state for execution continuity and candidate findings
- `/workspace/context/platforms/` for shared temporal awareness
- canonical domains for steward-owned durable truth

### TTL

Temporal observation requires TTL semantics.

TTL metadata alone is **not** sufficient; it must be enforced somehow.

Two enforcement models:

1. **Soft TTL**
   - expired entries remain on disk
   - readers ignore or deprioritize them
   - lower implementation cost

2. **Hard TTL**
   - expired entries are deleted or compacted by a hygiene job
   - keeps the folder clean
   - requires explicit cleanup logic

Current preference:

- start with **soft TTL**
- add hard cleanup later only if the temporal folder becomes noisy

This does **not** require bringing back backend sync jobs.

A lightweight scheduler hygiene pass is acceptable if needed. That is categorically different from a platform ingestion worker.

---

## Task Roles

External-reading recurring tasks should usually fall into one of three roles:

### Observer

Reads external sources live and produces observations.

Typical writes:

- `signals/`
- task-local working state
- candidate updates

### Curator / Steward

Reads existing context, observations, and optionally external sources. Updates canonical domain files.

Typical writes:

- entity files
- domain synthesis files

### Synthesizer

Reads canonical context and produces downstream outputs.

Typical writes:

- task outputs
- rendered deliverables

This model is preferable to assuming every platform-reading task is also a canonical domain writer.

---

## Platform Guidance

### Slack

Slack is primarily a **temporal observation surface**.

Useful for:

- decisions in motion
- action items
- blockers
- urgency
- relationship signals
- project movement

Default handling:

- read live during task execution
- write observations to temporal observation layer
- stage candidate updates to `relationships/` or `projects/` when appropriate
- canonical promotion occurs through steward curation

Slack content itself should not be treated as workspace canon.

### Notion

Notion is a **hybrid**:

- temporal change surface
- document/reference source

Supported modes:

- monitor what changed
- use selected pages/databases as direct source material
- selectively promote distilled findings into workspace canon

If a temporal platform folder exists, Notion change observations may live there while durable document-derived conclusions are promoted elsewhere.

Notion content is not automatically workspace canon just because it is more structured than Slack.

### GitHub

GitHub should be split into two conceptual modes:

#### A. Work Artifact Surface

Issues, PRs, discussions, comments.

Handling:

- temporal/workstream observation
- useful for `projects/` and `signals/`

#### B. Repository / System Reference Surface

Repositories as source-of-truth about the user's product, system, or implementation reality.

Handling:

- live, selective reads
- reference input during task execution
- persist only derived summaries, architecture understanding, or task-relevant conclusions

GitHub does **not** automatically require its own context domain.

A dedicated technical-context domain should be considered only if repository/system understanding becomes a first-class part of the product model.

If a temporal platform folder exists, GitHub issue/PR observations may live there, while repository/system understanding remains reference-oriented and task-scoped unless explicitly promoted.

---

## Source Selection

Platform observation should be **extremely user-selected**.

This is especially important if a shared temporal folder exists. Without strict source selection, the temporal layer will drift toward a noisy cache.

Implications:

- Slack: selected channels only
- Notion: selected pages/databases only
- GitHub: selected repos only

Default principle:

**No broad workspace mirroring.**

The user should opt into the specific external surfaces that are worth recurring attention.

This keeps the temporal layer:

- bounded
- inspectable
- trustworthy enough for awareness
- resistant to sliding back into background sync philosophy

---

## Product and Architecture Check: Is This Sunk Cost?

This proposal should be rejected if it becomes:

- "platform_content, but in files"
- broad ingestion of all connected platforms
- a hidden cache that other agents treat as canon
- a new default substrate for every task

This proposal is justified only if it remains:

- task-driven
- source-bounded
- explicitly temporal
- TTL-aware
- separate from canon
- promotion-based rather than automatic

The question is not "should platforms have folders because they used to?"

The question is:

**Does a dedicated temporal platform observation layer make recurring autonomous work clearer and more trustworthy than either task-local-only state or direct writes into canon?**

That is the standard by which this should be judged.

---

## Implementation Surfaces If Proceeding

This ADR does not implement them, but if the temporal-folder variant is adopted, these surfaces likely need review:

- directory registry and scaffolding
- workspace initialization
- task type registry for platform observer tasks
- TP working memory / awareness formatting
- primitives and read/write boundaries
- search/query behavior so temporal observations are not mistaken for canon
- scheduler hygiene only if hard TTL is adopted

---

## What This ADR Does Not Decide

- exact format for candidate updates
- whether candidate updates should be explicit files or implicit task-local notes
- whether steward review should be explicit or implicit
- whether some domains should allow broader write authority than others
- whether GitHub warrants a dedicated domain later
- the exact headless live-platform-read tool surface

---

## Consequences

### Positive

- restores a trust boundary between observation and durable truth
- keeps tasks as the single scheduling model
- avoids rebuilding platform sync/cache infrastructure
- lets Slack, Notion, and GitHub behave differently without forcing one ontology
- makes canonical context more defensible

### Negative

- introduces a more explicit distinction between observation and curation
- may slow direct platform-to-canon writes
- may require additional task orchestration between observer and steward tasks

### Risks

- too much process could block useful automation
- if candidate staging is too implicit, ambiguity will return
- if steward-only mutation is too rigid, the system could bottleneck

---

## Open Questions

1. Should candidate updates live only in task-local state, or also in shared observation files?
2. Should steward tasks poll for candidate updates, or be explicitly triggered?
3. Should some domains allow broader write authority than others?
4. Is GitHub repository understanding important enough to deserve its own domain?
5. How should headless agents get live external read capability without collapsing authority boundaries?
6. Should YARNNN explicitly distinguish **reference canon** from **workspace canon** in the product model?
7. Should `/workspace/context/platforms/` exist as a first-class temporal observation domain, or is task-local state + `signals/` sufficient?
8. If `/workspace/context/platforms/` exists, should TTL be soft (read-time) or hard (cleanup-time)?
9. How should TP present temporal platform awareness without implying canonical truth?

---

## Decision Heuristic

If a source read says:

- "what happened?" -> temporal
- "what does this external source currently say?" -> reference
- "what should become durable workspace truth?" -> workspace canon

Default rule:

**External reads are temporal or reference.  
Workspace canon must be earned through curation.**
