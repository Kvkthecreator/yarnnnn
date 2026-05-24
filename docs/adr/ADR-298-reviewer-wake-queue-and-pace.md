# ADR-298 — Reviewer Wake Queue + Pace Dial

> **Same-day amendment (2026-05-22 — [ADR-300](ADR-300-pace-as-atomic-kernel-surface.md)):** Pace gets its own atomic kernel surface at `/pace` (Document archetype, 16th kernel surface). D5 §"cockpit Schedule tab section" pace rendering site is superseded — pace UX no longer lives on the cockpit. PaceBadge becomes a read-only deep-link to `/pace`. The pace substrate (`_pace.yaml`), the trifecta canon (D11), the queue model (D2), the drain rate (D4), and the population constraint (D5 enforcement) are all preserved verbatim.

**Status**: **FULLY IMPLEMENTED 2026-05-22.** All 5 phases shipped. Phase 1: schema + service helpers (41/41 test gate, commit `42c9b13`). Phase 2: pace substrate + Schedule primitive gate + reviewer envelope (54/54 test gate, commit `9d320b5`). Phase 3: cutover — submit_wake_proposal enqueues, wake_drainer dispatches, stream_addressed_wake acquires lock via Option α (39/39 test gate, commit `2dfdb98`). ADR-261 D3 §1-§3 amendment banner landed in same commit. Canary v5 validated structural lifecycle end-to-end (7/8 layers, commit `9aaddfb`). Phase 4: bundle `minimum_pace` declarations on alpha-trader + alpha-author MANIFESTs + activation gate + D8 default-pace seeding (36/36 test gate, commit `b2c4bef`). Phase 5: walker legacy dedup check removed + migration 180 dropping `execution_events.wake_dedup_key` + cockpit FE pace badge + canary v6 L6 validation (3 Reviewer substrate writes through the post-cutover pipeline, commit `dc36cdf` + observation folder). Cumulative test gates: **170/170 PASS**. All ADR commitments structurally enacted; one deployment-ordering anomaly on canary v6 documented in [the v6 observation](../observations/2026-05-22-024952-canary-v6-l6-validation/findings.md) §"L8 anomaly" with no system impact.
**Date**: 2026-05-21 (Proposed) · 2026-05-22 (Fully Implemented)
**Supersedes / amends**: ADR-261 D3 §1–§3 (architectural guarantees on parallel concurrent Reviewer sessions, sub-minute precision, no head-of-line blocking — reversed; see §3 evidence + §4 amendment)
**Amends**: migration-178-wake-dedup-key (`wake_dedup_key` migrates from `execution_events` insert-time check to queue-side dedup at enqueue time), ADR-296 v2 (wake sources enqueue rather than directly dispatch)
**Builds on**: ADR-209 (Authored Substrate revision chain), ADR-231 D4 (thin scheduling-index precedent), ADR-274 (Reviewer cadence-authoring), ADR-275 (introspection cadence Reviewer-authored from `_preferences.yaml`), ADR-276 (reactive-trigger envelope governance pre-load), ADR-293 (governance-operational substrate taxonomy)
**Preserves**: FOUNDATIONS Axioms 0–9, ADR-194 v2 Reviewer substrate, ADR-216 orchestration-vs-judgment vocabulary, Principle 18 (standing intent implies Trigger-authoring authority)

## 1. Problem statement

The Reviewer fires **concurrently** across wake sources today. Five sources (`cron_tick`, `addressed`, `substrate_event`, `proposal_arrival`, `manual_fire`) each dispatch their own Reviewer session directly via `services/wake.py::submit_wake_proposal`. ADR-261 D3 explicitly canonized this as architectural guarantee: parallel concurrent sessions, sub-minute scheduling precision, no head-of-line blocking.

Since ADR-261 shipped (2026-05-08), production has surfaced concerns the parallel-concurrent guarantee does not address:

- **Concurrent writes producing logically-confused state.** Wake-duplication audit (`bdaff4d`) documented multiple Reviewer sessions writing `standing_intent.md` within seconds — substrate writes serialized correctly via ADR-209, but the *logical content* was two Reviewers thinking past each other in the same minute.
- **Cross-source dedup gap.** migration-178-wake-dedup-key's `wake_dedup_key` is per-source (e.g., substrate-event revision-id). No mechanism prevents an `addressed` wake and a `substrate_event` wake firing on the same operator action.
- **Pattern 1 wake-duplication bug** (`fa22788`). Patched substrate-event walker dedup; the underlying architectural pattern (multiple wake sources can fire concurrently with no shared dedup point) remains.
- **No first-class pace authority.** Operators have no lever for "how often does the agent work?" Pace is bottom-up emergent from individual recurrence schedules; not legible, not enforceable, not budget-bounded.
- **Operator-facing legibility.** "What is my agent doing today?" has no single-glance answer.

The structural root: the Reviewer is **one judgment seat per workspace** but the execution model lets that seat exist as **N concurrent instances**. Substrate coherence depends on serializing through ADR-209's revision chain, which orders *writes* but not *judgments* — two Reviewer instances can each read state, decide, and write without seeing each other.

## 2. Decisions

### D1 — Single-lane Reviewer execution per workspace

The Reviewer is one logical entity per workspace; it executes one wake at a time. No two Reviewer sessions for the same workspace run concurrently.

This is a structural inversion of ADR-261 D3 §1 (parallel concurrent Reviewer sessions). The reversal is **prudentially justified by observed failure modes**, not axiomatically mandated — single-lane is currently-right given coherence/dedup concerns dominating production; if future production data shifts the failure-mode distribution, the choice should be revisited. See §3 (evidence) + §4 (amendment).

### D2 — Wake queue is the singular entry point; the queue is transient compute, not state

All five wake sources enqueue into a single per-workspace queue. The scheduler drains the queue; the Reviewer executes drained wakes. No source bypasses the queue.

**Critical classification per Axiom 1 — this is the load-bearing structural move of the ADR.** The queue is **transient compute + deterministic enforcement, not authoritative state.** Without this classification, ADR-298 would introduce a parallel state-bearing substrate outside the filesystem-is-truth axiom — a structural drift from FOUNDATIONS Axiom 1 that would set precedent for future "this state can live in DB too" decisions and erode the substrate-is-filesystem discipline. Scenario L (§6) is the falsifiability check that confirms this classification is honest: the queue table can be wiped and reconstructed entirely from filesystem state + existing DB telemetry. If that reconstruction is not possible, the classification is wrong and the ADR fails.

Modeled on the `tasks` scheduling-index precedent (ADR-231 D4), the queue is:

- Mechanically reconstructable from filesystem state + DB telemetry at every moment. Every pending wake's source-of-truth lives in files: cron recurrences in `_recurrences.yaml`, hooks in `_hooks.yaml`, substrate transitions in `workspace_file_versions`, addressed turns in `session_messages`, proposals in `action_proposals`.
- A denormalized read-optimization layer + atomic-lock surface for the scheduler to coordinate single-lane drain across multiple scheduler instances.
- Not operator-readable as substrate. Operators read configuration (yaml files), outcomes (feed + `execution_events`), and watch-state (`standing_intent.md`). The "things about to happen" intermediate state is implementation detail.
- Garbage-collected after completion; completed wakes older than 7 days dropped by back-office maintenance (mirrors `execution_events` retention).

**Distinction from `execution_events`** (worth naming because future reviewers will ask "why not just append to `execution_events` with `status='pending'`?"): `execution_events` is historical telemetry — immutable, append-only, GC'd by age, no UNIQUE-constraint-driven enforcement on the insert path. `wake_queue` is imminent compute — mutable status field, lock acquire/release semantics, dequeue mutates state, UNIQUE constraint on `(user_id, wake_source, dedup_key)` is system-behavior enforcement, not telemetry. Both are non-substrate (per Axiom 1) but have different lifecycle shapes that demand separate tables. Folding the queue into `execution_events` would conflate immutable history with mutable in-flight state and make the dedup-and-lock semantics expensive on a high-write append-only table.

**No `_queue.yaml` file in workspace.** A workspace-substrate queue would: (a) require rewriting on every enqueue/dequeue, (b) introduce file-lock contention on bursts, (c) trigger ADR-209 revision-chain growth for transient state, (d) misframe the queue as semantically meaningful operator-readable substrate. The queue is closer to `execution_events` (DB-resident, non-substrate) than to `_recurrences.yaml` (filesystem-resident, substrate), but is structurally distinct from `execution_events` for the lifecycle reasons above.

Schema (proposed):

```sql
CREATE TABLE wake_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  wake_source TEXT NOT NULL,    -- 'cron_tick' | 'addressed' | 'substrate_event' | 'proposal_arrival' | 'manual_fire'
  lane TEXT NOT NULL,            -- 'paced' | 'live'
  slug TEXT,                     -- recurrence slug, if applicable
  payload JSONB NOT NULL,        -- full wake payload (envelope, context, etc.)
  dedup_key TEXT,                -- cross-source dedup; nullable for manual_fire
  status TEXT NOT NULL DEFAULT 'pending',  -- 'pending' | 'locked' | 'completed' | 'failed' | 'dropped'
  enqueued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  locked_at TIMESTAMPTZ,
  locked_by TEXT,                -- scheduler instance ID
  completed_at TIMESTAMPTZ,
  execution_event_id UUID,       -- FK to execution_events when wake actually runs
  UNIQUE (user_id, wake_source, dedup_key)  -- cross-source dedup at the queue layer
);

CREATE INDEX idx_wake_queue_pending ON wake_queue (user_id, status, lane, enqueued_at)
  WHERE status = 'pending';
```

### D3 — Two lanes: paced + live

Wakes enter one of two lanes at enqueue time:

| Lane | Wake sources | Drain rate | Latency expectation |
|---|---|---|---|
| **paced** | `cron_tick` (judgment-mode recurrences) | **Capped by operator-declared pace** | Per pace: hourly fires drain within 1h, daily within 24h, weekly within 7d |
| **live** | `addressed`, `substrate_event`, `manual_fire`, `proposal_arrival` (Reviewer-relevant) | As fast as single-in-flight constraint allows | Drained next-available; waits for current wake to complete (~30-75s typical) |

Both lanes share the **single-in-flight constraint**: only one wake executes per workspace at a time. The lane determines drain rate, not concurrency.

**FIFO within the live lane is deliberate, not a default-by-omission.** Live-lane wakes drain in enqueue order; addressed turns do NOT preempt mid-flight substrate-event wakes (and vice versa). The reasoning: substrate-event wakes are also operator-driven (the operator just transitioned substrate by editing a file or flipping a status); allowing addressed turns to preempt their own causally-prior substrate transitions would let the operator chat "is the audit done?" *before* the audit actually fires — producing operator confusion, not better UX. FIFO serialization gives the operator the coherent audit-then-respond story: substrate transition → audit fires → operator's next addressed turn reads the just-completed audit via `judgment_log.md` and responds with awareness (see Scenario H). The ~30-75s latency cost on addressed turns waiting behind a substrate-event audit is the tax for that coherence. If future production data shows operators frequently typing during mid-flight audits and complaining about the wait, a preemption policy could be introduced as an ADR amendment — but the current default is FIFO, deliberately.

Mechanical-mode wakes (`@primitive: SyncPlatformState()`) do NOT enter the queue. They execute directly without invoking the Reviewer (zero LLM cost, no concurrency-with-Reviewer concern).

### D4 — Pace declaration

Operator-authored substrate at `/workspace/context/_shared/_pace.yaml`:

```yaml
pace:
  kind: hourly | daily | weekly | continuous
  every: <ISO 8601 duration>    # optional; numeric override
```

Enum:
- `hourly` — drain paced lane ≤1 wake/hour.
- `daily` — drain paced lane ≤1 wake/day.
- `weekly` — drain paced lane ≤1 wake/week.
- `continuous` — no drain rate cap; paced lane drains as fast as scheduler can pull.

Numeric override (`every: 4h`) computes back to the nearest enum band for cockpit display.

Pace applies ONLY to paced lane (cron-tick judgment). Live lane is untouched — reactive judgment correctness requires immediate response to substrate transitions and operator addressing.

File format: yaml (machine-parsed config, per File Format Discipline §9 in CLAUDE.md — `_*.yaml` files are machine-parsed; integer/enum fields are typed, not strings).

### D5 — Pace as recurrence-population constraint at declaration time

Pace's authority is **enforced at recurrence declaration time**, not at runtime queue drain. This prevents the unbounded-queue-depth failure mode (where declared cron frequency exceeds drain rate and the paced lane grows indefinitely).

When the Reviewer calls `Schedule(action="create", schedule=<cron>)`, the system computes:
- The new recurrence's daily fire-frequency from its cron expression.
- The sum of existing scheduled recurrences' daily fire-frequency.
- The workspace's pace drain rate (e.g., daily pace = 1/day).

If total declared frequency exceeds drain rate, the `Schedule()` call fails with `{success: false, error: "pace_exceeded", message: "..."}`. The Reviewer surfaces a Clarify to the operator with alternatives (pause an existing recurrence, upgrade pace, skip this addition).

### D6 — Cross-source dedup at queue layer

The `wake_queue.dedup_key` column with `UNIQUE (user_id, wake_source, dedup_key)` constraint replaces migration-178-wake-dedup-key's `execution_events.wake_dedup_key`. Every enqueue computes a dedup key per its source's natural identity:

- `substrate_event` — `<revision_id>` of the matched `workspace_file_versions` row.
- `cron_tick` — `<slug>:<scheduled_minute>` (drops concurrent fires of the same recurrence in the same minute).
- `addressed` — `<message_id>` (drops accidental double-submits of the same operator message).
- `proposal_arrival` — `<proposal_id>`.
- `manual_fire` — null (operator explicitly bypasses dedup).

The cross-source case (substrate-event + addressed referring to the same operator intent) is **not deduped** — they have different dedup keys because they're different judgment shapes. Both run, serialized via single-in-flight.

**Load-bearing dependency: D6's non-dedup is only safe because of D1 (single-lane).** In a parallel-concurrent execution world, the un-deduped substrate-event + addressed pair would race for substrate writes — exactly the failure mode ADR-298 §1 identifies as motivating the queue. Single-lane drain serializes them: the second wake reads the first's output via `judgment_log.md` + `standing_intent.md` and stays coherent (see Scenario H). If a future ADR ever proposes relaxing D1 (e.g., "live-lane wakes have different dedup keys, why not parallelize them?"), the answer is no — the un-deduped cross-source pair would race again and the queue's whole coherence guarantee collapses. D6 and D1 are co-load-bearing; neither can be relaxed without revisiting the other.

### D7 — Bundle-declared minimum pace

Bundles declare a `minimum_pace:` field in their MANIFEST. The operator's declared pace at workspace activation must be ≥ bundle minimum, else activation fails with a Clarify.

```yaml
# docs/programs/alpha-trader/MANIFEST.yaml
minimum_pace: daily   # alpha-trader needs daily judgment for outcome-reconciliation + signal-evaluation
```

When multiple programs activate in one workspace, workspace pace = max of all active bundles' minimums (most-frequent constraint wins).

### D8 — Default pace at activation

At signup, before any program activates, workspace has no pace declared and no paced-lane work exists. On first program activation, pace defaults to the bundle's `minimum_pace`. Operator can override upward (faster), not downward (slower than the bundle requires).

If no program activates, no pace is enforced. Operator interacts only via live-lane sources (addressed, manual-fire).

### D9 — Hard ceilings: budget exhaustion + operator-set cap

Two cost-protection mechanisms layer on pace:

1. **Operator-set monthly budget** (optional, in `_pace.yaml`): `monthly_budget_usd: 50`. At 80% consumption: Reviewer Clarify ("at $40/$50 monthly budget; reduce pace or accept overage?"). At 100%: paced lane stops draining; live lane continues until billing-level hard cap.

2. **Billing-level hard cap** (system-enforced): when workspace billing is delinquent or system-wide budget exceeded, ALL queue drain stops. Workspace operates in read-only / mechanical-only mode until payment resolves.

Live-lane bursts (operator activity exceeding baseline) surface in cockpit as a "pace overrun" signal — operator-visible cost reality, not throttled. Honest information, not punitive throttling.

### D10 — Pricing model — meter-based, pace is descriptive

Pricing remains meter-based per token usage. Pace is a **cost-approximation tool**, not a subscription tier. Per-pace monthly cost estimates surface in cockpit as operator guidance, not as committed pricing.

This is the alpha-stage decision. A future ADR may revisit if usage data shows clean tier clustering that justifies a subscription model.

### D11 — Operator dial trifecta canonized

This ADR ratifies the three first-class operator levers as canon. Each maps to a different axiom dimension:

| Lever | Axiom dimension | Substrate file | What it controls |
|---|---|---|---|
| **Pace** | Trigger (Axiom 4) | `_pace.yaml` | How often the agent works |
| **Autonomy** | Mechanism (Axiom 5) | `_autonomy.yaml` | How much trust the agent has |
| **Persona** | Identity (Axiom 2) | `review/IDENTITY.md` + `review/principles.md` | How the agent reasons |

Three different dimensions, three different axioms, three different first-principles homes. No conflation. All three are operator-authored substrate. All three feed the Reviewer's wake envelope (per ADR-276). None substitutes for the others.

## 3. Evidence supporting ADR-261 D3 reversal

ADR-261 D3's parallel-concurrent guarantee protected against three scenarios. Production data across 4 active workspaces × 13 days shows:

| ADR-261 D3 guarantee | Production evidence | Verdict |
|---|---|---|
| Parallel concurrent sessions across recurrences | **0 distinct same-minute judgment fires in 13 days.** All same-minute collisions are mechanical-mode (no Reviewer) or duplicate-bug-events. | Theoretical protection — never materialized |
| Sub-minute scheduling precision | **3-47s jitter already exists** in production (cron-tick judgment fires land at avg 16-22s into the scheduled minute). Render Scheduler's `*/1 * * * *` polling already prevents true sub-minute precision. | Theoretical protection — production doesn't have it today |
| No head-of-line blocking | **0 colliding recurrences in production.** alpha-trader and alpha-author both stagger judgment recurrences hours apart. Honest cost: live-lane burst latency (~5min on 5-substrate-transition burst) — acceptable trade for coherent serialized writes. | Real cost on bursts; trade is favorable |

Source queries: `execution_events` filtered on `mode='judgment'` for the 2026-05-08 → 2026-05-21 window. See [canary v4 findings](../observations/2026-05-21-044500-canary-v4-substrate-event-revalidation/findings.md) + [wake-duplication audit](../observations/2026-05-21-005856-wake-duplication-audit/findings.md) + [round-budget population audit](../observations/2026-05-21-014009-reviewer-round-budget-population-audit/findings.md) for the data motivating this reversal.

The reversal is **prudential, not axiomatic**: single-lane is currently-best given observed failure modes (coherence + dedup + cost-control), not eternally-correct. If future production data shifts the failure-mode distribution, this decision should be revisited.

## 4. Amendment to ADR-261 D3

ADR-261 D3 §1–§3 architectural guarantees are reversed by this ADR:

| ADR-261 D3 guarantee | ADR-298 replacement |
|---|---|
| Parallel concurrent Reviewer sessions | **Single-lane Reviewer execution per workspace** (D1) |
| Sub-minute scheduling precision | **Pace-bounded drain rate** (D4–D5) — operator chooses precision-vs-coherence trade explicitly via pace declaration |
| No head-of-line blocking | **Single in-flight + two-lane drain** (D3) — live lane bypasses pace; reactive/addressed bursts accept ~30-75s serialization latency for coherence |

ADR-261 D3 §"Implementation shape" (per-recurrence Render Cron Jobs / pg_cron / single long-running scheduler service) is no longer relevant — the implementation shape becomes "queue + drainer," chosen at implementation PR time.

## 5. Implementation scope

### Code touched

| File | Change |
|---|---|
| `api/services/wake.py` | `submit_wake_proposal()` enqueues to `wake_queue` instead of dispatching |
| New: `api/services/wake_queue.py` | Queue enqueue / dequeue / lock / complete / GC operations |
| `api/jobs/unified_scheduler.py` | Becomes queue drainer: pulls next pending wake (paced respects pace; live FIFO), locks, invokes Reviewer, marks completed |
| `api/services/recurrence.py` | Walker enqueues due cron-tick wakes at paced lane |
| `api/services/wake_sources/*.py` | Each source's `submit_wake_proposal` call now enqueues (not direct dispatch) |
| `api/services/wake_evaluation.py` | Funnel logic preserved; output becomes enqueue-at-lane instead of dispatch |
| `api/services/primitives/schedule.py` | Add pace-population-constraint check before allowing `Schedule(action="create"\|"update")` |
| New: `/workspace/context/_shared/_pace.yaml` (operator-authored, machine-parsed) | Operator-authored pace declaration |
| New: `api/services/pace.py` | Pace parsing, drain-rate computation, recurrence-population check |
| `docs/programs/*/MANIFEST.yaml` | Each program declares `minimum_pace:` |
| New: cockpit Schedule tab section | Renders pace + queue depth + per-pace cost approximation |

### Schema migrations

- Migration N: create `wake_queue` table per D2 schema.
- Migration N+1: drop `execution_events.wake_dedup_key` after queue-side dedup wired (post-cutover).

### ADRs amended (status banners + supersede notes)

- ADR-261 D3 §1–§3 — guarantees inverted; amendment table inline (§4 above).
- migration-178-wake-dedup-key — `wake_dedup_key` location moved.
- ADR-296 v2 — wake sources enqueue rather than dispatch (load-bearing dispatch path change).

### Singular implementation discipline

The five wake sources' direct dispatch paths are DELETED. There is one entry point (`submit_wake_proposal` → enqueue) and one drainer (scheduler). No parallel paths. No "old dispatch + new queue" coexistence period.

## 6. Stress test scenarios (in-line)

### Scenario A — alpha-trader activation, operator declares weekly pace

Bundle `minimum_pace: daily`. Operator declares `weekly`. **Activation fails** with Clarify: "alpha-trader requires daily-pace minimum; declared weekly pace would prevent daily outcome-reconciliation. Switch to daily, choose a different program, or skip activation?"

### Scenario B — operator flips 10 drafts to ready_for_review in 30 seconds

10 substrate-event wakes enqueue at live lane within 30s. Reviewer drains one at a time at ~60s each. Total wall-clock: ~10 minutes for the last audit. Cost: 10 × $0.30 = $3 (same as today, no cost change). Coherence: serial audits, no parallel-write race. **Acceptable trade for coherence.**

### Scenario C — addressed turn during cron wake mid-flight

Cron-tick `outcome-reconciliation` fires at 05:00:00, takes 50s. Operator chats at 05:00:30. Chat enqueues at live lane but cron wake is locked (mid-flight). Chat waits 20s for cron to complete, then drains. **20s latency on chat; acceptable.**

### Scenario D — workspace with multiple programs

alpha-trader (minimum daily) + alpha-author (minimum weekly) activate in same workspace. Workspace pace = `daily` (max of minimums). Operator cannot drop to weekly without deactivating alpha-trader.

### Scenario E — operator changes pace mid-flight, denser

Operator on `daily`, switches to `hourly`. Existing scheduled recurrences continue at their declared cron schedules; pace allows new recurrences up to hourly density. Reviewer may propose new recurrences ("you've increased to hourly; want me to add a midday corpus-coherence check?") — operator authors or rejects.

### Scenario F — operator changes pace mid-flight, sparser

Operator on `daily`, switches to `weekly`. Existing 3 daily recurrences exceed weekly drain (3 > 1). Reviewer Clarify: "your 3 daily-cadence recurrences exceed new weekly pace budget. Pause 2 of them, change to weekly, or revert pace?" No auto-pause; operator decides.

### Scenario G — Reviewer authors a new recurrence; pace check fails

Reviewer calls `Schedule(action="create", schedule="0 14 * * *")` (daily). Existing recurrences: 2 daily, workspace pace: daily (1/day drain). New recurrence would be 3rd daily → exceeds drain rate. `Schedule()` fails with `{success: false, error: "pace_exceeded"}`. Reviewer surfaces Clarify to operator with alternatives.

### Scenario H — cross-source coherence

Operator flips draft `ready_for_review` (substrate-event wake enqueues at live lane). 5s later operator chats "hey, ready to publish?" (addressed wake enqueues at live lane). Both have different dedup keys, both enqueue, both drain in FIFO order. Substrate-event audit runs first (enqueued first); addressed turn runs after. Reviewer in addressed turn reads the just-completed audit in `judgment_log.md` and responds with awareness. **Coherent flow.**

### Scenario I — same-source cross-tick dedup

Walker scheduler ticks at 14:00:00 and 14:01:00. The 14:00 tick enqueues `corpus-coherence-check` with dedup_key `corpus-coherence-check:2026-05-21T14:00`. At 14:01 tick, walker re-checks: same recurrence still due? Dedup key `corpus-coherence-check:2026-05-21T14:00` already in queue → UNIQUE constraint blocks INSERT, silently dropped. **Cross-tick dedup works.**

### Scenario J — scheduler instance crashes mid-wake

Scheduler instance A locks a wake at 14:00:23, crashes at 14:00:45 before completing. Wake stays locked with `locked_at = 14:00:23`, `locked_by = <instance A>`. Scheduler instance B (next tick) checks for stale locks (`locked_at < now() - <threshold>`), reclaims the wake, sets `locked_by = <instance B>`, executes. **Stale-lock recovery prevents queue stalling.** Stale-lock threshold: open question for code-PR; ≥ longest expected Reviewer session + safety margin (population data shows current sessions 30-75s; ~180s threshold likely safe).

### Scenario K — budget exhaustion mid-burst

Operator on `pace: daily`, `monthly_budget_usd: 30`. Operator flips 50 drafts in one day (50 live-lane audits at $0.30 = $15). Cumulative monthly cost crosses 80% threshold at $24. Reviewer Clarify surfaces. Operator ignores. Cost crosses 100% at $30. Paced lane stops draining; live lane continues for remaining budget. At billing-level hard cap, all drain stops. Workspace in mechanical/addressed-only mode until budget extended.

### Scenario M — operator drops pace while paced-lane queue has pending wakes

Operator on `daily` with 4 daily-cadence recurrences active. Over a 24h period, 4 paced-lane wakes have queued (one per recurrence) but only 1 has drained (drain rate = daily = 1/day). Operator drops pace to `weekly`.

What happens to the 3 pending paced-lane wakes?

- **Pending wakes are NOT auto-dropped.** Dropping queued fires would mean the system silently discarding work the operator's recurrences scheduled — a substrate-aligned-execution violation.
- **Pending wakes drain at the new pace.** Drain rate immediately becomes weekly (1/week). The 3 pending wakes will drain over the next 3 weeks at 1/week.
- **Scenario F's Clarify mechanism handles the underlying recurrence reconciliation.** When operator drops pace to weekly, Scenario F's Clarify fires: "your 4 daily-cadence recurrences exceed new weekly pace budget. Pause 3, change them to weekly, or revert pace?" Operator's choice on recurrence-level cleanup determines whether new paced wakes continue accumulating; the existing queue contents drain at new pace regardless.
- **Cockpit signals the backlog.** "Paced lane: 3 pending, drain rate: weekly. Estimated time to clear: 3 weeks." Operator-visible cost reality, not silent backlog.

Combined effect: pace-change is a forward-looking policy change; existing queue contents honor the new policy from the moment of change but are not retroactively dropped. The operator-explicit recurrence reconciliation in Scenario F is the cleanup mechanism for the underlying frequency mismatch.

### Scenario L — queue is reconstructable from filesystem state (Axiom 1 check)

Database wiped accidentally. `wake_queue` table empty. Scheduler restarts:
- Walks `_recurrences.yaml` → recomputes due cron-tick wakes since last tick, re-enqueues at paced lane.
- Walks `_hooks.yaml` + recent `workspace_file_versions` (per migration-178-wake-dedup-key walker) → re-enqueues matched substrate-event wakes at live lane.
- Addressed turns in flight at time of wipe: lost (operator may re-send; meter-priced anyway).
- Proposal-arrival wakes for pending proposals: re-enqueued from `action_proposals` table state.

**Confirmation:** the queue table holds no semantic truth that doesn't exist elsewhere. Loss of queue contents is recoverable from filesystem + DB substrate. Axiom 1 alignment confirmed.

## 7. What this ADR does NOT do

- **Does not introduce queue-state-as-substrate.** The queue is transient compute (D2) per Axiom 1. Operator does not read queue contents as workspace state.
- **Does not change pricing model.** Pure meter remains. Pace is descriptive cost-approximation, not subscription tier.
- **Does not introduce concurrency across workspaces.** Each workspace has its own single-lane queue. Workspace A's wakes do not block Workspace B.
- **Does not affect mechanical-mode recurrences.** `@primitive: SyncPlatformState()` directives bypass the queue entirely (no Reviewer involvement, no LLM cost, no concurrency-with-Reviewer concern).
- **Does not require operator to declare pace at signup.** Pace defaults to bundle minimum on first activation. Pre-activation workspaces have no pace and operate only via live-lane sources.
- **Does not establish a new wake source.** The five sources from ADR-296 v2 are preserved; only their dispatch path changes (direct → enqueue).
- **Does not change the Reviewer's tool surface.** `Schedule` primitive gains a pace-check, but the action enum (`create | update | pause | resume | archive`) is unchanged.
- **Does not claim single-lane execution is axiomatically correct.** Single-lane is prudentially chosen by observed failure modes (§3). The discipline being locked in is "choose based on observed failure modes," not "single-lane forever."
- **Does not address durable execution / step-level memoization.** A Reviewer wake is the unit of retry; mid-wake failure means re-running all tool calls within the session. This is fine for the current Reviewer cost profile (30-75s sessions); if session duration grows past ~3min or tool-call cost dominates wake cost, step-level memoization becomes the next architectural seam. Scope for a future ADR. Inngest's per-LLM-call retry-with-persisted-result model is the mature shape to study when that ADR opens.
- **Does not address cross-workspace fairness.** When N workspaces all hit hourly pace and share an upstream LLM rate limit, contention behavior is unspecified. Within-workspace serialization is solved (D1 + D3); cross-workspace prioritization, throttling, and fairness are the next problem layer. Scope for a future ADR. OpenClaw's global concurrency lane + Inngest's multi-tenant throttling are the patterns to study when that ADR opens.

## 8. Open questions to resolve during code-PR

- **Stale-lock detection threshold.** Empirical-tuning target: 2× the p95 session duration from `execution_events.duration_ms` (population data shows current sessions 30-75s; p95 ≈ 75s suggests ~150-180s threshold). Recommend computing from telemetry at implementation time rather than picking a round number.
- **Cockpit Schedule tab UX shape.** Queue depth visibility? Per-pace cost estimate sub-line? Defer to FE PR.
- **Pace-overrun signaling.** Cockpit chip vs daily-update entry vs Reviewer Clarify? Probably all three at different thresholds.
- **Numeric pace override (`every: 4h`).** First iteration: parse + compute back to enum band for display + drain rate. Future: pure-numeric pace if operators consistently want fine-grained tuning.
- **GC interval for completed wakes.** 7 days mirrors `execution_events` retention; specific back-office task slug + cadence TBD.
- **Operator-set monthly budget rollout.** First iteration may ship without `monthly_budget_usd:` — billing-level hard cap is enough alpha-stage protection. Operator-set cap is a follow-on if operators ask.

## 9. Cross-references

- ADR-261 — recurrences-as-prompts (this ADR amends D3 §1–§3)
- migration-178-wake-dedup-key — substrate-event walker + wake_dedup_key (this ADR migrates dedup_key location)
- ADR-274 — Reviewer cadence-authoring (preserved; pace adds gating on Schedule calls)
- ADR-275 — introspection cadence Reviewer-authored from `_preferences.yaml` (preserved; Reviewer-authored recurrences pass through pace gate)
- ADR-276 — reactive-trigger envelope governance pre-load (preserved; `_pace.yaml` joins the envelope)
- ADR-296 v2 — wake architecture (5 wake sources preserved; dispatch path changes)
- ADR-194 v2 — Reviewer substrate (persona axis of the operator dial trifecta)
- ADR-209 — Authored Substrate (revision chain serializes substrate writes; queue serializes Reviewer judgments)
- ADR-231 D4 — thin scheduling-index precedent (queue follows this pattern: compute, not state)
- ADR-259 — feed surface (the outflow narrative the queue's coherent inflow makes coherent)
- ADR-293 — governance/operational substrate taxonomy (`_pace.yaml` joins the governance set alongside `_autonomy.yaml`)
- FOUNDATIONS Axiom 0 (six dimensions) — pace lives in Trigger dimension; autonomy in Mechanism; persona in Identity
- FOUNDATIONS Axiom 1 (filesystem-is-substrate) — `_pace.yaml` is substrate; `wake_queue` is transient compute per D2
- FOUNDATIONS Principle 18 — standing intent implies Trigger-authoring authority; pace constrains but does not remove the authority
- Production evidence: [canary v4 findings](../observations/2026-05-21-044500-canary-v4-substrate-event-revalidation/findings.md), [wake-duplication audit](../observations/2026-05-21-005856-wake-duplication-audit/findings.md), [round-budget population audit](../observations/2026-05-21-014009-reviewer-round-budget-population-audit/findings.md)
- Cross-system convergence evidence: [ADR-298 cross-analysis against OpenClaw, Hermes, and durable-execution platforms](../analysis/adr298-cross-analysis-openclaw-hermes-2026-05-22.md) — single-lane execution, two-lane drain, and queue-as-transient-compute are convergent with production agent-OS patterns; pace as first-class operator dial is YARNNN-distinctive net addition

## 10. Path to ratification

This ADR is Proposed. The path to Implemented:

1. **Discourse pass.** Re-read this ADR against scenario tests (§6). If any scenario breaks the thesis, document the failure inline and decide whether to revise or kill.
2. **Schema migration.** Written, reviewed, applied to dev workspace.
3. **Implementation PR.** Services + scheduler + primitives changes, atomic. ADR-261 D3 amendment lands in same PR (no dual-architecture state).
4. **Test gate.** Regression suite passes; canary fires through the new path end-to-end.
5. **Status flip to Implemented.**

Discourse-driven amendments to this ADR before implementation are expected. Pace enum granularity, default behavior at signup, monthly-budget rollout shape — all open for revision during discourse.
