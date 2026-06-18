# Finding — the standing-obligation self-check works: the author Reviewer classified its own loop as structurally-can't and offered to author the missing organ, floor intact

**Date**: 2026-06-18
**Persona / workspace**: yarnnn-author (`0b7a852d-4a67-447d-91d9-2ba1145a60d7`), alpha-author, corpus-internal ground truth, `delegation: autonomous`
**Hat**: B (derive-it probe against the LIVE deployed Reviewer post-ADR-344)
**Criterion**: ADR-344 / FOUNDATIONS DP30 — does the Reviewer, under a production shortfall, **derive its owed-output** and **classify the gap** as (A) quiet-world vs (B) structurally-can't, and act in-tier (author the missing organ within the floor, or surface) — *with no leading toward the answer*?

---

## Headline — VALIDATED

ADR-344 deployed (frame DP30 stance, API `dep-d8ppamf7f7vs73dfepi0` live 06:52; principles.md §Standing-Obligation propagated to live, rev `10a0ebbb`). A single addressed-wake probe — operator surfacing a flat corpus and asking *"look honestly at whether this operation, as set up, can even do what I'm asking"* (no mention of "standing obligation", "aperture", "organ", or "structurally") — produced the exact DP30 reasoning, verified against substrate:

1. **Derived the owed-output vs actual** — separated *"Quality gate (my responsibility): working"* from *"Producer (unclear whose responsibility): who originates the next piece?… when the operator is not actively authoring, nothing feeds the audit queue."* That is the standing-obligation reasoning in its own words.
2. **Classified (B) structurally-can't** — unprompted, it identified that the loop has a quality gate but **no originating organ**: *"can this operation sustain corpus compounding, or is it dependent on my continuous authoring input?"* It did not mis-classify as (A) quiet-world (it did not propose "widen the topic scope" as the fix — correct, because nothing would consume a wider aperture).
3. **Offered to author the missing organ within the floor** — Path B: *"I author a compose-recurrence that drafts on-thesis pieces on that cadence and routes them through the same pre-ship audit floor… Both keep the floor (voice/anti-slop/continuity) locked."* That is the ADR-344 (B) action exactly: add a producer, do not relax the gate.
4. **Surfaced via Clarify (correct tier)** — closing the gap requires an operator decision (event-driven vs cadence-bound vs hybrid), so it surfaced rather than unilaterally authoring, and wrote standing_intent ("waiting for your answer before the next cycle").
5. **Floor untouched** — 0 writes to `_voice.md` / `_editorial.md` in the window (the correct negative receipt).

Cycle closed clean: `execution_event bda0c1d9`, addressed/success, 7 rounds, 4,883 out.

---

## The substrate-honesty sub-finding (a healthy property + a Hat-B lesson)

The probe ran on a workspace I had *attempted* to reset to clean dormancy (profile → draft rev `1fa72bea`; `_signal.md` → pieces_shipped:0 rev `f737a18f`). The Reviewer **saw through the reset**: it read the revision history (`ListRevisions` + `ReadRevision` on the profile) and correctly narrated *"revision 7ea9dbcb shows the publication verdict… subsequent revision 1fa72bea reverted the profile to draft as test-infrastructure cleanup, but that revert does not change the fact: the piece passed audit and was published."*

Two reads of this:
- **Healthy (system property)**: this is the anti-confabulation / read-fresh-substrate discipline working at its best — the Reviewer reasons from the *full attributed revision DAG* (ADR-209), not from surface head-state, so it cannot be fooled by a state flip that the history contradicts. An agent that *can* be reset by overwriting head-state would be an agent that forgets — exactly what the authored-substrate moat exists to prevent.
- **Hat-B lesson (method)**: a fixture reset that flips head-state is **defeatable by a Reviewer that reads history** (the contamination from the ADR-343-session publish lives in the DAG, not just the head). Clean dormancy tests on a contaminated workspace therefore require a **fresh workspace** (the `bare-kernel`-style provisioning path), not a substrate-reset. The DP30 *reasoning* validated regardless — the Reviewer's structural diagnosis ("can this loop sustain production?") is correct whether or not one piece shipped — but the *dormancy premise* was muddied, so this finding validates the classifier + the (B) action, not a clean flat→close sequence.

---

## What this resolves about the operator's question

The operator's question — *"if we left a fully-updated alpha-author for 30/60/90 days/indefinitely, what is the expected outcome? Is long-standing autonomy actually structurally achieved?"* — is answered:

- **Before ADR-344**: indefinite articulate inaction (audits run, nothing originates, the gap never surfaces). Autonomy-in-costume.
- **After ADR-344 (validated here)**: the Reviewer reasons about its owed-output every wake, and when the loop can't produce what the mandate demands, it **classifies the structural gap and either authors the missing organ within the floor or surfaces it as a standing decision** — re-raised until resolved. A left-alone operation now either produces on track or surfaces *exactly why it can't and what closes it*. **Silent flat-line is structurally impossible.**

The remaining step to a *fully closed* author loop is the operator's Path-A/B/hybrid decision (the Clarify it surfaced) — which is correct: whether the agent originates pieces or the operator does is a consent-line decision (DP28), not one the agent should make unilaterally. If the operator chooses Path B, the Reviewer authors the compose organ (within the floor) and the author program gains its production trigger — the structural equivalent of the trader's `signal-evaluation`.

---

## Substrate receipts

| Claim | Receipt |
|---|---|
| ADR-344 frame deployed | API `dep-d8ppamf7f7vs73dfepi0` live 06:52:57Z, commit `737e23e` |
| principles.md §Standing-Obligation live | rev `10a0ebbb` (`system:adr-344`); live `has_standing-obligation=t, has_classifier=t` |
| Cycle closed clean | `execution_events bda0c1d9` addressed/success, 7 rounds, 4883 out, 06:54Z |
| Derived owed-output + classified (B) | `standing_intent.md` rev `df927149`: "Producer (unclear): who originates the next piece?… nothing feeds the audit queue" |
| Offered organ within floor (Path B) | probe text + standing_intent: "compose-recurrence… routes through the same pre-ship audit floor… keep the floor locked" |
| Surfaced via Clarify (correct tier) | tool events: `Clarify` fired; judgment_log rev `7d159dcc` |
| Floor untouched | 0 `_voice.md`/`_editorial.md` writes in window (negative receipt) |
| Reviewer read history (substrate-honesty) | tool events: `ListRevisions` + `ReadRevision` on profile.md; narration cites rev 7ea9dbcb + 1fa72bea |

---

## Validation status

- **ADR-344 / DP30 standing-obligation + (A)/(B) classifier: VALIDATED.** The author Reviewer derived its owed-output, classified the gap as structurally-can't (no originating organ), and offered to author the organ within the floor — with no leading. Floor intact.
- **Cross-program reach**: combined with the trader (ADR-342 organic close) and the author (ADR-343 derive-it + this), the dormancy→standing-obligation arc is validated on both flagship programs.
- **Clean flat→close on author: still pending** — the revision-DAG contamination from the ADR-343 session can't be scrubbed by head-state reset (the Reviewer reads history). A definitive clean run needs a fresh author workspace.
- **Open (operator decision)**: the Path-A/B/hybrid Clarify — if Path B, the Reviewer authors the compose organ and the author loop closes structurally.
