# Re-founding: a wake is a pre-authored ask — the CC-analogous spine for full autonomy

**Date**: 2026-06-24
**Hat**: B → A (Hat-B reasoning that recommends a Hat-A re-founding; the ADR it feeds is system canon)
**Status**: Conviction document — pre-ratification. The spine claim is **receipt-backed** (`2026-06-24-spine-present-tense-ask-VALIDATION.md`); the blast-radius mapping is the next step, deliberately deferred.
**Operator thesis on record (2026-06-24)**: *"Using the Claude Code benchmark, we have a straightforward model of our fully autonomous, file-system-native, attributed substrate. A near-clean-slate rewrite is potentially valid because once we have the right analogous reframing of prompt and behavior, the implementation collapses toward what CC achieves elegantly for millions of use cases — axiomatic and agnostic in nature."*
**Builds on**: the CC source audit (`docs/analysis/src_claudeCC/` — `context.ts`, `constants/prompts.ts`, `query.ts`), the 6-probe falsification arc (the-occasion-of-work + judgment-execution-unification + 5 FALSIFICATIONs + the spine VALIDATION), ADR-318 (a wake is a situation not a task), ADR-327 (budget collapses pace), ESSENCE/THESIS (the moat).

---

## 0. The one-paragraph thesis

Claude Code achieves axiomatic, agnostic, fully-autonomous agent behavior for millions of use cases with a strikingly compact envelope: **three context items** (`gitStatus` snapshot, `CLAUDE.md`, date) + a **static cached behavioral prompt** + a **loop that stops on silence**. YARNNN's *substrate* is already the CC-analogue done right — file-system-native, authored, attributed, portable (ADR-209). The failure to lock in autonomous posture is **not in the substrate**; it is that YARNNN's *wake envelope grew prosthetics to simulate the one thing CC gets for free: a present, asking principal at every turn.* The re-founding: **a YARNNN wake is a user message the operator pre-authored and the world delivers on their behalf.** The substrate's job is to make the obligation *arrive as a present-tense ask* — an event with a live imperative — not as standing state the agent must classify itself into caring about. Once the wake is ask-shaped, the CC analogy is exact, the prosthetics collapse, and the implementation lands where CC's does: compact, axiomatic, agnostic.

---

## 1. The benchmark — what CC actually is (from the source, not from memory)

`docs/analysis/src_claudeCC/` is the extracted CC implementation. Three structural facts, receipt-grounded:

1. **The per-conversation context envelope is three things** (`context.ts:155-189` `getUserContext` + `getSystemContext`): `claudeMd`, `currentDate`, and a `gitStatus` snapshot explicitly stamped *"this status is a snapshot in time, and will not update during the conversation."* That is the **entire** standing context. Everything else the agent needs, it reads on demand via tools.

2. **The system prompt is static and cached** (`constants/prompts.ts:560-576`): intro, system, doing-tasks, **actions**, using-tools, tone, output-efficiency — then a `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` marker, then a handful of memoized-per-session dynamic sections. The behavioral posture is fixed and tiny; the agent's *situation* is the conversation, not a pre-computed block.

3. **The loop terminates on silence** (`query.ts:307` `while(true)`; ends when the assistant emits no `tool_use`). There is **no terminal-move contract** ("close with a verdict"), **no recovery synthesizer** that fabricates a default action when the agent goes quiet. "Nothing to do" is silence — costless, needs no machinery.

4. **The whole autonomy story is one paragraph** (`getActionsSection`, `prompts.ts:255-267`): *carefully consider reversibility and blast radius; freely take local reversible actions; for hard-to-reverse / shared-state / risky actions, confirm first unless durably authorized; authorization stands for the scope specified, not beyond.* That single paragraph is YARNNN's AUTONOMY.md + ADR-307 gate + ADR-352 ask-vs-act + witness dial.

**Why CC is axiomatic**: the compactness is *causal*, not aesthetic. The agent infers "what to do" from a **live present-tense ask** (the user message) against a **world that answers back** (tool results), and stops when done. No `mode`, no wake-taxonomy, no obligation-tracking, no "what kind of turn is this." One posture, N situations, judgment maps situation → action.

---

## 2. The asymmetry you cannot copy — the absent principal

There is exactly one place the CC analogy breaks, and every probe this arc crashed into it:

**CC's principal is present at every turn. YARNNN's principal is absent by design.**

CC never solves "what should I do when no one asked me anything," because in CC *someone always just asked*. The user message is the obligation, present-tense, every turn. CC's "stop on silence" is correct because silence means *the human is satisfied*. The human is the clock, the trigger, the obligation, and the are-we-done judge, all at once.

YARNNN's reason to exist is to **run in the operator's absence** (ADR-296 wake architecture). Strip that and you have rebuilt Claude Code. So the wake *cannot* carry a live request — and that is the product, not a defect. Which has two consequences that forbid naive copying:

- **CC's "stop on silence" is catastrophic for YARNNN.** In CC, quiet = satisfied. In YARNNN, quiet = the agent did nothing and no one was watching. The 6-probe arc is exactly this: the author treated the wake as a status check and went quiet; CC-style "quiet = done" would ratify the never-composes failure as success. The recovery synthesizer YARNNN built (clumsily) exists to make absence-of-action *visible* — a real need CC doesn't have.
- **The obligation must be reconstituted.** CC reads the obligation off the user message; YARNNN, with no message, must derive it from standing substrate (`_expected_output.yaml` → DP30 derivation → ADR-359 `_compute_occasion_fact`). Each layer is correct and each is *load carried because the wake has no live principal in it.*

So the re-founding is **not** "copy CC's envelope." It is: **what is the minimal substitute for the always-present principal?** — and the answer the evidence forces is *make the obligation arrive as a present-tense ask, shaped like the user turn CC relies on.*

---

## 3. The spine, proven (the receipt)

`2026-06-24-spine-present-tense-ask-VALIDATION.md`. Single variable against five stable FAILs: identical netflix-author substrate (funded, autonomous, weekly scene, **empty corpus, 0 content.md**), identical edited code. The only change — deliver the obligation as a **present-tense operator-authored ask** through the **addressed** path (`user_message`, the CC user-turn analogue: *"Compose this week's scene now... writing the prose IS the work of this wake"*) instead of the situation-forward framing every prior probe used.

**Result: it composed.** 1,973 chars of in-voice screenplay prose to `ep-01-the-office/content.md`, `reviewer:ai:reviewer-sonnet-v8`, in-cycle, verdict=approve, 7 rounds — and the ADR-359 occasion-nudge **never fired** (instrumented), so the **bare ask carried it**, not the machinery. The agent's standing_intent recorded `## What I did this cycle` (completion), against five prior `Action this cycle: none` (deferral). First production in the entire arc.

**What it proves**: the blocker was never the frame, the prompt content, the recurrence-type, or the occupant (each falsified in turn). It was the **obligation's event-shape at the wake**. Standing-state-to-classify → defers. Present-tense-ask-the-wake-is-about → produces. Same agent, same code, same empty corpus. The operator's absent-principal thesis is validated on its core claim.

**What it does NOT prove** (honest bound, and the design work §5 owes): this was an *addressed* wake — the probe typed the ask. In the operator's *absence*, **what fires the present-tense ask?** The trader's answer is the market (a signal arriving IS a present-tense ask). The author has nothing firing one. That gap is the whole of the remaining design.

---

## 4. What collapses once the wake is ask-shaped

If the wake carries a live ask, the prosthetics that simulate a present principal are no longer load-bearing and shrink toward CC's compactness:

| YARNNN prosthetic | Why it exists today | Under the ask-shaped wake |
|---|---|---|
| ~20-section pre-framed envelope | reconstruct the principal's context | → CLAUDE.md-analogue (MANDATE + principles + AUTONOMY, static/cached) + **the ask** + tool-readable substrate (read on demand, CC-style — not pre-dumped) |
| verdict enum (`stand_down`/`non_performance`/…) | a terminal-move contract the loop requires | → the agent acts on the ask and stops; "nothing warranted" is a legitimate *reply to a specific ask* ("the signal fired but EV is negative"), not a free-floating default |
| recovery synthesizer (fabricates `stand_down` on silence) | make absent-action visible | → an unanswered ask is a visible non-completion *of that ask*; no fabrication needed |
| recurrence-types / wake-taxonomy (`mode`, named judgment slugs) | label what kind of wake this is | → there is no "kind of wake," only "an ask arrived" (the original task-label instinct — right destination; the falsification showed slug-removal alone is insufficient; it becomes sufficient *once the ask is event-shaped*) |
| occasion-header among twenty (ADR-359 D1) | inject the missing ask as computed prose | → the ask **is** the message, not a header decorating a maintenance heartbeat |
| persona-frame cycle-close contract | tell the agent how to terminate | → CC-style: stop when the ask is answered |

The autonomy story stays exactly CC's: `getActionsSection`-analogue (reversibility + blast radius + the witness dial), one paragraph, static. The **substrate floor is untouched** — ADR-209 authored/attributed/portable files + primitives-as-tools is *already* the CC-analogue (CC's filesystem + tools). The rewrite is **envelope-and-loop clean-slate over an intact substrate floor**, not literal clean-slate.

---

## 5. The audit the operator asked for — does budget / cadence / pace accommodate the spine?

The operator's explicit gate: *ensure the existing approach is the correct substrate for the spine — meaning, if budget/cadence accommodates the pace.* Audited against current code (not stale CLAUDE.md):

### 5a. Budget — ALREADY spine-aligned (ADR-327 did the conceptual move)

`services/budget.py` (ADR-327): `_budget.yaml` is a **dollar envelope over a window** (`amount_usd` / `window`), nothing more. The pivotal line in its own docstring: *"`_pace.yaml` (frequency cap) — DELETED. 'How often' is the Reviewer's allocation problem within the budget, not an operator dial."* (`services/pace.py` is **deleted**; CLAUDE.md's pace section is stale.) This is **exactly** the spine's shape: the operator declares *how much attention is affordable* (the budget); the agent allocates *when to spend it* (the cadence). Budget gates at the funnel (`wake.py:441-450`: window-to-date spend ≥ amount → skip cron wakes, reactive warns-but-fires). **No conflict with the spine — budget is the cost ceiling under which asks fire; it does not itself classify or frame the wake.** It survives the re-founding intact.

### 5b. Cadence — the SEAM, and it is exactly the spine's diagnosis

`_recurrences.yaml` cadence is where the tension lives. The author bundle ships **cron-scheduled judgment recurrences**: `corpus-coherence-check` (Mon+Thu 12:00), `revision-audit` (Fri 22:00), `outcome-reconciliation` (daily 05:00), `reddit-publish` (Tue 15:00) — each a *named recurrence with a fixed cron + a situation-framing prompt* (`mode: judgment`). **A cron firing a judgment recurrence manufactures a WAKE but not an ASK.** The cron says *when*; the prompt is standing-state framing ("assess the operation against its mandate"), not a present-tense imperative. That is precisely the FAIL shape the 6 probes isolated — the system produces a wake the agent then has to *classify itself into caring about*, and it classifies it as maintenance. So:

- **Mechanical recurrences (`track-*`, `mode: mechanical`)** — zero-LLM deterministic intake (ADR-335 perception field). These are NOT wakes-for-the-judgment-agent and carry no spine tension. **Survive verbatim.**
- **Reactive recurrences (`schedule: null` + substrate-event hooks)** — fire on a substrate transition (a draft hits `ready_for_review`). These ARE ask-shaped by construction: the event *is* the present-tense ask ("this draft is ready — audit it"). **Spine-aligned; survive.**
- **Cron-scheduled judgment recurrences** — the seam. A clock is the *wrong* originator of a present-tense ask for *owed-output* work, because the clock fires regardless of whether the world changed, so the prompt can only frame standing state. This is why the author defers and the trader (whose ask is fired by the *market*, a real event) does not.

### 5c. The audit verdict

**Budget is the correct substrate and survives. Cadence is half-right and half-seam.** The half that fires asks from *events* (mechanical intake feeding reactive hooks; the market; a ready draft) is spine-correct. The half that fires *judgment recurrences from a bare clock* is the residual prosthetic — a wake-without-an-ask, the thing the re-founding must reshape. The spine's design work (§6) is precisely: **convert clock-fired judgment recurrences into ask-fired wakes** — either an event manufactures the ask (perception field, ground-truth arrival, ready draft), or, for genuinely time-driven owed-output (the author's weekly scene), the *cadence fires an ASK* ("compose this week's scene now") rather than a *situation-framing prompt* ("assess the operation"). The validation proved the former composes; the cadence layer must deliver the latter shape.

**Conclusion**: the existing budget/cadence substrate is the *right* substrate for the spine — ADR-327 already collapsed pace into agent-allocated cadence-under-budget, which is the spine's exact economic shape. The one change cadence needs is not structural replacement but **re-shaping the judgment-recurrence prompt from standing-state framing into a present-tense ask** (and, where possible, firing it from an event rather than a bare clock). That is a smaller change than the prosthetics it lets us delete.

---

## 6. The open design edge (what the re-founding ADR owes, NOT decided here)

The spine is proven; the autonomy edge is open. The ADR must answer:

1. **What fires the present-tense ask in the operator's absence?** Three sources, in order of cleanliness: (a) a **world event** (perception-field observation, ground-truth arrival, substrate transition) — already ask-shaped, the trader/reactive path; (b) a **cadence that fires an ask** for time-driven owed-output ("compose this week's scene now") — the author path the validation used, but originated by the schedule instead of a typed operator; (c) nothing — genuine quiet, the agent legitimately doesn't wake. The design must make (b) *stay ask-shaped* (imperative, present-tense, the-wake-is-about-this) and not degrade back into framed standing state.
2. **The terminal contract.** Can the loop adopt CC's "stop when the ask is answered" while preserving YARNNN's need to make non-completion *visible* (the absent-watcher problem §2)? Likely: an *unanswered ask* is a first-class visible state (the ask persists / re-fires), replacing the fabricated `stand_down`.
3. **The consequential gate stays.** None of this touches the witness dial / ADR-307 gate / ground-truth calibration — the moat's real independence sources (`judgment-execution-unification.md` §3). The ask-shaped wake changes *how work is originated*, not *how consequential acts are bound*.
4. **The judge↔produce question.** The validation shows one unified agent produces on an ask (it composed, it didn't dispatch). Whether a genuinely-independent audit-agent is ever warranted (real outside vantage, not a same-model second pass) stays a *future seam*, out of the spine's scope.

---

## 7. The honest bottom line

The operator's thesis holds on its load-bearing claim, and the receipt is in hand: **once the obligation arrives as a present-tense ask, the agent infers-and-acts exactly as Claude Code does** — and everything YARNNN built to simulate a present principal (envelope sections, verdict enum, recovery synthesizer, wake-taxonomy, occasion header) becomes deletable rather than extendable. The substrate floor (ADR-209) and the cost substrate (ADR-327 budget) are *already* the CC-analogues done right and survive untouched. The cadence layer is the one seam — clock-fired judgment recurrences manufacture wakes-without-asks — and the fix is to re-shape it into ask-firing, which is smaller than the prosthetics it retires. The compactness CC achieves for millions of use cases is reachable here because the divergence was never the substrate or the model — it was that YARNNN answered "what do I do when no one asked?" with twenty framed sections and a default-to-inaction recovery, when the answer is **make sure something always asks.** The rewrite is de-risked to the degree the ask-shaping spine is held as the axiom; the blast-radius map (what survives, what is re-derived) is the next deliverable, now that the spine is proven rather than asserted.
