# ADR-270: Fire-on-Activation Recurrences — Closing the Cold-Start Activation Gap

**Status**: Proposed 2026-05-13. Implementation in same commit as the ADR (atomic).

**Companion**: this ADR ships alongside the alpha-trader bundle's first cold-start research recurrence (`falsify-signals`) and `fire_on_activation` markers on `track-account` / `track-regime` / `track-universe`. The kernel change is the scheduler conditional; the bundle change is operator-facing.

**Supersedes**: none directly. Fills a gap in the existing activation sequence (ADR-226 reference-workspace fork → ADR-231 scheduling-index materialization → first scheduler tick) where the operator-facing reality during the gap between fork and the first periodic fire is *dead-quiet substrate*.

**Amends**:
- FOUNDATIONS Axiom 4 (Trigger). Activation is named as a deterministic fire shape under the periodic sub-shape's umbrella — it does not introduce a new trigger taxonomy entry; it leverages the existing periodic-trigger path via the scheduler's normal cron tick.
- ADR-261 D1 (recurrence schema `{slug, schedule, mode, prompt}`) — preserved. `fire_on_activation: true` is operator-authored as a sibling key, parsed into `rec.options` (the dataclass's existing extensibility surface), no new dataclass field.

**Preserves**:
- Axioms 1 (Substrate), 2 (Identity), 7 (Recursion), 9 (Invocation and Narrative). Activation fires accumulate substrate via existing recurrence machinery; no new substrate convention beyond what bundles declare.
- ADR-209 Authored Substrate. Activation-fired recurrences write via `write_revision()` with the same attribution discipline as periodic fires.
- ADR-226 fork sequence. The fork-then-materialize order is unchanged; this ADR only changes what `compute_next_run_at` returns for recurrences with the flag set when `last_run_at is None`.
- ADR-231 single dispatch path. The scheduler is the only invoker — activation fires are not a side-channel.
- ADR-260 real-time Reviewer loop. Wake mechanism unchanged. Reviewer wakes when the scheduler dispatches the row, same as any other cron tick.

---

## 1. Why this ADR

### The observation

Activation produces a workspace whose substrate is the bundle's reference content — operator-facing files, recurrence declarations, a materialized scheduling index. **No work has executed.** The first periodic fire of any recurrence happens whenever the cron-resolved `next_run_at` arrives. For US-market-bound recurrences activated outside RTH, that gap can be many hours — `track-universe` at `@market_open + 15min` activated at 22:00 KST on a weekday waits 11.5 hours before fetching its first ticker snapshot.

During that gap:
- The operator's cockpit faces are empty (no positions, no account snapshot, no regime substrate, no per-ticker bars).
- The Reviewer cannot reason about EV — `_money_truth.md` is empty *and* there's no historical context to fall back on.
- The feed surface (ADR-259) shows the fork attribution then silence.
- The operator's first lived experience of YARNNN is "I activated and nothing visibly happened."

### Why this is structurally wrong, not just cosmetic

Axiom 7's recursion claim is *substrate accumulates and compounds*. Compounding requires there to be substrate to compound from. Axiom 1's substrate-canonical-world claim implies the workspace's filesystem should reflect operationally-relevant state. At T+0 of activation, the workspace is in a degenerate state where:

- The Reviewer has reasoning machinery but no inputs (`_money_truth.md` empty, regime substrate empty, ticker substrate empty).
- The substrate-canonical-world axiom is technically honored (nothing in substrate is wrong; it's just empty), but the operator-experienced reality is that activation is decorative until the first scheduled fire lands.
- The autonomy story (Phase 0 onward in AUTONOMY.md) describes a system that judges and proposes capital actions — none of which can happen against empty substrate.

The architecture has been describing itself as "agent-OS" but the experienced reality of activation is closer to "scaffolded inbox waiting for a cron." This ADR closes the gap.

### What it doesn't do

This ADR does not introduce a new trigger taxonomy, a new agent class, or a new substrate file convention. It is the smallest possible change that makes activation an active moment instead of a passive one. Three things the operator might expect that this ADR explicitly does NOT do:

1. **Does not add chat-callable invocation verbs.** Reactive recurrences (`schedule: null`) are still operator-driven via `FireInvocation` from the cockpit's `/work` surface or via Reviewer judgment; this ADR does not add chat-surface idioms for "fire this recurrence right now."
2. **Does not write substrate from chat exploration.** When the operator asks YARNNN exploratory questions in chat, the answers remain ephemeral narrative entries (per ADR-259); they do not auto-write to `/workspace/research/exploration/` or similar.
3. **Does not introduce a Researcher Agent class.** The bundle's `falsify-signals` is a recurrence (per ADR-261), not a new persona-bearing seat. Whether to elevate falsification work to an ongoing fiduciary role is deferred per ADR-270 §"Earned escalation" below.

These three deferrals are deliberate. The discussion that produced this ADR considered all three; each was rejected on the grounds that activation-time fires alone close the load-bearing gap, and the other three patterns can be earned by observation post-shipping.

---

## 2. The decision

### D1 — Recurrence YAML accepts `fire_on_activation: true`

Operator authors `fire_on_activation: true` as a sibling key to `schedule:` and `mode:` in the recurrence's body. The parser (`api/services/recurrence.py::parse_recurrences_yaml`) does not need to know about this key — `rec.options` (the dataclass's existing absorption surface for unrecognized keys) carries it through transparently.

Example bundle YAML:

```yaml
- slug: track-regime
  schedule: "@market_close + 30min"
  mode: judgment
  fire_on_activation: true   # ← this ADR
  required_capabilities: [read_trading]
  prompt: |
    ...
```

### D2 — Scheduler returns `now` when `fire_on_activation` is set AND `last_run_at is None`

The single mechanical change. In `compute_next_run_at`:

```python
if rec.options.get("fire_on_activation") and last_run_at is None:
    return now_utc
```

Placed above the schedule-resolution path. Honors pause state (paused-recurrences-with-activation-flag stay paused — pause beats activation, intentional).

The semantic: activation-fired recurrences fire on the next scheduler tick after `materialize_scheduling_index` runs (which happens immediately after fork per ADR-226). After the first fire records `last_run_at`, the recurrence falls back to its normal schedule (or `None` for reactive recurrences with `schedule: null` + `fire_on_activation: true` — they fire once and stay reactive thereafter).

### D3 — One fire, exactly, per activation

The semantic is **fire once when the workspace is freshly activated, then resume normal cadence**. Subsequent calls to `compute_next_run_at` see `last_run_at` populated and fall through.

The activation event is *workspace reset* (ADR-226 fork). A workspace L4-reset purges `tasks` rows, the next fork re-materializes the index with `last_run_at = None` for the activation-fired recurrences, and they fire again. This matches the desired semantic: every activation event re-bootstraps substrate.

### D4 — Pause beats activation

If `paused: true` is set on a recurrence with `fire_on_activation: true`, the pause check (which runs first in `compute_next_run_at`) returns None. Activation does not fire paused recurrences. Intentional: the operator can ship a paused activation-fired recurrence in the bundle for "available but not yet engaged" patterns (e.g., a heavy-cost falsification cycle that the operator opts in to by resuming).

### D5 — Reactive recurrences (`schedule: null`) with `fire_on_activation: true` fire exactly once

This is the canonical shape for *one-shot bootstrap recurrences*. The alpha-trader bundle's `falsify-signals` uses it: walks operator-declared signals against historical bars at activation, writes findings, then never auto-fires again. Subsequent invocations are operator-driven via `FireInvocation`.

This is distinct from periodic recurrences with `fire_on_activation: true` (which fire at activation then continue on cadence). The flag's semantic is consistent: "fire on next scheduler tick after activation"; the *subsequent* behavior is determined by `schedule`.

### D6 — Recurrence selection for activation firing is operator-authored at bundle layer

The kernel does not opine on which recurrences should be activation-fired. That's a bundle-authoring decision. The alpha-trader bundle marks four recurrences:

- `track-account` (substrate snapshot of broker account state — visible cockpit content immediately)
- `track-regime` (VIXY + SPY regime, needed before signal-evaluation can size correctly)
- `track-universe` (per-ticker bar snapshots, needed before signal-evaluation can evaluate)
- `falsify-signals` (90-day historical falsification, bootstrap research substrate)

The other bundle recurrences (signal-evaluation, trade-proposal, periodic deliverables, back-office maintenance) explicitly do NOT carry the flag — they need the activation-fired recurrences' substrate to exist first.

Future bundles (alpha-commerce, alpha-prediction, hypothetical alpha-content) author their own activation-fired set per domain.

### D7 — Activation is a deterministic environment fire under Axiom 4's periodic umbrella

Axiom 4 names three Trigger sub-shapes: periodic, reactive, addressed. Activation is *not* a fourth — it's a deterministic environment event that fires recurrences eligible to fire at it. Mechanically, the scheduler dispatches the row when `next_run_at <= now`; activation-fired recurrences have `next_run_at = now` immediately after materialization. The trigger taxonomy is preserved.

The conceptual framing: activation is an *event the kernel knows about* (the moment of bundle fork), and the recurrence machinery has long supported "fire when due." This ADR makes "due at activation" expressible. No new dispatch path; no new primitive; no new sub-shape.

---

## 3. Earned escalation

This ADR ships the smallest possible change. Three deliberate non-actions are deferred to future ADRs *if observation warrants*:

### 3a — Chat-callable reactive recurrence invocation as first-class operator gesture

Today `FireInvocation` is available from `/work` UI and as a Reviewer-side primitive. There is no chat-surface idiom for "operator says 'run X now' → YARNNN translates to FireInvocation". Adding it is a chat-prompt convention + maybe a thin alias verb in the chat tool surface. **Deferred until observation shows operators want this often.**

### 3b — Ad-hoc chat exploration writes substrate by default

Today YARNNN's chat replies are narrative entries (per ADR-259). The proposal that "substantively-shaped exploration should write to `/workspace/research/exploration/`" was raised and explicitly deferred — the convention for "what counts as substantive enough to retain" wants operator input before shipping. **Deferred until convention is operator-authored.**

### 3c — Periodic `falsify-signals` schedule

The bundle ships `falsify-signals` as `schedule: null + fire_on_activation: true` — one-shot bootstrap. If observation shows ongoing falsification is load-bearing (signals drift faster than the quarterly audit catches), a future bundle revision adds a periodic schedule. **Deferred until evidence justifies it; explicit per `research/mandate.md` §"Earned escalation".**

The escalation pattern: ship the smallest version, observe lived experience, promote a deferred piece into shipped substrate when evidence justifies. Same discipline as AUTONOMY.md's Phase 0 → Phase 1 graduation.

---

## 4. Implementation surface

### Modified files

| File | Change |
|---|---|
| `api/services/scheduling.py` | One conditional at top of `compute_next_run_at`: returns `now_utc` when `rec.options.get("fire_on_activation")` is true AND `last_run_at is None` |
| `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml` | `fire_on_activation: true` added to `track-account`, `track-regime`, `track-universe`; new `falsify-signals` reactive recurrence with the flag |
| `docs/programs/alpha-trader/reference-workspace/review/principles.md` | New bullet in Capital-EV section: Reviewer reads `/workspace/research/findings/{signal_id}.md` alongside `_money_truth.md`; live data weighs more than replay |

### New files

| File | Purpose |
|---|---|
| `docs/programs/alpha-trader/reference-workspace/research/mandate.md` | Operator-facing mandate for the `/workspace/research/` substrate (analog of `/workspace/review/IDENTITY.md`) |
| `docs/programs/alpha-trader/reference-workspace/specs/falsify-signals.md` | Schema for per-signal findings written by `falsify-signals` to `/workspace/research/findings/{signal_id}.md` |

### Not changed

- **No new primitive.** `falsify-signals` runs as a regular judgment-mode recurrence with `required_capabilities: [read_trading]`; the Reviewer dispatches a specialist for the historical-bar work via existing `DispatchSpecialist` path.
- **No new agent.** No Researcher class. The recurrence is the work; no persistent persona-bearing seat.
- **No FOUNDATIONS amendment.** Axiom 4's trigger taxonomy is preserved; activation is the existing periodic path with `next_run_at = now`.
- **No primitive matrix change.** No new tools.
- **No CHANGELOG-required prompt change beyond the principles.md edit** (Reviewer's prompt itself is unchanged — `principles.md` is a substrate file the Reviewer reads, not a system prompt).

---

## 5. Validation

### Operator-experience test (manual, post-deploy)

Reset a persona's workspace (e.g., `reset.py --persona alpha-trader --confirm`), activate (`activate_persona.py --persona alpha-trader`), connect platform (`connect.py alpha-trader`). Within the next scheduler tick (≤60 seconds):

1. `_account.yaml` should exist at `/workspace/context/portfolio/_account.yaml` with current broker account snapshot.
2. `_regime.yaml` should exist at `/workspace/context/trading/_regime.yaml` with current VIXY + SPY regime.
3. Per-ticker snapshots should exist at `/workspace/context/trading/{ticker}.yaml` for each universe member.
4. Per-signal findings should exist at `/workspace/research/findings/{signal_id}.md` with `source: replay` frontmatter.

Feed surface should show the activation burst: 4-7 system-attributed entries within the first minute.

### Failure-mode walkthrough

Three failure modes considered and resolved:

1. **Activation outside RTH for an RTH-only recurrence.** `track-universe` is RTH-only via its semantic schedule. With `fire_on_activation: true`, the scheduler returns `now` regardless of RTH state — the recurrence fires immediately on activation even on weekends. The Alpaca platform tool will return whatever stale-but-most-recent bars are available; the recurrence prompt's stale-data handling stands.

2. **Repeated activation in close succession.** Each activation L4-resets the workspace, purging `tasks` rows. Re-fork re-materializes with `last_run_at = None`, activation-fired recurrences fire again. Intentional.

3. **Paused activation-fired recurrence.** Pause check runs first in `compute_next_run_at`; returns None or `paused_until`. Activation does not fire paused recurrences. Operator can ship a paused activation-fired recurrence as "available but not engaged" pattern.

---

## 6. What this means for the agent-OS thesis

THESIS Commitment 4 (Authored Accumulation) claims context "accumulates and compounds under use." That claim's hidden precondition is that the first cycle has substrate to read. ADR-270 makes activation an active accumulation moment instead of a passive one. The operator's first 60 seconds of activation now produce a workspace with live broker state, regime substrate, ticker substrate, and historical research findings. The Reviewer's first proposal can reason against real context.

This does not promote any axiom or thesis commitment. It closes a gap between what canon claims about the architecture (accumulating, compounding) and what the operator's lived activation experience demonstrates (dead-quiet substrate until first cron). The two are now aligned.

---

## 7. Discourse context (for trace)

This ADR's framing emerged from a multi-turn architectural discourse on 2026-05-13 (alongside the ADR-269 regime wiring discussion). The discourse considered three richer shapes:

- A dedicated learning-playbook userspace (rejected — doesn't serve money-truth strongly enough)
- An extended workspace with replay-as-platform-connection (rejected — over-architected for the actual gap)
- A new Researcher Agent class (rejected — no judgment capability structurally absent from existing framework)

The first-principled rest after stress-testing was: **the framework already supports cold-start substrate population via the existing recurrence machinery; what's missing is a way for bundles to mark recurrences for activation-fire.** That is this ADR.

Trace lives in `docs/alpha/observations/2026-05-13-activation-fire-wiring.md` (companion observation doc).
