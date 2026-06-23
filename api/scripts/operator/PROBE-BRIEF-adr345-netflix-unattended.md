# Probe brief — ADR-345 netflix unattended-wake capture (cloud agent reads this)

**Hat:** B (external-developer / evaluation). Speak in evaluation vocabulary
(scenario / expected vs observed / finding). Put a **substrate receipt** —
an `execution_event` id, a revision id, or an `action_proposals` id — under
every load-bearing claim. A claim without a receipt is narrative, not evidence.

## Scenario

ADR-345 (Expected Output as the workspace's declared output contract) + ADR-344
(Standing Obligation) **unattended-cadence behavioral probe** on the
**netflix-script-author** workspace (an alpha-author program persona):
- `owner_id`: `23cc7951-b6c7-471c-ac38-657d931db6f7`
- `workspace_id`: `341ec5b9-1cb6-4178-993e-94c7842d33b1`

**T0 state (2026-06-23 06:22 UTC):**
- Effective balance topped up `-0.08` → `+9.92` via a $10 `admin_grant`
  (this is what unblocks judgment-mode wakes — they were `balance_exhausted`-skipping).
- ADR-345 fixture **staged**: `governance/_expected_output.yaml` = `{kind: scene, delivery_cadence: weekly}`;
  `governance/_autonomy.yaml` = `{delegation: autonomous}`.
- Revision DAG is **clean** (no prior-session contamination — unlike yarnnn-author).
- Recurrences are **all auditors** (`corpus-coherence-check`, `outcome-reconciliation`,
  `revision-audit`, `track-sources`, `weekly-corpus-review`, `quarterly-voice-audit`)
  and **NONE produces an artifact**. That all-audit-no-producer shape is precisely
  the **ADR-344 (B) "structurally-can't"** condition.
- The `outcome-reconciliation` judgment cron was scheduled to fire **unattended at
  2026-06-24 05:00 UTC**, ~1h before this probe runs.

## Task

1. From the repo root, run:
   ```
   bash api/scripts/operator/check_netflix_unattended_wake.sh
   ```
   It queries the DB directly via `psql` (no setup needed). If `psql` is absent:
   `apt-get install -y postgresql-client`, then re-run. The script header documents
   what each numbered section reads.

2. Report **EXPECTED vs OBSERVED** on three questions, quoting ids verbatim:

   **(a) Top-up worked?** Did the 05:00 UTC `outcome-reconciliation` judgment wake
   run with `status=success` and NOT `error_reason=balance_exhausted`?
   *Expected:* success (effective balance is now positive). Quote the `execution_event`
   row (created_at, slug, mode, status, error_reason).

   **(b) Shortfall classified?** Did the Reviewer classify the ADR-344 (B)
   "structurally-can't" shortfall — i.e. recognize that its recurrences all audit and
   none produces against the **declared weekly** Expected Output?
   *Expected:* the judgment trail (standing_intent / judgment_log) names the gap.
   Quote the revision.

   **(c) Authored a compose organ — or asked?** Did the Reviewer **author a compose
   organ within the floor** (a NEW *producer* recurrence appearing in the `tasks`
   index) — the ADR-344 (B) resolution — OR did it emit a spurious "what cadence?"
   `Clarify` (an `action_proposals` row with `primitive=Clarify`)?
   *Expected (clean close):* it authors the compose recurrence and does NOT emit the
   "what cadence?" Clarify, because the **declared** `_expected_output.yaml` supplies
   the contract that the missing-contract Clarify would otherwise ask for. Quote the
   new recurrence revision OR the Clarify proposal.

3. **Honest verdict.** If the judgment wake still failed (balance, or any other
   `error_reason`), say so plainly with the receipt — do NOT narrate a success that
   the substrate doesn't show. If nothing was authored and no Clarify emitted (a
   silent hold), that is also a finding worth reporting (could be quiet-world (A),
   or a gap). State which.

The clean ADR-345 close = (a) success + (b) shortfall classified + (c) compose organ
authored within the floor, with NO "what cadence?" Clarify.
