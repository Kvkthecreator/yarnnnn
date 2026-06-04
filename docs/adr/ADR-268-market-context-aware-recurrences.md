# ADR-268: Market-Context-Aware Recurrences — Calendar-Native Scheduling for Market-Bound Programs

**Status**: Proposed 2026-05-13. Implementation in same commit as the ADR (atomic).

**Companion**: this ADR ships alongside L2 dispatch_specialist signature fix (one of the three layers in iter-2 observation [2026-05-13-iter2-three-layer-trade-execution-gap-kvk.md](../alpha/observations/2026-05-13-iter2-three-layer-trade-execution-gap-kvk.md)).

**Supersedes**:
- The implicit "encode US RTH in UTC cron expressions" pattern in the alpha-trader bundle's `_recurrences.yaml` (e.g., `"5 8 * * 1-5"` for signal-evaluation). The pattern was wrong-shaped (fired at 04:05 ET = pre-market, missed RTH), DST-drift-fragile (UTC encoding doesn't track EDT↔EST), and bundle-specifically-fitted to US equities. This ADR replaces it with a semantic vocabulary that resolves against a bundle-declared market context.

**Amends**:
- ADR-261 D1 (recurrences shape `{slug, schedule, mode, prompt}`) — preserved. `schedule` is still a single string field; this ADR enriches the *vocabulary* of that string with a `@`-prefixed semantic form. No new fields on the Recurrence dataclass.
- ADR-223 (program bundle specification) — extends MANIFEST.yaml schema (still `schema_version: 1`) with an optional `market_context:` block. Bundles without the block use plain-cron-only and continue to work unchanged.

**Preserves**:
- FOUNDATIONS Axiom 4 (Trigger). The recurrence's trigger axis is unchanged; this ADR clarifies the *when* that trigger fires.
- ADR-209 Authored Substrate. No changes to revision-chain semantics.
- ADR-260 real-time Reviewer loop. Wake mechanism unchanged.
- ADR-262 filesystem-native output topology.
- ADR-263 judgment/mechanical mode distinction.
- ADR-264 SyncPlatformState. Mechanical mirrors stay mechanical; only their schedules become semantic.

---

## 1. Why this ADR

The alpha-trader program runs against US equities. US equities have structural trading hours (NYSE/NASDAQ RTH 09:30–16:00 ET, Mon–Fri, minus US market holidays). Every signal evaluation, every position-state mirror, every pre-market brief, every post-close reconciliation is anchored to one of those structural times — not to abstract UTC clock-time.

Today the alpha-trader bundle's `_recurrences.yaml` tries to encode that structure by hand-rolling UTC cron expressions:

```yaml
- slug: signal-evaluation
  schedule: "5 8 * * 1-5"          # 08:05 UTC
```

The encoding is wrong on three independent axes:

1. **Wrong time-of-day**: 08:05 UTC = 04:05 ET = pre-market, before NYSE/NASDAQ even opens. Signal evaluation against pre-market bars is meaningless for an alpha-trader strategy targeted at RTH price action. The intent was "after market open" but the cron has it 5h25min before market open. Operator reading the bundle has no way to spot the error short of doing the timezone math themselves.

2. **Wrong DST behavior**: UTC encoding doesn't track EDT↔EST transitions. Even if "08:05 UTC = 04:05 ET" were correct for one half of the year, the other half it would be 03:05 EST or 05:05 EDT depending on which half. The bundle author has to re-author cron strings twice a year, or accept that fires drift by an hour seasonally.

3. **No holiday awareness**: cron fires every weekday. US markets close on ~10 holidays per year (MLK, Presidents Day, Good Friday, Memorial Day, Juneteenth, Independence Day, Labor Day, Thanksgiving, Christmas, New Year's). Recurrences fire on these days, do nothing useful, burn LLM cost (judgment mode) or API quota (mechanical mode). Reviewer logs a confused failure ("markets are closed, no bars to evaluate").

The 2026-04-27 observation already named this as "structural problem (no markets-closed gate) won't fix itself." It's been a known gap for 16 days. Iter-2 of the steered closed-loop development pass surfaced it as one of three layers blocking trade execution on kvk's workspace.

Beyond the alpha-trader-specific problem, there's a forward-looking concern: the architecture should not be accidentally fitted to US equities. Future bundles will target Korean equities (KRX 09:00–15:30 KST, different holidays), crypto (24/7, never closed), futures (Sun 18:00 ET open through Fri 17:00 ET close, brief daily breaks), FX (24/5). A market-context system designed for US equities by hand-rolled cron arithmetic doesn't scale to those markets without re-doing the work each time.

This ADR commits a structural market-context system that is **bundle-declared, semantically-scheduled, and multi-market forward-compatible**.

---

## 2. The single principle

> **Market hours are a property of the program, not of the recurrence. Bundles targeting a specific market declare that market's context (timezone, sessions, calendar). Recurrences within those bundles schedule against semantic anchors (`@market_open`, `@market_close`, `@every N during session`), which resolve to UTC at materialize-due time using the bundle's market context. Plain UTC cron remains the escape hatch for market-agnostic recurrences. The substrate stays single-shaped; the vocabulary of the `schedule` field expands.**

> **Behavioral synthesis:** this ADR is the *scheduling-plane* (Plane 1) instance of the broader three-plane temporal model. For how time reaches an agent's *reasoning* (Plane 2 perception) and *action gating* (Plane 3), and how to think about temporal behavior across all programs, see the singular synthesis at [`cadence-and-wakes.md` §8b](../architecture/cadence-and-wakes.md#8b-temporal-model--how-time-reaches-agent-behavior).

Three consequences:

1. **One new optional block on MANIFEST.yaml**: `market_context:`. Declares timezone, session windows, calendar key. Bundles without it use plain cron only — backward compatible.
2. **One new schedule vocabulary** on recurrences: `@`-prefixed semantic times. Resolved at materialize-due time, not stored as resolved UTC. DST + holidays are computed at resolution time so the result is always correct for the current date.
3. **One canonical resolution path**: `scheduling.py::compute_next_run_at` extends to recognize `@`-prefixed schedules and resolve them via a new `market_calendars.py` module. All other code paths (dispatcher, Reviewer, Schedule primitive) see fully-resolved UTC and require no changes.

---

## 3. Decision

### D1 — Bundle MANIFEST gains an optional `market_context:` block

```yaml
# docs/programs/{slug}/MANIFEST.yaml
schema_version: 1
slug: alpha-trader
# ... existing fields preserved ...

market_context:
  exchange: us_equities                   # canonical key; informational
  timezone: America/New_York              # IANA name; resolves DST
  sessions:
    regular_hours: { open: "09:30", close: "16:00" }
    pre_market:    { open: "04:00", close: "09:30" }
    after_hours:   { open: "16:00", close: "20:00" }
  trading_days: weekdays                  # weekdays | all_days
  calendar: nyse_us                       # holiday-calendar key (see D4)
```

**Required fields when `market_context:` is present**: `timezone`, `sessions.regular_hours`, `trading_days`, `calendar`. `exchange` is informational. `pre_market` + `after_hours` are optional (used only if a recurrence references them).

**Absent `market_context:`**: bundle declares itself market-agnostic. Recurrences in this bundle MUST use plain UTC cron (no `@`-prefix). A semantic schedule with no market context is a parse error.

### D2 — Three semantic schedule constructs (minimal v1)

The `schedule` field on a recurrence accepts any of:

**A. Plain UTC cron** (existing, unchanged):
```yaml
schedule: "0 7 * * *"
```
Fires per the cron expression. Market-agnostic. Holiday-agnostic. Use for daily housekeeping (narrative-digest, morning-reflection), weekly reviews, etc.

**B. Anchored to session boundary**:
```yaml
schedule: "@market_open"              # at the open
schedule: "@market_open + 15min"      # 15 minutes after open
schedule: "@market_open - 30min"      # 30 minutes before open
schedule: "@market_close"             # at the close
schedule: "@market_close + 1h"        # 1 hour after close
schedule: "@pre_market_open"          # at pre-market open
schedule: "@after_hours_close - 10min"
```

Resolves to the next valid trading-day occurrence in UTC. Skips non-trading days (weekends, holidays per the bundle's calendar).

Grammar: `@<session>_<edge>` `[+|-]` `<N>` `<unit>` where:
- `<session>` ∈ {`market`, `pre_market`, `after_hours`}
- `<edge>` ∈ {`open`, `close`}
- `<N>` is a positive integer
- `<unit>` ∈ {`min`, `h`}
- Offset clause (`+ Nunit` / `- Nunit`) is optional.

Note: `@market_open` is an alias for `@regular_hours_open` (the common case). Same for `@market_close`. Operators rarely need the longer form.

**C. Interval within a session**:
```yaml
schedule: "@every 1min during regular_hours"
schedule: "@every 5min during regular_hours"
schedule: "@every 10min during pre_market"
```

Resolves to fires every N minutes between the session's open and close, on trading days only. The first fire of each session is at session-open exactly (so `@every 1min during regular_hours` produces a 09:30, 09:31, 09:32, ... sequence).

Grammar: `@every <N> <unit> during <session>` where `<session>` ∈ {`regular_hours`, `pre_market`, `after_hours`}.

### D3 — Resolution happens at `scheduling.py::compute_next_run_at`

The single existing chokepoint for next-run computation. Pseudocode:

```python
def compute_next_run_at(rec, last_run_at, now, market_context=None):
    schedule = rec.schedule
    if schedule is None:
        return None  # reactive-only, no scheduling
    if schedule.startswith("@"):
        if market_context is None:
            raise ScheduleParseError(
                f"recurrence {rec.slug!r} uses semantic schedule {schedule!r} "
                f"but bundle has no market_context — cannot resolve"
            )
        return resolve_semantic_schedule(
            schedule, market_context, last_run_at, now,
        )
    # Plain cron path — existing behavior, unchanged
    base = last_run_at or now
    return croniter(schedule, base).get_next(datetime)
```

`market_context` is loaded once per scheduler tick from the workspace's active bundle MANIFEST (cached via `bundle_reader`). One bundle per workspace per ADR-244.

### D4 — Market calendars live in `api/services/market_calendars.py`

New module owns the holiday-calendar registry + lookup:

```python
# api/services/market_calendars.py

CALENDARS: dict[str, MarketCalendar] = {
    "nyse_us": NyseUsCalendar(),
    # "korea_krx": KoreaKrxCalendar(),  # future
    # "crypto_24x7": Always Open,        # future
}

class MarketCalendar:
    def is_trading_day(self, date: date) -> bool: ...
    def session_window(self, date: date, session: str, tz: ZoneInfo) -> tuple[datetime, datetime]: ...
```

**Initial implementation: hand-rolled `NyseUsCalendar` with explicit 2026 + 2027 holiday dates inline.** The US-equities holiday set is small (~10 dates/year + Good Friday floating), well-documented, and stable. Hand-rolling avoids adding `pandas-market-calendars` as a dependency for one consumer. If/when a second market (Korean equities, futures) lands, evaluate `pandas-market-calendars` or `exchange-calendars` at that point — singular implementation discipline says don't add the dep until extension demand surfaces.

Holiday calendar must be refreshed manually: when 2028 approaches, add 2028 holidays to the inline list. This is acceptable for the alpha-1 timeframe (alpha-1 success contract is 90-day rolling window per SCOPE.md; we'll know well before 2028 whether the project survives).

### D5 — Recurrence dataclass gets NO new fields

`Recurrence` dataclass remains `{slug, schedule, prompt, mode, paused, options}` per ADR-261 D1 + ADR-263 D1. The `schedule` field is still `Optional[str]`. The new vocabulary lives inside that string. This preserves the "one shape" axiom of ADR-261.

### D6 — Dispatcher does no runtime market-hours check (compile-time only)

By design, semantic schedules resolve to UTC times that are already RTH-aligned. The dispatcher fires the recurrence at the resolved UTC time without re-checking "is the market open right now." This is the simpler architecture: one source of truth (the semantic resolver), no defense-in-depth gate that could disagree.

Plain-cron recurrences fire whenever the cron says — they're operator-asserted market-agnostic. If an operator authors a plain cron that fires during market-closed hours and expects it to silently skip, that's an authoring mistake the system surfaces by *not* skipping (the recurrence fires, the Reviewer or mechanical handler reports "no market data available," operator sees the noise and reauthors with `@`-syntax).

**The trade-off**: if a market has an unscheduled early-close (rare — usually Black Friday half-day or Christmas Eve, which are typically known in advance and in the calendar), a `@market_close - 30min` fire could be inaccurate by ~3h. Acceptable risk for v1; if it surfaces as a problem, add a defense-in-depth check in a follow-up ADR.

### D7 — Default behavior with no `market_context`

Backward-compatible by construction. Every existing bundle (alpha-trader pre-this-ADR, alpha-commerce, future bundles that don't need market awareness) declares no `market_context:` block. Recurrences in those bundles use plain UTC cron exclusively, and `compute_next_run_at` takes the existing plain-cron path. **Nothing changes for bundles that don't opt in.**

A bundle gains market-context awareness by *only one* additive operation: adding the `market_context:` block to MANIFEST.yaml + rewriting its recurrences to use `@`-syntax where appropriate. There is no migration step, no schema_version bump, no compatibility shim.

### D8 — Alpha-trader bundle migration

Rewrite `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml` per the following intent map. Operator (KVK) reviews + adjusts the exact times when authoring intent diverges:

| Slug | Old schedule (UTC) | New schedule | Intent |
|---|---|---|---|
| `track-universe` | `0 8,11,15 * * 1-5` | `@market_open + 15min`, `@market_open + 3h`, `@market_close - 1h` | Three RTH snapshots: post-open, midday, pre-close |
| `signal-evaluation` | `5 8 * * 1-5` (pre-market!) | `@market_open + 15min` | Post-open, after price discovery settles |
| `pre-market-brief` | `15 8 * * 1-5` (pre-market) | `@market_open - 30min` | 30 min before open, with overnight context |
| `track-positions` | `* * 9-16 * 1-5` (wrong UTC range) | `@every 1min during regular_hours` | Every minute during RTH |
| `track-orders` | `* * 9-16 * 1-5` | `@every 1min during regular_hours` | Every minute during RTH |
| `track-account` | `*/5 * 9-16 * 1-5` | `@every 5min during regular_hours` | Every 5 min during RTH |
| `outcome-reconciliation` | `0 5 * * *` (12:00 AM ET) | `@market_close + 1h` | 1h after close, fills settled |
| `narrative-digest` | `0 3 * * *` | unchanged (plain cron) | Daily housekeeping, market-agnostic |
| `morning-reflection` | `0 7 * * *` | unchanged | Market-agnostic |
| `morning-calibration` | `0 6 * * *` | unchanged | Market-agnostic |
| `proposal-cleanup` | `0 4 * * *` | unchanged | Market-agnostic |
| `weekly-performance-review` | `0 18 * * 0` | unchanged | Weekly, market-agnostic |
| `quarterly-signal-audit` | `0 18 31 3,6,9,12 *` | unchanged | Quarterly |
| `trade-proposal` | `null` (reactive) | unchanged | Reactive, no schedule |

Multiple-fire-per-day recurrences (`track-universe` with three semantic anchors) are represented by listing the recurrence three times with different `schedule` values, or by supporting a list-of-schedules field. **Decision: support a list-of-schedules form** for cleaner authoring:

```yaml
- slug: track-universe
  schedule: ["@market_open + 15min", "@market_open + 3h", "@market_close - 1h"]
  mode: judgment
  prompt: |
    Refresh fundamentals for every ticker ...
```

When `schedule` is a list, the scheduler computes the next-run-at as the minimum of each member's individually-resolved next time. Implementation detail; doesn't affect the substrate shape (`Recurrence.schedule` becomes `Optional[Union[str, list[str]]]`).

### D9 — Implementation surface

Atomic single commit:

1. **MANIFEST schema**: add `market_context:` to `docs/programs/alpha-trader/MANIFEST.yaml`. Pure additive.
2. **`api/services/market_calendars.py`** (new): `NyseUsCalendar` class with inline 2026 + 2027 holidays. ~120 LOC.
3. **`api/services/scheduling.py`**: extend `compute_next_run_at` to dispatch on `@`-prefix. New helper `resolve_semantic_schedule()` parses and resolves. ~150 LOC additions.
4. **`api/services/recurrence.py`**: `Recurrence.schedule` typed as `Optional[Union[str, list[str]]]`. Parser accepts both shapes. ~20 LOC changes.
5. **`api/services/bundle_reader.py`**: helper `get_market_context_for_user(client, user_id) -> Optional[dict]` reads the workspace's active bundle's MANIFEST.market_context. ~30 LOC.
6. **`docs/programs/alpha-trader/reference-workspace/_recurrences.yaml`**: rewrite per D8 table. ~50 LOC changes.
7. **L2 fix** (coupled per iter-3 design decision): `api/services/primitives/dispatch_specialist.py:185` — fix `agent_role=role` → `agent={"role": role}`. Minimal change that lets specialists at least launch even before L3 (capability-flow wiring) ships. ~3 LOC.
8. **Regression gate** `api/test_adr268_market_context.py`: parse correctness + resolution correctness + holiday handling + backward-compat (no-market-context bundle still parses). ~120 LOC.

Total: ~500 LOC across 8 files. One commit.

### D10 — Operator-side change after deploy

After the commit deploys to Render:

1. `reset.py kvk --confirm` — purges kvk's workspace; auto-re-forks alpha-trader with the new bundle YAML.
2. `connect.py kvk` — reconnect Alpaca paper EE8K.
3. `verify.py kvk` — expect 32/32 invariants pass.
4. Wait for next semantic-scheduled fire — first should be a mechanical mirror (track-positions) at next RTH open + 1min, which is ~22:31 KST tonight Wed 2026-05-13. If we're past 22:30 KST when this commits, the very next minute fires.
5. Observe substrate writes to `/workspace/context/portfolio/positions/` to confirm mechanical-mirror loop is alive against the new schedule.
6. Watch for signal-evaluation at `@market_open + 15min` on Thu morning KST (22:45 KST Wed = 09:45 ET Wed = first RTH fire post-deploy).

---

## 4. Out of scope (explicit deferrals)

These are real concerns but not iter-3 scope:

- **L3 capability-flow wiring** (Recurrence dataclass `required_capabilities` field, DispatchSpecialist input schema, Reviewer prompt awareness). This is the "specialist receives platform_trading_get_market_data" problem from iter-2. L2 unblocks specialist launch; L3 unblocks specialist tool surface. Sized for iter-4 with its own ADR pass.
- **Multi-market bundles** (one bundle targeting multiple exchanges simultaneously). Not a real need until alpha-2+; design under "one bundle, one market_context" until pressure surfaces.
- **Calendar drift / auto-update** (pulling NYSE holidays from a live source). Hand-rolled inline calendar is fine for alpha-1; revisit when alpha-2 approaches 2028.
- **Cross-day session boundaries** (futures markets, FX). v1 vocabulary assumes session opens and closes on the same calendar day. Futures session "Sun 18:00 ET → Fri 17:00 ET" needs richer grammar; deferred to a future ADR when a futures bundle is in scope.
- **Half-day sessions** (Black Friday early close, Christmas Eve). Holiday calendar treats these as full trading days currently; fires scheduled for the normal close time would fire after-hours. Acceptable v1 limitation. Mitigation: operator can manually skip the half-day by adding to bundle's holiday list temporarily.
- **Workspace overlay of market_context** (operator overrides bundle-declared market_context). Not in scope — market context is a program property; operators wanting a different market run a different program.

---

## 5. Dimensional classification (FOUNDATIONS Axiom 0)

**Primary**: **Trigger** (Axiom 4) — refines the *when* of recurrence firing without changing the *what* or *who* dimensions.

**Secondary**: **Substrate** (Axiom 1) — the MANIFEST.yaml `market_context:` block is operator-readable filesystem-native declaration; the holiday calendar is code-resident (acceptable for slow-changing data per "computed at runtime" carve-out).

**Tertiary**: **Channel** (Axiom 6) — Reviewer wakes happen at meaningful market times; operator-facing recurrence list at `/work` or in `_recurrences.yaml` reads as market-anchored intent rather than UTC-arithmetic puzzles.

---

## 6. Why this won't reinvent prior work

Audit done 2026-05-13 of prior ADRs touching market-hours / scheduling:

- **`api/services/risk_gate.py` execution-gate market-hours** — partial market-hours awareness at the *execution gate* (post-proposal, pre-order). This ADR adds market-hours awareness at the *scheduling layer* (pre-recurrence-fire). The two layers are complementary. **Update (2026-06-04, finding `docs/evaluations/2026-06-04-temporal-awareness-kernel-vs-program-audit/`):** the execution gate's hand-rolled `_is_us_market_hours()` approximation (DST-blind, holiday-blind) was deleted and the gate now routes through this ADR's kernel calendar primitive (`market_calendars.NyseUsCalendar.is_open_now`). Both layers now share one DST-/holiday-correct source of truth.
- **`docs/alpha/observations/2026-04-27-trader-rls-fix-signal-eval-hang.md`** — observed the structural gap and explicitly named it deferred ("won't fix itself by re-triggering"). This ADR closes that deferral.
- **ADR-263 §"Two operator scenarios" example schedule** `"0 * 9-16 * 1-5"` — the example schedule in ADR-263 was descriptively-correct for a US-RTH-like window but encoded by hand-rolled UTC. This ADR replaces the encoding pattern; ADR-263's principles (mode authoring intent, judgment vs mechanical) are preserved.
- **ADR-187 (Alpaca integration)** — specifies the trading platform but does not specify schedule semantics. No conflict.

No prior ADR has shipped a market-context system. This is net-new ground; prior work is gap-acknowledgment, not gap-resolution.

---

## 7. Revision history

| Date | Change |
|------|--------|
| 2026-05-13 | v1 Proposed. Same-day implementation: minimal vocabulary (`@market_open[±Nmin]`, `@market_close[±Nmin]`, `@every Nmin during {session}`), compile-time resolution, hand-rolled NYSE calendar, alpha-trader bundle migration, L2 dispatch_specialist fix coupled. Surfaced from iter-3 of the steered closed-loop dev pass after iter-2 identified market-hours as one of three structural blocks to trade execution on kvk's workspace. |
