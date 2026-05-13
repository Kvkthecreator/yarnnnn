# Session Carry — 2026-05-13 → next session

> **⚠️ DELETE THIS FILE after front-loading context into the new session.**
> This is an ephemeral hand-off artifact, not canonical documentation.
> Everything load-bearing is already in CHANGELOG + observation docs + ADRs.
> This file is the *narrative thread* that ties them together for resumption.

---

## TL;DR — where we are

Today's session shipped **9 commits** that resolved the cold-start activation problem on alpha-trader end-to-end, fixed three Python crashes in DispatchSpecialist that had been silently broken since 2026-05-10 (PR #9 squash), and restored cost-discipline mechanisms (cache markers + per-recurrence round budgets) that the same PR #9 dropped. Verified live on seulkim88 persona.

**One real architectural gap remains**: specialist LLMs are exiting their dispatch loops early without persisting the substrate the bundle prompt requested. The infrastructure works; the *prompt/brief discipline at the Reviewer→Specialist boundary* is the next gate.

You stopped before any code on this gap and asked for the carry doc. The discourse on which architectural layer to fix is teed up (Layer 1 bundle / Layer 2 Reviewer brief composition / Layer 3 specialist role prompt). Diagnostic A is the agreed first move.

---

## Commits today (in order)

| Commit | Scope | Status |
|---|---|---|
| `914086f` | ADR-270: `fire_on_activation` scheduler extension + alpha-trader bundle changes + falsify-signals research recurrence | Implemented + verified |
| `f9e79c9` | Initial verification findings (pre-credentials) | Doc |
| `8045238` | Full E2E findings post-credentials — surfaced Gate 1 (`tool_uses_raw`) | Doc |
| `16dcd5f` | **Fix 1**: `tool_uses_raw` AttributeError in dispatch_specialist | Verified working |
| `9d85d12` | **Fix 2**: `ToolUseBlock.get()` AttributeError in dispatch_specialist | Verified working |
| `1f41279` | track-regime first E2E success documentation | Doc |
| `5225165` | Cold-start verification doc — load-bearing answer to ADR-270's central question | Doc |
| `cf5bb69` | **Fix 3**: dispatch_specialist cache markers (A) + per-recurrence max_rounds (B) | A verified, B mechanically correct but inert today |
| `d90ab72` | cf5bb69 verification outcome — A works, B inert, next gate is brief composition | Doc |
| `85035a8` | **Fix 4**: Reviewer-side cache markers (same pattern as cf5bb69 A) | Test gate passes; not yet log-verified live |

ADR-269 regression gate: **108/108 PASS** (was 74 at start of day).

---

## What's verified working end-to-end

**The cold-start infrastructure is fully resolved.** Within ~5 minutes of activation on a clean seulkim88 workspace:

- `track-account` fires → `/workspace/context/portfolio/_account.yaml` populated with real Alpaca broker data (PA3D05L0X4DJ, equity numbers from API)
- `track-regime` fires → `/workspace/context/trading/_regime.yaml` + raw bar caches populated (VIXY/SPY 1Day bars, computed SMAs, regime predicate correctly classified)
- Reviewer + DispatchSpecialist + Alpaca + WriteFile chain produces canonical substrate with `authored_by="ai:reviewer"` per ADR-209
- Sonnet specialist hits 59-67% cache on rounds 2+ (verified in Render logs — Anthropic's prompt cache fires as ADR-171 pricing assumes)

**Pre-ADR-270 baseline**: activation was silent for up to 11.5 hours (waited for next periodic cron). **Post-ADR-270**: operationally productive workspace in under 5 minutes.

---

## What's NOT yet working (the gap to resume on)

Two of four activation-fired recurrences fire cleanly but **don't write the spec'd substrate**:

- `track-universe` (5-ticker fundamentals refresh) — specialist fetches bars, exits at 5 rounds without calling WriteFile, no `{ticker}.yaml` files produced
- `falsify-signals` (5-signal × 5-ticker × 90d historical falsification) — specialist runs 5 rounds / 14 platform tool calls (all `platform_trading_get_market_data`), zero WriteFile calls, no `/workspace/research/findings/{signal_id}.md` files produced

Critical observation: **the specialist exits early via natural `stop_reason != "tool_use"`, not via round-budget exhaustion.** The `max_rounds: 12` (track-universe) and `max_rounds: 20` (falsify-signals) declared in the bundle are correctly wired through (ADR-269 gate proves the threading) but inert because the specialist *decides* it's done before hitting the ceiling.

Reviewer's defer entry on the falsify-signals fire:
> *"specialist executed (5 rounds, 14 platform API calls) but produced no output files to /workspace/research/findings/."*

The specialist fetches data, summarizes inline, and returns terminal text **without persisting per-file substrate**.

---

## The design-shape discourse (where to resume)

The gap is at the **Reviewer→Specialist boundary**, not in the kernel mechanics. Three possible layers where the fix could live:

| Layer | Hypothesis | Fix shape |
|---|---|---|
| **L1 — Bundle prompt** | Operator's recurrence prompt isn't emphatic enough about "write per-file before terminating" | Tighten falsify-signals + track-universe prompts to lead with the write directive. Bundle-only, no kernel change. |
| **L2 — Reviewer brief composition** | Reviewer paraphrases the bundle prompt when authoring the specialist's brief and drops the WriteFile emphasis | Reviewer prompt change: "preserve operator's file-write directives verbatim when composing specialist briefs." |
| **L3 — Specialist role prompt** | Universal specialist role doesn't strongly instruct "persist substrate before terminating" | Tighten `_SPECIALIST_FRAME` in dispatch_specialist.py. Kernel-side, affects every specialist invocation across every program. |

**The architecturally-honest test, per ADR-176 + ADR-216**:

The DispatchSpecialist tool schema explicitly says: *"brief: Focused brief: what to produce, where to read from, where to write to. The Reviewer's standing context is NOT injected — the brief carries everything the specialist needs to know."*

→ The Reviewer is contractually supposed to author a complete brief. If the brief is dropping the WriteFile directive, **the Reviewer is failing its tool contract** — which makes L2 the architecturally correct fix layer, *if* the diagnostic confirms.

### Diagnostic A — the agreed next move

**Pull Render logs for the falsify-signals specialist invocation and read the actual `brief` field** that the Reviewer passed to DispatchSpecialist. 10 minutes of log-reading tells us in three flavors:

1. **Brief preserves WriteFile directive clearly** → specialist LLM is the failure layer → L3 fix (role-level prompt tightening) or stronger ("specialist must call WriteFile before terminating if brief mentions files")
2. **Brief paraphrases without the directive** → Reviewer is the lossy layer → L2 fix (Reviewer prompt: "preserve operator's file-write directives verbatim")
3. **Brief contains directive but specialist still ignores** → most concerning — model itself isn't complying. Could need a structural change like "specialist's terminating round must include a WriteFile or it's not terminal."

**Specific log query for the next session:**

```
mcp__render__list_logs:
  resource: ["crn-d604uqili9vc73ankvag"]
  text: ["falsify-signals", "DispatchSpecialist", "brief"]
  startTime: 2026-05-13T07:43:30Z
  endTime: 2026-05-13T07:46:00Z
```

The Reviewer's `tool_use` invocation against DispatchSpecialist contains the `input.brief` field as part of the request payload. Some Render log lines do echo tool inputs at info level. If not visible at info, may need to add a one-line log statement in `dispatch_specialist.py::handle_dispatch_specialist` (`logger.info("[DISPATCH_SPECIALIST] brief=%s", brief[:500])`) and re-run the cycle.

---

## Open follow-on items (smaller scope, after the main discourse resolves)

| Item | Scope | Notes |
|---|---|---|
| **Verify Reviewer caching live** (commit `85035a8`) | 5 min | Wait for next Reviewer wake post-deploy; Render log grep for `TOKENS.*haiku.*cache_read`. Expect non-zero on rounds 2+. Fix is byte-identical to the cf5bb69 A pattern that's already verified working — high-confidence, just needs a log confirmation. |
| **Substrate-write-failure-recorded-as-success** scheduler interaction | Design call + small change | When dispatcher records `last_run_at` on body-failure, fire_on_activation thinks it succeeded and never retries. Flagged earlier; deferred. |
| **Cost-truth telemetry productization** | Bigger | Currently audit cost via `SELECT cost_usd FROM token_usage` ad-hoc. SCOPE.md commits to cost-truth alongside money-truth for Alpha-2 live-trading decision. Worth its own iter. |
| **Re-fire on substrate-success rather than dispatch-completion** | Real scheduler-discipline change | Today: `last_run_at` set on dispatch return regardless of body outcome. Better: `last_run_at` set only when body produced spec'd substrate. Removes the silent-failure trap fire_on_activation exposed. |
| **Manual top-up automation** | Trivial productization | Currently `UPDATE workspaces SET balance_usd = ...` via psql. Worth a `/admin/topup` route or alpha-ops harness command. |

---

## Critical context for the next session

### Persona under test
- `seulkim88@gmail.com` → persona slug `alpha-trader`
- `user_id = 2be30ac5-b3cf-46b1-aeb8-af39cd351af4`
- `workspace_id = b7e1b9bc-ffb3-478e-bd05-dcae01a8a6b1` (note: prior to today's resets — current workspace_id may differ; check)
- Alpaca paper account suffix `X4DJ`, credentials in `api/.env.alpha-ops` under `ALPHA_TRADER_ALPACA_KEY` / `_SECRET` (already uncommented from earlier session)

### Balance state
Last topped up to $20 this session. Some spent on cf5bb69 verification cycle. Check `SELECT balance_usd FROM workspaces WHERE owner_id = '2be30ac5-...'` before any re-fire.

### Render workspace
`tea-cspsq5ogph6c73f4m8t0` (only one available). Auto-selects.

### Service IDs
- API: `srv-d5sqotcr85hc73dpkqdg`
- Unified Scheduler: `crn-d604uqili9vc73ankvag`
- MCP Server: `srv-d6f4vg1drdic739nli4g`
- Output Gateway: `srv-d6sirjffte5s73f90pfg`

### Database access
Connection string in `docs/database/ACCESS.md`. URL-encoded password.

### Harness commands (from `api/scripts/alpha_ops/`)
```bash
python api/scripts/alpha_ops/reset.py alpha-trader --confirm
python api/scripts/alpha_ops/activate_persona.py --persona alpha-trader
python api/scripts/alpha_ops/connect.py alpha-trader        # needs env sourced
python api/scripts/alpha_ops/verify.py alpha-trader
```

`reset.py` auto-re-forks the program (calls `initialize_workspace(program_slug=...)`). Workspace row gets recreated with default `balance_usd = 3.00` so top up after reset, before re-fire.

---

## Files touched today (high-level)

### Code
- `api/services/scheduling.py` — `fire_on_activation` conditional (ADR-270)
- `api/services/primitives/dispatch_specialist.py` — three fixes: `tool_uses_raw`, `ToolUseBlock.get()`, cache markers + max_rounds
- `api/agents/reviewer_agent.py` — recurrence_options threading + cache markers (latest)
- `api/test_adr269_capability_flow.py` — extended to 108 assertions

### Bundle
- `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml` — `fire_on_activation: true` + `max_rounds` on heavy recurrences + new `falsify-signals` recurrence
- `docs/programs/alpha-trader/reference-workspace/review/principles.md` — rules 6+7 for regime gating
- `docs/programs/alpha-trader/reference-workspace/research/mandate.md` (new)
- `docs/programs/alpha-trader/reference-workspace/specs/falsify-signals.md` (new)
- `docs/programs/alpha-trader/reference-workspace/specs/regime-state.md` (from prior session today)

### Docs
- `docs/adr/ADR-270-fire-on-activation-recurrences.md` (new)
- `docs/adr/ADR-233-shape-driven-invocation-lifecycle.md` (status banner updated)
- `docs/alpha/observations/2026-05-13-activation-fire-wiring.md` (live observation log — read this for full narrative)
- `api/prompts/CHANGELOG.md` entries `[2026.05.13.2]` through `[2026.05.13.7]`

### Operator credentials
- `api/.env.alpha-ops` — `ALPHA_TRADER_ALPACA_KEY` / `_SECRET` uncommented (gitignored, local only)

---

## What was deliberately NOT done

- **No new ADR for the cache+max_rounds fixes** (cf5bb69, 85035a8). Restoring documented prior behavior + matching `fire_on_activation` precedent. Operator confirmed no ADR needed.
- **No FOUNDATIONS amendment** for fire_on_activation. The activation event uses the existing periodic trigger path with `next_run_at = now`. No new sub-shape, no axiom change.
- **No kernel changes to substrate-write contract**. The scheduler still records `last_run_at` on dispatch-completion regardless of body success. Flagged as future scope.
- **No re-introduction of ADR-233's lost routing mechanism** (shape-keyed prompt routing through `dispatch_helpers.py`). ADR-233 status banner updated to note the orphan; choice deferred until evidence justifies.
- **No D (specialist posture by recurrence shape)** from the cost-fix audit. Decided structurally wrong — specialists are operator-agnostic capability bundles per ADR-216.

---

## How to resume

1. **Front-load this doc into the next session's context.**
2. **Verify Reviewer caching (5 min)**: Render log grep for `TOKENS.*haiku.*cache_read` on a recent Reviewer wake; expect `cache_read > 0` on round 2+. If working, mark `85035a8` verified.
3. **Run Diagnostic A**: pull the actual `brief` the Reviewer passed to DispatchSpecialist for the falsify-signals invocation. Determine which layer (L1/L2/L3) is the right fix point.
4. **Pause for design call** based on Diagnostic A result before shipping the L1/L2/L3 fix.
5. **Delete this file (`SESSION_CARRY_2026-05-13.md`)** after context is loaded.

---

## What good looks like at session end (next session goal)

- Diagnostic A complete + the brief-composition layer identified
- L1 / L2 / L3 fix shipped (whichever the diagnostic indicates)
- `track-universe` produces `{ticker}.yaml` files end-to-end
- `falsify-signals` produces `/workspace/research/findings/{signal_id}.md` files end-to-end
- Full cold-start cycle on seulkim88 produces ALL FOUR activation-fired substrate outputs (not just two of four)
- Observation doc closing entry that names: today's activation-fire infrastructure work + tomorrow's brief-composition discipline work = complete cold-start resolution

That's the load-bearing final state. Everything else is decoration.

---

> **Delete this file after context load. Canonical sources are CHANGELOG + ADRs + observation doc.**
