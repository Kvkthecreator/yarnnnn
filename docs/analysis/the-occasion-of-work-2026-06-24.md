# The occasion of work — now-vs-later as a judgment the system has never had

**Date**: 2026-06-24
**Hat**: B → A (Hat-B insight that recommends a Hat-A re-founding; feeds the same ADR as the unification conviction)
**Status**: Thesis / insight document. Pre-ratification. Standalone because it is *upstream of* the judgment-execution unification (`judgment-execution-unification-2026-06-24.md`) — that doc's §6 summarizes this; this is the full statement.
**Operator framing (2026-06-24)**: *"We should ensure we also have a clear posture for when to work on what how — which seems to be the fundamental difference between acting now and handling wakes. The concept of waking itself up later to do work, and doing work now at the runtime it's awakened, is confused."*

> **Reversibility note.** Everything this thesis recommends is a reversible experiment first (a probe), not a canon commitment. The point of writing it down is to make the idea legible and falsifiable before any code or canon moves — and to be able to revert cleanly if the probe falsifies it, exactly as the prior four frame-level theories were reverted at zero canon cost.

---

## 1. The insight in one paragraph

A YARNNN agent is **wake-driven**: it does nothing until it is woken, acts within that runtime, and closes the cycle. On every wake it faces a fork on every obligation it holds — **do this work now, in this runtime**, or **author a future wake to do it later**. The system gives it *no principled basis for choosing*, and no concept that the choice even matters. So it defaults to "later," because "later" (author a `Schedule`) is the move its loop is shaped for and "later" always reads as responsible — planning, readiness, "the operation is structured to produce." Critically, the agent **does not experience this as deferral**: it experiences *scheduling the later-wake* as having discharged the obligation. The missing concept is the **occasion of work** — the runtime in which a given obligation *should* be discharged — and the judgment of when "now" is mandatory versus when "later" is legitimate.

## 2. Two kinds of waking the system conflates

There are two structurally different reasons an agent is awake, and canon treats them as one:

| | **Decide-wake** | **Do-wake** |
|---|---|---|
| The wake exists to | render judgment; place future attention | discharge owed work |
| The product of the wake is | a decision (verdict, a watch, a scheduled future wake) | an artifact / an executed act |
| "Author a future wake" is | **the work itself** — "watch for X; revisit at T" is a legitimate, complete output | **evasion** — the future wake faces the identical fork and defers again (infinite recursion) |
| The occasion is | *later*, gated on a real external condition the agent is waiting for | ***now*** — this runtime is the occasion; there is nothing external to wait for |
| Trader instance | `signal-evaluation`: evaluate, and if nothing warrants action, "wake me when the signal changes" is correct | submit the bracket order once the signal fires |
| Author instance | `corpus-coherence-check`: audit, and if the corpus is unchanged, revisit later is correct | **compose the owed scene — nothing external gates it** |

The trader's life is *mostly decide-wakes* (it waits on the market), which is why the confusion never surfaced there: the market originates the trader's do-wake triggers, so the trader rarely has to choose "now" against its own deferral reflex. The author's life is *mostly do-wakes* (it waits on nothing), so the author exposes the gap completely: every wake is an occasion to produce, and the agent defers every one.

## 3. The diagnostic the agent lacks

The judgment that distinguishes the two — which the agent currently cannot make because the concept does not exist:

> **"If I author a future wake to do this, will that wake be in any materially different position than I am right now — more information, fewer blockers, an external condition met?**
> - **If yes** → the occasion is later; scheduling future attention is real work (a decide-wake move).
> - **If no** → deferring is *circular*; the future wake is just this wake postponed, facing the same fork; **now is the occasion** and scheduling-instead is non-performance (a do-wake that must discharge here)."

Applied to the empirical case: the netflix author, on 2026-06-24, authored a future `compose-screenplay-scene` wake for Monday and recorded "obligation discharged." Had it run the diagnostic, it would have seen Monday's wake faces the **same empty corpus, same mandate, same absence of blockers** — Monday is today, postponed. The deferral was circular. It never asked, because nothing in canon told it to.

## 4. Why ADR-318 is the direct predecessor (and where it fell short)

ADR-318 ("A Wake Is a Situation, Not a Task") was correct and load-bearing — it freed the agent from "run one prompt and exit" and gave it standing-judgment posture. But it shipped **one gear**. Its only named forward move (D1, verbatim):

> *"a future wake you should author so you're woken when it matters... serve the named task first, then plan forward."*

That is the **decide-wake** posture, made universal. "Plan forward" = "author a Schedule." ADR-318 has no concept of a do-wake whose forward move is *discharge it now, and authoring a future wake would be evasion*. So an agent following ADR-318 faithfully — as the netflix author did — serves the named task, then "plans forward" by scheduling, and closes. **The bug is not the agent disobeying the posture; it is the posture having only the later-gear.** This thesis is the second gear ADR-318 needs, and the ADR that lands it should amend ADR-318 (not supersede — D1's situation-not-task framing survives; it gains the now/later axis).

## 5. Why this is upstream of the judgment/execution unification

The session's prior conviction was "unify judgment and production — the never-composes bug is the judge≠producer wall." The §5 probe falsified the *frame-prose* version of that (an explicitly-unifying prompt still deferred — see `2026-06-24-author-unified-prompt-FALSIFICATION.md`). The reason it falsified is *this thesis*: even an agent told "you may produce; produce now" defers, because it lacks the **occasion** judgment — it routes the production obligation to a future wake and calls that discharge. So:

- The judgment/execution separation is **a consequence**, not the root. (Production is implicitly "what a future wake does," because the agent always defers do-work to later.)
- The root is **the system has no posture for the occasion of work.** It answers "now or later?" with the later-reflex on every obligation.
- Therefore unification is **necessary but insufficient.** Adding a "produce" terminal move to the loop, by itself, will not produce — the agent will author a future *produce*-wake instead, unless it also holds the occasion judgment telling it *this obligation's occasion is now*. The probe proved this directly: the occupant HAD `WriteFile` (the production mechanism) and still chose "later."

Two load-bearing pieces, this one senior:
1. **(this thesis — conceptual)** the occasion judgment: decide-wake vs do-wake, the circularity diagnostic, "now" as mandatory when nothing external is waited on.
2. **(unification — mechanical)** the loop must be *able* to discharge in-cycle (a produce terminal move), and "author the producer organ" must stop counting as discharge of a production obligation.

## 5b. The wake handling rule (operator formulation, 2026-06-24) — IS / NOW / LATER

The thesis above says *there must be an occasion judgment*. This section says *what the judgment is structured as* — the operator's formulation, which is the operational half:

**Every wake carries one posture — awareness-and-work-at-large — that resolves into three tenses:**

| Tense | What it is | Derived from |
|---|---|---|
| **IS** (past / present-state) | what happened + what is true now — front-loaded context | the envelope (substrate, ground-truth, recent execution, the wake's named reason) |
| **NOW** | the present work of *this* runtime — judgment, actions, outputs, confirmations | **IS** ("given what is true, what does this moment require?") |
| **LATER** | future wakes / recurrences | **NOW** ("given what I just did and decided, what should I be woken for next?") |

**NOW and LATER are independent** (operator decision, 2026-06-24): a wake may legitimately do NOW only (produce/act/confirm), LATER only (a pure decide/watch wake — e.g. `signal-evaluation` that finds no signal and just sets "watch for the level"), or both. There is **no forced sequence** that demands present output on every wake. A quiet decide-wake is complete, honest work.

**The correction that fixes the bug** — *which* of {NOW-only, LATER-only, both} a wake does is **itself the judgment, and it must be earned from IS, not reached for by reflex.** LATER for a given obligation is legitimate **only when IS shows a future wake would be in a materially different position** (an external condition met, more information, a blocker cleared). The failure mode is **LATER chosen when IS does not justify it** — deferring work whose occasion is *now*, dressed as forward-thinking. The netflix author did exactly this: it owed a scene, IS showed nothing external gating composition, and it still chose LATER (authored a future producer-wake) and called it discharge. It mis-made the independent choice because LATER is the move the loop is shaped for and nothing required it to *earn* LATER from IS.

So the rule is **not** "always produce now." It is: **LATER must be earned from IS; it is never the unconditioned default close.** When the agent picks LATER it is because IS genuinely contains a future-gating condition — otherwise the occasion is NOW and the present work is owed in this runtime. This keeps the occasion-of-work choice a real judgment (honest — the agent should have to decide) while removing the reflex that made LATER free.

**Implications for the terminal-move set**: a cycle closes when its chosen tenses are complete — present work discharged (NOW, e.g. the `content.md` WriteFile for a do-shaped obligation) and/or forward-setup authored (LATER, the `standing_intent`/`Schedule`). `standing_intent` is the *record of the LATER tense*; producing the artifact is the NOW tense. The current "close with a verdict OR a standing_intent" collapses this — it offers only the LATER-record close and the verdict close, with no NOW-discharge close, which is why a do-wake has no way to terminate by *having produced*.

**Single-queue note** (operator): there is one wake lane, so a wake is not a "task slot" — it is a moment in a continuous operation that always reads IS, decides NOW, and derives LATER. Recurrences/future-wakes are NOW deciding *when the operation should next become aware* — memory-of-what-to-do-later derived from the present, never a parking lot for present work.

## 6. Where the posture must live (proposal, for the audit + ADR to confirm)

- **Persona-frame (`reviewer_agent.py`)** — the occasion judgment is a **principal-shift-class** correction (Derived Principle 22): it corrects the model's trained reflex "no trigger fired → schedule something → done." That reflex is a property of installing standing-judgment over an assistant prior, not an operator declaration, so it belongs in the frame, not substrate. It is a *posture*, not a rule-of-judgment — so it is frame-eligible under §3.2.1.
- **`principles.md` (program-tuned)** — the *thresholds*: what counts as "a real external condition I'm waiting on" differs by program (trader: a price/signal level; author: an operator input or a corpus change). The decide/do *frame* is universal; the *instances* are program-derived (ADR-222 kernel-names-category boundary).
- **The `Schedule` move + the standing-obligation discharge logic (code)** — the gate: authoring a future wake for an obligation whose occasion is *now* should be recognized as non-discharge. The DP30 standing-obligation check must read *work actually discharged*, not *future wakes scheduled*. (Audit to locate the exact site where "scheduled" currently reads as "discharged.")

## 7. The falsifiable prediction

If this thesis is right, an author agent given **both** (a) the occasion judgment in its wake posture and (b) a loop that can close by producing, will **compose in-cycle on its first wake** against an empty corpus + owed-output mandate — because it will run the diagnostic ("a future wake faces the same empty corpus → deferring is circular → now is the occasion"), find no external condition to wait on, and discharge. If it still defers, the occasion posture is mis-stated or there is a third blocker, and we revert and learn — at zero canon cost (probe before canon).

## 8. Bottom line

The system has been wake-driven without a theory of *the occasion of work*. It conflates two kinds of waking — *deciding/watching* (where "later, when it matters" is the right output) and *doing owed work* (where "now, this runtime" is the only honest output) — and applies the watch-and-schedule reflex to both. That is why production never happens and why deferral feels like readiness. The fix is a posture that makes the now-vs-later choice a *judgment* — with the circularity diagnostic as its test — paired with a loop that can actually discharge work in-cycle. Both are reversible experiments first. Document, audit, probe, then (only if the probe composes) canon.
