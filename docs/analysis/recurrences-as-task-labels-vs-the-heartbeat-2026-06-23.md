# Recurrences as task-labels vs. the heartbeat — a first-principles reassessment (DRAFT, Hat B, open)

**Date:** 2026-06-23
**Hat:** B (external-developer / strategy discourse). Recommends; does NOT edit ESSENCE / FOUNDATIONS / any ADR / any bundle. If a fork is chosen, it lands in Hat-A canon afterward.
**Status:** **CENTRAL PROPOSAL FALSIFIED by its own §5 probe (2026-06-23).** The heartbeat reframe did NOT fix composition — see §8 (added after the probe ran) and `docs/evaluations/2026-06-23-author-heartbeat-FALSIFICATION.md`. The task-label thesis is wrong; the cause is the judgment-vs-labor wake shape, and the redirect is production-as-distinct-execution (which the architecture ALREADY has via `dispatch_specialist.py`). The §§1–7 below are preserved as written (the reasoning that led to the probe); §8 records the falsification and pivot. The discourse did its job: it produced a falsifiable probe that killed a plausible-but-wrong theory cheaply.
**Driving evidence:** the 2026-06-23 author-origination arc — `docs/evaluations/2026-06-23-adr354-author-collapse-VALIDATION.md` + `2026-06-23-adr354-author-first-autonomous-VALIDATION.md` + the live netflix-script-author substrate receipts quoted below.

---

## 0. The one-paragraph thesis

YARNNN ships each workspace a **directory of named judgment recurrences** (`corpus-coherence-check`, `revision-audit`, `outcome-reconciliation`, `compose-screenplay-scene`, …), each with a hand-authored prompt. Canon has spent three ADRs (275 → 306 → 354) making those prompts *thinner* but never asked whether the **named, per-task recurrence** should exist at all. The thesis here: **a named judgment recurrence is structurally a task-label, and a task-label contradicts ADR-318 ("a wake is a situation, not a task").** The contradiction is not cosmetic — it is the direct cause of the production-deferral this session could not fix by trimming prompts. The Claude-Code-shaped resolution: **judgment recurrences dissolve into a single heartbeat** (a clock + the mandate + live substrate); on each wake the agent reasons *situation → action* and does the work the operation needs — audit if there is a corpus, compose if it owes output and none exists, reconcile if outcomes arrived. The clock and the mechanical/deterministic jobs (`track-*`) survive; the named judgment scripts dissolve.

---

## 1. The receipts — what we could not fix by trimming prompts

The author program owes "~1 scene/week" (declared Expected Output) and started from an empty corpus. Four wakes, four behaviors, each after we removed the prior obstruction:

| Wake | What we'd fixed first | What the agent did | Receipt |
|---|---|---|---|
| `corpus-coherence-check` | (nothing) | audited nothing, "documented waiting state" | runs 070553 / 071317 |
| `corpus-coherence-check` | collapsed the audit prompt (ADR-354 §7) + force-pushed the (B) rule | classified (B), **asked** ("authorize me to compose…") | exec `07:28:46`, `outcome_kind: clarify` |
| `corpus-coherence-check` | rewrote (B) to author-first-under-autonomous (ADR-354 §8) | **authored a producer recurrence** (`compose-screenplay-scene`) | exec `07:49:42`, `outcome_kind: schedule_create` |
| **`compose-screenplay-scene`** (fired on-demand, its prompt literally says *"Author a screenplay scene"*) | (the producer organ now exists) | **wrote `standing_intent` planning to compose "when it fires Monday"** — composed nothing | exec `08:11:14`, wrote only `standing_intent.md`, **zero `content.md`** |

The last row is the tell. The producer recurrence fired **now**, holding an explicit "Author a scene" instruction, and the agent's own words were:

> `horizon: "Waiting for compose-screenplay-scene to fire Monday 2026-06-24T10:00:00Z."`
> *"On Monday 10:00 UTC when `compose-screenplay-scene` fires: 1. The recurrence prompt directs me to author a screenplay scene…"*

**It waited for itself.** The wake that *was* the production act was narrated as a routine check whose production happens at the *next* instance of the same recurrence. No prompt edit reached this — we had already collapsed the prompt and fixed the precedence. The deferral retreated one rung up every time we fixed the rung below. That pattern — assess → classify → schedule → plan, never produce — is the signature of a structural cause, not a prompt defect.

**Across the whole arc, the agent has never composed an artifact. Not once.** "Full autonomy demonstrated" was over-claimed at every step on the strength of the *setup* (a classified gap, a created organ) rather than the *product* (a scene). The honest state: zero `content.md` exists on netflix-script-author.

---

## 2. The first-principles read — why a named recurrence is a task-label

Strip the mechanism. What does a wake hand the occupant?

- **A clock fired** (the Trigger; genuinely needs to exist — something must wake the loop in the operator's absence).
- **A named recurrence + its prompt** ("you woke for `compose-screenplay-scene`; here is what that recurrence is about").

The second half is the problem. ADR-318 D1 says, verbatim:

> *"A wake is a situation, not a task. You are a standing judgment seat that was woken for a reason — not a function that runs one prompt and exits… This is judgment, not a checklist: reason about your forward state, don't run a fixed list."*

But a **named recurrence with a per-task prompt is exactly a task label.** `compose-screenplay-scene` doesn't say "here is the situation, serve the mandate" — it says "you are in the compose ritual." The slug *is* a fixed list of one. An LLM occupant handed a concrete labeled ritual ("the compose-screenplay-scene wake") will perform the ritual's *shape* — and the shape of a judgment recurrence is *deliberate, then write standing_intent, then close*. So it deliberates about composing (plans it, schedules it, describes it) instead of composing. **The named recurrence imports a deliberation posture onto a labor task, and the deliberation posture wins** — because the label told it "this is a wake about composing," not "compose."

This is the **exact ADR-354 pathology** ("a concrete labeled procedure beats the abstract frame") — but ADR-354 located it in the prompt *content* and collapsed the content. The deeper instance is in the prompt's *existence as a named task*: even a one-line compose prompt, attached to a slug called `compose-screenplay-scene`, is a task-label that pre-slices attention. You cannot trim your way out of a label by shortening it.

### Why the trader doesn't expose this (and why that misled us)

The trader's named recurrences *work* (fire → propose → execute). Tempting to conclude "named recurrences are fine; the author is special." The honest read: the trader's product — a `ProposeAction(ticker, size, stop)` — **is itself a decision**, which fits the deliberation posture natively. `signal-evaluation` as a task-label asks for a decision, and the agent makes a decision. The author's product — prose — is **labor**, which the deliberation posture cannot carry. The named-recurrence model is *masked* by the trader's decision-shaped output and *exposed* by the author's labor-shaped output. The model was always task-labelling; we only noticed when the task was labor.

---

## 3. The Claude-Code resolution (the operator's chosen altitude)

Claude Code has **no directory of named judgment recurrences.** It has: a filesystem, tools, a thin stable prompt (CLAUDE.md + system), and a trigger. When invoked, the agent looks at the actual state and does what is needed — run tests if tests are failing, write the feature if a feature is owed, nothing if the tree is clean. **One posture, N situations, judgment maps situation → action.** There is no `run-tests` recurrence competing with a `write-feature` recurrence; "what to do" is *derived from the world*, never *dispatched by a label*.

ADR-261 D1 already says YARNNN "gears toward Claude Code / Claude Cowork **at the framework level**." ADR-281 §2 draws the explicit analogy (workspace files = filesystem; primitives = tools; `principles.md`+`MANDATE.md` = CLAUDE.md). **The one place YARNNN diverges from Claude Code is precisely here: it ships a per-workspace directory of named judgment recurrences with per-task prompts.** That divergence is the residual over-engineering. Finishing the Claude-Code arc means dissolving it.

### The proposal (boldest form)

**A workspace's judgment surface is: a heartbeat (when to wake) + the mandate + live substrate. No named judgment recurrences.** On each heartbeat wake, the envelope carries the situation (what changed, what's owed, current ground-truth — the substrate already computes this), and the agent reasons:

> *"I am the standing judgment for this operation. Given the current state — corpus, outcomes, owed-output, watches — what does the mandate need from me right now?"*

…and does it. Compose if it owes a scene and none exists. Audit if a corpus exists and coherence is the live concern. Reconcile if outcomes arrived. Nothing (standing_intent only) if genuinely quiet. **This is ADR-318 taken literally** — the wake is the situation; there is no task label to perform the shape of.

### What survives (this is NOT "delete recurrences")

- **The clock.** Something must wake the loop on a cadence in the operator's absence. The heartbeat *is* a recurrence in the minimal ADR-261 sense (`schedule` + `mode`). What dissolves is the **per-task `slug` + per-task `prompt`** for judgment work.
- **Mechanical/deterministic jobs (`track-*`).** `track-universe`, `track-positions`, `track-sources`, `track-repo` are `mode: mechanical` — deterministic Python, no judgment, no LLM. These are genuinely named jobs (fetch *this* data on *this* cadence) and should stay exactly as they are. They are not task-labels for a judgment occupant; they are the perception field's intake (ADR-335). The dissolution is **judgment-mode only.**
- **Reactive triggers / hooks** (`_hooks.yaml`, `schedule: null`) — a substrate transition fires a wake. These are situations by construction ("a draft hit ready_for_review"), not task-labels. They stay.

So the end state per workspace: a small set of **mechanical intake jobs** + **reactive hooks** + **one judgment heartbeat** (or a couple, at different cadences — daily deep, hourly light), each heartbeat carrying *the situation*, not *a task*. The `_recurrences.yaml` directory shrinks to intake + hooks + heartbeat; the four-to-five named judgment scripts collapse to zero.

---

## 4. What this contradicts, honestly

- **ADR-261 D2** ("single canonical place" — the named-recurrence directory) is *preserved in shape* (the file stays) but *changed in content* (no named judgment entries). The data model `{slug, schedule, mode, prompt}` survives for mechanical + heartbeat; the assumption that *judgment work is enumerated as named entries* is what's dropped.
- **ADR-275 D1** (Reviewer-authored judgment cadence) is *strengthened, not broken*: if there are no named judgment recurrences to author, the Reviewer authors only its *heartbeat cadence* (how often to wake) — a pure ADR-275 act, with none of the task-labelling. The "author a `compose-next-piece` recurrence" move from ADR-344 (B) **dissolves**: there is nothing to author, because composing is just what the heartbeat does when the mandate owes output. (This is the cleanest evidence the proposal is right — ADR-344's (B) "author the missing organ" was itself a symptom of the task-label model; under a heartbeat there is no "missing organ," only "work the mandate owes that this wake should do.")
- **ADR-354** is *completed and then superseded at the judgment layer*: it correctly collapsed judgment-prompt *content*; this collapses the judgment-prompt *existence*. ADR-354's mechanical-recurrence and the trader's decision-shaped `signal-evaluation` are the boundary cases worth re-examining (see §6).

The contradiction with ADR-318 is the load-bearing one, and it resolves *in ADR-318's favor*: the directory of named judgment recurrences was the un-collapsed remnant that ADR-318's "a wake is a situation, not a task" had already declared wrong in principle.

---

## 5. The concrete probe — test the reframe before believing it (ADR-352 §6b)

The discipline this session repeatedly violated: declaring the milestone on setup, not product. The probe must read **a composed artifact**, on demand, no calendar wait. Design:

**Probe name:** `author-heartbeat-composes` (Hat-B scenario, deterministic via `fire_cron`).

**Hypothesis:** if a judgment wake carries *the situation* ("you are awake; here is the operation's current state and what it owes") rather than *a task label* (`compose-screenplay-scene`), the agent composes an actual `content.md` on that wake — no deferral, no permission ask, no "when it fires next."

**Setup (single-variable against the failed run):**
- netflix-script-author, funded, autonomous, declared Expected Output (weekly scene), empty corpus — *identical to the runs that deferred*.
- The ONLY change: replace the named judgment recurrence(s) the wake fires under with a **single heartbeat** whose prompt is situation-forward and task-label-free. Candidate prompt (thin, ADR-318-shaped):
  > *"You are the standing judgment for this operation. The substrate below is the current state (mandate, owed-output, corpus, outcomes, watches). Serve the mandate against this state — do the work it needs now. principles.md is your framework; the frame owns how you close."*
  No slug named "compose." No "audit for 1,2,3." No "author a scene." Just: here is the world, serve the mandate.

**Fire:** `fire_cron` the heartbeat (deterministic, on-demand — the harness built this session).

**PASS criterion (product, not setup):** a new `content.md` exists under `/workspace/operation/authored/{scene-slug}/` with actual prose, attributed `reviewer:*`, status `draft`/`ready_for_review` — OR a `WriteFile` proposal carrying the scene content (if a gate applies). A `schedule_create`, a `clarify`, or a `standing_intent`-only close is a **FAIL** (the deferral reproduced — the heartbeat reframe didn't fix it, and the cause is deeper than the task-label).

**Control:** the failed `compose-screenplay-scene` on-demand fire (exec `08:11:14`, zero content) is the before-state. Same workspace, same funding, same autonomy — only the wake's framing differs. If the heartbeat composes where the named recurrence deferred, the task-label thesis holds on a single variable.

**Honest failure branch:** if the heartbeat *also* defers, the thesis is wrong and the cause is NOT the task-label — it is something deeper (the occupant genuinely will not perform labor in a judgment wake; the production must be a distinct execution mode / sub-dispatch — the "Option 1" the operator set aside). The probe is designed to *falsify* the task-label thesis cleanly, not just confirm it.

---

## 6. Open questions for the next pass (the lean is visible; attack it)

1. **Does the trader's `signal-evaluation` survive as a named recurrence, or does it dissolve too?** Lean: it dissolves *in principle* (it's a task-label that happens to work because its task is decision-shaped), but it's lower-priority to touch because it isn't broken. A clean design would have the trader heartbeat too — "serve the mandate against the market state" — and let the agent decide to evaluate-and-propose. Worth testing the trader heartbeat doesn't regress before generalizing.
2. **How many heartbeats?** One cadence, or a few (a daily deep wake + an hourly light wake)? The cadence is genuinely operator/Reviewer-authored (ADR-275); the question is whether *multiple heartbeats at different cadences* re-introduces task-labelling by the back door ("the hourly one is for X"). Lean: cadences are fine as long as each carries *the situation*, not *a task* — a faster clock is still "serve the mandate," just more often.
3. **Does the situation-envelope already exist?** The substrate already computes owed-output (DP30), watch signals (ADR-335), recent execution (`_recent_execution.md`), calibration (`_calibration.md`). The heartbeat envelope is mostly *assembling what's already there* — this may be a small change, not a large one. Worth confirming the envelope can carry "what the operation needs now" without new machinery.
4. **Is "compose" labor the occupant resists in ANY judgment wake** (the falsification branch §5)? If the heartbeat probe fails, the real fork is production-as-distinct-mode, and this whole discourse is the wrong tree. The probe settles it.

---

## 7. The honest bottom line

We over-engineered to a fixed point: a directory of named judgment recurrences, each a little task-script, that we kept trimming instead of questioning. Canon already declared the principle (ADR-318: a wake is a situation, not a task; ADR-261: gear toward Claude Code at the framework level) but stopped at trimming prompts. The author program's total failure to ever compose an artifact — even when its own producer recurrence fired with an explicit compose instruction — is the evidence that the named-recurrence model itself is the residual task-labelling. The Claude-Code resolution is to dissolve the judgment recurrences into a heartbeat + mandate + substrate, and let judgment map situation → action. **Prove it with the §5 probe before any canon moves.** If the heartbeat composes where the named recurrence deferred, the directory was the over-engineering. If it also defers, the cause is deeper and this doc is wrong — which the probe will show honestly.

---

## 8. The probe ran. The thesis is FALSIFIED. (2026-06-23 — `author-heartbeat-FALSIFICATION.md`)

The §5 probe fired a task-label-free, situation-forward `heartbeat` on the identical failed-run substrate. **It did NOT compose.** The heartbeat wake (`exec 23:28:26`, judgment, success, $0.59) classified itself "routine heartbeat; substrate maintenance only," bootstrapped `_signal.md`, and **deferred composition to "Monday compose-screenplay-scene"** — the very recurrence it had authored in the prior run. Removing the task-label changed nothing about the never-composes behavior.

So §1–§7's central claim — "the named recurrence (task-label) is the cause" — is **wrong.** The directory-of-named-recurrences is still defensible as a *simplification* (the Claude-Code argument in §3 stands on its own merits — it is genuinely over-engineering to ship N named judgment scripts), but it is **NOT the cause of the deferral**, so dissolving it would not have fixed composition. Good thing we probed before moving canon.

**The real cause (now evidence-grounded, was the operator's set-aside Option 1):** the occupant will not perform **labor** (compose ~2,000 words of prose) inside a **judgment wake** — under ANY framing. A judgment wake's shape is perceive → decide → standing_intent/verdict → close; composing prose is production, not a decision, so the occupant does the judgment-shaped moves (assess/maintain/plan/schedule/defer) and pushes the labor elsewhere. Four wakes (two audit, one on-demand compose-recurrence, one heartbeat) all produced every judgment-shaped artifact EXCEPT the prose. The constant is "judgment wake"; the variable (task-label vs heartbeat) didn't move it.

**The redirect is already in the architecture, not invented:** `REVIEWER_PRIMITIVES` *does* include WriteFile (so composing is mechanically available — the block is posture, not capability), and the registry comment beside it says *"for production work the Reviewer's context shouldn't carry"* — with `dispatch_specialist.py` already being the headless sub-LLM production surface. Canon ALREADY separates judgment from production. The author program just isn't routing composition through it. The next pass: **the Reviewer judges "the mandate owes a scene" and `DispatchSpecialist`s the composition** (off its own context), then audits the returned draft through the existing pre-ship floor — the trader pattern made symmetric (trader proposes a decision; author dispatches a production). That is a separate ADR, gated on its own probe (does a dispatched-specialist compose produce a real `content.md`?). This doc closes here; the production-as-distinct-execution thread opens fresh.
