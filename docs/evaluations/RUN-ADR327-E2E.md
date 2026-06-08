# RUN-ADR327-E2E — Runbook for the ADR-327 validation e2e suite run

> **Purpose:** make `main` runnable end-to-end for validating ADR-327 (budget
> reframe + self-improving calibration loop). A fresh session copy-pastes the
> prompt in §5 and follows this runbook. Hat-B (developer/evaluation surface).
>
> **Authored:** 2026-06-08, alongside the ADR-327 eval validation pass
> (commit `3bd8118`). All commands below were smoke-tested (`--help` resolves)
> against the repo at that commit.

---

## 0. What this run validates

ADR-327 retired "pace" (a frequency dial) and replaced it with a dollar
**budget** envelope; it added a **self-improving calibration loop**
(`_calibration.md` kernel mirror + `substrate_abi.ground_truth`). The Hat-A
code gates already pass. This e2e run is the **Hat-B empirical validation**:
does the Reviewer actually *reason correctly* against the new substrate?

The three ADR-327-relevant evals (all **market-independent — run any time**):

| Suite | Eval | What it reads |
|---|---|---|
| `alpha-trader-stewardship` | **calibration-cadence-stewardship** (eval-3, NEW) | Seeds `_calibration.md` showing a recurrence fired 38× / 0 proposals; tests whether the Reviewer re-authors that cadence citing the evidence (the D6 loop's central claim). |
| `yarnnn-author-judgment` | **budget-coherence** (eval-5, retargeted from pace-coherence) | Reviewer reads `_budget.yaml` + reasons about wake allocation within the envelope. |
| `yarnnn-author-responsiveness` | **counterfactual-budget-raise** (eval-9, retargeted from pace-raise) | Operator raises `_budget.yaml` amount $50→$150; tests allocation-within-envelope reasoning. |

---

## 1. Preconditions (read before running)

1. **Environment** — `api/.env.alpha-ops` + repo `.env` must carry
   `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `ANTHROPIC_API_KEY`,
   `INTEGRATION_ENCRYPTION_KEY`. (`api/.env.alpha-ops` is present at `main`;
   the harness loads both files automatically.)
2. **Venv** — repo-root `.venv` (the harness uses `.venv/bin/python`).
3. **Live LLM + DB** — these runs make real Anthropic calls and write real
   Supabase substrate for the persona workspaces. They cost money (each
   suite declares a `budget.per_session_usd` ≈ $6, surfaced-not-gated).
4. **Personas** (`docs/alpha/personas.yaml`):
   - `yarnnn-author` → `user_id 0b7a852d-…` (market-independent author workspace)
   - `kvk` → `user_id 2abf3f96-…` (personal trader workspace; the stewardship
     suite is market-independent — it reads seeded ground-truth, not live market)

---

## 2. Setup (idempotent — safe to re-run)

Run from **repo root** unless noted. Each persona needs its program activated
once + the ADR-327 budget migration run once (collapses any stale
`_pace.yaml`/`_token_budget.yaml` → `_budget.yaml`; idempotent no-op if the
workspace is already on the budget model or has only the kernel default).

```bash
# --- yarnnn-author (author suites) ---
.venv/bin/python api/scripts/alpha_ops/activate_persona.py --persona yarnnn-author

# --- kvk (trader stewardship suite) ---
.venv/bin/python api/scripts/alpha_ops/activate_persona.py --persona kvk

# --- ADR-327 budget migration (per workspace; idempotent) ---
# Migrates ALL workspaces that still carry _pace.yaml / _token_budget.yaml.
# Dry-run first to see what it will touch, then apply.
cd api
../.venv/bin/python -m scripts.oneshot.adr327_collapse_pace_tokenbudget_to_budget --dry-run
../.venv/bin/python -m scripts.oneshot.adr327_collapse_pace_tokenbudget_to_budget
cd ..
```

**Verify the migration landed** (each workspace should now have `_budget.yaml`,
no `_pace.yaml`/`_token_budget.yaml`). Substrate-receipt query:

```bash
psql "$(grep -m1 'postgresql://' docs/database/ACCESS.md | sed 's/.*\(postgresql[^ ]*\).*/\1/')" -t -c \
  "SELECT split_part(path,'/',4) AS file, count(*) FROM workspace_files
   WHERE path LIKE '%governance/_budget.yaml'
      OR path LIKE '%governance/_pace.yaml'
      OR path LIKE '%governance/_token_budget.yaml'
   GROUP BY file ORDER BY file;"
```
Expected after migration: `_budget.yaml` rows present; zero `_pace.yaml` /
`_token_budget.yaml` rows.

---

## 3. Run the ADR-327 validation suites (market-independent — any time)

Run in this order (cheapest-blast-radius first). Each emits a timestamped
session folder under `docs/evaluations/`.

```bash
# (a) The self-improving loop — the NEW calibration eval (trader stewardship)
.venv/bin/python -m api.scripts.operator.run_eval_suite \
  --suite docs/evaluations/eval-suites/alpha-trader-stewardship.yaml \
  --caller eval-suite-runner

# (b) Budget-reading coherence (author judgment, 6 evals incl. budget-coherence)
.venv/bin/python -m api.scripts.operator.run_eval_suite \
  --suite docs/evaluations/eval-suites/yarnnn-author-judgment.yaml \
  --caller eval-suite-runner

# (c) Budget-raise responsiveness (author, 4 evals, ordered-arc; incl. counterfactual-budget-raise)
.venv/bin/python -m api.scripts.operator.run_eval_suite \
  --suite docs/evaluations/eval-suites/yarnnn-author-responsiveness.yaml \
  --caller eval-suite-runner
```

**Optional — the market-DEPENDENT suite** (only during US market hours; reads
live signal rules against the market): `alpha-trader-autonomous-loop.yaml`.
Skip it for ADR-327 validation — it doesn't exercise budget/calibration.

---

## 4. Read the results (the load-bearing half)

Each run writes `docs/evaluations/{YYYY-MM-DD-HHMMSS}-{suite}-session/`:
- `SESSION.md` — auto-scaffold: §Preconditions (auto), §Thesis (copy), §The
  read (**blank — you fill this**), §Cost (auto).
- `raw/{eval}/transcript.md` · `substrate-diff.md` · `shape-receipts.md`
- `raw/cost-rollup.csv`

**Discipline (EVAL-SUITE-DISCIPLINE.md):** the run produces artifacts; it does
NOT produce verdicts. After each run, READ the raw artifacts and fill
`SESSION.md` §The read with the forensic finding — naming the (a) PASS / (b)
UNDER-FIRE / (c) MIS-FIRE outcome per the eval's `prior:` hypothesis, with
substrate-receipts (revision_ids, decisions.md citations, execution_event
rows). For the ADR-327 evals specifically:
- **calibration-cadence-stewardship**: did the Reviewer author a Schedule()
  pause/update/archive on `intraday-momentum-rescan` (the 38-fire/0-proposal
  recurrence) citing `_calibration.md`? Or notice-and-defer (the failure)?
  Did it leave healthy `signal-evaluation` untouched (mis-fire guard)?
- **budget-coherence**: did the Reviewer cite `_budget.yaml` (not a memory of
  pace) and reason about allocation-within-envelope?
- **counterfactual-budget-raise**: on the raised `_budget.yaml` ($150), did
  the Reviewer cite `amount_usd:150` from the fresh envelope and reason about
  ALLOCATION (the self-improving-loop posture), not a frequency cap?

A NULL-output-token "success" row in `cost-rollup.csv` is the silent-wake
fault — it invalidates that eval's read (S9).

---

## 5. The copy-paste fresh-session prompt

> Paste the block below verbatim into a new session at repo root. It is
> self-contained: it tells the session to run this runbook, in order, with
> the right discipline.

```
Run the ADR-327 e2e validation suite per docs/evaluations/RUN-ADR327-E2E.md.

Context: ADR-327 (budget reframe + self-improving calibration loop) is merged
to main. I want the Hat-B empirical validation — run the three
market-independent ADR-327 suites and read the results with substrate-receipts.

Do this in order, from repo root:

1. SETUP (idempotent): activate personas yarnnn-author + kvk, then run the
   ADR-327 budget migration (--dry-run first, show me the plan, then apply).
   Verify with the psql query in §2 that _budget.yaml is present and
   _pace.yaml/_token_budget.yaml are gone. Show me the receipts.

2. RUN the three suites in §3 order:
   (a) alpha-trader-stewardship  (b) yarnnn-author-judgment
   (c) yarnnn-author-responsiveness
   These are market-independent and run any time. Pause after each run and
   tell me the session folder path + cost before starting the next.

3. READ each session's raw/ artifacts per §4. Fill SESSION.md §The read with
   the forensic finding for each ADR-327 eval (calibration-cadence-stewardship,
   budget-coherence, counterfactual-budget-raise): name PASS/UNDER-FIRE/
   MIS-FIRE with revision_ids + decisions.md + execution_event receipts. Do
   NOT declare a verdict without the substrate-receipt under it.

4. SUMMARIZE: did ADR-327 validate? Name any finding (a Hat-B finding
   recommends a system-side change; it does not make one). Surface anything
   that needs a follow-up ADR or fix.

These runs cost real money (~$6/suite) and write real substrate. Confirm the
setup receipts look right before running the suites. If any precondition is
off (env var missing, migration didn't land, persona not activated), STOP and
tell me rather than running against a broken workspace.
```

---

## 6. Notes / gotchas

- **Run order matters for the author-responsiveness suite**: it's an ordered
  arc (evals 2→4 accumulate; `counterfactual-budget-raise` is eval-9,
  `counterfactual-preferences-add` eval-10 `requires` `_budget.yaml
  amount_usd:150` from eval-9). Run the suite as a whole; don't run
  individual evals out of order.
- **The migration is per-workspace and global** — it walks every workspace
  with a stale file, not just the two eval personas. Dry-run first.
- **D6.d (deferred)**: alpha-author has no `substrate_abi.ground_truth`
  declaration yet, so its calibration mirror degrades to cadence-history-only.
  The calibration *loop* validation runs against alpha-trader (kvk), which
  declares `ground_truth: operation/trading/_money_truth.md`. Second-program
  (alpha-author) ground-truth validation is a follow-up, not part of this run.
- **Pre-existing eval rot** (unrelated to ADR-327): some older non-suite test
  gates reference moved bundle paths. Out of scope for this run.
```
