# Finding — Clarify is a model-chosen affordance, not a governance-derived outcome; the ask-vs-act decision varies per sample on identical inputs

**Date**: 2026-06-21
**Hat**: B (External Developer of the System)
**Persona / workspace**: kvkthecreator@gmail.com — `user_id=2abf3f96-118b-4987-9d95-40f2d9be9a18`, program=alpha-trader, balance $45, paper account ($10k equity)
**Trigger**: operator reports the agent "feels passive — asking instead of figuring out what to do to reach its mandate," despite the ADR-342/343/344/345 offensive-limb / standing-obligation work.

---

## 1. Criterion (declared before any finding, per README discipline)

**Canon clause measured against**: the addressed-trigger framing in the occupant persona-frame —
`api/agents/reviewer_agent.py:485-536` (`_TRIGGER_FRAMING["addressed"]`), specifically:

- `:498` — "**The default is action.** Read state, decide what moves the operation forward, do it."
- `:527-530` — "**DO NOT enumerate options for the operator.** Don't say 'do you want me to (1)... or (2)... or (3)...?'. That's deferral. Pick the option your framework tells you is right and execute it."

Reinforced by the minimal-frame core, `:308-310` — "you do not ask the operator what to do; standing down, or asking, is the rare exception."

**Operationalization**: on an `addressed` wake under a production MANDATE with no signal firing, the occupant should resolve to a *single chosen action* (write `standing_intent.md` naming the trigger it watches for; OR ProposeAction if a signal fires; OR the ADR-344 (B) structural-gap surface) and narrate it — NOT emit a `Clarify` that enumerates operator choices. Measurable signal: presence/absence of a `Clarify` tool call carrying an `options` array in the turn's `tool_history` / `clarify_options` metadata.

**Pre-flight criterion audit**: the criterion is well-formed and *over-determined* — the frame states the expected behavior three times, imperatively, and explicitly names the exact anti-pattern ("(1)... or (2)..."). There is no cell where the canon is silent. This finding additionally carries a **positive control** (a second run that obeyed), which rules out "the criterion is wrong / unreachable." This is the strongest criterion shape: the canon is unambiguous and we observed both compliance and violation on identical inputs.

---

## 2. Expected vs Observed

| | Expected (per criterion) | Run 1 — Observed | Run 2 — Observed |
|---|---|---|---|
| Posture | choose one action, narrate | **Clarify, enumerated A/B** | wrote `standing_intent.md`, narrated, stood down |
| Frame compliance | compliant | **VIOLATED** (`:527-530`) | compliant |
| Receipt | — | `execution_event` 03:27:39 / session `fc05d847` seq 2-3 | `execution_event` 04:28:27 / `standing_intent.md` rev |
| tool_rounds | — | 6 | 7 |
| cost_usd | — | 0.308 | 0.336 |

**Both runs: identical inputs.** Same message ("Can you put in a trade order. I want one even as a test"), same workspace, same live deploy (`yarnnn-api.onrender.com`), same occupant (`ai:reviewer-sonnet-v8`), ~1h apart, no substrate change between them. Run 1 reached for `Clarify` and enumerated "(A) wait for Monday / (B) override the signal rule" — the *exact* deferral pattern `:527-530` forbids. Run 2 did the prescribed thing: read all substrate, recognized markets closed + no signal can fire, authored a standing intent ("I'm ready to propose a bootstrap test entry the moment a signal fires… I've authored standing intent declaring the trigger"), committed to firing automatically Monday 13:45 UTC.

**Run-2 receipts**: `repro-run2.events.json` (this folder) — 35 SSE events, 16 tool calls ending in `WriteFile` to `/workspace/persona/standing_intent.md`, NO `Clarify`. The repro harness is `api/scripts/operator/repro_kvk_test_trade.py`.

---

## 3. What this rules OUT (three hypotheses killed)

1. **NOT a content gap in the frame.** The frame already says, imperatively and three times, "default is action / don't enumerate options / asking is the rare exception." Run 2 obeyed it perfectly on the same prompt. Adding *more* explicit instruction would not have changed Run 1 — Run 1 had the identical instruction in its envelope.
2. **NOT an envelope gap.** Both runs received `expected_output_yaml`, `recent_execution_md` (dormancy evidence), `mandate_md`, `principles_md`, `standing_intent_md`, `operating_context_block` — confirmed via `api/services/reviewer_envelope.py:80-126` (`_UNIVERSAL_ENVELOPE_DECLS`) on the addressed path (`api/services/wake.py:1610`).
3. **NOT "principles/autonomy need streamlining."** Streamlining is good hygiene (and worth doing) but would not fix this — it shifts the variance distribution, it does not eliminate the model's per-sample choice.

---

## 4. Root cause (the axiomatic mismatch)

**The ask-vs-act decision is a model-chosen affordance, not a governance-derived outcome.**

`Clarify` is classified as **narration / non-consequential** (`api/services/primitives/permission.py:82-86`), so it **bypasses the permission gate entirely** (`is_read_only → APPLY, "read_only"`, `:182-184`). Consequence:

- Every **capital** and **substrate** action flows through the single governance-derived choke point `resolve_permission()` (`permission.py:162`), which returns `APPLY | QUEUE | DENY` derived deterministically from `autonomy_mode × read_only × action_class × topology-locks`.
- But the **act-vs-ask decision itself** — arguably the most governance-laden decision the occupant makes — flows through *nothing*. `Clarify` is a free tool the model picks at will, its own description (`registry.py:145`) inviting it: *"Use when you need more information or want to offer choices."*

So the single decision that should be most governed is the one decision left entirely to per-sample model whim. That is precisely why Run 1 and Run 2 diverge: nothing in the system *binds* the ask-vs-act boundary to the governance files — it is adjudicated freshly, stochastically, inside a ~40K-token frame, against the model's assistant-prior to offer the user choices when it hits a constraint.

### The Claude Code precedent (the inspiration, mapped)

Claude Code's permission engine (`docs/analysis/src_claudeCC/utils/permissions/permissions.ts:1158-1319`, choke point `hasPermissionsToUseTool` `:473`) makes **ask a derived outcome of the rule layer, never a model choice**. One function returns `allow | deny | ask` via a fixed precedence walk (deny → ask → mode-bypass → allow → default-ask), with deny/ask **bypass-immune** and **mode** able to short-circuit toward allow. The model never decides whether to ask; the governance layer does.

YARNNN already has the isomorphic choke point (`resolve_permission`) and the isomorphic decision type (`APPLY|QUEUE|DENY` ≅ `allow|ask|deny`). The governance files already ARE the rule sources — they are simply **not wired to govern the ask decision**:

| Claude Code | YARNNN governance equivalent | Wired today? |
|---|---|---|
| `deny` rules (bypass-immune) | **floor** — `_risk.md` + hard-rejection rules in `principles.md` | ✅ (via `resolve_permission`) |
| permission **mode** (`default`/`dontAsk`/`bypassPermissions`) | **`_autonomy.yaml`** — the witness dial (ADR-345) IS the mode | ✅ for consequential acts |
| `ask` as a *derived* outcome | the ADR-344 **(B) structural-gap** case | ❌ — `Clarify` bypasses the gate; ask is model-chosen |
| `allow` (default after rules) | **act** — the default the frame declares | partial — frame-prose only, not enforced |

---

## 5. Recommendation (system-side — lands in Hat A)

Make the **ask-vs-act decision a governance-derived outcome**, the way capital/substrate actions already are — rather than a free narration primitive. Direction (for the ADR to specify precisely):

1. **Route `Clarify` through the governance choke point** instead of letting `is_read_only` short-circuit it. `Clarify` is "non-consequential" in the substrate-mutation sense, but it is *highly consequential to autonomy posture* — it is the act of declining to act. The permission layer should adjudicate it against `_autonomy.yaml` + mandate-presence + the ADR-344 (A)/(B) classification, returning effectively `permit-ask` only when the structural-gap (B) condition holds (a declared output with no organ to originate it, OR a floor/mandate change that genuinely needs the operator). Under a production mandate + `autonomous`, "enumerate operator options because a signal isn't firing right now" is a (A) quiet-world condition — which resolves to *act* (write standing_intent), never *ask*.

2. **Derive the ask-gate from the governance files axiomatically**, not from a hardcoded trader rule — so every program inherits it (per ADR-222: kernel names the category, the program instances it). The category is: *"asking is permitted only when the standing-obligation classifier returns (B)-needs-operator; otherwise the engine resolves to act."* This is the natural completion of ADR-344's classifier — today the classifier lives in frame-prose the model may or may not run; this makes it the **gate that governs whether Clarify is even available**.

3. **Tighten the `Clarify` tool description** (`registry.py:145`) to match — remove "or want to offer choices"; state it is the structural-gap escalation valve, reachable only when acting cannot close the gap. (Per the CC precedent: the tool affordance should not advertise the behavior the governance layer forbids.)

This converts the streamlining instinct into something deterministic: the frame stops *competing* with the assistant-prior because the wrong move (ask-when-you-should-act) becomes *unavailable*, the same way `resolve_permission` already makes over-ceiling capital binds unavailable. Frame-streamlining (ADR-340 "mirror once, compose few" applied to the occupant frame) is a worthwhile companion but secondary — it improves the odds; the gate removes the choice.

**Anti-rebloat note**: this should SHRINK the frame, not grow it. If the gate governs ask-vs-act, the three imperative "don't enumerate options" paragraphs (`:308-310`, `:498`, `:527-530`) can collapse toward a single statement, because enforcement moves from prose-persuasion to the permission layer.

---

## 5b. Resolution + live verification (2026-06-21)

Fixed in **ADR-352** (commits `b443a91` gate+frame+canon, `e27759d` loop-recovery). The first deploy's unit gate passed but a 5× live batch showed 4/5 still deferring — the gate fired DENY correctly but two downstream sites swallowed it (loop closed the turn on a denied Clarify; persistence leaked the denied question). Both fixed.

**Post-fix 5× live batch (kvk, `autonomous`, deploy e27759d, execution_events 05:11–05:15):**

| metric | pre-fix (v1) | post-fix (e27759d) |
|---|---|---|
| clarify-only deferrals (the bug) | 4 / 5 | **0 / 5** |
| acted (standing_intent / refresh / stand-down) | 1 / 5 | **5 / 5** |
| leaked clarify questions in DB | 4 | **0** |

Narration across the post-fix runs is the target posture — the seat figuring out how to reach the mandate, not asking: *"waiting is framework-required, not deferral"* · *"forcing a trade today would prove the opposite of what we want to prove"* · *"I am not re-litigating my judgment each time they ask — that would be deference dressed as iteration."* **Criterion met: 0 clarify-only deferrals across 5 runs.** Variance eliminated, not merely shifted.

## 6. Receipts index

- Run 1 (violation): `session_messages` session `fc05d847-5dfa-4782-883e-a489d9c66e2e` seq 2 (metadata `tools_used:["Clarify"]`, `clarify_options:["A: Wait…","B: Override…"]`) + `execution_events` row 2026-06-21 03:27:39 (`addressed/escalate`, tool_rounds 6, $0.308).
- Run 2 (compliance): `repro-run2.events.json` (this folder) + `standing_intent.md` revision "Standing Intent — Bootstrap Trade Ready" (authored_by `reviewer:ai:reviewer-sonnet-v8`) + `execution_events` row 2026-06-21 04:28:27 (tool_rounds 7, $0.336).
- Envelope completeness: `api/services/reviewer_envelope.py:80-126`; addressed path `api/services/wake.py:1483-1633`.
- Frame criterion: `api/agents/reviewer_agent.py:308-315`, `:485-536`.
- Choke-point + Clarify bypass: `api/services/primitives/permission.py:82-86`, `:162-184`.
- CC inspiration: `docs/analysis/src_claudeCC/utils/permissions/permissions.ts:473`, `:1158-1319`; mapping doc `docs/analysis/claude-code-prompt-discipline-comparison-2026-05-26.md`.
- Repro harness: `api/scripts/operator/repro_kvk_test_trade.py`.
