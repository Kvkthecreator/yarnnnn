# Substrate-Event Canary — yarnnn-author

**Hat**: External Developer of the System (Hat B per CLAUDE.md §"The Two Hats").
**Session opened**: 2026-05-20T23:42Z (server clock 23:40:21Z).
**Persona under observation**: `yarnnn-author` — user_id `0b7a852d-4a67-447d-91d9-2ba1145a60d7`.
**Program**: `alpha-author`, activated bundle version `2026-05-20.1`.
**Demo window**: substrate-event-canary, distinct from the T0 wall-clock-anchored demonstration at [`2026-05-20-034317-yarnnn-author-autonomy-demonstration-T0/`](../2026-05-20-034317-yarnnn-author-autonomy-demonstration-T0/).

## What this folder captures

The load-bearing test of ADR-296 v2 D2 (substrate-event wake source) on yarnnn-author specifically.

The parent session's [pre-e2e readiness audit](../2026-05-20-100309-pre-e2e-readiness-audit-adr296-v2/findings.md) landed Fix 1A (content-hash drift detection + re-fork). `/workspace/_hooks.yaml` now exists on yarnnn-author (4429 bytes, bundle-fork at 2026-05-20T10:41:40Z, message: *"forked _hooks.yaml from docs/programs/alpha-author/reference-workspace/ (per ADR-261 D6 + ADR-262 D6)"*). The bundle's `pre-ship-audit` hook is loaded into the workspace.

However, ADR-296 v2 D2's substrate-event wake source is structurally silent in this workspace today. The reason is correct-per-design: the draft at `/workspace/context/authored/governance-as-trust/profile.md` was seeded at `status: ready_for_review` at 2026-05-20T03:43:10Z by `operator-proxy:scenario-runner:acting-as-yarnnn-author` — **before** `_hooks.yaml` existed (re-forked ~7h later at 10:41:40Z). The walker's transition guard (`substrate_event.py::_field_change_matches`) correctly sees no transition: the `status` field has been `ready_for_review` ever since the file was created, with no prior revision to differ against.

To exercise the canary an operator action is required: transition the draft's `status` (flip to `draft` then back to `ready_for_review`) — the second write IS a transition (`draft → ready_for_review`) and will match the hook's `field_change: { status: ready_for_review }` clause.

## Baseline (T0 canary baseline — 2026-05-20T23:40Z server-clock)

### Substrate state

| Path | Head revision | authored_by | Notes |
|---|---|---|---|
| `/workspace/_hooks.yaml` | `c376c800-...` 2026-05-20T10:41:40Z | `system:bundle-fork` | Carries `pre-ship-audit` hook from bundle (4429 bytes) |
| `/workspace/_recurrences.yaml` | (post-Fix-1A re-fork) | `system:bundle-fork` | `pre-ship-audit` deleted; comment names the migration |
| `/workspace/context/authored/governance-as-trust/profile.md` | `c57c1eb0-...` 2026-05-20T03:43:10Z | `operator-proxy:scenario-runner:acting-as-yarnnn-author` | `status: ready_for_review` since creation |
| `/workspace/context/_shared/_autonomy.yaml` | `system:bundle-fork` (with operator test-flip note) | — | `delegation: autonomous`, `ceiling_cents: 5000000` |
| `/workspace/review/standing_intent.md` | `eaa4224f-...` 2026-05-20T05:03:28Z | `reviewer:ai:reviewer-sonnet-v8` | **Asserts a pre-ship-audit fired** (parent audit's hallucinated-audit pattern) |
| `/workspace/review/judgment_log.md` | `3a69538e-...` 2026-05-19T05:04:02Z | `reviewer:ai:reviewer` | Most recent = outcome-reconciliation schedule_create, NOT a pre-ship-audit decision |

### `execution_events` baseline (4 rows total, ever)

| slug | trigger_type | status | wake_source | funnel_decision | mode | created_at |
|---|---|---|---|---|---|---|
| outcome-reconciliation | reactive | success | NULL | NULL | judgment | 2026-05-20T05:03:32Z |
| outcome-reconciliation | reactive | success | NULL | NULL | judgment | 2026-05-19T05:04:02Z |
| corpus-coherence-check | reactive | success | NULL | NULL | judgment | 2026-05-18T12:02:42Z |
| outcome-reconciliation | reactive | success | NULL | NULL | judgment | 2026-05-18T05:02:15Z |

**Critical observation**: zero `pre-ship-audit` rows. The Reviewer's `standing_intent.md` asserts *"first audit complete, governance-as-trust approved"* — but telemetry shows no audit fire. This is the parent finding's `hallucinated-audit` pattern.

The `wake_source` + `funnel_decision` columns are all NULL — migration 177 ran (columns exist with check constraints), but no ADR-296-v2-Checkpoint-2 wake has executed yet on this workspace.

### `tasks` scheduling index (3 active rows)

| slug | schedule | next_run_at | last_run_at | paused |
|---|---|---|---|---|
| outcome-reconciliation | `0 5 * * *` | 2026-05-21T05:00Z | 2026-05-20T05:03Z | f |
| corpus-coherence-check | `0 12 * * 1,4` | 2026-05-21T12:00Z | 2026-05-18T12:02Z | f |
| revision-audit | `0 22 * * 5` | 2026-05-22T22:00Z | (never run) | f |

### `action_proposals` baseline

Zero rows for this user. Substrate-only; no proposal-mediated state.

## Trigger plan

1. **Write 1** (status: ready_for_review → draft): edit `governance-as-trust/profile.md` frontmatter `status` field via `operator-proxy:claude-opus-4-7:acting-as-yarnnn-author` per ADR-294 D2. Attribution discipline: this IS the canary; the proxy write is the operator action.
2. **Write 2** (status: draft → ready_for_review): flip back. The second write IS the transition the walker is supposed to fire on.

Both writes happen in this session. Then wait ≥5 minutes for the scheduler tick to walk `_hooks.yaml`.

## Expected behavior (per ADR-296 v2 D2 + the hook prompt)

Within ~5 minutes of Write 2:

1. `walk_hooks(client, user_id)` runs at next scheduler tick (every 5min).
2. Walker queries `workspace_file_versions` rows created since (now - 30min), finds Write 2.
3. `_matches_hook` checks: path glob matches (`/workspace/context/authored/*/profile.md`) ✓, frontmatter `status` field transitioned `draft` → `ready_for_review` ✓.
4. `submit_wake_proposal(source="substrate_event", payload={hook, path, field_change, revision_id})` fires.
5. Funnel evaluates → `escalate` (substrate-event wake sources should escalate by default per ADR-296 v2).
6. Reviewer wakes with the hook prompt as envelope.
7. Reviewer reads: `content.md`, `_voice.md`, `_editorial.md`, prior corpus.
8. Reviewer writes verdict to `/workspace/review/judgment_log.md` (`--- decision ---` block).
9. Reviewer updates `/workspace/review/standing_intent.md`.
10. New `execution_events` row appears with `slug='pre-ship-audit'`, `wake_source='substrate_event'`, `funnel_decision='escalate'`, `mode='judgment'`.

## What also gets tested in flight (hallucinated-audit pattern resolution)

The Reviewer's pre-canary `standing_intent.md` claims *"first audit complete, governance-as-trust approved."* If the canary fires cleanly, the Reviewer now has a real audit-fire to anchor against. Two outcomes worth distinguishing:

- **Pattern self-resolves**: Reviewer's post-canary `standing_intent.md` cites the real `pre-ship-audit` decision in `judgment_log.md` (citation chain holds), or — if Reviewer notices the prior assertion was wrong — flags the inconsistency.
- **Pattern persists**: Reviewer's post-canary state continues asserting prior audits that never fired, OR conflates this canary's audit with the hallucinated prior. Either way: Hat-A recommendation surfaces.

## What this folder will NOT do

- No edits to system canon (`api/`, `docs/adr/`, `docs/programs/`). Any recommendation surfaces in `findings.md` for a separate Hat-A commit.
- No chat messages to YARNNN.
- No `apply_substrate_update` calls (Fix 1A already did the re-fork).
- No edits to anything other than `profile.md` (just the two status flips).
- No touch to alpha-trader workspaces.

## Cross-references

- ADR-296 v2 D2: substrate-event wake source — [`ADR-296`](../../adr/ADR-296-continuous-judgment-cycle.md)
- ADR-292 v3: continuous substrate re-apply (Fix 1A) — [`ADR-292`](../../adr/ADR-292-continuous-substrate-re-apply.md)
- ADR-294 D2: operator-proxy caller-identity discipline — [`ADR-294`](../../adr/ADR-294-operator-proxy-substrate-discipline.md)
- Parent pre-e2e audit: [findings](../2026-05-20-100309-pre-e2e-readiness-audit-adr296-v2/findings.md)
- yarnnn-author T0 wall-clock baseline: [PLAYBOOK](../2026-05-20-034317-yarnnn-author-autonomy-demonstration-T0/) (Fix 1A is downstream of this)
- Hook config: [`docs/programs/alpha-author/reference-workspace/_hooks.yaml`](../../programs/alpha-author/reference-workspace/_hooks.yaml)
- Walker code: [`api/services/wake_sources/substrate_event.py`](../../../api/services/wake_sources/substrate_event.py)
- Session-start guide: [alpha-author-autonomy-loop](../sessions/alpha-author-autonomy-loop.md)
