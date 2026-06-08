# Substrate Portability Swap-Test — Is "Agent OS" Load-Bearing or Aspirational?

> **Date**: 2026-06-08
> **Hat**: B (external developer of the system) — this is a *finding* doc. It surfaces a code-vs-canon gap with receipts; the *fix* lands as system canon (ADR-328).
> **Authors**: KVK, Claude
> **Method**: the swap-test — "if we replaced the Postgres-backed `workspace_files` + OpenAI embeddings + Anthropic LLM with a local model + local storage, what survives intact and what is a parallel rewrite?" Used as an axiomatic probe, not an implementation proposal.
> **Triggers**: the filesystem-native / Files-surface / embed-split discourse (this session) → the deeper question "how far does *Agent OS* go, and are we reinventing Claude Code with extra steps?"
> **Verification status (2026-06-08)**: the two-layer model below was *receipt-verified* via a full `workspace_files` column audit (see §"Verification addendum" at the end). The audit **refined the model from two categories to three** and surfaced one genuine portability gap (`content_url` binaries). The body below reads in the original two-layer framing that got us here; the addendum carries the corrected three-category model that ADR-328 ratifies. Read both — the body is the reasoning path, the addendum is the verified conclusion.

---

## The one-sentence finding

**YARNNN's canon asserts the workspace is a "sovereign, portable artifact … that travels with the operator across any model" (ESSENCE; THESIS Commitment 4; FOUNDATIONS Axiom 1 "storage-agnostic by design per ADR-106") — but the implementation is Postgres / Supabase-RLS / pgvector / OpenAI / Anthropic-coupled at the code level, with no storage abstraction. The two claims are reconcilable, but only because the substrate decomposes into two layers — an authoritative, portable Layer 1 and a reconstructable-cache Layer 2 — and that decomposition is currently an *unstated assumption*, not a *guaranteed, tested invariant*.** The same structural move ADR-298 made for `wake_queue` ("transient compute, not authoritative state … the table can be wiped and reconstructed from filesystem state … if that reconstruction is not possible, the classification is wrong and the ADR fails") has never been made for the embedding column or the search indices, even though it is equally true and equally load-bearing.

---

## Why this matters (the axiomatic stake)

The "Agent OS" framing (ADR-222, Derived Principle 16) is canonized as *literal, not metaphorical*. The single sharpest differentiator in THESIS is Commitment 4 — *authored accumulation*:

> "context is authored, attributed, and retained … the operator's workspace is a sovereign, portable artifact that accumulates value over time in a form the operator owns and can inspect … This is the single sharpest technical differentiator YARNNN has. Inferred context commoditizes … Authored context does not commoditize; it … travels with the operator across any model, any agent layer, any future incumbent." — THESIS Commitment 4

And ESSENCE, "What YARNNN Is Not":
> "locked to one model — the substrate is portable across every LLM; that is the point."

If portability is the moat, then "could a foreign model read this workspace?" is not a nice-to-have question — **it is the falsifiability test of the central differentiator.** A claim that cannot be demonstrated is marketing. The swap-test is the instrument that makes the claim falsifiable.

---

## Expected vs observed

### Expected (from canon)
A storage-agnostic substrate. ADR-106 ("storage-agnostic abstraction layer — swap backing store without changing agent code") and FOUNDATIONS Axiom 1 ("`workspace_files` today; storage-agnostic by design per ADR-106") set the expectation that the backing store is pluggable behind an interface.

### Observed (from code) — receipts
There is **no `StorageBackend` interface.** The substrate API issues raw Supabase queries directly.

- **The single write path is Postgres-shaped.** `api/services/authored_substrate.py::write_revision()` (the one door every mutation routes through per ADR-209) executes four raw Supabase table operations:
  - `_upsert_blob` → `db_client.table("workspace_blobs").upsert(...)` ([authored_substrate.py:145-158](../../api/services/authored_substrate.py#L145))
  - `_read_head_revision_id` → `db_client.table("workspace_file_versions").select("id").eq("user_id", ...).order("created_at", desc=True)` ([:161-181](../../api/services/authored_substrate.py#L161))
  - `_insert_revision` → `db_client.table("workspace_file_versions").insert(...)` ([:184-214](../../api/services/authored_substrate.py#L184))
  - `_upsert_workspace_file` → `db_client.table("workspace_files").upsert(...)` ([:217-262](../../api/services/authored_substrate.py#L217))
- **Reads/lists/searches are Postgres-shaped.** `AgentWorkspace` and `UserMemory` issue `.table("workspace_files").select().eq("user_id", ...).execute()` and `.rpc("search_workspace", ...)` directly (`api/services/workspace.py`). No indirection.
- **Search is two Postgres-resident RPCs.** BM25 via `search_workspace` (a `tsvector` SQL function); semantic via `search_workspace_semantic` (a `pgvector` cosine function with an `ivfflat` index). Neither has a non-Postgres path.
- **Embeddings are an external hardcoded call.** `api/services/embeddings.py::get_embedding()` calls OpenAI `text-embedding-3-small`, `dimensions=1536`. No local-model path.
- **Multi-tenancy is RLS-only.** `user_id` scoping is enforced *in the database* (RLS policies on `workspace_files`) and *assumed* by 40+ unguarded Python call sites. There is no application-layer tenancy guard.
- **The LLM is Anthropic-hardcoded.** `api/services/anthropic.py` — 5 `chat_completion_*` functions, ~20+ call sites, no provider abstraction.

**Verdict:** ADR-106's storage-agnosticism is aspirational at the code level. A local swap is a parallel rewrite of `workspace.py` + `authored_substrate.py` + the search layer + the tenancy guards, not a backend reconfiguration behind an interface.

---

## The reconciliation: the substrate is two layers, not one

The gap is not fatal — it is a *layering that was never named*. The swap-test sorts everything in "the filesystem" into two structurally different kinds of thing.

### Layer 1 — the *authored semantic filesystem* (the substrate; the moat; portable)
What it is:
- `workspace_files.content` — markdown / YAML / prose. POSIX-shaped paths (`operation/competitors/acme/signals.md`).
- `workspace_blobs` — content-addressed immutable store, keyed by sha256. **This is git's object model.** ([authored_substrate.py:145-158](../../api/services/authored_substrate.py#L145): "Content-addressed by sha256 … Identical content across workspaces shares a single blob.")
- `workspace_file_versions` — parent-pointered revision chain with required `authored_by` + `message`. **This is git's commit chain.**

Swap-test result: **survives intact.** `git init` a directory, write the files, replay the revision chain as commits — a foreign LLM (local or hosted) reads it with zero translation. This is what ADR-310/311 mean by "portable across every AI" and what ADR-311 calls "an attributed, walkable revision chain … no competitor's agent-filesystem has [it]." Layer 1 is genuinely model-independent and storage-independent *in shape* — the only thing tying it to Postgres is that the *current host* is Postgres.

### Layer 2 — the *derived index machinery + runtime plumbing* (NOT the substrate; NOT portable; not supposed to be)
What it is:
- `workspace_files.embedding` (pgvector) + `search_workspace_semantic` RPC + OpenAI embedding compute.
- `search_workspace` BM25 RPC (`tsvector`).
- RLS multi-tenancy.
- The Anthropic LLM runtime.

Swap-test result: **does not survive — and should not be expected to.** These are *derived indices over* Layer 1 and *runtime that operates over* Layer 1. Critically: **every byte of Layer 2 is reconstructable from Layer 1, and none of Layer 1 is reconstructable from Layer 2.** You can drop the embedding column and re-embed from `content`. You can drop the BM25 index and rebuild it from `content`. You cannot recover a single authored revision from an embedding vector.

This is the exact distinction a real OS makes: **ext4 is the filesystem; Spotlight's index, the page cache, and the process scheduler are not the filesystem** — they are machinery the kernel rebuilds over it. `rm -rf` the Spotlight index and your files are untouched. *The index is reconstructable from the files; the files are not reconstructable from the index.*

### The precedent already exists — for one Layer-2 thing
ADR-298 D2 made *exactly this classification* for `wake_queue`, and named the falsifiability check:

> "The queue is **transient compute + deterministic enforcement, not authoritative state.** Without this classification, ADR-298 would introduce a parallel state-bearing substrate outside the filesystem-is-truth axiom … Scenario L is the falsifiability check that confirms this classification is honest: the queue table can be wiped and reconstructed entirely from filesystem state + existing DB telemetry. **If that reconstruction is not possible, the classification is wrong and the ADR fails.**" — ADR-298 D2

The embedding column and the search indices deserve the same classification and the same falsifiability check. They have never received it. **That omission is the finding.**

---

## Are we reinventing Claude Code with extra steps?

The sharpest version of the operator's question. The swap-test + the canon answer it precisely. The answer is *split*, and conflating the two halves is the trap.

### YES — for the bare file-operation loop. Stop elaborating it.
The canon *cites Claude Code as the precedent it copies*: compaction (ADR-067 — "There is no architectural reason to deviate"), skills.md, sub-agents, the runtime-gate model, "self-running Claude Code" (eval philosophy, commit a0cb990). The primitive set (`ReadFile`/`WriteFile`/`SearchFiles`/`ListFiles`) is Claude Code's tool surface. **The file-operations loop is not the differentiator.** Making the *Files surface* more elaborate (richer file explorer, more file-data-displays, a first-class Finder) is reinventing what Claude Code gets for free by running on a real OS. That instinct — "are we re-inventing what doesn't need to be there" — is correct *about Layer 2 and about the Files surface*.

### NO — for the four THESIS commitments. None exist in Claude Code.
1. **Authored substrate with attributed, walkable revision history** (Commitment 4). Claude Code runs *on* git but does not make attribution *load-bearing for judgment*. YARNNN's Reviewer calibrates against attributed outcomes over tenure.
2. **The detached, persistent judgment seat** (Commitment 2; ADR-320 two-poles). Claude Code is the *commissioned-tool pole* — a harness the human *wields*, gone at session end. YARNNN is the *delegated-agent pole* — a durable seat the human *delegates authority to*, that runs in the human's absence.
3. **Topology-as-permission — `access(2)` for the agent OS** (ADR-320, DP25). Five roots, a caller×root matrix. Claude Code has no concept of "the Reviewer may amend `constitution/` but not `governance/`; a foreign MCP caller may write only `operation/`." This only exists because there are *multiple non-human caller classes with different authority* — which only exists because of #2.
4. **Portability as the distribution face** (ADR-310/311). The substrate is reachable by *any* LLM via MCP; the model is interchangeable.

**The clarifying reframe:** "Agent OS" does not mean "we reimplement an OS's storage." It means *the operator's relationship to their work is OS-shaped* — a sovereign, inspectable, portable filesystem; multiple caller-classes operating over it under a topological permission model; a persistent seat running against it in their absence; the whole thing reconstructable from authored truth. By that definition, Layer 1 + the permission topology + the judgment seat ARE the Agent OS; Layer 2 is implementation that happens to live in Postgres today.

---

## What this implies for the original frontend question (it reverses the prior emphasis)

The prior session draft leaned toward making Files more first-class. The swap-test demotes that:

- **The frontend importance of a richer Files surface is LOW.** Claude Code proves you don't need a built-in file browser — it borrows the real OS's Finder. A fancier Files surface is the *least fundamental* layer of the whole question.
- **The OS metaphor's frontend payoff is the two things only Layer 1 can show that a Finder cannot:**
  1. **Attribution / provenance** — "who authored this claim, how did it evolve, has it been judged." The revision panel (`RevisionHistoryPanel.tsx`, ADR-209 Phase 4) — already built. This is `git log` surfaced as L3, and it is the moat made visible.
  2. **The permission topology made legible** — which root, who-can-write (ADR-320 as a visible Channel, Axiom 6).
- **Files stays exactly where the canon put it**: L1 raw escape hatch (ADR-245), windowed, operator-pinnable, never kernel-fixed. Home stays the cockpit. The upload affordance is a minor ergonomic fix, not a strategic surface.

The single most fundamental move surfaced by this discourse is **not** about the Files surface at all. It is: **make portability a tested invariant rather than an asserted line.**

---

## Findings (each recommends a system-side change; the fix lands in ADR-328)

1. **F1 — The two-layer decomposition is unstated.** Canon treats "the filesystem" as one thing. It is two: Layer 1 (authoritative, portable) and Layer 2 (reconstructable cache). *Recommend:* name the decomposition in FOUNDATIONS Axiom 1, generalizing the ADR-298 `wake_queue` classification to all Layer-2 machinery (embeddings, BM25 index).

2. **F2 — The reconstructable-cache property is ungUaranteed and untested.** It is *probably* true today (embedding writes are metadata-only column updates, not revisions — [workspace.py:30-51](../../api/services/primitives/workspace.py#L30); `Embed` per ADR-325 produces a derived index, not authored content) but nothing guards it. A future change could make a Layer-2 index hold semantic content not present in Layer 1 — the exact silent-substrate-violation class that ADR-321 fixed when `scope='context'` wrote into a deleted root. *Recommend:* a regression guard shaped like ADR-298 Scenario L — assert that Layer 2 is droppable + reconstructable from Layer 1.

3. **F3 — Portability is asserted, not demonstrated.** No artifact proves a workspace exports to a foreign-readable form. Given `workspace_blobs` + `workspace_file_versions` *are* git's object + commit model, a git-format export is the natural, near-free proof — and the strongest possible evidence that "Agent OS" is load-bearing. *Recommend:* commit to an export target (git format, leading hypothesis) as the falsifiability artifact for Commitment 4. (Mechanism may be deferred to a phase; the *commitment* is the keystone.)

4. **F4 — ADR-106's "storage-agnostic" claim is aspirational and should be re-scoped honestly.** *Recommend:* ADR-328 reframes it: Layer 1 is storage-agnostic *in shape* (portable, exportable); the *current host* is Postgres and that is a runtime fact, not a substrate property. No false promise of a pluggable `StorageBackend` interface that doesn't exist.

5. **F5 — The LLM and embedding providers are runtime, not substrate — and that's correct.** Anthropic/OpenAI coupling is *not* a portability violation. The substrate (Layer 1) does not depend on which model wrote it (`authored_by` records the model name as data, not as a coupling). *Recommend:* ADR-328 explicitly scopes provider-coupling OUT — portability is a Layer-1 substrate property, not a runtime-provider property. This prevents the invariant from over-reaching into "must support local LLMs," which is a different (and non-load-bearing) question.

---

## What is forced vs. chosen (claim tiering — do not let the framing foreclose redesign)

- **FORCED (by evidence + axioms):** the two-layer decomposition exists (the receipts prove Layer 2 is derived-from-Layer-1); the reconstructable-cache property is the *only* thing that reconciles the code with Axiom 1 + Commitment 4. If Layer 2 is NOT reconstructable, the canon is false and must change, not the code.
- **DP16/Commitment-4-GROUNDED:** portability-as-the-Agent-OS-test; export-as-falsifiability. Sound while we hold the OS frame + the authored-accumulation moat.
- **DESIGN CHOICE (open to pushback):** the export *format* (git vs tar-of-files+manifest vs a YARNNN-native bundle); whether export ships now or is deferred to a phase; whether the guard is a unit test, an eval scenario, or both; whether Layer-1/Layer-2 gets new FOUNDATIONS vocabulary or folds into the existing Axiom 1 subsections.
- **EXPLICITLY OUT OF SCOPE:** a pluggable local-storage backend (the swap is a *thought experiment* that clarifies the invariant, NOT a feature to build); local-LLM support; provider abstraction. These are runtime concerns; the invariant is a substrate concern.

---

## The honest tension, stated plainly (for the ADR to resolve)

> Canon: "the operator's workspace is a sovereign, portable artifact … it travels with the operator across any model."
> Code: a multi-tenant Postgres database with RLS, pgvector, tsvector, hardcoded OpenAI + Anthropic.

These are reconcilable — Layer 1 *is* portable, Layer 2 *is* a rebuildable cache — but that reconciliation is an **unstated assumption**, not a **guaranteed property**. ADR-328's job is to convert the assumption into a tested invariant: name the layers, declare authored-truth authoritative and cache reconstructable, pick the export target as the falsifiability artifact, and add the guard. That single decision does more for the Agent-OS thesis than any frontend file work — because it makes the central differentiator falsifiable instead of merely asserted.

---

## Verification addendum (2026-06-08) — the two-layer model was too coarse; it's three categories + one real gap

The reconstructable-cache claim (F2) was load-bearing enough to demand a receipt before canonizing. A full `workspace_files` column audit (schema migrations 100 + 112 + 116 + 158 + 159, each column traced to its writer) produced the verified classification. **Finding: the clean "Layer 1 / Layer 2" binary is wrong. There are three categories of persisted substrate + a fourth orthogonal thing (enforcement) — and one genuine portability gap.**

### The verified three categories

| Column(s) | Category | Receipt |
|---|---|---|
| `content` (in `workspace_blobs`), `path`, `authored_by`, `message`, `parent_version_id`, `created_at` | **1 — Authored truth** (the moat; in the revision chain) | [authored_substrate.py:264](../../api/services/authored_substrate.py#L264); [158_adr209](../../supabase/migrations/158_adr209_authored_substrate.sql) |
| `embedding`, `size_bytes` (generated), `head_version_id`, tsvector/pgvector indices | **2 — Reconstructable cache** (drop + rebuild from Cat 1) | [workspace.py:30-51](../../api/services/primitives/workspace.py#L30) (embedding is metadata-only, not a revision) |
| `summary`, `tags`, `lifecycle`, `content_type`, `metadata`, **`content_url`** | **3 — Unversioned head-row sidecar** (NOT in chain, NOT a pure cache) | `_upsert_workspace_file` writes these on the head row only; lost-on-overwrite |
| RLS multi-tenancy + ADR-320 `_is_path_locked` gate | **(4) — Enforcement, orthogonal** | host-enforced access policy; reconstructable-in-shape but neither cache nor content |

### What the audit changed vs. the body's two-layer story

1. **Category 3 genuinely exists.** `summary`/`tags`/`lifecycle`/`content_type`/`metadata` are written on the head row, are *lost* on overwrite (unlike `content`, which is retained in the chain), and are *not* functions of `content` (they're independent inputs). So they are neither authored-truth-in-the-chain nor pure-reconstructable-cache. The two-layer model had no home for them. **Severity: low** — they're descriptors and operational state, re-derivable or losable without losing the moat.

2. **One material gap: `content_url` / binaries.** This is the sharp finding. `content_url` ([runtime_dispatch.py:179](../../api/services/primitives/runtime_dispatch.py#L179)) points at a *binary asset* (PDF/PPTX/PNG) in Supabase Storage — **entirely outside Category 1.** A git export of Category 1 would carry the markdown row + a *dangling pointer* to a binary not in the export. This is the ADR-209 §7 / ADR-249 D6 deferred binary-preservation frontier, now appearing as a *portability* hole. ADR-328 D8 names it honestly (accept + declare-in-manifest for now; bundle-into-export or bring-into-Category-1 are deferred options).

3. **The reconstructability claim is TRUE for Category 2, with a caveat.** Nothing I found puts *authored semantic content* into Category 2 or 3 today (`summary` is a short descriptor redundant with `message`, read display-only at [working_memory.py:937](../../api/services/working_memory.py#L937); `metadata` carries provenance like `skill_type`/`run_id`, not reasoning content). So the invariant holds *now*. The risk the guard must catch: a *future* change that stores LLM-generated semantic content only on the head row (e.g., a generated summary not in any revision, non-deterministic to rebuild) — that would be the violation. The D3 guard + D9 naming exist to make that recognizable.

### Why verifying first mattered (the discipline receipt)

Had we canonized the two-layer model as drafted, FOUNDATIONS would now assert a clean binary that the schema contradicts, and the "portable export" claim would silently omit binaries — making "portable" a lie by omission. The verification converted F2 from "probably true" to "true for Cat 2, here are the receipts, and here is the one real gap (binaries) named honestly." That is the Hat-B discipline working as intended: receipts under the load-bearing claim *before* it becomes Hat-A canon.
