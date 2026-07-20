# ADR-328 — Substrate Portability Invariant: Layer 1 is Authoritative & Portable, Layer 2 is Reconstructable Cache

> **Status**: PROPOSED (2026-06-08). **D8 RESOLVED by [ADR-427](ADR-427-binary-native-substrate-and-the-storage-seam.md) (Phases 1–3 Implemented 2026-07-20)** — binary is now Category-1: a content-addressed, attributed revision behind the stream-first storage seam (`services/storage_backend.py`; marker-row CAS + `workspace-cas` bucket, migration 219). `content_url` is no longer stored for versioned binary (serving URLs are minted per-request, ADR-427 D4); legacy raw-lane rows retain it until migrated. Drafted by KVK + Claude. **Verification-hardened 2026-06-08** — the receipt-backed `workspace_files` column audit (below) refined the original two-category model into THREE categories and surfaced one genuine portability gap (`content_url` binaries). The draft's clean "two layers" story was *too coarse* and is corrected here.
> **Decision state (set 2026-06-08 by KVK)**: D1–D7 + D9 + Q1–Q5 are resolved and ready for ratification (the three-category invariant + reconstruction guard + git-export-as-Phase-2 + RLS-as-enforcement). **D8 (the `content_url` binary-portability gap) is DELIBERATELY LEFT OPEN** — not resolved to any option, flagged as a follow-on awaiting real pressure. **No code and no canon edits land until KVK reviews this ADR and ratifies.** This doc is review-ready, not implemented.
> **Date**: 2026-06-08
> **Authors**: KVK, Claude
> **Upstream discourse**: [substrate-portability-swap-test-2026-06-08.md](../analysis/substrate-portability-swap-test-2026-06-08.md) (the swap-test finding — code-vs-canon gap with receipts; F1–F5).
> **Dimensional classification**: **Substrate** (Axiom 1 — what persists vs. what is rebuilt) primary; **Channel** (Axiom 6 — export as the portability surface) secondary.
> **Canon backing**: FOUNDATIONS Axiom 1 (filesystem-is-substrate) + ADR-209 (Authored Substrate) + ADR-298 D2 (`wake_queue` as transient-compute-not-state — the precedent this generalizes) + THESIS Commitment 4 (authored accumulation, portable) + ADR-222 / Derived Principle 16 (literal OS framing).

---

## The one-sentence thesis

**Everything the workspace persists sorts into exactly three categories — Category 1, the *authored semantic filesystem* (`content` via `workspace_blobs` + the `workspace_file_versions` revision chain), which is authoritative, attributed, retained, and portable; Category 2, *reconstructable cache* (the `embedding` column, the tsvector/pgvector indices, `size_bytes`, `head_version_id`), which is transient compute droppable + rebuildable from Category 1; and Category 3, *unversioned head-row sidecar* (`summary`, `tags`, `lifecycle`, `content_type`, `metadata`, `content_url`), which is neither retained in the chain nor a pure cache — operational descriptors written onto the head row.** Portability is a Category-1 property; Postgres is the runtime host, not a substrate property; the falsifiability test of THESIS Commitment 4 is that Category 1 exports to git format. This generalizes ADR-298 D2's `wake_queue` classification, names the third category the verification surfaced, and converts an unstated assumption into a guarded, tested invariant — including an *honest* statement of the one real gap it exposed: **binary assets (`content_url`) live entirely outside Category 1 and are therefore not in the portable export.**

> **Naming note**: the upstream analysis + early draft used "Layer 1 / Layer 2." The verification forced a third bucket, so this ADR uses **Category 1 / 2 / 3** to avoid implying a clean two-layer stack. "Authored truth / reconstructable cache / unversioned sidecar" are the load-bearing names; the numbers are shorthand.

---

## Context — the gap (receipts)

The canon asserts portability as the central moat:
- THESIS Commitment 4: "the operator's workspace is a sovereign, portable artifact … it travels with the operator across any model, any agent layer, any future incumbent. This is the single sharpest technical differentiator YARNNN has."
- ESSENCE: "locked to one model — [we are not]; the substrate is portable across every LLM; that is the point."
- FOUNDATIONS Axiom 1: "`workspace_files` today; **storage-agnostic by design per ADR-106**."

The code does not back the literal reading of those claims:
- `write_revision()` ([authored_substrate.py:264](../../api/services/authored_substrate.py#L264)) issues four raw Supabase table ops; there is no `StorageBackend` interface.
- Search is two Postgres-resident RPCs (`search_workspace` tsvector; `search_workspace_semantic` pgvector + ivfflat).
- Embeddings are a hardcoded OpenAI call ([embeddings.py](../../api/services/embeddings.py)).
- Tenancy is RLS-only, assumed by 40+ unguarded call sites.
- The LLM is Anthropic-hardcoded (`anthropic.py`, no provider abstraction).

A local swap would be a parallel rewrite, not a backend reconfiguration. **So either the canon is false, or the canon is true at a layer the canon never named.** The swap-test (upstream doc) establishes it is the latter: the substrate is two layers, and only Layer 1 carries the portability claim.

**The structural precedent already exists for one Layer-2 thing.** ADR-298 D2 classified `wake_queue` as "transient compute … not authoritative state … the table can be wiped and reconstructed entirely from filesystem state … if that reconstruction is not possible, the classification is wrong and the ADR fails." The `embedding` column and the search indices are *the same kind of thing* and have never received that classification. This ADR gives it to them.

---

## Verification audit — the `workspace_files` column classification (receipts)

Before drafting D1, every column on `workspace_files` (schema: migrations 100 + 112 + 116 + 158 + 159) was traced to its writer and classified. This is the receipt under the reconstructability claim.

| Column | Category | Receipt / reasoning |
|---|---|---|
| `content` | **1 — authored** | the file body; stored in `workspace_blobs` by sha256, versioned in the chain ([authored_substrate.py:145](../../api/services/authored_substrate.py#L145), [:264](../../api/services/authored_substrate.py#L264)) |
| `path`, `authored_by`, `message`, `parent_version_id`, `created_at` | **1 — authored** | the revision row ([158_adr209](../../supabase/migrations/158_adr209_authored_substrate.sql)) — git's commit chain |
| `embedding` (vector 1536) | **2 — cache** | metadata-only column update, not a revision ([workspace.py:30-51](../../api/services/primitives/workspace.py#L30)); re-derivable from `content` via `get_embedding` |
| `size_bytes` | **2 — cache** | `GENERATED ALWAYS AS (octet_length(content)) STORED` — pure function of `content` |
| `head_version_id` | **2 — cache** | denormalized pointer; the chain itself is authoritative ([authored_substrate.py:161-181](../../api/services/authored_substrate.py#L161)) |
| tsvector / pgvector / btree indices | **2 — cache** | derived indices over `content`; rebuildable |
| `summary` | **3 — sidecar** | short descriptor, redundant with `message`, display-only (read truncated to 300 chars — [working_memory.py:937](../../api/services/working_memory.py#L937)); written on head row, **not in chain** |
| `tags` | **3 — sidecar** | derived labels (`["rendered", skill_type, output_format]` — [runtime_dispatch.py:185](../../api/services/primitives/runtime_dispatch.py#L185)); not in chain |
| `lifecycle` | **3 — sidecar** | state enum `ephemeral\|active\|delivered\|archived` ([116_workspace_lifecycle](../../supabase/migrations/116_workspace_lifecycle_version.sql)); operational state, not authored content |
| `content_type`, `metadata` (JSONB) | **3 — sidecar** | provenance descriptors (`skill_type`, `run_id`, `agent_id`, `role`); not in chain |
| **`content_url`** | **3 — sidecar + PORTABILITY GAP** | points at a **binary asset** (PDF/PPTX/PNG) in Supabase Storage, **entirely outside Category 1** ([runtime_dispatch.py:179](../../api/services/primitives/runtime_dispatch.py#L179), [112_workspace_content_url](../../supabase/migrations/112_workspace_content_url.sql)). A git export of Category 1 gets the row but a *dangling pointer* to a binary not in the export. |

**What the audit changed vs. the draft:** the clean two-category model was too coarse. Category 3 (unversioned sidecar) genuinely exists — those fields are neither retained-in-the-chain (so prior values are *lost* on overwrite, unlike `content`) nor pure caches (they're independent inputs, not functions of `content`). The honest invariant must name three categories and must state the binary gap rather than assert clean reconstructability.

**Severity assessment:** Category 3's sidecar fields (`summary`/`tags`/`lifecycle`/`content_type`/`metadata`) are *not load-bearing for portability* — they're descriptors and operational state, re-derivable or losable without losing authored truth. The **one material gap is `content_url` / binaries**: rendered deliverables and uploaded binaries live in Supabase Storage, not in Category 1, so they do not travel in a Category-1 git export. This is the same deferred frontier as ADR-209 §7 (binary preservation) + ADR-249 D6 (persistent images) — now showing up as a *portability* gap, which is the honest place to name it.

---

## Decisions (proposed)

### D1 — Name the three categories in canon (Axiom 1 subsection).

Everything `workspace_files` persists is exactly one of:

- **Category 1 — Authored Semantic Filesystem (authoritative + portable).**
  `content` (in `workspace_blobs`, sha256-keyed — *git's object model*) + the `workspace_file_versions` chain (`path`, `authored_by`, `message`, `parent`, `created_at` — *git's commit chain*). **This and only this is what the portability claim covers.** Nothing in Category 1 is reconstructable from the others. Every Category-1 mutation routes through `write_revision` (ADR-209).

- **Category 2 — Reconstructable Cache (transient compute, droppable + rebuildable).**
  `embedding`, the tsvector/pgvector/btree indices, `size_bytes` (generated), `head_version_id` (denormalized pointer). **Every byte rebuilds from Category 1.** Correctly written outside the revision path. `wake_queue`-class per ADR-298 D2.

- **Category 3 — Unversioned Head-Row Sidecar (operational descriptors, neither retained nor pure-cache).**
  `summary`, `tags`, `lifecycle`, `content_type`, `metadata`, `content_url`. Written onto the head row by `_upsert_workspace_file`, NOT in the revision chain (prior values lost on overwrite), NOT functions of `content`. **Acknowledged honestly:** Category 3 is a *known imperfection* — these fields are not first-class authored truth. They are tolerable because they are descriptors/state, not authored semantic content — EXCEPT `content_url`, which is the binary-portability gap (D8).

Diagnostic test: *drop it and rebuild from `content` + the chain — loses no authored content AND is a pure function of Category 1 → Category 2. Loses authored content → it's a Category-1 violation (some writer bypassed `write_revision`). Neither in the chain nor a pure function of `content`, but also not authored semantic truth → Category 3 (tolerated descriptor) — unless it points at out-of-substrate bytes, then it's the binary gap.*

### D2 — Category 2 is `wake_queue`-class: transient compute, not authoritative state.

Generalize ADR-298 D2's classification. `embedding`, the search indices, `size_bytes`, `head_version_id` are transient compute. They are *correctly* written outside the ADR-209 revision path (embedding writes are metadata-only column updates — [workspace.py:30-51](../../api/services/primitives/workspace.py#L30); `Embed` per ADR-325 produces a derived index, not authored content). This ADR ratifies that those out-of-revision writes are *legitimate Category-2 cache updates*, not Authored-Substrate exceptions — closing the conceptual gap between "ADR-209 says every mutation routes through `write_revision`" and "the embedding column is written directly."

### D3 — Falsifiability check: the reconstruction guard (the ADR-298 Scenario L analog). **[Q3 RESOLVED: both]**

A regression guard asserts the D2 classification is honest: **Category 2 can be dropped and reconstructed from Category 1 alone.** Concretely — for a fixture workspace: clear the `embedding` column + drop the search index → re-run the rebuild path (re-embed eligible files from `content`; rebuild tsvector) → assert `QueryKnowledge` / `SearchFiles` return equivalent results. *If reconstruction is not possible, the classification is wrong and this ADR fails* (verbatim the ADR-298 D2 discipline). **Resolution (Q3): both** — a CI unit test is the regression gate (`api/test_adr328_substrate_portability.py`); a one-time Hat-B eval receipt confirms a *live* workspace reconstructs. The unit test must pass; the eval receipt is the honesty check.

### D4 — Portability falsifiability artifact: Category 1 exports to git format. The STORE stays Postgres (ADR-208 already decided this). **[Q1 RESOLVED: export phases to P2]**

Because `workspace_blobs` *is* a content-addressed object store and `workspace_file_versions` *is* a parent-pointered commit chain, the natural, near-free export of Category 1 is **a git repository**: blobs → git objects, revision chain → commit history, `authored_by` + `message` → commit author + message, paths → working tree. This is the strongest possible demonstration that "Agent OS" + "portable substrate" are load-bearing: an operator (or a foreign LLM) gets a plain directory of files + a full attributed history, readable by any tool that speaks git or POSIX.

**Why the store is NOT git — already-decided, not re-opened.** That `workspace_blobs` + `workspace_file_versions` *are* git's data model invites the obvious question: "then why isn't the store just per-workspace git repos?" **That question was asked and answered: [ADR-208](archive/ADR-208-workspace-git-backend.md) proposed exactly per-workspace bare git repos and was WITHDRAWN** — it created a Postgres-vs-git substrate bifurcation (Axiom 1 violation), imported coordination machinery (branches, clone/push, merge UX) alpha operators don't need, and applied versioning to a curated subset when the same benefits apply uniformly. [ADR-209](ADR-209-authored-substrate.md) was the deliberate answer: **adopt git's three useful capabilities (content-addressed retention, parent-pointer history, authored-by attribution) natively in Postgres, and explicitly EXCLUDE git's coordination machinery** (authored-substrate.md §7: "Branches are out of scope … not a roadmap … explicit exclusions"). ADR-328 D4 therefore commits the *narrow, already-sanctioned* slice: Postgres remains the authoritative store (one host, no bifurcation); **git is the *export format only*** — the portability proof, not the backing store. This re-opens nothing; it operationalizes ADR-209's git-data-model-in-Postgres as a git-data-model-out-to-git export.

**The *commitment* is the keystone; the *mechanism* phases.** D4 ratifies git format as the export target + portability proof. **Resolution (Q1): export is Phase 2** — Phase 1 lands the classification + guard (D1/D2/D3/D5/D8/D9), which is the load-bearing canon move; the export (D4) is the proof artifact and follows once the invariant is named, possibly as its own follow-on ADR. (Alternative export formats — tar+manifest, YARNNN-native bundle — rejected as weaker proofs: only git carries the attributed history that IS the moat per ADR-311.) **Resolution (Q2): delivery is an authenticated route** (`GET /api/workspace/export`), not a primitive — "download your workspace" is an operator sovereignty affordance, not an LLM-surface tool.

### D5 — Re-scope ADR-106's "storage-agnostic" claim honestly.

ADR-106's "swap backing store without changing agent code" is aspirational at the code level (no `StorageBackend` interface exists). **Re-scope, do not delete:** Category 1 is storage-agnostic *in shape* — it is portable and exportable, and its data model (blobs + revision chain + paths) is host-independent. The *current host* is Postgres; that is a runtime fact, not a broken promise. FOUNDATIONS Axiom 1's "storage-agnostic by design per ADR-106" parenthetical is amended to "portable by design (Category 1); Postgres-hosted (runtime)" with a pointer to this ADR. **No false promise of a pluggable backend interface that doesn't exist** — Singular Implementation honesty.

### D6 — Provider coupling (LLM + embeddings) is runtime, explicitly OUT of scope.

Anthropic + OpenAI coupling is **not** a portability violation and this ADR does not touch it. The substrate (Category 1) does not depend on which model authored it — `authored_by` records the model name as *data*, not as a *coupling*. Portability is a Category-1 substrate property, not a runtime-provider property. This decision exists to **prevent the invariant from over-reaching** into "must support local LLMs / must abstract providers," which is a different, non-load-bearing question. The swap-test's local-model half is a *thought experiment that clarified the invariant*, not a feature to build.

### D7 — No new substrate, no new primitive, no schema change (for the invariant itself).

The invariant is a *classification + guard + export commitment*, not new machinery. D1/D2/D5/D8/D9 are canon edits. D3 is a test. D4's export, when implemented, reads existing tables (`workspace_blobs` + `workspace_file_versions`) and emits git — no schema change. The export delivers as a route (Q2 resolved).

### D8 — Name the binary gap honestly: `content_url` assets are OUTSIDE Category 1, therefore outside the portable export.

The verification surfaced one material gap. Rendered deliverables (`RuntimeDispatch` PDFs/PPTX/PNGs) and uploaded binaries live in Supabase Storage, pointed at by the Category-3 `content_url` column — they are **not in Category 1** and therefore **not in a Category-1 git export.** A git export would contain the markdown rows + a *dangling* `content_url` to a binary not present.

**This ADR does NOT close the gap, and (per KVK 2026-06-08) does NOT pre-resolve it to an option — it names the limitation, scopes the three resolutions, and leaves the choice open as a flagged follow-on.** None is forced; the decision waits for real pressure (a binary that genuinely needs to travel):
- **(a) Accept it** — the export carries authored *text* truth (the moat: prose, decisions, accumulated context, attribution) + declared-omitted pointers to binaries that remain in Storage. Honest, documented, lowest cost. The text IS the differentiator; binaries are derivative artifacts.
- **(b) Bundle binaries into the export** — the export route fetches each `content_url` binary from Storage and includes it in the git working tree (git LFS or raw). Complete but heavier; binaries bloat the repo.
- **(c) Bring binaries into Category 1** — content-address binary bytes as blobs (the ADR-209 §7 / ADR-249 D6 deferred frontier). Architecturally cleanest, largest scope, its own ADR; likely re-opens the binary-preservation question.

**Status: OPEN.** Whichever option is chosen, **the binding discipline is: the export must *declare* what it omits** — silent omission would make "portable" a lie; declared omission keeps it honest (the ADR-202 expository-pointer discipline applied to export). That discipline holds for (a) and (b); (c) removes the need for it. The option choice is deferred to the Phase-2 export ADR or to whenever binary portability becomes load-bearing.

### D9 — Category 3 is a tolerated imperfection, named, not hidden. (Q5: RLS is a fourth thing — enforcement, not substrate.)

Category 3 (unversioned head-row sidecar: `summary`, `tags`, `lifecycle`, `content_type`, `metadata`) is an **acknowledged imperfection**, not a clean category we're proud of. These fields are written on the head row, lost-on-overwrite (unlike `content`), and not pure functions of `content`. They are *tolerated* because they carry descriptors/operational-state, not authored semantic truth — losing them loses no moat. **This ADR does not refactor them** (Singular Implementation says don't add machinery for a non-problem). It *names* them so a future change that tries to put *authored semantic content* into Category 3 (e.g., LLM-generated summaries stored only on the row, non-deterministic to rebuild) is recognizable as a violation. **If load-bearing content ever needs Category 3, it must move to Category 1** (become a revision) — that's the rule the naming enforces.

**Q5 RESOLVED — RLS + the ADR-320 gate are a fourth thing: *enforcement*, not substrate.** RLS multi-tenancy and `_is_path_locked(caller_class, path)` are *access-policy enforcement* the host performs over the substrate — they are reconstructable in *shape* (tenancy is `user_id` scoping; the gate is derivable from ADR-320's prefix table) but they are **not a cache and not authored content.** They belong alongside ADR-320's topological permission as "the host's enforcement of a policy Category 1 implies." Not forced into the three-category substrate taxonomy. Named here so the taxonomy stays clean: **three categories of *persisted substrate*; enforcement is orthogonal.**

---

## What this is NOT

- **NOT a pluggable local-storage backend.** The swap is a thought experiment that clarifies the invariant. We are not building a `StorageBackend` abstraction or a local-filesystem driver.
- **NOT local-LLM support or provider abstraction.** Explicitly out of scope (D6).
- **NOT a change to ADR-209.** It *clarifies* the boundary ADR-209 already implies: ADR-209 governs Category 1 (every authored mutation is a revision); Category 2 cache writes were always outside that and are now named as legitimate, not exceptional.
- **NOT a frontend / Files-surface change.** The swap-test demoted the Files surface as the least-fundamental layer; this ADR is purely substrate canon. (The provenance-display + permission-legibility frontend moves remain valid but are separate, lower-priority work.)
- **NOT closing the binary gap.** D8 *names* `content_url` binary portability as a known limitation and defers the fix; it does not solve it.
- **NOT a claim that the export must exist before the canon lands.** D1/D2/D5/D8/D9 (classification + honesty) land in Phase 1; D4 (export) is the Phase-2 proof artifact.

---

## Claim tiering (forced vs chosen — do not let the framing foreclose redesign)

- **FORCED (by evidence + axioms):** the category decomposition exists (the column audit proves Category 2 is derived-from-Category-1 and Category 3 is unversioned sidecar); the reconstructable-cache property for Category 2 is the *only* reconciliation of the code with Axiom 1 + Commitment 4. If Category 2 is NOT reconstructable, the canon is false and must change — not the code. The `content_url` binary gap (D8) is forced-by-evidence — it is a real out-of-substrate pointer, not a framing choice.
- **DP16 / Commitment-4-GROUNDED:** portability-as-the-Agent-OS-test; export-as-falsifiability (D4); the store-stays-Postgres-only-export-is-git split (ADR-208 withdrawal + ADR-209 git-data-model-in-Postgres). Sound while we hold the OS frame + the authored-accumulation moat.
- **DESIGN CHOICE (settled this round, recorded for reversibility):** export *format* = git (D4, over tar/native — only git carries attributed history); guard *shape* = both unit + eval (Q3); export *delivery* = route (Q2); FOUNDATIONS vocabulary = a Derived Principle (Q4 → DP26, see below); export *phasing* = Phase 2 (Q1); binary gap resolution = (a) accept+declare for now (D8).
- **EXPLICITLY OUT OF SCOPE:** pluggable backend; local LLM; provider abstraction (D6); binary-into-Category-1 (D8 option c — own ADR); Category-3 refactor (D9 — non-problem).

---

## Open questions — RESOLVED this round (recorded with reasoning, reversible)

1. **Q1 — Export phasing → RESOLVED: Phase 2.** Phase 1 lands classification + guard (D1/D2/D3/D5/D8/D9 — the load-bearing canon move); D4's git export is the Phase-2 proof artifact, possibly its own follow-on ADR. Rationale: the invariant's value is in *naming + guarding* the categories; the export *demonstrates* it but unblocks nothing.
2. **Q2 — Export delivery → RESOLVED: route** (`GET /api/workspace/export`), not a primitive. "Download your workspace" is operator sovereignty, not an LLM-surface tool.
3. **Q3 — Guard shape → RESOLVED: both.** Unit test = CI regression gate (must pass); one-time Hat-B eval receipt = live-reconstruction honesty check.
4. **Q4 — FOUNDATIONS vocabulary → RESOLVED: a Derived Principle (DP26).** "Authored truth over reconstructable cache (over tolerated sidecar)" becomes a citeable diagnostic, the role DP25 plays for topology. Folding into prose loses the handle future ADRs cite.
5. **Q5 — RLS classification → RESOLVED: a fourth thing (enforcement), not a substrate category** (D9). RLS + the ADR-320 gate are host-enforced access policy, reconstructable in shape but neither cache nor authored content. Named orthogonal to the three substrate categories.

**Remaining genuinely-open (deferred, not resolved):**
- **D8 binary gap** — accepted+declared for now (option a); options (b) bundle-into-export and (c) bring-binaries-into-Category-1 graduate to a follow-on ADR if binary portability becomes load-bearing. This is the one substantive thing left undecided, and deliberately so.

---

## Relationship to other ADRs / canon

- **Generalizes** ADR-298 D2 (`wake_queue` transient-compute classification + Scenario L falsifiability) from one table to all derived state (Category 2).
- **Clarifies** ADR-209 (Authored Substrate) — names the Category-1 boundary it governs; ratifies Category-2 cache writes (embedding column) as legitimate non-revision writes, not exceptions; names Category-3 sidecar as a tolerated imperfection.
- **Builds on** ADR-208 (WITHDRAWN — per-workspace git backend) — D4 cites the withdrawal as the reason the store stays Postgres while only the export is git; re-opens nothing.
- **Clarifies / re-scopes** ADR-106 (storage-agnostic claim) — D5.
- **Backs** THESIS Commitment 4 (portable authored accumulation) with a falsifiability artifact (D4) instead of an assertion.
- **Backs** ADR-310 / ADR-311 (interop / portability face) — the git export is the *bulk* portability complement to the MCP *live-query* portability; both serve "the substrate reaches any LLM."
- **Composes with** ADR-222 + Derived Principle 16 (literal OS framing) — Category 1 = ext4; Category 2 = Spotlight index + page cache; the OS analogy's own filesystem/index distinction, made canon.
- **Surfaces (does not close)** ADR-209 §7 + ADR-249 D6 binary-preservation frontier — D8 names it as a *portability* gap.
- **Preserves** ADR-320 topological permission (orthogonal — permission is *who writes Category 1*; RLS+gate are enforcement per D9/Q5; this ADR is *what is authored truth vs cache vs sidecar*), ADR-325 (Embed produces Category 2), the schema, the primitive surface, the LLM runtime.

---

## Scope / blast radius (if ratified)

**Phase 1 (classification + guard + honesty — the keystone, low risk):**
1. FOUNDATIONS Axiom 1 subsection + **DP26**: three-category decomposition (D1) + Category-2-as-transient-compute (D2) + Category-3-tolerated + RLS-as-enforcement (D9) + amend "storage-agnostic" parenthetical (D5).
2. ADR-106 amend note (D5).
3. Regression guard (D3) — `api/test_adr328_substrate_portability.py`: Category-2 drop+reconstruct equivalence + a Category-1-no-bypass check (no writer puts authored content into Category 3).
4. CLAUDE.md ADR-summary entry; GLOSSARY (Category 1/2/3 + enforcement vocabulary).
5. Document the binary gap (D8 option a) — the export-manifest-declares-omissions discipline noted for Phase 2.

**Phase 2 (export proof — D4, deferred per Q1; possibly own ADR):**
6. Git-format export of Category 1 via `GET /api/workspace/export` (Q2) — reads `workspace_blobs` + `workspace_file_versions`, emits a git repo; manifest declares omitted binaries (D8). Plus an eval-scenario receipt that a real workspace round-trips + a foreign LLM reads it.

No schema change either phase. No Render-service env-var change. No primitive rename.
