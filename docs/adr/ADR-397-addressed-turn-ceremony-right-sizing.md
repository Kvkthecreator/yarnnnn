# ADR-397: Addressed-Turn Ceremony Right-Sizing — the Wake Liturgy is Reactive-Scoped

**Status**: Implemented (2026-07-02)
**Date**: 2026-07-02
**Deciders**: KVK + Claude
**Plan context**: Rung 2 of [the Freddie envelope refactor plan](../analysis/freddie-envelope-refactor-plan-2026-07-02.md)
**Amends**: ADR-318 (agentic wake posture — the *obligation prose* becomes reactive-scoped; the posture itself is unchanged), ADR-306/ADR-383 (persona-frame contents — two paragraphs relocate out of the cached frame)
**Preserves**: ADR-360 (the honest close terminal — ReturnVerdict stays the uniform close on EVERY trigger), ADR-344/DP30 (the standing obligation — checked at wakes, exactly as before), ADR-291 (telemetry accounting unchanged), agent-composition.md §3.2.1 (no rules-of-judgment enter the kernel)

## Context

The Rung-0 baseline (`docs/evaluations/2026-07-02-freddie-envelope-baseline/`) measured the addressed path: on 5 read-shaped operator asks, 3 closed with liturgy writes (standing_intent / judgment_log / notes) the ask did not need, at a mean of 11.2 tool calls per turn. The cached persona frame instructs — on **every** trigger — the full wake liturgy: "a wake is a situation, not a task" forward-reasoning, the standing_intent carry-forward, the reflection-write prompt, and the verdict-taxonomy pedagogy. That liturgy is what makes **unattended** autonomy work (ADR-318/344): a reactive wake has no operator present, so the agent must tend its forward state and leave a verdict-of-record.

An **addressed** turn is structurally different: the operator is present and witnessing. The standing loop is being driven by the human in the room; prompting the agent to also perform the unattended-cycle ceremony on every chat turn produces the measured ceremony tax — extra writes, extra narration lines, slower turns — without adding to the audit trail the operator is *currently reading*.

## Decision

**D1 — ReturnVerdict stays the uniform close on every trigger.** One close contract across rungs (ADR-381), one honest terminal (ADR-360), unchanged telemetry. This ADR moves *prose*, not the close contract. (The alternative — a prose-close for addressed turns — is explicitly deferred; it touches the stream/accounting layer and is only worth its blast radius if this change proves insufficient.)

**D2 — The wake liturgy moves from the cached persona frame to the `reactive` trigger framing.** Two frame paragraphs relocate, compressed: (a) "a wake is a situation, not a task" (forward-reasoning obligation, standing_intent carry-forward), (b) "close every cycle with a verdict" (verdict taxonomy, reflection-write prompt, the fault semantics of a silent exit). Reactive wakes — the unattended cycles — receive them exactly as before. The frame keeps everything universal: principal-shift, action-grammar, anti-confabulation, fresh-substrate rule, narration register, citation discipline.

**D3 — The addressed framing keeps a one-line close** ("Close the turn with ReturnVerdict; its reasoning is your report") and gains nothing else. Forward-tending on an addressed turn remains *available* (the tools are unchanged; principles.md may still direct it) — it is no longer *prompted on every turn*. The obligation to check owed-output (DP30) is a wake-time obligation and continues to fire on wakes.

**D4 — Ceiling accounting** (the Rung-1 ratchet, `test_adr383_trigger_framing_recarved.py`): the reactive ceiling rises 1,600 → 2,600 chars to receive the relocated liturgy; the addressed ceiling is unchanged; the frame ceiling drops 9,000 → 7,600 (the frame shrinks by ~1.6k chars). Net tokens: addressed turns drop by the full liturgy size; reactive wakes are flat (same content, different carrier).

## Consequences

- Addressed turns stop performing unattended-cycle ceremony for a present operator; the measured liturgy-write rate on read-shaped asks is the validation metric (`docs/evaluations/2026-07-02-freddie-envelope-rung2/`).
- The frame's cached prefix shrinks — every trigger's prompt gets smaller; the reactive envelope carries the same total as before.
- The seat's unattended discipline (verdict-of-record, standing intent, reflection) is untouched where it matters — on wakes.
