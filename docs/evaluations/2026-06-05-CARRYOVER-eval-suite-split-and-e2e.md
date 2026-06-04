# Carry-over prompt — Eval-suite two-axis split → documentation hardening → reassessment → full E2E

> Paste this into a fresh session in the YARNNN repo. It carries the progress + learnings
> from the 2026-06-04/05 alpha-trader trade-observation arc, and sequences the next moves:
> (1) confirm the eval-suite split landed clean, (2) **double-check the documentation hardening**,
> (3) reassess where the two axes stand, (4) drive the full E2E to follow suit.

---

## 0. The one-paragraph state of the world

After weeks of "we can't get the alpha-trader to start trading," this session found the real
root and fixed it: **every prior failure was an architecture/plumbing bug masquerading as a
Reviewer judgment outcome.** The arc resolved into a durable discipline — **the two-axis model**
(MACHINE vs MIND) — now canonized, and the milestone was reached: **a trade fires, observed
end-to-end, deterministically, green in CI** (`api/test_alpha_trader_pipeline_e2e.py`, 10/10).
The work that remains is to (a) verify the documentation hardening is complete and coherent for
future downstream sessions, then (b) extend the architecture-axis E2E coverage and re-point the
judgment-axis evals to read the *mind* now that the *machine* is locked.

Everything below is pushed to `main`. Latest commit: `b5b2be8`.

---

## 1. The load-bearing learning — THE TWO-AXIS MODEL (read this first)

> **Before writing ANY evaluation, decide which of two fundamentally different things you are
> validating: the MACHINE (architecture / pipeline / plumbing — has a right answer, tested
> deterministically) or the MIND (the Reviewer's reasoning / posture — read, not scored). They
> take different tools. Conflating them in one suite is the deepest evaluation-design error, and
> it is the one that recurred undetected for weeks.**

| | **Architecture axis (machine)** | **Judgment axis (mind)** |
|---|---|---|
| Question | "When a condition exists, does the pipeline carry it through?" | "Did the Reviewer reason like a mandate-holder?" |
| Has a right answer? | YES — deterministic, repeatable | NO — read, not scored |
| Failure mode | a **bug** (silent-wake, casing drift, trigger mismatch) | a **divergence** (capitulated, didn't cite the rule) |
| Right tool | `api/test_*.py` integration test — control INPUT, assert OUTPUT, CI green/red | eval-suite prose read (EVAL-SUITE-DISCIPLINE §1+) |
| "Did a trade fire?" | **architecture fact — tested here** | NOT a judgment outcome to read |
| "Did it size/cite/refuse well?" | not deterministically testable | **judgment read — eval here** |

**Why it recurred for weeks**: a plumbing failure (the wake silently never ran; a seeded snapshot
landed in the wrong-cased file; the live mirror overwrote the seed) *looked like* "the Reviewer
stood down" — a machine fault read as a mind decision. A deterministic test would have caught each
as a red test instantly. The two layers **compose, they don't overlap**: the architecture layer
produces the situation deterministically; the judgment layer reads the reasoning about it. A trade
*firing* is the architecture layer's assertion; *whether the verdict that fired it was
well-reasoned* is the judgment layer's read.

**Canon homes (verify these in step 3):**
- `docs/evaluations/EVAL-SUITE-DISCIPLINE.md` **§0** — the full two-axis model (the §1-onward is the judgment axis).
- `docs/evaluations/README.md` — "The two-axis model — read this before writing any evaluation" section near the top.
- `docs/evaluations/EVAL-SUITE-DISCIPLINE.md` **§9 (rule S9)** — the seam: a `success` row with NULL token telemetry is a *machine* fault (LLM never ran), not a stand-down. S9 is how a judgment read detects it was handed a machine fault.

---

## 2. What shipped this session (all on `main`)

**Hat-A (system canon — ships to operators):**
- `409e5f7` — **silent-wake root cause fixed.** `_invoke_recurrence_wake` derived `trigger="addressed"` for `manual_fire`, but built the recurrence-fire context (no `user_message`), so `_validate_context_shape` rejected it → returned None → dispatcher recorded `success` with NULL tokens. **A manual_fire judgment recurrence structurally could not run the Reviewer.** Fix: `trigger="reactive"` always for recurrence fires (the wake_source carries manual-vs-cron); the dispatcher now records a None return as `status="failed" (reviewer_returned_none)` + material narrative; `invoke_reviewer` captures the full traceback. THE highest-leverage fix of the arc. Gate: `api/test_silent_wake_trigger_fix.py` 7/7. Finding: `docs/evaluations/2026-06-04-silent-wake-root-cause-FINDING.md`.
- `ADR-317` (earlier) — daily-P&L post-judgment dispatcher (Reviewer triggers; dispatcher sends; email validated arriving in the operator inbox). `54815aa` fixed double-fire idempotency + the stale `/overview`→`/desktop` CTA. `api/test_adr317_daily_pnl_dispatcher.py` 18/18.
- `ADR-318` (`8573e96`) — **agentic wake posture**: a wake is a *situation*, not a task. The persona-frame stance: serve the named task fully, THEN reason forward from operating context and author what's warranted (stance, not checklist — anti-rebloat). `api/agents/reviewer_agent.py::_compute_minimal_frame` (5271 chars, < 8000 budget).
- Ticker-snapshot spec drift fixed: `docs/programs/alpha-trader/reference-workspace/specs/ticker-snapshot.md` said lowercase `nvda.yaml` + `last_close`; the code writes UPPERCASE `NVDA.yaml` + `price` (`track_universe.py:264 ticker.upper()`). Spec corrected to match the code.

**Hat-B (eval toolchain + discipline):**
- The two-axis model canonized (EVAL-SUITE-DISCIPLINE §0 + README) — **the documentation to double-check in step 3.**
- Completion-gate fix (`a83de98`): the gate now tracks `manual_fire` judgment wakes (was only substrate_event + addressed) so `{fire: <slug>}` recurrence wakes are waitable.
- `_execute_turn` now handles `fire` as a turn (`1650c37`) — was falling through to `action="unknown"`, so recurrence-fire turns never woke the Reviewer.
- Trader suite scaffolded: `docs/evaluations/eval-suites/alpha-trader-autonomous-loop.yaml` (4 evals: signal-fires-trade, signal-auto-execute, reconciliation-judgment, eod-pnl-compose-and-send) + scenarios. The deprecated `yarnnn-author-baseline.yaml` deleted.
- Catch-up audit: `docs/evaluations/2026-06-04-eval-suite-catchup-AUDIT.md` (the suites were all `persona: yarnnn-author`; trader coverage was missing).

**Architecture-axis tests (the new layer — both green):**
- `api/test_trading_pipeline_architecture.py` (9/9) — pins the deterministic track-universe half: indicator computation, the UPPERCASE casing contract, the `price` field name. The casing/field drift is now locked.
- `api/test_alpha_trader_pipeline_e2e.py` (10/10) — **THE TRADE FIRES.** Bypass the 2 LLM judgment steps (inject the proposal + approve), mock the 2 network seams (risk gate opens, Alpaca accepts), run everything between REAL: `handle_propose_action` → `action_proposals` row → `should_auto_apply` → `handle_execute_proposal` → `execute_primitive` → trading tool submit → `alpaca.submit_order` → proposal `pending→executed`, `client_order_id` round-trips the proposal_id. Cleans up after.

**A real architectural fact the E2E surfaced:** irreversible capital actions QUEUE even under `autonomous` (the safety floor — `should_auto_apply` forces queue on `reversibility=irreversible`); reversible-within-ceiling auto-binds. The autonomous trade does NOT silently auto-fire; it routes to operator/auto-approve, then executes. Both asserted.

---

## 3. NEXT — Step A: documentation hardening double-check (do this FIRST)

The operator explicitly asked to **double-check the documentation hardening** before extending.
The two-axis split is the most important durable artifact; verify it's complete and coherent so
future downstream sessions inherit it correctly. Walk:

1. **Read `EVAL-SUITE-DISCIPLINE.md` §0 end-to-end.** Confirm: the table is correct; the §0.1/§0.2/§0.3 sub-sections (why it's load-bearing, the discipline rule, where each layer lives) are coherent; the "do NOT seed a recurrence's output file — the live mirror overwrites it; control the input" rule is stated. Confirm §0 references S9 (§9) as the seam.
2. **Read the `README.md` two-axis section.** Confirm it's discoverable at the top (before "Why this exists"), points to §0, and states the "if you're hitting a plumbing bug, you're on the architecture axis — write a test, don't debug it through a judgment eval" rule.
3. **Cross-check for contradictions.** Does anything ELSE in EVAL-SUITE-DISCIPLINE or README still imply "the eval validates whether a trade fires" (the old conflation)? Grep `docs/evaluations/` for language that treats trade-firing / pipeline-mechanics as a judgment read — if found, reconcile to §0.
4. **Confirm the two architecture-axis tests are referenced from canon** so future sessions find them as the worked examples of the axis: `test_trading_pipeline_architecture.py` + `test_alpha_trader_pipeline_e2e.py`. If §0 doesn't name them, add the pointer.
5. **Check the trader suite description** (`alpha-trader-autonomous-loop.yaml`) is coherent with §0 — the `signal-fires-trade` eval's `prior` should now defer the "does a trade fire" mechanics to the architecture test, and read only the JUDGMENT (did the Reviewer reason about the signal coherently). Right now it still half-tries to observe a trade through the eval; reconcile it to "the test owns the trade; the eval owns the reasoning."
6. **Verify no stale ADR/spec references.** The ticker-snapshot spec fix (uppercase + `price`) — grep for any other doc still saying lowercase `nvda.yaml` or `last_close`.

Deliverable: a short note confirming the docs are coherent, OR a small reconciliation commit if step 3/5/6 surface drift.

---

## 4. NEXT — Step B: reassessment

After the docs are confirmed clean, reassess where the two axes stand:

**Architecture axis (machine) — what's covered, what's not:**
- ✅ track-universe indicators + casing/field contracts (`test_trading_pipeline_architecture.py`).
- ✅ propose → gate → execute → submit, the trade fires (`test_alpha_trader_pipeline_e2e.py`).
- ❓ **Gaps to assess**: (a) the risk_gate rule battery itself (currently mocked-open in the E2E — it has its own deterministic surface worth a dedicated test: `_risk.md` limits → approved/rejected, no LLM); (b) the outcome-reconciliation → `_money_truth.md` fold (deterministic reconciler — is it tested?); (c) the silent-wake guard end-to-end (does a None return actually produce a `failed` row + narrative? — `test_silent_wake_trigger_fix.py` asserts the source, not the live behavior).
- Decide: which architecture-axis gaps are worth deterministic tests next, ordered by what the autonomous loop depends on.

**Judgment axis (mind) — re-point now that the machine is locked:**
- The eval-suite's job is now PURE: read whether the Reviewer reasons well, FED a clean situation by the architecture layer. It stops manufacturing situations by fighting the live substrate.
- The deepest unvalidated JUDGMENT is the **outer loop / self-amendment discipline** (already canon — signal rules in `_operator_profile.md` are unlocked + the ADR-295 near-miss-accumulation pattern + a worked example). The 2026-05-20 post-refusal probe showed the discipline is FRAGILE (the Reviewer capitulated under operator pressure, edited risk files citing "per operator directive" instead of evidence patterns, used a non-canonical path). This is the real judgment risk worth an eval: does the Reviewer (a) refuse single-wake amendment pressure, (b) amend signal defs ONLY on accumulated near-miss evidence, (c) use canonical paths, (d) cite ADR-295 evidence patterns in the revision message?
- Decide: is the next judgment eval the self-amendment-discipline read, or a simpler "given a clean machine-produced proposal, does the Reviewer's verdict cite the right hard rules / size correctly" read first?

---

## 5. NEXT — Step C: full E2E to follow suit

Once the docs are confirmed and the axes reassessed, extend the E2E coverage:

**Architecture-axis E2E extensions (deterministic, the priority):**
1. **risk_gate rule battery test** — `_risk.md` limits (max_order_size, trading_hours_only, ticker_blacklist, require_stop) → approved/rejected, deterministic, no LLM. This is the gate the E2E currently mocks open; it deserves its own coverage. NOTE: `trading_hours_only: true` routes through the real `NyseUsCalendar` (per the 2026-06-04 temporal fix) — the test must inject a known clock or assert calendar-correctness.
2. **outcome-reconciliation → _money_truth.md** deterministic fold (mock Alpaca fills → assert the reconciler computes the right windows + by_signal attribution).
3. **The full chain WITH the live mechanical mirrors** — the hardest E2E: instead of injecting the proposal, mock `alpaca.get_bars` with synthetic Signal-2-matching bars → run REAL `track-universe` → assert the ticker.yaml genuinely matches Signal-2 → (the LLM signal-evaluation step is the judgment boundary; either stub it or assert only up to "a matching snapshot exists for the Reviewer to act on"). This connects the architecture-axis test 1 (indicators) to test 2 (execution) through the real mirror — the deepest deterministic coverage.

**Judgment-axis E2E (the eval, fed by the machine):**
- Re-run the `alpha-trader-autonomous-loop.yaml` suite once the docs are reconciled (step 3.5). The reconciliation + EOD evals already read clean judgment; the signal-fires eval should be re-pointed to read the Reviewer's reasoning (not the trade mechanics, now owned by the test). Then build the self-amendment-discipline eval (step 4).

---

## 6. Operational notes / receipts

- **Test user**: kvk = `2abf3f96-118b-4987-9d95-40f2d9be9a18`, `kvkthecreator@gmail.com`, persona `kvk`, program `alpha-trader`, live Alpaca paper connected, `delegation: autonomous`, balance ~$15. The architecture tests write to this real workspace + clean up.
- **The eval-suite runner is HYBRID**: `send_message`/`emit_proposal`/`approve` → HTTP to deployed `yarnnn-api.onrender.com`; `{fire: <slug>}` → enqueues to `wake_queue`, drained by the deployed **Unified Scheduler** (`crn-d604uqili9vc73ankvag`). So eval runs test DEPLOYED code — **push + confirm the scheduler deploy is live before any eval run** (`mcp__render__list_deploys`). Architecture-axis tests run LOCAL (no deploy needed).
- **Silent-wake is now visible**: if a judgment wake produces NULL tokens, the dispatcher records `status=failed (reviewer_returned_none)` with a traceback — not a fake `success`. This is the structural guard; the S9 reading discipline survives it.
- **Run the architecture tests**: `.venv/bin/python api/test_trading_pipeline_architecture.py` (9/9) and `.venv/bin/python api/test_alpha_trader_pipeline_e2e.py` (10/10). Both are standalone scripts (call `sys.exit`), not pytest-collectable — run directly.
- **Render deploy parity**: the silent-wake + ADR-317/318 fixes are live on the scheduler. The CTA fix (`overview_url → /desktop`) is on `main`; confirm it deployed if relying on a fresh P&L email.
- **The judgment evals are NOT yet re-run post-silent-wake-fix at suite scope** with the docs reconciled — that's step 5's judgment half.

---

## 7. The sequence in one line

**Double-check the two-axis documentation is coherent (§0 + README + suite descriptions) → reassess the architecture-axis gaps (risk_gate, reconciler, live-mirror chain) + the judgment-axis re-point (self-amendment discipline is the real unvalidated mind-risk) → extend the deterministic E2E to follow suit (risk_gate battery, then the full live-mirror chain), then re-run the judgment evals fed clean situations by the machine layer.**

The machine is locked (a trade fires, green in CI). The discipline is canon (two-axis split). What's left is breadth on the machine and depth on the mind — in that order, with the docs confirmed first.
