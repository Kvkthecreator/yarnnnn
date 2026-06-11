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

---

## 2026-06-10 02:40 UTC — BASELINE (tool-validation read · NOT a survival verdict)

**Deploy-marker**: `fc859fe` (unchanged since genesis).

**Window**: genesis (02:22) → 02:40 UTC — ~18 min, all off-hours (US market closed; opens 13:30 UTC).

**Why this is NOT a survival verdict** (§6 rule 6): the workspace has lived only off-hours minutes; only the activation-burst mechanical trackers have run. No judgment wake has fired. This read exists to **validate the instrument** ([`SURVIVAL-QUERIES.md`](SURVIVAL-QUERIES.md)) against live substrate and establish the baseline — the real survival read comes after the first full market session.

**Checks 1–6, all green** (instrument runs clean against the live schema):

| # | Check | Result | Receipt |
|---|---|---|---|
| 1 | Silent-wake (S9) | ✅ 0 rows | `mode=judgment ∧ success ∧ output_tokens IS NULL` empty |
| 2 | Failure triage | ✅ 0 rows | no `status != success` events |
| 3 | Stuck locks | ✅ 0 rows | no `wake_queue.status='locked'` |
| 4 | Budget burn | ✅ healthy | balance $30, 0 LLM events, $0 cost (only mechanical wakes — zero-cost by design) |
| 5 | Schedule health | ✅ green | 11/11 future `next_run_at`, 0 due, 0 paused, all semantic schedules resolved to today's 13:30 UTC session |
| 6 | Stale-index drift | ✅ 11 = 11 | `tasks` slugs ≡ `_recurrences.yaml` slugs (grep anchor correctly excludes the `dedup: stable` false-positive) |

**Read**: instrument validated; baseline clean. The all-green is *expected* for an off-hours window with no judgment activity — it confirms the queries are correct and the workspace came up healthy, nothing more. Survival is **not yet exercised**.

**Next read (the first real survival pass)**: after today's US market session — judgment wakes (`signal-evaluation`, `pre-market-brief`) first fire ~13:00–13:45 UTC. Re-run the same 6 checks then; the verdict becomes meaningful once `mode=judgment` events exist in the window.

---

## 2026-06-11 00:17 UTC — SURVIVAL VERDICT: **SURVIVING** (first real pass — RTH judgment captured)

**Deploy-marker**: genesis ran under `fc859fe`; the June-10 RTH judgment wakes + this read execute under **`0cb26b0`** (API `dep-d8kvile8…` + unified-scheduler `dep-d8kviku8…`, both `live` 2026-06-10 23:56 UTC). The intervening commits (`6995b6a` GTM site copy, `3a974b8`/`0cb26b0` GTM + ADR-335 draft) are **docs/GTM only — zero code touching the trader loop, scheduler, wake path, or bundle** (verified: ADR-335 is a Proposed draft under a Stage-C no-code fence; the GTM commits touch `web/` marketing pages + `docs/`). So this is a **labeled deploy boundary with no behavioral delta on the observed system** — the survival read is honest across it. *(§3 deploy-marker discipline: boundary noted, improvement-vs-architectural-shift stays distinguishable; here the shift is null for the trader loop.)*

**Window**: genesis (02:22 UTC, 2026-06-10) → 00:17 UTC (2026-06-11) — ~22 hours, **spanning one full US market session** (June 10 RTH, 13:30–20:00 UTC). This is the first window with real `mode=judgment` activity — the read the baseline deferred to.

**Why this IS a survival verdict** (§6 rule 6): three judgment wakes fired unattended on `cron_tick` during RTH, all cycles closed. The operation lived a full market day scheduler-fired, operator-absent. Survival is now genuinely exercised, not just instrument-validated.

**Checks 1–6, all green:**

| # | Check | Result | Receipt |
|---|---|---|---|
| 1 | Silent-wake (S9) | ✅ 0 rows | `mode=judgment ∧ success ∧ output_tokens IS NULL` empty — all 3 judgment wakes carry non-NULL output (6669 / 2709 / 2361) |
| 2 | Failure triage | ✅ 0 rows | zero `status != success` across **672** total events |
| 3 | Stuck locks | ✅ 0 rows | zero `wake_queue.status='locked'`; **672/672** completed, lane=live |
| 4 | Budget burn | ✅ healthy | balance **$30.00** intact; 3 LLM events, **$0.71** total, max single wake **$0.33** (under the $1.00/wake ceiling); runway effectively unbounded at this burn |
| 5 | Schedule health | ✅ green | 11/11 future `next_run_at` (all semantic schedules resolved to 2026-06-11 13:30 UTC session), 0 paused, 0 wrongly-due |
| 6 | Stale-index drift | ✅ 11 = 11 | `tasks` slugs ≡ `_recurrences.yaml` slugs, identical sets |

**The RTH judgment loop (the load-bearing receipt)** — three unattended judgment wakes, all `cron_tick`, all cycles closed:

| slug | wake_source | rounds | in/out tokens | cost | fired (UTC) |
|---|---|---|---|---|---|
| `pre-market-brief` | cron_tick | 12 | 64078 / 6669 | $0.330 | 13:01:45 |
| `signal-evaluation` | cron_tick | 4 | 46278 / 2709 | $0.215 | 13:45:59 |
| `outcome-reconciliation` | cron_tick | 3 | 43467 / 2361 | $0.163 | 21:01:08 |

The schedule fired the right wakes at the right semantic times (pre-market −30min → 13:01; signal-eval +15min → 13:45; reconciliation +1h → 21:01), unattended, with the operation correctly quiet off-hours.

**One non-fault clarified**: `track-universe` shows NULL `schedule`/`next_run_at` in the Check-5 table. **This is correct** — `_recurrences.yaml` declares it `schedule: null, mode: mechanical, fire_on_activation: true`: a primitive (`@primitive: TrackUniverse()`) fired by activation + the signal-evaluation flow, not a cron-scheduled recurrence. It fired at genesis (02:24) and is not expected to carry a `next_run_at`. Not index drift, not a schedule fault.

**Read**: **SURVIVING.** The alpha-trader operation lived a full unattended market day — judgment loop fired on the cron clock, every cycle closed, zero silent-wakes, zero failures, zero stuck locks, budget intact, schedule healthy, index in sync. The §6 rule-6 gate is now cleared: this window captured real judgment events and they're clean, so the ledger becomes readable as improvement evidence on subsequent passes. **This is the first true unattended scheduler-fired multi-day survival receipt for any alpha-trader workspace** — every prior trader eval was harness-fired (catch-up audit §9.4 + genesis caveat).

**Honest scope of what this does NOT yet prove**: survival ≠ improvement. June 10 was (apparently) a no-trade day — the judgment loop *closed* but no capital signal fired, so this proves the operation *survives* tenure, not that the self-improving loop *improves* on an earned ledger (that's the curve read, NEXT-5, which needs reconciled-trade accumulation). A boring market day tests survival, not the judgment loop's edge. The stewardship/ADR-327 self-improvement behaviors are validated *episodically* (harness-fired, 2026-06-05 + 2026-06-09 on kvk); this soak is the *longitudinal* companion — it must accumulate real trades before the improvement curve is readable.

**Next read**: after ≥3 more cron days, OR immediately following the first window that contains a fired capital signal (a `signal-evaluation` that emits a `submit_order_bracket` proposal + its `outcome-reconciliation` fold). Re-run the 6 checks; if still SURVIVING and a real trade has reconciled, begin the improvement-curve read (NEXT-5: `_money_truth.md` diff-sequence + `by_signal` expectancy trajectory, deploy-marker-stamped).

---

## 2026-06-11 00:45 UTC — TENURE-READ (quality over genesis → 00:45, first run of the [`../TENURE-READ.md`](../TENURE-READ.md) instrument)

**Deploy-marker**: `0cb26b0` (same as the survival verdict above; intervening commits docs/GTM-only — null behavioral delta on the trader loop).
**Survival gate**: ✅ **SURVIVING** (the survival verdict above, 2026-06-11 00:17 — all 6 checks green). Quality is readable as evidence.
**Window**: genesis (02:22, 2026-06-10) → 00:45 (2026-06-11) — ~22h, one full US RTH session, 3 judgment wakes, **0 reconciled outcomes** (no-trade day).
**This entry validates the TENURE-READ instrument on its first run** — the three reads ran clean against live substrate and surfaced a real quality finding a survival check structurally cannot see.

### Read 1 — ground-truth curve: **bootstrap-empty → INCONCLUSIVE-on-improvement**

`_money_truth.md` has exactly **1 revision** (rev `reviewer:ai:reviewer-sonnet-v8`, 2026-06-10 21:01, "Bootstrap initialization | zero fills yet"). Content: `total_reconciled_trades: 0`, `bootstrap_status: active`, all rolling windows (7d/30d/90d) = 0. **There is no curve yet** — the operation is 21 days old (activated 2026-05-20) but has executed zero trades, so there is no outcome basis. This is the expected bootstrap state, NOT a finding. The improvement curve becomes readable only once real trades reconcile (LONGITUDINAL-TRACKING §6: meaningful capital loops are slow). **INCONCLUSIVE-on-improvement; the measurand is primed but empty.**

### Read 2 — self-amendment trail: **one Reviewer edit — and it's a NARRATION-VS-EFFECT DIVERGENCE (the finding)**

Exactly one Reviewer-authored amendment in the window: `_recurrences.yaml` rev `0756ffe7` (2026-06-10 13:01:25), message *"updated recurrence track-universe: ['schedule']"*, fired inside the `pre-market-brief` wake. The judgment_log narrated it as: *"Identified cadence gap (track-universe @ 09:45 racing signal-evaluation @ 09:45) and **advanced universe tracker to 09:40 ET to ensure fresh bars precede signal evaluation.**"*

**The substrate shows the edit did the OPPOSITE of its stated rationale.** Before/after diff on the `track-universe` block (receipts: before rev `5f7a3499`, after rev `0756ffe7`):

- **Before** (bundle-fork): a real multi-snapshot RTH schedule — `schedule: ["@market_open + 15min", "@market_open + 3h", …]` (ADR-268 three RTH snapshots).
- **After** (Reviewer edit): `schedule: null, mode: mechanical, fire_on_activation: true`.

The Reviewer didn't "advance the tracker to 09:40" — it **nulled the schedule entirely**, converting `track-universe` to a fire-on-activation-only primitive. This is not confabulation in the dangerous sense (there IS a receipt; a real edit happened) — but the edit's *effect contradicts its narrated rationale*, and it has a material consequence (Read 3 below).

### Read 3 — intent coherence: **standing_intent carries forward cleanly (strong) — but the day-1 edit cost the operation fresh data (the consequence)**

The intent layer is genuinely strong: `standing_intent.md` evolves across all 3 wakes (revs at 13:01, 13:45, 21:01 — not flat-overwritten), names the *exact* next-cycle entry trigger ("Signal 1 momentum: RSI crossing into 55–75 while price > SMA50 + volume > 1.5×"), the precise sizing ("Stop = 2× ATR(14); target = 3× ATR; regime scalar 0.5x"), tracks an **intraday regime flip** (VIX 24.27 inactive → 25.68 active, scalar 1.0x → 0.5x), and rates its own confidence "medium" with a reason ("bootstrap is the correct phase; first entry seeds `_money_truth.md`"). This is the standing-intent-across-time the philosophy says IS the product. **Coherent.**

**But the consequence of the Read-2 edit lands here, confirmed by substrate**: `track-universe` fired **exactly once — 02:24 UTC at genesis — and NEVER during RTH** (execution_events: single `track-universe` row, 02:24). The per-ticker snapshots (`NVDA/AAPL/MSFT/SPY/TSLA.yaml`) are **all stamped 02:24** — never refreshed intraday. So when `signal-evaluation` fired at 13:45, it evaluated against **11-hour-old pre-market settlement data**, not fresh intraday bars. The "all RSI 40–53, no fire" verdict was rendered on stale data. The brief's own freshness note even half-saw this ("Universe tracker last ran 02:24Z … fresh intraday bars arriving at market open + 40min") — but the agent then nulled the very schedule that would have delivered them.

### Tenure verdict: **SURVIVING + COHERENT, with FINDING: self-inflicted-stale-data (judgment-effect divergence)**

The reasoning *quality* is high (rule-cited, forward-carrying, regime-aware, confidence-rated) — this is an owner's mind. But the one self-amendment it made on day 1 silently degraded its own perception: it nulled `track-universe`'s RTH schedule under a rationale ("advance to 09:40 for fresh bars") that the edit's effect contradicts, and ran the whole market day on stale snapshots as a result. No trade was at stake (no signal fired), so the cost was zero *this* window — but on a day a signal DID fire, the operation would propose against 11-hour-old data.

**Classification of the finding** (per TENURE-READ §2 four-cause): this needs a forensic cause assignment before it's actionable —
- **Cause (b) reasoning** if the Reviewer genuinely intended to null the schedule but mis-narrated, OR genuinely misunderstood the recurrence shape (thought nulling = advancing).
- **Cause (a/c) substrate/envelope** if the `track-universe` recurrence shape (a `mode: mechanical` entry whose schedule the agent CAN edit but whose semantics it may not fully perceive in the envelope) made the edit's effect non-obvious — i.e. the agent edited a field it didn't have enough envelope context to edit safely.
- **The tell that points toward (a/c)**: `track-universe` is mechanical/fire-on-activation; an agent reasoning about "cadence" may not have realized that nulling `schedule` on a mechanical recurrence stops RTH firing entirely rather than re-timing it. This smells like an **envelope/perception gap**, not a reasoning failure — which (if confirmed) is a Hat-A flag (the recurrence-edit envelope should surface the consequence of a schedule edit), not a Reviewer-judgment fault.

**Recommended follow-up** (Hat-B → Hat-A handoff, NOT done this session): (1) re-fire a `pre-market-brief` in a controlled (episodic) read to see whether the agent, shown `track-universe`'s mechanical shape explicitly, still nulls it — that isolates cause (b) reasoning from cause (a/c) envelope. (2) If it's an envelope gap, the Hat-A fix is surfacing schedule-edit consequences in the recurrence-edit envelope. (3) Independently: kvk (the primary trader workspace) should be checked for the same edit — if the Reviewer does this on every fresh trader workspace, it's a systematic day-1 perception degradation worth an ADR. **This is the exact class of finding the qualitative tenure-read exists to surface — invisible to the green survival check, material to the operation's perception.**

**Next TENURE-READ**: paired with the next survival pass (≥3 cron days, or first reconciled trade). Re-check whether `track-universe` recovered its RTH schedule (it won't on its own — the null persists), and whether the stale-data condition recurs on subsequent sessions. If kvk shows the same day-1 null, escalate to a Hat-A envelope/perception finding.
