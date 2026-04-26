# ADR-219: Invocation and Narrative — Implementation

> **Status**: **Implemented** (Commits 1–6 landed 2026-04-25 / 2026-04-26).
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

- **Commit 2 — Narrative substrate + write path** (Implemented 2026-04-25). Migration 161 widened `session_messages.role` to add `'agent'` and `'external'` (final enum: user / assistant / system / reviewer / agent / external). `api/services/narrative.py` lands `write_narrative_entry()` as the **single write path** into `session_messages` — RPC-first with direct-insert fallback collapsed into one site. Helper validates role/pulse/weight pre-flight (matches the migration-161 CHECK constraint), enforces summary required, and applies the ADR-219 D3 default weight policy via `resolve_default_weight()`. The envelope (summary, pulse, weight, invocation_id, task_slug, provenance) lives in metadata JSONB; envelope keys win over caller `extra_metadata` on collision. Migrated call sites — all atomically in this commit, no shims: `routes/chat.py::append_message()` (now a thin envelope-builder delegate; the four callers — user-message append, YARNNN-reply append, memory.py workspace_init card, task_pipeline.py task_complete card — pass envelope fields via metadata and route through it), `services/reviewer_chat_surfacing.py::write_reviewer_message()` (collapsed to one `write_narrative_entry` call; reviewer = role='reviewer', pulse='reactive', weight='material'), `services/notifications.py::_insert_chat_notification()` (replaces direct RPC; pulse='reactive', weight='routine'), `services/task_pipeline.py` task_complete card (pulse='periodic', weight='material', invocation_id=str(version_id), provenance points at output folder). MCP narrative emission deferred to Commit 6 per D7. `agent_runs` writes untouched. Test gate `api/test_adr219_narrative_write_path.py` — 8/8 assertions pass: role validation, pulse/weight validation, summary required, default weight policy table (8 rows), envelope flows through RPC with envelope-wins-over-extra collision rule, summary-as-content fallback, `is_valid_envelope` helper, and the **B1 coverage gate** — git-grep enforcement that no live file outside an explicit allowlist makes raw `.table("session_messages").insert(...)` or direct `append_session_message` RPC calls. Per ADR-186 / Prompt Change Protocol, no prompt body changed; logged in `api/prompts/CHANGELOG.md` for substrate-change traceability.

- **Commit 3 — Back-office digest task** (Implemented 2026-04-25). New back-office task `back-office-narrative-digest` registered in `TASK_TYPES` (`output_kind=system_maintenance`, `default_mode=recurring`, `default_schedule=daily`, executor `services.back_office.narrative_digest`). Executor scans the past 24h of `session_messages` owned by the user (joined through `chat_sessions.user_id`), groups by `metadata.weight`, and emits **exactly one material-weight rolled-up narrative entry** when housekeeping entries exist in the window — empty-state writes nothing (the digest is a response to noise, not a heartbeat). Rollup envelope per ADR-219 D2: `role='system'`, `pulse='periodic'`, `weight='material'`, `metadata.system_card='narrative_digest'`, `metadata.rolled_up_count`, `metadata.rolled_up_window_hours`, `metadata.rolled_up_ids` (bounded at 200), `metadata.counts` per weight bucket, `metadata.authored_by='system:back-office-narrative-digest'`. **Originals stay** in `session_messages` — the rollup is purely additive (preserves Commit 6's coverage gate that every invocation has a narrative entry; Commit 5 frontend will render the rollup as expand-to-list using `rolled_up_ids`). Promoted `find_active_workspace_session(client, user_id)` from `reviewer_chat_surfacing.py` into `services.narrative` as the canonical session resolver for autonomous narrative entries — `reviewer_chat_surfacing` migrated to import the shared helper, local `_find_active_workspace_session` deleted (singular implementation discipline). Untagged session_messages rows (legacy entries without the ADR-219 envelope) bucket into `counts.untagged` and do **not** pollute the rollup. Trigger semantics deferred: the spec calls for materialize-on-first-housekeeping-emission, but Commits 2–3 leave back-office executors emitting workspace_files outputs only (not narrative entries yet — that integration lands in Commit 6 alongside MCP emission and the final coverage grep gate). Until then, operators can opt the digest in via `ManageTask(action="create", type_key="back-office-narrative-digest")`. Test gate `api/test_adr219_commit3_narrative_digest.py` — 6/6 assertions pass: empty-state (no rollup when 0 housekeeping), rollup envelope (one material entry with rolled_up_count + rolled_up_ids + counts), graceful skip when no active session, untagged entries do not pollute rollup, registry entry correctness, helper promotion to narrative module.

- **Commit 4 — `/work` list view as filter-over-narrative** (Implemented 2026-04-25). New backend endpoint `GET /api/narrative/by-task` mounted at `api/routes/narrative.py` (router included in `api/main.py` under prefix `/api/narrative`). Returns `NarrativeByTaskResponse` keyed by `task_slug` with three fields per slice: `last_material` (most-recent material entry — summary, role, pulse, created_at, invocation_id), `counts` (rolling 24h totals for material/routine/housekeeping), `most_recent_at` (any-weight timestamp for sort). Two-step query: chat_sessions for the user → session_messages joined via session_id (RLS-scoped + explicit user_id filter). Inline-action rows (no `metadata.task_slug`) are excluded — they surface in `/chat` directly, not via the by-task filter. `last_material` is the most-recent material entry irrespective of window (the headline is "what shipped last," not "what shipped today"); `counts` are window-bounded (default 24h, configurable via `?window_hours=N`). Response sorted by `most_recent_at desc`. ROW_FETCH_CAP at 500 keeps payloads bounded; default window matches `back-office-narrative-digest` so the cockpit headlines and the daily digest agree on "recent." Frontend wiring: `web/types/index.ts` adds `NarrativeMaterialEntry` / `NarrativeCounts` / `NarrativeByTaskSlice` / `NarrativeByTaskResponse`; `web/lib/api/client.ts` adds `api.narrative.byTask(windowHours?)`; `web/hooks/useAgentsAndTasks.ts` extended with `includeNarrative?: boolean` opt-in (off by default — `agents/[id]`, `agents/page`, `chat/page` callers don't fetch narrative); `/work` page opts in. `web/components/work/WorkListSurface.tsx` accepts `narrativeByTask: Map<string, NarrativeByTaskSlice>` and `WorkRow` consumes the slice — replaces the legacy `Last: 5m ago` timestamp with the most-recent material narrative entry's `summary` rendered as a second meta line + relative timestamp on the right. Active scheduled tasks keep their forward-looking `Next: ...` signal (the schedule, not historical activity). Tasks with no narrative entries yet (likely on pre-Commit-2 invocations until next run lands one) show no headline — the row simply doesn't claim activity it can't attribute. Singular-implementation discipline: list-row activity has ONE source now (the narrative); WorkDetail's per-task run-history continues to read `agent_runs` (audit ledger, separate consumer per D7). Other surfaces consuming `task.last_run_at` (settings/system, admin, context, agents detail) are out of scope for Commit 4 — they're different consumers with different framings, evaluated separately. Test gate `api/test_adr219_commit4_narrative_by_task.py` — 10/10 assertions pass: empty-when-no-sessions, inline-actions-excluded, last_material-most-recent-irrespective-of-window, counts-windowed, sort-by-most_recent_at-desc, invalid-weight-ignored-from-counts, no-material-null-headline, plus three frontend-wiring grep assertions (hook exposes narrativeByTask, surface consumes slice, api client wires endpoint).

- **Commit 5 — `/chat` weight-driven rendering + inline-to-task affordance** (Implemented 2026-04-26). `web/types/desk.ts`: `TPMessage.role` widens to mirror migration 161's enum (`user | assistant | system | reviewer | agent | external`); new `NarrativeEnvelope` type carries `summary | pulse | weight | taskSlug | invocationId`; `SystemCardType` extends with `'narrative_digest'`. `web/contexts/TPContext.tsx`: history loader pulls the envelope from `metadata` into `TPMessage.narrative`; the streaming optimistic-UI rows (operator message + initial assistant message) stamp `pulse='addressed', weight='material'` so weight-driven rendering applies live without flickering on history reload; system_card cards now thread `m.content` through `data._body` so the digest card has its bullet list available for expand-to-list. `web/components/tp/ChatPanel.tsx`: introduces `NarrativeMessage` as the per-row weight dispatcher (material → existing card path with `agent`/`external` Identity labels added; routine → collapsed line with chevron + identity tag + summary + timestamp + on-click expand to full content; housekeeping → dim one-liner). Legacy "no envelope" rows default to material so historical messages predating Commit 2 don't disappear. Adds `narrativeFilter` + `onMakeRecurring` props; the `narrativeFilterMatches` helper applies weights/identities/taskSlug filters. **"Make this recurring"** button rendered on operator (`role='user'`) material entries with no `taskSlug` (i.e. inline actions per ADR-219 D6); on click invokes the parent's callback. `web/components/chat-surface/ChatFilterBar.tsx` (new): three deep-linkable query-param-driven filter rows — weight chips, identity chips, task-slug pill (set externally, clearable). Exports `parseChatFilterFromSearch(URLSearchParams)` so the parent surface drives the filter prop. `web/components/chat-surface/ChatSurface.tsx`: imports the bar + parser; `useSearchParams` + `useMemo` keeps the filter in sync with the URL; auto-opens the bar when any filter is active so the operator never gets stranded; new `Filter` icon header action toggles the bar; new `handleMakeRecurring` opens `TaskSetupModal` pre-filled with `Recurring intent: <message-prefix>` so YARNNN turns it into `ManageTask(action='create')` on submit. `web/components/tp/SystemCard.tsx` (extended): new `NarrativeDigestCard` renders the Commit 3 digest entry as a collapsed-by-default card with chevron-toggle expand-to-list, headline (`{count} housekeeping invocations rolled up — all clean`), per-weight count strip, and pre-formatted body bullets on expand. **Deferred from this commit per discipline rule 1 (no half-finished work):** D6's "Archive task (keep history)" affordance — that lives on WorkDetail, not /chat, and pairs cleanly with a future task-lifecycle commit; not gated on Commit 5. **Pulse + time-range filters** also deferred (richer UI requirement, not gated). Test gate `api/test_adr219_commit5_chat_rendering.py` — 12/12 grep-shape assertions pass: TPMessage role union widened, NarrativeEnvelope type exported, SystemCardType narrative_digest, TPContext loader pulls envelope, TPContext threads body to digest card, ChatPanel dispatches on weight (material/routine/housekeeping), narrativeFilterMatches handles all three dimensions, ChatPanel props include narrativeFilter + onMakeRecurring, ChatFilterBar exists with parseChatFilterFromSearch, ChatSurface mounts ChatFilterBar + threads filter to ChatPanel, Make-this-recurring button rendered with proper guards, ChatSurface wires handleMakeRecurring → TaskSetupModal, SystemCard renders narrative_digest with expand-to-list.

- **Commit 6 — MCP narrative emission + final coverage gate** (Implemented 2026-04-26). MCP `server.py` gains a private `_emit_mcp_narrative()` helper that wraps `find_active_workspace_session` + `write_narrative_entry` with the standard `role='external'` envelope. Each of the three tools emits exactly one narrative entry per invocation: **`work_on_this`** → `weight='routine'` (curated read, no substrate change), **`pull_context`** → `weight='routine'` on success/failure both (no write either way; failure path emits so the operator sees the foreign-LLM call landed even when QueryKnowledge errors), **`remember_this`** → `weight='material'` on success (substrate write committed), `weight='routine'` on the ambiguous classification path (clarification needed, no write yet) and on the UpdateContext failure path, `weight='housekeeping'` on the empty-content rejection (the foreign LLM tried but contributed nothing). Every emission carries `extra_metadata.mcp_tool` + `extra_metadata.mcp_client` so /chat filters and the daily-update attribution per ADR-169 can surface foreign-LLM provenance. Best-effort: emission failures never fail the MCP tool itself — the canonical record lives in `mcp_oauth_*` + the substrate writes themselves; narrative is the second read path. **No new env vars** — MCP server already uses `SUPABASE_SERVICE_KEY` for `auth.client`, which is what the helper needs. Final coverage gate `api/test_adr219_invocation_coverage.py` — 4/4 assertions pass: every named invocation entry point reaches `write_narrative_entry` (task pipeline → `chat.append_message` shim, back-office → direct, review dispatch → `write_reviewer_message` shim, propose_action handlers → same shim, notifications → direct, chat append_message → direct, memory workspace_init → `chat.append_message` shim, reviewer_chat_surfacing → direct, MCP server → `_emit_mcp_narrative` shim); each of the three MCP tools emits at least once with the matching `tool="..."` argument; `write_narrative_entry` signature stable (10 named params guarded against rename); `role='external'` only used by MCP server (allowlist enforced via git grep). Combined with the Commit 2 B1 raw-write coverage gate (no `.table("session_messages").insert()` or direct `append_session_message` RPC outside the helper + tests + scripts), the universal-coverage commitment is now structurally enforceable both at the **write-path side** (Commit 2) and at the **invocation-site side** (Commit 6).

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
| 2026-04-25 | v1.1 — Commit 2 landed (migration 161 + `services/narrative.py` + 4 call-site migrations + 8/8 test gate). Status flipped to Commits 1–2 Implemented. Commit 3 (back-office digest task) is next. |
| 2026-04-25 | v1.2 — Commit 3 landed (`back-office-narrative-digest` task type + `services/back_office/narrative_digest.py` executor + `find_active_workspace_session` promoted to `services.narrative` + 6/6 test gate). Status flipped to Commits 1–3 Implemented. Commit 4 (`/work` list view as filter-over-narrative) is next. |
| 2026-04-25 | v1.3 — Commit 4 landed (`api/routes/narrative.py` GET /api/narrative/by-task endpoint + `useAgentsAndTasks` `includeNarrative` opt-in + `WorkListSurface` row migrated to consume narrative slice + 10/10 test gate). Status flipped to Commits 1–4 Implemented. Commit 5 (`/chat` weight-driven rendering + inline-to-task affordance) is next. |
| 2026-04-26 | v1.4 — Commit 5 landed (`TPMessage` role union widened + `NarrativeEnvelope` type + `narrative_digest` SystemCardType + `NarrativeMessage` weight dispatcher in `ChatPanel.tsx` + `ChatFilterBar.tsx` deep-link query-param filters + `handleMakeRecurring` graduation affordance + `NarrativeDigestCard` expand-to-list renderer + 12/12 test gate). "Archive task (keep history)" affordance from D6 deferred to a future task-lifecycle commit. Pulse + time-range filters deferred. Status flipped to Commits 1–5 Implemented. Commit 6 (MCP narrative emission + final coverage grep gate) is next. |
| 2026-04-26 | v1.5 — **Commit 6 landed. ADR-219 Implemented.** MCP server (`api/mcp_server/server.py`) gains `_emit_mcp_narrative` shim + emission on all three tools (`work_on_this` routine, `pull_context` routine on success/failure, `remember_this` material on success / routine on ambiguous + failure / housekeeping on empty-content reject). Final coverage gate `api/test_adr219_invocation_coverage.py` — 4/4 pass; combined with Commit 2's B1 raw-write gate, the universal-coverage commitment is enforceable on both sides (write-path + invocation-site). Total tests across the implementation: **40/40** (8 + 6 + 10 + 12 + 4). Cumulative net change vs. ADR-219 Commit 1 baseline: 13 files modified or added, +3000/−170 LOC across migration 161, `services/narrative.py`, `services/back_office/narrative_digest.py`, `routes/narrative.py`, the MCP server, ChatPanel weight dispatch, ChatFilterBar, NarrativeDigestCard, and the five test gates. |
