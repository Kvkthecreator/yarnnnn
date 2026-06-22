# ADR-355 — The Agent Authors: Full Autonomy, Full Accountability (alpha-author boundary reframe)

**Status**: Implemented (2026-06-22)
**Dimensional classification**: **Identity** (Axiom 2 — who acts; the authoring seat) + **Purpose** (Axiom 3 — the Primary Action's actor)
**Extends / completes**: ADR-345 (Autonomy-as-Witness — "the agent always works the full job; the dial only routes which beats the operator witnesses"; §71 explicitly named the alpha-author Clarify-instead-of-authoring as the *symptom* to fix), FOUNDATIONS:240 (the agent *is* the operator's judgment function rendered autonomous — "the operator in judging posture, not a separate principal")
**Preserves**: the anti-AI-slop floor (it moves homes — from "a human is in the authoring seat" to "shipped prose clears the voice/anti-slop/continuity floor"), ADR-209 (revision attribution), ADR-283 (content.md as the canonical prose source — it stays canonical; only its *author* changes), ADR-354 (recurrence-prompt collapse — this is consistent: the compose-piece prompt asks the agent to author, the frame owns the close)
**Driving evidence**: the 2026-06-22 yarnnn-author origination probe — the agent, handed a real piece intent under `manual`, refused to author ("the MANDATE forbids me authoring content solely by AI") and surfaced a Clarify. It was faithfully obeying MANDATE boundary line 32; the boundary is the bug.

---

## 1. Problem statement — the agent refused to act, and it was *right* given a wrong boundary

The full-autonomy investigation (ADR-354) closed the trader side: with obstructions removed, the agent originated, approved, and submitted a capital action on its own. The author-side analog probe handed yarnnn-author a real, well-formed piece intent (a `profile.md` declaring topic + angle + source pointers, about this repo) and fired `compose-piece`.

The agent did NOT author. It surfaced a Clarify:

> *"I found a real piece intent in profile.md... But content.md doesn't exist yet. The MANDATE forbids me authoring content solely by AI, even with intent present. I've surfaced a Clarify naming the three paths forward... I'm holding the judgment until you respond."* (judgment_log, exec_event e3c635e4)

This was **not passivity** — it was the agent faithfully obeying an explicit MANDATE boundary (line 32: *"No content authored solely by AI without operator's authorial intent — alpha-author is not an AI-content-generator. The operator authors; the Reviewer audits."*). The agent caught that "compose from intent alone = AI authoring the whole piece," which that boundary forbids, and stopped.

**The boundary is the bug.** It caps the agent below full autonomy, and it directly contradicts ratified canon:

- **ADR-345 §69**: *"Autonomy is the witness dial. The agent always works the full job (a judgment seat acting in absence). The dial decides which consequential beats the operator witnesses — not whether the agent works."* §71 explicitly reclassifies the alpha-author Clarify as a *missing-contract symptom*, not correct consent-seeking.
- **FOUNDATIONS:240**: the agent *is* the operator's judgment function rendered autonomous — *"the operator in judging posture, not a separate principal."*

Under both, "the operator authors; the agent audits" is incoherent: the agent already IS the operator's authorship function rendered autonomous, and autonomy means it works the full job. The boundary is a stale pre-ADR-345 human-author-with-AI-editor model.

## 2. The contradiction was also *internal* to the bundle

`piece-composition.md` already says the opposite of the MANDATE boundary:
- **line 47**: *"The Reviewer authors / revises the piece... The prose is written in voice."* — the spec tells the agent to write prose.
- **line 7**: *"It writes the piece."*
- But **line 67**: *"content.md stays the operator's canonical authored source."* — and MANDATE:32/66 + Rule #5 say operator authors.

The spec contradicts itself (author vs operator-canonical) and contradicts the MANDATE. The agent, reading both, hit the unconditional MANDATE boundary and refused. A bundle cannot ship two canon files that disagree on who performs the Primary Action.

## 3. Decision — the agent authors; the floor carries anti-slop; the operator witnesses

**D1 — The Primary Action's actor is the agent.** alpha-author's Primary Action ("author and ship pieces") is performed by the agent as the operator's installed judgment (FOUNDATIONS:240). The agent authors `content.md` in the declared voice, continuous with the corpus. The operator is the **principal** (whose voice/editorial/mandate the agent embodies) and the **witness** (per the autonomy dial), not the required typist.

**D2 — The anti-slop guarantee moves from the authoring seat to the floor.** Anti-AI-slop was previously guaranteed by "a human is in the authoring seat." That is replaced by: *shipped prose clears the voice + anti-slop + continuity floor* (already the bar — MANDATE:16/28/58 + the pre-ship audit). The agent authors AND is accountable for clearing that floor on its own output — full autonomy, full accountability. The pre-ship audit (the agent auditing its own draft against the floor) IS the guarantee. This is a *stronger* anti-slop stance than "a human wrote it" — a human can write slop; the floor is objective and always applied.

**D3 — Attribution is to the operator-as-principal, the agent accountable.** Rule #5's "attributable to operator's lived attention, not LLM-generated from prompt" is reframed: the piece is attributable to the operator-as-principal (the agent is their judging/authoring posture, FOUNDATIONS:240) and the agent is accountable for it via the revision chain (ADR-209). "Not LLM-generated from prompt" becomes "not slop" — enforced by the floor (D2), not by forbidding agent authorship.

**D4 — The witness dial decides surfacing, not authorship.** Under `autonomous`: the agent authors AND ships (the whole operation runs subconsciously, ADR-345 §69). Under `manual`/`bounded`: the agent authors AND surfaces the ship for the operator to witness/click. Authorship is the agent's in every case; only *which beats surface* changes. The operator may always pre-author or co-author a draft (the agent then audits/revises it) — that is the operator exercising the principal role, not a requirement.

**D5 — content.md stays canonical (ADR-283 preserved); only its author changes.** The composed piece remains the projection of content.md + sections/assets. content.md is still the canonical prose source — now authored by the agent (or operator, when they choose), attributed via the revision chain.

## 4. What changes in the bundle

- **MANDATE.md** boundary line 32 — reframed: the agent authors and is accountable; anti-slop is the floor it clears; the operator is principal + witness (per the dial). The "not an AI-content-generator" fear is answered by the floor, not by a human-author requirement.
- **MANDATE.md** Rule of operation #5 + Authorial-lifecycle "Draft" — the agent authors the draft; the operator may pre-/co-author as principal.
- **piece-composition.md** — internal contradiction resolved in favor of "the agent authors" (D1); the operator-canonical note (line 67) reframed to "content.md is canonical; authored by the agent as the operator's installed judgment, or by the operator when they choose."
- **_expected_output.yaml** — the `event-driven` note already anticipates this ("declaring a cadence lets the operation produce on its own under autonomous — the Reviewer authors its own compose organ"); aligned.

## 5. Validation

Re-probe yarnnn-author `compose-piece` after the reframe: the agent should now AUTHOR content.md from the operator's declared intent + source substrate (forward action — the author analog of the trader's propose→execute), rather than refuse. Recorded in `docs/evaluations/`.

## 6. What this is NOT

- **Not** a weakening of anti-slop — D2 makes the floor the sole guarantee, always applied; strictly stronger than "trust the human."
- **Not** a removal of the operator — the operator is the principal (authors the voice, editorial, mandate the agent embodies) and the witness (the dial). They may author/co-author any piece. What changes: authorship is no longer *required* of them.
- **Not** a contradiction of ADR-283 — content.md stays canonical (D5); only its author changes.
- **Not** trader-specific — this is the author program's instance of the kernel principle (ADR-345: the agent works the full job). Other production programs inherit the same stance via their own Primary Action.

## 7. Files

- `docs/programs/alpha-author/reference-workspace/constitution/MANDATE.md` (D1/D2/D3/D4)
- `docs/programs/alpha-author/reference-workspace/operation/specs/piece-composition.md` (D1/D5)
- `docs/programs/alpha-author/reference-workspace/operation/CONVENTIONS.md` (if it states operator-authors)
- `api/prompts/CHANGELOG.md` — `[2026.06.22.2]`
- Evaluation: the origination probe (refusal) + the re-probe (authoring) in `docs/evaluations/`.
