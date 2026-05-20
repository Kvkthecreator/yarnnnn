# ADR-296: Wake Is Event-Driven and Evaluation-Gated — The Reviewer Fires When the Moment Warrants Judgment

> **Status**: Proposed (v2 — pure thesis, distilled from v1 + audit + alignment discourse 2026-05-20)
> **Date**: 2026-05-20
> **Authors**: KVK, Claude
> **Scope**: System canon — the architectural shape of how the Reviewer is invoked, by whom, against what. Pure thesis. Implementation, migration, and ADR-relationship sections deferred to post-ratification work.

> **Note on this ADR's form.** This is a **pure thesis ADR**. It states the target shape of wake, recurrences, hooks, and Reviewer invocation derived from first principles + the human-autonomy analogy + the runtime audit at [`adr296-canon-and-runtime-audit.md`](../architecture/adr296-canon-and-runtime-audit.md). It deliberately does **not** declare what existing canon (FOUNDATIONS axioms, prior ADRs, current runtime) it supersedes, amends, preserves, or contradicts. Those declarations require a separate cross-canon-edit work product after thesis ratification. Until then, the thesis stands alone for reasoning against.

> **What changed from v1 → v2.** v1 framed the thesis around "the Reviewer is a continuous self-pacing judgment cycle." The audit + alignment discourse surfaced that this was reaching for the right intuition (continuous-feeling autonomy) via the wrong mechanism (continuously-running cycle). v2 reframes around **wake** as the irreducible architectural unit, **evaluation** as the gate, and **the Reviewer as event-fired, not continuously-running**. The seven-thesis form collapses to three load-bearing decisions + an explicit diagram. The autonomy property the operator wants (Reviewer originates external-world writes on its own cadence, against real worldview, under operator-absent conditions) is preserved without committing to a daemon-process runtime shape.

---

## Context

The autonomy demonstrations on `kvk` (alpha-trader + alpha-author personas) are testing whether the system closes the loop end-to-end on real external-world writes under operator-absent conditions. As of 2026-05-20 T0 baseline, the loop does not close cleanly. Bundle authors keep reaching for inert recurrence shapes that require an upstream prompt-declared caller to ever fire. The Reviewer's principles documents carry patches that compensate for kernel-scheduling latency. The primitive surface canonized for "fire this unit of work" has thirteen prose mentions across bundles and Reviewer prompts but only two production fires in the system's history. The four-trigger taxonomy has been amended five times and still does not cleanly express what the autonomy loop needs.

The diagnosis these incremental amendments keep producing is "tighten the trigger envelope" or "fix the bundle prompt." Both miss the underlying shape.

The underlying shape is this: every ADR in the lineage frames the Reviewer as a **trigger-responsive** entity — invoked by an external event, runs one session, terminates back to latent. The autonomy demos are testing whether a trigger-responsive entity produces continuously-autonomous behavior. That test conflates two different things — the *property* the operator wants (autonomy: Reviewer originates external writes on its own clock against real worldview under operator-absent conditions) and the *mechanism* used to achieve it (continuously-running cycle vs event-fired with cheap evaluation).

The human-autonomy analogy reveals: a human is not a continuously-running daemon. A human is a being whose conscious attention fires in response to events (internal or external) and decides whether each event warrants action. Most events don't (you don't act on every breath you take or every cloud you see); some do. The "continuous feel" of conscious autonomy comes from the firing being frequent and cheap, not from the consciousness being a non-terminating process.

This ADR commits the same shape for the Reviewer.

---

## The thesis

### T1 — Wake is the irreducible architectural unit. The Reviewer is event-fired, not continuously-running.

The most basic feature of the system's autonomy, stripped of all mechanism, is:

> **Something changed in the world or worldview. Under the operator's standing intent, this change warrants a moment of judgment. The moment happens now.**

That's the irreducible shape of a **wake**. Every wake source in the system is a specific implementation of "something changed, judgment is warranted, now":

- Clock tick at 7am = *time* changed in a way that warrants judgment per operator-authored cadence.
- Operator chat message = *operator's expressed intent* changed; they want attention now.
- Proposal arrival = *substrate state* changed; a proposal now exists that needs judgment.
- Substrate write at a watched path = *worldview state* changed in a way the operator/Reviewer declared interest in.
- Platform event = the *external world* changed.
- Manual fire = operator explicitly asserts a wake is warranted.

The Reviewer is **the judgment seat that fires when a wake passes evaluation**. It is not a continuously-running cycle; it is event-fired. What makes the system *feel* continuously autonomous is that wakes are frequent and the evaluation that gates them is cheap. The Reviewer fires when a moment warrants judgment, and the moments are evaluated frequently enough that operator-absent autonomy is real.

### T2 — Many wake sources contribute signals to one evaluation gate.

There is **one wake-evaluation mechanism**. Many wake sources contribute signals to it. The mechanism is a three-tier funnel:

- **Tier 1 (deterministic, zero LLM cost)** — given the wake-event signal + operator's standing intent + Reviewer's prior-cycle hints + budget state, does this event warrant Tier 2 attention? Most don't (a 5-minute clock tick on a quiet workspace doesn't, a back-office cron tick doesn't). Some do. Decision: `skip | tier-2 | escalate-to-full-cycle`.
- **Tier 2 (cheap idle-tick judgment)** — when Tier 1 says ambiguous, fire a minimal-envelope cheap LLM call that asks "given what I know, does this moment warrant the Reviewer's full attention?" Decision: `wait | observe | escalate`.
- **Full cycle** — the current Reviewer real-time loop. Worldview-read, judgment, action (worldview-write, back-edge action via ProposeAction, cadence-author for next interest), terminus.

Wake sources propose wakes; the funnel decides which propagate to the Reviewer's full attention. The Reviewer reads worldview and judges; it does not reason about *which wake source proposed this wake*.

This is the pattern the system had in ADR-126 (Agent Pulse — Autonomous Awareness Engine), applied at the wrong layer (per-agent pulse) and dissolved when the work unit changed. v2 reapplies it at the correct layer (Reviewer-wake) where the work unit lives now.

### T3 — Recurrences are one wake source's configuration. Not the essence of wake.

Today's recurrence shape — `{slug, schedule, mode, prompt}` — looks like the architectural essence because it is the only declarative wake-shape the operator/Reviewer can author. That is accident, not design.

Recurrences are the configuration that **the cron-tick wake source** reads to know what time-passages warrant evaluation. Other wake sources (operator chat, proposal arrival, substrate change, platform event, manual fire) do not consult recurrences — they propose wakes through their own paths.

Reframed:

- **Wake source = cron-tick** reads recurrences to know "what time-events warrant proposing a wake."
- **Wake source = substrate-event** reads operator/Reviewer-authored event-interest declarations (hooks) to know "what substrate transitions warrant proposing a wake."
- **Wake source = operator-addressed** unconditionally proposes a wake (operator presence is itself a wake-warrant).
- **Wake source = proposal-arrival** unconditionally proposes a wake (proposal creation is itself a wake-warrant; today's `on_proposal_created` handler).
- **Wake source = manual fire** unconditionally proposes a wake (operator explicit assertion).

A **hook** is the substrate-event-driven generalization of "what warrants wake." Recurrences are the time-driven sub-case. Both compose into the evaluation gate (T2) identically.

The mental model "recurrences = work units" dissolves cleanly. Recurrences are *cadence declarations* the cron-tick wake source consults. The Reviewer doesn't own them; the operator does (with Reviewer authority to author cadence on its own behalf per ADR-274 / ADR-275 standing canon).

### Diagram — The whole shape

```
Wake sources                Wake evaluation              Reviewer
(many)                      (funnel: T1 + T2)            (one)
─────────                   ──────────────────           ────────
clock tick     ─┐                                        ┌─→ full cycle
operator chat   │                                        │   (worldview-read,
proposal land   ├──→  T1 zero-LLM check  ──→  pass  ────┤    judgment, act,
substrate write │     T2 cheap Haiku check  →  escalate  │    schedule next)
platform event  │                                        │
manual fire    ─┘     ──→  skip (most cases)             │
                                                          │
operator-authored      Reviewer-authored
mandate + cadence      standing intent + next-wake hint
prefs + AUTONOMY       (shapes T1+T2 evaluation)
(shapes T1+T2 evaluation)
```

The diagram is canonical. Every implementation question downstream of ratification (where does Tier 1 live? what schema does hooks read? what does standing_intent.md's frontmatter contain?) resolves against this shape.

---

## What this thesis commits — three load-bearing decisions

The seven thesis claims from v1 collapse into three load-bearing decisions. Everything else is implementation detail.

### D1 — Wake is event-driven and evaluation-gated. One mechanism, many sources.

Wake is the irreducible unit. Multiple wake sources contribute signals; one evaluation gate (Tier 1 deterministic + Tier 2 cheap LLM) decides which proposals reach the Reviewer's full cycle. The Reviewer does not reason about wake-source taxonomy at its prompt-facing layer — it reads worldview at full-cycle entry.

This commits:
- Wake sources are plumbing-internal; the Reviewer-facing surface is "the worldview at the moment of judgment."
- The evaluation funnel is the *singular mechanism* across all wake sources. No per-source dispatch bypasses evaluation.
- Operator-addressed wakes pass evaluation by default (operator presence is itself a wake-warrant); the funnel acknowledges this without bypassing the structure.

### D2 — Recurrences are the cron-tick wake source's configuration. Hooks are the substrate-event wake source's configuration. Both are equal in shape.

Recurrences and hooks are sibling declarative shapes for two wake sources. They compose into the evaluation gate identically. The kernel reads both at every scheduler tick + substrate-write transition.

This commits:
- "Schedule" remains the kernel-level vocabulary for time-driven wake configuration.
- A new sibling declarative shape (operator or Reviewer-authored "watch for substrate-event X") becomes the canonical mechanism for substrate-event-driven wake. Bundle-author confusion about `schedule: null` recurrences resolves cleanly.
- Both shapes are operator-authorable (via chat → YARNNN) and Reviewer-authorable (mid-loop, per ADR-274 cadence authority).

### D3 — The Reviewer's authority is over cadence preference + standing intent. Not over invoking itself.

The Reviewer authors its own cadence preferences (per ADR-274 already canonical). It authors `standing_intent.md` at every cycle terminus (per ADR-284 already canonical). These two artifacts together shape **what kinds of wake the funnel allows through** — not by direct invocation, but by declaring "here are the wake-warrants I care about next."

The Reviewer does not have a primitive for "invoke yourself" or "invoke another Reviewer cycle on this slug." The system's wake sources + evaluation gate fire the Reviewer when their criteria match. The Reviewer's response to stale upstream substrate is to author cadence (Schedule the next mechanical mirror) or to write standing intent ("if X transitions, I want to be woken"). Not to dispatch its own next wake by name.

This commits:
- FireInvocation remains in `CHAT_PRIMITIVES` (operator-via-chat needs a slug-resolution wake-proposal shim — operator presence + explicit assertion warrants wake).
- FireInvocation leaves `REVIEWER_PRIMITIVES`. The Reviewer's authority surfaces are Schedule + WriteFile to standing intent + ProposeAction + worldview-writes. Not self-invocation.
- Cycle-terminus contract: the Reviewer's last act before `ReturnVerdict` is updating standing_intent.md (already canonized in ADR-284). The structural commitment ADR-296 v2 adds is that *this update is what shapes future wake evaluation*, not just an audit trail.

---

## The three operational constraints the thesis must satisfy

The thesis is real only if the system can satisfy three observable properties. Each is testable through the existing autonomy-demo framework.

### C1 — Evaluation cost is tractable

The funnel must be cheap enough to run at high frequency. Tier 1 is zero-LLM by construction. Tier 2 is a Haiku call with minimal envelope — measurable; expected to be sub-cent. If Tier 2 costs swamp full-cycle costs at scale, the thesis has a calibration gap addressable at bundle/preferences layer.

### C2 — Worldview-read remains complete and fast at full-cycle entry

When the funnel escalates to full cycle, the existing envelope assembly (per `reviewer_envelope.py`) carries everything the Reviewer needs. This is already aligned per the audit; T2 escalation does not change envelope shape, only frequency of fire.

### C3 — The Reviewer originates action when criteria are met

The largest risk under any wake-evaluation frame is that the Reviewer reads worldview, decides "nothing warrants action right now," over and over, and never originates external-world writes. Cure is twofold: (a) operator standing intent must be concretely actionable in bundle principles + mandate; (b) Reviewer must be calibrated to act when its own criteria match, not defer reflexively. The autonomy-demo framework measures (a) and (b) through observed `ProposeAction` rates and observed external-world write outcomes.

---

## What the thesis preserves

Without committing canon-relationship sections, the thesis explicitly **does not displace**:

- Substrate as the runtime bus (FOUNDATIONS Axiom 1 + ADR-209 Authored Substrate).
- Identity layers — Reviewer as persona-bearing judgment seat per FOUNDATIONS Axiom 2.
- Operator-authored governance (mandate, principles, AUTONOMY, cadence preferences) as the shaping surface for the funnel.
- ProposeAction as the back-edge primitive (ADR-193) for external-world effect.
- Mechanical mirrors as worldview maintainers running on declared schedules.
- The Reviewer's full-cycle real-time tool-use loop shape — including DispatchSpecialist for sub-judgment inline calls.
- The autonomy-demo + observation-discipline framework (ADR-294 + ADR-295).
- The lock-set as current dev-trust state, orthogonal to wake architecture.

The thesis reorganizes the wake / recurrence / FireInvocation layer. It does not touch the substrate, governance, or back-edge layers.

---

## What this ADR does not yet say

Deferred to post-ratification work:

1. Which existing FOUNDATIONS axioms, ADRs, primitives, or runtime mechanisms this thesis supersedes, amends, or preserves explicitly.
2. The schema of the substrate-event hook declaration (file path, field name, watch-criteria syntax). Likely lives in `standing_intent.md` frontmatter for Reviewer-authored hooks + operator-authored cadence prefs for operator-authored hooks; specifics deferred.
3. Implementation mechanism for Tier 1 / Tier 2 in code (where in dispatch path does Tier 1 sit? does Tier 2 run as part of `invoke_reviewer` with an early-exit, or as a separate cheap call upstream of `invoke_reviewer`?).
4. Migration plan for the alpha-trader and alpha-author bundles — both currently use prompt-driven chain patterns + `schedule: null` reactive recurrences that reshape under D2.
5. The specific kernel mechanism that translates substrate-event-writes into wake-proposals at scheduler-tick time (revision-chain query? change-detection helper? pure scheduler-tick scan?).
6. Cycle-terminus contract: does the Reviewer's `ReturnVerdict` enforce a minimum standing_intent.md write? Soft default vs hard contract.
7. Backwards compatibility — none, per Singular Implementation discipline; but specific deletion order matters for safe deploy.
8. Per-program back-edge action coverage canonization (alpha-author publish-action surface today is not covered; affects what the autonomy demo can test on that persona).

Each of these requires either implementation choices grounded in runtime experiments, or follow-on ADRs that decompose specific layers.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-05-20 | v1 — Initial pure thesis. Seven thesis claims (T1–T7) anchored on "continuous self-pacing judgment cycle." |
| 2026-05-20 | v2 — Reframed around wake as the irreducible unit, evaluation as the gate, Reviewer as event-fired. Seven claims collapse to three load-bearing decisions (D1 wake + funnel; D2 recurrences + hooks as sibling configs; D3 Reviewer authors cadence + intent but not self-invocation). Canonical diagram added. FireInvocation asymmetric resolution (chat keeps, Reviewer drops) named as part of D3. Continuous-cycle mechanism dissolves; continuous-feeling autonomy preserved via cheap frequent evaluation. |
