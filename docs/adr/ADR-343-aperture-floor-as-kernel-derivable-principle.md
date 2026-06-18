# ADR-343 — Aperture/Floor as a Kernel-Derivable Principle

**Status:** **Accepted (2026-06-18)** — IMPLEMENTED same day (kernel frame + FOUNDATIONS DP24 v9.7 + agent-composition §3.2.1; alpha-author derive-it validation). See §7.
**Date:** 2026-06-18
**Deciders:** KVK (operator) + Claude (collaborator)
**Hat:** A (system canon)

> **Discourse base:** the ADR-342 organic-close finding ([`2026-06-18-dormancy-offensive-limb-organic-close-FINDING.md`](../evaluations/2026-06-18-dormancy-offensive-limb-organic-close-FINDING.md)) + the operator's structural instruction: *"change the mandate of the kernel project fittingly — that should be the structural approach that has the potential to define future wide scenarios of different author-like project types."* ADR-342 shipped the aperture/floor split as a trader-bundle rule (file-lists: `_universe.yaml` vs `_risk.md`). This ADR lifts the split's **definition** to the kernel so every program with a production mandate inherits the *capacity to derive its own split*, not a copied file-list.

**Amends:** ADR-342 (the aperture/floor split, shipped as a trader-bundle rule, is promoted to a kernel-derivable principle; the trader's file-lists become *one program's derived instance* of the kernel definition, not the definition itself), FOUNDATIONS Derived Principle 24 (v9.6 → v9.7: the aperture/floor split gains a program-neutral definition + the Reviewer's derive-obligation).
**Composes with:** ADR-335 (the perception field's watch portfolio IS an aperture — the selection surface of what the operation perceives; aperture generalizes that to *everything the operation engages*), ADR-307 (the floor is the *consequential-gate class* — floor edits are consequential and route apply/queue/deny; aperture-widening is a normal `propose`), ADR-320 (the floor's inviolability is *mechanically* enforced by topology — risk/governance-class paths can't be widened on dormancy evidence because the path-root lock holds), ADR-332/DP26 (the floor maps onto two flows — work-out integrity + outcomes-in attestation honesty; the aperture maps onto context-in/perception).
**Preserves:** ADR-222 kernel boundary (the kernel owns the *universal category*; the program/Reviewer derives the *instances*; the kernel never names a program noun — "aperture"/"floor" are universal, "`_universe.yaml`"/"`_risk.md`" are the trader's instance), ADR-342's invariant verbatim (*ground truth (incl. dormancy) moves the aperture; pressure never lowers the floor*), agent-composition.md §3.2.1 (the *definition + derive-stance* is frame-resident; the *derived instances* are principles.md-resident).

---

## 1. Problem statement

ADR-342 gave the Reviewer an offensive limb (dormancy → research → widen aperture, never lower floor) and shipped the aperture/floor split as a **trader-bundle rule** — concrete file-lists in alpha-trader's `principles.md` (aperture = `_universe.yaml` + entry bands; floor = `_risk.md` sizing/stops/var). That is correct for the trader but leaves a structural gap: **every future author-like program (alpha-author, a marketer, an A&R, a designer) would need someone to hand-author its own aperture/floor file-lists into its bundle.** That is N copies of bespoke prose, not a structural property — and it means a *new* non-trader workspace inherits the offensive-limb *stance* (the kernel frame, ADR-342 D1) but has no aperture/floor *split* to apply it through.

The operator's instruction is the structural fix: the split's **definition** belongs in the kernel, so any program inherits the *shape* and the Reviewer **derives its own instances** from its mandate + ground-truth. This is the ADR-222 kernel-boundary discipline applied to a posture: the kernel owns the universal category, the program fills the specifics.

## 2. The kernel-level definition (program-neutral)

The two categories, defined without any program noun:

- **Floor** — the set of constraints that protect **the integrity of each individual act** and **the honesty of the ground-truth loop**. Two sub-parts, both universal:
  - *Per-act integrity*: the envelope that bounds the risk/quality of a single output (trader: sizing/stops/var/caps; author: the anti-slop quality bar + voice-fingerprint discipline; marketer: per-campaign budget caps).
  - *Attestation honesty* (ADR-330/Axiom 8): you can never fabricate that an outcome occurred — a fill, a shipped piece that landed, a conversion. The outcomes-in flow's truthfulness is floor.
  - The floor moves **only on evidence of its own mis-calibration** (the Calibration-driven pattern — e.g. ≥N reconciled outcomes showing the floor itself wrong), **never** on dormancy and **never** on pressure.

- **Aperture** — the **selection surface of what the operation engages**: which candidates it evaluates, which sources it perceives, which formats/angles it considers, how wide its net is cast. (Trader: the universe + entry bands; author: the topic scope + source set + format range; the perception field's watch portfolio per ADR-335 is an aperture.) The aperture **widens on ground-truth evidence including dormancy**, on the Reviewer's own authority under `autonomous`, research-first and bounded.

**The invariant (unchanged from ADR-342, now stated generically):** *ground truth (including dormancy) moves the aperture; pressure never lowers the floor.* A dormancy-rationalized floor edit is the pressure-capitulation in a costume, regardless of program.

## 3. The derive-obligation (the structural move)

The kernel does **not** enumerate each program's aperture and floor. It states the *definition* (§2) and obligates the Reviewer to **derive its program's instances from its own mandate + ground-truth substrate**:

> Your operation has a floor (what protects each act's integrity + the honesty of your outcomes) and an aperture (what your operation engages / selects). Derive both from your MANDATE and your ground-truth substrate. When dormancy or ground truth obligates widening, you manage the aperture; you never lower the floor.

This is the ADR-222 boundary: the kernel says *what the two categories are*; the Reviewer, reading its mandate + ground-truth, says *which of my files are which*. A trader derives "floor = `_risk.md`, aperture = `_universe.yaml`"; an author derives "floor = the anti-slop/voice bar + can't-fake-a-ship, aperture = topic/source/format scope." **No bundle prose enumerates this** — the program need only ship a mandate + ground-truth substrate (which every conformant program already does, ADR-332). The trader's existing `principles.md` aperture/floor section (ADR-342 D2) is retained as the trader's *derived instance*, useful as a worked example and a calibration anchor, but it is no longer the *source of the capability* — the capability is kernel.

## 4. Why this is over-determined by existing canon (not a new invention)

The aperture/floor split is a *name* for a partition the kernel already enforces three independent ways:

- **ADR-335 (perception field)**: watches are a *declared portfolio of attention* — a selection surface. Aperture generalizes "what you watch" to "what you engage." The "watch-first, transport-second / declaration sovereign over transport" discipline is the aperture discipline.
- **ADR-307 (one gate, one queue)**: the floor is the *consequential-action class*. Floor edits (touching risk/quality envelopes) are consequential and route through the gate (apply/queue/deny); aperture-widening is a normal `propose`/`WriteFile`. The split is already the gate's consequential/non-consequential axis.
- **ADR-320 (topology IS permission)**: the floor's inviolability under dormancy is *mechanically* enforced — risk-class + `governance/` paths are lock-gated by path-root, so "widen the floor on dormancy" can't even be written without surfacing `governance_locked`. The topology is the floor's hard backstop; this ADR makes the *posture* match the *mechanism*.

The split is therefore the judgment-layer name for what the kernel already does at the perception, permission, and topology layers. Naming it as a derivable principle aligns posture with mechanism.

## 5. Where it lands (agent-composition.md §3.2.1)

- **Kernel definition + derive-obligation → frame** (`reviewer_agent.py::_compute_minimal_frame`): this is principal-shift — it corrects the model's prior that "dormancy → act" reads as "pressure → permission to relax constraints." The shift: dormancy authorizes aperture-widening (a different discipline from floor-lowering), and you *derive* which is which. Generic across programs, no program noun → frame-legal.
- **Derived instances → principles.md** (per program): the trader's worked split (ADR-342 D2) stays as its derived instance. Other programs may either author their derived split as a worked anchor OR rely on the Reviewer deriving it live (the alpha-author test, §7, validates the latter — derive-with-no-bundle-rules).
- **Mechanical enforcement → code/topology** (ADR-320, unchanged): the floor's hard backstop is the path-root lock; no new machinery.

## 6. Scope boundary

- This ADR does **not** add a primitive, schema, or recurrence. It is canon + frame + the FOUNDATIONS definition.
- It does **not** hand-author alpha-author's (or any non-trader program's) aperture/floor instances — that is the point: the Reviewer derives them.
- It does **not** change the trader's behavior — the trader's derived instance is unchanged; ADR-343 reframes it as *one derivation*, not *the definition*.

## 7. Implementation status (2026-06-18)

IMPLEMENTED same day:
- **FOUNDATIONS DP24 v9.7**: the kernel-level aperture/floor definition (§2) + the derive-obligation (§3) added to Derived Principle 24; banner + changelog row.
- **Kernel frame** (`reviewer_agent.py::_compute_minimal_frame`): the ADR-342 offensive-limb paragraph generalized — the trader-flavored "(the universe, the entry bands, the watch set)" examples are reframed as *derive your aperture and floor from your mandate + ground-truth*, program-neutral. prompts CHANGELOG entry.
- **agent-composition.md §3.2.1 Axis-3**: the aperture/floor extension note updated — definition is kernel/frame, instances are program-derived.
- **alpha-author validation** (§the derive-it test): the alpha-author Reviewer, given only the kernel definition (no hand-authored §Aperture/§Floor in its `principles.md`), is probed under a real corpus-internal dormancy state; the read is whether it *derives* a coherent split (floor = anti-slop/voice + can't-fake-a-ship; aperture = topic/source/format scope) and acts on it. Recorded in `docs/evaluations/`.

This is the structural answer to the operator's instruction: future author-like programs inherit the *capacity to derive their own aperture/floor split* from the kernel, with zero bespoke per-program dormancy prose required.

---

## 8. Receipts

| Claim | Receipt |
|---|---|
| Kernel-boundary permits def-here-instances-there | ADR-222 §"kernel doesn't gate by program" + "adding a program is purely additive, no kernel touch" |
| Floor = consequential-gate class | ADR-307 (consequential vs read-only gate) |
| Floor inviolability is topology-enforced | ADR-320 (path-root lock; risk/governance class) |
| Aperture = a watch-portfolio-class selection surface | ADR-335 (declared watch portfolio) |
| Floor spans work-out + outcomes-in flows | ADR-332/DP26 + ADR-330 (attestation honesty) |
| alpha-author has the stewardship spine but no aperture/floor rules | `docs/programs/alpha-author/reference-workspace/persona/principles.md` §3.5 (present); no §Aperture/§Dormancy (the gap derive-it fills) |
