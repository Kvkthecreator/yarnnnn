# ADR-324 — InferContext Dissolution: an Application Masquerading as a Primitive

> **Status**: ACCEPTED (2026-06-07). Ratified by KVK ("dissolve, recommended"). Implementation in progress (this commit chain; independent of 321/322, pairs with 325). **Reshaped** from the earlier "derive-from-substrate producer (deferred stub)" framing — the operator's reconsideration ("this primitive warrants a reconsideration… up for removal even") resolved the deferred horizon into a concrete dissolution. **Part of the post-ADR-320 surface re-grounding arc** (ADR-321 file primitives → ADR-322 entity pruning → ADR-323 frame collapse → **ADR-324 InferContext dissolution** + ADR-325 Embed primitive).
> **Date**: 2026-06-07
> **Authors**: KVK, Claude
> **Upstream**: [primitive-surface-grounding discourse](../analysis/primitive-surface-grounding-2026-06-07.md) §5 (file-operation taxonomy: one authored write; producers author into it) + the operator's reconsideration (InferContext is an application-level workflow, not a primitive; the fundamental operations underneath are ingest + embed).
> **Dimensional classification**: **Mechanism** (Axiom 5 — removing a pseudo-primitive from the vocabulary).
> **Canon backing**: FOUNDATIONS Axiom 1 + ADR-209 (one authored write; `InferContext` was a merge-then-author wrapper, not a distinct substrate operation) + the Singular-Implementation discipline (CLAUDE.md §2 — delete the thing whose existence is the confusion, don't rename it).

---

## The one-sentence thesis

**`InferContext` is not a primitive — it is an application-level workflow ("LLM-merge operator input into the two authored-identity files, with gap-detection") that has exactly two callers (chat feed + MCP `remember_this`), both identity/brand.** Renaming it relabels the confusion; *dissolving* it removes the thing whose existence was the confusion. Its three pieces relocate to where they belong, and the actually-fundamental operation hiding underneath — embed / make-AI-ready — gets promoted to a first-class gated primitive in the sibling ADR-325.

---

## Context — what `InferContext` actually is

`INFER_CONTEXT_TOOL` (`infer_context.py:25-83`) is described as "Run inference-merged write to IDENTITY.md or BRAND.md." Its `target` enum is hardcoded to exactly `{identity, brand}` (`infer_context.py:57`). Its handler (`handle_infer_context`) does three things:
1. **Merge** — `infer_shared_context()` (`context_inference.py:89`): one `chat_completion` (Sonnet) over a read-set (operator text + uploaded-doc contents + URL contents + existing file) → merged markdown. Two hardcoded system prompts (IDENTITY_SYSTEM / BRAND_SYSTEM).
2. **Gap-detect** — `detect_inference_gaps()`: deterministic, zero-LLM post-pass; returns a `gaps` report the caller may act on with a `Clarify`.
3. **Author** — `UserMemory.write()` → `write_revision()` → `persona/IDENTITY.md` or `operation/BRAND.md`, `authored_by="operator"`.

**Receipts on the caller surface (the case for dissolution):**
- Live callers: chat feed (`feed.py:356`) + MCP `remember_this` composition (`mcp_composition.py:681-703`). **That is the entire consumer set.** Both route only identity/brand.
- `InferWorkspace` (the first-act scaffold sibling) was already removed by ADR-314 D4 — InferContext is the lone survivor of the infer family, narrowed to two targets.
- The naming is doubly misleading: "Context" implies the `context/` root it does NOT touch (it writes `persona/` + `operation/`); "Infer" implies generality the two-value enum doesn't have.

Per FOUNDATIONS Axiom 1 + ADR-209, the *author* step is the one substrate operation (`write_revision`). The *merge* is an LLM call; the *gap-detect* is a deterministic helper. Neither is a distinct substrate primitive — they are an application composed over the chat LLM's existing tool surface (`ReadFile` to get the existing file + the operator's input + `WriteFile` to author). A primitive should be an irreducible substrate/runtime verb; `InferContext` is a *workflow* (read → LLM-merge → author → gap-check) that the chat surface can run with primitives it already has.

---

## Decision — dissolve, relocate the three pieces

### D1 — Delete `InferContext` from the primitive registry.
Remove `INFER_CONTEXT_TOOL` from `CHAT_PRIMITIVES`, `handle_infer_context` from `HANDLERS`, the `InferContext` entry from `primitives-matrix.md`. The `context` substrate family (already deleted by ADR-321 D5) loses its last named member.

### D2 — The merge relocates to a server-side helper the chat dispatch calls inline.
The identity/brand merge is still a focused LLM call with focused system-prompts — that *quality* is worth preserving (the discourse §5.1 rejected "drop it entirely, let raw WriteFile do it"). But it does not need to be an LLM-*facing tool*. The chat surface (YARNNN), when handling operator identity/brand input, calls a server-side helper `author_identity_merge(target, text, doc_ids, url_contents)` (the renamed/relocated `infer_shared_context`) and then `WriteFile`s the result. The merge becomes **infrastructure the chat dispatch invokes**, not a tool the model selects. Same `chat_completion`, same IDENTITY_SYSTEM/BRAND_SYSTEM prompts, same cost-ledger (`caller='inference'`) — relocated from a primitive handler to a dispatch helper. (`context_inference.py` largely survives as that helper module; only its primitive wrapper dies.)

### D3 — Gap-detection becomes a standalone helper, callable post-write.
`detect_inference_gaps()` survives as a pure helper. After the chat dispatch authors identity/brand, it runs the gap-check and surfaces the result the same way (at most one targeted `Clarify` on high-severity). No behavior change for the operator; the gap-report just isn't bolted to a dissolved primitive.

### D4 — MCP `remember_this` routes identity/brand through the same dispatch helper.
`mcp_composition.classify_memory_target` currently routes `target='identity'|'brand'` to `InferContext` (`mcp_composition.py:681-703`). Post-dissolution it routes to the same `author_identity_merge` helper (D2) + `WriteFile`. The MCP intent-tool surface (`remember_this`) is unchanged; only its internal routing target changes from a dissolved primitive to the helper. The other `remember_this` branches (memory/agent/task → `WriteFile`) are untouched.

### D5 — The inference eval harness re-points at the helper.
`api/eval/run_inference_eval.py` already calls `infer_shared_context()` directly (`run_inference_eval.py:191`), not the primitive — so it re-points at the renamed helper (`author_identity_merge`) with zero structural change. The eval discipline (entity recall, anti-fabrication, etc.) is preserved; it was always testing the *merge function*, not the primitive wrapper.

### D6 — Honest naming for the surviving helper.
The relocated merge helper is named for what it does: `author_identity_merge` (or `merge_authored_identity`) — not "infer," not "context." It authors the operator's identity/brand by merging input with existing content. The `caller='inference'` token-ledger tag may stay (it's a cost-attribution string, a GLOSSARY-exception slug like others) or migrate to `caller='identity-merge'` — a minor sub-decision at implementation.

---

## What this is NOT

- **NOT a loss of the merge quality.** The focused IDENTITY/BRAND system-prompts + gap-detection survive as helpers (D2/D3). The operator experience (paste a doc/URL/text → identity/brand file updates, gaps surfaced) is identical.
- **NOT "all files are pure, no merge."** The discourse §5.1 rejected that — there IS a real derive operation; it just isn't a *primitive*, it's a dispatch-invoked helper.
- **NOT a schema change.** No tables. The files it wrote (`persona/IDENTITY.md`, `operation/BRAND.md`) are unchanged; only *how the write is triggered* changes (dispatch helper, not LLM tool call).
- **NOT the embed change.** The fundamental operation the operator's reconsideration surfaced (embed / make-AI-ready) is ADR-325 — a sibling, not this ADR. ADR-324 removes the pseudo-primitive; ADR-325 promotes the real one.

---

## Claim tiering

- **FORCED (by the caller evidence + Axiom 1):** `InferContext` has 2 callers, both identity/brand; the author step is the one substrate op; the merge is an LLM call not a substrate verb. That it is an *application*, not a primitive, is a finding, not a preference.
- **DESIGN CHOICE (selected):** dissolve vs demote-and-rename. The operator chose dissolve (Singular Implementation — delete the confusion rather than relabel it). Defensible either way; dissolve is the cleaner end state.
- **PRESERVED:** the merge quality (focused prompts), gap-detection, cost-ledger, the eval harness, the MCP `remember_this` intent surface, the authored files.

---

## Scope / blast radius

Medium — a real primitive removal (158 `InferContext` references across the tree per the rename-protocol grep; most are docs/ADR historical mentions that get a "dissolved per ADR-324" note, not edits). Single PR (independent of ADR-321/322/323; can land in parallel — it touches the inference path, not the file-primitive scope enum or the entity layer or the reviewer frame):

1. `infer_context.py`: DELETE the primitive (`INFER_CONTEXT_TOOL` + `handle_infer_context`). Keep `context_inference.py` as the merge-helper module (rename its public fn to `author_identity_merge`).
2. `registry.py`: remove `InferContext` from `CHAT_PRIMITIVES` + `HANDLERS` + `permission.py` (it's consequential today; removing it removes a gate entry).
3. `routes/feed.py`: the chat dispatch path that routed identity/brand input to `InferContext` now calls the helper + `WriteFile` + gap-check inline.
4. `mcp_composition.py` + `mcp_server/server.py`: `remember_this` identity/brand routing → helper (D4).
5. `eval/run_inference_eval.py`: re-point to `author_identity_merge` (D5).
6. Tool-surface counts: `CHAT_PRIMITIVES` drops 1 (the matrix's MCP-mode "4 primitives" note re-counts).
7. Canon: `primitives-matrix.md` (`context` family already gone; remove the `InferContext` row + the `identity`/`brand` target table), GLOSSARY, CLAUDE.md ADR-summary, the MCP feature docs (`docs/features/mcp/*` — `remember_this` internal routing note).
8. Regression gate `api/test_adr324_infercontext_dissolution.py`: (a) `InferContext` not in `CHAT_PRIMITIVES`/`HANDLERS`; (b) `author_identity_merge` helper exists + produces the same shape; (c) chat identity/brand authoring still works end-to-end (merge + write + gap); (d) MCP `remember_this(target='identity')` still authors `persona/IDENTITY.md`; (e) the inference eval harness passes against the helper.

**Prompt-change protocol:** removing a tool description is a prompt change — `api/prompts/CHANGELOG.md` entry. The chat prompt guidance that told YARNNN "use InferContext for identity/brand" changes to "merge identity/brand inline" (or the dispatch handles it without prompt mention — preferred, since it's now infrastructure).

---

## Relationship to other ADRs

- **Reshapes** the earlier ADR-324 deferred-stub (the "derive-from-substrate producer" horizon dissolves into this concrete decision — there is no separate general `Derive` verb to build; identity/brand merge is a helper, and if a third merge target ever appears it's another helper, not a generalized primitive).
- **Completes** ADR-321 D5 (the `context` substrate family loses its last member — `InferContext` was the one piece that wasn't already `file` or `lifecycle`).
- **Amends** ADR-235 D1.a (which *created* `InferContext` by splitting `UpdateContext`; this finishes the arc — the split was right to separate the cognitive shapes, but the identity/brand merge belongs as a helper, not a standing primitive) + ADR-314 D4 (which removed `InferWorkspace`; this removes the last infer primitive).
- **Sibling of** ADR-325 (Embed primitive — the real fundamental operation the reconsideration surfaced; ADR-324 removes the false primitive, ADR-325 adds the true one).
- **Preserves** ADR-162 (gap-detection — survives as helper), ADR-171 (cost-ledger), ADR-169 (MCP intent tools — `remember_this` surface unchanged), ADR-209 (the author step), the inference eval discipline.
