# ADR-209: Authored Substrate — Content-Addressed Revisions with Authored-By Attribution

> **Status**: **Phases 1–5 Implemented 2026-04-23 — ADR FULLY IMPLEMENTED.** Deprecation manifest closed. Phase 1: substrate foundation + backfill. Phase 2: write-path unification + legacy deletion. Phase 3: read-side primitives + compact-index authorship signal + prompt posture. Phase 4: HTTP revision endpoints + cockpit UI + inference-meta simplification. Phase 5: schema cleanup (Migration 159 — dropped `workspace_files.version`, tightened lifecycle constraint, deleted legacy `/history/` artifact row), regression-guard test, final grep gate. Full test suite: 65/65 (11 Phase 1 + 14 Phase 2 + 15 Phase 3 + 13 Phase 4 + 12 Phase 5).
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

### D10 — Branches and distributed replication are explicitly out of scope

The two git capabilities the Authored Substrate does not adopt (D1 §2) are **not a roadmap**. They are explicit exclusions for the same reasons ADR-208 v1 was withdrawn.

**Branches are out of scope.** YARNNN hosts one authoritative copy of each file per workspace. There is no `workspace_refs` table, no `ManageBranch` primitive, no divergent head-pointer walking. The `head_version_id` column is singular by design. Operators who need to compare alternatives use `DiffRevisions` across two revisions of the same file; operators who need to revert from an experiment use the revert path (which is itself a new revision, Axiom 7).

**Distributed replication (clone/push/pull) is out of scope.** There is no `git clone` of a workspace, no git pack export, no `workspace.bundle` endpoint, no smart-HTTP protocol. Operators supervise through the cockpit (ADR-198); foreign LLMs consult through the MCP tool surface (ADR-169). Those two surfaces **replace** the coordination affordances in the git toolkit for YARNNN's ICP — they are not placeholders for them.

**Stability guarantee.** The substrate shape (singular `head_version_id`, one authoritative head per path) is what the Authored Substrate is on its own merits. The `parent_version_id` column being nullable/many-to-one is a general DAG property, not an accommodation for future branching. If a multi-head coordination use case ever emerged, a new ADR would have to argue on its own terms against the withdrawal rationale of ADR-208 v1. Until then, this section exists to prevent roadmap drift.

See [authored-substrate.md §7](../architecture/authored-substrate.md) for the canonical statement.

---

## Phased implementation

Five phases. Each phase is individually shippable; each phase **must** land with its corresponding legacy deletion in the same PR — no "clean up later" allowances. This is the anti-dual-approach discipline that ADR-194, ADR-195, and ADR-153 lessons all reinforce.

### Phase 1 — Substrate foundation (additive only) — **IMPLEMENTED 2026-04-23**

Scope:
- Migration 158: create `workspace_blobs` + `workspace_file_versions`; add `head_version_id` column to `workspace_files`
- Backfill: every existing `workspace_files` row produces one synthetic initial revision (`authored_by='system:backfill-158'`, `message='initial backfill — pre-ADR-209 content'`, one blob per distinct content)
- New service: `api/services/authored_substrate.py` with `write_revision()` as the sole write function + `list_revisions()` / `read_revision()` / `count_revisions()` read helpers + `is_valid_author()` taxonomy validator
- No call-site migration yet

**Legacy deleted in Phase 1**: none (additive only).

**Phase 1 implementation notes**:
- Parent-pointer resolution in `write_revision()` queries `workspace_file_versions` directly (newest row by `created_at DESC`), not the denormalized `workspace_files.head_version_id`. The revision chain is authoritative; the `head_version_id` column is a Phase 2 read-optimization layer kept in sync by the full write path. This decouples Phase 1 from the call-site migration — new revisions chain correctly against the backfilled revisions even though `workspace_files.head_version_id` is not updated by Phase 1 writes on new paths.
- Backfill results against dev DB (user: kvkthecreator@gmail.com): 99 files → 99 revisions → 69 unique blobs (content-addressed dedup confirmed). Every file has `head_version_id` set; every head resolves to a real revision; every revision's `blob_sha` resolves to a real blob.

**Gate**: [api/test_adr209_phase1.py](../api/test_adr209_phase1.py) — 11/11 assertions pass. Table creation, column add, backfill completeness, attribution, head integrity, blob integrity, blob dedup, write round-trip, validation rejection, list+read round-trip, parent-pointer chain all verified against live dev DB.

### Phase 2 — Write path unification + legacy deletion — **IMPLEMENTED 2026-04-23**

Scope:
- Every `workspace_files` write at the content layer routes through `write_revision()`. Call sites migrated:
  - `api/services/workspace.py` — `AgentWorkspace.write` (default `authored_by=f"agent:{self._slug}"`), `UserMemory.write` (default `"system:user-memory"`, overridden to `"operator"` / `"yarnnn:<model>"` where context is known)
  - `api/services/task_workspace.py` — `TaskWorkspace.write` (default `f"task:{self._slug}"`), `save_output` (threads `f"agent:{agent_slug}"`), `append_run_log` (`"system:task-pipeline"`)
  - `api/services/reviewer_audit.py` — `_write_sync` (threads `f"reviewer:{reviewer_identity}"` from `append_decision`)
  - `api/services/primitives/workspace.py` — context writes via `um.write` with caller-driven attribution; ADR-176 Phase 4 entity-profile `history/v{N}.md` archive block DELETED
  - `api/services/primitives/runtime_dispatch.py` — rendered-asset write (`f"agent:{agent_slug}"` when available, else `"system:runtime-dispatch"`)
  - `api/services/outcomes/ledger.py` — `_upsert_performance_file` + summary write (both `"system:outcome-reconciliation"`)
  - `api/routes/documents.py` — operator file share (`"operator"`)
  - `api/routes/chat.py` — conversation.md summary (`"system:conversation-summary"`)
  - `api/routes/workspace.py` — operator file edit (`"operator"`)
  - `api/routes/integrations.py` — trading risk scaffold (`"system:trading-risk-scaffold"`)
- `authored_by` enforcement: `write_revision()` rejects empty attribution with `ValueError`; class wrappers (`AgentWorkspace`, `UserMemory`, `TaskWorkspace`) carry sensible class-scoped defaults that callers with better context can override via the `authored_by` + `message` keyword args

**Class-level defaults rationale** (decision made during Phase 2):
The class wrappers synthesize sensible `authored_by` defaults from their class-scoped context (e.g., `f"agent:{self._slug}"` for `AgentWorkspace` since it's always scoped to one agent). This preserves singular-implementation — there is still exactly one write path enforcing one contract — while avoiding a ~60-call-site uniform-edit diff where most call sites would pass the same class-derivable value explicitly. Callers that represent a different Identity (YARNNN writing an agent file via `UpdateContext` primitive, operator editing via route) override with the `authored_by` keyword argument. The substrate remains the Axiom 2 enforcement point; the wrappers translate class context into substrate-required format.

**Legacy deleted in Phase 2** (singular-implementation discipline, all in same PR as migration):
- `AgentWorkspace._archive_to_history()`, `_cap_history()`, `_is_evolving_file()`, `list_history()` — deleted
- `AgentWorkspace._EVOLVING_PATTERNS`, `_EVOLVING_DIRS`, `_MAX_HISTORY_VERSIONS` class constants — deleted
- `/history/{filename}/v{N}.md` write pattern in `AgentWorkspace.write()` — deleted
- ADR-176 Phase 4 entity-profile `v{N}.md` archive block in `primitives/workspace.py` — deleted (including `_MAX_PROFILE_VERSIONS` cap + `_ENTITY_PROFILE_FILENAMES` constant)
- `workspace_files.version` integer increment in `AgentWorkspace.write()` — deleted (column scheduled for drop in Phase 5)
- All direct `workspace_files` INSERT/UPDATE/UPSERT at the content layer — only two permitted: `authored_substrate._upsert_workspace_file` (the write target itself) and `primitives/workspace._embed_workspace_file` (metadata-only embedding column update, documented as a substrate-permitted exception)

**Gates** ([api/test_adr209_phase2.py](../api/test_adr209_phase2.py) — 14/14 assertions pass against live dev DB):
1. `write_revision` syncs `workspace_files.head_version_id` + `content`
2. `AgentWorkspace.write` routes through substrate with default `authored_by=f"agent:{slug}"`
3. `AgentWorkspace.write` override works
4. `UserMemory.write` defaults to `"system:user-memory"`, operator override works
5. `TaskWorkspace.write` defaults to `f"task:{slug}"`
6. `TaskWorkspace.save_output` attributes to `f"agent:{agent_slug}"`
7. `TaskWorkspace.append_run_log` attributes to `"system:task-pipeline"`
8. `reviewer_audit.append_decision` attributes to `f"reviewer:{identity}"`
9. Parent chain on rewrite: second revision's `parent_version_id` = first revision's id
10. Content + head stay in sync across multiple writes
11. **Grep gate 1**: zero live-code references to any deleted history methods/constants across `api/services/`, `api/routes/`, `api/agents/`, `api/integrations/`, `api/jobs/`, `api/mcp_server/`
12. **Grep gate 2**: only `authored_substrate.py` (the write target) and `primitives/workspace.py` embedding-update (permitted exception) touch `workspace_files` with `insert/update/upsert` — every other mutation routes through `write_revision()`
13. Phase 1 backfill preserved (99 `system:backfill-158` revisions still present)
14. Phase 1 test suite (11/11) also still passes — no regressions

### Phase 3 — Read-side primitives + prompt posture — **IMPLEMENTED 2026-04-23**

Scope:
- New primitives landed in [api/services/primitives/revisions.py](../../api/services/primitives/revisions.py):
  - `ListRevisions(path, limit?)` — revision chain for a workspace path, newest first
  - `ReadRevision(path, offset? | revision_id?)` — read a specific historical revision
  - `DiffRevisions(path, from_rev, to_rev)` — pure-Python unified diff, zero LLM cost
- Registered in both `CHAT_PRIMITIVES` and `HEADLESS_PRIMITIVES` — chat parity intentional (operators + YARNNN both need to inspect authored files through the same API for cockpit supervision per ADR-198)
- `ListFiles` extended with optional `authored_by` (prefix match) + `since` / `until` (ISO 8601) filters — handler applies them via a `workspace_file_versions` query intersected with the path list
- `format_compact_index()` gains a one-line activity summary when `recent_authorship.total > 0`: renders revision counts grouped by cognitive-layer prefix (operator / yarnnn / reviewer / agent / specialist / system). ~20-40 tokens in the busiest case — well under the 600-token ceiling (measured char_count=835 ≈ 208 tokens in test)
- New working-memory signal `recent_authorship` loaded via `_get_recent_authorship_sync()` in `api/services/working_memory.py` — 24h rolling aggregation over `workspace_file_versions.authored_by`
- "Revision-Aware Reading (Authored Substrate, ADR-209)" section added to [api/agents/yarnnn_prompts/tools_core.py](../../api/agents/yarnnn_prompts/tools_core.py) documenting the three primitives, the `ListFiles` filters, the authored_by taxonomy, and the posture: *"Before acting on accumulated context, check its authorship and freshness."* Second-order accumulation-first posture layered on ADR-173's "read before generating"
- [docs/architecture/primitives-matrix.md](../architecture/primitives-matrix.md) updated: three new rows with `file` substrate + `chat ● headless ● MCP ○` availability + `authored-substrate` capability tag; mode totals updated (chat 14→17, headless 16→19); Hard boundaries note acknowledges the chat exception for revision primitives

**Scope adjustments from original ADR-209 draft**:
- `ListEntities` filters (original scope) — **dropped**. `ListEntities` operates on the relational entity layer (agents, memory, tasks), not on the Authored Substrate (which lives in `workspace_files`). Applying `authored_by` / `since` / `until` to `ListEntities` would be a category confusion: it would require `workspace_file_versions` joins for every entity type. The filters live on `ListFiles` (and implicitly on `ListRevisions` via its natural shape).
- `SearchFiles` revision-metadata enrichment (original scope) — **deferred**. Low marginal value given `ListRevisions` exists; callers needing revision-aware search can list revisions per result. Revisit if operator signal shows need.
- `ReadRevision` / `ListRevisions` / `DiffRevisions` **not exposed on MCP surface** — the MCP contract (ADR-169) is intent-shaped (`work_on_this`, `pull_context`, `remember_this`), not substrate-archaeology-shaped. Foreign LLMs that need revision context receive it through `pull_context` results when relevant; adding revision primitives to the MCP surface would break the three-tool intent-shape discipline. This is a conscious departure from original ADR-209 D5 phrasing and is noted in the primitives-matrix MCP row.

**Legacy deleted in Phase 3**: none (Phase 3 is additive on the read side).

**Gates** ([api/test_adr209_phase3.py](../../api/test_adr209_phase3.py) — 15/15 assertions pass):
1. CHAT_PRIMITIVES includes all three new primitives
2. HEADLESS_PRIMITIVES includes all three new primitives
3. HANDLERS dict has all three handler mappings
4. ListRevisions returns chain newest-first with correct attribution
5. ReadRevision with offset=-1 returns previous revision
6. ReadRevision with revision_id returns exact revision
7. ReadRevision rejects ambiguous input (both offset + revision_id)
8. DiffRevisions produces unified diff with correct from/to headers
9. DiffRevisions flags identical blobs (empty diff, identical=True)
10. ListFiles with `authored_by` filter correctly intersects results
11. `_get_recent_authorship_sync` returns correct shape + buckets by cognitive-layer prefix
12. Compact index renders the activity line with revision counts
13. Compact index stays under 600-token ceiling (measured 208 tokens)
14. Phase 1 regression: all 11/11 still pass
15. Phase 2 regression: all 14/14 still pass

**Grep sweep (CLAUDE.md rule 7b)**: 26 consistent references to new primitive names across `api/agents/yarnnn_prompts/`, `docs/architecture/primitives-matrix.md`, `docs/adr/ADR-209-authored-substrate.md`, `CLAUDE.md`, and the primitive service files.

### Phase 4 — Cockpit UI + inference-meta simplification — **IMPLEMENTED 2026-04-23**

Scope:
- Three HTTP endpoints expose the revision-aware primitives to the frontend (`routes/workspace.py`):
  - `GET /api/workspace/revisions?path=...&limit=10` — revision chain newest-first
  - `GET /api/workspace/revisions/{id}?path=...` — specific revision content + trailer
  - `GET /api/workspace/revisions/diff/two?path=...&from_rev=...&to_rev=...` — pure-Python unified diff
- `PATCH /api/workspace/file` gained an optional `message` field. The UI revert action passes `message="revert to revision {shortId}"`; default when omitted is `"edit file {path}"`.
- New frontend component: [web/components/workspace/RevisionHistoryPanel.tsx](../../web/components/workspace/RevisionHistoryPanel.tsx). Reads `listRevisions`, renders as `r{N} · <author chip> · "<message>" · <ago>` newest first. Author chips color-coded by cognitive layer (operator=blue, yarnnn=purple, agent=emerald, reviewer=amber, specialist=cyan, system=zinc) so the ADR-189 four-layer model is visible at a glance. Click a non-head revision → inline diff vs. current via `diffRevisions`. Revert button (non-head rows) → reads old revision content → PATCH `/api/workspace/file` with revert message → chain grows. `revertDisabled` prop hides revert on surfaces where the edit path doesn't route through `PATCH /api/workspace/file` (Agent AGENT.md).
- Panel wired into three surfaces:
  - `MemorySection.tsx` `BrandSection` for `/workspace/context/_shared/BRAND.md` (revert refetches via `api.brand.get()`)
  - `TaskContentView.tsx` `TaskDefinitionView` for `/tasks/{slug}/TASK.md` (revert refetches TASK.md)
  - `AgentContentView.tsx` `AgentRoleBlock` for `/agents/{slug}/AGENT.md` (read-only; agent writes flow via primitives, not PATCH)
- `save_identity` + `save_brand` routes now pass `authored_by="operator"` explicitly (was defaulting to `"system:user-memory"` in Phase 2). Required for the RevisionHistoryPanel to correctly distinguish operator edits from YARNNN inference writes on the same paths.
- `_append_inference_meta` schema simplified: `inferred_at` field dropped. The revision chain already carries `created_at` authoritatively; duplicating timestamp in the HTML comment would violate FOUNDATIONS v6.1 Axiom 1 (substrate-as-source-of-truth). Retained: `target`, `sources`, `gaps`.
- `InferenceContentView.tsx` dropped `formatRelativeAge` + the "Inferred Nh ago" caption. Age now comes from the adjacent `RevisionHistoryPanel` mount when surfaces want it. `parseInferenceMeta` + `InferenceMeta` interface updated to match.
- `web/lib/api/client.ts` gained `listRevisions` / `readRevision` / `diffRevisions` functions.

**Scope adjustment**:
- `ManageContextModal` (CONVENTIONS.md editor) not wired. It's a tab-based transient modal — the panel is a persistent-surface pattern; embedding it in a modal would be awkward and low-value. Users needing convention revision history can read it from the dedicated Context surface (future work) or the Settings / Work surfaces where the panel is mounted on related paths.
- No new `revert_to_revision=N` primitive parameter. Frontend revert is a two-call round-trip (`readRevision` to fetch content → `editFile` with content + explicit message). Reuses the Phase 2–hardened `write_revision` path. The revert IS a new revision in the chain, not a pointer-flip — which is architecturally cleaner (FOUNDATIONS Axiom 7 recursion preserved; revert is itself an authored event).

**Legacy deleted in Phase 4**:
- `inferred_at` field in `_append_inference_meta` output
- `inferred_at: string` in the TS `InferenceMeta` interface
- `formatRelativeAge()` helper in `InferenceContentView.tsx` (no callers)
- "Inferred N ago" caption path in `InferenceContentView.tsx` JSX
- Default `"system:user-memory"` attribution for operator-initiated identity/brand saves (now explicit `"operator"`)

**Gates** ([api/test_adr209_phase4.py](../../api/test_adr209_phase4.py) — 13/13 assertions pass; full ADR-209 suite 53/53):
1. `GET /workspace/revisions` returns chain newest-first with correct attribution
2. `GET /workspace/revisions/{id}` returns specific revision + content
3. `GET /workspace/revisions/{id}` 404 for unknown id
4. `GET /workspace/revisions/diff/two` returns unified diff with correct from/to
5. `PATCH /workspace/file` with `message` lands the custom message on the revision
6. Revert round-trip: read old → PATCH with content + revert message → chain has 4 revisions, head.parent = prior head
7. `_append_inference_meta` drops `inferred_at` (fields = ['sources', 'target'])
8. `_append_inference_meta` keeps target + sources + gaps
9. Backend emits inference-meta comment matching frontend's `META_COMMENT_RE` parser
10. `save_brand` routes operator-attributed revision (`authored_by="operator"`, message "edit BRAND.md (settings surface)")
11. Phase 1 regression: 11/11 still pass
12. Phase 2 regression: 14/14 still pass
13. Phase 3 regression: 15/15 still pass

**Frontend build gate**: `npx next build` — 0 TypeScript errors from Phase 4 changes. Full production build compiles all routes.

### Phase 5 — Schema cleanup + final grep gate — **IMPLEMENTED 2026-04-23**

Scope:
- Migration 159 applied to dev DB:
  - Dropped `workspace_files.version` integer column (post-audit: zero live writers, zero meaningful readers; DB state had 100 rows at default `1`, one residual at `2` from pre-Phase 2 legacy path — now gone)
  - Tightened `workspace_files_lifecycle_check` to `(ephemeral | active | delivered)` — `archived` enum value dropped (no live producers after Phase 2 deleted `_archive_to_history`)
  - Deleted the one residual `/history/{filename}/v{N}.md` artifact row (`/agents/trading-operator/history/AGENT.md/v1.md`) — the last remnant of the superseded ADR-119 Phase 3 convention
- `workspace_files.content` denormalization **retained** after measurement: read-latency delta between denormalized read (0.05ms) and three-table join-through (0.065ms) is negligible, but the FTS index (`idx_ws_fts`) + embedding index (`idx_ws_embedding`) are both defined on `workspace_files.content`. Dropping the column would require rebuilding both indexes on a joined view or on `workspace_blobs` — materially invasive for zero measurable benefit. Decision documented in Migration 159 comment + [authored-substrate.md §3](../architecture/authored-substrate.md).
- Final grep-gate sweep: zero live-code references to `_archive_to_history`, `_cap_history`, `_is_evolving_file`, `list_history`, `_MAX_HISTORY_VERSIONS`, `_MAX_PROFILE_VERSIONS`, `_ENTITY_PROFILE_FILENAMES`, `_EVOLVING_PATTERNS`, `_EVOLVING_DIRS`, `/history/{...}/v{N}.md` literal paths, `thesis-v2.md`-style filename versioning, or `-archive.md` suffix across `api/`, `web/`, `docs/architecture/`, `docs/features/`. Only `docs/adr/ADR-119-*`, `docs/adr/ADR-209-*`, `docs/architecture/authored-substrate.md`, `docs/architecture/GLOSSARY.md`, and `docs/architecture/FOUNDATIONS.md` mention the retired patterns — every mention is part of an explicit deprecation record.
- Permanent CI regression guard: [api/test_adr209_no_filename_versioning.py](../../api/test_adr209_no_filename_versioning.py) runs the grep gate with an allowlist of legitimate deprecation-record files. Any future reintroduction of a banned pattern fails the guard.
- Branches + distributed replication reframed as **explicitly out of scope** (not "deferred future work"). See D10 above and [authored-substrate.md §7](../architecture/authored-substrate.md).
- `docs/database/ACCESS.md` unchanged — Phase 5 schema changes (drop `version`, tighten `lifecycle`) are fully reflected by the migration file itself; access.md doesn't enumerate column lists.

**Legacy deleted in Phase 5**:
- `workspace_files.version` integer column
- `lifecycle='archived'` enum value from the `workspace_files_lifecycle_check` constraint
- The last residual `/history/{filename}/v{N}.md` artifact row in `workspace_files`

**Gates** ([api/test_adr209_phase5.py](../../api/test_adr209_phase5.py) — 12/12 assertions pass; full ADR-209 suite 65/65):
1. `workspace_files.version` column dropped (`information_schema.columns` lookup)
2. Lifecycle check constraint excludes `archived`
3. Zero `%/history/%/v%.md` artifact rows remain
4. `workspace_files.content` column preserved (denormalization intact)
5. FTS + embedding indexes preserved on `workspace_files.content`
6. DB rejects inserts with `lifecycle='archived'` (direct check-constraint test)
7. Smoke write through `write_revision` post-migration round-trips correctly
8. Filename-versioning regression guard passes (`test_adr209_no_filename_versioning.py` — 12 banned-pattern checks)
9. Phase 1 regression: 11/11 still pass
10. Phase 2 regression: 14/14 still pass
11. Phase 3 regression: 15/15 still pass
12. Phase 4 regression: 13/13 still pass

---

## Deprecation manifest (authoritative — **CLOSED 2026-04-23**)

The complete list of what gets deleted and in which phase. Every item has a phase ownership. No item is "TBD." Every item has shipped.

| Legacy surface | Phase | Status | Replacement |
|---|---|---|---|
| `/history/{filename}/v{N}.md` subfolder convention (ADR-119 Phase 3) | 2 | ✅ Deleted | Revision chain + `ReadRevision(path, offset=-N)` |
| `AgentWorkspace._archive_to_history()` | 2 | ✅ Deleted | `write_revision()` — automatic history |
| `AgentWorkspace._cap_history()` | 2 | ✅ Deleted | No application-layer cap |
| `AgentWorkspace.list_history()` | 2 | ✅ Deleted | `ListRevisions(path)` primitive |
| `AgentWorkspace._is_evolving_file()` | 2 | ✅ Deleted | Irrelevant — all files get revisions |
| `KnowledgeBase._archive_to_history()` | 2 | ✅ Deleted | `write_revision()` |
| `KnowledgeBase.list_history()` | 2 | ✅ Deleted | `ListRevisions` |
| `/history/{filename}/v{N}.md` write pattern in `primitives/workspace.py` | 2 | ✅ Deleted | `write_revision()` |
| `reviewer_audit.py` per-entry attribution header duplication | 2 | ✅ Deleted | Authorship trailer on the revision |
| Filename-versioning patterns (`thesis-v2.md`, `-archive` suffix, dated-for-version-rather-than-content suffix) | 2 banned; 5 grep-gated | ✅ Enforced | Revision chain on the canonical filename |
| `workspace_files.version` integer column | 5 | ✅ Dropped (Migration 159) | `head_version_id` → `workspace_file_versions` |
| `workspace_files.lifecycle='archived'` state | 5 | ✅ Dropped (Migration 159 — removed from constraint + purged residual row) | Revision chain; lifecycle kept only for ephemeral TTL |
| The one residual `/agents/trading-operator/history/AGENT.md/v1.md` row | 5 | ✅ Deleted (Migration 159) | — |
| `<!-- inference-meta -->` HTML comment **`inferred_at` field** | 4 | ✅ Dropped | Revision chain's `created_at` |
| `<!-- inference-meta -->` HTML comment **source-summary fields** | *kept* | ✅ Retained | No deletion — distinct concern (which documents/URLs the inference consumed) |
| Default `"system:user-memory"` attribution for operator identity/brand saves | 4 | ✅ Replaced with explicit `"operator"` | `save_identity` / `save_brand` now pass attribution |
| ADR-119 Phase 3 as an active implementation target | 2 | ✅ Superseded in-place | Marked Superseded with inline banner |
| ADR-208 v1 as Proposed | 1+2 | ✅ Withdrawn in-place | Marked Withdrawn with historical banner |

**Permanent regression guard**: [api/test_adr209_no_filename_versioning.py](../../api/test_adr209_no_filename_versioning.py) enforces zero reintroduction of any banned pattern. Ran Phase 5 with 12/12 checks green.

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
| 2026-04-23 | **Phase 1 Implemented.** Migration 158 (`workspace_blobs` + `workspace_file_versions` + `workspace_files.head_version_id`) applied to dev DB. Backfill: 99 files → 99 revisions → 69 unique blobs (content-addressed dedup confirmed). `api/services/authored_substrate.py` lands `write_revision()` + `list_revisions()` + `read_revision()` + `count_revisions()` + `is_valid_author()`. Test gate [api/test_adr209_phase1.py](../api/test_adr209_phase1.py) — 11/11 assertions pass (tables, backfill, head/blob integrity, dedup, end-to-end write, empty-attribution rejection, list+read round-trip, parent-pointer chain). Implementation note: parent resolution queries the revision chain directly, not the denormalized `head_version_id` pointer — decouples Phase 1 from Phase 2's call-site migration. Phases 2–5 proposed. |
| 2026-04-23 | **Phase 5 Implemented — ADR FULLY CLOSED.** Migration 159 applied: `workspace_files.version` column dropped, lifecycle check constraint tightened (`archived` enum value removed), residual `/agents/trading-operator/history/AGENT.md/v1.md` row deleted (last pre-Phase 2 `/history/` artifact). `workspace_files.content` denormalization retained after measurement (0.05ms vs 0.065ms, plus FTS + embedding indexes are defined on that column). Final grep gate confirmed zero live-code references to any banned pattern across `api/`, `web/`, `docs/architecture/`, `docs/features/`. Permanent CI regression guard at [api/test_adr209_no_filename_versioning.py](../../api/test_adr209_no_filename_versioning.py) — 12 banned-pattern checks with an explicit allowlist for deprecation-record files (ADR-119, ADR-209, authored-substrate.md, GLOSSARY.md, FOUNDATIONS.md, CHANGELOG.md, Phase 2+ test files, Migrations 158/159). **Branches and distributed replication reframed as explicitly out of scope** (D10 rewrite, §7 rewrite in authored-substrate.md v1.1) — correcting v1 drift that read as "deferred future work." The three adopted git capabilities are the complete Authored Substrate; nothing is pending. Test gate [api/test_adr209_phase5.py](../../api/test_adr209_phase5.py) — 12/12 assertions pass. **Full ADR-209 suite across all five phases: 65/65** (11+14+15+13+12). Frontend `npx tsc` clean; Phase 4 Next.js build remains green. Deprecation manifest closed — every row shipped. |
| 2026-04-23 | **Phase 4 Implemented.** Three HTTP endpoints expose the revision-aware primitives (`GET /api/workspace/revisions`, `GET /api/workspace/revisions/{id}`, `GET /api/workspace/revisions/diff/two`). `PATCH /api/workspace/file` accepts an optional `message` field used by the UI revert action. New frontend component `RevisionHistoryPanel` wired into BrandSection (MemorySection), TaskContentView (TASK.md), AgentContentView (AGENT.md, read-only). Panel shows `r{N} · <author chip> · "<message>" · <ago>` newest first, with cognitive-layer color coding (operator=blue, yarnnn=purple, agent=emerald, reviewer=amber, specialist=cyan, system=zinc). Non-head revisions are clickable → inline unified diff vs. current; revert button on editable-path surfaces writes the old content back through PATCH `/api/workspace/file` with message `"revert to revision {shortId}"`, landing a new revision in the chain (revert is itself an authored event, not a pointer-flip — preserves FOUNDATIONS Axiom 7 recursion). `save_identity` + `save_brand` routes now pass explicit `authored_by="operator"` so the panel correctly distinguishes operator edits from YARNNN inference writes. `_append_inference_meta` schema simplified: `inferred_at` dropped (substrate's `created_at` is authoritative — dual timestamps violate FOUNDATIONS v6.1 Axiom 1); retained `target` + `sources` + `gaps`. `InferenceContentView` dropped the "Inferred N ago" caption; age now surfaces via the adjacent `RevisionHistoryPanel` when callers want it. `web/lib/inference-meta.ts` `InferenceMeta` interface updated to match backend. Test gate [api/test_adr209_phase4.py](../../api/test_adr209_phase4.py) — 13/13 assertions pass. Full ADR-209 suite across all phases: 53/53 (11 Phase 1 + 14 Phase 2 + 15 Phase 3 + 13 Phase 4). `npx next build` passes cleanly — zero TypeScript errors from Phase 4. **Scope adjustments from original draft**: (a) `ManageContextModal` not wired — transient modal is wrong surface for persistent history; (b) no new `revert_to_revision=N` primitive parameter — UI round-trips through existing readRevision + editFile, reuses Phase 2–hardened write path. Phase 5 (schema cleanup + grep gate) proposed. |
| 2026-04-23 | **Phase 3 Implemented.** Three new read-side primitives live at `api/services/primitives/revisions.py`: `ListRevisions`, `ReadRevision`, `DiffRevisions`. Registered in both CHAT_PRIMITIVES and HEADLESS_PRIMITIVES — chat parity is intentional because operators + YARNNN both need to inspect authored files via the same API (cockpit supervision per ADR-198). `ListFiles` extended with `authored_by` / `since` / `until` filters. Compact index (`format_compact_index`) renders a one-line activity summary when substrate has been written in the last 24h — grouped by cognitive-layer prefix (operator / yarnnn / reviewer / agent / specialist / system), measured at ~208 tokens total (well under 600-token ceiling). "Revision-Aware Reading" posture section added to `yarnnn_prompts/tools_core.py` (picked up by both workspace + entity profiles per ADR-186). Three scope adjustments from original Phase 3 draft: (1) `ListEntities` filters dropped — category confusion (relational layer ≠ Authored Substrate); (2) `SearchFiles` revision-metadata enrichment deferred — low marginal value given `ListRevisions` exists; (3) revision primitives NOT exposed on MCP surface — MCP's intent-shaped contract (ADR-169) rejects substrate archaeology. Test gate [api/test_adr209_phase3.py](../../api/test_adr209_phase3.py) — 15/15 assertions pass. Full suite across all phases: 40/40 (11 Phase 1 + 14 Phase 2 + 15 Phase 3). Phases 4–5 proposed. |
| 2026-04-23 | **Phase 2 Implemented.** Write-path unification across every call site in the codebase; legacy deletion complete. `write_revision()` extended to keep `workspace_files.head_version_id` + `content` + `updated_at` + optional metadata columns in sync on every write. Class wrappers (`AgentWorkspace.write`, `UserMemory.write`, `TaskWorkspace.write`) now route through `write_revision` internally with class-scoped `authored_by` defaults that callers can override via keyword args. `reviewer_audit._write_sync` threads `f"reviewer:{reviewer_identity}"` from `append_decision`. Route-layer direct writes (`routes/documents.py`, `routes/chat.py`, `routes/workspace.py`, `routes/integrations.py`) migrated with explicit attribution. `outcomes/ledger.py` + `primitives/runtime_dispatch.py` migrated. ADR-176 Phase 4 entity-profile `v{N}.md` archive block in `primitives/workspace.py` deleted. **Zero live-code references** to `_archive_to_history`, `_cap_history`, `_is_evolving_file`, `list_history`, `_EVOLVING_PATTERNS`, `_EVOLVING_DIRS`, `_MAX_HISTORY_VERSIONS`, `_MAX_PROFILE_VERSIONS`, `_ENTITY_PROFILE_FILENAMES` anywhere in the codebase. **Only two** `workspace_files` content-layer mutation call sites remain: `authored_substrate._upsert_workspace_file` (the write target) and `primitives/workspace._embed_workspace_file` (permitted metadata-only update for the embedding column). Test gate [api/test_adr209_phase2.py](../api/test_adr209_phase2.py) — 14/14 assertions pass. Phase 1 test suite also re-verified: 11/11 still passing, no regressions. **Key Phase 2 decision**: class wrappers carry `authored_by` defaults derived from class-scoped context rather than forcing ~60 uniform-edit call-site changes — the substrate still enforces the Axiom 2 contract; the wrappers translate class context into substrate-required format. Phases 3–5 proposed. |
