# ADR-324 — Derive-from-Substrate Producer: Generalizing `InferContext` (DEFERRED — named, not built)

> **Status**: DEFERRED STUB (2026-06-07). Named so the horizon is known-intentional and has a number; **NOT to be implemented in the current arc.** Bundling a new *capability* with the post-ADR-320 *cleanup* (ADR-321/322/323) would repeat the anti-pattern ADR-320's discipline warns against. This is a forward ADR, opened only when demand surfaces.
> **Date**: 2026-06-07
> **Authors**: KVK, Claude
> **Upstream**: [primitive-surface-grounding discourse](../analysis/primitive-surface-grounding-2026-06-07.md) §5 + §5.1 (the file-operation taxonomy: one authored write; upload/infer/render are *producers* that author into the one substrate; `InferContext` is the first instance of a *derive-from-substrate producer*).
> **Dimensional classification**: **Mechanism** (Axiom 5 — a new producer shape in the primitive vocabulary).

---

## Why this stub exists

The post-ADR-320 cleanup arc (ADR-321 file primitives, ADR-322 entity pruning, ADR-323 frame collapse) is *deletion + alignment* — finishing collapses the architecture already decided. This ADR is the one **forward** thread the discourse surfaced, and it is deliberately separated so the cleanup ships clean.

The operator's framing question — *"the InferContext confusion is both problematic AND a hint at a future consideration of how we handle files at large"* — has two halves. The **problematic** half (InferContext mis-classified as a `context`-family "place") is resolved by ADR-321 D5 (it leaves the `context` family). The **hint** half is this stub.

## The thesis (for when it's time)

The discourse established (§5, with receipts) that the filesystem-native architecture has **one write** (`write_revision` — 100% of content writes route through it, ADR-209) and that upload / infer / render are not parallel file APIs but **producers**: they compute content and then author it. Their shapes:

- **Upload** = (deterministic text-extraction) → author.
- **Render** = (gateway compute) → author.
- **InferContext** = (LLM-merge over a read-set: text + uploaded-doc contents + URLs + existing file) → author.

`InferContext` is the first instance of a **derive-from-substrate producer**: *read a substrate set → run an LLM merge → author the result.* Today it is hardcoded to two targets (`persona/IDENTITY.md`, `operation/BRAND.md`) with two focused system prompts (IDENTITY_SYSTEM, BRAND_SYSTEM) + deterministic gap-detection + cost-ledger attribution.

The forward question: **is there a general derive-from-substrate primitive** of which "infer identity," "infer brand," "synthesize a brief from these uploaded docs," "draft a domain landscape from accumulated context" are instances — or do we keep per-purpose producers that share a helper?

## What §5.1 already settled (so this ADR doesn't relitigate it)

The discourse adjudicated the operator's two horns:
- **NOT "all files are pure files, drop InferContext"** — `InferContext` carries deterministic gap-detection + cost-ledger + focused merge-prompts that a generic `WriteFile` would lose. There IS a real derive operation.
- **Keep infer, generalize the frame** — the right synthesis. The architecture wants the *producer shape* generalized (any read-set → merge → authored result), not per-target infer primitives multiplied.

So this ADR's job, when opened, is **the shape of the generalization**, not whether to do it.

## Open design space (for the future ADR — explicitly undecided)

1. **One general `Derive(read_set, merge_prompt, target)` primitive** vs **per-purpose producers sharing a `derive` helper.** The former is grep/bash-elegant (one verb, parameterized); the latter keeps each producer's focused system-prompt + gap-detection co-located. Trade-off: generality vs focused-quality.
2. **Where do the focused merge-prompts live?** Today IDENTITY_SYSTEM/BRAND_SYSTEM are hardcoded. A general primitive would need them as substrate (bundle-shipped `derive-specs`?) or as caller-supplied — which touches ADR-281 (kernel does not author its own pedagogy) and the spec-library pattern (ADR-261 D6).
3. **Gap-detection generalization.** `detect_inference_gaps` is identity/brand-specific (deterministic, zero-LLM). A general producer needs a general or per-target gap pass.
4. **Relationship to `DispatchSpecialist`.** A specialist sub-LLM-call *also* reads substrate → produces → authors. Is "derive-from-substrate producer" just a *lightweight inline specialist*? Or distinct (no separate context, single merge vs multi-round)? The boundary needs drawing.
5. **Demand trigger.** This ADR opens when a *third* derive target appears (beyond identity/brand) — e.g., "infer a domain profile from these uploads," "derive a risk envelope from the operator's described strategy." Two instances (identity, brand) don't justify a generalization; three do (the rule-of-three).

## What this stub does NOT do

- Does NOT change `InferContext` (it stays exactly as it is; ADR-321 D5 only corrects its *family label* from `context` to producer).
- Does NOT add any primitive.
- Does NOT block ADR-321/322/323 — those ship without it.

## Trigger condition

Open this ADR when a **third** derive-from-substrate target is demanded (rule-of-three), OR when an operator/bundle needs to author a derive target the kernel doesn't hardcode. Until then it remains a named horizon — preventing the cleanup arc from being tempted to build a capability while doing a deletion.

---

## Relationship to other ADRs

- **Forward thread of** the post-ADR-320 arc (ADR-321/322/323 are cleanup; this is the one new capability the discourse surfaced).
- **Generalizes** ADR-235 (`InferContext` — the first derive-from-substrate producer) + ADR-314 (which removed `InferWorkspace`, narrowing infer to identity/brand — this would re-widen it *as a general shape*, not as scattered targets).
- **Adjacent to** ADR-261 D7 (`DispatchSpecialist` — the boundary question in §4) + ADR-281 (where the merge-specs live).
- **Preserves** ADR-209 (the producer authors via `write_revision` like everything else) + Derived Principle 19 (the kernel does not compute for the prompt — a derive producer is an *explicit* LLM call, not envelope-time computation).
