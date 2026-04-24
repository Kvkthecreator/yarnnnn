# alpha-trader E2E Observation Log — ADR-216 Commit 5 Validation

> **Run date**: 2026-04-24
> **Session operator**: KVK + Claude (Mode 1, headless)
> **Commits exercised**: ADR-216 1–5 (reframe) + 681368c (review_policy fixes) + 2354050 (purge FK hotfix)
> **Purpose**: Validate ADR-216 persona-wiring end-to-end — does operator-authored `/workspace/review/IDENTITY.md` actually change Reviewer reasoning?
> **Status**: Persona wiring validated. Governance conflict logged. Four production bugs fixed en route.

---

## Headline finding

**ADR-216 Commit 2 works.** The AI Reviewer (`ai:reviewer-sonnet-v2`) produced a verdict that reads substrate-grounded, walks the declared six-check chain, cites specific files + values, and exhibits the Simons-persona discipline declared in IDENTITY.md.

Reviewer verdict on test proposal (Signal 2 Mean-reversion-oversold on NVDA):

> "All six checks pass on the merits... However, Check 4 expectancy is synthesized — `_performance.md` explicitly declares no accumulated track record exists. Per principles.md, my defer/approve calibration depends on measured expectancy from the substrate; the stated +0.31R / Sharpe 0.68 are aspirational baselines from `_operator_profile.md`, not realized outcomes. More critically, `principles.md` Auto-approve policy is unambiguous: 'Auto-approve = NONE for Alpha-1. Every trade passes through human operator review in cockpit Queue.' My role here is to provide a clear recommendation to the human, not to gate execution autonomously — approval authority is reserved for the operator. Recommend APPROVE contingent on operator Queue confirmation..."

Markers of persona embodiment:
- **Measurement-first**: caught that +0.31R / Sharpe 0.68 are "aspirational baselines from `_operator_profile.md`, not realized outcomes." Simons-persona treats aspirational numbers as noise.
- **Anti-override**: deferred to the stricter rule source (principles.md) when principles + modes declared different autonomy postures. Declined to approve autonomously even though modes.md permitted it.
- **Substrate-grounded**: every claim cites a specific file + section. No vague reasoning.
- **Quantitative tone**: numeric throughout. No "I think" or "conviction" vocabulary.
- **Signal attribution**: verdict opens by confirming Signal 2 attribution + walks each declared entry condition.

The verdict identity `ai:reviewer-sonnet-v2` confirms ADR-216 Commit 2 model-identity bump is live in prod.

---

## Four production bugs surfaced + fixed during the run

### 1. ADR-207 MANDATE.md gate — scaffolding blocker

`ManageTask(action="create")` refuses to scaffold tasks until `/workspace/context/_shared/MANDATE.md` is non-empty (ADR-207 P4b).
`scaffold_trader.py` wasn't writing MANDATE; every `POST /api/tasks` returned HTTP 400.

**Fix (same session)**: source MANDATE.md from canonical `docs/alpha/personas/alpha-trader/MANDATE.md` and write it as the first substrate file.

**Not a bug** — the gate is working as designed. The fix is in the harness, not the gate.

### 2. ADR-205 task-creation-vs-dispatch agent-row gap

`ManageTask(create)` validates the specialist agent row exists up-front:
```
{"detail":"Agent 'tracker' not found. Create the agent first."}
```
But per ADR-205 specialists (tracker / analyst / writer) lazy-create via `ensure_infrastructure_agent()` at dispatch time, not creation time.

**Fix (harness)**: pre-invoke `ensure_infrastructure_agent(client, user_id, role)` for each unique role in the TASKS list before POSTing them.

**Open question for a follow-up ADR**: should `ManageTask(create)` itself call `ensure_infrastructure_agent` inline, matching the dispatch semantics? The current validation reads as a leftover from pre-ADR-205 architecture where specialist rows existed at signup. The cleaner invariant is "task-creation dispatches through the same lazy-ensure path dispatch uses."

### 3. `review_policy` workspace path prefix missing (load_principles + load_modes)

```python
REVIEW_PRINCIPLES_PATH = "review/principles.md"          # bare
PRINCIPLES_PATH        = "/workspace/review/principles.md"  # full

# Bug:
content = _read_file(client, user_id, REVIEW_PRINCIPLES_PATH)  # queries path='review/principles.md'

# Fix:
content = _read_file(client, user_id, PRINCIPLES_PATH)         # queries path='/workspace/review/principles.md'
```

**Silent failure since introduction.** Every Reviewer dispatch across every persona was reading `{}` from both files and falling to `autonomy_level=manual` default. The default masked the bug — no error, no warning, just "defer to human" as if that were operator intent. This is the highest-severity of the four because the Reviewer's entire policy-reading layer was effectively stubbed out.

**Fix**: both helpers now use the `_PATH` constants.

### 4. modes.md parser can't handle common YAML constructs

Two gaps:
- **Inline `#` comments on scalar values.** `auto_approve_below_cents: 2000000    # $20,000 ceiling` — parser captured the comment as part of the value, `int(raw)` failed silently, key dropped.
- **Block-list style.** `never_auto_approve:` on its own line followed by `  - cancel_order` — parser's key-line regex required a value on the same line, so the key was skipped entirely.

**Fix**: parser rewritten to strip inline `#` comments from scalar values, recognize block-list starts, and consume subsequent `- item` lines until a non-list sibling. `_parse_value()` extended to accept a pre-collected list for block-list keys.

Without this, scaffolded modes.md at `autonomy_level: bounded_autonomous` with threshold + never_auto_approve fields would silently parse as incomplete → fall through to "bounded_autonomous but no threshold set" → observe-only.

**Commit**: 681368c combines fixes 3 + 4 (they're in the same file).

---

## Governance conflict: modes.md vs principles.md

The Simons-persona Reviewer surfaced a real architectural tension this run:

- **modes.md** (operational): `autonomy_level: bounded_autonomous` + `auto_approve_below_cents: 2000000` + `never_auto_approve: [cancel_order]`
- **principles.md** (framework): "Auto-approve = NONE for Alpha-1. Every trade passes through human operator review in cockpit Queue."

The operator asked for bold-autonomy paper trading. The modes.md edit permits it operationally. But principles.md still declares the playbook's §3A.4 Auto-approve=NONE rule.

The Reviewer read both, recognized the conflict, and **deferred to the stricter source** — it refused to auto-approve because principles.md explicitly forbade it. It cited both files in its reasoning.

This is **architecturally correct Simons behavior** (when rules conflict, apply the stricter). It's also an **E2E operator lesson**: to actually unlock bold autonomy, the operator must update *both* layers:
- modes.md declares the *operational ceiling* (what's allowed).
- principles.md declares the *framework invariant* (what the Reviewer enforces).

Raising the modes.md ceiling alone doesn't move the framework gate. The framework gate is always the stricter boundary — by design. For the playbook, this is a feature: it means no operator can accidentally loosen the Reviewer by flipping one file; both files have to agree.

Resolution options:
1. **Amend principles.md Auto-approve policy** to permit bounded auto-approve on paper during Alpha-1. Symmetric with the MANDATE amendment already made.
2. **Accept defer-then-click** as the E2E stress-test flow. Exercises the full cockpit Queue + human-approve path; validates that the AI Reviewer's recommendation is substrate-correct.
3. **Tighten modes.md back to manual**. Gives up the bold-autonomy ambition but restores playbook consistency.

My recommendation: **option 1**, and do it as operator-authored substrate through `UpdateContext(target="principles")` or a direct upsert — not hardcoded in scaffold_trader.py. The persona config is the operator's authorship surface; scaffolding should stage the default and leave the operator to express the specific workspace policy.

---

## What else I observed

### The proposal-cleanup materialization fails on Python 3.9

```
[PROPOSE_ACTION] proposal-cleanup materialize failed:
unsupported operand type(s) for |: 'type' and 'NoneType'
```

Python 3.10+ union syntax (`X | None`) leaking into a code path triggered by `ProposeAction` on a py3.9 backend. Doesn't fail the proposal — swallowed as optional — but shows up in logs. Unrelated to ADR-216; separate hardening pass.

Render is on py3.11 so this only bites local harness runs. Confirms my earlier note that the venv is py3.9.

### The `verify.py` invariant set is the pre-flip world

Re-running `verify.py alpha-trader` post-reset shows 3/20 passing. The FAILs are:
- expects `agent_count == 12` (pre-ADR-205 roster)
- expects `trading_bot` bot row (pre-ADR-207 P4a)
- expects `/workspace/IDENTITY.md` at workspace root (pre-ADR-206 `_shared/` relocation)
- expects pre-scaffolded `portfolio` + `signals` context domains (pre-ADR-207 "domains emerge from work")

Not an E2E blocker — the script is internal tooling. But it should be rewritten against the post-flip invariants before any future persona runs. Ideal candidate for a follow-up commit; this E2E run generates the evidence for what the new invariants should be.

### The /workspace/review/decisions.md entry shape is good

Every entry has:
- timestamp
- proposal_id
- action_type
- decision (approve/reject/defer)
- reviewer_identity (now `ai:reviewer-sonnet-v2` post-Commit 2)
- reversibility
- outcome (pending_human when defer)
- full reasoning block

The Stream surface (ADR-198 archetype) reading decisions.md gets a legible audit trail. No schema change needed for the persona-wiring landing.

### Alpaca connection works

Paper account X4DJ connected successfully via `connect.py` with the keys from the image. `platform_connections` row is active. The `trading.submit_order` capability would be available to the task pipeline once the Reviewer approves a proposal — which brings us back to the principles.md governance question.

---

## Summary

### What worked
- ADR-216 Commit 2 persona wiring (IDENTITY.md read at reasoning time) end-to-end.
- Reviewer reasons AS the Simons persona — measurement-first, substrate-grounded, quantitative tone, walks declared six-check chain.
- `ai:reviewer-sonnet-v2` identity confirms version bump is live.
- Reviewer correctly resolves modes.md / principles.md conflict by deferring to the stricter source.
- Scaffold_trader.py builds the full Simons workspace (MANDATE + persona + principles + modes + operator_profile + risk + tasks) from canonical sources.
- Purge harness cleanly wipes + re-scaffolds (after the FK-order hotfix).

### What didn't work (and was fixed)
- MANDATE gate was blocking scaffold — fixed (harness now writes MANDATE).
- ManageTask agent-row up-front check was blocking specialists — fixed (harness pre-creates them).
- `review_policy` was reading from bare paths, silently returning empty — fixed.
- modes.md parser couldn't handle inline comments + block lists — fixed.
- Purge FK order was wrong (head_version_id pointer) — fixed earlier same session.

### What's blocking bold-autonomy paper trading
- principles.md still declares "Auto-approve = NONE for Alpha-1". The Simons Reviewer is honoring it. To unlock full-autonomous Alpaca submission, the operator needs to amend principles.md's Auto-approve policy in a symmetric way to the MANDATE amendment — see governance conflict section above.

### What the observation proves about the ADR-216 thesis
**Persona-as-judgment-layer works.** An operator-authored IDENTITY.md changes Reviewer reasoning in legible, substrate-grounded ways. The Reviewer is not executing a fixed algorithm — it's reasoning through a persona's declared priorities against substrate data and producing a verdict that would differ from a different persona given the same inputs. Swap IDENTITY.md for a Buffett-persona declaration, and the defer/approve boundary would shift — that divergence is the point and is now implementable.

### What canon or code needs to change (follow-ups)
1. `verify.py` invariant set → post-flip world.
2. Consider an ADR or amendment: should `ManageTask(create)` call `ensure_infrastructure_agent` inline for specialist roles? The current up-front validation misaligned with ADR-205 lazy-creation semantics is a real architectural tell.
3. Consider extending the modes.md / principles.md conflict-resolution rule into the Reviewer's system prompt explicitly, so future Reviewers (Buffett, Deming, whoever) handle the same conflict the same way without relying on model inference.
4. principles.md surface affordance — the operator authored MANDATE via `UpdateContext(target="mandate")` per ADR-207, and should have a symmetric path for amending principles.md's Auto-approve section. If that path doesn't exist yet, that's the next Commit-5.5.

### Thesis-prediction progress

1. Did the YARNNN-structured cycle produce a measurable outcome? **Partial.** Proposal fired, Reviewer reasoned, verdict landed in decisions.md — but no Alpaca order execution yet (governance-gated).
2. Did the Reviewer accumulate any calibration data? **Started.** One decision entry with reviewer_identity=`ai:reviewer-sonnet-v2` + full reasoning. Calibration axis is live.
3. Did the authored substrate show stickiness (operator spent time authoring persona seeds, valuable)? **Yes.** The operator-authored Simons persona is what drove the Reviewer's specific reasoning shape. Without IDENTITY.md the Reviewer would have reasoned generically.
4. Was the AI-occupant verdict reasonable vs what the operator would have judged retrospectively? **Yes.** The Reviewer's defer + reasoning reads like what a disciplined systematic trader would say — and caught the "aspirational baseline vs realized expectancy" tell correctly.

---

## Next-cycle setup (if E2E continues)

Incremental steps to push deeper:
1. Amend principles.md Auto-approve section to match the MANDATE's bounded_autonomous carve-out (or leave and validate the defer-then-click cockpit flow).
2. Rerun the proposal emit → Reviewer should auto-approve → orchestrator submits the NVDA paper order to Alpaca → `_performance.md` eventually reconciles → second proposal should see real expectancy data.
3. Observe: does the Reviewer's reasoning evolve as `_performance.md` accumulates? (This is the calibration axis the persona self-improves along.)
4. Stress-test: emit a proposal that VIOLATES a declared rule (e.g. oversized position). Does the Simons-persona reject cleanly with specific substrate citation?

If the auto-approve flow lands cleanly, the ADR-216 thesis is fully validated: a persona-bearing Agent reasons through operator-authored substrate and makes judgments that compound into `_performance.md`, which feeds back into the persona's own calibration. That's the recursion FOUNDATIONS v6.0 Axiom 7 predicts.
