# ADR-352 — Ask-vs-Act as a Governance-Derived Outcome (Clarify joins the uniform gate)

**Status**: Implemented (2026-06-21)
**Dimensional classification**: **Mechanism** (Axiom 1 §4 — the gate) + **Identity** (Axiom 2 — the witness dial governs the seat's ask-vs-act stance)
**Extends**: ADR-307 (Unified Permission Taxonomy / DP23 — the one gate), ADR-344 (Standing Obligation / DP30 — the (A)/(B) classifier), ADR-345 (Autonomy-as-Witness — the delegation dial is the witness dial)
**Preserves**: ADR-209 (Authored Substrate), ADR-293 (governance/operational scoping), ADR-306 (persona-frame collapse — this SHRINKS the frame), ADR-318 (agentic-wake posture), FOUNDATIONS Axioms 1–9
**Driving evidence**: `docs/evaluations/2026-06-21-kvk-clarify-variance-ask-vs-act/findings.md`

---

## 1. Problem statement — asking is the one ungoverned decision

The operator (kvkthecreator, alpha-trader program, `autonomous` delegation) reported the Reviewer "feels passive — it asks me what to do instead of figuring out how to reach its mandate." We reproduced it with a substrate-receipted control:

- **Same message** ("Can you put in a trade order. I want one even as a test"), **same live workspace**, **same occupant** (`ai:reviewer-sonnet-v8`), **~1h apart**, **no substrate change between runs**.
- **Run 1**: `Clarify` enumerating "(A) wait for Monday / (B) override the signal rule" — the *exact* deferral pattern the persona-frame forbids at `reviewer_agent.py:527-530`.
- **Run 2** (repro): read all substrate, recognized markets closed + no signal can fire, **wrote `standing_intent.md`** committing to auto-fire when a signal fires, narrated, stood down. The prescribed behavior.

Two runs, identical inputs, opposite postures. The frame is **correct** and the occupant **disobeys it stochastically**. The variance is the bug — not a missing rule.

**Root cause.** Every *consequential* primitive (capital + substrate) flows through the one governance choke point — `resolve_permission()` (`permission.py:162`) — which returns `APPLY | QUEUE | DENY` (≅ Claude Code's `allow | ask | deny`) derived deterministically from `autonomy_mode × read_only × action_class × topology-locks`. But `Clarify` is classified **narration / non-consequential** (`permission.py:82-86`), so it **short-circuits the gate** (`is_read_only → APPLY`). The act-vs-ask decision — arguably the most autonomy-laden decision the seat makes (asking is the act of *declining to act*) — is the one decision left entirely to per-sample model whim, fought against the model's trained assistant-prior to offer the user choices when it hits a constraint.

So the single decision that should be most governed is the one decision the governance layer does not touch.

## 2. The axiom — asking is the inverse of binding-without-witness, so the witness dial governs it

ADR-345 reframed autonomy as the **witness dial**: it decides *which consequential beats the operator witnesses before they bind* — not *whether* the agent works. The agent always works the full job.

Asking-the-operator-to-choose-instead-of-acting is the **inverse** of binding-without-witness. It is the seat handing a decision back rather than taking it. Therefore the *same dial* that governs binding must govern asking:

- **`autonomous`** — the operator delegated the work. The seat acts; it does not bounce a choice back. Asking-to-choose is **not available**. The genuine escape valve survives: the **ADR-344 (B) structural gap** — "the operation as configured cannot produce what it owes" — is not "which option do you want," it is "the loop is broken and only you can fix it." That remains permitted.
- **`bounded` / `manual`** — the operator wants to witness. Asking is available; the witness wants the choice.

This makes **ask a derived outcome of the delegation dial**, kernel-universal (every program inherits it via `_autonomy.yaml`), the same way QUEUE/DENY already are. It is the **wake-time enforcement** of ADR-344's (A)/(B) classifier: today the classifier lives in frame-prose the model may or may not run; this moves the *availability of asking* into the gate, so a quiet-world (A) condition can no longer resolve to a Clarify.

This is the Claude Code precedent applied honestly (`docs/analysis/claude-code-prompt-discipline-comparison-2026-05-26.md`): in Claude Code `ask` is a derived outcome of the rule layer, **never a tool the model elects**. YARNNN already has the isomorphic engine and decision type; this wires the one remaining decision into it.

## 3. Decision

**D1 — `Clarify` becomes a gate-owned primitive; it is removed from `READ_ONLY_PRIMITIVES`.** It no longer short-circuits at `is_read_only`. It flows into `resolve_permission`, which derives the ask-permission from governance.

**D2 — The ask-gate derivation (kernel-universal, in `resolve_permission`).** For a Reviewer-authored `Clarify`:
- Load the workspace delegation (`load_autonomy` → `autonomy_for_domain(...)["delegation"]`).
- If delegation is **`bounded` or `manual`** → `APPLY` (`ask_permitted:witness_mode:{delegation}`). The operator wants to witness; asking is theirs to receive.
- If delegation is **`autonomous`**:
  - If the call carries **`structural_gap: true`** → `APPLY` (`ask_permitted:structural_gap`). This is the ADR-344 (B) escalation — a genuine "no organ can produce what I owe / a floor or mandate change only you can authorize" surface.
  - Otherwise → `DENY` (`ask_denied:autonomous_default_is_act`). The seat must act. The DENY message tells the occupant exactly that: under `autonomous` you do not enumerate options; pick the disciplined action your framework names and execute it; if you genuinely cannot produce what you owe, re-call Clarify with `structural_gap=true` naming the missing organ.
- Non-Reviewer callers (operator, headless, MCP) → `APPLY` (asking is scoped to the Reviewer seat, like the autonomy gate per ADR-293).

**D3 — `Clarify` gains an optional `structural_gap: bool` input.** It is the machine-checkable carrier of the ADR-344 (B) classification — the operator-decision-required escape valve. Default `false`. The occupant sets it only when surfacing a genuine structural/floor/mandate gap, never to enumerate operational options.

**D4 — The `Clarify` tool description is rewritten to match.** The permissive "use when you need more information or want to offer choices" (`registry.py:145`) — which actively advertised the forbidden behavior — is replaced with the escalation-valve framing: *Clarify surfaces a structural gap or a decision only the operator can make (a floor/mandate change, a missing capability). It is not for enumerating operational options; under a delegated mandate, pick the disciplined action and act.*

**D5 — The persona-frame SHRINKS (anti-rebloat; completes ADR-306).** Because the ask-vs-act boundary is now code-enforced, the three imperative anti-enumerate paragraphs collapse to a single sentence that points at the enforcement, consistent with `agent-composition.md` §3.2.1 ("Write authority + locks → code … No prose enumeration needed"). Specifically:
- `_TRIGGER_FRAMING["addressed"]` (`reviewer_agent.py:527-530`) "DO NOT enumerate options…" paragraph collapses to one clause.
- The minimal-frame "asking is the rare exception" sentence (`:308-310`) is retained (it is the assistant-prior correction — the irreducible sliver per §3.2.1 line 188) but trimmed of the now-redundant elaboration.

## 4. What this is NOT

- **Not a fourth gate outcome.** `Clarify` resolves to the existing `APPLY` / `DENY` — no new `PermissionDecision` value. (`QUEUE` is wrong: a denied ask is not a substrate write to enqueue. `DENY` reusing the existing error-with-guidance surface is exactly right — the occupant already understands a DENY result and reasons forward from it, as ADR-318 prescribes.)
- **Not a trader rule.** The derivation reads `_autonomy.yaml` (kernel-universal governance) + a generic `structural_gap` flag. No program noun. alpha-trader and alpha-author inherit it identically.
- **Not a frame addition.** It removes frame prose. The enforcement moves from persuasion to the gate.
- **Not autonomy-widening.** The seat could always act; this removes an *affordance to decline*. The floor is untouched; capital/substrate gating is unchanged.

## 5. Where it lands (agent-composition.md §3.2.1)

- **Enforcement → code** (`resolve_permission`): when asking is available is now a gate decision, not prose. §3.2.1's "When to Clarify vs decide → principles.md" line is amended: the *rule of judgment* (what makes a gap (B)-shaped) stays in `principles.md`; the *availability of asking* is now code-enforced (like write-locks), and the frame's anti-enumerate sliver shrinks to a pointer.
- **Stance → frame**: unchanged in kind — the "you are installed judgment, asking is the rare exception" principal-shift remains, trimmed.
- **(B)-classification rules → principles.md**: unchanged — both bundles already carry the §Standing-Obligation (A)/(B) classifier from ADR-344.

## 6. Risk + revert

- **Risk**: a legitimate operator-decision-required ask under `autonomous` gets DENY'd because the occupant didn't set `structural_gap`. Mitigation: the DENY message explicitly instructs the re-call with `structural_gap=true`; the occupant gets one cheap round to reclassify. This is strictly better than the status quo (a quiet-world Clarify that should never have fired).
- **Revert**: re-add `"Clarify"` to `READ_ONLY_PRIMITIVES` and drop the ask-gate branch. One-commit revertible. The frame trim is independently revertible from git history.

## 6b. Loop-recovery — the DENY must not be swallowed downstream (added after live batch)

The first deploy's unit gate passed but a 5× live batch (kvk, `autonomous`) showed 4/5 still ending in a Clarify deferral. The gate was firing DENY correctly; **two downstream sites swallowed it**:

- **Bug 1 (`reviewer_agent.py`)** — `invoke_reviewer` set `clarify_called_this_round = True` on *any* Clarify call, so a gate-DENIED Clarify still fired the "question surfaced → ReturnVerdict(stand_down)" nudge and closed the turn. Fix: gate the flag on `actions_taken[-1]["success"]` — a denied Clarify lets the loop continue so the seat reads the deny guidance and acts this same wake.
- **Bug 2 (`reviewer_chat_surfacing.py`)** — `surface_reviewer_actions` stamped `clarify_question`/`options` onto the persisted operator-facing message for *any* Clarify, so a DENIED Clarify's enumerated A/B question leaked to the operator as if it had been asked (the live SSE path at `wake.py:1660` already guarded on `success`; the persistence path did not). Fix: gate the question/options stamp on `success` — a blocked Clarify renders as a blocked action, not a surfaced question.

Lesson: a gate decision is only as good as the call sites that honor its result. The DENY result (`success=False`) must be respected by **every** consumer of the action record — loop-continuation logic AND operator surfacing. Always-on `[ASK-GATE]` decision telemetry (`permission.py::_resolve_ask_gate` + the log line) was added so a live eval reads the gate decision directly rather than inferring it from downstream surfacing.

## 7. Verification

- Regression gate: `api/test_adr352_ask_gate.py` — asserts (a) `Clarify` not in `READ_ONLY_PRIMITIVES`, (b) autonomous + no structural_gap → DENY, (c) autonomous + structural_gap → APPLY, (d) bounded/manual → APPLY, (e) non-reviewer caller → APPLY.
- Live behavioral verification: re-run the kvk repro (`api/scripts/operator/repro_kvk_test_trade.py`) post-deploy; expected: NO enumerated-option Clarify; the occupant acts (standing_intent or proposal) or surfaces a true structural gap. Recorded in the driving evaluation folder.
