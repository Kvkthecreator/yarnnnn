# ADR-325 — Embed as a Gated Primitive: Make-AI-Ready as an Explicit, Autonomy-Governed Step

> **Status**: ACCEPTED (2026-06-07). Ratified by KVK (promote embed to first-class, but **scope it carefully** — not a 100%-embed principle; an explicit step governed by autonomy like every other tool). Implementation in progress (this commit chain; pairs with 324). **Sibling of ADR-324** (which removes the false primitive `InferContext`; this adds the true fundamental operation the reconsideration surfaced). Part of the post-ADR-320 surface re-grounding arc.
> **Date**: 2026-06-07
> **Authors**: KVK, Claude
> **Upstream**: [primitive-surface-grounding discourse](../analysis/primitive-surface-grounding-2026-06-07.md) §1 FACT A + §5 (embed is a derived index over authored content; today it's a buried fire-and-forget) + the operator's framing ("embed/yarnnn-ify should be an explicit additional step, agent/operator chooses, handled by autonomy mode — potentially a primitive that's gated or evolved as a tool").
> **Dimensional classification**: **Mechanism** (Axiom 5 — a new consequential primitive in the vocabulary) + **Substrate** (Axiom 1 — it produces the semantic index over `workspace_files`) + **Purpose** (Axiom 3 — the autonomy mode IS the embed policy).
> **Canon backing**: ADR-307 (the unified permission gate — `read_only` vs `consequential`, `GATE_QUEUEABLE_PRIMITIVES`, autonomy resolves APPLY/QUEUE/DENY) + FOUNDATIONS Derived Principle 23 (one gate, one queue) + Derived Principle 12 (Channel legibility gates autonomy).

---

## The one-sentence thesis

**"Make a file AI-ready" (embed → semantic-searchable) is currently a buried fire-and-forget side-effect that fires only on `WriteFile(scope='context')` — applied inconsistently across the three doors files enter through. Promote it to an explicit, first-class `Embed` primitive that flows through the existing ADR-307 permission gate — consequential, autonomy-governed (manual/bounded → queue, autonomous → apply), cost-ceilinged — so embedding is a *chosen* step governed by the same machinery as every other consequential action, not an automatic 100%-of-writes tax.**

---

## Context — embed is half-wired and inconsistent

Three doors files enter the workspace (discourse §5). Embedding is applied to *one* of them:

| Door | Embeds today? | Receipt |
|---|---|---|
| **Author** (`WriteFile scope='context'`) | ✅ fire-and-forget | `workspace.py:672` → `_embed_workspace_file` |
| **Author** (`WriteFile scope='workspace'`/`agent`) | ❌ no | (only the `context` branch calls `_embed_workspace_file`) |
| **Ingest** (document upload) | ✅ separately, in the route | `documents.py:212-223` (embeds an excerpt) |
| **Derive** (identity/brand merge) | ❌ no | (`handle_infer_context` doesn't embed) |

So "make AI-ready" is:
- **Inconsistent** — context writes embed, other writes don't, uploads embed differently (excerpt only), derives don't embed at all.
- **Automatic** — where it fires, it fires unconditionally as a side-effect, with no operator/agent choice and no autonomy governance.
- **Cost-invisible** — each embed is an OpenAI `text-embedding-3-small` call (`embeddings.py:24`); today they accrue silently with no ceiling, unlike RuntimeDispatch (token budget) or Schedule (pace cap) which carry explicit resource ceilings.

The operator's insight, precisely: incumbent LLMs (Claude Code, ChatGPT) don't embed 100% of files — embedding is **selective / on-demand**. YARNNN is filesystem-native, but that does NOT imply "embed everything." The right nuance: embed is an **explicit step the agent or operator chooses**, and *the choice flows through autonomy* — so an `autonomous` workspace can embed liberally, a `manual` operator approves each embed. **The autonomy mode is the embed policy.**

---

## The structural fit (why this needs zero new mechanism)

ADR-307's gate (`permission.py`) already has the exact taxonomy this needs:
- A primitive NOT in `READ_ONLY_PRIMITIVES` is **consequential** → it passes the gate.
- A consequential primitive in `GATE_QUEUEABLE_PRIMITIVES` resolves, per call, from `autonomy_mode` to **APPLY** (autonomous) / **QUEUE** (bounded/manual → `action_proposals`) / **DENY** (governance-locked).
- Each gate-queueable primitive may carry an **orthogonal resource ceiling** (Schedule's pace cap, RuntimeDispatch/DispatchSpecialist's token budget) — "additive checks, not replaced by the autonomy gate" (`permission.py:126-128`).

`Embed` drops straight in:
- **NOT** in `READ_ONLY_PRIMITIVES` → consequential. ✅
- **IN** `GATE_QUEUEABLE_PRIMITIVES` → manual/bounded QUEUE, autonomous APPLY. ✅ (The autonomy mode is the embed policy — exactly the operator's design.)
- Carries an **orthogonal cost ceiling** (embedding-call budget) like RuntimeDispatch. ✅
- Authored by the Reviewer/agent/operator → inherits attribution + the whole gate. ✅

No bespoke embed-policy mechanism. No new gate. `Embed` is a consequential tool governed by the autonomy trifecta like everything else. This is the structurally future-proof answer the operator asked for ("see how existing autonomy and permissions are executed to give a clearer structural future-proof approach").

---

## Decision (proposed)

### D1 — Introduce an `Embed` primitive.
`Embed(path)` (or `Embed(path, scope=)`) — make the file at `path` AI-ready: compute its embedding, store in `workspace_files.embedding`, so `QueryKnowledge` (semantic search) can rank it. Idempotent (re-embedding a current file is a no-op via content-hash check, already the pattern at `workspace.py:642`). Consequential; gate-owned.

### D2 — Delete the fire-and-forget side-effect.
Remove the `_embed_workspace_file` call from `handle_write_file`'s `scope='context'` branch (`workspace.py:672`). Embedding is no longer a silent side-effect of *any* write — it is the explicit `Embed` primitive. (Singular Implementation: one way to embed.) The `_embed_workspace_file` *helper* survives as the embed mechanism the `Embed` handler calls; only its automatic invocation dies.

### D3 — `Embed` is autonomy-governed via the ADR-307 gate.
Add `Embed` to `GATE_QUEUEABLE_PRIMITIVES`. Under `manual`/`bounded` a Reviewer/agent `Embed` call QUEUEs to `action_proposals` (operator approves which files get indexed); under `autonomous` it applies. Operator-direct and headless callers apply per their own paths (the gate scopes the autonomy decision to Reviewer-runtime calls per ADR-293, unchanged). **The autonomy mode is the embed policy — no separate config.**

### D4 — `Embed` carries an orthogonal cost ceiling.
Embedding calls cost money (OpenAI API). Like RuntimeDispatch's token budget, `Embed` checks an additive resource ceiling (a per-period embed-call budget, or folds into the existing `_token_budget.yaml` governance ceiling as an embed-call line). Prevents an autonomous workspace from running up unbounded embedding cost. Scoped at implementation — reuse the existing budget plumbing, don't invent a parallel ceiling.

### D5 — Scope WHICH files are embed-*eligible* (the "carefully" the operator asked for).
Not every file should be embeddable — embedding `governance/_pace.yaml` is pointless. Embed-eligibility is by *content kind*, not blanket:
- **Embed-eligible** (semantic-search targets): accumulated domain context (`operation/{domain}/**`), uploaded reference material (`uploads/**`), authored prose the operator wants discoverable (reports, notes).
- **Embed-ineligible** (machine config / structured state / tiny files): `governance/*.yaml`, `*_recurrences.yaml`, signal YAML, `_principles.yaml` — these are read by path, never semantically ranked.
- The eligibility rule is a content-kind check (extension + root + size heuristic), surfaced so `Embed` on an ineligible file returns a clear "not embed-eligible" rather than silently wasting a call. This is the discipline that keeps us off the "100% embed" anti-pattern: **embed is selective by content-kind AND chosen by autonomy.**

### D6 — Re-home the inconsistent existing embeds.
- Upload (`documents.py:212-223`): instead of auto-embedding an excerpt in the route, the upload completes as ingest (author `uploads/{slug}.md`); embedding becomes an explicit `Embed` the operator/agent chooses (or an `autonomous` workspace auto-applies via the gate). Consistent with all other files.
- Identity/brand (post-ADR-324 dissolution): if the operator wants identity/brand semantically searchable, it's an `Embed` call like anything else — not a special case.
- Net: **one embed path, one gate, one policy (autonomy), one eligibility rule.** The three-door inconsistency dissolves.

---

## What this is NOT

- **NOT a 100%-embed principle.** Explicitly the opposite — embed is selective (D5 content-kind eligibility) AND chosen (D3 autonomy governance). The operator's exact instinct.
- **NOT a new gate or autonomy mechanism.** It reuses ADR-307 wholesale. `Embed` is just another consequential gate-queueable primitive.
- **NOT removing semantic search.** `QueryKnowledge` (the read side) is unchanged; this changes *how files become semantically searchable* (explicit Embed, not auto side-effect), not how they're queried.
- **NOT blocking the rest of the arc.** Independent of ADR-321/322/323; pairs with ADR-324 (which removes InferContext) — together they decompose the file-operation tangle into its fundamentals.

---

## Claim tiering

- **FORCED (by the evidence):** embed is currently inconsistent (one of three doors) + automatic + cost-invisible. That's a defect against the filesystem-native coherence goal.
- **DP16/DP23-GROUNDED (the OS + one-gate frame):** embed-as-gated-consequential-primitive — it inherits ADR-307 because that's the uniform action-permission model. Sound while we hold the one-gate frame.
- **DESIGN CHOICE (selected):** the content-kind eligibility rule (D5); whether the cost ceiling is its own budget or a `_token_budget.yaml` line (D4); the exact `Embed` signature. Defensible; decided at ratification/implementation.
- **PRESERVED:** `QueryKnowledge`, `workspace_files.embedding` column + RPC, the embed mechanism (`get_embedding`), the content-hash idempotency.

---

## Scope / blast radius

Medium. Single PR (pairs naturally with ADR-324; can land together or separately):
1. New `api/services/primitives/embed.py`: `EMBED_TOOL` + `handle_embed` (calls the surviving `_embed_workspace_file` mechanism + the eligibility check).
2. `registry.py`: add `Embed` to `CHAT_PRIMITIVES` + `HEADLESS_PRIMITIVES` (+ `REVIEWER_PRIMITIVES`? — a Reviewer choosing to index a domain file it just wrote is plausible; decide at ratification) + `HANDLERS`.
3. `permission.py`: `Embed` is consequential by omission from `READ_ONLY_PRIMITIVES`; ADD to `GATE_QUEUEABLE_PRIMITIVES`.
4. `workspace.py`: DELETE the `_embed_workspace_file` auto-call from the `scope='context'` write branch (D2); keep the helper.
5. `documents.py`: upload no longer auto-embeds (D6); ingest completes as author-only.
6. Eligibility helper (D5): content-kind check (root + extension + size).
7. Cost ceiling (D4): reuse budget plumbing.
8. Canon: `primitives-matrix.md` (new `Embed` row, `file` family / `asset-render`-adjacent tag; note semantic-index is now explicit), GLOSSARY, CLAUDE.md ADR-summary.
9. `api/prompts/CHANGELOG.md` (new tool — prompt change; guidance on when to Embed).
10. Regression gate `api/test_adr325_embed_primitive.py`: (a) `Embed` is consequential (gates); (b) under manual/bounded a Reviewer `Embed` QUEUEs; under autonomous it applies; (c) `scope='context'` write no longer auto-embeds; (d) `Embed` on an ineligible file (`governance/*.yaml`) returns not-eligible; (e) `Embed` on an eligible file populates `workspace_files.embedding` + makes it `QueryKnowledge`-rankable; (f) idempotent re-embed is a no-op.

---

## Open questions (deferred to ratification)

1. **Reviewer surface** — should `Embed` be in `REVIEWER_PRIMITIVES`? A Reviewer that just wrote a domain synthesis might want it indexed. But per the ADR-299 tool-count-corrosive-to-judgment finding, every Reviewer tool addition needs canary-validation. Default NO until evidence; revisit.
2. **Cost ceiling home (D4)** — own budget vs `_token_budget.yaml` line. Lean toward the existing governance ceiling (one budget surface) unless embed cost dynamics differ enough to warrant separation.
3. **Auto-embed-on-autonomous convenience** — under `autonomous`, should *eligible* writes auto-`Embed` (the gate applies it without a separate call), or always require an explicit `Embed` call? The former restores some convenience for autonomous workspaces while keeping manual/bounded explicit. Decide at ratification — it's the difference between "autonomy mode is the embed policy" meaning *gate-applies-explicit-calls* vs *auto-triggers-eligible-writes*.

---

## Relationship to other ADRs

- **Sibling of ADR-324** (InferContext dissolution) — together they decompose the file-operation tangle: ADR-324 removes the false primitive (the identity/brand merge workflow), ADR-325 adds the true fundamental operation (make-AI-ready). The discourse §5 taxonomy (one authored write; producers; embed as derived index) is realized by the pair.
- **Inherits** ADR-307 (the unified permission gate — `Embed` is a consequential gate-queueable primitive, zero new mechanism) + ADR-293 (autonomy scopes Reviewer-runtime calls) + Derived Principle 23 (one gate, one queue).
- **Amends** ADR-174 Phase 2 (the fire-and-forget context-embed — replaced by the explicit primitive) + ADR-151 (`QueryKnowledge` semantic search — its index is now populated explicitly, not as a write side-effect).
- **Preserves** `QueryKnowledge`, the `workspace_files.embedding` column + `semantic_search_workspace` RPC, `get_embedding`, content-hash idempotency.
- **Part of** the post-ADR-320 surface re-grounding arc (ADR-321/322/323/324/325).
