# ADR-219: Invocation and Narrative — Implementation

> **Status**: Proposed — staged across six commits.
> **Date**: 2026-04-25
> **Authors**: KVK, Claude
> **Dimensional classification**: **Channel** (Axiom 6) primary, **Trigger** (Axiom 4) + **Substrate** (Axiom 1) secondary.
> **Ratifies for implementation**: FOUNDATIONS v6.8 Axiom 9 + [invocation-and-narrative.md](../architecture/invocation-and-narrative.md) + GLOSSARY v1.9.
> **Amends**: ADR-138 (tasks reframed as legibility wrappers; schema unchanged), ADR-163 + ADR-198 (Chat is not a destination — it is the narrative surface; `/work` is the narrative filtered by task slug, not a parallel substrate), ADR-167 v2 (list/detail surface pattern preserved; data source for `/work` list view re-articulated as filter-over-narrative), ADR-164 (back-office tasks emit narrative entries — additive, schema unchanged).
> **Preserves**: ADR-141 (execution mechanism layers unchanged), ADR-169 (MCP as fifth caller of `execute_primitive()` — invocations from `external:<client>` Identity), ADR-194 v2 + ADR-211 (Reviewer substrate unchanged; narrative emission is additive on top of `decisions.md`), ADR-205 (chat-first triggering, run-now-default — inline addressed invocations under the new framing), ADR-209 (Authored Substrate — narrative entries inherit `authored_by`).

---

## Context

FOUNDATIONS v6.8 Axiom 9 (2026-04-25) ratified three commitments that were previously implicit:

1. **Invocation** is the atom of action — one cycle through the six dimensions, actor-class-agnostic.
2. **Narrative** is a single chat-shaped log of every invocation, with material/routine/housekeeping rendering weights.
3. **Tasks** are legibility wrappers (nameplate + pulse + contract) over recurring categories of invocations; `/work` is the narrative filtered by task slug, not a parallel substrate.

The vocabulary canon is in place. This ADR scopes the implementation that makes the canon enforceable in code and operator-visible in the cockpit.

The implementation is not greenfield. Three load-bearing pieces already exist:

- **`session_messages` table** with a recently widened role enum (`user`, `assistant`, `system`, `reviewer`) per migration 160 — the table is already evolving from "chat conversation" toward "workspace narrative." This ADR ratifies that direction and finishes the move.
- **`agent_runs` table** — neutral audit ledger per FOUNDATIONS Axiom 1 permitted-row kind 2. Already records every invocation. Untouched by this ADR.
- **Surface routing** — `/chat` and `/work` exist as separate React surfaces. Their data sources need the conceptual reshape described below; the URL structure stays.

The drift this ADR closes: `/work` currently fetches from `agent_runs` + `tasks` as a parallel substrate; back-office invocations and Reviewer verdicts have inconsistent surfacing in `/chat`; MCP-caller invocations have no narrative surface at all; the inline-to-task graduation flow has no UX affordance.

---

## Decision

### D1 — `session_messages` is the narrative substrate (no new table)

The narrative log lives in `session_messages`. The recent migration 160 (Reviewer role addition) and migration 123 (`thread_agent_id`) already established the pattern: `session_messages` is the unified chat-thread substrate where multiple Identity classes write entries that the operator reads chronologically.

This ADR finishes the move:

- **The role enum widens once more** to `('user', 'assistant', 'system', 'reviewer', 'agent', 'external')`.
  - `agent` — invocations by user-authored domain Agents (currently routed through `assistant` — that conflation breaks attribution; we split it).
  - `external` — MCP-caller invocations (foreign LLMs via `pull_context` / `remember_this` / `work_on_this`).
- **`metadata` JSONB extension** carries the narrative-entry envelope:
  - `invocation_id` — links the entry to its `agent_runs` row (or null for operator-authored messages).
  - `task_slug` — the task nameplate this invocation was labeled with, or null for inline actions.
  - `pulse` — `'periodic'` | `'reactive'` | `'addressed'` | `'heartbeat'`.
  - `weight` — `'material'` | `'routine'` | `'housekeeping'`.
  - `summary` — one-line headline (used for collapsed rendering).
  - `provenance` — array of substrate pointers (output folder paths, decision.md line refs, `_performance.md` section anchors).
- **No sibling `narrative_entries` table.** A new table would re-introduce the `/chat`-vs-`/work` substrate split this ADR collapses. One log, one source of truth.

Rejected alternative: separate `narrative_entries` table joined to `session_messages` for chat-only entries. Considered and rejected because it preserves exactly the dual-substrate confusion Axiom 9 dissolves. The cost of widening `metadata` is bounded; the cost of a parallel log is unbounded conceptual drift.

### D2 — Every invocation emits exactly one narrative entry

The pipeline that runs invocations (`task_pipeline.execute_task()`, `chat.py` YARNNN turn, MCP `server.py` primitive dispatch, Reviewer dispatch in `review_proposal_dispatch.py`, back-office task executors via `_execute_tp_task()`) gains a single helper:

```python
# api/services/narrative.py (new)
def write_narrative_entry(
    client,
    user_id: str,
    session_id: str,
    role: Literal['user', 'assistant', 'system', 'reviewer', 'agent', 'external'],
    invocation_id: str | None,
    task_slug: str | None,
    pulse: Literal['periodic', 'reactive', 'addressed', 'heartbeat'],
    weight: Literal['material', 'routine', 'housekeeping'],
    summary: str,
    body: str | None = None,
    provenance: list[dict] | None = None,
) -> dict:
    ...
```

Every invocation call site invokes `write_narrative_entry` exactly once at termination (success or graceful failure). The function is the **single write path** — no other code path inserts into `session_messages` after this ADR lands. Existing direct `session_messages` inserts in `chat.py`, `task_pipeline.py`, etc. are migrated to the helper in Commit 2.

Authorship inherits from FOUNDATIONS Derived Principle 13: the Identity that ran the invocation is the entry's `authored_by` (recorded in `metadata.authored_by` since `session_messages` itself is not under `workspace_files` Authored Substrate).

### D3 — Default weight policy (deterministic, code-level)

Weight is determined by a small deterministic policy in `narrative.py`:

| Invocation shape | Default weight |
|---|---|
| Operator chat message | `material` (always) |
| YARNNN reply with substrate write | `material` |
| YARNNN reply with no substrate change | `routine` |
| Agent task run delivering to a task output folder | `material` if first delivery in 24h; else `routine` |
| Reviewer verdict on a proposal | `material` (always) |
| Reactive task firing on platform event | `material` (the event is the news) |
| Back-office task with substantive change | `routine` |
| Back-office task with no change (cleanup found nothing) | `housekeeping` |
| Heartbeat with empty-state output | `housekeeping` |
| MCP `pull_context` from external LLM | `routine` |
| MCP `remember_this` write from external LLM | `material` |

Weight can be overridden per-call (e.g., a Reviewer verdict on a low-impact proposal could be marked `routine`). Default policy ships first; per-shape overrides are added when operator feedback shows they're needed.

### D4 — `/work` list view becomes a filter-over-narrative

`web/components/work/WorkListSurface.tsx` data source is rewritten:

- **Today**: queries `tasks` joined against `agent_runs` for last-run metadata.
- **After**: queries `session_messages WHERE metadata->>'task_slug' IS NOT NULL` grouped by `task_slug`, joined against `tasks` for the nameplate metadata (status, schedule, mode, essential flag).

The list still surfaces task slug + status + last-run + filter chips (output_kind / agent / status / schedule). What changes: the *items* are tasks (the legibility wrappers), the *recent activity* is read from the narrative, the *click-through* takes the operator to the task-detail surface where the per-task narrative slice is also rendered.

Implementation note: `agent_runs` queries are not deleted — `agent_runs` remains the audit ledger and continues to back the per-task run-history view in `WorkDetail`. The change is that `/work` list-view headlines are sourced from the narrative for consistency with `/chat`.

### D5 — `/chat` renders the full narrative with weight-driven density

`web/app/(authenticated)/chat/page.tsx` and the chat message-list component evolve:

- **Material entries**: rendered as full cards (existing `assistant` / `reviewer` rendering pattern extends to `agent` + `external`). Action affordances inline (e.g., approve/reject for proposal cards).
- **Routine entries**: rendered as collapsed lines — Identity icon + summary + timestamp + expand affordance. Click expands to material-shape rendering.
- **Housekeeping entries**: rolled up into a daily digest card ("12 housekeeping invocations on 2026-04-25 — all clean") with expand-to-list affordance. The digest is itself a narrative entry written by `system:back-office-digest` once daily.

Filter affordances on `/chat` (deferred to Commit 5 frontend phase): by Identity (Agent / Reviewer / YARNNN / external), by task slug, by pulse sub-shape, by weight, by time range. Each filter is a query-param on `/chat`; deep-linkable.

### D6 — Inline-to-task graduation UX

The new vocabulary makes the graduation gradient legible. Two affordances ship in Commit 5:

1. **On a material-weight inline-action narrative entry**, a "Make this recurring" affordance appears. Clicking opens `CreateTaskModal` pre-filled with the inline action's primitive call as the seed (objective phrasing + suggested schedule). Operator confirms; `ManageTask(action='create')` fires; future invocations inherit the new task slug.

2. **On a task-detail surface**, an "Archive task (keep history)" affordance detaches the pulse but preserves the nameplate. Future operator asks of the same shape route as inline actions again. The narrative thread under the archived slug remains queryable.

Reversibility is the test: the operator should never feel the transition is irreversible.

### D7 — Six-commit staged implementation

This ADR is **Commit 1 — ratification only, docs only**. The remaining five commits land sequentially, each green:

- **Commit 2 — Narrative substrate + write path** (~150 LOC + migration 161). Migration widens `session_messages.role` enum to add `'agent'` and `'external'`. New `api/services/narrative.py` with `write_narrative_entry()` helper + weight policy. Existing direct `session_messages` inserts (chat.py, task_pipeline.py, review_proposal_dispatch.py, MCP server.py) migrated to the helper in the same commit. `agent_runs` writes continue in parallel (audit ledger, untouched). Test gate: `api/test_adr219_narrative_write_path.py` — assert every invocation in a fixture run produces exactly one narrative entry with correct envelope.

- **Commit 3 — Back-office digest task** (~80 LOC + 1 task type). New back-office task `back-office-narrative-digest` (executor `services.back_office.narrative_digest`). Runs daily after housekeeping cron; folds the day's `housekeeping`-weight entries into one `system:back-office-digest`-authored material-rendered roll-up entry. Closes Axiom 9 Clause B's "every invocation logged, weight determines visibility" commitment.

- **Commit 4 — `/work` list view as filter-over-narrative** (~120 LOC frontend + 1 backend endpoint). New `GET /api/narrative/by-task` returns task-grouped narrative slices with last-material-entry + counts. `WorkListSurface.tsx` consumes the new endpoint instead of `tasks + agent_runs` join. `/work` list cards show consistent recent-activity headlines with `/chat` material entries.

- **Commit 5 — `/chat` weight-driven rendering + inline-to-task affordance** (~200 LOC frontend). Material/routine/housekeeping render styles. Filter affordances. "Make this recurring" affordance on material inline-action entries. "Archive task (keep history)" affordance on task-detail.

- **Commit 6 — MCP narrative emission + final grep gate** (~60 LOC + test). MCP `server.py` writes `external:<client>`-authored narrative entries on each tool call (with `weight='routine'` for `pull_context`, `weight='material'` for `remember_this`). Final test gate: `api/test_adr219_invocation_coverage.py` asserts every invocation site in the codebase routes through `write_narrative_entry()` (grep gate, similar to ADR-209 Phase 5 final gate). ADR-219 status flips to `Implemented`.

---

## Consequences

### Positive

- **Single source of truth for "what happened."** Operator scrolls `/chat`, sees everything; opens `/work`, sees everything filtered by task. No more split-attention between two surfaces with subtly different views of the same activity.
- **Channel legibility (Principle 12) becomes structurally enforceable.** Every autonomous invocation has a narrative home by construction; the grep gate in Commit 6 prevents drift.
- **MCP cross-LLM continuity (ADR-169 thesis) gains a visible substrate.** When ChatGPT pulls context at 3pm, the operator sees the entry in the narrative at 4pm. The cross-LLM workflow becomes observable, which is the point.
- **Inline-to-task graduation has UX.** The conceptual collapse (atom-is-the-same-throughout) becomes a reversible one-click affordance, not an architectural footnote.
- **`session_messages` evolves cleanly.** No new table, no parallel storage, no migration burden beyond a metadata-shape extension and a role-enum widening.

### Negative / risks

- **Volume.** `session_messages` becomes the highest-write table. Mitigation: housekeeping-weight entries are rolled up by the daily digest task (Commit 3), so steady-state row growth tracks material+routine entries only — same rough volume as today's chat usage.
- **Weight-policy drift.** Default weights baked into `narrative.py` may need calibration per shape. Mitigation: weight is a `metadata` field, not a column — adjusting after launch is a code change, not a migration. Operator feedback will surface miscalibration fast.
- **Dual rendering complexity on `/chat`.** Three weight tiers means three rendering paths. Mitigation: Commit 5 ships material + routine first; housekeeping digest is a single rolled-up entry with collapsed-by-default rendering, lowest-complexity tier.

### Out of scope (deferred or rejected)

- **Narrative search.** Full-text search across `session_messages` is doable today via the existing `chat_sessions` content. A dedicated narrative-search affordance is deferred until operator usage shows the need.
- **Per-Identity threads as separate views.** "Show me only Reviewer verdicts" is achievable via the filter (`?reviewer`) — does not need a separate surface. Threads-as-surfaces is rejected for the same reason `/work` ≠ parallel substrate.
- **External-caller permission gates on narrative emission.** MCP callers can write narrative entries unconditionally because they already passed primitive-layer auth (ADR-169). Rate-limiting at the narrative layer is not added; rate-limiting is upstream.

---

## Validation

The ADR is ratified by FOUNDATIONS v6.8 Axiom 9 — the canon doc is the upstream commitment, this ADR is the implementation. After Commit 6 lands, two assertions must hold:

1. **Coverage**: every invocation site in the codebase (greppable list of `execute_primitive` callers + task pipeline + Reviewer dispatch + MCP server + back-office executors) routes through `write_narrative_entry()`. Final test gate enforces this.

2. **Filter equivalence**: `SELECT count(*) FROM session_messages WHERE user_id = X AND created_at >= D` equals the operator's mental model of "things that happened in my workspace today." If the operator returns and asks "what happened while I was away," scrolling `/chat` is the answer — no separate surface required.

Both assertions are testable. Commit 6 lands the second as an evaluation item before status flips to `Implemented`.

---

## Open questions (carried forward, do not block ratification)

1. **Compaction policy for the narrative.** ADR-067 + ADR-159 already compact chat history. As the narrative absorbs more invocations, does the compaction window stay at 10 messages, or does material/routine/housekeeping weighting let us keep richer history without prompt bloat? Likely the latter — compact housekeeping aggressively, preserve material; deferred to follow-up after Commit 5 ships.

2. **Cross-workspace narrative for polymath operators (ADR-191).** When an operator runs multiple workspaces, is each narrative scoped to its workspace, or is there a meta-narrative? Current ADR scopes to per-workspace; meta-narrative is a separate ADR if/when needed.

3. **Audio / multimodal narrative entries.** A Reviewer verdict could be a 30-second voice clip; an inline-action result could be an image. The `metadata.body` field is text today. Multimodal extension is straightforward (supabase storage URLs in `provenance`) but deferred until a use case ships.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-04-25 | v1 — Initial proposal. Six-commit staged implementation: substrate + write path, back-office digest, /work as filter, /chat weight rendering, inline-to-task affordance, MCP emission + final gate. |
