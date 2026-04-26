# E2E Validation — alpha-trader paper loop, full circuit exercised

> **Date**: 2026-04-26
> **Persona**: alpha-trader (`user_id=2be30ac5-b3cf-46b1-aeb8-af39cd351af4`)
> **Posture**: bounded_autonomous trading, $20K ceiling (per AUTONOMY.md / MANDATE §40)
> **Scope**: First full E2E exercise of substrate → pipeline → proposal → AI Reviewer → decision under post-ADR-219 system state
> **Operator (this run)**: Claude (builder seat — authored repair substrate, did not impersonate the persona)

---

## Outcome: full loop closed end-to-end, AI Reviewer correctly deferred

The complete circuit is alive. Substrate scaffolding writes through ADR-209 authored
revisions. Pipeline executes. Sonnet-class agents produce real artifacts. Proposals
emit. AI Reviewer (Sonnet v5) runs the full Simons 6-check framework against
`principles.md`. Decision lands as an authored-substrate revision in
`/workspace/review/decisions.md`. The narrowing condition that says "thin track
record → defer" fired correctly on the synthetic Signal-2 AAPL proposal.

**The autonomy ladder behaved as designed**: bounded_autonomous gives the
Reviewer authority to auto-execute, but `principles.md` narrows that authority
on Check 4 when `_performance.md` is empty. The Reviewer chose `defer` and
routed to the human Queue. ADR-217 D4 invariant ("principles.md narrows but
never widens") holds in production.

No paper order fired this run. Expected — the substrate has zero realized-trade
history, so every Reviewer pass will continue to defer until `_performance.md`
accumulates. That gating is the correct safety floor for an alpha-trader with
no track record.

---

## What got exercised

| Layer | Artifact | Status |
|---|---|---|
| Substrate write (ADR-209) | 6 trader `TASK.md` files | ✅ written via `TaskWorkspace.write` → `write_revision` |
| Substrate write | `/workspace/context/trading/universe.md` | ✅ authored (operator-tag) — fixed agent's "universe undefined" misread |
| Pipeline (ADR-141) | `track-universe` v2 (Tracker, 67s) | ✅ delivered, output.md written |
| Pipeline | `signal-evaluation` v2 (Analyst, 90s) | ✅ delivered, 5 signal state files at `/workspace/context/trading/signals/` |
| Pipeline | `pre-market-brief` v1 (Writer, 53s) | ✅ delivered, 6332-char HTML at `outputs/latest/output.md` |
| Proposal emission | `action_proposals` row `dcafe41f-…` | ✅ inserted, full ADR-194 envelope |
| Reviewer dispatch (ADR-194 v2 Phase 3) | AI Reviewer Sonnet v5 fired reactively | ✅ 7586 in / 406 out tokens |
| Reviewer reasoning | 6-check Simons framework against `principles.md` | ✅ Checks 1–3 pass with quantitative reasoning, Check 4 deferred |
| Decision substrate | `decisions.md` revision via authored substrate | ✅ written with `reviewer:ai-reviewer-sonnet-v5` author tag |
| Autonomy gate | `principles.md` narrowing on thin track record | ✅ correct defer per ADR-217 D4 |
| Money-truth substrate (ADR-195 v2) | `_performance.md` empty | ✅ correctly blocks autonomous execution |

---

## What surfaced (gaps, not failures)

### A1 — Domain-authored files not auto-injected as task context (load-bearing)

**Symptom**: Both Analyst (signal-evaluation) and Writer (pre-market-brief)
agents reported `_operator_profile.md` and `_risk.md` as **absent** despite
both being present in `workspace_files` at the canonical paths. Their tasks'
output decks accordingly say "BOOTSTRAP-BLOCKED — substrate undefined" while
the substrate is in fact defined.

**Cause**: `directory_registry.WORKSPACE_DIRECTORIES["trading"]` declares
`synthesis_file: "overview.md"` only. The pipeline's `_gather_context_domains`
auto-injects the synthesis file plus a budget-bounded sample of entity files,
but **does not** inject the `_`-prefixed operator-authored substrate files
(`_operator_profile.md`, `_risk.md`, `_performance.md`, `_tracker.md`). The
agent has `ReadFile` available and could fetch them, but the agent's prompt
does not name them as canonical reads, so the agent reasons over what it has
(synthesis + `_tracker.md` floor) and reports absence.

**Why this is the highest-leverage gap**: it makes the difference between
"agent sees the operator's declared truth and reasons against it" and
"agent reasons against missing context, produces honest-but-blocked output,
and the Reviewer's narrowing condition triggers on a phantom missing
substrate." For the trader persona, `_operator_profile.md` IS the system —
not having it in-prompt makes the Analyst structurally unable to evaluate
signals.

**Proposed direction (separate ADR or registry extension)**:
`directory_registry` entries gain an `authored_substrate: list[str]` field
declaring underscore-prefixed operator files that the pipeline injects
verbatim alongside the synthesis. For trading: `["_operator_profile.md",
"_risk.md", "_performance.md"]`. Inject them as a `## Authored Substrate`
section in the prompt context, distinct from synthesis (which is
agent-managed) and tracker (which is signal-state). This preserves the
ADR-152 directory registry as the single source for "what files this domain
holds" while making operator authorship structurally legible to agents.

**Dimensional classification**: Substrate (Axiom 1) — agents read against
operator-authored truth, currently the read path doesn't see it.

**Objective**: A (system).
**Within-A scope**: pipeline context-gather + directory_registry contract.
**FOUNDATIONS dimension**: Substrate.

### A2 — Narrative entries (ADR-219) not landing on task-pipeline runs

**Symptom**: 5 successful task runs in the past 10 minutes wrote 0 narrative
entries to `session_messages`. Only Reviewer-decision and chat-appends are
emitting entries. Per ADR-219 D2, every invocation should emit exactly one
narrative entry.

**Cause (likely)**: ADR-219 Commit 2 wired `task_pipeline.py` task_complete
card to call `write_narrative_entry`, but that emission is gated on a path
that's not being hit (likely tied to `delivery` recognition — the
`"cockpit-only"` delivery format logged "Unknown delivery format — skipping"
during all 3 runs). If task_complete is in the same branch as the delivery
emit, an unknown-delivery path silently skips both.

**Proposed direction**: separate the narrative emission from the delivery
emission. `task_complete` narrative entries should fire on every successful
run regardless of delivery format. `cockpit-only` should be a recognized
delivery format that resolves to "no external delivery, but compose +
narrative + workspace write are required."

**Dimensional**: Channel (Axiom 6) — operator-facing legibility broken
when the back-office pipeline runs but doesn't surface in `/chat`.

### A3 — Silent failure at `manage_task.py:1410` ("non-fatal" TASK.md write)

**Symptom**: Six trader tasks were created on 2026-04-24 06:03 UTC but only
their `tasks` table rows landed — none of them had a `TASK.md` in
`workspace_files`. The pipeline then dispatched them every ~2 hours for 44+
hours, each dispatch failing fast at "TASK.md not found", silently
advancing `next_run_at` by +2h via the claim sentinel without ever updating
`last_run_at`. Result: 22 phantom dispatches, zero work done, zero error
surface to operator.

**Cause**: [`manage_task.py:1410`](../../api/services/primitives/manage_task.py#L1410)
catches every exception in the TASK.md write block as `logger.warning("non-fatal")`.
The DB insert that creates the `tasks` row is *not* in this try-block, so
the row lands unconditionally. No transactional pairing.

**Why "non-fatal" is wrong**: a task with no TASK.md is a structurally broken
task — the entire pipeline reads from TASK.md as authoritative (ADR-207 P4b).
The "non-fatal" framing made sense pre-ADR-207 when TASK.md was a denormalized
copy of registry/DB state. It does not make sense post-ADR-207.

**Proposed fix** (next commit): make the TASK.md write fatal — wrap the
insert + write in a transaction so failure rolls back the row insert, OR
roll back the row insert manually if write fails. Either way, no
half-created tasks.

**Dimensional**: Substrate (Axiom 1) — partial substrate writes break the
filesystem-as-substrate guarantee.

### A4 — `_post_run_proposal_cleanup` Python 3.9 type-syntax error

**Symptom**: `[PROPOSE_ACTION] proposal-cleanup materialize failed:
unsupported operand type(s) for |: 'type' and 'NoneType'`

**Cause (likely)**: PEP 604 union syntax (`X | None`) used as a runtime
type expression in a function signature on a code path that's evaluated
under Python 3.9 (deprecated but still in venv). Cosmetic — proposal-cleanup
is a side effect of `propose_action`, the proposal itself was committed
before the failure.

**Dimensional**: Substrate (deprecated Python — infra hygiene).

### A5 — `agent_runs.status` stuck at `generating` post-completion

**Symptom**: 5 rows in `agent_runs` show `status='generating'` even though
the corresponding tasks have advanced `last_run_at` (proving completion).

**Cause (likely)**: `agent_runs.status` write happens at a different point
than `tasks.last_run_at`. Status update is missed on the success path.

**Dimensional**: Substrate — UI signal drift from authoritative state.

---

## Builder-seat actions taken (one-cycle repair, not policy)

1. Wrote 6 missing TASK.md files for trader tasks via `TaskWorkspace.write`
   (singular implementation — same code path as `_handle_create`, no
   side-channel).
2. Authored `/workspace/context/trading/universe.md` (920 chars,
   `authored_by="operator"`) to give Tracker a clean read surface for the
   declared universe. Mirrors `_operator_profile.md` § "Declared universe".
3. Reset `next_run_at` on 3 trader tasks to NOW − 1 minute so the pipeline
   would dispatch immediately rather than waiting for the next cron tick
   (which lands Monday 08:00 UTC under weekday-only cron).
4. Topped up `workspaces.balance_usd` from $3.00 → $50.00 and reset
   `subscription_refill_at` so `get_effective_balance()` returns positive.
   Necessary because the first track-universe run alone consumed $3.13 in
   token usage (see token_usage table) and the alpha workspace had no
   subscription refill.
5. Emitted synthetic Signal-2 AAPL `trading.submit_order` proposal via
   `handle_propose_action` to exercise the Reviewer chain. Used hypothetical
   prices that match Signal 2's declared rules (RSI(14)=23, within-5%-of-200-SMA,
   correct sizing math). Stays in scope — the ProposeAction primitive is the
   exact path the Analyst would have taken if `_operator_profile.md` had been
   in its prompt.

None of these mutations are policy changes. They are the minimum needed for
the loop to close once. The gaps surfaced (A1–A5) are the candidates for
durable code/registry changes.

---

## Loop math (this run)

- Token spend: $3.13 (track-universe) + $5.81 (signal-evaluation, est) +
  $3.40 (pre-market-brief, est) + $0.05 (Reviewer Sonnet v5 on AAPL proposal)
  ≈ **$12.40 spent, $37.60 remaining of the $50 grant**.
- Authored revisions: 12+ (TASK.md × 6, universe.md, decisions.md, signals × 5,
  outputs × 3).
- Proposals: 1 emitted, 1 deferred by AI Reviewer.
- Paper orders: 0 (correct — defer not approve).

---

## What this proves about the system

1. **The substrate is real.** ADR-209 authored revisions chain correctly,
   ADR-217 AUTONOMY.md gates correctly, ADR-194 v2 Reviewer dispatch fires
   reactively, ADR-195 v2 money-truth substrate gates the autonomy correctly.
2. **The recursion is intact.** Reviewer chose defer on a thin-track-record
   condition declared in `principles.md` — exactly the principle-as-narrowing-
   condition pattern. If `_performance.md` accumulates, future identical
   proposals could clear Check 4. The system is self-improving in the
   designed sense.
3. **The information architecture has one load-bearing gap (A1).** Operator-
   authored substrate files inside a domain are not auto-injected. This is
   the gap between "we wrote the files" and "the agent reasons over them."
   Closing this gap turns the persona's declared system from "agent has to
   discover the files via tools" into "agent reasons against operator truth
   in every turn."

---

## Next cycle (suggested, not committed)

- **Substrate fix (A3)**: `manage_task.py:1410` write-must-succeed. Single
  commit, small.
- **Registry extension (A1)**: `directory_registry` `authored_substrate` field,
  pipeline context-gather injection. Larger — needs an ADR sketch first to
  confirm it doesn't conflict with ADR-152's "directory registry as
  naming-convention reference" framing.
- **Narrative coverage (A2)**: track which task_pipeline paths emit
  `write_narrative_entry` and which don't. Likely a one-line addition.
- **Run again**: with A1 closed, run signal-evaluation again. If signals
  still don't fire (because real market data + indicator computation is a
  separate skill we haven't built), that's a real product gap and needs its
  own ADR (probably "track-universe needs a real Alpaca/AlphaVantage market
  data integration with computed indicators").
