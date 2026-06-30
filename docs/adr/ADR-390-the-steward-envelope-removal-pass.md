# ADR-390 — The steward envelope is the base case: a removal pass, not an addition

> **Status**: **Accepted + Implemented** (2026-06-30). Doc + code same session (gates: `test_perception_envelope.py` 36/36, `test_attribution_fact.py` 16/16, `test_reviewer_context_contract.py` 16/16, `test_adr276_reactive_envelope.py` 9/9). **Substrate/Identity dimension** — it REMOVES operation machinery from the steward's wake envelope and FOLDS the perception facts into one surface; it changes no substrate paths, no write gate, no schema, no primitive.
> **Date**: 2026-06-30
> **Authors**: KVK (operator) + Claude (collaborator)
> **Discourse base**: the operator's reassessment after [ADR-389](ADR-389-principal-vs-peripheral-and-the-steward-shaped-envelope.md) failed its validation wake — *"if you track prior refactoring on the reviewer agent's prompt envelope, you'll notice a lot of issues were resolved by REMOVING redundancies, complexities, and reaching for the most mutually-exclusive documentation, fundamental primitives, and strong ownership — that was the closest we got to the purest results on expected behavior and posture. Reassess based on these principles."*
> **Amends**: [ADR-389](ADR-389-principal-vs-peripheral-and-the-steward-shaped-envelope.md) — its *taxonomy* (principal vs peripheral) is RIGHT and survives; its *method* (add a principal-commons fact + a peripheral-field fact onto an already-63-section envelope) was the wrong axis. This ADR keeps the taxonomy, deletes the accretion: the three perception facts FOLD into one surface, and the capital-operation machinery is REMOVED from the steward base case.
> **Builds on**: [ADR-383](ADR-383-the-consistent-agent-framework-and-mandate-as-purpose.md) (the two-order model: the steward is the base case, judgment is program-activated — this ADR makes the ENVELOPE obey what the frame already said) + the persona-frame collapse arc ([ADR-302](ADR-302-persona-frame-collapse.md)/[ADR-306](ADR-306-persona-frame-minimal.md)/[ADR-323](ADR-323-cockpit-awareness-removal.md) — 36K→3.5K by removal; the discipline this ADR applies to the envelope) + the [ADR-299](ADR-299-operator-addressing-writes.md) email-canary finding (tool-list/section VOLUME is empirically corrosive to judgment — adding one tool collapsed output 74%).
> **Preserves**: DP19 (kernel presents, the agent's rules judge); the write gate; ADR-389's principal-vs-peripheral taxonomy; the program-active path (a program still gets its full machinery — only the BARE steward is stripped).
> **Dimensional classification** (Axiom 0): **Substrate** (Axiom 1 §8 — what the steward perceives) + **Identity** (Axiom 2 — envelope-by-agent-kind).

---

## 1. The reassessment (why ADR-389 was the wrong axis)

The attribution catch failed four wakes running. Each prior fix ADDED a perception signal (presence → salience → referent). None closed the catch. ADR-389 added two more facts. Under the discipline that actually purified this agent's prompt historically — **remove redundancy, reach for mutual-exclusivity + fundamental primitives + strong ownership** — that pattern is the smell, not the cure.

The receipts confirmed it. The steward's wake **user message** had grown to **63 section headers / 19 distinct facts**. On a bare steward workspace, **10 of 19 facts were empty** — yet most still rendered empty-state scaffolding (`## _schedule_index.md — (empty — kernel mirror hasn't run yet)`, `## _calibration.md — (empty…)`, reflection-gap, specs, expected-output). The persona-frame was collapsed 36K→3.5K precisely because section volume dilutes judgment; **the same discipline was never applied to the envelope.** The steward's actual job (tend the commons) was one voice among machinery built for a *different agent config* — the capital-judge Reviewer.

So the catch wasn't missing for lack of a signal. It was missing because **the steward's posture was diluted** — its attention spread across an operation's machinery it doesn't have. The "rule trigger" ADR-389 §5 named as the next lever is itself a symptom: a rule buried in 63 sections doesn't fire.

## 2. The decision

### D1 — The steward envelope is the BASE CASE; the program ADDS machinery

ADR-383 already says the steward is the base and judgment is program-activated. The envelope never obeyed it. **The single predicate**: `program_active = bool(program_decls)` — a workspace runs a program iff its active bundle declared wake-envelope substrate (`bundle_reader.get_substrate_abi_for_workspace`, the canonical connection-or-MANDATE-slug activation truth). No new concept: a bundle that ships ground-truth/risk/signals IS an operation; a bare steward ships none.

### D2 — Fold the three perception facts into ONE commons surface (mutual-exclusivity)

ADR-389's principal-commons + attribution + peripheral facts were three competing `## ` headers describing one concern: the steward's perception of the commons. They fold into **one** surface — `## The commons — who writes here, is it honest, is the perimeter sound` — in reading order: roster (the referent) → per-write attribution (the integrity detail) → perimeter health (peripherals). One header, one owner. Each part empty-graceful; the whole surface silent on a quiet single-owner bare workspace.

### D3 — REMOVE operation machinery from the steward base case

Six facts are capital-operation machinery: `reflection_gap_fact` (closed intent→outcome loop), `schedule_index_md` + `recent_execution_md` (pulse), `calibration_md` (cadence-vs-outcome), `expected_output_yaml` (output contract), `specs_inventory`. A bare steward has no operation: no cadence to calibrate, no ground-truth outcomes to reflect on, no specs, no owed output. These move OUT of the universal envelope set into the `program_active` branch — read in exactly ONE place, gated. The render layer's empty-state scaffolding headers (`(empty — kernel mirror hasn't run yet)`) are DELETED: empty now means "not this agent's concern," and renders nothing. A bare steward sees none of it.

### D4 — Strong ownership

Each operation-machinery fact is read in exactly one place (the program-active branch), not read-universally-then-discarded. The perception roster logic has one home (`services/principals.py`, ADR-389 D4, preserved). The commons render is one block.

## 3. The result (measured)

The bare-steward rendered message dropped from the accreted surface to **23 headers** — and the operation machinery is **entirely gone**: no schedule/recent-execution/calibration scaffolding, no specs, no expected-output, no reflection-gap. The three perception headers became one (`## The commons`). What remains is exactly the steward's job: persona · framework (its 5 rules) · precedent · mandate · budget · occupant · operating-context · standing-intent · **the commons** · the wake. (Most of the 23 are sub-headers *inside* the steward's own governance files — content, not envelope scaffolding.)

The program-active path is unchanged: a program still mounts its full machinery (the gate adds, it doesn't subtract from programs).

## 4. What this is NOT

- **Not a reversal of ADR-389's taxonomy.** Principal-vs-peripheral is right and load-bearing — it's *why* the commons folds in that order (roster as the referent). ADR-390 keeps the concept, deletes the accretion method.
- **Not removing perception.** The commons is always present (steward-base). What's removed is the *operation* machinery a bare steward shouldn't read.
- **Not a behavior change for programs.** A program workspace's envelope is the steward base + its declared machinery — same content as before, just no longer the universal default.

## 5. Validation

Re-fire the bare-steward wake against the CONCENTRATED envelope: does a steward whose attention is no longer diluted catch the seeded mis-attribution? This tests the reassessment's core claim — that the catch failed from dilution, not from a missing signal or an unsharpened rule. Logged as a dated FINDING. If it catches, the discipline (removal > addition) is validated and the rule-trigger lever is moot. If it still misses with a concentrated envelope, the gap is genuinely the rule wording (the ADR-389 §6 lever), now tested against a clean surface.

## 6. The principle (for the next envelope change)

The durable rule this ADR encodes, from the reviewer-prompt history: **when behavior is wrong, first ask what to REMOVE.** Reach for mutual-exclusivity (one concern, one surface, one owner), fundamental primitives (the steward reads an attributed filesystem; perception is one commons, not N facts), and the base-case/overlay split (the agent sees only what its mandate requires; a program adds). Adding signal to a diluted surface deepens the dilution. Any future envelope fact must justify itself against this — and prefer folding into an existing surface over a new header.
