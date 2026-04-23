# ADR-209: Authored Substrate — Content-Addressed Revisions with Authored-By Attribution

> **Status**: Proposed
> **Date**: 2026-04-23
> **Authors**: KVK, Claude
> **Ratifies**: [docs/architecture/authored-substrate.md](../architecture/authored-substrate.md) (canonical deep-dive) + FOUNDATIONS v6.1 Axiom 1 second clause + Derived Principle 13
> **Supersedes**: ADR-208 v1 (Workspace Git Backend for Operator-Authored Files — withdrawn 2026-04-23, never implemented)
> **Supersedes**: ADR-119 Phase 3 (`/history/` subfolder version history for evolving files)
> **Amends**: ADR-106 (Agent Workspace Architecture), ADR-162 (Inference Hardening Sub-phase D), ADR-194 v2 (Reviewer Layer — `reviewer_audit` in-file entry simplification), ADR-207 v1.2 (open question #1 now resolved)
> **Dimensional classification (FOUNDATIONS v6.0)**: Primary **Substrate** (Axiom 1). Secondary **Identity** (Axiom 2 — every write declares its cognitive layer).

---

## Context

### The gap this ADR closes

FOUNDATIONS Axiom 1 has always said *where* semantic state lives: the filesystem (`workspace_files`). It has not, until v6.1, said *how* state evolves. The gap was tolerable while the workspace was small, but three recent pressures forced the question:

1. **ADR-207 v1.2** explicitly deferred file-versioning for operator-authored files (MANDATE.md, IDENTITY.md, BRAND.md, CONVENTIONS.md, `_operator_profile.md`, `_risk.md`, `review/principles.md`). Without versioning, operator revisions silently overwrote prior intent — acceptable short-term, not architecturally.
2. **ADR-119 Phase 3** had shipped a `/history/{filename}/v{N}.md` subfolder convention for evolving files (AGENT.md, thesis.md, memory). But this approach (a) had no attribution, (b) polluted the namespace with versioning metadata, (c) applied only to a curated "evolving files" subset, (d) required every reader to learn the convention.
3. **ADR-194 v2** introduced a Reviewer audit pattern (`reviewer_audit.py` writing to `/workspace/review/decisions.md`) with its own ad-hoc per-entry attribution header. ADR-162 Sub-phase D had introduced a separate `<!-- inference-meta -->` HTML comment that carried its own authorship. Two patterns, both ad-hoc, neither substrate-enforced — the signal that authorship was trying to exist but had no home.

### What ADR-208 v1 proposed and why it was withdrawn

ADR-208 v1 (2026-04-22) proposed a per-workspace bare git repo on Supabase Storage backing seven operator-authored paths, with `workspace_files` rows demoted to a cache over the git working tree. Six implementation phases, including smart-HTTP hosting, merge conflict UX, external remote mirroring.

The proposal was withdrawn before any code shipped, for three reasons:

1. **It created substrate bifurcation.** Seven paths in git, everything else in Postgres, with routing rules between. FOUNDATIONS Axiom 0's dimensional test flagged this — Substrate was conflated with Mechanism (git's write-mechanism leaked into where the bytes live).
2. **It imported coordination infrastructure nobody had asked for.** Branches, clone/push, remote mirroring — capabilities that serve a <10% developer-fluent operator cohort, delivered via six phases of engineering (smart-HTTP reverse proxy, merge UX, etc.) that alpha does not need.
3. **It scoped versioning to a curated subset.** The same benefits (attribution, retention, diff, revert) apply just as well to `_performance.md`, task outputs, agent memory, and domain entities. Scoping to seven paths meant maintaining an inclusion test forever.

### The reframing

Git is the default reference because it is the most widely understood system solving these problems. But git bundles **five capabilities** and YARNNN needs **three**:

| Capability | YARNNN adopts? |
|---|---|
| Content-addressed immutability | ✅ |
| Parent-pointer history (DAG) | ✅ |
| Authored-by attribution | ✅ |
| Branching (divergent parallel histories) | ❌ deferred — recoverable cheaply when demanded |
| Distributed replication (clone/push/pull) | ❌ deferred — recoverable cheaply when demanded |

The first three describe how a single source of truth stores its history. The last two describe how multiple copies coordinate. Alpha operators consume via the cockpit (ADR-198), not via local clones — we do not need coordination infrastructure.

**ADR-209 commits to the three capabilities, in a Postgres-native implementation, applied uniformly across every file in `workspace_files`.** The architecture is canonically named **Authored Substrate**. No Postgres-vs-git bifurcation. No per-path exceptions. One substrate, one write path, universal coverage.

The full design rationale, the git-capability decomposition, and the deprecation boundary are in [docs/architecture/authored-substrate.md](../architecture/authored-substrate.md). This ADR is the decision record.

---

## Decision

### D1 — Three substrate-level invariants, enforced at the write path

Every mutation to `workspace_files` produces a **revision** that satisfies all three:

1. **Content-addressed retention** — file content stored immutably, keyed by sha256. Overwrites never destroy; they add a revision pointing at new content.
2. **Parent-pointered history** — every revision records the revision it descended from. The revision chain for any path is walkable backward.
3. **Authored-by attribution** — every revision carries an `authored_by` identity string and a `message`. Writes without attribution are rejected at the boundary.

These are invariants of the substrate, not properties of the application layer. The write path enforces them; there is no escape hatch.

### D2 — Three new tables (the minimum viable CAS + revision chain)

```sql
-- Content-addressed store
workspace_blobs (
  sha256 TEXT PRIMARY KEY,
  content TEXT NOT NULL,
  size_bytes INT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
)

-- Revision chain per (workspace_id, path)
workspace_file_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL,
  path TEXT NOT NULL,
  blob_sha TEXT NOT NULL REFERENCES workspace_blobs(sha256),
  parent_version_id UUID REFERENCES workspace_file_versions(id),
  authored_by TEXT NOT NULL,
  author_identity_uuid UUID,
  message TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
)

-- workspace_files preserved; becomes the head pointer
ALTER TABLE workspace_files
  ADD COLUMN head_version_id UUID REFERENCES workspace_file_versions(id);
```

`workspace_files` retains all its existing columns (path, content, summary, tags, embedding, lifecycle, content_url) so read-path code is unchanged for current-state reads. The new `head_version_id` column is the authoritative pointer into the revision chain. Phase 5 audits whether the denormalized `content` column on `workspace_files` can be dropped in favor of joining through `head_version_id → blob_sha → workspace_blobs.content`; the answer may be "keep the denormalization for read performance" — final call made in Phase 5 with data.

### D3 — Single write path: `write_revision()`

All substrate mutations flow through one function:

```python
async def write_revision(
    workspace_id: UUID,
    path: str,
    content: str,
    authored_by: str,           # required — non-empty
    message: str,               # required — non-empty
    author_identity_uuid: UUID | None = None,
    summary: str | None = None,
    tags: list[str] | None = None,
    lifecycle: str | None = None,
) -> UUID:
    """Writes a new revision. Returns the new revision id.

    Enforces:
      - authored_by is non-empty (else ValueError)
      - content is stored idempotently via sha256
      - parent_version_id = current head for (workspace_id, path), or NULL if first write
      - workspace_files.head_version_id is updated atomically in the same transaction
    """
```

Every existing caller of `AgentWorkspace.write`, `KnowledgeBase.write`, `TaskWorkspace.write`, `UserMemory.write`, `reviewer_audit.append_decision`, and direct `workspace_files` INSERT/UPDATE routes through `write_revision`. The existing `.write()` methods preserve their external signatures but become thin wrappers.

**The `authored_by` argument is required at every call site.** No caller-layer defaults; the invoking primitive is responsible for supplying the correct value from the invocation context. This is the Axiom 2 enforcement moment.

### D4 — `authored_by` taxonomy (structured prefix)

`authored_by` is a prefixed string. The prefix maps to FOUNDATIONS Axiom 2's four cognitive layers plus a `system:*` namespace for deterministic actors.

| Prefix | Meaning | Example value |
|---|---|---|
| `operator` | The workspace's human operator | `operator` |
| `yarnnn:<model>` | YARNNN (meta-cognitive layer) | `yarnnn:claude-sonnet-4-7` |
| `agent:<slug>` | A user-created domain agent | `agent:alpha-research` |
| `specialist:<role>` | A specialist's style distillation | `specialist:writer` |
| `reviewer:<identity>` | The Reviewer seat filler | `reviewer:human`, `reviewer:ai-sonnet-v1` |
| `system:<actor>` | Deterministic system actors | `system:outcome-reconciliation`, `system:workspace-cleanup`, `system:backfill-158` |

Primitive handlers resolve the prefix from invocation context:

- `UpdateContext` invoked from chat → `operator` or `yarnnn:<model>` depending on who authored the chat turn
- Task pipeline writes → `agent:<slug>` for the dispatched agent
- Reviewer decisions → `reviewer:<identity>` resolved from `reviewer_identity` on the proposal
- Reconciler writes → `system:outcome-reconciliation`
- Cleanup jobs → `system:workspace-cleanup`

### D5 — Three new read-side primitives

| Primitive | Purpose | Modes |
|---|---|---|
| `ReadRevision(path, offset=-1 \| revision_id)` | Read a specific historical revision. `offset=-1` = previous, `offset=-N` = N revisions ago. | chat + headless + MCP |
| `DiffRevisions(path, from_rev, to_rev)` | Text diff between two revisions of the same path. Pure Python (`difflib.unified_diff`). Deterministic, zero LLM cost. | chat + headless |
| `ListRevisions(path, limit=10)` | The revision chain for a path, newest first. Returns `(id, authored_by, message, created_at)` tuples. | chat + headless + MCP |

And extensions to existing primitives:

- `ListFiles` / `ListEntities` gain optional `authored_by`, `since`, `until` filter args
- `SearchFiles` results include revision metadata per hit (authored_by, created_at)

**No new write primitive.** Writes still go through `UpdateContext` / `WriteFile` / existing call sites. Authored Substrate is transparent to the external write signature; it only surfaces on reads and queries.

### D6 — Compact index surfaces revision metadata

`format_compact_index()` (ADR-159) extends each file entry with revision summary:

```
/workspace/context/_shared/MANDATE.md (2.1KB, r3, operator · 2d ago)
/workspace/context/trading/_performance.md (1.8KB, r142, system:outcome-reconciliation · 1h ago)
/workspace/review/decisions.md (12KB, r88, reviewer:ai-sonnet-v1 · 3h ago)
```

Cost: ~30 tokens extra per workspace compact index. Benefit: YARNNN knows *what was just touched, by whom, how many times* on every turn, without a substrate read. Feeds the "revision-aware reading" prompt posture (D8).

### D7 — Revert is a substrate operation, not a primitive

Revert is implemented as a write through the standard path: reading a prior revision's content and writing it as a new revision with `message="revert to r{N}"`. No new primitive needed; the revision chain naturally records "the operator reverted on date X via a new revision."

Exposed via existing `UpdateContext` / `WriteFile` callers with explicit `revert_to_revision=N` ergonomics at the frontend layer (Phase 4).

### D8 — Prompt posture: "revision-aware reading"

Alongside ADR-173's "accumulation-first execution" posture (read before generating), Authored Substrate adds a second posture to `tp_prompts/tools_core.py`:

> **Before acting on accumulated context, check its authorship and freshness.** If the operator just revised `_risk.md` an hour ago, treat that as the most current intent. If `_performance.md` hasn't been reconciled in three days, flag staleness. Revisions carry intent signal — attend to them.

Referenced from both workspace and entity profiles (ADR-186). Lands in Phase 3.

### D9 — Universal coverage, no bifurcation

Authored Substrate applies to **every file in `workspace_files`**. There is no Postgres-vs-git split, no curated authored-file subset, no per-path exception.

The FOUNDATIONS Axiom 1 four permitted DB row kinds are unaffected — scheduling indexes (`tasks`, `agents`), neutral audit ledgers (`agent_runs`, `token_usage`), credentials (`platform_connections`), and ephemeral queues (`action_proposals`) do not go through `write_revision`. They are not semantic content. The boundary is sharp: semantic content → Authored Substrate; four permitted row kinds → unchanged.

### D10 — Branches and git portability are deferred, not excluded

**Branches** are recoverable via a `workspace_refs` table keyed `(workspace_id, ref_name) → head_version_id` + a `ManageBranch` primitive + divergent revision-chain walking. The DAG substrate (`parent_version_id` can be many-to-one) already supports branching structurally.

**Git portability** is recoverable via an export endpoint that walks `workspace_file_versions` + `workspace_blobs` and synthesizes a git pack file (pygit2/dulwich at the boundary, not at rest). Operators can `git clone workspace.bundle` and work locally; push-back replays incoming commits as revisions through the standard write path.

Neither ships in ADR-209. Each ships when a concrete operator signal demands it (see [authored-substrate.md §7](../architecture/authored-substrate.md)).

---

## Phased implementation

Five phases. Each phase is individually shippable; each phase **must** land with its corresponding legacy deletion in the same PR — no "clean up later" allowances. This is the anti-dual-approach discipline that ADR-194, ADR-195, and ADR-153 lessons all reinforce.

### Phase 1 — Substrate foundation (additive only)

Scope:
- Migration 158: create `workspace_blobs` + `workspace_file_versions`; add `head_version_id` column to `workspace_files`
- Backfill: every existing `workspace_files` row produces one synthetic initial revision (`authored_by='system:backfill-158'`, `message='initial backfill'`, one blob per distinct content)
- New service: `api/services/authored_substrate.py` with `write_revision()` as the sole write function
- No call-site migration yet

**Legacy deleted in Phase 1**: none (additive only).

**Gate**: `workspace_files` reads unchanged; new test writes land revisions correctly; backfill produces exactly one revision per existing file.

### Phase 2 — Write path unification + legacy deletion

Scope:
- Every `workspace_files` write routes through `write_revision` internally. Call sites affected:
  - `api/services/workspace.py` — `AgentWorkspace.write`, `KnowledgeBase.write`, `TaskWorkspace.write` (wrappers over `write_revision`)
  - `api/services/memory.py` — `UserMemory.write`
  - `api/services/reviewer_audit.py` — `append_decision` (decision file becomes a revision)
  - Any direct `workspace_files` INSERT/UPDATE in primitives, services, or routes (grep-sweep in Phase 2)
- `authored_by` threaded through every call site from the invoking primitive's context

**Legacy deleted in Phase 2** (singular-implementation discipline):
- `AgentWorkspace._archive_to_history()`, `_cap_history()`, `_is_evolving_file()`, `list_history()` (`api/services/workspace.py` lines 116–237) — revision chain replaces `/history/` subfolder pattern
- `KnowledgeBase._archive_to_history()`, `list_history()`
- `/history/{filename}/v{N}.md` write pattern in `api/services/primitives/workspace.py` lines 341–346
- `_MAX_HISTORY_VERSIONS` cap constant
- `reviewer_audit.py` per-entry attribution header duplication (authorship now comes from revision, in-file entry simplifies to decision content only)

**Gate**: `grep -rn "history/" api/services/ api/routes/` returns zero live-code references to the versioning pattern (output-folder `history/` references in prompts are fine); `_archive_to_history` returns zero hits; all call sites write successfully with attribution.

### Phase 3 — Read-side primitives + prompt posture

Scope:
- New primitives: `ReadRevision`, `DiffRevisions`, `ListRevisions` — add to `api/services/primitives/` + `registry.py` CHAT_PRIMITIVES / HEADLESS_PRIMITIVES / MCP surface
- Extend `ListFiles` / `ListEntities` with `authored_by` / `since` / `until` filters
- Extend `SearchFiles` results with revision metadata
- Compact index: `working_memory.format_compact_index()` gains revision summary column
- Prompt posture: "Revision-aware reading" section in `api/agents/tp_prompts/tools_core.py`, referenced from workspace + entity profiles
- `docs/architecture/primitives-matrix.md` updated with new rows + modes
- `api/prompts/CHANGELOG.md` entry

**Legacy deleted in Phase 3**: none structural (Phase 3 is additive on the read side).

**Gate**: new primitives callable from chat + headless + MCP; compact index renders revision metadata; rename-protocol grep sweep (CLAUDE.md 7b) confirms primitives-matrix alignment.

### Phase 4 — Cockpit UI + inference-meta simplification

Scope:
- Revision history panel on Work / Context / Agents detail routes (reads `ListRevisions`, shows `r{N}, authored_by, message, ago`)
- Click a revision → diff against current (reads `DiffRevisions`)
- Revert action routes through `UpdateContext` / `WriteFile` with `revert_to_revision=N` ergonomics
- `InferenceContentView` (ADR-162 frontend) simplifies: provenance caption source = revision chain (authorship) + HTML comment (source summary only)
- `api/services/context_inference.py` `_append_inference_meta()` schema reduced to source-summary fields only — authorship fields removed

**Legacy deleted in Phase 4**:
- `<!-- inference-meta -->` authorship fields (kept: source-summary fields — distinct concern)
- Frontend components that assumed old `workspace_files.version` integer

**Gate**: revert round-trip works via UI; inference-meta HTML comment renders only source summary; frontend grep for `workspace_files.version` returns zero.

### Phase 5 — Schema cleanup + final grep gate

Scope:
- Audit `workspace_files.version` usage across entire codebase; drop column if unused (Migration 159)
- Audit `workspace_files.lifecycle='archived'` usage; retain only if still serving ephemeral TTL (`working/`, `user_shared/`); otherwise drop or simplify
- Audit `workspace_files.content` denormalization — keep if read-path performance justifies, drop if join-through is acceptable
- Final grep gate: zero live-code references to `history/` versioning pattern, `_archive_to_history`, `thesis-v2`, filename-versioning patterns across `api/`, `web/`, `docs/architecture/`, `docs/features/`
- CLAUDE.md updated: `/history/` convention reference removed; pointer added to `authored-substrate.md`
- `api/prompts/CHANGELOG.md` entry

**Legacy deleted in Phase 5**:
- `workspace_files.version` integer column (if audit confirms unused)
- Stale `lifecycle` states tied to `/history/` pattern
- Any residual filename-versioning patterns (`thesis-v2.md`, `-archive` suffix) — grep-gated

**Gate**: final grep returns zero. CI lint rule (or repo test) added to enforce no-filename-versioning going forward.

---

## Deprecation manifest (authoritative)

The complete list of what gets deleted and in which phase. Every item has a phase ownership. No item is "TBD."

| Legacy surface | Phase | Replacement |
|---|---|---|
| `/history/{filename}/v{N}.md` subfolder convention (ADR-119 Phase 3) | 2 | Revision chain + `ReadRevision(path, offset=-N)` |
| `AgentWorkspace._archive_to_history()` | 2 | `write_revision()` — automatic history |
| `AgentWorkspace._cap_history()` | 2 | No application-layer cap (optional future workspace-wide revision gc) |
| `AgentWorkspace.list_history()` | 2 | `ListRevisions(path)` primitive |
| `AgentWorkspace._is_evolving_file()` | 2 | Irrelevant — all files get revisions, not only "evolving" ones |
| `KnowledgeBase._archive_to_history()` | 2 | `write_revision()` |
| `KnowledgeBase.list_history()` | 2 | `ListRevisions` |
| `/history/{filename}/v{N}.md` write pattern in `primitives/workspace.py` | 2 | `write_revision()` |
| `reviewer_audit.py` per-entry attribution header duplication | 2 | Authorship trailer on the revision (in-file entry simplifies) |
| Filename-versioning patterns (`thesis-v2.md`, `-archive` suffix, dated-for-version-rather-than-content suffix) | Convention-banned in Phase 2; grep-gated in Phase 5 | Revision chain on the canonical filename |
| `workspace_files.version` integer column | 5 (drop after audit) | `head_version_id` → `workspace_file_versions` |
| `workspace_files.lifecycle='archived'` state | 5 (review + possibly drop) | Revision chain; lifecycle kept only for ephemeral TTL |
| `<!-- inference-meta -->` HTML comment **authorship fields** | 4 | Authorship trailer on the revision |
| `<!-- inference-meta -->` HTML comment **source-summary fields** | *kept* | No deletion — distinct concern (which documents/URLs the inference consumed) |
| ADR-119 Phase 3 as an active implementation target | Phase 2 lands; ADR-119 status banner updated same PR | Marked Superseded in-place |
| ADR-208 v1 as Proposed | Same PR as ADR-209 lands | Marked Withdrawn in-place |

---

## Consequences

### Positive

- **Axiom 1 is complete.** The filesystem substrate now carries its own audit trail, substrate-native. No sibling tables, no ad-hoc conventions.
- **Axiom 2 is enforceable.** "Every file has an author" was aspirational; now the write path rejects unattributed writes.
- **Universal coverage.** Every file gets the benefit. `_performance.md` history, `TASK.md` evolution, agent memory drift — all queryable. The earlier "inclusion test" problem (ADR-208 v1) disappears.
- **Meta-awareness for all four cognitive layers.** YARNNN can see its own activity; agents can see their own memory drift; Reviewer can see its own decision rate; operators can see every layer's contribution. The cockpit's supervision promise (ADR-198) becomes concretely observable rather than vibes-based.
- **Singular implementation.** One substrate, one write path, one attribution model. Replaces three ad-hoc patterns (`/history/` folders, inference-meta authorship, reviewer_audit entry headers).
- **Postgres-native.** No new storage backends, no S3 git repos, no smart-HTTP proxies. Three tables, single-digit-ms write overhead, zero new infrastructure.

### Costs

- **Storage growth.** Every mutation creates a revision row + (if content changes) a blob row. For high-churn files (`_performance.md` reconciled daily; `awareness.md` per-session) this accumulates. Mitigations: content-addressed dedup (identical content shares a blob); optional future workspace-wide revision gc policy (defer until storage signal). Estimated alpha-scale cost: <100MB per workspace per year.
- **Write latency adds one INSERT.** Measured: single-digit ms. Acceptable for every write path in the system.
- **`authored_by` must be threaded through every write call site.** The Phase 2 audit is real work — ~170 call sites across services and routes. Non-trivial but mechanical.
- **Backfill is one-shot but workspace-scaled.** Migration 158 backfills every existing workspace_files row to a synthetic revision. Runs once; measured against dev data before prod.

### Risks and mitigations

- **Dual-approach drift during Phase 2 rollout.** The `/history/` convention and `write_revision` could coexist briefly. Mitigation: Phase 2 **must** delete `_archive_to_history` and `list_history` in the same PR as the write-path migration — no staged rollout.
- **Call-site authored_by drift.** A new primitive could be added with a weak default `authored_by`. Mitigation: `write_revision` rejects empty `authored_by` at runtime; primitive contract test in Phase 2 enumerates primitives and confirms each supplies attribution.
- **Namespace discipline erosion.** A future ADR could reintroduce filename-versioning ("just one exception"). Mitigation: Phase 5 adds a CI lint rule that fails on filename-versioning patterns in `workspace_files.path` writes.

---

## Alternatives considered and rejected

### Alternative 1: Literal git backend (ADR-208 v1)

**Rejected.** Two-substrate bifurcation, unrequested coordination infrastructure, curated-subset inclusion test. See [authored-substrate.md §2](../architecture/authored-substrate.md) for the full rejection rationale.

### Alternative 2: `/history/{filename}/v{N}.md` subfolder (ADR-119 Phase 3 as-is)

**Rejected.** No attribution, manual reversion/comparison, namespace pollution. See [authored-substrate.md §2.4](../architecture/authored-substrate.md).

### Alternative 3: Scoped versioning (authored-file subset only)

**Rejected.** The inclusion test ("does this file deserve versioning?") is a maintenance burden forever. `_performance.md`, task outputs, and agent memory all benefit from attribution + retention; scoping excludes them arbitrarily. Universal coverage at Postgres-INSERT cost is strictly better.

### Alternative 4: Sibling `workspace_audit_log` table

**Rejected.** An audit table is observation-after-the-fact; it can drift from substrate state. Authored Substrate makes substrate state and authorship *the same data* — drift is structurally impossible.

---

## Open questions

1. **Revision gc at scale.** Alpha workspaces accumulate ~100MB/year of revisions; multi-year Pro workspaces could accumulate 1GB+. Do we (a) keep everything forever, (b) prune revisions older than N years, (c) prune to every-Nth-revision for low-value paths? Defer until storage signal. Revisit 6 months post-ADR-209 implementation.
2. **Revert attribution.** A revert by the operator that restores a YARNNN-authored state — is the new revision `authored_by='operator'` (with message "reverted to r5")? Or does the new revision preserve the original author? Current answer: `authored_by='operator'`, message captures the revert. Revisit if confusing in practice.
3. **Cross-workspace author identity.** When an operator's account is deleted, `authored_by='operator'` on historical revisions becomes orphaned. Does the revision preserve the string literal? Answer: yes — `authored_by` is a historical record, not a FK, so account deletion doesn't cascade. `author_identity_uuid` becomes dangling but historical attribution remains legible.
4. **`content` column denormalization on `workspace_files`.** Phase 5 audits whether to keep it for read-path performance or drop in favor of join-through. Final call after production measurements.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-23 | v1 — Initial decision record. Ratifies [authored-substrate.md](../architecture/authored-substrate.md) + FOUNDATIONS v6.1 Axiom 1 second clause + Derived Principle 13. Five-phase implementation. Deprecation manifest authoritative. Supersedes ADR-208 v1 (withdrawn) + ADR-119 Phase 3. Amends ADR-106, ADR-162 Sub-phase D, ADR-194 v2, ADR-207 v1.2. |
