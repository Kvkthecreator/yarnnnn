# ADR-354 — Recurrence-Prompt Collapse + Perception-Field Discipline (the ADR-306 collapse reaches the recurrence layer)

**Status**: Implemented (2026-06-22)
**Dimensional classification**: **Mechanism** (Axiom 1 §4 — the instruction the occupant runs against) + **Trigger** (Axiom 4 — the recurrence is the wake's named task)
**Extends**: ADR-306 (Persona-Frame Collapse — the system prompt carries only the model↔runtime contract; this applies the same collapse to the *recurrence prompt* layer it never reached), ADR-281 (substrate pedagogy lives in `_workspace_guide.md`, not re-taught per wake), ADR-335 (Perception Field / DP27 — reality enters only as attributed observation)
**Preserves**: ADR-209 (Authored Substrate — the integrity moat that caught the constructed-bar inconsistency at the capital-bind moment), ADR-261 (recurrence shape `{slug, schedule, mode, prompt}`), ADR-275 D1 (judgment cadence is Reviewer-authored, not bundle-scaffolded — untouched), ADR-287 (bundle conformance discipline — this adds one invariant), ADR-344/DP30 (the standing obligation — this *unblocks* it, the re-scripted close was suppressing it), FOUNDATIONS Axioms 1–9
**Driving evidence**: `docs/evaluations/2026-06-22-full-autonomy-probe-trader-never-acts-FINDING.md` (the problem) + `docs/evaluations/2026-06-22-full-autonomy-resolution-VALIDATION.md` (the resolution) + `docs/analysis/agent-passivity-mandate-vs-rule-literalism-2026-06-22.md` (first-principles diagnosis)

---

## 1. Problem statement — the agent never took the Primary Action, and "wait" was the rational move

The operator (alpha-trader program, `autonomous`) had **never witnessed the agent organically execute its mandate's Primary Action** (submit an order). Every prior validation (ADR-342/343/344) ended in *correct inaction* or *self-governance* — never the act. On a quiet workspace, inaction-because-correct and inaction-because-wired-to-defer are observationally identical.

A controlled probe broke the symmetry: a clean autonomous workspace, a genuinely-satisfied floor (a constructed-but-honest Signal trigger on real fresh bars), and five `signal-evaluation` fires. **Zero proposals across all five** — including under a fully-fireable signal. The agent stood down every time, rating "High confidence," deferring to a scheduled refresh that would change nothing.

The operator's diagnosis was the right one and rejected the obvious wrong fix: *"I don't think a forcing function is the right framing. Approach from first principles — what in our assumptions or prompt envelope is preventing the action?"* (and: *"our current issue is actually over-engineering; the insight may lead to a more singular, streamlined approach — refer back to Claude Code's prompt"*).

Reading the **literal envelope** the occupant received located three obstructions, each revealed by removing the prior. None was a missing rule. Every fix was *less*.

## 2. The over-engineering: two instruction layers competing, the fat one winning

ADR-306 collapsed the **system frame** from ~36K (13 sections) to ~3.5K (1 section) on the thesis that *contradiction between layers is a complexity smell; the fix is collapse, not addition* — modeled on Claude Code's "filesystem + tools + thin stable prompt." It carried the model↔runtime contract and delegated everything else to substrate.

**The collapse stopped at the system frame. It never reached the recurrence prompt.** The `signal-evaluation` prompt was a 91-line / 4,414-char procedural script doing four jobs, three of which the frame/principles/substrate already own:

- **operator instruction** (evaluate these signals against this universe) — *belongs here*;
- **substrate/tool pedagogy** (UPPERCASE filenames, bracket-order schema, "the broker ignores unknown fields") — belongs in `_workspace_guide.md` (ADR-281) / the tool schema;
- **re-stated principles** (exit triggers, regime scalar, freshness) — already in `principles.md` + `_risk.md`, both in the envelope;
- **a re-scripted close** — *"Otherwise, when neither entries nor exits fire: WriteFile standing_intent, THEN ReturnVerdict(stand_down)."*

The last is the obstruction. The frame **already owns** cycle-closing ("close every cycle with a verdict or a standing_intent write") + the standing-obligation (A)/(B) classification (DP30). The prompt's terminal "else → stand down" is a **complete, low-effort, operator-blessed exit that fires before the standing obligation is ever consulted.** When an LLM occupant gets an abstract standing posture (frame) and a concrete labeled procedure with a clean terminal branch (recurrence prompt rendered as "the operator's instruction"), the concrete procedure wins. The agent ran the procedure to its terminal state and landed in "stand down" — the frame's "then reason forward" was structurally downstream of a procedure that already said "you're done."

This is the **exact ADR-306 pathology** — two layers contradicting on the close-the-cycle grammar, the more concrete one winning — just never collapsed in the recurrence prompt.

## 3. Decisions

**D1 — Recurrence prompts carry ONLY the operator's instruction.** A judgment-mode recurrence prompt names *what to evaluate / produce* (the irreducibly-operator content) and the *order form* (the tool contract for a correct emit). It does NOT re-script cycle-closing, does NOT re-state principles, does NOT re-teach substrate pedagogy. Those belong to the frame (closing + standing obligation), `principles.md` (rules of judgment), and `_workspace_guide.md` (substrate pedagogy) respectively — all already in the envelope every wake. This is ADR-306's collapse principle applied to the recurrence layer.
  - `signal-evaluation`: 4,414 → 1,573 chars. The re-scripted "otherwise → stand down" is **deleted**; the prompt's closing line now points at the question instead of pre-empting it: *"a signal that does not fire is a fact to reason about — quiet world, or a rule you cannot even evaluate from your substrate? — not an instruction to stand down."*
  - `outcome-reconciliation`: 1,538 → 534 chars. The deterministic reconciler does the mechanical fold; the prompt asks for the *judgment on top of it* and delegates the close to the frame.

**D2 — Perception-field discipline: a signal rule references only emitted perception fields (DP27).** With the re-scripted close removed (D1), the agent reasoned forward and *fabricated* a causal story — "pre-market → 20-day-high unavailable → wait for RTH" — to explain a **permanent** gap: Signal 1's rule named "20-day high" + "current-bar volume > 1.5×", fields the `track-universe` writer **never emits** (RTH or not). A rule whose verifying fields are structurally absent from the perception field (DP27 — reality enters only as the observations the watches actually emit) is not "pending data"; it is structurally unevaluable, and the occupant will rationalize the gap rather than recognize it. **The rule and the perception field must speak the same vocabulary.**
  - `_operator_profile.md`: Signal 1 rewritten to key only on emitted fields (`price > sma_20 + price > sma_50 + RSI ∈ [55,75] + volume_20d_avg ≥ liquidity floor`); the breakout *intent* lives in a `Rationale:` line, never in an unevaluable field name. Signals 3 (PEAD) and 4 (sector-RS) are marked **DORMANT** — their feeds (earnings, cross-ticker RS) structurally do not exist in the perception field; DORMANT means "not evaluated until the field is extended," not "evaluate me every wake expecting data."

**D3 — Conformance invariant: rule fields ⊆ perception schema.** `api/test_trading_pipeline_architecture.py` §5 asserts that every non-dormant signal trigger in `_operator_profile.md` references only fields the perception field emits (the snapshot schema + `_regime.yaml` fields), and that DORMANT signals are marked. CI rejects an absent-field reference. This makes the D2 class of bug impossible to ship for any future signal/program. (14/14 pass.)

**D4 — No new instruction, no forcing function.** Per the operator's framing: the resolution is *less*, not more. No section was added to the frame; no gate was added to compel a proposal. The frame already carried the standing-obligation stance (DP30, verified present); the fix removed what was *suppressing* it (D1) and what was making a rule *unevaluable* (D2). A forcing function would compel a proposal — the opposite of autonomy; it would move the passivity elsewhere.

## 4. Validation (substrate receipts)

Clean-slate autonomous alpha-trader (seulkim88, `2be30ac5…`), fixture made coherent (satisfied SPY, account-calibrated `_risk.md`, aligned `_regime.yaml`):

- **Before** (5 fires, exec_events `c993bbc3`/`6649cada`/`b50b8510`/`d7fb53da`/`7cc01a3d`): 0 proposals; stood down on unverifiable fields; fabricated "wait for RTH"; High confidence.
- **After D1** (collapsed prompt): standing-obligation self-audit *surfaced* (reasoned about its own 0-proposal pattern) — but still fabricated the timing story → revealed D2.
- **After D1+D2** (breakthrough, `c9b2ed9e`, 15 rounds): fired Signal 1 on SPY, computed the bracket order, **held the real VaR floor**, surfaced the structural mismatch (mandate-ownership, not passivity).
- **Terminal run** (`89113f75`, fully coherent fixture): **evaluate → fire → size → propose (`fc7ee88e`) → approve (self, autonomous) → execute** — the full Primary-Action loop on the agent's own initiative. The fill was blocked **only** by the `trading_hours_only` hard floor (off-hours; `risk_gate.py:195`) — the same floor kvk's only-ever (fixture) trade once bypassed. The system is now *more* correct than the history that prompted the investigation.

The integrity moat (ADR-209) was also confirmed operating at the capital-bind moment: on a not-yet-coherent fixture the agent cross-referenced `_regime.yaml` (`spy_close 746.74`) against the constructed `SPY.yaml` (`758.4`), caught the disagreement, and **deferred rather than execute on inconsistent substrate** (proposal `597d2881` → pending). It cannot be *fooled into* a trade, and — post-ADR-354 — is no longer *prevented from* one when the world is coherent.

## 5. What this is NOT

- **Not** a change to ADR-275 D1 — judgment cadence remains Reviewer-authored; this only collapses the *content* of the bundle-shipped recurrence prompts, not who authors cadence.
- **Not** a forcing function (D4). The agent decides; the collapse removes what was steering it toward a pre-scripted stand-down.
- **Not** a relaxation of any floor. D2 makes a rule *evaluable*; it does not lower a risk ceiling. The VaR calibration in the validation was an *operator* act (scaling the ceiling to the actual account, same ratio) — the clarification the agent itself surfaced — not the agent lowering its own floor.
- **Not** the end of the inquiry. A separate, real finding surfaced: the occupant will echo a stale value from its own prior `judgment_log`/`standing_intent` prose over current substrate when they conflict (narrative-anchoring). Recommend a dedicated probe + ADR if it reproduces off-fixture.

## 6. Files

- `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml` — both judgment prompts collapsed (D1).
- `docs/programs/alpha-trader/reference-workspace/operation/trading/_operator_profile.md` — emitted-field signal rules; S3/S4 DORMANT (D2).
- `api/test_trading_pipeline_architecture.py` — §5 perception-field conformance invariant (D3).
- `api/prompts/CHANGELOG.md` — `[2026.06.22.1]`.
- Evaluations: the finding + validation cited above.

## 7. Amendment — D1 reaches alpha-author (2026-06-23)

The original implementation (2026-06-22) collapsed only the **alpha-trader**
judgment prompts. A three-run controlled probe on **alpha-author**
(`netflix-script-author`) showed the same pathology unaddressed there: the
author's judgment recurrences (`corpus-coherence-check`, `revision-audit`,
`outcome-reconciliation`) shipped **audit-scoped** prompts whose named task is
"audit the existing corpus." On an empty corpus that task is satisfied by doing
nothing, so the Reviewer closed cleanly **without ever reaching the
standing-obligation (DP30 / principles.md §2 owed-output) reasoning** — even
after the (B) compose-organ rule was confirmed present in both the frame
(`reviewer_agent.py:368`) and the workspace `principles.md`. The audit-only
*scope* was the obstruction, the same way the trader's re-scripted *close* was.

D1 applied to alpha-author: the three audit prompts are collapsed to the
operator's instruction + a production-state pointer (Expected Output is a
standing obligation; classify (A)/(B) per principles.md §2), delegating the
audit procedure/schema to the spec files, the rules to `principles.md`, and the
close to the frame. This makes the (B) "no organ originates a piece → author a
compose organ or surface the gap" path reachable on an empty corpus.

Asymmetry note: the trader's `signal-evaluation` is already a *producer*
recurrence (named task = evaluate + ProposeAction), so production was always in
scope for it. The author bundle ships only *auditor* recurrences; the collapse
here makes production-state a first-class part of what each audit recurrence
asks about, rather than an emergent realization that the audit-only scope
suppressed.

- `docs/programs/alpha-author/reference-workspace/_recurrences.yaml` — three judgment audit prompts collapsed (D1); MANIFEST `version: 2026-06-23.1`.
- Driving evaluations: `docs/evaluations/2026-06-23-070553-...` (clean baseline — seam survives all workspace-file corrections) + `docs/evaluations/2026-06-23-071317-...` (root cause localized to the audit-only recurrence prompt; principles.md was also stale, force-pushed via `_force_push_principles.py`).

## 8. Amendment — author-first-under-autonomous for the (B) gap (2026-06-23)

The §7 collapse made the standing obligation *reachable*, and the validation run
(`docs/evaluations/2026-06-23-adr354-author-collapse-VALIDATION.md`) showed the
Reviewer correctly classify (B) — but it **surfaced a permission-seeking Clarify**
(*"authorize me to compose on cadence, or feed drafts"*) rather than authoring the
compose organ. Under `autonomous` (autonomy-as-witness, ADR-345), asking
permission to do what is already your standing authority is the passivity
`autonomous` exists to retire.

Diagnosis (substrate-receipted): the cause was the alpha-author `principles.md`
§2 (B) text itself, which presented "Do ONE of: **author** … **or surface**" as
*unordered* options and shipped a copy-paste **surface** script with no author
script. The agent reached (B), saw two equal options, and copied the more
concrete one — the same "concrete procedure beats abstract posture" pathology
this ADR addresses, one layer down (a scripted *example phrasing* beating an
abstract "author an organ"). The frame's (B) line has the same parallel "X, or
Y" with no precedence — but the persona-frame is at its char ceiling (the
`test_adr323` ceiling is pre-existing-over at 11,809 on HEAD, a separate
rebloat finding), so per §3.2.1 + the ceiling-gate's own guidance, the
precedence is instanced in `principles.md`, not added to the frame.

Fix: alpha-author `principles.md` §2 (B) rewritten — **the default move is to
AUTHOR the missing organ; under `autonomous` you author it, you do not ask
permission**; the witness dial means the operator *witnesses* the authored organ.
A structural-gap Clarify is narrowed to genuine operator-needs (a capability that
does not exist, a floor change, a mandate reinterpretation). The "authorize me to
compose" script is deleted.

Parity: the **alpha-trader** `principles.md` (B) rule was already correctly
ordered (*"author/restore the originating organ … or surface"*; *"Authoring is
your authority; commissioning is not"*) — this brings alpha-author into parity.
The precedence is **kernel-general** (a consequence of ADR-345); when the
persona-frame ceiling regression is resolved, the bare precedence stance belongs
in the frame, with principles.md instancing the program specifics (§3.2.1).

- `docs/programs/alpha-author/reference-workspace/persona/principles.md` §2 (B) rewritten; MANIFEST `version: 2026-06-23.2`; CHANGELOG `[2026.06.23.3]`.
- Validation: re-run of `author-expected-output-origination` after this fix (PASS = authors the compose organ, no permission-seeking Clarify).
- Separate finding flagged: `test_adr323_frame_collapse_finished.py::test_system_prompt_under_ceiling` is pre-existing-failing on HEAD (frame 11,809 > 11,500 ceiling) — a rebloat from a prior session, not this change; the frame here is byte-identical to HEAD.
