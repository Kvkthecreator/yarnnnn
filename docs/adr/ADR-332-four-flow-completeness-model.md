# ADR-332 — The Four-Flow Operation Completeness Model (framing)

**Status:** **Ratified (framing)** — 2026-06-10. Canon cascade lands in the same commit (FOUNDATIONS v9.1 Derived Principle 26, GLOSSARY v2.4, ESSENCE v14.1). No code in this ADR; the model's enforcement artifacts land with their owning ADRs (§5).
**Date:** 2026-06-10
**Deciders:** KVK (operator) + Claude (collaborator)
**Hat:** A (system canon)

> **Discourse base (the 2026-06-10 capture chain, in order):**
> [`author-blindness-and-invariant-capabilities-2026-06-10.md`](../analysis/author-blindness-and-invariant-capabilities-2026-06-10.md) (invariants → flows) →
> [`reality-in-current-standing-and-setup-as-rendering-2026-06-10.md`](../analysis/reality-in-current-standing-and-setup-as-rendering-2026-06-10.md) (the audited four-flow standing) →
> [`four-flow-completeness-and-program-floor-2026-06-10.md`](../analysis/four-flow-completeness-and-program-floor-2026-06-10.md) (the model + Direction A reaffirmation — the primary source this ADR canonizes) →
> [`perception-under-calibration-arc3-foundation-2026-06-10.md`](../analysis/perception-under-calibration-arc3-foundation-2026-06-10.md) (the arc-3 perception foundation, deferred).

**Amends:** FOUNDATIONS (new Derived Principle 26; version v9.1) · GLOSSARY (v2.4 — Four Flows vocabulary) · ESSENCE (v14.1 — the asset's world-facing half).
**Composes with:** [ADR-222](ADR-222-agent-native-operating-system-framing.md) (OS framing — programs as applications), [ADR-320](ADR-320-constitution-region-topological-cut.md) (five-root topology — flows write into `operation/`), [ADR-330](ADR-330-ground-truth-intake.md) (flow 3 generalized; its D4 gate is this model's first conformance instance), [ADR-331](ADR-331-setup-as-rendering.md) (`/setup` = flow-declaration walking), ADR-287 (bundle conformance discipline), Direction A ([bare-kernel-product-floor-2026-06-01.md](../architecture/bare-kernel-product-floor-2026-06-01.md)).
**Preserves:** FOUNDATIONS Axioms 0–9 (this is a derived-principle addition, not an axiom change) · Axiom 2's perception-layer taxonomy (§D1 relates the two views) · ADR-153 · ADR-222's no-workspace-types rule.

---

## 1. Context

Four discourse sessions on 2026-06-10 converged on one structural account of what an operating YARNNN workspace *is*, why generic workspaces feel "off," why Direction A (program-activation as the product floor) was right, and what the remaining build arcs share. The account is load-bearing for onboarding (ADR-331), ground-truth intake (ADR-330), the future perception arc, and bundle authoring — but it lived only in dated Hat-B captures. This ADR promotes it to canon.

## 2. Decisions

### D1 — The four-flow model is canonical

An **operating workspace runs four flows**:

| Flow | What it is | Detail |
|---|---|---|
| **1. Context in** (perception) | World-state entering, feeds production | Three sub-modes by origin/time: self-past (harvest, ADR-331), self-present (live reads + operator push), world-present (the **perception field** — arc-3, deferred) |
| **2. Work out** (the acts) | Artifacts / transactions / messages leaving | The act-shape map; artifact acts are kernel-universal |
| **3. Outcomes in** (ground-truth intake) | Reality's verdict on the operation's **own** acts | The **coupling term** between self and world — neither pure perception nor pure action, which is why Axiom 8's substrate is the moat's spine. Generalized by ADR-330. |
| **4. The loop** (calibration) | Outcomes reconcile against verdicts → sharper judgment | ADR-327; runs only where flow 3 exists |

**Relation to Axiom 2's perception layers** (external / user-contributed / internal / reflexive): the perception layers are the **source taxonomy** (where signals come from); the four flows are the **loop view** (directional completeness of one operation cycle). They compose without conflict — e.g., reflexive perception is largely flow 3+4 content viewed by source.

### D2 — Flow-incompleteness is the diagnosis vocabulary

The felt "offness" of a generic workspace is **flow-incompleteness** — not UX, not ICP, not cold-start (those are symptoms). alpha-trader feels like an operation because all four flows run; it was, at ratification time, the only flow-complete instance. **Diagnostic test:** when a workspace or program "feels partial," enumerate its four flows; the missing or undeclared flow is the diagnosis, and the remedy is a *declaration* (bundle-side) or an *intake/transport* (kernel slot) — never a parallel subsystem.

### D3 — A program IS a flow-declaration set (Direction A's positive account)

What a bundle ships — oracle + `substrate_abi.ground_truth` (flow 3), context domains + universe + recurrences (flow 1), capabilities (transports for flows 1+2), deliverable specs (flow 2), plus the Reviewer persona and surfaces — **is the four flows, declared.** Direction A ("program-activation is the product floor") therefore reads: *you cannot operate with undeclared flows.* Consequences, all ratified:

- **No default program** (a flow-declaration set with no operation behind it would recreate the shapeless workspace one level up). The bare kernel stays an inspect-only resting state.
- **No freehand workspace-level flow declarations** — flow slots are what *programs* declare. Operator-assembled programs (the deferred ADR-312 horizon) arrive, if ever, as *assembling a program*, never as a parallel declaration path. Singular path preserved: signup → resting kernel → `/setup` → pick program → walk its declared flows to completeness.
- **ADR-331's `/setup` sequence is flow-declaration walking** — the kernel's definition of "becoming operational," rendered as a sequence (already cross-referenced in ADR-331's discourse-base note).

### D4 — Flow-completeness is bundle conformance (gate deferred to arc-3)

Every **active** program must declare all four flows or explicitly mark a flow N/A with rationale. ADR-330 D4 (alpha-author's ground-truth declaration + ADR-287 gate extension) is the **first instance**; the *general* four-flow conformance assertion lands with the arc-3 ADR (extending `api/test_adr287_bundle_conformance.py`, per ADR-287's same-commit discipline). Until then, D4 binds as authoring discipline for any new or amended bundle.

### D5 — The perception field is arc-3, with its foundation fixed now

Flow 1's world-present cell (the perception field) is deferred to a future arc-3 ADR, demand-pulled (triggers: bundle #3, first non-trader watch need, or alpha-author post-330 deepening). Its conceptual foundation is **fixed by this ADR** so it cannot drift: the three-layer cut (declaration / observation-contract / transport-as-driver), perception-under-calibration (flow 4 judges attention; the trader's `by_signal` attribution is the existing proof), the MCP-client-not-connector-catalog transport posture, and the candidate axiom clauses — *reality enters only as attributed observation; watches are declared, never crawled; transports are peripherals; attention is calibrated* — per [`perception-under-calibration-arc3-foundation-2026-06-10.md`](../analysis/perception-under-calibration-arc3-foundation-2026-06-10.md). FOUNDATIONS axiom-text treatment of those clauses happens at arc-3 ratification, not now.

### D6 — Canon cascade (same commit)

- **FOUNDATIONS v9.1** — new Derived Principle 26 (the model, the diagnosis, program-as-flow-declaration-set, the conformance commitment, the perception discipline pointer).
- **GLOSSARY v2.4** — Four Flows vocabulary section (four flows · flow-completeness · perception field [forthcoming]). *Deliberately excluded:* "ground-truth intake" / "consequence pipe" entries — those land with **ADR-330 Phase 5**, which owns the Axiom-8 vocabulary work (no duplication).
- **ESSENCE v14.1** — one addition: the cumulative asset's **world-facing half** (the workspace accumulates not only your work but your declared universe's distilled history under your judgment).

## 3. What this ADR does NOT do

No code. No new subsystem (Derived Principle 7 / the dual-tracking bright line stand). No perception build (arc-3). No axiom change (derived principle only). No GLOSSARY entries owned by ADR-330 P5. No bundle edits (alpha-author's flow-3 fix is ADR-330 D4's).

## 4. Falsifiability / revisit triggers

Revisit if: (a) a workspace demonstrably operates well with a structurally absent flow that isn't N/A-by-nature (would falsify D2's diagnosis claim); (b) operator-assembled programs arrive and need workspace-level declarations after all (would amend D3's third consequence); (c) arc-3's observation contract proves un-unifiable with `OutcomeCandidate`'s attestation shape (would weaken the D5 foundation).

## 5. Follow-up ledger (docs that inherit this model later — tracked here so nothing drifts silently)

| Doc | What changes | When |
|---|---|---|
| `docs/architecture/SERVICE-MODEL.md` | Execution-flow framing gains the four-flow vocabulary | At arc-3 ratification (one pass, not piecemeal) |
| `docs/architecture/WORKSPACE.md` + `docs/design/WORKSPACE.md` | `/setup` sequence + flow-declaration framing | At ADR-331 implementation (its doc cascade) |
| FOUNDATIONS Axiom 8 + GLOSSARY (ground-truth intake / consequence pipe) | Vocabulary entries | **ADR-330 Phase 5** (owns it) |
| FOUNDATIONS (perception axiom clauses) + GLOSSARY (observation, watch, perception-field full entries) | Axiom-grade treatment of D5's candidate clauses | Arc-3 ADR ratification |
| `docs/architecture/invocation-and-narrative.md` | No change required (flows are orthogonal to the invocation atom); confirm at arc-3 | Arc-3 |
| `docs/programs/README.md` | Bundle-authoring guidance: declare four flows or mark N/A | With the arc-3 conformance gate |
| ESSENCE / NARRATIVE / GTM | Already aligned (v14/v5/v4 carry the cumulative-workspace frame; v14.1 adds the world-facing half) | Done this commit |
