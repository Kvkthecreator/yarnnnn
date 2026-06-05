# Canon Sketches — Personified Seat as Root Entity (b1 proposals)

> **Status**: Proposal sketches for review. NOT applied to canon. Companion to [personified-judgment-seat-vs-task-harness-2026-06-05.md](personified-judgment-seat-vs-task-harness-2026-06-05.md) (the discourse) — this file proposes the *exact canon edits* that discourse implies, for KVK sign-off before any FOUNDATIONS/THESIS write.
> **Date**: 2026-06-05
> **Two sketches**: (1) FOUNDATIONS Derived Principle 25; (2) THESIS Commitment 2 sharpening (the commissioned-tool foil).
> **Compose-not-collide check done**: against Derived Principle 21 (Reviewer formalization), 22 (frame-carries-only-interface), 24 (stewardship/ADR-319 — same-session), and Axiom 1 + Axiom 2.

---

## Why these are sketches, not edits

FOUNDATIONS and THESIS are canon. The discourse doc reached `[validated]` on the *de-naming axis* and the *substrate-orthogonality* claims, but ratifying canon is an operator decision, and the directory-cut ADR (b2) should land *first in draft* so the amendment can cite a concrete decision rather than a hope. So these sketches state **what the amendment would say** and **where it slots**, for review — not as applied text.

A naming caveat threads both sketches: the discourse settled the *claim* (name the detachment, not the review function) but scoped the *rename execution* out (high blast radius — DB enum slugs, routes, doc surface). So the sketches below **keep "Reviewer" as the current term** and add the axiom-level reframing *around* it, leaving the rename to a separate pass. The principle names the entity by its nature ("detached personified judgment seat"); the rename later swaps the surface label.

---

## Sketch 1 — FOUNDATIONS Derived Principle 25

**Proposed number**: 25 (24 is the highest; ADR-319 stewardship, same session).
**Proposed title**: *The workspace root entity is a detached, personified judgment seat; person-defining and operation-shaping substrate are orthogonal regions.*
**Slots**: in the Derived Principles list, after 24. Header-line version-bump to v9.0.

### Draft principle text

> 25. **The workspace root entity is a detached, personified judgment seat; person-defining and operation-shaping substrate are orthogonal regions** (2026-06-05, ADR-320) — The durable entity a workspace exists to hold is a **detached, personified judgment seat** — the operator's installed judgment, acting on their behalf (Axiom 2 two-embodiments; Derived Principle 21's formalization). "Reviewer" names its **first Purpose** (independent judgment on proposed writes — Axiom 2 "distinctness is in Purpose + Trigger, not Identity"), not the entity itself; the entity is the *detachment + personification* from which independence follows (THESIS Commitment 2 — independence is detachment-from-producers + judgment-against-ground-truth, never the *review* function). **Two corollaries of treating the seat as the root entity:**
>
> **(a) Permission is topological: the directory determines who may write, for every caller, with no file enumeration.** Axiom 1 (identity manifests through filesystem) + Axiom 2 (identity is orthogonal to mechanism) + Derived Principle 16 (literal OS framing) *together require* that the workspace root *be* the permission taxonomy. ADR-320 resolves this to **five top-level roots, each one semantic class named by the directory**: `governance/` (operator-only ceilings the seat runs under but cannot set), `constitution/` (operator intent the seat amends; read by all), `persona/` (the seat — how it reasons + its trail; occupant-agnostic), `operation/` (the work the agent operates on/produces; many writers), `system/` (orchestration runtime accumulation; not Identity-bearing). Today these intermingle in `context/_shared/` (receipt: the alpha-trader reference-workspace tree), blurring an orthogonality the axioms declare. The write-lock becomes `access(2)` for the agent OS: one `_is_path_locked(caller_class, path)` over a per-caller prefix table — *the seat may write everything it is not structurally restricted from* (`governance/` + `system/`), restriction-by-region not restriction-by-enumeration. This collapses the two divergent lock functions (`_is_path_locked_for_reviewer` flat-list + `_is_path_locked_for_mcp` prefix) into one, and is *more* OS-faithful than the status quo (which co-locates `/etc`-class, `~/.config`-class, and `~/Documents`-class in one directory — something no OS does). See [ADR-320](../adr/ADR-320-constitution-region-topological-cut.md).
>
> **(b) The person-defining region is a required region; "onboarding" is its first authoring, not a phase.** The constitution must be non-empty for the workspace to operate — generalizing ADR-207's MANDATE hard-gate from one file to the whole region. Onboarding dissolves into *the first time the operator authors a required region*; thereafter it is maintained like any substrate. **The product has two co-equal durable halves** — the always-present **orchestration system** (Axiom 2: not Identity-bearing; a *different actor* per ADR-257) and the **personified agent** — with an **operation** a third attachment. This is why a pre-operation (bare) workspace is *coherent*, not empty: the agent half is real and maintained even when no operation gives it ground truth; the system half carries it. (The agent/system/operation weight ratio is co-equal today, subject to change.)
>
> **What this does NOT change**: the seat's authority (Derived Principle 21 §4.4 — already near-full self-amendment); the minimal frame (Derived Principle 22 — richness goes in *substrate*, never the system frame — so "front-load the persona" means front-load `principles.md`/`IDENTITY.md`, NOT the frame); the stewardship posture (Derived Principle 24 — ground-truth moves the intent, pressure never does). It *reorders the mental model*: the seat is the entry commitment the workspace is built around; an operation is attached to an already-formed agent.
>
> **Diagnostic test**: if a substrate file's primary read-purpose is "to become the judge" it belongs in `constitution/` (or `persona/` if it is the seat's own reasoning); if "to shape the work-output" it belongs in `operation/`; if it is a ceiling the seat runs under but cannot set, `governance/`; if orchestration runtime state, `system/`. If a workspace can dispatch work with an empty constitution region, the hard-gate is missing. If the seat's write-boundary is an enumerated file-list rather than a per-caller region prefix (`access(2)`), corollary (a) is unfinished. **Composes with** Derived Principle 21 (formalization — this names *where the formalized seat's constitution lives*), 22 (frame stays minimal — substrate carries the richness), 24 (stewardship — the posture over the authority this region grants), and Axiom 1 + Axiom 2 (the orthogonality this enforces). **Canon source**: [ADR-320](../adr/ADR-320-constitution-region-topological-cut.md) + [personified-judgment-seat-vs-task-harness-2026-06-05.md](../analysis/personified-judgment-seat-vs-task-harness-2026-06-05.md).

### Compose-not-collide notes (for the reviewer of this sketch)

- **vs. DP21 (formalization):** DP21 says *what* the Reviewer is (full-substrate-authoring persona seat). DP25 says *where its constitution lives* (a required, topologically-isolated region) and *that the entity is bigger than "review."* No contradiction — DP25 is the substrate-placement + naming-altitude companion to DP21's nature statement. DP25 must cite DP21, not restate it.
- **vs. DP22 (frame-minimal):** the one collision risk is "front-load the persona" → re-bloat the frame. DP25 explicitly defers to DP22: richness → substrate, frame stays minimal. Stated in "What this does NOT change."
- **vs. DP24 (stewardship):** DP24 governs *how the granted authority is used* (posture). DP25 governs *where the constitution that grants it lives* (topology) + *what the entity is* (naming). Orthogonal; DP25 cites DP24 as the posture-over-the-authority.
- **vs. Axiom 2 two-embodiments:** DP25 leans on it directly (the seat = operator's installed judgment). No new claim about embodiments; it *applies* the existing one to substrate topology.

---

## Sketch 2 — THESIS Commitment 2 sharpening (the commissioned-tool foil)

**Slots**: as a new dated sharpening paragraph inside Commitment 2, *after* the existing "ADR-319 sharpening (2026-06-05)" paragraph, *before* the `*Implemented by*:` line. Same paragraph-form as the ADR-253 + ADR-319 sharpenings already there.

### Draft sharpening text

> **Two-poles sharpening (2026-06-05): independence is the property of the *delegated-agent* pole, named against the *commissioned-tool* pole it is not.** The wider LLM-runtime ecosystem is bifurcating into two poles (see [personified-judgment-seat-vs-task-harness-2026-06-05.md](../analysis/personified-judgment-seat-vs-task-harness-2026-06-05.md)). The **commissioned-tool** pole (exemplified by per-task agent harnesses — e.g. Anthropic's dynamic Claude Code workflows) is a transient orchestration the human *wields*: intelligence lives in the spawning graph, verification happens **in space** (parallel adversarial sub-agents, *now*), and nothing persists — there is no standing intent, no track record, no stake, so there is nothing for "independence" to be a property *of*. The **delegated-agent** pole (YARNNN) is a durable seat the human *delegates authority to*: intelligence lives in persistent substrate, verification happens **in time** (the calibration loop reconciling verdicts against ground-truth outcomes, *later*), and the seat *is* the independent thing precisely because it persists with standing intent and accountable tenure. This sharpens what independence *is*: not a within-run check (the commissioned pole's move, which YARNNN's ADR-272 deliberately declined for the seat — judgment is done inline, not fanned out to sub-agents), but a **structural property of a detached, accountable, persistent seat judged against ground truth over tenure.** The commissioned pole *cannot* have this property; the delegated pole *is constituted by* it. The cost of the delegated pole is a **cold-start seam** the commissioned pole avoids by never relying on tenure: the first high-stakes verdict after an operation attaches has no calibration history yet — managed by defer-to-human or tighter cold-start `principles.md`, never by importing the commissioned pole's fan-out (which would break the seat's economic model and its single-voice personification).

### Compose-not-collide notes

- **vs. existing C2 body:** the body already says independence = "judgment evaluated against ground-truth substrate, not against internal agreement with producers." The sharpening *names the foil* that makes this sharp (the commissioned pole, which has nothing to be independent of) and ties it to ADR-272 (inline, not fan-out). It extends, doesn't contradict.
- **vs. ADR-319 sharpening (immediately above it):** ADR-319 added "independence from the operator's own pressure." This adds "independence as the *delegated-pole* property named against the *commissioned-pole*." Different axis (the prior is *from-whom*; this is *what-kind-of-system*). They stack cleanly.
- **Naming caveat:** keeps "reviewer"/"seat" as-is; the de-naming is a separate pass.

---

## What b1 deliberately leaves to b2 (the ADR)

These sketches assert the *axioms*. The **decisions** they imply are the ADR's job (b2), and the sketches above cite "[ADR-directory-cut]" as a placeholder precisely so the amendment lands *after* the ADR fixes:

1. **The region names + boundaries** — what the constitution region is *called* and its exact path (e.g. a root `/workspace/constitution/` vs. keeping `context/_shared/` and splitting operation-config out). The sketch says "distinct regions"; the ADR picks the topology.
2. **PRECEDENT's side** — the discourse flagged it borderline (leans person). The ADR must decide.
3. **Lock topology** — flat-list → subtree-prefix is sketched; the ADR specifies the prefix set + the migration off `DEFAULT_REVIEWER_WRITE_LOCKS`.
4. **Hard-gate shape** — one aggregate check vs. per-file; what "non-empty/non-skeleton" means for the region (reuse `workspace_utils.is_skeleton_content`).
5. **Fork compatibility** — the three-way branch (`write_new` / `write_refresh_skeleton` / `skip_operator_authored_prose`) must keep working across the file moves; the ADR names this as a preserved invariant.

The sequencing discipline (per the discourse §6): **b2 ADR drafts → resolves 1–5 → then DP25 + the THESIS sharpening land citing it.** Do NOT apply DP25 before the ADR fixes the topology, or the principle cites decisions that don't exist yet (the exact drift FOUNDATIONS §5.3 warns against).
