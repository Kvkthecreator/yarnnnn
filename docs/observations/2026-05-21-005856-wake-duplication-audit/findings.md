# Wake-Duplication Audit — Three Patterns Surfaced From Feed Inspection

**Hat**: External Developer of the System (Hat B per CLAUDE.md §"The Two Hats").
**Trigger**: Operator screenshot of yarnnn-author's `/feed` surface (2026-05-21T00:54Z) showed visually-duplicated action lines across two adjacent Reviewer wake cards + a same-day stack of identical-looking `Schedule` lines. Operator framing: *"some duplication actions on the feed, can you audit on this"* + *"this is more than one workspace issue"*.

**Scope**: All live workspaces with `_hooks.yaml` defined (3 workspaces) + the underlying walker / Reviewer-loop / feed-narration code paths. NOT scoped narrowly to yarnnn-author because the operator explicitly framed it as a system-level concern.

## What this folder is

Hat-B observation that distinguishes **three different patterns of "duplication"** the feed appears to show, traces each to its root cause, and recommends fix shapes. The downstream Hat-A commits (separate from this folder) land the actual fixes; the resolution addendum closes the loop.

This is the second exercise of the in-session three-commit cross-hat discipline added to CLAUDE.md §"The Two Hats" earlier today (commit `3ba880b`). First exercise was the substrate-event walker fix.

## Pattern 1 — Same revision re-firing across 6 scheduler ticks (REAL BUG, cost-significant)

### Observed

The yarnnn-author canary write at 2026-05-20T23:48:12Z (revision `43d8f1a3`, single transition `status: draft → ready_for_review` on `governance-as-trust/profile.md`) produced **6 Reviewer wakes** across 6 minutes:

| # | wake_id | created_at | duration_ms |
|---|---|---|---|
| 1 | `73cbe656` | 2026-05-21T00:12:07Z | 64,796 |
| 2 | `5f51db26` | 2026-05-21T00:12:56Z | 22,357 |
| 3 | `8f434a2c` | 2026-05-21T00:14:19Z | 28,987 |
| 4 | `d01d4ed3` | 2026-05-21T00:15:31Z | 30,865 |
| 5 | `40fdabca` | 2026-05-21T00:17:17Z | 73,987 |
| 6 | `42905fb3` | 2026-05-21T00:18:17Z | 21,183 |

All carry `wake_source='substrate_event'`, `funnel_decision='escalate'`, `mode='judgment'`, `slug='pre-ship-audit'`. Total **323,035 tokens** consumed, **$1.35 spent** for what should have been ONE wake. Wakes stopped at 00:18:17Z when the canary revision (23:48:12Z) fell outside the walker's 30-minute lookback window.

### Root cause

`services/wake_sources/substrate_event.py::walk_hooks` has a 30-minute lookback (line 264-265: `since = datetime.now(timezone.utc) - timedelta(minutes=30)`) intended to catch hooks that fire during a missed scheduler tick (the comment is explicit: *"30min covers up to 6 missed ticks"*). The walker queries `workspace_file_versions` rows in that window, matches each against declared hooks via the transition guard `_field_change_matches`.

**The transition guard protects against re-firing on preserving writes** (correctly skips a write that preserves the matched state). It does NOT protect against re-firing the same matched revision across multiple scheduler ticks. With a 30-min lookback and `*/1 * * * *` scheduler cadence, a single matched transition revision becomes 30 successive wakes — one per tick — until the lookback expires.

The transition-guard comment hints at the intent: *"Over-firing within a single transition is prevented by the field_change transition guard."* That intent is wrong as implemented — the guard prevents over-firing *within the same write*, not *across walks of the same revision*.

### Cost impact at scale

Per-workspace ceiling per `_hooks.yaml`-matched transition under current behavior: **30 wakes** (one per `*/1` tick during 30-min lookback). With Sonnet @ ~$0.005/wake average, that's ~$0.15 per single hook match. Real operators flipping multiple drafts/day in a workspace with multiple hooks ⇒ accumulating dollar-per-day burn from a single architectural omission.

### Blast radius

| user_id | _hooks.yaml bytes | currently-matched revisions in 30min lookback |
|---|---|---|
| `0b7a852d` (yarnnn-author) | 4429 (alpha-author pre-ship-audit hook) | 1 (the canary) → 6 wakes observed |
| `29a74c63` | 1336 (empty `hooks: []`) | 0 (no harm — empty list) |
| `2abf3f96` (alpha-trader / kvk) | 1336 (empty `hooks: []`) | 0 (no harm — empty list) |

Only yarnnn-author hit this in practice today because it's the only workspace with a non-empty `hooks:` list. The moment real alpha-author / future operators flip drafts, the burn lights up across every active workspace.

### Fix recommendation: wake-proposal idempotency at `execution_events`

Three candidate layers; one chosen below.

- **Option 1 (chosen)** — Add `wake_dedup_key TEXT NULL` column to `execution_events`. Walker computes the key per matched revision (`revision_id` for substrate_event) and skips submission if `execution_events` already carries a row with the same `(user_id, slug, wake_source, wake_dedup_key)` tuple. Generalizable: future wake sources can populate `wake_dedup_key` with their natural identity (`proposal_id` for proposal_arrival, etc.). Uses the existing canonical telemetry surface; no new tables.
- Option 2 — Dedicated `wake_proposal_history` table. Rejected: new table for a single concern; `execution_events` is already the natural home.
- Option 3 — Per-instance LRU. Rejected: doesn't survive scheduler restarts, doesn't work multi-instance.
- Option 4 — Per-user "high water mark" timestamp. Rejected: loses missed-tick recovery semantics; doesn't handle multiple hooks on the same path.

**Implementation shape**:
1. Migration 178: `ALTER TABLE execution_events ADD COLUMN wake_dedup_key TEXT NULL` + partial unique index `(user_id, wake_source, wake_dedup_key) WHERE wake_dedup_key IS NOT NULL`.
2. `services/telemetry.py::record_execution_event` gains `wake_dedup_key: Optional[str] = None` parameter.
3. `services/wake_sources/substrate_event.py::walk_hooks` calls a new helper `_already_fired_for(client, user_id, slug, revision_id) -> bool` before `submit_wake_proposal`; skips if True.
4. `services/wake.py::_invoke_substrate_event_wake` records the `wake_dedup_key=revision_id` on its final `record_execution_event` call.
5. Regression test extends `test_adr296_substrate_event_walker.py` with a "same revision walked twice → fires once" assertion.

Race-window note: theoretical sub-30s race between walker check + Reviewer-complete-write where a second scheduler tick could double-fire. In practice scheduler ticks at `*/1 * * * *` are well-separated; race window is the Reviewer's full LLM duration (~20-75s) which IS larger than the tick interval. Worth tightening with INSERT-on-claim if observed; documented as known race in the ADR amendment.

## Pattern 2 — Reviewer wrote `standing_intent.md` twice per wake (LLM iterative behavior, mild)

### Observed

Within the first wake (00:12:07Z, 64.8s duration), the Reviewer produced TWO revisions on `/workspace/review/standing_intent.md`:

| revision_id | created_at | message |
|---|---|---|
| `daa312db` | 00:11:43Z | `WriteFile workspace review/standing_intent.md` |
| `7d6224f4` | 00:12:03Z | `WriteFile workspace review/standing_intent.md` |

Same pattern in wake #5 (00:17:17Z): `05eb1c1b` at 00:16:53Z + `f1707cae` at 00:17:12Z (19s apart).

The Reviewer's tool-use loop emits `WriteFile` in round N, then refines and emits `WriteFile` again in round N+M. Both succeed; both produce real revisions per ADR-209. The feed shows both as adjacent identical lines.

### Root cause

Two layers:
- **Hook prompt** allows multiple writes to the same file. The instruction *"AND update /workspace/review/standing_intent.md with what you'll be watching for"* is a SINGLE update in intent but the prompt doesn't constrain "ONCE at end of audit."
- **Feed narration** doesn't collapse consecutive same-path same-actor writes within one invocation. Per-write narration is structurally honest (one revision → one narration) but visually noisy when the writes are iterative refinement.

### Fix recommendation: feed-side collapse, not prompt restriction

Option A — Tighten hook prompt: *"Update standing_intent.md ONCE at the end of the audit"*. Rejected as primary fix because (a) iterative refinement is honest LLM behavior, (b) the same pattern recurs across other recurrences' prompts (corpus-coherence-check, revision-audit, outcome-reconciliation all instruct standing_intent updates), (c) doing the prompt-side fix in N places is N times the surface to maintain.

Option B (chosen) — Feed-side collapse within `services/reviewer_chat_surfacing.py::surface_reviewer_actions`: when consecutive actions in `actions_taken` share `(tool, path)` within the same invocation, emit ONE narration line summarizing them ("Wrote 2 revisions to …"). The revision chain itself preserves both writes per ADR-209 — operator can audit them via the Files surface. The feed surfaces *judgment* not *every keystroke*.

## Pattern 3 — `Schedule × 2` looks duplicated but is two distinct slugs

### Observed

Feed entry on May 18 at 21:02 KST (12:02Z UTC) shows two adjacent lines:

```
Executed `Schedule` on Reviewer's direction. path=/workspace/_recurrences.yaml    09:02 PM
Executed `Schedule` on Reviewer's direction. path=/workspace/_recurrences.yaml    09:02 PM
```

DB substrate shows two DIFFERENT recurrences created:

| revision_id | created_at | message |
|---|---|---|
| `6cfd74a9` | 12:02:20Z | `created recurrence weekly-corpus-review (mode=judgment)` |
| `030deddd` | 12:02:21Z | `created recurrence quarterly-voice-audit (mode=judgment)` |

The Reviewer did its ADR-275 job — read `_preferences.yaml` and authored Schedule calls for declared deliverable cadences. **Not a duplication**: two distinct work items that look identical because the narration template uses `path=` which is identical for both.

### Root cause

`api/agents/reviewer_agent.py::_summarize_result` returns `path=…` for any result dict carrying a `path` key, BEFORE checking for more semantic identifiers. Schedule's response includes both `slug` (the recurrence slug, distinct per action) and `path` (always `/workspace/_recurrences.yaml`). Current logic prefers `path` → identical summary across distinct actions.

```python
def _summarize_result(result: Any) -> str:
    if not isinstance(result, dict):
        return "ok"
    if result.get("success") is False:
        return f"error: {result.get('error') or 'unknown'}"
    if "path" in result:        # <-- matches Schedule first
        return f"path={result['path']}"
    if "proposal_id" in result:
        return f"proposal_id={result['proposal_id'][:8]}..."
    if "slug" in result:        # <-- never reached for Schedule
        return f"slug={result['slug']}"
    return "ok"
```

### Fix recommendation: reorder + enrich `_summarize_result`

Move `slug` ahead of `path` (slug is more semantic when present), and for Schedule specifically include the action verb ("create", "update", "archive"). After the fix, the same May 18 entries would render:

```
Executed `Schedule` on Reviewer's direction. action=create slug=weekly-corpus-review
Executed `Schedule` on Reviewer's direction. action=create slug=quarterly-voice-audit
```

No longer reads as duplication.

## Cross-pattern summary

| Pattern | Layer | Shape | Cost impact | Urgency |
|---|---|---|---|---|
| 1: same revision re-fires across ticks | walker (kernel) | architectural omission of idempotency | $1.35/canary observed; scales linearly | HIGH (cost + correctness) |
| 2: intra-wake double-write on same path | reviewer loop + feed | LLM iteration + feed-side noise | none (substrate is honest) | LOW (cosmetic noise) |
| 3: Schedule narration collapses to identical line | feed narration template | summary helper prefers wrong field | none (substrate is correct) | LOW (cosmetic misread) |

## Recommended fix sequence

Three Hat-A commits, each independent + each landing a single concern:

- **Commit A — wake-proposal idempotency** (migration 178 + walker dedup + telemetry param + regression test). Highest priority; closes the cost burn + correctness gap on Pattern 1.
- **Commit B — feed-side collapse of consecutive same-path same-actor writes** (`reviewer_chat_surfacing.py::surface_reviewer_actions` adds a fold step before emit). Closes Pattern 2.
- **Commit C — `_summarize_result` reorder + enrich** (`reviewer_agent.py`). Closes Pattern 3.

After Commits A+B+C land + deploy, re-run the yarnnn-author canary (single status-flip) and confirm:
- One `pre-ship-audit` wake (not 6).
- One feed narration line for the standing_intent write (not 2-4).
- Future Schedule × N narrations carry distinct slugs (no need to re-fire for this; existing May 18 entries are historical artifact).

Resolution addendum in this folder captures all three confirmations.

## What this folder will NOT do

- No system canon edits. All three fixes land in subsequent Hat-A commits (separate from this folder per the three-commit-shape discipline added to CLAUDE.md earlier today).
- No chat to YARNNN, no scenario fires, no operator-proxy writes (the audit is read-only — psql queries + Render logs + code grep).
- No touch to the parallel ADR-275 amendment work in the same checkout (modified files visible in `git status` but not staged here).

## Cross-references

- Walker code: [`api/services/wake_sources/substrate_event.py`](../../../api/services/wake_sources/substrate_event.py) — `walk_hooks` (lookback window line 264) + `_field_change_matches` (transition guard line 175)
- Wake gateway: [`api/services/wake.py`](../../../api/services/wake.py) — `_invoke_substrate_event_wake` (line 1321) + `record_execution_event` call sites
- Telemetry: [`api/services/telemetry.py`](../../../api/services/telemetry.py) — `record_execution_event` (line 109)
- Migration 177 precedent: [`supabase/migrations/177_adr296_execution_events_wake_columns.sql`](../../../supabase/migrations/177_adr296_execution_events_wake_columns.sql)
- Feed narration: [`api/services/reviewer_chat_surfacing.py`](../../../api/services/reviewer_chat_surfacing.py) — `surface_reviewer_actions` (line 246) + `narrate_reviewer_action` (line 228)
- Action summary: [`api/agents/reviewer_agent.py`](../../../api/agents/reviewer_agent.py) — `_summarize_result` (line 1623)
- Prior session fix: commit `5364ca7` (walker async-context-leak + workspace_blobs join)
- Cross-hat discipline: commit `3ba880b` (CLAUDE.md + hook amendment)
- Parent canary observation: [`2026-05-20-234300-yarnnn-author-substrate-event-canary/`](../2026-05-20-234300-yarnnn-author-substrate-event-canary/findings.md)
- ADR-296 v2: [`ADR-296`](../../adr/ADR-296-continuous-judgment-cycle.md)
- ADR-289 invocation-id taxonomy (the related telemetry layer): [`ADR-289`](../../adr/ADR-289-invocation-id-taxonomy.md)

## Capture method (reproducibility)

All findings derived from:

- Operator screenshot of `/feed` surface (2026-05-21T00:54Z) for visual evidence.
- psql against Supabase prod via `docs/database/ACCESS.md` for substrate evidence — `execution_events`, `workspace_file_versions`, `workspace_files`.
- Render API logs via MCP for scheduler-side tick + walker-fire confirmation.
- Code reads against `api/services/wake_sources/substrate_event.py`, `api/services/wake.py`, `api/services/telemetry.py`, `api/services/reviewer_chat_surfacing.py`, `api/agents/reviewer_agent.py`, `api/services/primitives/schedule.py`, `supabase/migrations/177_*.sql`.

No operator-proxy writes, no chat messages, no scenario runs were issued during this audit. Hat-B observation-only discipline preserved.
