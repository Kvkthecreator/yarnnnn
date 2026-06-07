# ADR-322 — Entity-Layer Pruning: a Narrow `/proc` over the Filesystem-Native Substrate

> **Status**: DRAFT (2026-06-07). Proposed by Claude, pending KVK ratification. Part of the post-ADR-320 surface re-grounding arc (ADR-321 file primitives → **ADR-322 entity layer** → ADR-323 frame collapse → ADR-324 InferContext dissolution → ADR-325 Embed primitive). **Gated on ADR-321 landing** — the entity-layer pruning routes `document` reads into the `file` family, so the file side must be path-native first.
> **Date**: 2026-06-07
> **Authors**: KVK, Claude
> **Upstream**: [primitive-surface-grounding discourse](../analysis/primitive-surface-grounding-2026-06-07.md) §4 (the entity-layer evidence map) + the two Explore caller-traces it cites.
> **Dimensional classification**: **Substrate** (Axiom 1 — which substrate the entity verbs address) + **Mechanism** (Axiom 5 — primitive vocabulary).
> **Canon backing**: FOUNDATIONS Axiom 1 ("Axiom 0 note" in primitives-matrix — the entity layer is "narrow by design… operates only on scheduling-index / credential / ephemeral-queue DB rows; semantic content lives in files") + ADR-222 OS framing (the entity layer is the agent OS's `/proc`, not its filesystem).

---

## The one-sentence thesis

**The entity layer has been shrinking with every architectural collapse (project/task/user_memory) until it now over-claims: it carries a `<type>:UUID` ref grammar + four CRUD verbs over six types, but `document` is a file, `task` is a redirect, and `EditEntity` is load-bearing for only two of six types.** Prune it to what it actually is post-ADR-320: a narrow `/proc`-style *relational-read* surface over the ~4 genuinely-non-file DB objects (`agent`, `platform`, `session`, `version`), with `document` and `task` reads moving to the file family + `Schedule`, and `EditEntity` shrinking to its two live jobs.

---

## Context — the entity layer is archaeological

The `entity` substrate family (`LookupEntity`, `ListEntities`, `SearchEntities`, `EditEntity` over `<type>:UUID` refs resolved in `refs.py`) was sized for a world that no longer exists. Each architectural collapse drained it:

- **ADR-138** deleted the project layer → project entity refs gone.
- **ADR-196** dropped `user_memory` → `memory` + `domain` entity types deleted (`refs.py:73-87`).
- **ADR-197** moved documents into `workspace_files` at `uploads/*.md` → `document` resolves to a **file** now (`refs.py:166`).
- **ADR-231** thinned `tasks` to a scheduling index, recurrences became YAML files → `task` is a redirect (`LookupEntity` actively rejects task slugs and steers to `ReadFile` + `Schedule`, `read.py:120-131`).

What's left (live `ENTITY_TYPES`, `refs.py:71-88`): `agent, version, platform, session, document, task`. The discourse §4 caller-trace, with receipts:

| Type | Table | Reality |
|---|---|---|
| `agent` | `agents` | LOAD-BEARING — roster identity; `EditEntity` routes observation/goal/instructions to **workspace files** (`edit.py:140-162`), DB for the rest |
| `platform` | `platform_connections` | LOAD-BEARING — OAuth credential state; `EditEntity` does status/metadata |
| `session` | `chat_sessions` | read-only — continuity index |
| `version` | `agent_runs` | read-only — **immutable** audit ledger (EditEntity impossible) |
| `document` | `workspace_files` | **read-only, and it's a FILE** (ADR-197) — `uploads/*.md` rows |
| `task` | `tasks` | **VESTIGIAL** — thin scheduling index; `LookupEntity` redirects slug refs to `ReadFile`+`Schedule` (`read.py:120-131`) |

And per-verb (discourse §4): `Lookup`/`List`/`Search` are LIVE (chat+headless+reviewer reads). `EditEntity` is **chat-only**, load-bearing for `agent`+`platform`, dead-code for `task`/`document`/`session`, impossible for `version` (`edit.py:140-236`).

**The over-claim:** a six-type four-verb CRUD layer where two types are files, one is a redirect, and the write verb serves two types. That is not a coherent abstraction; it is residue.

---

## Why not just delete the entity layer (the maximal grep/bash reading)

The discourse §4.2 stress-tested "collapse the entity layer entirely into files + `GetSystemState`." It fails on one irreducible fact: **an OAuth token's live refresh state, the agent roster, session continuity, and the immutable run ledger are not files.** They are relational/runtime records. A filesystem-native OS still has `/proc` and `ps` alongside `cat`. `GetSystemState` is the *aggregate* snapshot (`ps aux` — platform sync, pending reviews, scheduler health; `system_state.py`); per-record relational read is a genuine different need (`cat /proc/{pid}`). You cannot express "this connection's token refreshed at T, expires at T+N" as a file read.

So the entity layer survives — but **pruned to its `/proc` core**, not kept as CRUD-over-everything.

---

## Decision (proposed)

### D1 — `document` leaves the entity layer; its reads move to the `file` family.
Post-ADR-197 a document IS a `workspace_files` row at `uploads/{slug}.md`. `LookupEntity(document:uuid)` and `SearchEntities(scope=document)` are doing path-file work through a relational facade — the same pathology ADR-321 fixes one layer up (a relational handle over what is a file). Document reads become `ReadFile`/`SearchFiles`/`ListFiles` over `uploads/`. Remove `document` from `ENTITY_TYPES`. (The upload *route* and binary-storage path are unchanged — this is only about how the *LLM addresses* an uploaded doc: by path, not by `document:uuid`.)

### D2 — `task` leaves the entity layer; recurrence interaction is `Schedule`/`FireInvocation`/`ReadFile`.
It already half-has — `LookupEntity` redirects slug refs (`read.py:120-131`). Finish it: remove `task` from `ENTITY_TYPES`. The thin `tasks` *scheduling-index table* stays (it's the cron index); it is simply no longer addressed via the entity-ref grammar. Recurrence reads are `ReadFile` of the YAML at the natural-home path; recurrence lifecycle is `Schedule`; manual fire is `FireInvocation`.

### D3 — `EditEntity` shrinks to its two live jobs, or folds entirely.
`EditEntity` serves `agent` (observation/goal/instructions → workspace files; some DB fields) + `platform` (status/metadata). The `task`/`document`/`session` branches are dead code (delete per Singular Implementation); `version` is immutable. **Open sub-decision (D3-fork):**
- **D3-a (shrink):** keep `EditEntity` but restrict its type set to `{agent, platform}`, delete the dead branches.
- **D3-b (fold):** delete `EditEntity` entirely — route agent mutations into `ManageAgent` (which lacks the `append_observation`/`set_goal` shape today, so this needs a `ManageAgent` action extension) and platform mutations into a dedicated platform-status path. Stronger Singular Implementation (no `<type>:UUID`-grammar write verb over a 2-type set), but more migration.

**Leaning D3-b** (a 2-type write verb carrying a 6-type ref grammar is hard to justify), but it requires extending `ManageAgent`. Decide at ADR-ratification with a `ManageAgent`-shape check.

### D4 — The surviving entity layer is `{agent, platform, session, version}` read-only.
Three read verbs (`LookupEntity`, `ListEntities`, `SearchEntities`) over four genuinely-DB-backed object types. This is the `/proc` core. `EditEntity` either shrinks to `{agent, platform}` (D3-a) or dissolves (D3-b).

### D5 — Rename the family (open) — `entity` → `record` or merge into `introspection`.
Post-pruning, the entity reads + `GetSystemState` share a *purpose* (relational/runtime introspection) at two granularities (per-record vs aggregate). Two options:
- **D5-a:** rename the substrate family `entity` → `record` (clearer: "a DB record handle," not "an entity" which implied semantic content the file layer now owns).
- **D5-b:** merge entity-reads + `GetSystemState` under one `introspection` family (they're the same purpose). The four verbs stay distinct primitives; the *family label* unifies.

**Leaning D5-b** for conceptual economy (one introspection surface, two granularities), but D5-a is lower-churn. Decide at ratification.

### D6 — Correct the canon.
`primitives-matrix.md` Axiom-0 note + family list updated to the pruned set. (The stale `work` type claim was already fixed with ADR-321's canon-drift pass; this completes the type-list correction.) The `entity` substrate-family entry rewrites to describe the `/proc` core. GLOSSARY entity-ref vocabulary updated.

---

## What this is NOT

- **NOT a deletion of the entity layer.** D4 keeps the `/proc` core — credentials, roster, sessions, run-ledger are not files.
- **NOT a schema change.** No tables drop. `tasks` stays (scheduling index); `workspace_files` already holds documents. This changes *how the LLM addresses* these, not where data lives.
- **NOT an upload-path change.** The document upload route + binary storage are untouched (ADR-322 only changes that the LLM reads an uploaded doc by `ReadFile(uploads/...)` not `LookupEntity(document:uuid)`).
- **NOT bundled with the file-primitive change.** Gated on ADR-321; lands after.

---

## Claim tiering

- **FORCED (by prior ADRs — already true in code):** `document` is a file (ADR-197); `task` is a redirect (ADR-231); `memory`/`domain` are gone (ADR-196). D1/D2 are *finishing migrations the code already started*, not new direction.
- **DESIGN CHOICE (selected):** D3-fork (shrink vs fold `EditEntity`); D5 family rename. Defensible either way; decided at ratification.
- **PRESERVED (non-negotiable):** the `/proc` core (D4) — Axiom 1's "entity layer is narrow by design over DB rows" is *kept*, just pruned to its true extent. The maximal "delete the entity layer" reading is explicitly rejected (§"Why not just delete").

---

## Scope / blast radius

Medium. Single PR after ADR-321 lands:
1. `refs.py`: remove `document` + `task` from `ENTITY_TYPES` + `TABLE_MAP`; the document `_enrich_document_with_content` path retires (reads go through file primitives).
2. `read.py`/`search.py`/`list.py`: drop `document`/`task` scopes; the `task`-redirect guard (`read.py:120-131`) becomes unnecessary (no `task` type to redirect).
3. `edit.py`: D3-a (delete dead branches, restrict to `{agent, platform}`) or D3-b (delete file + extend `ManageAgent`).
4. Tool descriptions: `SearchEntities` scope enum drops `document`; `LookupEntity`/`ListEntities` examples re-pointed.
5. Canon: `primitives-matrix.md` (`entity`/`record`/`introspection` family rewrite), GLOSSARY, CLAUDE.md ADR-summary.
6. Regression gate `api/test_adr322_entity_pruning.py`: (a) `ENTITY_TYPES == {agent, platform, session, version}`; (b) `LookupEntity(document:...)` returns a redirect-to-ReadFile (or is rejected); (c) `EditEntity` type set is `{agent, platform}` or the verb is gone; (d) document reads resolve via `ReadFile(uploads/...)`; (e) no live caller references a `document:`/`task:` entity ref.

**Caller-trace prerequisite (do at ratification):** the discourse §8 open question #4 — confirm `version`/`session`/`platform` are ever *LLM-read* in practice vs only route/UI-read. If a type is never LLM-addressed, it may not need an LLM-facing entity verb at all (it'd be a route-only concern), shrinking the `/proc` core further. Trace before finalizing D4.

---

## Relationship to other ADRs

- **Part of** the post-ADR-320 arc: ADR-321 (file primitives) → **ADR-322 (this)** → ADR-323 (frame collapse) → ADR-324 (InferContext dissolution) → ADR-325 (Embed primitive).
- **Gated on** ADR-321 (document reads route into the now-path-native `file` family).
- **Finishes migrations** ADR-197 (document-as-file → document reads as file reads) + ADR-231 (task-as-redirect → task off the entity grammar).
- **Amends** primitives-matrix.md Axiom-0 note (the entity layer's true extent) + ADR-168 (the `Read→LookupEntity` naming reform — this prunes the type set that reform operated over).
- **Preserves** Axiom 1 (entity layer narrow-by-design over DB rows — *kept*, pruned to truth), `GetSystemState` (the aggregate introspection it pairs with), the `tasks` scheduling index + `workspace_files` (no schema change).

---

## Open questions (deferred to ratification)

1. **D3-fork** — shrink `EditEntity` to `{agent, platform}` (D3-a) or fold it into `ManageAgent` + a platform path (D3-b)? Needs a `ManageAgent`-shape check (does it want `append_observation`/`set_goal` actions?).
2. **D5** — rename `entity`→`record` (D5-a) or merge entity-reads + `GetSystemState` into one `introspection` family (D5-b)?
3. **§Scope caller-trace** — are `version`/`session`/`platform` ever LLM-read, or only route/UI-read? If route-only, the `/proc` LLM-surface shrinks further.
