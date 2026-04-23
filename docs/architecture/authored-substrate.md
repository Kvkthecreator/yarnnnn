# Authored Substrate

> **Status**: Canonical
> **Date**: 2026-04-23
> **Ratified by**: FOUNDATIONS v6.1 Axiom 1 (second clause) + ADR-209
> **Scope**: The substrate-level commitment that every mutation is attributed, purposeful, and retained. This doc holds the full design rationale, the git-inspiration framing, and the deprecation boundary. ADR-209 is the decision record; this is the durable architecture reference.

---

## Purpose

FOUNDATIONS Axiom 1 originally said *where* state lives: the filesystem holds all semantic state; everything else is stateless computation over it. v6.1 adds a second clause that says *how* state evolves: **every mutation carries authorship and preserves history.** This document explains that clause — what it is, why it is framed as git-inspired but not git-implemented, and what it replaces.

The single most important idea to carry out of this doc: **Authored Substrate is the property, not the feature.** "Versioning" is a consequence. "Diff" is a consequence. "Revert" is a consequence. The property is that every byte in the substrate arrived attributed, purposeful, and retained, and the property applies uniformly to everything in `workspace_files` — not to a curated subset.

---

## 1. What Authored Substrate is

Three substrate-level invariants, enforced at the write path (not by convention, not by sibling audit tables):

| Invariant | Meaning | Enforcement |
|---|---|---|
| **Content-addressed retention** | Every distinct file content is stored immutably, keyed by hash. Overwrites never destroy; they append a new revision that points at the new content. | `workspace_blobs` table (sha256 PK, content). The write path upserts by hash. |
| **Parent-pointered history** | Every revision records the revision it descended from. The revision chain for any path is walkable backward. | `workspace_file_versions.parent_version_id` column. The write path reads the current `head_version_id` and stores it as the new revision's parent. |
| **Authored-by attribution** | Every revision carries an author identity (one of four cognitive layers plus `system:*` actors) and a short message. Writes without attribution are rejected at the boundary. | `workspace_file_versions.authored_by` + `message` columns, required (NOT NULL). Primitive layer threads `authored_by` through every call. |

The *current state* of any path is `workspace_files.head_version_id` pointing at the most recent revision in that path's chain. Reads default to head. Any prior revision is retrievable by id or by offset (e.g., "two revisions ago").

### What the invariants deliver

Each invariant separately enables a property operators and cognitive layers actually use:

- **Content-addressed retention** → nothing is lost. Every prior state of every file is still there. Revert is pointing `head_version_id` at an earlier revision — no restore-from-backup flow.
- **Parent-pointered history** → diff and history traversal are substrate operations. `ListRevisions`, `ReadRevision`, `DiffRevisions` are three primitive calls, not three subsystems.
- **Authored-by attribution** → every cognitive layer's contribution is observable. YARNNN can ask *"what did I write this week?"*; the operator can ask *"what did YARNNN do while I was away?"*; the Reviewer can ask *"has `_risk.md` drifted from the operator's hand?"*

Together, they turn the substrate from a flat filesystem into a **four-dimensional substrate**: path × content × author × time. Every read can be scoped on any axis.

---

## 2. Why this is framed as git-inspired — and what we deliberately don't adopt

Git is the default reference because it is the most widely understood system that already solves these properties. But git bundles five capabilities, and YARNNN only needs three.

### Git's five capabilities, separated

| Capability | What it gives you | YARNNN adopts? |
|---|---|---|
| **Content-addressed immutability** | Every version has a stable hash; nothing is lost to overwrite | ✅ Yes — via `workspace_blobs` |
| **Parent-pointer history (DAG)** | Every version knows what it came from | ✅ Yes — via `workspace_file_versions.parent_version_id` |
| **Authored-by attribution** | Every change has a declared author + intent | ✅ Yes — via `authored_by` + `message` columns |
| **Branching (divergent parallel histories)** | Alternate timelines for experimentation | ❌ **Explicitly out of scope** — see §7 |
| **Distributed replication (clone/push/pull)** | Multiple working copies diverge and reconcile | ❌ **Explicitly out of scope** — see §7 |

### Why the 3/5 split is the right cut

The first three capabilities are **substrate properties** — they describe how a single source of truth stores its history. The last two are **coordination properties** — they describe how multiple independent copies of the source coordinate.

For YARNNN's alpha-operator ICP, coordination is not required. There is one authoritative copy of the workspace — the one YARNNN hosts. Operators consume and supervise via the cockpit (ADR-198), not via local clones. Adopting branching + clone/push would bring (a) merge-conflict UX, (b) smart-HTTP hosting infrastructure, (c) remote-mirroring configuration, (d) dual-substrate reasoning for engineers — all to serve a <10% operator cohort that doesn't exist yet at alpha scale.

The singular-implementation principle (FOUNDATIONS Derived Principle 7) says: *if YARNNN composes, there is no separate Composer.* Applied here: *if the substrate carries authored history, there is no separate git backend.* Adopt the properties; reject the bundled infrastructure.

### The exclusion is structural, not a "not yet"

Branches and distributed replication are **explicitly out of scope** for the Authored Substrate — not items sitting on a backlog. See §7 for the full statement. The short version: YARNNN hosts one authoritative copy of each file, operators supervise through the cockpit (ADR-198), foreign LLMs consult through MCP (ADR-169). The cockpit + MCP surfaces are what replace the coordination affordances in the git toolkit, not deferred placeholders for them.

The three adopted capabilities (content-addressed retention, parent-pointer history, authored-by attribution) are the complete Authored Substrate. Nothing else is required, nothing else is pending.

### Why not literal git (the rejected ADR-208 v1 path)

ADR-208 v1 proposed a per-workspace bare git repo on Supabase Storage backing seven operator-authored files, with `workspace_files` rows demoted to a cache over the git working tree. It was withdrawn before any code shipped. The rejection has three reasons:

1. **It created substrate bifurcation.** Seven paths in git, everything else in Postgres, with routing rules between. The dimensional test (FOUNDATIONS Axiom 0) flagged this immediately — Substrate was being conflated with Mechanism (git's write-mechanism leaked into where the bytes live).
2. **It bought coordination infrastructure nobody had asked for.** Smart-HTTP reverse proxy, merge conflict UX, remote mirroring — six phases of engineering to serve a use case that alpha operators don't yet have.
3. **It applied versioning to a curated subset.** The same benefits (attribution, retention, diff, revert) are just as valuable for `_performance.md`, task outputs, agent memory, and domain entities as for the seven authored files. Scoping versioning to a subset meant designing an inclusion test and maintaining it forever.

The collapse to Authored Substrate resolves all three: one substrate, one write model, universal coverage, no coordination infrastructure until demanded.

### Why not filename-encoded versioning (`/history/v{N}.md`, `thesis-v2.md`, `-archive` folders)

An earlier interim approach (ADR-119 Phase 3) archived evolving files to `/agents/{slug}/history/{filename}/v{N}.md` before overwrites. That approach is also retired by ADR-209. Four failures:

- **No attribution.** A filename can't declare *who* wrote v2 or *why*. You can stuff it in a comment, but there's no enforcement.
- **Manual reversion.** "Revert to v3" means the operator has to know v3 exists and find it. No substrate-level backward walk.
- **Manual comparison.** Diff requires the operator to know which two filenames to diff.
- **Namespace pollution.** Every reader — agents, frontend, search — has to decode *which file is current*. `thesis-v2.md` and `thesis-v3.md` sitting next to `thesis.md` is a constant source of "which one do I read?" drift. The substrate's namespace starts encoding version metadata; every read path must learn the convention.

Git's actual insight isn't branches — it's *"the working tree shows current state; history is a sibling plane."* Filename-versioning violates that. Authored Substrate inherits it.

---

## 3. The CAS + revision-chain model

Three tables. All in Postgres. The substrate itself — not a backing store, not a cache, not a mirror.

```sql
-- Content-addressed store
workspace_blobs (
  sha256 TEXT PRIMARY KEY,
  content TEXT NOT NULL,
  size_bytes INT,
  created_at TIMESTAMPTZ
)

-- Revision chain per path
workspace_file_versions (
  id UUID PRIMARY KEY,
  workspace_id UUID NOT NULL,
  path TEXT NOT NULL,
  blob_sha TEXT NOT NULL REFERENCES workspace_blobs(sha256),
  parent_version_id UUID REFERENCES workspace_file_versions(id),
  authored_by TEXT NOT NULL,
  author_identity_uuid UUID,
  message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
)

-- workspace_files preserved; becomes a head pointer
workspace_files (
  ...existing columns...,
  head_version_id UUID NOT NULL REFERENCES workspace_file_versions(id)
)
```

### The write path (single function, every primitive routes through it)

```python
def write_revision(
    workspace_id: UUID,
    path: str,
    content: str,
    authored_by: str,   # required
    message: str,       # required
    author_identity_uuid: UUID | None = None,
) -> UUID:
    sha = sha256(content)
    upsert workspace_blobs(sha, content)
    prev_head = (
        select head_version_id from workspace_files
        where workspace_id = :workspace_id and path = :path
    )
    new_rev = insert workspace_file_versions(
        workspace_id, path, blob_sha=sha,
        parent_version_id=prev_head,
        authored_by, author_identity_uuid, message,
    ) returning id
    upsert workspace_files(workspace_id, path)
        set head_version_id = new_rev.id
    return new_rev.id
```

Properties this guarantees by construction:

- **Singular write path.** Every primitive that mutates substrate — `UpdateContext`, `WriteFile`, `reviewer_audit.append_decision`, `_append_feedback_entry`, `_compose_and_persist`, every caller — flows through this one function. No mutation can bypass attribution.
- **No silent overwrites.** The content hash is the store key; duplicate content reuses the existing blob, but the revision row is still created — the fact that layer X wrote the same content at time T is itself information.
- **Atomic head advance.** `head_version_id` update and revision insert are one transaction. No window where head points at a stale revision.

### The read path (transparent for current-state reads)

Current-state reads are unchanged:

```python
def read_file(workspace_id, path) -> str:
    row = select content from workspace_files wf
        join workspace_file_versions wv on wf.head_version_id = wv.id
        join workspace_blobs wb on wv.blob_sha = wb.sha256
        where wf.workspace_id = :workspace_id and wf.path = :path
    return row.content
```

Historical reads are new:

```python
def read_revision(workspace_id, path, offset=-1, revision_id=None) -> str:
    # offset=-1 = previous revision, offset=-N = N revisions ago
    # revision_id = specific named revision
    ...
```

### `authored_by` taxonomy

The `authored_by` column is a structured string. The taxonomy maps to FOUNDATIONS Axiom 2 (Identity) cognitive layers plus a `system:*` space for deterministic actors:

| Prefix | Meaning | Example |
|---|---|---|
| `operator` | The workspace's human operator | `operator` |
| `yarnnn:<model>` | YARNNN (meta-cognitive layer) | `yarnnn:claude-sonnet-4-7` |
| `agent:<slug>` | A user-created domain agent | `agent:alpha-research` |
| `specialist:<role>` | A specialist's style distillation | `specialist:writer` |
| `reviewer:<identity>` | The Reviewer seat (human, AI, impersonation) | `reviewer:human`, `reviewer:ai-sonnet-v1` |
| `system:<actor>` | Deterministic system actors (reconciler, cleanup, backfill) | `system:outcome-reconciliation`, `system:backfill-158` |

The prefix is mandatory; the suffix is actor-specific. Primitive handlers set the prefix based on the invoking context; the suffix is resolved from model configuration or slug.

---

## 4. Reading with provenance (how this changes prompts and primitives)

The property unlocks a class of reads that were previously unavailable or expensive.

### Compact index gains a revision dimension

The compact index (ADR-159) today shows YARNNN the *shape* of the substrate. Authored Substrate adds a revision column at near-zero token cost:

```
/workspace/context/_shared/MANDATE.md (2.1KB, r3, operator · 2d ago)
/workspace/context/trading/_operator_profile.md (4.3KB, r7, operator · 4h ago)
/workspace/context/trading/_performance.md (1.8KB, r142, system:outcome-reconciliation · 1h ago)
/workspace/review/decisions.md (12KB, r88, reviewer:ai-sonnet-v1 · 3h ago)
```

This is ~30 tokens extra per workspace for dramatically richer situational awareness. YARNNN now knows *what was just touched, by whom, how many times* — the ambient signal that was previously only extractable by reading files.

### New revision-aware primitives

Three new primitives, minimal surface:

| Primitive | Purpose | Modes |
|---|---|---|
| `ReadRevision(path, offset=-1 \| revision_id)` | Read a specific historical revision | chat + headless + MCP |
| `DiffRevisions(path, from, to)` | Text diff between two revisions of the same path. Pure Python. | chat + headless |
| `ListRevisions(path, limit=10)` | The revision chain for a path, newest first. Returns `(id, authored_by, message, created_at)` tuples. | chat + headless + MCP |

And extensions to existing primitives:

- `ListFiles` / `ListEntities` gain `authored_by`, `since`, `until` filters
- `SearchFiles` results include revision metadata per hit

Notably: **no new write primitive.** Writes still go through `UpdateContext` / `WriteFile` / the existing call sites. Authored Substrate is transparent to the write path's external signature; it only surfaces on reads and queries.

### Prompt posture: "revision-aware reading"

Alongside ADR-173's "accumulation-first execution" posture (*read before you generate*), Authored Substrate adds a second posture:

> **Before acting on accumulated context, check its authorship and freshness.** If the operator just revised `_risk.md` an hour ago, treat that as the most current intent. If `_performance.md` hasn't been reconciled in three days, flag staleness. Revisions carry intent signal — attend to them.

This goes into `tp_prompts/tools_core.py` in Phase 3 of the implementation, referenced from both the workspace and entity profiles.

### Meta-awareness for all four cognitive layers

The property is uniform across cognitive layers. Each gets a mirror it didn't have before:

- **YARNNN** can ask *"what have I been doing lately?"* and see its own activity across the workspace
- **Agents** can see their own prior memory writes and track drift (*"have I changed my domain stance five times this week?"*)
- **Reviewer** can see its own decision rate and recent calls (*"am I approving too much given performance?"*)
- **Operator** can see every other layer's activity (*"what did YARNNN do overnight?"*)

This last one is the **supervision property** that the cockpit model (ADR-198) implicitly demands. The operator is supervising an autonomous team; without Authored Substrate, that supervision is vibes-based. With it, the supervision is concretely observable.

---

## 5. What gets deleted (deprecation manifest)

Singular-implementation discipline: the Authored Substrate replaces several legacy mechanisms, and those mechanisms are deleted in the same cycle. See ADR-209 for the phased manifest; this table summarizes the terminal state.

| Legacy surface | Replacement | Deletion phase |
|---|---|---|
| `/history/{filename}/v{N}.md` subfolder pattern (ADR-119 Phase 3) | Revision chain + `ReadRevision(path, offset)` | Phase 2 |
| `AgentWorkspace._archive_to_history()`, `_cap_history()`, `list_history()` | `write_revision()` (automatic); `ListRevisions` primitive | Phase 2 |
| `KnowledgeBase._archive_to_history()`, `list_history()` | Same | Phase 2 |
| Filename-encoded versioning (`thesis-v2.md`, `-archive` suffix, dated-for-version suffix) | Revision chain on the canonical filename | Convention-banned Phase 2; grep-gated in Phase 5 |
| `workspace_files.version` integer column | `workspace_files.head_version_id` + `workspace_file_versions` | Phase 5 (drop) |
| `workspace_files.lifecycle='archived'` | Revision chain makes this redundant; lifecycle stays only for ephemeral TTL (`working/`, `user_shared/`) | Phase 5 (review + prune) |
| `<!-- inference-meta -->` HTML comment **authorship portion** | Authorship trailer on the revision | Phase 4 (schema simplified) |
| `<!-- inference-meta -->` HTML comment **source-summary portion** | *Kept* — distinct concern (which documents / URLs the inference consumed, which the revision chain doesn't carry) | No deletion |
| ADR-119 Phase 3 status | Superseded in same PR as ADR-209 lands | Phase 2 |
| ADR-208 v1 (withdrawn) | Withdrawn in same PR as ADR-209 lands | Same PR |

The **inference-meta boundary** is the subtlest item. ADR-162 Sub-phase D's HTML comment mashes two concerns: *who wrote this* (authorship) and *what external sources did it consume* (provenance summary — "from 2 documents + 1 URL"). Authored Substrate handles the first; it does not handle the second. Phase 4 simplifies the HTML comment's schema to source-summary only; the frontend's `InferenceContentView` renders authorship from the revision chain instead.

---

## 6. What does *not* get Authored Substrate

Not every persistence store is semantic content. The four permitted DB row kinds from FOUNDATIONS Axiom 1 still exist and are not versioned under Authored Substrate:

| Row kind | Example tables | Why not versioned |
|---|---|---|
| Scheduling indexes | `tasks`, `agents` | Pointers at files; the files are the source of truth, and the files *are* versioned |
| Neutral audit ledgers | `agent_runs`, `token_usage`, `activity_log`, `render_usage` | Already append-only by design; no "previous state" to retain |
| Credentials / auth | `platform_connections`, `mcp_oauth_*` | Opaque encrypted secrets; versioning would expose rotation history as attack surface |
| Ephemeral queues | `action_proposals` | TTL-bounded; not accumulating state |

The boundary is sharp: **semantic content goes through Authored Substrate; the four permitted row kinds do not.** If a new table is proposed and the question arises whether it should be versioned, the answer is: if it belongs in one of the four permitted row kinds, no — and if it doesn't belong in one of them, it probably shouldn't be a table at all, it should be a file.

---

## 7. Out of scope: branches and distributed replication

The two git capabilities we deliberately did not adopt (§2) are **not a roadmap**. They are explicit exclusions from the Authored Substrate's remit, for the reasons §2 lays out: coordination infrastructure serves a use case the cockpit (ADR-198) already replaces, and dragging it in would reintroduce the exact Postgres-vs-git bifurcation that ADR-208 v1 was withdrawn to avoid.

**Branches are out of scope.** YARNNN hosts one authoritative copy of each file per workspace. The `head_version_id` pointer is singular. There is no `workspace_refs` table, no `ManageBranch` primitive, no divergent-revision-chain walking. If an operator needs to compare alternatives, they compare two revisions of the same file (via `DiffRevisions`). If they need to experiment, they revert if the experiment fails (revert is itself a revision, Axiom 7).

**Git portability is out of scope.** There is no `git clone` of a workspace, no git pack export, no `workspace.bundle` endpoint, no smart-HTTP protocol. Operators consume and supervise the workspace through the cockpit; foreign LLMs consult it through the MCP tool surface (ADR-169). Speaking git at the boundary would recreate the coordination-infrastructure tax we rejected.

**Stability guarantee.** The substrate's data-model shape — `parent_version_id` being many-to-one-capable, the one-authoritative-head invariant, the singular `head_version_id` pointer — is not "keeping the door open" for branches or replication. It's the shape the authored-substrate model has on its own merits. If YARNNN ever needs multi-head coordination (it does not today and has no signal it will), that would be a new ADR that would have to argue on its own terms against the ADR-208 v1 withdrawal rationale.

This section exists to prevent drift. An earlier draft of this document framed branches + portability as "deferred-but-recoverable future work," which reads as a roadmap. It was not. The intent was always explicit exclusion. This rewrite makes that clear.

---

## 8. Relationship to other architecture docs

| Doc | Relationship |
|---|---|
| [FOUNDATIONS.md](FOUNDATIONS.md) | Authored Substrate completes Axiom 1's second clause (v6.1). Derived Principle 13 is the implementation rule. |
| [GLOSSARY.md](GLOSSARY.md) | Canonical vocabulary: Authored Substrate, Revision, Revision chain, Head, Authorship trailer (v1.4). |
| [SERVICE-MODEL.md](SERVICE-MODEL.md) | Entity Model gains an Authored-Substrate subsection (Phase 1 doc sweep). |
| [workspace-conventions.md](workspace-conventions.md) | `/history/` convention removed (Phase 2). Authorship-trailer requirement added. Filename-versioning banned. |
| [primitives-matrix.md](primitives-matrix.md) | `ReadRevision`, `DiffRevisions`, `ListRevisions` added. `ListFiles` / `ListEntities` gain authorship filters. (Phase 3.) |
| ADR-106 (Agent Workspace Architecture) | Extended — Authored Substrate is the second-half completion of ADR-106's filesystem-over-Postgres commitment. |
| ADR-119 (Workspace Filesystem Architecture) | Phase 3 (`/history/` subfolder versioning) superseded. Phases 1, 2, 4 preserved. |
| ADR-162 (Inference Hardening Sub-phase D) | Amended — `<!-- inference-meta -->` simplified to source-summary only; authorship comes from revision chain. |
| ADR-194 v2 (Reviewer Layer) | Amended — `reviewer_audit.append_decision` pattern gains free attribution via revision chain; in-file decision entries simplify. |
| ADR-208 v1 (Workspace Git Backend) | **Withdrawn.** Replaced by ADR-209 + this doc. |
| ADR-209 (Authored Substrate) | The decision record for this architecture. Ratifies this doc. |

---

## 9. The one-paragraph version

YARNNN's substrate is the filesystem (Axiom 1). Every mutation to that filesystem carries three substrate-level properties: it is content-addressed (nothing is lost), parent-pointered (history is walkable), and authored (every write declares its author and reason). This is git's philosophy without git's infrastructure — we adopt the three capabilities that describe how a single source of truth stores history, and we defer the two capabilities that describe how multiple copies coordinate. The property applies uniformly to every file in `workspace_files` — no subset, no bifurcation, no separate backend. Legacy `/history/` subfolders and filename-versioning (`thesis-v2.md`) are retired. The result is that every cognitive layer (operator, YARNNN, agents, Reviewer) gets a concrete mirror of its own contributions to the workspace, and every supervisory question ("what has YARNNN done this week?", "how has this risk profile evolved?", "who last touched this file?") becomes a substrate query rather than an inference.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-23 | v1 — Initial canonical doc. Ratified by FOUNDATIONS v6.1 Axiom 1 second clause + ADR-209. Captures the git-inspiration framing (3 of 5 capabilities), the CAS + revision-chain model, the `authored_by` taxonomy, the deprecation manifest (`/history/` pattern and filename-versioning retired), and the deferred-extension gating for branches + git portability. Supersedes ADR-208 v1 (withdrawn) and ADR-119 Phase 3. |
| 2026-04-23 | v1.1 — Branches + distributed replication **reframed as explicitly out of scope, not deferred-future-work.** §7 rewritten from "Future extensions (gated on real operator signal)" to "Out of scope: branches and distributed replication." §2 table bullets changed from "❌ Deferred" to "❌ **Explicitly out of scope**". The "What 'deferred' means concretely" subsection replaced with "The exclusion is structural, not a 'not yet'." Rationale: the v1 phrasing read as a roadmap; the intent was always exclusion. The cockpit (ADR-198) + MCP surface (ADR-169) are what replace git's coordination affordances, not placeholders for them. Corrects drift without altering any shipped code or the three-of-five capability commitment. |
