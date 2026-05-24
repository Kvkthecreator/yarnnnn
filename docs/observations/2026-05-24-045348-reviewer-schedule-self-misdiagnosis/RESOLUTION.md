# RESOLUTION — Reviewer schedule self-misdiagnosis closed via ADR-301

**Captured**: 2026-05-24T05:35Z (Hat-B closure, ~40 min after the finding was first captured at 04:53Z).

**Sibling**: [`findings.md`](./findings.md) (Hat-B finding) · [`PLAYBOOK.md`](./PLAYBOOK.md) (audit method).

**Hat-A fix commit**: `fa733f8` (`feat(adr-301): reviewer pulse envelope — schedule_index + recent_execution`).

## Three-commit shape — completed in-session

The cross-hat work followed the discipline rule from `CLAUDE.md §"The Two Hats"`:

| # | Hat | Commit | Scope |
|---|---|---|---|
| 1 | Hat-B | `772a569` | `findings.md` + `PLAYBOOK.md` capturing the schedule-hallucination class + `CORRECTION.md` on the sibling L6 ADDENDUM clause-5 misclaim. No code changes. |
| 2 | Hat-A | `fa733f8` | ADR-301 ratification + MirrorScheduleIndex + MirrorRecentExecution mechanical primitives + envelope wire + persona-frame Pulse Discipline section + scheduler integration + Cleanup 1+2 + cadence-and-wakes.md §8 extension + regression gate (32/32 PASS). |
| 3 | Hat-B | this | Resolution addendum confirming the post-deploy substrate matches the spec. |

In-session crossing was warranted per the discipline rule: the fix had named in-canon precedent (`MirrorSignalState` is the exact pattern; ADR-285 D3 already specified the design taxonomy; ADR-209 already specified the attribution shape; ADR-298 already specified the scheduler-tick maintenance phase). Total Hat-A change: ~1800 LOC added, ~130 deleted, 17 files, zero new abstractions.

## What was shipped

ADR-301 ratifies the Reviewer Pulse Envelope:

- Two new kernel-universal envelope entries under `/workspace/memory/`:
  - `_schedule_index.md` — literal `schedule:` + `mode` + `last_run_at` + `next_run_at` + `paused` for every recurrence in the workspace
  - `_recent_execution.md` — last-24h `execution_events` rollup with outcomes, costs, durations, per-mode + per-wake-source counts
- Both files mirrored per scheduler tick by `services.kernel_mirrors` (piggybacks on the existing `reclaim_stale_locks` + `drain_all_users_with_pending` maintenance phase). Same precedent: kernel maintenance is scheduler-side, not workspace-side recurrences.
- Diff-aware writes — most ticks produce zero substrate revisions. ADR-209 attribution `system:mirror-schedule-index` and `system:mirror-recent-execution`.
- Reviewer perception: `_PERSONA_FRAME` gains "Pulse Discipline (ADR-301)" section instructing the Reviewer to read both files **before** reasoning about cadence or recent activity, with explicit reference to the hallucination case the discipline closes.

Bundled cleanups (Singular Implementation):

- **Cleanup 1**: `build_operating_context_block` consolidated into `services/reviewer_envelope.py`. Pre-cleanup composed at three `wake.py` call sites + defined in `reviewer_agent.py`; post-cleanup composed once in the envelope helper, flows through the `**governance_envelope` spread. `agents.reviewer_agent` re-export shim preserves the ADR-274 import contract; test gate continues to pass.
- **Cleanup 2**: `Pace.min_interval_seconds` property extracted; `wake_drainer.py` inline `86400 / fires_per_day` arithmetic removed. Singular pace-budget arithmetic site.
- **Cleanup 3** (originally proposed): DEFERRED with rationale — pre-lock balance gate would force two balance checks (pre-lock for efficiency, post-lock for forensic `execution_events` ledger + ADR-291 repeat-suppression discipline) violating Singular Implementation; no observed lock-starvation symptom in the 2026-05-24 audit.

## Post-deploy validation

Deploy went live at **2026-05-24T05:31:56Z** (yarnnn-unified-scheduler `dep-d898pup9rddc73ai81vg`). API + Scheduler both on `fa733f8`.

**First post-deploy scheduler tick (2026-05-24T05:32:30Z)** produced this log line:

```
[SCHED] kernel mirrors: schedule_index wrote 6/6 (skip=0, fail=0), recent_execution wrote 6/6 (skip=0, fail=0)
```

DB verification — 12 file rows materialized within 3 seconds (05:32:27Z → 05:32:30Z) across all 6 active workspaces:

| workspace | schedule_index bytes | recent_execution bytes |
|---|---:|---:|
| yarnnn-author@yarnnn.com | 847 | 372 |
| netflix-script-author@yarnnn.com | 711 | 372 |
| korea-thriller-shorts@yarnnn.com | 711 | 372 |
| kvkthecreator@gmail.com (alpha-trader main) | 1694 | 131 |
| alpha-trader-2@yarnnn.com | 1694 | 131 |
| seulkim88@gmail.com | 1503 | 131 |

ADR-209 attribution clean:

```
        authored_by           | revisions
--------------------------------+-----------
 system:mirror-recent-execution |    6
 system:mirror-schedule-index   |    6
```

## The closure of the hallucination class — substrate-side proof

The Reviewer-on-alpha-trader-main hallucination on 2026-05-22T21:01Z asserted: *"signal-evaluation judgment recurrence failed to fire today during all scheduled RTH windows."* It conflated `signal-evaluation` (1× per RTH per `@market_open + 15min`) with `track-universe` (3× per RTH).

Post-ADR-301, kvk's `_schedule_index.md` (workspace where hallucination happened) contains the literals **in the envelope the Reviewer reads at every wake**:

```markdown
| signal-evaluation | `"@market_open + 15min"   # 09:45 ET` | judgment | 2026-05-22T13:45:20Z | 2026-05-26T13:45:00Z | false |
| track-universe | `- "@market_open + 15min"     # 09:45 ET — 15 min after open, price discovery settled` | mechanical | 2026-05-22T19:00:19Z | 2026-05-26T13:45:00Z | false |
```

- `signal-evaluation`: literal schedule `"@market_open + 15min"` (single string, one fire). Last fired 2026-05-22T13:45:20Z (correctly, on Friday). Next fires 2026-05-26T13:45:00Z (Tuesday — Memorial Day Monday correctly skipped). **No basis for "should fire 3× RTH" — the literal is unambiguous.**
- `track-universe`: literal schedule starts with `-` (list-style YAML), which is the multi-fire shape the Reviewer hallucinated. **This is the recurrence with 3× RTH fires.** The Reviewer can now see the distinction directly in the envelope.

The Reviewer reading the envelope substrate can no longer plausibly fabricate "signal-evaluation should have fired 3× today" — the literal `@market_open + 15min` (single string) is structurally present. The hallucination class is closed by substrate, not by prompt-hope.

## What this validates beyond the singular hallucination

1. **FOUNDATIONS Derived Principle 19 honored end-to-end** — kernel maintenance computes substrate at known cadence; the prompt reads substrate; no LLM-time derivation. The mirror pattern (ADR-281 → ADR-301) is the canonical shape for substrate-derivative envelope content.
2. **Singular Implementation discipline preserved across three concurrent changes** — the envelope helper is the singular envelope assembly point (Cleanup 1); pace-budget arithmetic lives at one site (Cleanup 2); the persona-frame addition lives in one file with prompt CHANGELOG entry.
3. **The Reviewer's self-diagnostic reliability is now substrate-backed.** Future standing_intent.md claims about "missed fires" / "system silent" / "cadence broken" will (post-this-deploy) be grounded in the schedule_index + recent_execution substrate or visibly off-script from it. The next time the operator reads a Reviewer's "scheduler appears broken" claim, they can cross-reference the same `_schedule_index.md` + `_recent_execution.md` files to confirm or refute. **The substrate trail becomes the discipline rule's enforcement mechanism, not just narrative scaffolding.**

## What remains follow-on

- **Next-natural-wake validation of the persona-frame Pulse Discipline section** — confirming the Reviewer actually consults `_schedule_index.md` before claiming missed fires. The first natural opportunity is the next `cron_tick` wake or operator-addressed turn that surfaces cadence reasoning. If a future standing_intent.md write quotes `_schedule_index.md` directly (or its literal contents), the behavioral closure is empirically confirmed. The structural closure (envelope substrate present + persona frame instruction present) is already proven.
- **ADR-285 D5+ alpha-trader world-mirror entries** (`MirrorTickerSnapshot` + `MirrorPositionState`) remain Proposed for separate bundle work.
- **Hat-B observation cadence**: the next time a Reviewer narrative claim about "cadence broken" or "missed fires" lands, capture the standing_intent.md write + the corresponding `_schedule_index.md` / `_recent_execution.md` content as paired evidence. If they agree, the Reviewer's claim is substrate-backed. If they diverge, that's the next Hat-B finding.

## Status

**Schedule-hallucination class STRUCTURALLY CLOSED via ADR-301 (commit `fa733f8`, deployed 2026-05-24T05:31:56Z).** First post-deploy scheduler tick (2026-05-24T05:32:30Z) wrote the pulse envelope substrate to all 6 active workspaces with correct content, correct attribution, correct diff-aware behavior.

**Three-commit cross-hat shape completed in-session**: Hat-B finding (`772a569`) → Hat-A fix + ADR + cleanups + docs + tests (`fa733f8`) → Hat-B resolution (this commit). Cleanup 3 deferred with documented rationale; remaining follow-on is behavioral validation of the persona-frame instruction in a future natural wake.
