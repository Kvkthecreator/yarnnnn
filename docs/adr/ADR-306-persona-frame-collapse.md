# ADR-306: Persona-Frame Collapse — The System Prompt Carries Only the Model↔Runtime Interface Contract

**Status**: **Implemented + validated** 2026-05-29 (Phases A–F all landed; commit `e881a3e` + validation `c60ed86`; falsifiable prediction held on all four dimensions — see §Implementation + the [validation finding](../evaluations/2026-05-29-persona-frame-collapse-VALIDATION.md))
**Date**: 2026-05-29
**Deciders**: KVK (operator) + Claude (collaborator)
**Hat**: A (system canon — real-operator-facing)

> **Evidence base**: [`docs/evaluations/2026-05-29-persona-frame-collapse-ablation.md`](../evaluations/2026-05-29-persona-frame-collapse-ablation.md) (per-section ablation verdicts + risk register) + [`docs/evaluations/2026-05-29-reviewer-action-grammar-framing-gap.md`](../evaluations/2026-05-29-reviewer-action-grammar-framing-gap.md) (the confabulation finding that triggered the inquiry).

---

## Context

The Reviewer's system prompt (the persona-frame, `api/agents/reviewer_agent.py`) had grown to ~36K chars across 13 `_compute_*` sections. The 2026-05-29 framing-gap finding showed two of those sections *contradicting each other* on the Reviewer's action-grammar (directs vs. executes), producing confabulation that survived into a *validated* eval session. That contradiction was a complexity smell: an artifact so large that its own sections disagree and the disagreement isn't caught until a transcript-vs-receipt audit.

The deeper question (operator-raised): **does the persona-frame need to exist at all, given YARNNN already has the Claude-Code-analogous triad — authored substrate (= the repo/filesystem), primitives (= tools), and the dispersed operator-authored governance files (= CLAUDE.md)?**

Claude Code's decomposition is: filesystem + tools + user-authored CLAUDE.md + a *thin, stable* system prompt. YARNNN had clean analogues for the first three (authored substrate, primitives, the dispersed MANDATE/IDENTITY/principles/AUTONOMY set) but a **36K bespoke system-authored persona-frame** where Claude Code has ~2-3K. That asymmetry was the divergence to interrogate.

## The three fundamental Claude-Code/YARNNN differences (real, axiom-worthy)

YARNNN genuinely differs from Claude Code in three ways — but each is carried by **substrate + code**, not by system prose:

| Fundamental | Carried by | NOT by |
|---|---|---|
| **Δ1 on-behalf-of** — installed judgment acting unsupervised, not a user-driven tool | MANDATE.md + standing_intent.md (substrate) | persona-frame narration |
| **Δ2 identity-infusion** — a persona-bearing *someone* (qualitative + mechanical) | IDENTITY.md + _autonomy.yaml + _pace.yaml (substrate) | persona-frame narration |
| **Δ3 self-referential governance** — the agent's own "CLAUDE.md" is in its repo and it can amend it | substrate-location + write-locks (code) + ADR-209 attribution | persona-frame narration |

The persona-frame was largely **the system narrating its own architecture to the model** — re-teaching what the substrate files declare and the envelope already renders with labeled headers. That is the **ADR-281 anti-pattern ("the kernel does not author its own pedagogy") applied at the behavioral layer.** ADR-281 ruled substrate *organization* is bundle-shipped operator-canon; the persona-frame was Python-injecting substrate *semantics + behavior*.

## Decision

**The system-authored prompt layer collapses to the MINIMAL shape — carrying only the two things that are irreducibly system-authored because neither is the operator's to declare:**

**D1 — Principal-shift.** "You are installed judgment acting on the operator's behalf, not an assistant awaiting instruction." This corrects the *model's trained assistant prior* — a model reading IDENTITY.md through its assistant prior becomes "a helpful assistant playing the persona." It cannot live in operator substrate because it is not an operator declaration; it is a property of installing judgment over an assistant-trained model.

**D2 — Action-grammar.** The agent↔runtime interface contract: a tool call IS the action (you direct, the runtime executes, the substrate revision is the channel); the anti-confabulation rule (narrate only what tool calls returned); read-fresh-not-cached; close-every-cycle-with-a-verdict-or-standing-intent-write. This cannot live in substrate because it is the protocol between agent and runtime, not data the agent reasons over. It is the cc8e0ab fix, proven load-bearing.

**D3 — Everything else moves to its correct home (the inverted boundary).** The reasoning-posture content that filled 11 of the 13 sections is reclassified:

- **Rules of judgment** (self-amendment evidence-patterns, the six anti-patterns, independence, when-to-Clarify, the fiduciary principle) → **`principles.md`** (operator/bundle substrate, rendered every wake under "## principles.md — Your framework"). These fit the §3.2.1 four-field rule shape; they were mis-classified as "reasoning posture."
- **Substrate pedagogy** (cadence-trifecta, wake-context discipline, pulse-file reading, preferences semantics, workbench purpose) → **`_workspace_guide.md`** (ADR-281's home) + the envelope's own labeled headers.
- **Code-enforced** (write-locks, AUTONOMY application) → no prose; the gate holds and the tool result reports it.

**D4 — §3.2.1 boundary inverted.** `agent-composition.md` §3.2.1's "what does NOT belong in principles.md" bright-line table is rewritten: self-amendment / anti-patterns / independence / fiduciary are now **principles.md content** (rules of judgment), not persona-frame content. The minimal frame holds only D1 + D2. This inverts the prior framing (hardened 2026-05-23, commit d8d0e57).

**D5 — Anti-rebloat constraint (FOUNDATIONS Derived Principle, Phase D).** The fundamentals are carried by substrate + code; the system prompt narrates none of them and re-teaches no substrate file. Every future addition to the frame must answer "is this correcting the model's prior or defining the runtime interface?" — if not, it belongs in substrate or code. This is the constraint that prevents the frame from re-bloating to 36K.

Net: the system frame goes from ~36K chars (13 sections) to ~3.5K chars (1 section). 90% reduction.

## What this supersedes / amends

- **Supersedes** the 13-section `_compute_*` registry structure documented in **ADR-302** (the registry shape it shows is collapsed to `_compute_minimal_frame`).
- **Amends ADR-295** — the self-amendment evidence-patterns + six anti-patterns + fiduciary principle relocate from the persona-frame `_compute_self_amendment_discipline` / `_compute_anti_patterns` sections to `principles.md` (bundle templates). The *discipline itself is unchanged*; only its canonical home moves. ADR-295's categories survive verbatim as principles.md rules.
- **Amends ADR-303** — the P1–P5 posture taxonomy: the dispatcher-synthesized cells (P4/P5) stay code; the model-facing contract compresses to the minimal frame's "close every cycle with a verdict or a standing_intent write" line.
- **Amends ADR-305** — ADR-305's "the categories survive in the persona-frame `_compute_self_amendment_discipline`" statements are superseded; the categories now live in principles.md per D4.
- **Inverts** `agent-composition.md` §3.2.1 boundary (per D4).
- **Extends** ADR-281 (kernel-does-not-author-its-own-pedagogy) to the behavioral layer.
- **Builds on** the 2026-05-29 framing-gap fix (cc8e0ab) + §3.2.2 composed-coherence canon.

## What this preserves

- FOUNDATIONS Axioms 1–8. The collapse is *consistent with* Axiom 1 §4 + Axiom 2 (it removes prose that contradicted them).
- All autonomy-safety: the anti-patterns relocate to principles.md (still read every wake); the hard gates (`should_auto_apply`, `ceiling_cents`, write-locks) were always code and are untouched.
- The non-assistant posture (D1, the one thing that genuinely fights the assistant prior).
- The action-grammar (D2, the cc8e0ab fix).
- ADR-194 v2 Reviewer substrate, the seat structure, the occupant model.

## Risk + revert

Each phase is a separable commit. The load-bearing risk — autonomy-safety regressing — is mitigated structurally: the safety discipline is *relocated, not deleted* (alpha-trader principles.md already carried it; alpha-author's was migrated in Phase B), and the hard gates are code. If re-validation (Phase F) shows behavioral regression, revert the Phase A commit and the system returns to the cc8e0ab state (working, deployed). **Validation runs against alpha-trader first** (its principles.md already carries the migrated content, so it is safe to validate immediately); alpha-author validation is gated on its Phase B migration (now complete) + Phase C/E.

## Implementation

- **Phase A (Implemented 2026-05-29)**: `reviewer_agent.py` persona-frame → `_compute_minimal_frame` (single section, ~3.5K chars). Prompt assembles; action-grammar + anti-confabulation + principal-shift invariants present.
- **Phase B (Implemented 2026-05-29)**: §3.2.1 + §3.2.2 inverted; alpha-author `principles.md` gains §3.5 (self-amendment + anti-patterns + independence, migrated); both bundles' persona-frame pointers flipped. (alpha-trader principles.md already carried the rules.)
- **Phase C (Implemented 2026-05-29)**: substrate-pedagogy (wake envelope, wake-source taxonomy, pulse discipline, cadence-trifecta, serialized cycles, preferences/notifications, standing-intent workbench) migrated into both bundles' `_workspace_guide.md` (~206/208 lines each).
- **Phase D (Implemented 2026-05-29)**: FOUNDATIONS Derived Principle 22 (the anti-rebloat constraint) + v8.7 header/version-table entry.
- **Phase E (Implemented 2026-05-29)**: 9 collapse-consequence tests re-pointed to the content's new home (principles.md / workspace-guide / code / minimal-frame contract) — none weakened. Found + hardened a 10th test (`test_adr301::test_persona_frame_pulse_discipline`) that was *false-passing* via an `_ok/_bad`+try/except-ImportError shape. Added a when-to-Clarify rule to both bundles' principles.md (closes the §5-pointer migration gap). `CHANGELOG [2026.05.29.2]`. 2 pre-existing failures (envelope-count drift + Py3.9 union-syntax) left untouched, proven independent.
- **Phase F (Implemented + PASS 2026-05-29)**: committed as one revertable commit `e881a3e`, pushed, deployed live (`dep-d8cfuv7aqgkc73d4mcjg`, 02:54:50Z). Re-validated via the confabulation wake against the collapsed frame (yarnnn-author / alpha-author program). The prediction below HELD on all four dimensions with full substrate receipts — confabulation absent (real WriteFile attempt → `substrate_write_requires_autonomous` gate → receipt-matching narration), non-assistant posture preserved, autonomy-safety preserved (0 writes/proposals landed), mandate-coherence equal-or-better (cited its own ADR-284 contract). **Collapse KEPT; no revert.** A harness false-empty-capture bug (the prior session's INCONCLUSIVE cause) was diagnosed + fixed in the same validation pass (`c60ed86`). Full receipts: [validation finding](../evaluations/2026-05-29-persona-frame-collapse-VALIDATION.md).

## The falsifiable prediction (Phase F judges this)

The collapsed frame produces **equal-or-better** behavior than the 36K frame on: confabulation (absent — action-grammar preserved), non-assistant posture (preserved — principal-shift preserved), autonomy-safety (preserved — anti-patterns in principles.md + gates in code), mandate-coherence (equal-or-better — less system narration competing with the operator's MANDATE for the model's attention). Any regression falsifies the thesis for that dimension and reverts Phase A.
