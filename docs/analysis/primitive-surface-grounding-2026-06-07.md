# Discourse — Re-grounding the Primitive Surface to the Filesystem-Native Architecture

> **Status**: DISCOURSE (2026-06-07). Evidence-gathering + argument, not a decision. Feeds: a possible ADR-321 amendment, a possible new ADR, and a possible FOUNDATIONS/SERVICE-MODEL revisit. No canon edited by this doc.
> **Hat**: A (system canon — `api/services/primitives/`, `docs/architecture/`). System vocabulary throughout.
> **Authors**: KVK, Claude
> **Upstream**: ADR-320 (five-root permission topology made the workspace a real filesystem) + ADR-321 draft (path-native file primitives — the narrow forced slice) + the operator's framing: *"because our file-system is native, the InferContext confusion is both problematic AND a hint at a future consideration of how we handle files at large… we need an axiomatic-level revisit of the primitives that reflects the architecture + service-model vision."*
> **Receipts discipline**: every load-bearing claim below carries a `file:line` or migration receipt. Two Explore sweeps (entity-layer reality + file-ingestion reality) are the evidence base.

---

## 0. The question, stated at the right altitude

The operator's grep/bash instinct is not "rename some primitives." It is: **post-ADR-320 the workspace is a literal five-root filesystem with first-class revision history (ADR-209). Does the primitive surface still reflect a pre-filesystem-native world — multiple half-overlapping mental models for "a file" and "a record" — or has it earned its current shape?**

Three sub-questions, smallest to largest:

1. **`scope='context'` addresses a dead root.** (Settled — ADR-321 owns it.)
2. **Is the `context` substrate *family* a fiction now?** (Strong yes — argued in §3.)
3. **Is the `entity` layer one abstraction more than a filesystem-native OS needs?** (The real open question — §4.)

Plus the operator's orthogonal axis, which cuts across all three:

4. **The file-operation taxonomy.** Upload ≠ infer ≠ embed ≠ author ≠ render. Are these N kinds of operation deserving N primitives, or one substrate with operations layered on top? (§5 — and the answer reframes 1–3.)

---

## 1. What the substrate actually is now (the ground truth all four questions stand on)

Two facts, both receipt-confirmed, that the pre-ADR-320 primitive surface predates:

**FACT A — Authored Substrate is genuinely first-class. Every content write is one attributed revision.**
100% of content-mutating writes to `workspace_files` route through `services/authored_substrate.py::write_revision()` (`authored_substrate.py:264`). The full writer inventory:

| Writer | Receipt | → `write_revision`? |
|---|---|---|
| WriteFile (workspace/context/agent) | `primitives/workspace.py:527-707` | ✅ |
| InferContext | `primitives/infer_context.py:170-176` | ✅ |
| Document upload | `services/documents.py:197-206` | ✅ |
| RuntimeDispatch (asset render) | `primitives/runtime_dispatch.py:167-186` | ✅ |
| Outcome reconciler | `outcomes/ledger.py:300-313` | ✅ |
| Cross-domain money-truth summary | `outcomes/ledger.py:823-836` | ✅ |
| Bundle fork | `services/programs.py:586-591` | ✅ |
| Kernel mirrors (schedule/recent-exec) | `kernel_mirrors.py:44-45` | ✅ |
| ShareFile | `routes/documents.py:291-333` | ✅ |
| Embedding / tag / lifecycle | metadata-only | ❌ (correct — not content) |

The *only* bypass is metadata-only updates (embedding vector, tags, lifecycle flag) — which are derived indexes, not content, and correctly don't create a revision. **Implication: the substrate already unifies "kinds" of writes.** Upload, infer, render, reconcile, fork all land as `write_revision(path, content, authored_by, message)`. The cognitive layer is carried in `authored_by` (`operator` / `agent:*` / `reviewer:*` / `system:*` / `yarnnn:mcp`); the operation is carried in `message` (`upload X` / `infer X` / `render X` / `reconcile X`). This is FOUNDATIONS Axiom 2 embodied in the substrate.

**FACT B — the workspace root is five semantic-class roots, and permission is `access(2)`.**
ADR-320: `governance/ constitution/ persona/ operation/ system/` (+ per-agent `agents/{slug}/`, ephemeral `working/`, uploads `uploads/`). Write-permission derives from `(caller_class, top-level-root)` via one `_is_path_locked` prefix table. The path IS the address; the root IS the scope.

**These two facts together are the lens.** A primitive surface designed *after* A+B would look different from the one we have, which accreted across the project/PM era (ADR-138-deleted), the task era (ADR-231-thinned), and the user_memory era (ADR-196-dropped). The surface is archaeological; A+B are the present.

---

## 2. The surface as it stands (counted honestly)

36 primitives, 8 declared substrate families (`entity / file / context / lifecycle / action / interaction / external / introspection`). The four families this discourse interrogates:

- **`file`** — `ReadFile WriteFile SearchFiles ListFiles QueryKnowledge ReadAgentFile`. Path-based over `workspace_files`. **This is the grep/bash-native surface.** Healthy.
- **`context`** — per the matrix (`primitives-matrix.md:113-121`), this "family" is `InferContext` + `WriteFile(scope='context')` + `Schedule`. See §3 — it's already dissolved at the substrate level; the matrix admits it.
- **`entity`** — `LookupEntity ListEntities SearchEntities EditEntity` over `<type>:UUID` refs. See §4.
- **`introspection`** — `GetSystemState`. The aggregate operational snapshot (platform sync, pending reviews, scheduler health — `primitives/system_state.py`). The rival to per-record entity reads.

---

## 3. Layer 2 — the `context` substrate family is a fiction (strong, low-risk)

The matrix already half-confesses this (`primitives-matrix.md:113-121`): the `context` family is three categorically different things wearing one label, each of which has *already migrated elsewhere*:

- "Inference-merged writes" → `InferContext` — really an **LLM-merge** operation (§5), not a context-place thing.
- "Substrate writes" → `WriteFile(scope='context')` — just the **`file`** family with a path.
- "Recurrence lifecycle" → `Schedule` — the **`lifecycle`** family.

The matrix's own words: *"the consolidation rationale of ADR-146 is preserved at the substrate level, not at the primitive-name level."* Translation: `context` is a vestigial *family label* over primitives that all live in `file` or `lifecycle` already. ADR-320 finishes it — once domains are `operation/{domain}/`, "context" is not a *place*, it's a path prefix under the `operation` root.

**Position:** delete the `context` substrate family from the matrix; its members are `file` (`WriteFile`), `lifecycle` (`Schedule`), and — see §5 — a distinct `infer` operation (`InferContext`). This is bigger than ADR-321's "drop the `scope` enum value" but the same gravity, and ADR-321 D5 already proposes dropping `context` from the substrate-family enum. **Fold into ADR-321.**

---

## 4. Layer 3 — is the `entity` layer one abstraction too many? (the real open question)

### 4.1 What the code actually says (not the canon)

The canon (`primitives-matrix.md`) claims **5 types incl. `work`**. The code (`refs.py:71-88`) has **6, and `work` is not one of them**: `agent, version, platform, session, document, task`. (Canon drift receipt #1: there is no `work` entity type; ADR-138 renamed it `task`, ADR-231 gutted it.)

Per-verb, per-type reality (Explore receipts):

| Verb | Surfaces | Live? |
|---|---|---|
| `LookupEntity` | chat + headless + reviewer | LIVE (read) |
| `ListEntities` | chat + headless + reviewer | LIVE (read) |
| `SearchEntities` | chat + headless + reviewer (scopes: document, agent, version) | LIVE (read) |
| `EditEntity` | **chat only** | load-bearing for **agent + platform only**; dead-code for task/document/session; impossible for version (`agent_runs` immutable) (`edit.py:140-236`) |

Per-type reality:

| Type | Table | What it is now |
|---|---|---|
| `agent` | `agents` | LOAD-BEARING — roster identity; EditEntity routes observation/goal/instructions to **workspace files** (`edit.py:140-162`), DB for the rest |
| `platform` | `platform_connections` | LOAD-BEARING — OAuth credential state; EditEntity does status/metadata |
| `session` | `chat_sessions` | read-only — continuity index |
| `version` | `agent_runs` | read-only — immutable audit ledger |
| `document` | `workspace_files` | **read-only, and it's a FILE** — post-ADR-197 documents ARE `workspace_files` rows at `uploads/*.md` (`refs.py:166`) |
| `task` | `tasks` | **VESTIGIAL** — post-ADR-231 the thin scheduling index; `LookupEntity` actively *rejects* slug refs and redirects to `ReadFile` + `Schedule` (`read.py:120-131`) |

### 4.2 The two honest readings

**Reading A — keep the entity layer; it's `/proc`.** A real OS has `ps`/`/proc` alongside `cat`. The entity layer is structured read access to *runtime/relational objects* the filesystem can't naturally express: a live OAuth connection's refresh state, the roster, session continuity, the immutable run ledger. `GetSystemState` is the *aggregate* (`ps aux`); the entity verbs are the *per-record* (`cat /proc/{pid}`). You cannot `cat` an OAuth token's live refresh status as a file. Keep it — but **prune it to its live core** (3 read verbs over `agent/platform/session/version`; `document` is a file; `task` redirects).

**Reading B — collapse toward files.** The entity layer keeps shrinking with every ADR: project entities gone (ADR-138), `memory`/`domain` types gone (ADR-196), `document` is now a file (ADR-197), `task` is now a redirect (ADR-231). `EditEntity` is chat-only and genuinely serves *two* types. What remains that is *not* a file and *not* covered by `GetSystemState`? Honestly: `agent` (roster), `platform` (credentials), `session` (continuity), `version` (run ledger) — four DB-backed object types, three read verbs, one half-dead write verb. The grep/bash question: does that earn a whole substrate family + a `<type>:UUID` ref grammar + four verbs the LLM must hold, or could it be **one introspection-family read** (`GetSystemState` extended to per-record) + file reads for everything the filesystem already holds?

### 4.3 The honest call (mine, for discourse — not a decision)

**Reading A's core is right; Reading B over-fires on the read side but is dead-right on `EditEntity` and on `document`/`task`.** Specifically:

- **`document` should leave the entity layer.** It's a `workspace_files` row at `uploads/*.md`. `LookupEntity(document:uuid)` and `SearchEntities(scope=document)` are doing path-file work through a relational facade. This is the exact `scope='context'` pathology one layer up — a relational handle over what is now a file. **Position: `document` reads move to the `file` family** (`ReadFile`/`SearchFiles` over `uploads/`).
- **`task` should leave the entity layer.** It already half-has — `LookupEntity` redirects slug refs to `ReadFile` + `Schedule` (`read.py:120-131`). Finish it: remove `task` from `ENTITY_TYPES`; recurrence interaction is `Schedule`/`FireInvocation`/`ReadFile` of the YAML. (The thin `tasks` *scheduling index* stays as a DB table; it's just not addressed via the entity-ref grammar.)
- **`EditEntity` shrinks to what it does:** `agent` + `platform` mutations. Everything else is dead code to delete (Singular Implementation). Whether `EditEntity` survives *at all* or its two live jobs fold into `ManageAgent` (agent) + a platform-status path is a sub-question — but a 4-type-dead-code verb is not the shape to keep.
- **`agent`/`platform`/`session`/`version` reads stay** as the `entity` (or renamed `introspection`/`record`) layer — they are genuinely `/proc`, not files. This is Reading A's defensible core.

Net: the entity layer survives as a **narrow relational-read surface over ~4 genuinely-DB-backed object types**, not a 6-type 4-verb CRUD layer. That is a real pruning (it removes `document` + `task` from the grammar, deletes 4 `EditEntity` branches, and corrects the canon's type list), but it is **not** the "delete the entity layer" maximal grep/bash reading — because credentials and live-runtime records are not files.

---

## 5. Layer 4 — the file-operation taxonomy (the operator's reframe, and why it dissolves the confusion)

The operator's sharpest point: *uploading a file and inferring from it are different operations — think embedding.* The evidence says they are **already cleanly separated**, and naming *why* dissolves the `InferContext` confusion.

Five operations touch files. They feel different; the substrate unifies them; the **distinction that matters is read-vs-derive, not five-separate-write-primitives**:

| Operation | Input | Nature | Output | Receipt |
|---|---|---|---|---|
| **Upload / ingest** | binary (PDF/DOCX) | deterministic text-extraction | `uploads/{slug}.md` (operator-authored) | `documents.py:66-206` |
| **Infer / merge** | text + uploaded-doc *contents* + URLs + existing file | **LLM merge** | `persona/IDENTITY.md` / `operation/BRAND.md` (operator-authored) | `infer_context.py`, `context_inference.py` |
| **Embed** | a file's content | deterministic vectorize | `workspace_files.embedding` (metadata, no revision) | `documents.py:212-223`, `workspace.py:30-51` |
| **Author / write** | path + content | attributed revision | any path | `write_revision` (§1 FACT A) |
| **Render** | spec | gateway compute | asset + `workspace_files` metadata | `runtime_dispatch.py:167-186` |

**The clarifying claim:** these are NOT five write-primitives. **Author/write is the one substrate operation** (`write_revision`). Upload, infer, and render are **producers that compute content and then author it.** Embed is a **derived index over authored content**, not a write at all. So:

- **Upload** = (extract) → author. The extract is the only special step; the write is `write_revision`.
- **InferContext** = (LLM-merge over read inputs) → author. The merge is the only special step; the write is `write_revision`. **InferContext is fundamentally an *LLM-merge-over-substrate* operation, not a file-family operation** — which is exactly why its presence in the `context` family was a category error (§3). It belongs to a `derive`/`infer` shape: *read substrate, run an LLM, author the result.*
- **Render** = (gateway compute) → author. Same shape.
- **Embed** = derive an index from authored content. Different axis entirely (read-side acceleration), correctly bypassing the revision chain.

**This is the axiomatic insight the operator was reaching for:** the file-system-native architecture means there is **one write** (authored substrate) and **one read** (path + optional semantic rank), and everything else — upload-extract, infer-merge, render-compute, embed-index — is a **producer or an index over that one substrate**, not a parallel file API. The `InferContext` confusion is a symptom of describing a *producer* (LLM-merge) as a *place* (`context` family). Name it as a producer and the confusion evaporates — and the door opens to the operator's "future consideration": a general **derive-from-substrate** shape (read files → LLM/compute → author result) of which `InferContext` is the first instance, and of which "infer a brief from these uploaded docs," "synthesize a domain landscape," etc. are future instances. Today that shape is hardcoded to identity/brand; the architecture wants it generalized — but that is a *forward* ADR, explicitly not this pruning.

### 5.1 The "do we even need infer, or are all files just pure files?" fork

The operator named both horns. The evidence adjudicates:

- **All-files-pure** (no `InferContext`, just `WriteFile` + let the chat LLM merge inline): tempting, and for *some* cases the chat surface already does this. But `InferContext` carries **deterministic gap-detection** (`context_inference.py`, zero-LLM post-pass) + **cost-ledger attribution** (`caller='inference'`) + a **focused merge system-prompt** (IDENTITY_SYSTEM/BRAND_SYSTEM) that a generic WriteFile wouldn't. Collapsing it to WriteFile would lose the gap-report and the focused merge. So *not* "all files are pure" — there is a real derive operation.
- **Keep infer, but generalize its frame**: the synthesis at the time of writing. `InferContext` stays as the **first instance of a derive-from-substrate producer**, and the architecture's forward direction is to generalize the *frame* (any read-set → LLM-merge → authored result) rather than to multiply per-target infer primitives. The upload→infer distinction stays sharp precisely because upload is *deterministic extraction* and infer is *LLM derivation* — two genuinely different producers, both ending in `write_revision`.

> **Resolution (2026-06-07, after operator reconsideration — supersedes the "generalize the frame" synthesis above):** the operator pushed harder — *"this primitive warrants a reconsideration… up for removal even… maybe it shifts toward embed + yarnnn-ify a file ready for AI."* That decomposed the tangle one level deeper than this section had. The resolved decisions:
> - **`InferContext` DISSOLVES, not generalizes** (ADR-324). It has only 2 callers (chat feed + MCP `remember_this`), both identity/brand. It is an *application-level workflow*, not a primitive. Its merge relocates to a dispatch-invoked helper (`author_identity_merge`); its gap-detection becomes a standalone helper. There is no general `Derive` primitive to build — if a third merge target ever appears it's another helper, not a generalized verb. The "deferred derive-producer horizon" this doc named is *closed*, not deferred.
> - **Embed / make-AI-ready is the fundamental operation underneath** (ADR-325) — and it was buried (fire-and-forget on `scope='context'` writes only, inconsistent across the three doors). It is PROMOTED to a first-class `Embed` primitive that flows through the existing ADR-307 permission gate: consequential, autonomy-governed (manual/bounded → queue, autonomous → apply), cost-ceilinged, content-kind-selective (NOT a 100%-embed principle — the operator's explicit nuance vs Claude-Code-selective). The autonomy mode IS the embed policy; no bespoke mechanism.
> The pair (ADR-324 removes the false primitive; ADR-325 adds the true one) realizes this §5 taxonomy in code: one authored write, producers that author into it, and embed as a derived index that is now *explicit and governed* rather than an automatic side-effect.

---

## 6. Synthesis — what the architecture-and-service-model vision actually wants

Stack the four layers against FACT A (one authored write) + FACT B (five-root filesystem):

1. **One write.** `write_revision` is the substrate operation. Producers (upload-extract, infer-merge, render-compute) compute content and author it; they are not parallel file APIs. **Canon should say this** — it's latent in ADR-209 but not stated as the organizing principle of the primitive surface.
2. **One read, two ranks.** Path-based (`ReadFile`/`ListFiles`/`SearchFiles` BM25) + semantic (`QueryKnowledge` vector). The `file` family is the grep/bash surface; it's healthy. ADR-321 makes it path-native (drops `scope='context'`).
3. **`context` family deletes.** Its members are `file` (WriteFile), `lifecycle` (Schedule), and `infer` (InferContext-as-producer). (§3 — fold into ADR-321.)
4. **`entity` family prunes to a narrow relational-read surface** over genuinely-non-file DB objects (`agent/platform/session/version`); `document` → `file`, `task` → `Schedule`/`ReadFile`, `EditEntity` → its 2 live jobs (or fold into `ManageAgent` + platform path). (§4.)
5. **`InferContext` reframes as the first derive-from-substrate producer** — the operator's forward horizon (generalize the frame), explicitly a future ADR, not this pruning. (§5.)

**The grep/bash answer, precisely:** YES the surface should re-ground to filesystem-native fundamentals — but the destination is *not* "only files + bash." It is **one authored write, one two-rank read, a narrow `/proc`-style relational-read for credentials/roster/sessions/run-ledger, and producers (upload/infer/render) that author into the one substrate.** The over-firing maximal reading ("collapse the entity layer entirely") fails on the irreducible fact that **an OAuth token's live refresh state and the roster are not files** — they are relational/runtime records, and a filesystem-native OS still has `/proc`.

---

## 7. Recommended downstream shape (for the operator to choose)

Three landing zones, increasing canon-radius:

- **A. ADR-321 absorbs Layers 1–3** (path-native file primitives + delete `scope='context'` value + delete the `context` substrate *family*). Already mostly in the draft; sharpen D5 to "delete the family," add the canon-drift fixes (the matrix's wrong type list, the `/workspace/context/` stragglers in the matrix prose). **This is the cheap, forced-by-ADR-320 slice.**

- **B. A new ADR for Layer 4 (entity-layer pruning):** remove `document` + `task` from `ENTITY_TYPES`, route their reads to `file`/`Schedule`, shrink `EditEntity` to agent+platform (or fold into `ManageAgent` + platform path), correct the canon's type list, rename the family if `entity` no longer fits (`record`/`introspection`). Medium radius, real Singular-Implementation deletions. **Separable from A; depends on A landing first so the file-side is clean.**

- **C. A FOUNDATIONS / SERVICE-MODEL revisit** stating the organizing principle the surface should *derive* from: **one authored write (producers author; they are not parallel file APIs); one two-rank read; a narrow relational-read surface; the file-system is the substrate and the permission topology.** This is the axiomatic layer the operator asked for — it makes future primitive additions *derivable* rather than accreted. It also names the **derive-from-substrate producer** shape (§5) as the forward horizon for generalizing `InferContext`. Highest radius; should be *downstream* of A+B proving the principle in code, not upstream of it (ADR-320's own doc-first-but-code-validated discipline).

**My recommendation:** A now (fold into the already-pushed ADR-321 draft, after its ratification). B as its own ADR once A lands. C as the capstone once A+B have validated the "one write / one read / narrow /proc" principle in code — write the axiom *after* the code proves it, not as speculation. The `InferContext`-generalization (derive-from-substrate producer) is a **separate forward ADR**, explicitly deferred — it is a new capability, not a cleanup, and bundling it would repeat the anti-pattern ADR-320's discipline warns against.

---

## 8. Open questions (named so they're known-intentional)

1. **Does `EditEntity` survive at all, or do its 2 live jobs fold into `ManageAgent` (agent) + a platform-status path?** Leaning fold (Singular Implementation — a 2-job verb with a `<type>:UUID` grammar over a dead-4-type set is hard to justify), but `ManageAgent` lacks the `append_observation`/`set_goal` shape today. Sub-question for Layer-4 ADR.
2. **Does the `entity`/`introspection` boundary want a rename?** Post-pruning, `entity` reads + `GetSystemState` are the same *purpose* (relational/runtime introspection) at different granularities (per-record vs aggregate). Might be one family. Naming sub-question.
3. **The derive-from-substrate producer generalization** (forward horizon for `InferContext`) — its own ADR, deferred. What's the right frame: a general `Derive(read_set, merge_prompt, target)` primitive, or per-purpose producers that share a helper? Not decided here.
4. **`version`/`session`/`platform` read justification** — these are genuinely `/proc` (run ledger, continuity, credentials). Confirmed non-file. But are they ever *read by the LLM* in practice, or only by routes/UI? If the latter, they may not need an LLM-facing entity verb at all. Caller-trace sub-question for the Layer-4 ADR.

---

## Appendix — receipt index

- Authored-substrate writer inventory: `authored_substrate.py:264`; `workspace.py:527-707`; `infer_context.py:170-176`; `documents.py:197-206`; `runtime_dispatch.py:167-186`; `outcomes/ledger.py:300-313,823-836`; `programs.py:586-591`; `kernel_mirrors.py:44-45`; `routes/documents.py:291-333`.
- Entity types (code): `refs.py:71-88` (6 types; no `work`). EditEntity branches: `edit.py:140-236`. Task-ref redirect: `read.py:120-131`.
- Upload path: `documents.py:66-206` (ADR-197 landed — `uploads/{slug}.md` in `workspace_files`; `filesystem_documents`/`_chunks` dropped, migration 166).
- InferContext: `infer_context.py`, `context_inference.py` (targets `persona/IDENTITY.md` + `operation/BRAND.md` — ADR-320-correct).
- Embeddings: column `migrations/100_workspace_files.sql:31`; RPC `migrations/145_semantic_search_workspace.sql`; compute `services/embeddings.py`; read (semantic-primary, BM25-fallback) `workspace.py:783-881`.
- GetSystemState shape: `primitives/system_state.py` (aggregate: platform sync, pending reviews, scheduler health).
- Canon drift: `primitives-matrix.md:56` (`context` substrate family), `:99` (`/workspace/context/{domain}/` old root), `:113-121` (`context` family confession), type list claims `work` (code has `task`).
