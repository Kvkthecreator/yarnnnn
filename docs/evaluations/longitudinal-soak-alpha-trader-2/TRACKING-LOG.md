# Longitudinal soak — alpha-trader-2 (continuous tenure track)

> **Surface**: the continuous tenure monitor per [`../LONGITUDINAL-TRACKING.md`](../LONGITUDINAL-TRACKING.md). NOT an episodic dev-eval session — this is a single growing log, read periodically over the soak window, every entry deploy-marker-stamped (§3 / §5 rule 3). Hat-B (a report over substrate, not a fired probe).
>
> **What this soak proves**: that the alpha-trader operation *survives* unattended tenure (§6 rule 6 — survival precedes improvement), and — once survival holds — whether the self-improving loop *actually improves* on an earned, uncontaminated ledger (the thesis, FOUNDATIONS DP24 / ADR-327 D6).
>
> **Subject workspace**: `alpha-trader-2` · `user_id=29a74c63-0c9c-4998-b8bb-56dd0d810a4e` · program `alpha-trader` (bundle-default identity — persona-specific stat-arb overrides intentionally NOT applied; see genesis entry).
>
> **Clock owner**: the system. Render cron `crn-d604uqili9vc73ankvag` (`*/5 * * * *`) → recurrence walker → `wake_queue` → `wake_drainer` → `invoke_reviewer`, unattended. Claude is the periodic *reader* only (§4.1).

---

## How to read / extend this log

- One dated entry per read. Newest at the bottom (append-only, chronological — Stream archetype).
- **Every entry MUST carry its deploy-marker** (the `origin/main` commit the Render services ran under for that segment). When the marker changes between entries, that's a labeled boundary — improvement vs architectural-shift stays distinguishable by construction (§3).
- **Survival before improvement.** Until a survival entry is clean (zero silent-wakes, zero stuck locks, budget not exhausted, market-holiday next-fire correct), do NOT read the ledger as improvement evidence.
- Substrate-receipts under every claim: revision_id / execution_event id / wake_queue id / reproducible query.

The survival-audit queries are in [`SURVIVAL-QUERIES.md`](SURVIVAL-QUERIES.md) (built demand-pull from this soak — NEXT-4).

---

## 2026-06-10 02:31 UTC — GENESIS (tenure day 0)

**Deploy-marker**: `fc859fe` (`feat(alpha-ops): --clean-slate flag on activate_persona harness`). Render API redeploy went live 2026-06-10T02:31:08Z (`dep-d8kcnvek1jcs739g1ml0`); the unified-scheduler cron picks up the same commit on its next tick. This is the canon the soak runs under until the next labeled boundary.

**What was done to establish the clean ledger** (Hat-B setup, not part of the observed system):

1. **Destructive clean-slate** of alpha-trader-2 via `activate_persona.py --persona alpha-trader-2 --clean-slate --skip-connect`, which calls the singular `services.workspace_purge.clear_workspace_for_user` (commit `3a43d22`). Purged: 92 workspace_files, 6153 workspace_file_versions, 1 agent, 11 tasks, 4711 wake_queue rows. Re-forked the alpha-trader bundle at current-canon paths. Alpaca `trading:active` connection preserved (L2 invariant).
2. **Stale-path override contamination removed.** The persona overrides directory (`docs/alpha/personas/alpha-trader-2/overrides/`) still ships pre-ADR-320 `context/` paths; the override step wrote 3 duplicate files at stale paths (`context/_shared/MANDATE.md`, `context/trading/_operator_profile.md`, `context/trading/_risk.md`). All 3 files + their revision rows deleted (FK-safe order). The soak runs the **bundle-default** alpha-trader identity, not the stat-arb override (operator-chosen: identity fidelity not required for a survival soak). *The overrides-dir path drift is logged as a Hat-B backlog fix — STANDING-A.*
3. **Clean tenure-day-0 ledger.** L2 preserves `execution_events` (ADR-291 cost ledger, L4-only deletion) — so 9,401 pre-wipe events from alpha-trader-2's prior 22-day life survived the wipe. Deleted all events `created_at < 2026-06-10 02:22:00+00` so the cost/outcome ledger starts at the soak boundary. The improvement curve (§4) now reconstructs from a genuine day-0 origin.
4. **Soak runway.** `balance_usd` set $3 → $30 (the LLM-spend wallet). At the $50/monthly budget envelope, $30 is the runway ceiling; the operation will self-pace within the envelope.

**Start-state receipt** (`workspace_files` / `workspace_file_versions` / `execution_events` / `tasks` / `workspaces`, queried 02:31 UTC):

| metric | value | meaning |
|---|---|---|
| workspace_files | 44 | bundle substrate, all current-canon paths |
| stale `context/` files | 0 | contamination removed |
| workspace_file_versions | 55 | clean revision chain from genesis |
| execution_events | 4 | clean day-0 ledger (the 4 post-wipe mechanical tracker wakes) |
| tasks (scheduling index) | 11 | all scheduled (next_run_at populated) |
| MANDATE marker | `# Mandate — alpha-trader` | valid (parses in `_all_slugs`) |
| balance_usd | $30.00 | soak runway |
| `_budget.yaml` | $50.00 / monthly · $1.00/wake | the ADR-327 self-imposed ceiling **under observation** |

**First survival signal (positive).** Within ~2 minutes of clean-slate, the scheduler fired 4 mechanical-mode wakes (`track-universe`, `track-account`, `mirror-signal-state`, `track-regime`) at 02:24 UTC, all `wake_queue.status = completed`. The fresh workspace is live and the cron is correctly walking the re-forked recurrences. No silent-wakes, no stuck locks at minute zero.

**Honest caveats carried into the soak** (LONGITUDINAL-TRACKING §6):
- This is the **first true unattended scheduler-fired multi-day run.** All prior alpha-trader evals were harness-fired. Survival-class unknown-unknowns may still exist — survival must be demonstrated before the ledger is read as improvement.
- **Meaningful capital loops are slow** (days-to-a-week between genuine trader signals). A boring week tests survival, not the judgment loop. The window must be long enough to capture real judgment events.
- The **curve view does not exist yet** — the improvement read (NEXT-5) will be an ad-hoc query over `workspace_file_versions` (`_money_truth.md` diff-sequence) + `execution_events`, deploy-marker-stamped. Promote to a kernel mirror only if running the track proves the query insufficient (demand-pull).

**Next read**: first survival-audit pass after the soak has accumulated ≥1 full cron day (NEXT-3b → NEXT-4). Watch for: any `mode=judgment` wake with `status=success` + `output_tokens IS NULL` (silent-wake machine fault, S9), any `execution_events.status != success`, `tasks` slugs drifting from `_recurrences.yaml`, `balance_usd` burn rate vs the $50/mo envelope, and market-holiday next-fire correctness.
