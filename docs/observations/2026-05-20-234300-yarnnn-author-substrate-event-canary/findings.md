# yarnnn-author Substrate-Event Canary — Findings

**Hat**: External Developer of the System (Hat B per CLAUDE.md §"The Two Hats"). System-canon edits land in a separate commit; this folder records the observation and recommends.
**Captured**: 2026-05-20T23:54Z (DB clock). Canary fired 23:48:12Z; observation closes at T+6min (6 scheduler ticks).
**Author**: Claude (Opus 4.7) on KVK's session, yarnnn-author canary thread (distinct from the parent session's alpha-trader e2e prep work).

---

## 1. Headline finding

**ADR-296 v2 D2 substrate-event wake source has never fired in production.** The walker raises on every invocation, every user, every scheduler tick. The exception has been live since Checkpoint 2 deploy (`37426c5`, 2026-05-20T07:45Z).

The yarnnn-author canary fired exactly as designed at the substrate layer — frontmatter `status` transition `ready_for_review → draft → ready_for_review` lands in `workspace_file_versions` with the correct revision chain and ADR-294 D2 attribution. But the walker can never read those revisions because it crashes during `read_hooks()` before it ever reaches the matcher.

**This is the load-bearing failure of ADR-296 v2 D2.** The parent pre-e2e audit (`docs/observations/2026-05-20-100309-pre-e2e-readiness-audit-adr296-v2/findings.md`) named two preconditions for the canary: `_hooks.yaml` present in the workspace (Fix 1A landed this), and the walker firing on transitions. The first is satisfied; the second turns out to fail at the runtime layer — a class of failure neither the bundle propagation audit nor the canon-rewrite cascade could have caught.

## 2. The bug

`api/services/wake_sources/substrate_event.py::read_hooks` calls `UserMemory.read()` synchronously:

```python
# substrate_event.py:118-128
def read_hooks(client: Any, user_id: str) -> list[dict]:
    """Read the user's /workspace/_hooks.yaml + parse. Returns [] on absence."""
    try:
        from services.workspace import UserMemory
        memory = UserMemory(client, user_id)
        # UserMemory.read uses workspace-relative paths
        content = memory.read("_hooks.yaml") or ""        # <-- returns a coroutine
    except Exception as exc:
        logger.warning("[WAKE:substrate] _hooks.yaml read failed: %s", exc)
        return []
    return parse_hooks(content)                            # .strip() on coroutine → AttributeError
```

`UserMemory.read` is declared `async def` in `api/services/workspace.py:674`. The synchronous companion `UserMemory.read_sync` exists at `api/services/workspace.py:692` for exactly this thread-pool / non-async-context use case (`working_memory.py` calls it).

`read_hooks` is itself synchronous (`def`, not `async def`), called from the async `walk_hooks`. The async-context-leak isn't picked up because `parse_hooks` doesn't pass the coroutine through any awaiting code — it goes straight to `.strip()` on line 87 (`if not content or not content.strip():`), which produces the user-facing exception:

```
'coroutine' object has no attribute 'strip'
```

`walk_hooks` catches the exception via `try/except` in `unified_scheduler.py:337-341` and logs `WARNING:[SCHED] substrate-event walk failed for {user_id_prefix}: {exc}`. Result: walker degrades silently per user, every tick, since deploy. **No canary, no real operator workflow, no anything has been able to fire a substrate_event wake.**

### Render-log evidence

Sampled across 5 minutes post-canary (2026-05-20T23:48:00Z – 23:53:00Z), the walker fails for every active user on every scheduler tick:

| Tick (UTC) | Failing users |
|---|---|
| 23:48:25Z | 10 (incl. `0b7a852d` = yarnnn-author) |
| 23:49:17Z | 10 |
| 23:50:28Z | 10 |
| 23:51:23Z | 10 |
| 23:52:21Z | 10 |

Sampling backward to 2026-05-20T07:50Z (just after Checkpoint 2 deploy) shows the same exception trail. The failure has been continuous and uniform since the substrate-event wake source code first shipped.

## 3. What the canary did succeed at

Even though the load-bearing test failed at the runtime layer, the canary cleanly validated the layers below the walker:

**ADR-209 Authored Substrate (write side):** both canary writes landed correctly. Revision chain:

```
c57c1eb0  status=ready_for_review  parent=NULL                              operator-proxy:scenario-runner    2026-05-20T03:43:10Z
26c1215d  status=draft             parent=c57c1eb0                          operator-proxy:claude-opus-4-7    2026-05-20T23:48:09Z
43d8f1a3  status=ready_for_review  parent=26c1215d                          operator-proxy:claude-opus-4-7    2026-05-20T23:48:12Z
```

Both new revisions carry `authored_by="operator-proxy:claude-opus-4-7:acting-as-yarnnn-author"` per ADR-294 D2. The parent-pointer chain is correct. Write 2 IS the canonical `draft → ready_for_review` transition that the hook's `_field_change_matches` is supposed to detect.

**Hook substrate (Fix 1A side):** `/workspace/_hooks.yaml` is present and well-formed. 4429 bytes, bundle-fork at 2026-05-20T10:41:40Z carrying the alpha-author bundle's `pre-ship-audit` hook (`path_match: /workspace/context/authored/*/profile.md`, `field_change: {status: ready_for_review}`). `parse_hooks()` against this content (in isolation, outside the walker) returns a well-formed hook list.

**Funnel decision (in theory):** per `services/wake_evaluation.py:165-166`, `substrate_event → ("escalate", "hook_match")`. If `walk_hooks` had reached `submit_wake_proposal(source="substrate_event", ...)`, the funnel would have escalated and the Reviewer would have woken with the hook prompt as envelope. The kernel architecture is sound; only the entry-point walker is broken.

## 4. Hallucinated-audit pattern (parent finding) — non-resolution

The parent pre-e2e audit recorded that yarnnn-author's `standing_intent.md` head (authored 2026-05-20T05:03:28Z by `reviewer:ai:reviewer-sonnet-v8` during an outcome-reconciliation fire) asserts *"First audit baseline confirmed (May 20, governance-as-trust approved): governance-as-trust essay passed all five audit checks: voice clean, continuity explicit, anti-slop floor held, editorial principles advanced, cadence on-track"* — even though `execution_events` shows zero `pre-ship-audit` fires and `judgment_log.md` head carries zero `--- decision ---` blocks for any draft.

Parent operator direction (Fix 2): defer pre-investigation; re-test post-Fix-1A and see if the pattern self-resolves. The hypothesis was: with `_hooks.yaml` in place and the canary fireable, the Reviewer's next outcome-reconciliation reads a real audit decision and the hallucinated assertion gets corrected.

**Status post-canary (T+6min)**: pattern has not been tested. The walker bug prevents the canary from triggering a `pre-ship-audit` fire, so the Reviewer never gets the real audit-decision context that would have corrected its prior fabricated claim. The hallucinated assertion still sits at the head of `standing_intent.md`.

The hallucinated-audit pattern remains an open finding for e2e discovery. It will get tested at next `outcome-reconciliation` (scheduled 2026-05-21T05:00Z), but ONLY IF the walker bug is fixed first and the canary is re-run so a real audit decision actually fires. Without that, outcome-reconciliation will read the same `judgment_log.md` it has been reading — no pre-ship-audit rows, no corrective signal — and the Reviewer will either re-assert the same fabricated audit history or continue the pattern.

## 5. State diff (baseline → T+6min)

| Surface | Baseline (23:40Z) | Post-canary (23:54Z) | Delta |
|---|---|---|---|
| `profile.md` head | `c57c1eb0` (ready_for_review since 2026-05-20T03:43:10Z) | `43d8f1a3` (ready_for_review since 2026-05-20T23:48:12Z) | 2 new revisions establishing the substrate transition |
| `_hooks.yaml` | `c376c800` system:bundle-fork 10:41:40Z | unchanged | — |
| `_recurrences.yaml` | post-Fix-1A re-fork | unchanged | — |
| `standing_intent.md` head | `eaa4224f` reviewer:ai:reviewer-sonnet-v8 05:03:28Z asserting first audit complete | unchanged | Reviewer never woke |
| `judgment_log.md` head | `3a69538e` reviewer:ai:reviewer 2026-05-19T05:04Z material-outcome line | unchanged | Reviewer never woke |
| `execution_events` rows (lifetime total) | 4 (all wake_source=NULL, all pre-Checkpoint-2) | 4 (no new rows) | Canary produced zero events |
| `action_proposals` rows | 0 | 0 | — |
| Scheduler walker errors (Render WARNING logs) | continuous since 07:50Z | continuous; canary write window included | 10+ "substrate-event walk failed for {user}: 'coroutine' object has no attribute 'strip'" entries across the 23:48–23:53Z window |

## 6. Hat-A recommendations (do NOT make in this folder/session)

### Recommendation 1 — Fix `read_hooks` async-context-leak (URGENT)

**One-line fix** at `api/services/wake_sources/substrate_event.py:124`:

```python
# Before
content = memory.read("_hooks.yaml") or ""

# After
content = memory.read_sync("_hooks.yaml") or ""
```

`UserMemory.read_sync` exists for this exact use case (existing precedent: `working_memory.py` calls `read_sync` from synchronous contexts in `format_compact_index`'s thread-pool path). The change is purely behavior-preserving — same query, same Supabase client, just no coroutine wrapping. Singular Implementation discipline: keep `read_hooks` synchronous (matches its `def` not `async def` signature), use the matching sync API.

Alternative: make `read_hooks` itself async and `await memory.read(...)`. Slightly larger refactor (touches `walk_hooks` too — though `walk_hooks` is already async, so the call site change is trivial). Either works.

**Tightness of fit**: this fix is genuinely one line if option-1, or three lines if option-2. The walker's entire other logic (matching, transition guard, submit_wake_proposal) is correct and untested-but-untriggerable. The fix unblocks ADR-296 v2 D2 end-to-end on every workspace simultaneously.

### Recommendation 2 — Add a regression test that catches this class

The bug is a CI-shaped failure: it doesn't show up in any unit test today because the existing `parse_hooks` test (if one exists) takes a string, not the result of `read_hooks`. A test that calls `read_hooks(supabase, user_id)` against a substrate fixture with a known `_hooks.yaml` would have caught this at PR time.

Suggested shape: `api/test_adr296_substrate_event_walker.py` with a fixture that seeds `_hooks.yaml` + a profile.md + a revision chain, then asserts `walk_hooks` returns ≥1 outcome. Mirrors the existing `test_adr296_v2_full_landing.py` 22/22 pattern but exercises the walker end-to-end rather than the gateway primitives in isolation.

### Recommendation 3 — Scheduler-log signal hardening

The walker exception fires once per user per tick (~minute), producing ~50,000+ identical log lines per day across 10 active users. The current "log + degrade" pattern in `unified_scheduler.py:337-341` correctly prevents one user's broken hook config from blocking the others, but the log volume + uniformity means the genuine "first-time broken" signal is buried in repeat noise.

Two clean alternatives:
- **Deduplicate at log layer**: emit the warning once per process-instance per user, with a periodic "still failing" heartbeat (e.g., every 100 ticks). Standard Python `logging` plus a small per-user-id LRU keeps the signal floor high.
- **Surface as `execution_events` with status='walker_error'**: durable record per user per tick is overkill, but a once-per-user-per-day error event would put scheduler-side breakage on the same telemetry rail as the Reviewer's wake events. Operators have one place to look.

This recommendation is independent of Recommendation 1 — even after the walker is fixed, the next class of walker failure (bad `_hooks.yaml` YAML on a single user's workspace, network blip during query, etc.) will surface the same noise floor. Worth tightening before it tries to bury a real signal again.

### Recommendation 4 — Bundle propagation audit, redux

The Hat-A team landed Fix 1A (ADR-292 v3 content-hash drift detection + re-fork) under the assumption that `_hooks.yaml` reaching the workspace was the load-bearing missing piece for ADR-296 v2 D2. The walker bug surfaces an orthogonal failure: bundle content reached the workspace (correctly), but the runtime that READS that content fails before parsing it. This is not a Fix 1A miss — Fix 1A's scope was substrate propagation, not runtime correctness — but it means **the e2e cannot start until both classes of fix are in place**.

Suggested forward step: extend the Fix 1A regression-test pattern (validates bundle substrate reaches workspace under re-fork) with a runtime-side cousin (validates the walker can READ that substrate without raising). The two tests together cover: "did the bytes land?" (Fix 1A) AND "do the bytes get consumed?" (Fix 1A.next). Until both hold, the e2e demo gates ratify too early.

## 7. What this finding does not investigate

Per Hat-B discipline:

- **No code change in this folder.** The one-line fix candidate is named for Hat-A action; this session does not push it.
- **No re-run of the canary after the fix.** That happens in a fresh Hat-B observation folder after Hat-A ships Recommendation 1 and deploys. Repeating the canary in this session would conflate the failure-mode capture (this folder's purpose) with the resolution-validation capture (a future folder's purpose).
- **No investigation of the hallucinated-audit prompt-trace mechanism.** Parent finding deferred this to e2e discovery; deferral holds — the canary has not yet produced the real audit-fire that would exercise the resolution path. Re-test belongs in the follow-up canary observation folder.
- **No alpha-trader workspace touch.** Parent session's scope.
- **No edits to canon docs (FOUNDATIONS, GLOSSARY, primitives-matrix).** ADR-296 v2 D2 status banner in the ADR ledger may need a follow-on amendment from "Implemented 2026-05-20" to "Implemented except for the walker bug fixed in commit X" — that's a Hat-A judgment call.

## 8. Cross-references

- Walker code with the bug: [`api/services/wake_sources/substrate_event.py`](../../../api/services/wake_sources/substrate_event.py) (line 124)
- `UserMemory.read_sync` (the fix target): [`api/services/workspace.py`](../../../api/services/workspace.py) (line 692)
- Scheduler walker invocation: [`api/jobs/unified_scheduler.py`](../../../api/jobs/unified_scheduler.py) (lines 330-348)
- Funnel decision for substrate_event: [`api/services/wake_evaluation.py`](../../../api/services/wake_evaluation.py) (lines 165-166)
- Singular invocation gateway: [`api/services/wake.py`](../../../api/services/wake.py) (`submit_wake_proposal`)
- ADR-296 v2 (the architecture this canary tests): [`ADR-296`](../../adr/ADR-296-continuous-judgment-cycle.md)
- ADR-292 v3 (Fix 1A — bundle propagation): [`ADR-292`](../../adr/ADR-292-continuous-substrate-re-apply.md)
- ADR-294 D2 (operator-proxy caller-identity discipline): [`ADR-294`](../../adr/ADR-294-operator-proxy-substrate-discipline.md)
- Parent pre-e2e audit: [`findings`](../2026-05-20-100309-pre-e2e-readiness-audit-adr296-v2/findings.md)
- yarnnn-author session-start guide: [`alpha-author-autonomy-loop`](../sessions/alpha-author-autonomy-loop.md)
- yarnnn-author T0 baseline: [`T0`](../2026-05-20-034317-yarnnn-author-autonomy-demonstration-T0/)
- This folder's setup: [`PLAYBOOK.md`](PLAYBOOK.md)

## 8b. Resolution (addendum 2026-05-21T00:14Z)

Operator (Hat A) chose to ship the fix in the same session rather than gate it
behind a separate Hat-A pass. Recommendations 1 + 2 landed in commit
`5364ca7` (`fix(adr-296 v2 d2): substrate-event walker — read_sync + workspace_blobs join`).
The fix turned out to be two stacked bugs, not one: Recommendation 1 (sync
API) plus a previously-hidden Bug-2 (schema drift querying
`workspace_file_versions.content` directly, ADR-209-superseded).
Bug-2 only surfaced when the regression test exercised the integration path
end-to-end — the walker's outer `try/except` was catching it as a warning
log identical to the read_hooks failure mode, so neither was distinguishable
from the other in production until the test forced isolation.

Deploy `dep-d874ppu7r5hc73f490ig` went live at 00:09:15Z.

**Resolution confirmed at 00:12-00:13Z:**

| Signal | Pre-fix (23:54Z) | Post-fix (00:13Z) |
|---|---|---|
| `[SCHED] substrate-event walk failed` log lines | continuous (every tick × every user) | zero post-deploy |
| `[SCHED] substrate-event walker fired N hook(s)` log lines | never seen in production lifetime | 2 ticks × "fired 1 hook(s) across 9 user(s)" |
| `execution_events.wake_source='substrate_event'` rows | 0 | 2 (`slug=pre-ship-audit`, `funnel_decision='escalate'`, `mode='judgment'`, `status='success'`) |
| Reviewer wake on yarnnn-author canary | none | 2 wakes (durations: 64.8s, 22.4s) |
| Reviewer-authored revisions post-canary | none | 2 `standing_intent.md` writes |

**ADR-296 v2 D2 is live in production for the first time, end-to-end.**

### What also surfaced — the hallucinated-audit pattern is more nuanced than parent finding framed

With the fix deployed, the Reviewer actually ran the `pre-ship-audit` against
`governance-as-trust`: read the draft, ran the five-check audit, reached an
"approve" verdict, and updated `standing_intent.md` with calibrated forward
posture (*"Piece 1 audit complete (May 21, governance-as-trust approved):
governance-as-trust essay passed all five audit checks: voice clean (zero
anti-patterns), continuity explicit, anti-slop floor held, editorial
principles advanced, repo-grounded"*).

But the Reviewer did NOT write the corresponding `--- decision ---` block to
`/workspace/review/judgment_log.md`. The hook's prompt is explicit:

> Decide and emit one of:
>   - APPROVE — all checks pass; piece may ship. ...
>   - DEFER — ... Write specific defect to /workspace/review/judgment_log.md ...
>   - REJECT — Write structured reasoning to judgment_log.md.

`judgment_log.md` head is still `3a69538e` from 2026-05-19T05:04:02Z. The
parent finding's "hallucinated-audit pattern" is therefore **more nuanced
than originally framed**: the Reviewer is genuinely running the audit and
reaching genuine verdicts — but eliding the `judgment_log.md` write step
on the approve path. The artifact gap survives the architecture fix.

This is a downstream finding worth a separate Hat-A pass — likely persona-
frame tightening on the hook prompt (the "write to judgment_log.md" clause
should be load-bearing on the approve path, not only on defer/reject) or
prompt-following discipline at the agent layer. Out of scope for this fix;
documented here as the next surface to attack once the operator gates it.

### Recommendation status

| Original recommendation | Status |
|---|---|
| R1 — Fix `read_hooks` async-context-leak | **Done** in commit `5364ca7` (plus discovered + fixed stacked Bug-2 in same commit) |
| R2 — Add regression test | **Done** in same commit — `api/test_adr296_substrate_event_walker.py` (13 assertions, integration test exercises live DB) |
| R3 — Scheduler log dedup | Still open. Reduced urgency post-fix (the noise floor is currently zero for `substrate-event walk failed` lines), but the underlying design point — per-user per-tick repeat-warnings buried real signals — survives any class of future walker failure. Separate Hat-A commit when prioritized. |
| R4 — Bundle-propagation runtime audit | Still open. Less urgent post-fix (the runtime side of D2 now runs), but the discipline principle — "bytes landed" + "bytes consumed" both belong in the bundle-propagation test surface — is the durable take. Worth folding into the next ADR-292 v3 iteration when there's appetite. |

---

## 9. Capture method (reproducibility)

All findings derived from:

- Live psql against Supabase prod (connection string in `docs/database/ACCESS.md`) — `workspace_files`, `workspace_file_versions`, `execution_events`, `action_proposals`, `tasks`.
- Render API logs via MCP (`mcp__render__list_logs` against `crn-d604uqili9vc73ankvag`).
- Render service config via MCP (`mcp__render__get_service`).
- Render deploy history (`mcp__render__list_deploys`) to confirm the scheduler is on the post-Checkpoint-2 commit (`a0d592b`, live 2026-05-20T11:15Z).
- Substrate-write via canonical `services.operator_proxy.OperatorProxy.write_substrate()` → `services.authored_substrate.write_revision()` (ADR-209 single write path).
- Code reads against `api/services/wake_sources/substrate_event.py`, `api/services/workspace.py`, `api/jobs/unified_scheduler.py`, `api/services/wake_evaluation.py`, `api/services/wake.py`.
- Git history on `api/services/wake_sources/substrate_event.py` to confirm the bug shipped with Checkpoint 2 (`37426c5`).

Two operator-proxy substrate writes were issued (the canary itself); no chat messages, no scenario runs, no recurrence-manual-fires.
