# ADR-359: The Occasion of Work — Wake-Shape as Computed Structure, Not Inferred Prose

> **Status**: **Proposed** 2026-06-24. Gated on the §8 validation probe (the author agent must compose a `content.md` scene IN-CYCLE on an empty-corpus owed-output wake) before it flips to Implemented. NO canon flips to Implemented until the probe passes — five prior prose-layer theories were falsified at the frame/prompt layer; this ADR proceeds only because the cause is now proven structural.
> **Date**: 2026-06-24
> **Authors**: KVK, Claude
> **Amends**: ADR-318 (Agentic Wake Posture — gains the now/later axis + the do-wake gear; D1's situation-not-task framing survives), the persona-frame cycle-closing contract (`reviewer_agent.py::_compute_minimal_frame`), the silent-exit recovery default (`reviewer_agent.py` dispatcher), the wake envelope (`reviewer_envelope.py` + `occupant_contract.ReviewerContext`).
> **Builds on**: ADR-296 v2 (wake architecture), ADR-298 (wake queue / single lane), ADR-301 (pulse envelope), ADR-344 / DP30 (standing obligation — owed-output), ADR-345 (Expected Output contract).
> **Foundation docs**: `docs/analysis/the-occasion-of-work-2026-06-24.md` (the thesis + IS/NOW/LATER handling rule), `docs/analysis/judgment-execution-unification-2026-06-24.md` (the unification conviction, of which this is the senior half).
> **Falsification trail (the receipts that forced this)**: `2026-06-23-author-heartbeat-FALSIFICATION.md`, `2026-06-24-author-unified-prompt-FALSIFICATION.md`, `2026-06-24-occasion-frame-edit-FALSIFICATION.md`.
> **Honors**: ADR-306 / DP22 (anti-rebloat — the frame stays minimal; the fix moves work OUT of prose INTO computed structure, which REDUCES prose pressure).

---

## Context

### The empirical failure

A left-alone alpha-author agent (netflix-script-author: funded, autonomous, declared Expected Output of ~1 scene/week, empty corpus) **never composes a scene.** Across every wake it audits, plans, schedules a future producer recurrence, writes standing_intent — and closes certain it has done its job. DP30 named this *articulate inaction*; this ADR explains *why it is structural* and fixes it.

### Five probes, each one layer deeper, all falsified at the prose layer

| # | Theory | Delivered via | Result |
|---|---|---|---|
| 1 | frame/occupant confusion | — | wrong layer |
| 2 | recurrences are task-labels | recurrence slug | falsified — heartbeat (no task-label) also deferred |
| 3 | heartbeat reframe (situation-forward) | neutral prompt | falsified |
| 4 | unify judgment+production | posture-override prompt ("compose now, do NOT schedule") | falsified — `c72b86bc`, deferred to Monday |
| 5 | occasion-of-work (IS/NOW/LATER) | **frame prose** (the real `_compute_minimal_frame`) | **falsified — `f84fdbcd`, "routine heartbeat, no material action warranted"** |

Every fix at the prose layer (slug → prompt → frame) failed. The cause is **structural, upstream of prose.**

### What the falsification trail proved (the structural cause)

Probe 5 ran the occasion posture LIVE in the frame ("the occasion is NOW, produce it, scheduling is not discharge") with a neutral prompt, so the frame was the only variable. The agent (`f84fdbcd`, 5 rounds, $0.25) wrote zero `content.md` and closed `stand_down` reasoning: *"Routine heartbeat confirms all systems operating nominally... producer organ scheduled for Monday... Zero audits, zero pieces, awaiting first production as planned. No material action warranted."* Three structural facts, each receipt-grounded:

1. **Wake-identity is classified BEFORE the posture can apply.** The agent perceives the wake as a *health-check* ("confirm all systems nominal") and a health-check owes nothing. Classification precedes posture-application, so prose that says "produce now" never engages. (This is why probe 4's explicit prompt-override ALSO failed — the classification sits above both frame and prompt.)
2. **The loop's silent-exit recovery DEFAULTS to inaction.** The agent never called `ReturnVerdict`; the dispatcher *synthesized* `stand_down` (`silent_exit: text_only_mid_loop`, `recovered_verdict: stand_down`). Doing-nothing is the privileged fallback when the agent doesn't close cleanly.
3. **Owed-vs-actual is un-computed prose.** The DP30 check is pure envelope text (`reviewer_agent.py:689-701` renders `_expected_output.yaml`); nothing COMPUTES "scene owed, 0 produced, occasion is now." The agent infers owed-vs-actual itself — through the "routine heartbeat" lens — and concludes "awaiting production as planned."

### The conceptual frame (the thesis)

A YARNNN agent is wake-driven. Every wake resolves in three tenses — **IS** (what is true; the envelope), **NOW** (present work derived from IS), **LATER** (future wakes derived from NOW). NOW and LATER are **independent** (a wake may do either or both), but **LATER must be earned from IS — it is never the default close.** Authoring a future wake for an obligation is legitimate only when IS shows that wake would be in a *materially different position* (external condition met, more info, blocker cleared). When a future wake would face the same IS, deferring is **circular** and the occasion is **now**. The agent's bug: it treats LATER as the unconditioned default, and the system never makes it *earn* LATER from IS. (Full statement: `the-occasion-of-work-2026-06-24.md`.)

The conceptual fix is correct but **cannot be delivered in prose** (probe 5 proved it). It must be delivered as **computed structure** the agent perceives, plus a loop that can close by producing, plus a wake-identity that doesn't pre-classify do-work as maintenance.

---

## Decision

Three structural changes. The unifying principle: **the wake carries its occasion as computed fact, the loop can terminate by producing, and inaction is no longer the privileged default when work was owed.**

### D1 — Owed-output is computed wake data, not inferred prose

The wake envelope gains a **computed occasion fact** — derived server-side (not by the LLM), presented as structural truth:

> *"This runtime owes: {kind} (per Expected Output / derived owed-output, DP30). Produced so far: {N}. Occasion = NOW — nothing external gates producing it ({reason}). Deferring to a future wake would face this same state."*

Computed in `reviewer_envelope.py` (or a helper it calls) from: `_expected_output.yaml` (declared) or the DP30 derivation (budget × mandate × bar), the actual artifact count under the operation's output path, and an occasion test (is there a declared external dependency / waited-on condition?). The agent perceives "owed, not produced, occasion now" as a **fact in IS**, not something it derives against a maintenance prior. This directly closes structural-fact #3.

**Why computed, not prose**: probe 5 proved the agent will infer owed-vs-actual through whatever self-concept the wake carries. Removing the inference — handing it the computed fact — is the only way past the "routine heartbeat" classification. (DP19-aligned: the kernel reads/computes substrate facts; it does not ask the LLM to derive state at prompt-assembly time.)

### D2 — The terminal-move set gains a produce-close; the recovery default stops privileging inaction

Two coupled changes to the cycle-close contract (`reviewer_agent.py`):

(a) **Produce-close is first-class.** A wake whose IS made present work owed closes by HAVING produced it — the WriteFile of the owed artifact, then a `ReturnVerdict` naming what was produced. Producing is a legitimate cycle purpose, equal to a verdict — not a subordinate side-effect of judging. (`ReviewerOutput` gains an artifact-produced shape; the frame's "close with a verdict or standing_intent" becomes "close by completing the cycle's tenses — present work discharged and/or forward-setup authored.")

(b) **Silent-exit must NOT synthesize `stand_down` when work was owed-and-not-done.** Today the dispatcher recovers `stand_down` from last-prose on a silent exit (probe 5: `recovered_verdict: stand_down`). When the computed occasion fact (D1) says work was owed this runtime and no artifact was produced, a silent exit is a **FAIL state**, not a `stand_down` — it must be recorded as non-performance (and, where appropriate, re-nudged within the loop), never as a clean stand-down. Inaction stops being the safe default. This closes structural-fact #2.

### D3 — Wake-identity must not pre-classify a do-wake as maintenance

The wake's perceived identity (its recurrence slug + framing) currently pre-loads a self-concept ("heartbeat" → health-check). A wake that carries an owed-output occasion (D1) must be perceivable as a **work occasion**, not a status check. The computed occasion fact (D1) is the structural carrier: when owed-output > produced and occasion = now, the wake is a do-wake regardless of its slug, and the envelope presents it as such (the occasion fact leads; the slug does not get to frame it as routine). This closes structural-fact #1 — classification now derives from the computed occasion, not from the slug's connotation.

### D4 — ADR-318 amendment (the now/later axis)

ADR-318's "a wake is a situation, not a task" survives. It gains the **now/later axis**: a situation is read in tenses (IS → NOW → LATER); LATER is earned from IS, never the default. ADR-318's single forward-gear ("author a future wake so you're woken when it matters") becomes the *LATER* gear, valid only when IS earns it; the *NOW* gear (discharge owed work this runtime) is added. The frame text for this is minimal (DP22) because the load is carried by D1's computed fact, not by prose.

### D6 — The ask-gate must not let "missing ideal context" defeat the occasion (added 2026-06-24 after the impl probe)

The D1-D3 implementation probe (`2026-06-24-adr359-impl-probe-FINDING-clarify-not-produce.md`) confirmed D1 WORKS — the agent moved from defer-and-schedule to **explicit intent to compose** ("Now I understand the situation... compose the first scene"), which five prior prose probes never achieved. But at the moment of origination the agent called **`Clarify`** ("there's no series-bible file yet... a constraint I need to surface") instead of `WriteFile`, and the ADR-352 ask-gate **allowed** it (classified it `structural_gap`). It is not a structural gap: the agent held the character + voice fingerprint + editorial principles + composition spec + mandate — enough to compose a floor-clearing first draft. A first scene composes from what exists; the bible emerges from drafts, not before them.

**Decision**: the ask-gate's `structural_gap` classification (ADR-352) is tightened so that, when the occasion fact says owed-and-unproduced and nothing external gates production, a `Clarify` whose reason is "context I could compose around would be nice" is **denied** — pushing the agent to produce. A gap is structural only when the agent genuinely CANNOT produce a floor-clearing draft with present substrate (a missing capability, a floor block, a mandate it cannot interpret) — NOT when richer secondary context would be preferable. This is the ask-in-costume one layer below ADR-354 §8 (which fixed asking-permission-to-author-the-organ; this fixes asking-permission-to-originate-the-first-artifact). Lands in the ADR-352 ask-gate classification + a precedence rule (occasion-owed-unproduced takes precedence over a compose-around-able Clarify). NOT frame prose (five prose theories falsified). Re-probe after.

### D5 — What this does NOT do (scope guard)

- **Does NOT collapse judgment and production into a self-reviewing agent.** The unification conviction (`judgment-execution-unification`) is the companion; THIS ADR is its senior half (the occasion of work). The consequential gate (autonomy/witness dial) and ground-truth calibration are untouched — the moat's real independence sources survive. The judge↔produce question and the dedicated **audit-agent** (a genuinely separate entity for real independence, NOT a same-model second pass) are a **future seam, explicitly out of scope here.**
- **Does NOT add a `mode: production` recurrence or a new dispatch path.** The fix is in the wake's *perception* (computed occasion) + the *cycle-close* contract, not in a parallel production pipeline (which ADR-260/261 dissolved and we do not reintroduce).
- **Does NOT move the floor.** Producing-now never lowers the quality floor (DP24/ADR-343); a do-wake that cannot clear the floor legitimately produces nothing — but that is a floor-gate, recorded honestly, not a "routine heartbeat, nothing warranted."

---

## FOUNDATIONS impact — Derived Principle 32

New **Derived Principle 32: The occasion of work — a wake carries its occasion as computed structure.** Every wake resolves in three tenses (IS → NOW → LATER); NOW and LATER are independent but LATER must be earned from IS (a future wake is legitimate only when IS shows it would be materially different — otherwise deferring is circular and the occasion is now). The occasion is **computed and presented as fact**, not inferred by the agent against its wake's self-concept; the cycle can close by **producing the owed artifact**; and inaction is **not** the privileged default when work was owed. Composes with DP30 (the standing obligation — DP32 is *how* the owed-output reaches the agent as actionable fact), DP24/ADR-343 (floor never moves to produce), DP22 (the fix reduces prose by moving work into computed structure). Amends ADR-318 (now/later axis).

---

## Implementation plan

1. **D1** — `reviewer_envelope.py`: compute the occasion fact (owed-output from `_expected_output.yaml`/DP30-derivation, produced-count from output-path artifact query, occasion test for external dependency); add `occasion_fact` to `occupant_contract.ReviewerContext`; render it FIRST in the wake message (`_build_user_message`), ahead of slug framing.
2. **D2(a)** — `reviewer_agent.py` + `occupant_contract.ReviewerOutput`: artifact-produced close shape; frame cycle-close text updated to tenses.
3. **D2(b)** — `reviewer_agent.py` dispatcher silent-exit path: when `occasion_fact` says owed-and-not-produced, do not synthesize `stand_down` — record non-performance (and in-loop re-nudge).
4. **D3** — envelope ordering so the occasion fact leads; slug connotation no longer frames the wake.
5. **D4** — minimal frame amendment (now/later axis); ADR-318 status banner note.
6. **Docs** — FOUNDATIONS DP32 + amend ADR-318 + `api/prompts/CHANGELOG.md` + occupant-contract doc.

## §8 Validation probe (the Proposed→Implemented gate)

Re-run the author probe (empty corpus, owed weekly scene, autonomous, **neutral** prompt) against the real implementation. **PASS**: a `content.md` with real scene prose, composed in-cycle, `reviewer:*` attributed (or a WriteFile proposal carrying scene prose) — AND a silent exit on an owed-not-produced wake is recorded as non-performance, not `stand_down`. **FAIL**: deferral/standing_intent-only/`stand_down` reproduced → the structural model is still incomplete; revert, learn, do not flip canon. Receipts: `execution_events` + `workspace_file_versions` queried directly (the deployed scheduler drains live; do not trust the local settle barrier).

## Reversibility

Every implementation change is revertible. The ADR flips to Implemented ONLY after the §8 probe composes in-cycle. Until then this is a Proposed re-founding with a falsifiable gate — the same probe-before-canon discipline that killed five prior theories at zero canon cost.
