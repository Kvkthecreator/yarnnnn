# Workspace Architecture Analysis

Fork Decision, Execution Path Trace, and Memory Audit

YARNNN | March 2026 | Pre-ADR Analysis

---

## Version History

- **v1 (2026-03-02):** Original analysis. FK-scoping approach (Options A and B). Full execution path trace, memory audit, platform content assessment. Recommended Option A (evolve deliverables with FK columns).
- **v2 (2026-03-02):** Reframe. Introduced Option C (context document per deliverable) after recognizing that v1 claimed the filesystem-as-context insight but implemented relational-scoping instead. Sections 1–9 preserved as original analysis. Section 10 is the v2 evolution.
- **v3 (2026-03-02):** Exploratory. Section 11 pushes the filesystem metaphor further — what if everything is a file? Context, progress/todos, instructions, feedback patterns as typed files in a workspace, each feeding a UI component. Examines whether this forces workspace as a first-class entity (container → files) rather than a field on deliverables. Open for Claude Code assessment.
- **v4 (2026-03-03):** OpenClaw architecture deep-dive. Section 12 analyzes OpenClaw's gateway inputs, workspace directory structure, and memory-as-files model. Extracts 6 concrete learnings for YARNNN and maps the YARNNN↔OpenClaw equivalences. Updates the CLAUDE.md mapping table with a third column.
- **v5 (2026-03-03):** Consolidation. Section 13 resolves two remaining questions: (1) Why the filesystem analogy is already strong in YARNNN and doesn't require literal replication, (2) How the gateway/Lane Queue concern separates from the data model concern. Also incorporates the discovery that `projects` table exists as a ghost entity (designed, migrated, indexed, RLS'd, RPC'd — zero rows). Confirms v2 (`work_context` JSONB on deliverables) as the implementation path, with two separated follow-up tracks: data model (work_context → D2 workspace_files → D3 workspaces entity) and execution architecture (gateway + Lane Queue for input routing and concurrency isolation).

---

## 1. The Fork Decision: New Entity vs. Evolved Deliverable

This is the foundational choice. Everything else cascades from it. Both options are defensible, but they have different costs and different ceiling heights.

### 1.1 Option A: Evolve Deliverables into Workspaces

The deliverables table already has: title, description, sources (JSONB), schedule (JSONB), type_config, recipient_context, versions, status. A workspace without a scheduled output is structurally a deliverable with schedule = null.

**What changes:**

- **deliverables.mode** (new column): 'recurring' | 'goal'. Existing rows default to 'recurring'. Goal-mode deliverables have no schedule, and converge toward completion.
- **chat_sessions.deliverable_id** (new nullable FK): Scopes a TP session to a deliverable/workspace. Null = global session (current behavior preserved).
- **user_context.deliverable_id** (new nullable FK): Scopes a memory entry. Null = global memory (current behavior preserved).

**Concrete schema cost:**

- 2 new nullable columns (chat_sessions, user_context)
- 1 new column on deliverables (mode)
- 0 new tables, 0 new RLS policies, 0 new API routes for the entity itself
- Migration: ALTER TABLE ADD COLUMN, all nullable, zero downtime

**The problem:**

Deliverables carry semantic baggage. The word 'deliverable' means 'a thing that gets produced and delivered.' A workspace where you're brainstorming, researching, or just accumulating context doesn't feel like a deliverable. The UI would need to present the same entity differently depending on mode. The frontend route /deliverables/[id] would need to render as either a deliverable detail page or a workspace page. This is the 'dual approaches' smell your CLAUDE.md warns against.

### 1.2 Option B: New Workspaces Table

A workspace is the persistent context container. Deliverables become a child of workspaces.

**What changes:**

- **workspaces** (new table): id, user_id, title, description, mode ('ongoing' | 'goal'), status ('active' | 'completed' | 'archived'), sources (JSONB), created_at, updated_at.
- **deliverables.workspace_id** (new FK): Every deliverable belongs to a workspace. Migration: create a workspace for each existing deliverable, copy sources, set FK.
- **chat_sessions.workspace_id** (new nullable FK): Scopes TP session to workspace.
- **user_context.workspace_id** (new nullable FK): Scopes memory to workspace.

**Concrete schema cost:**

- 1 new table with RLS policies
- 3 new FK columns (deliverables, chat_sessions, user_context)
- New API routes: CRUD for workspaces
- Frontend: new navigation concept, sidebar changes, routing
- Migration: create workspaces from existing deliverables (data migration script)

**The advantage:**

Clean domain separation. A workspace IS a workspace. A deliverable IS a deliverable. No semantic overloading. The frontend can have /workspaces/[id] with a clear mental model. A workspace can have zero, one, or many deliverables. The 'board meeting prep' workspace has research, conversations, and eventually produces a deliverable. The 'weekly Slack digest' workspace has one recurring deliverable.

### 1.3 Recommendation

**Option A (evolve deliverables) is the right choice for now, with a clear path to Option B later.**

Here's why, grounded in your codebase reality:

- **Sources already live on deliverables.** The sources JSONB field on deliverables is the critical piece that scopes which platform_content feeds this work context. In Option B, you'd move sources to workspaces and add a workspace_id FK to deliverables. That's a significant migration for no functional gain today.
- **Your frontend already organizes around deliverables.** Routes: /deliverables/[id], /dashboard/deliverable/[id]/review/[versionId]. Components: deliverables/ directory. The sidebar, the dashboard, the review flow — all deliverable-centric. Option B requires rearchitecting navigation.
- **The 'dual approaches' risk is manageable.** A deliverable with mode='goal' renders differently, but it's one entity in the DB, one set of RLS policies, one API surface. The UI distinction is presentation logic, not data model divergence.
- **The path to Option B is clean.** If you later need workspaces as a first-class entity, the migration is: (1) create workspaces table, (2) for each deliverable, create a workspace, (3) move sources from deliverable to workspace, (4) update FKs. The scoping columns (chat_sessions.deliverable_id, user_context.deliverable_id) just get renamed to workspace_id.

*The third opinion correctly flagged that Option B was adopted too quickly without comparing schema costs. Option A costs 3 columns. Option B costs 1 table + 3 columns + migration script + new routes + new RLS + frontend navigation rework. For a solo founder pre-PMF, that delta matters.*

---

## 2. Execution Path Trace with Workspace Scoping

I traced every function in the chain. Here's what changes and what doesn't, applying Option A (deliverable scoping).

### 2.1 Session Creation Path

Current flow (chat.py lines 76-139):

- `get_or_create_session(client, user_id, session_type, scope)` → checks 4h inactivity boundary → reuses or creates session
- No awareness of deliverable context. Session is global.

**Required changes:**

Add optional deliverable_id parameter. When present, session boundary logic scopes to that deliverable — reuse an active session for THIS deliverable, not just any active session.

| Current Signature | New Signature |
|---|---|
| `get_or_create_session(client, user_id, session_type, scope)` | `get_or_create_session(client, user_id, session_type, scope, deliverable_id=None)` |

The inactivity check query adds: `.eq('deliverable_id', deliverable_id)` when set. Insert adds deliverable_id to the row. Existing callers pass None → zero behavior change.

**RPC change required:** The Python function delegates to the `get_or_create_chat_session` SQL RPC (defined in `supabase/migrations/061_session_compaction.sql`). This RPC currently takes `(p_user_id, p_project_id, p_session_type, p_scope, p_inactivity_hours)`. It needs a new `p_deliverable_id UUID DEFAULT NULL` parameter. The RPC's session-reuse query must add `AND deliverable_id = p_deliverable_id` (or `AND deliverable_id IS NULL` when null). The Python fallback path (lines 112-127, used when RPC fails) also needs the `.eq('deliverable_id', deliverable_id)` filter. This is a migration — new SQL function version, not just a Python change.

### 2.2 Working Memory Injection

Current flow (working_memory.py):

- `build_working_memory(user_id, client)` → returns dict with profile, preferences, known, deliverables, platforms, recent_sessions, system_summary
- All queries are user-scoped, never deliverable-scoped
- `_get_user_context()` → `SELECT * FROM user_context WHERE user_id = ?`
- `_get_recent_sessions()` → last 3 sessions with summaries, no deliverable filter

**Required changes:**

| Current Signature | New Signature |
|---|---|
| `build_working_memory(user_id, client)` | `build_working_memory(user_id, client, deliverable_id=None)` |
| `_get_user_context(user_id, client)` | `_get_user_context(user_id, client, deliverable_id=None)` |
| `_get_recent_sessions(user_id, client)` | `_get_recent_sessions(user_id, client, deliverable_id=None)` |

When deliverable_id is set:

- `_get_user_context()` returns BOTH global memories (deliverable_id IS NULL) AND scoped memories (deliverable_id = ?). Global always present; scoped adds specificity.
- `_get_recent_sessions()` filters to sessions with matching deliverable_id. This is the TP↔headless bridge: TP sees prior conversations about this specific deliverable.
- A new section is added: deliverable detail (title, type, last version content preview, version count, edit history summary). Currently deliverables appear as one-liners; for the scoped view, the active deliverable gets expanded context.

### 2.3 TP Chat Endpoint

Current flow (chat.py POST /chat):

- ChatRequest has surface_context with optional deliverableId
- surface_context is passed to TP system prompt but NOT used for session scoping or working memory

**Required change:**

When surface_context.deliverableId is present AND type is 'deliverable-review' or a new 'workspace' type:

- Pass deliverable_id to `get_or_create_session()`
- Pass deliverable_id to `build_working_memory()`
- The system prompt gains workspace-specific context without any prompt rewrite — it comes through the working memory formatting

This is the key insight: the existing surface_context mechanism already carries the deliverable_id from frontend to backend. The gap was that nothing in the backend used it for scoping. The fix is plumbing, not architecture.

**Frontend UX gap:** The surface_context with deliverableId is currently only sent when the user is viewing a deliverable review page (via `TPContext.tsx` line 322, triggered by `SurfaceData.deliverableId` in `surfaces.ts`). There is no mechanism for a user to say "I want to chat about this deliverable" from the main chat view or dashboard. Phase 1 works for the review-page use case (user is already looking at a deliverable). For broader workspace-scoped chat, Phase 3 needs a workspace selector or navigation affordance so the user can enter a workspace context without being on the review page.

### 2.4 Headless Execution Path

Current flow (deliverable_execution.py):

- `generate_draft_inline()` receives deliverable dict + gathered_context string
- Builds headless system prompt via `_build_headless_system_prompt()`
- Gets `past_versions_context()` for feedback patterns
- NO access to TP session history for this deliverable

**Required change:**

Before building the headless prompt, query recent scoped session summaries:

- `SELECT summary FROM chat_sessions WHERE deliverable_id = ? AND summary IS NOT NULL ORDER BY created_at DESC LIMIT 3`
- Inject as a 'User Context' section in the headless prompt: 'The user has discussed this deliverable in recent conversations: [summaries]'
- This gives the headless agent awareness of what the user discussed with TP

| Function | Change |
|---|---|
| `generate_draft_inline()` | Add scoped_session_summaries parameter |
| `_build_headless_system_prompt()` | Accept + inject session context section |
| `execute_deliverable()` caller | Query scoped sessions, pass to generate_draft_inline |

### 2.5 Concurrent Session Semantics

Adding deliverable_id to session scoping introduces a behavioral question the current architecture doesn't face: can a user have multiple active sessions simultaneously?

**Current behavior:** One active session per user (the 4h inactivity boundary reuses or creates). Simple.

**With workspace scoping:** A user chatting about "Weekly Slack Digest" and then switching to "Board Meeting Prep" would get (or create) a different session for each. Both could be "active" simultaneously — neither has hit the 4h boundary.

**Implications:**

- **Backend:** No structural issue. `get_or_create_session()` scoped by deliverable_id naturally creates independent sessions. The RPC already supports this — it just needs the additional filter.
- **Frontend:** `TPContext` currently manages a single session state. If the user switches workspace context, the frontend needs to either (a) maintain one session at a time and let the backend handle resume-on-return, or (b) track multiple active session IDs. Option (a) is simpler and sufficient for Phase 1 — the backend's 4h boundary handles resume naturally.
- **Working memory:** No issue. `build_working_memory()` is called per-request with the current deliverable_id. Each request gets the right scoped context.
- **Nightly cron:** No issue. Sessions are processed individually regardless of concurrency.

**Recommendation:** No special handling needed. The 4h boundary per (user, deliverable_id) pair naturally supports concurrent workspaces. Frontend stays single-session-at-a-time in the UI. This is a non-issue architecturally but worth documenting so it doesn't surprise during implementation.

---

## 3. Memory System Audit

I read memory.py (786 lines), working_memory.py (639 lines), and the nightly cron entry points in unified_scheduler.py. Here's the concrete assessment.

### 3.1 Current State

The memory system has three write paths:

| Write Path | Trigger | Output |
|---|---|---|
| `process_conversation()` | Nightly cron, processes prior day sessions | fact:\*, preference:\*, instruction:\* rows in user_context |
| `process_feedback()` | User approves edited deliverable version | preference:length, preference:format rows |
| `process_patterns()` | Daily background job | pattern:\* rows (day-of-week, time, type prefs) |

All three write paths write to user_context with user_id scoping only. There is no concept of workspace/deliverable-scoped memory.

### 3.2 What Needs to Change

**The memory framework is not outdated — but it needs scoping.**

The extraction logic (LLM-based fact extraction, heuristic edit pattern analysis, rule-based activity patterns) is sound and should stay. What changes is WHERE memories land:

**user_context table change:**

- Add: `deliverable_id UUID NULLABLE FK` to deliverables
- NULL = global memory (current behavior, all existing rows)
- Set = workspace-scoped memory

**process_conversation() change:**

Currently takes `(client, user_id, messages, session_id)`. It should also take deliverable_id (from the session). When present, extracted facts that are deliverable-specific (e.g., 'wants bullet points in this report') get written with deliverable_id. Facts that are universal ('prefers concise content') still get written as global.

The extraction prompt (memory.py line 274) already distinguishes between stable facts and transient info. It needs one addition: distinguish between universal preferences and deliverable-specific preferences. This is a prompt change, not an architectural change.

**process_feedback() change:**

Currently takes `(self, client, user_id, deliverable_id, original, edited)`. It already has deliverable_id — but it writes to user_context without it. The fix is NOT one line. `_write_memory()` currently takes `(self, client, user_id, key, value, source, confidence)` and upserts on the `UNIQUE(user_id, key)` constraint. To persist scoped memories, three changes are needed:

1. Add `deliverable_id` parameter to `_write_memory()` signature
2. Include `deliverable_id` in the upsert record
3. **Change the unique constraint** (see below)

**Unique constraint problem (critical):**

The current constraint is `UNIQUE(user_id, key)`. One user can have one `preference:format` entry. With workspace scoping, a user might have a global `preference:format` ("prefers concise") AND a workspace-scoped `preference:format` ("prefers detailed for board reports"). These must coexist.

The constraint must become `UNIQUE(user_id, key, deliverable_id)`. However, `deliverable_id` is nullable, and in Postgres `NULL != NULL` in unique constraints. This means multiple global (null) entries with the same key could be inserted without conflict — breaking the current guarantee.

**Solution:** Replace the unique constraint with two partial unique indexes:

```sql
-- Global memories: one per (user, key) when unscoped
CREATE UNIQUE INDEX user_context_global_unique
  ON user_context (user_id, key)
  WHERE deliverable_id IS NULL;

-- Scoped memories: one per (user, key, deliverable) when scoped
CREATE UNIQUE INDEX user_context_scoped_unique
  ON user_context (user_id, key, deliverable_id)
  WHERE deliverable_id IS NOT NULL;
```

This preserves existing behavior for global memories while allowing per-workspace overrides. The `_write_memory()` upsert logic must use `ON CONFLICT` targeting the appropriate index based on whether `deliverable_id` is null.

**working_memory read change:**

Already covered in Section 2.2 — `_get_user_context()` returns global + scoped when deliverable_id is set.

### 3.3 Session Summaries (ADR-067)

`generate_session_summary()` in memory.py writes to chat_sessions.summary via nightly cron. This already works correctly for workspace scoping because summaries are per-session, and sessions will be scoped to deliverables. No change needed to the summary generation itself — the scoping comes from the session's deliverable_id FK.

### 3.4 Nightly Cron Changes (unified_scheduler.py)

The document originally stated "unified_scheduler.py — scheduling logic unchanged." This is incorrect for the memory extraction path.

The nightly cron (runs at midnight UTC, `unified_scheduler.py` lines 926-999) currently:
1. Queries yesterday's `chat_sessions` (lines 934-941)
2. For each session: fetches `session_messages`, calls `process_conversation(client, user_id, messages, session_id)` (lines 964-969)
3. Calls `generate_session_summary()` if enough messages (lines 977-981)

**Required change (Phase 4):** Step 2 must also fetch `chat_sessions.deliverable_id` and pass it to `process_conversation()`. The session query (line 934) needs to include `deliverable_id` in the SELECT. This is plumbing — the cron fetches one more column and passes it through — but it IS a change to `unified_scheduler.py`.

### 3.5 Extraction Prompt Versioning

The extraction prompt (`memory.py` lines 274-303) currently has no concept of scope. It extracts facts from conversation text into categories (`fact:*`, `preference:*`, `instruction:*`).

To distinguish global vs workspace-scoped facts, the prompt needs:
1. **Workspace context injection:** When `deliverable_id` is present, prepend: "This conversation is about the deliverable: [title]. Distinguish between preferences specific to this deliverable and universal user preferences."
2. **Output schema extension:** Each extracted fact needs a `scope` field: `"global"` or `"deliverable"`. Global facts get `deliverable_id=NULL`, deliverable facts get the session's `deliverable_id`.

Per the Prompt Change Protocol in CLAUDE.md, this requires:
- Version bump in `memory.py` prompt section
- Entry in `api/prompts/CHANGELOG.md`
- Expected behavior documentation

---

## 4. Platform Content Scoping

The third opinion correctly flagged this: platform_content is user-level, not workspace-level. The same Slack channel could feed multiple deliverables/workspaces. This is a many-to-many relationship.

### 4.1 Current Architecture

platform_content rows are scoped by (user_id, platform, resource_id). A single Slack channel's messages are one set of rows. When a deliverable needs context, execution_strategies.py reads from platform_content filtered by the deliverable's sources JSONB:

- `deliverable.sources = [{type: 'integration_import', provider: 'slack', resource_id: 'C123', name: '#engineering'}]`
- Strategy queries: `SELECT * FROM platform_content WHERE user_id = ? AND platform = 'slack' AND resource_id = 'C123'`

### 4.2 No Schema Change Needed

**platform_content does NOT need a workspace/deliverable FK.**

The scoping already works through the sources JSONB on the deliverable. Multiple deliverables can reference the same resource_id — that's fine. The content rows don't need to know which workspace they belong to. The workspace (deliverable) knows which content it cares about via its sources field.

The retention system (retained, retained_ref) already handles the provenance question: when deliverable execution reads platform_content, it marks those rows as retained with retained_ref pointing to the deliverable_version_id.

This is precisely why your insight about 'platform sync is just automated git pull' is correct architecturally. The content is the filesystem. Workspaces are views over that filesystem — they select which files they care about. You don't reorganize the filesystem when you create a new project.

---

## 5. Complete Function Signature Changes

Every function that changes, with before/after signatures:

### 5.1 Schema Changes (3 columns, 1 RPC update, 1 constraint change, 0 new tables)

| Table | Column | Type |
|---|---|---|
| deliverables | mode | TEXT DEFAULT 'recurring' — 'recurring' \| 'goal' |
| chat_sessions | deliverable_id | UUID NULL FK deliverables(id) |
| user_context | deliverable_id | UUID NULL FK deliverables(id) |

**Constraint change on user_context:**

Drop existing `user_context_user_key_unique (user_id, key)` and replace with two partial unique indexes:

```sql
CREATE UNIQUE INDEX user_context_global_unique
  ON user_context (user_id, key) WHERE deliverable_id IS NULL;
CREATE UNIQUE INDEX user_context_scoped_unique
  ON user_context (user_id, key, deliverable_id) WHERE deliverable_id IS NOT NULL;
```

**RPC update:**

`get_or_create_chat_session` (migration 061) needs `p_deliverable_id UUID DEFAULT NULL` parameter. Session-reuse query scoped by deliverable_id when present.

### 5.2 Backend Function Changes

| Function | File | Change | Phase |
|---|---|---|---|
| `get_or_create_session()` | routes/chat.py | Add deliverable_id param, scope query | 1 |
| `get_or_create_chat_session` RPC | migrations/ | Add p_deliverable_id param, scope reuse query | 1 |
| `build_working_memory()` | services/working_memory.py | Add deliverable_id param, expand deliverable detail when scoped | 1 |
| `_get_user_context()` | services/working_memory.py | Add deliverable_id param, query global + scoped | 1 |
| `_get_recent_sessions()` | services/working_memory.py | Add deliverable_id param, filter sessions | 1 |
| POST /chat handler | routes/chat.py | Extract deliverable_id from surface_context, pass down | 1 |
| `_write_memory()` | services/memory.py | Add deliverable_id param, use correct partial index for upsert | 1 |
| `process_feedback()` | services/memory.py | Pass existing deliverable_id to `_write_memory()` | 1 |
| `generate_draft_inline()` | services/deliverable_execution.py | Accept scoped session summaries | 2 |
| `_build_headless_system_prompt()` | services/deliverable_execution.py | Inject session context section | 2 |
| `execute_deliverable_generation()` | services/deliverable_execution.py | Query scoped sessions before calling generate_draft_inline | 2 |
| Nightly memory cron | jobs/unified_scheduler.py | Fetch session.deliverable_id, pass to process_conversation | 4 |
| `process_conversation()` | services/memory.py | Accept deliverable_id, pass to _write_memory for scoped facts | 4 |
| Extraction prompt | services/memory.py | Add scope awareness, version bump per Prompt Change Protocol | 4 |

### 5.3 What Does NOT Change

- Execution strategies (execution_strategies.py) — context gathering is unchanged
- Platform sync (platform_worker.py, platform_sync_scheduler.py) — content pipeline untouched
- Unified scheduler deliverable scheduling (unified_scheduler.py) — deliverable scheduling/triggering logic unchanged (note: the nightly memory extraction path in the same file DOES change in Phase 4)
- Primitive registry (primitives/registry.py) — no new primitives needed
- TP system prompt (thinking_partner.py) — context comes through working memory, not prompt changes
- Deliverable pipeline (deliverable_pipeline.py) — type prompts unchanged
- Platform content service (platform_content.py) — no scoping FK needed

---

## 6. Frontend Impact Assessment

The third opinion correctly noted that frontend was unaddressed. Here's the assessment:

### 6.1 What Changes

- **Deliverable detail page (/deliverables/[id]):** Needs a mode-aware layout. Recurring deliverables show schedule + versions + review. Goal deliverables show progress + intermediate outputs + chat. This is the biggest frontend change.
- **TP chat panel:** When opened from a deliverable context, ChatRequest.surface_context.deliverableId is already sent (this exists today!). The backend change means TP will naturally have scoped context. Minimal frontend change.
- **Deliverable creation (/deliverables/new):** Needs a mode selector (recurring vs goal). Goal mode skips schedule configuration. Moderate change.
- **Dashboard:** May want to surface goal-mode deliverables differently (progress vs schedule). Could be phase 2.

### 6.2 What Doesn't Change

- Sidebar navigation — deliverables list still works, just shows both modes
- Context pages (/context/*) — platform content browsing unchanged
- Memory page (/memory) — could show global vs scoped, but not required for phase 1
- Settings, integrations, onboarding — completely unaffected

---

## 7. Implementation Phases

Following your CLAUDE.md discipline of singular implementation — no shims, no parallel paths.

### Phase 1: Schema + Backend Scoping (Backend only)

- Migration: add 3 columns (deliverables.mode, chat_sessions.deliverable_id, user_context.deliverable_id)
- Migration: replace `user_context_user_key_unique` constraint with two partial unique indexes (global + scoped)
- Migration: update `get_or_create_chat_session` RPC with `p_deliverable_id` parameter
- Update `get_or_create_session()` Python function with deliverable_id
- Update `build_working_memory()` with deliverable_id
- Update POST /chat to extract and pass deliverable_id from surface_context
- Update `_write_memory()` signature and upsert logic for scoped memories
- Update `process_feedback()` to pass deliverable_id to `_write_memory()`
- All changes are additive — null deliverable_id = current behavior

*Validation: TP sessions opened from deliverable review context now get scoped memory and session history. All existing global sessions work unchanged. Note: Phase 1 scoping only activates from the deliverable review page (existing surface_context path). Broader workspace entry points require Phase 3 frontend work.*

### Phase 2: Headless Bridge

- Update `generate_draft_inline()` to accept scoped session summaries
- Update `_build_headless_system_prompt()` to inject session context
- Query scoped sessions before headless execution

*Validation: Headless agent sees what user discussed in TP about this deliverable. Deliverable output quality improves for user-refined deliverables.*

### Phase 3: Goal Mode + Frontend

- Deliverable creation flow: add mode selector
- Deliverable detail page: mode-aware layout
- Goal deliverables: completion criteria, no schedule, progress view
- **Workspace chat entry point:** Add navigation affordance (workspace selector or deliverable-scoped chat button) so users can enter workspace-scoped TP context without being on the review page

*Validation: Users can create goal-oriented workspaces (board meeting prep, research project) alongside recurring deliverables. Users can start workspace-scoped chat from dashboard/sidebar, not just review pages.*

### Phase 4: Memory Extraction Scoping

- Update `process_conversation()` to accept and pass deliverable_id
- Update nightly cron (`unified_scheduler.py`) to fetch `chat_sessions.deliverable_id` and pass it through
- Update extraction prompt with workspace context injection and `scope` field in output schema
- Version bump extraction prompt per Prompt Change Protocol; update `api/prompts/CHANGELOG.md`
- Memory page optionally shows scoped vs global

*Validation: Deliverable-specific learnings stay scoped. Global preferences stay global. Prompt change is documented per CLAUDE.md protocol.*

---

## 8. Risk Assessment

| Risk | Mitigation | Severity |
|---|---|---|
| Semantic overloading of 'deliverable' | UI labels: 'Workspace' for goal mode, 'Deliverable' for recurring. Backend entity stays unified. | Low — presentation layer only |
| Token budget in scoped working memory | Deliverable detail expansion adds ~300 tokens. Within 2000 token budget. Monitor. | Low — configurable limits exist |
| Nightly cron complexity | Phase 4 only. Sessions already carry deliverable_id. Cron fetches one more column and passes it through. | Low — additive plumbing |
| Frontend mode-aware rendering | Phase 3. Can be deferred. Phase 1-2 work without frontend changes. | Medium — but deferrable |
| Migration path to Option B (workspaces table) | deliverable_id columns rename to workspace_id. Sources move from deliverable to workspace. Clean path. | Low — future concern |
| Unique constraint migration on user_context | Partial unique indexes replace single constraint. Must be done in correct order: create new indexes, drop old constraint. Existing data is all deliverable_id=NULL so global index covers it. Test migration on staging first. | Medium — data integrity risk if misordered |
| RPC version change for session creation | SQL function replacement. Must be backwards-compatible (new param has DEFAULT NULL). Deploy migration before Python code that passes the new param. | Low — standard migration ordering |
| Prompt Change Protocol compliance | Phase 4 extraction prompt change requires CHANGELOG.md update + version bump. Easy to forget. Add to PR checklist. | Low — process discipline |
| Phase 1 scoping limited to review page | Users can only enter workspace-scoped chat from deliverable review pages until Phase 3 adds broader entry points. May feel incomplete. Acceptable for initial validation. | Low — known limitation, not a bug |

---

## 9. Summary

The workspace concept is the right architectural evolution. Platform sync is 'automated git pull' into a unified filesystem (platform_content). Workspaces are scoped views over that filesystem. The deliverable entity, extended with mode and used as the scoping key for sessions and memory, becomes the workspace in all but name.

The total change is: 3 new columns, 1 RPC update, 1 constraint replacement (partial unique indexes), 14 backend function/prompt changes across 4 phases, 0 new tables, 0 new execution paths. Phase 1-2 are backend-only and fully backwards-compatible. The existing workflows (scheduled deliverables, global TP chat, headless execution, platform sync) continue unchanged when deliverable_id is null.

The hardest technical problem is the `user_context` unique constraint change — nullable FKs in Postgres unique constraints require partial indexes. The most impactful process requirement is the Prompt Change Protocol compliance for the Phase 4 extraction prompt update.

The biggest unlock: TP and headless execution finally see each other's work when operating on the same deliverable. This is the 'long-term work engine' — not a new system, but a scoping mechanism that connects existing systems.

---
---

## 10. V2 Reframe: Did We Actually Apply the Filesystem Insight?

### 10.1 The Problem with v1

Sections 1–9 claim the filesystem-as-context insight (ADR-038) as foundational: "platform sync is automated git pull," "workspaces are views over the filesystem," "you don't reorganize the filesystem when you create a new project." But the proposed implementation is FK columns and scoped SQL queries — `deliverable_id` on `chat_sessions`, `deliverable_id` on `user_context`, partial unique indexes, RPC parameter changes. That's relational-database thinking wearing a filesystem analogy as a hat.

Claude Code doesn't scope context by adding a `project_id` FK to a memories table. It reads CLAUDE.md. The context IS the file. Cowork doesn't scope context by querying a `workspace_id`-filtered table. The folder IS the workspace. The files are co-located.

v1 identified the right problem (TP and headless can't see each other's work) but proposed a solution from the wrong paradigm. The filesystem insight says: context should be a document that lives WITH the deliverable, not FK-scoped queries across normalized tables.

### 10.2 Option C: Context Document per Deliverable

What if each deliverable had a **context document** — a structured field that accumulates context the way CLAUDE.md does for a project?

The deliverables table already has fields that partially serve this role:

- `description` (TEXT) — user-provided notes, currently just a label
- `recipient_context` (TEXT) — injected into the generation prompt as audience context
- `type_config` (JSONB) — type-specific settings
- `template_structure` (TEXT) — custom output structure

These are static configuration. What's missing is **accumulated context** — the living document that grows as the user works with this deliverable. Think of it as: `description` is the README, but there's no CLAUDE.md.

**The new field:** `work_context` (JSONB or TEXT) on `deliverables`.

This is the deliverable's CLAUDE.md. It accumulates:

- **Scoped preferences:** "For this board report, use formal tone and bullet points" — extracted from TP conversations about this deliverable
- **Session summaries:** Compressed conversation history, appended after each scoped session (same compaction pattern as ADR-067, but writing to the deliverable instead of to a session row)
- **User-stated instructions:** Direct "remember this for next time" instructions from TP conversations in this context
- **Feedback patterns:** "User consistently expands the executive summary section" — from `process_feedback()`, which already has the deliverable_id
- **Goal state (for goal-mode):** What "done" looks like, progress markers, intermediate findings

### 10.3 How This Changes the Execution Paths

**TP chat (working memory injection):**

v1 proposed: `build_working_memory(user_id, client, deliverable_id=None)` → scoped SQL queries across `user_context` and `chat_sessions` tables.

v2 (Option C): `build_working_memory(user_id, client, deliverable=None)` → when deliverable is provided, include `deliverable.work_context` in the working memory dict. One field read, not multiple scoped queries. The working memory formatter already has a `deliverables` section that shows one-liners — for the active deliverable, it expands to include the full context document.

**Headless execution (TP↔headless bridge):**

v1 proposed: Query scoped session summaries from `chat_sessions WHERE deliverable_id = ?`, inject as text into headless prompt.

v2 (Option C): The headless prompt builder already reads the deliverable dict. `work_context` is right there. `_build_headless_system_prompt()` includes it. No new queries. The bridge isn't a query — it's a field on the entity you're already loading.

**Memory writes:**

v1 proposed: `deliverable_id` FK on `user_context`, partial unique indexes, scoped upserts, extraction prompt changes to output a `scope` field.

v2 (Option C): Two write targets. Global facts still go to `user_context` (unchanged). Deliverable-specific facts write to `deliverable.work_context` — either via a structured JSONB append or via a dedicated update endpoint. `process_feedback()` already has the deliverable — it writes feedback patterns directly to the deliverable's context document instead of to `user_context` rows with a FK.

**Session scoping:**

v1 proposed: `deliverable_id` FK on `chat_sessions`, RPC changes, concurrent session semantics.

v2 (Option C): This one is less clear-cut. Sessions still need SOME way to know which deliverable they relate to, because nightly summary compaction needs to know where to write the compressed summary. Two options:

- **Keep the FK** (hybrid): `chat_sessions.deliverable_id` stays, but purely as a routing key for "which `work_context` does this session's summary get appended to." No scoped session queries at read time — the context document is the read path.
- **No FK, surface_context only**: The deliverable association lives only in `surface_context` metadata on individual messages, and the nightly cron resolves it from there. Simpler schema, slightly more complex cron logic.

The FK as a routing key (hybrid) is probably the pragmatic choice. It's one column, no RPC changes needed (session creation doesn't need to scope its reuse query by deliverable), no partial unique indexes. The FK exists purely so the summary writer knows where to append.

### 10.4 What This Eliminates from v1

| v1 Requirement | Still needed in v2? |
|---|---|
| `deliverable_id` FK on `user_context` | **No.** Scoped preferences live in `work_context` on the deliverable itself. |
| Partial unique indexes on `user_context` | **No.** No FK, no constraint change. |
| `_write_memory()` signature change for scoped upserts | **No.** Global memories still upsert as before. Scoped context writes to the deliverable. |
| `_get_user_context()` scoped query (global + deliverable) | **No.** Read global from `user_context` (unchanged). Read scoped from `deliverable.work_context` (one field). |
| `_get_recent_sessions()` scoped query | **No.** Session history is IN the context document (compacted summaries), not queried at runtime. |
| RPC parameter change for session creation | **No.** Session reuse doesn't need to scope by deliverable. The 4h boundary is still user-level. |
| Extraction prompt `scope` field | **Simpler.** The nightly cron knows the session's deliverable_id (if the FK routing key exists). It runs extraction as before, but routes deliverable-specific outputs to `work_context` instead of to `user_context` rows. |

What **stays**:

| Requirement | Still needed? |
|---|---|
| `deliverables.mode` column | **Yes.** Recurring vs goal is still a real behavioral distinction. |
| `chat_sessions.deliverable_id` FK | **Yes, but simpler role.** Routing key for summary compaction, not a read-time query scope. No RPC change. |
| `build_working_memory()` change | **Yes, but simpler.** Accept deliverable dict, include `work_context` in output. No scoped DB queries. |
| Headless prompt injection | **Yes, but simpler.** Read `work_context` from the deliverable you already have. No session queries. |
| Nightly cron change | **Yes, but different.** Route extracted facts to `work_context` append instead of scoped `user_context` rows. |

### 10.5 The CLAUDE.md Mapping (Updated)

ADR-038 established the mapping. v2 completes it:

```
Claude Code                    YARNNN (v1, incomplete)         YARNNN (v2, filesystem-native)
──────────                    ──────────────────────          ──────────────────────────────
Source files                  platform_content                platform_content (unchanged)
Build output                  deliverable_versions            deliverable_versions (unchanged)
CLAUDE.md                     context injection (global)      deliverable.work_context (per-deliverable)
                              (no per-project equivalent)     + global context injection (unchanged)
Shell history                 session_messages                session_messages (unchanged)
Session compaction            chat_sessions.summary           work_context accumulation
                              (per-session, not per-project)  (per-deliverable, like CLAUDE.md)
Skills / .claude/ files       (none)                          work_context instructions section
                                                              (deliverable-specific agent instructions)
CI jobs / builds              work_tickets                    work_tickets (unchanged)
```

The key gap in v1: there was no per-project CLAUDE.md equivalent. Global context injection (user profile, preferences, deliverable one-liners) maps to a global CLAUDE.md. But Claude Code projects each have their own CLAUDE.md. v2 gives each deliverable its own context document.

### 10.6 The Cowork UI as Target Experience

The Cowork screenshot shows a workspace layout with:

- **Progress/tasks** — visible state of what's done, what's next
- **Files/artifacts** — the outputs and working documents
- **Context panel** — what the agent knows about this workspace
- **Chat** — the conversation, scoped to this workspace
- **Skills** — workspace-specific instructions for how the agent should behave

This maps to a deliverable detail page redesign:

| Cowork Element | YARNNN Deliverable Equivalent |
|---|---|
| Progress/tasks | Goal-mode: completion criteria + progress. Recurring: schedule + last run status. |
| Files/artifacts | `deliverable_versions` — the generated outputs, review history |
| Context panel | `work_context` — the accumulated context document, viewable and editable |
| Chat | Scoped TP chat panel (surface_context.deliverableId wired through) |
| Skills | `work_context` instructions section — deliverable-specific agent instructions |

The current `/deliverables/[id]` page is version-centric: a list of outputs with review actions. The Cowork-informed page is workspace-centric: chat + context + artifacts in one view. The data model should serve THAT experience.

This also implies an upgrade path for the TP chat on the dashboard page. Currently the dashboard is a global TP chat. With deliverable context documents, the dashboard could show the user's active workspaces with the ability to enter any one — each with its own context, chat history, and artifacts. The global TP chat becomes "unscoped" — no `work_context` loaded, just the global user profile. Both modes coexist naturally.

### 10.7 work_context Schema Sketch

Two realistic options for the field:

**Option 1: Structured JSONB**

```json
{
  "instructions": [
    "Use formal tone for this board report",
    "Always include an executive summary"
  ],
  "preferences": {
    "format": "detailed with bullet points",
    "length": "2-3 pages"
  },
  "session_summaries": [
    {"date": "2026-03-01", "summary": "Discussed shifting from quarterly to monthly cadence..."},
    {"date": "2026-02-25", "summary": "Reviewed draft, user wants more data citations..."}
  ],
  "feedback_patterns": [
    "User consistently expands the executive summary",
    "User removes the 'next steps' section"
  ],
  "goal": {
    "description": "Prepare board meeting materials for March 15",
    "status": "in_progress",
    "milestones": ["Research complete", "Draft v1", "Final review"]
  }
}
```

Pros: queryable (JSONB operators), structured appends, sections are clear. Cons: append operations need read-modify-write or JSONB path operations.

**Option 2: Markdown TEXT (the actual CLAUDE.md pattern)**

```markdown
## Instructions
- Use formal tone for this board report
- Always include an executive summary

## Preferences
- Format: detailed with bullet points
- Length: 2-3 pages

## Recent Context
### 2026-03-01
Discussed shifting from quarterly to monthly cadence. User wants trend analysis.

### 2026-02-25
Reviewed draft. User wants more data citations. Removed 'next steps' section.

## Feedback Patterns
- User consistently expands the executive summary
- User removes the 'next steps' section

## Goal
Prepare board meeting materials for March 15.
- [x] Research complete
- [ ] Draft v1
- [ ] Final review
```

Pros: directly injectible into prompts (it's already markdown), human-readable/editable, aligns with the actual CLAUDE.md pattern. Cons: not queryable, appends are string concatenation, harder to do structured updates.

**Recommendation:** JSONB for storage, markdown rendering for prompt injection and UI display. The `format_for_prompt()` function in `working_memory.py` already does this pattern — it reads structured data and formats it as markdown for the system prompt. Same approach: store as JSONB, render as markdown when injecting into prompts or displaying in the UI.

### 10.8 Trade-offs: v2 vs v1

| Dimension | v1 (FK scoping) | v2 (context document) |
|---|---|---|
| Schema complexity | 3 columns + partial indexes + RPC change | 1-2 columns (mode, work_context) |
| Read path for scoped context | Multiple scoped SQL queries at request time | One field read from the deliverable you already have |
| Write path for scoped context | Scoped upserts to user_context with partial index targeting | Append to work_context JSONB (read-modify-write or JSONB path) |
| Cross-deliverable queries | Easy (query user_context with deliverable_id filter) | Hard (work_context is per-deliverable; cross-workspace patterns need extraction to global user_context) |
| Token budget control | Configurable — query returns N rows | Document grows over time — needs size management / compaction |
| Headless bridge | New query + prompt section | Already loaded — deliverable dict includes work_context |
| Alignment with filesystem insight | Claims it, implements SQL | Actually implements it |
| Migration complexity | Partial indexes, RPC update, constraint drop+recreate | ALTER TABLE ADD COLUMN, zero risk |
| User editability | Users edit user_context rows via /memory page | Users edit work_context via deliverable detail page (more natural: "edit this deliverable's context") |

### 10.9 Open Questions for v2

1. **Size management:** CLAUDE.md files don't grow forever in practice — projects have a natural scope. But a long-running deliverable's `work_context` could accumulate indefinitely. Compaction strategy needed: summarize old session summaries, prune stale feedback patterns, cap instruction count. This parallels session compaction (ADR-067) but for the context document.

2. **Global vs scoped preference resolution:** If `work_context` says "use formal tone" but global `user_context` says "prefers casual," which wins? Proposed: scoped overrides global (same as CSS specificity). The prompt can say: "The user generally prefers casual tone, but for THIS deliverable has specified formal tone." Working memory injection already merges sections — it can merge global + scoped with a specificity note.

3. **Session FK role clarification:** If `chat_sessions.deliverable_id` is only a routing key for summary compaction (not a read-time query scope), does the session creation RPC need to change? Probably not — the FK gets set when creating the session, but the RPC's reuse logic doesn't scope by it. This eliminates the RPC migration entirely.

4. **Nightly cron write path:** The nightly cron extracts facts from conversations. For scoped sessions, some facts should go to `work_context` (deliverable-specific) and some to `user_context` (global). The extraction prompt still needs the `scope` distinction — but the write target changes from "scoped user_context rows" to "work_context append." Net complexity is similar, but the storage model is cleaner.

5. **Frontend: context document editor.** The Cowork-style deliverable page needs a way to view and edit `work_context`. This could be a markdown editor panel (if TEXT) or a structured form (if JSONB). The markdown approach is more aligned — the user sees and edits what the agent sees. JSONB with markdown rendering is the hybrid: structured storage, markdown display, with a raw/structured toggle for power users.

### 10.10 v2 Recommendation

**Option C (context document per deliverable) is fundamentally better than Option A (FK scoping).** It's not just cheaper to implement — it's the right abstraction. It completes the filesystem mapping that ADR-038 started. It eliminates the most complex part of v1 (partial unique indexes, scoped upserts, RPC changes) and replaces it with the simplest possible storage change (one JSONB column on a table you already load).

The `mode` column on deliverables still makes sense (recurring vs goal is a real behavioral distinction). The `chat_sessions.deliverable_id` FK still makes sense as a lightweight routing key. But the scoped context — preferences, session history, feedback patterns, instructions — lives in the context document, not in FK-scoped query results across normalized tables.

The implementation phases would change:

**Phase 1:** Add `work_context` (JSONB) and `mode` (TEXT) to deliverables. Wire `work_context` into `build_working_memory()` for prompt injection when deliverable is active. Wire into `_build_headless_system_prompt()` for headless execution. Two columns, two function changes.

**Phase 2:** Wire write paths. `process_feedback()` appends feedback patterns to `work_context`. Add `deliverable_id` FK to `chat_sessions` (routing key). Nightly cron appends session summaries to `work_context` for scoped sessions.

**Phase 3:** Frontend — deliverable detail page redesign (Cowork-inspired: chat + context + artifacts). Context document viewer/editor. Goal mode UI. Workspace chat entry points.

**Phase 4:** Memory extraction scoping — nightly cron routes deliverable-specific facts to `work_context`, global facts to `user_context`. Compaction strategy for long-running deliverables.

This is fewer migrations, fewer function signature changes, fewer constraint gymnastics — and it actually implements the pattern we said we were following.

---
---

## 11. V3 Exploration: What If Everything Is a File?

### 11.1 The Push Beyond v2

v2 proposed `work_context` as a single JSONB field on deliverables — the per-deliverable CLAUDE.md. This is better than v1's FK scoping, but it still flattens the workspace into one blob. Kevin's challenge: what if context is a file, progress/todos is a file, instructions is a file, feedback patterns is a file? Each feeds a different UI component. The deliverable detail page isn't a page that queries a JSONB blob — it's a page that renders a collection of files.

This is how Cowork actually works. The folder IS the workspace. Each file has a purpose. The UI renders them into panels. And critically — both the user AND the agent can read and write these files. The progress file gets updated by TP (user asks "mark research as done") and by headless execution (agent completes a step). The context file gets updated by TP (user says "remember to use formal tone") and by the feedback loop (agent observes edit patterns).

If you take this seriously, a workspace isn't a row with a JSONB field. It's a container with typed files.

### 11.2 The Files-as-Primitive Model

Each deliverable (or workspace) has a collection of **workspace files** — typed documents that serve specific roles:

```
workspace: "Board Meeting Prep" (deliverable row)
│
├── context          ← instructions, preferences, scoped memory (the CLAUDE.md)
├── progress         ← todos, milestones, completion state (feeds Progress widget)
├── history          ← compacted session summaries (feeds Timeline)
├── feedback         ← observed edit patterns (feeds agent learning)
└── [artifacts]      ← deliverable_versions (already exists, feeds Versions list)
```

Each file has:
- A **type** (context, progress, history, feedback — or extensible)
- **Content** (JSONB or TEXT, depending on type)
- A **deliverable_id** (the container)
- Timestamps for versioning/compaction

The chat panel doesn't need a file — it's `session_messages` scoped by the session's `deliverable_id` routing key. The artifacts are `deliverable_versions` — already a separate table. What's NEW is the workspace files that hold accumulated working state.

### 11.3 Where This Could Live in the Schema

Three options, ranging from simple to structural:

**Option D1: Multiple JSONB fields on deliverables (v2 extended)**

```sql
ALTER TABLE deliverables ADD COLUMN work_context JSONB DEFAULT '{}';
ALTER TABLE deliverables ADD COLUMN work_progress JSONB DEFAULT '{}';
ALTER TABLE deliverables ADD COLUMN work_history JSONB DEFAULT '[]';
ALTER TABLE deliverables ADD COLUMN work_feedback JSONB DEFAULT '[]';
```

Pros: no new tables, each "file" is a field. Cons: the deliverables row gets wide. Each field is a different shape. Hard to add new file types without another migration. Doesn't feel like files — feels like more columns.

**Option D2: Workspace files table (typed rows)**

```sql
CREATE TABLE workspace_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deliverable_id UUID NOT NULL REFERENCES deliverables(id),
    file_type TEXT NOT NULL,  -- 'context', 'progress', 'history', 'feedback'
    content JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(deliverable_id, file_type)
);
```

Pros: extensible (add new file types without migration), clean separation, each file is independently queryable and updatable, RLS straightforward (join through deliverable → user_id). Cons: 1 new table, new RLS policy, frontend needs to load files for a deliverable.

**Option D3: Workspace entity with files (full hierarchy)**

```sql
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    title TEXT NOT NULL,
    description TEXT,
    mode TEXT DEFAULT 'ongoing',  -- 'ongoing', 'goal', 'recurring'
    status TEXT DEFAULT 'active',
    sources JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE workspace_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id),
    file_type TEXT NOT NULL,
    content JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(workspace_id, file_type)
);

ALTER TABLE deliverables ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE chat_sessions ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
```

Pros: clean domain model — workspace is the container, files are the contents, deliverables are outputs. `sources` moves to workspace (where it conceptually belongs). The "board meeting prep" workspace can have zero deliverables initially (just research + chat) and spawn one later. Cons: full migration — create workspaces from existing deliverables, move sources, add FKs, new routes, new frontend navigation.

### 11.4 How Typed Files Feed the UI

The Cowork-style deliverable page becomes a file renderer:

| File Type | UI Component | Read by | Written by |
|---|---|---|---|
| `context` | Context panel (editable markdown/structured view) | TP working memory, headless prompt builder | User (direct edit), TP ("remember this"), nightly cron (extracted facts) |
| `progress` | Progress widget (todo list, milestones, checkboxes) | TP (can reference current state), headless (checks completion) | TP ("mark research done"), headless (updates after generation), user (direct edit) |
| `history` | Timeline (collapsible session summaries) | TP working memory (recent summaries), headless (conversation context) | Nightly cron (session summary compaction) |
| `feedback` | Feedback patterns panel (what the agent has learned from edits) | Headless prompt builder (style calibration) | `process_feedback()` (edit pattern analysis) |

The key insight: progress is a file that BOTH TP and headless execution read and write. When the user says "mark the research as complete," TP updates the progress file. When headless execution finishes generating a draft, it updates the progress file. The UI reflects the current state because it reads the file. This is exactly how Cowork's Progress panel works — it's state that persists across sessions and execution modes.

### 11.5 The Workspace vs Deliverable Hierarchy Question

This is where v3 forces a real structural decision that v2 sidestepped.

**If everything is a file in a deliverable** (Option D2), the deliverable table becomes overloaded. It's simultaneously:
- A workspace container (has files, sessions, context)
- A scheduled output config (has schedule, type, destination)
- A goal tracker (has progress, milestones)

The `mode` column distinguishes these, but semantically it's three different things wearing one table's clothing. The frontend route `/deliverables/[id]` renders three very different pages depending on mode.

**If you introduce workspaces** (Option D3), the domain model is cleaner:
- Workspace = persistent context container (files, sessions, accumulated context)
- Deliverable = output configuration within a workspace (schedule, type, destination, versions)
- A workspace can exist without deliverables (pure research/brainstorming)
- A workspace can have multiple deliverables (board prep workspace → board report + executive summary)

This maps directly to ESSENCE.md's domain model, which already has a `workspace` entity. It also maps to how users think about work — "I'm working on board meeting prep" (workspace), not "I'm working on deliverable #47" (DB row).

### 11.6 The Cost of Getting This Right vs Good Enough

| Approach | Schema cost | Conceptual clarity | Extensibility | Migration risk |
|---|---|---|---|---|
| v2: `work_context` JSONB on deliverables | 1-2 columns | Medium — one blob, not files | Low — new sections = prompt changes | Near zero |
| D2: workspace_files table, deliverable as container | 1 table | High — typed files, clear roles | High — new file types = INSERT, no migration | Low — new table, no existing data changes |
| D3: workspaces + workspace_files | 2 tables + FKs | Highest — clean hierarchy | Highest — proper domain model | Medium — data migration, frontend rework |

The pragmatic spectrum:
- **v2 gets you 80% of the value at 10% of the cost.** One JSONB field, two function changes, and the TP↔headless bridge works. But it's flat — adding new file types means growing the blob, and the "deliverable = workspace" semantic overload persists.
- **D2 gets you 95% of the value at 30% of the cost.** Typed files are extensible and clean. Deliverable is still the container (semantic overload stays), but the file abstraction is right. Frontend can render each file type as a panel.
- **D3 gets you 100% but at 60% of the cost.** Clean domain model. But it's a v1-era concern: full entity rework, migration scripts, new routes, frontend navigation changes.

### 11.7 A Possible Incremental Path

What if the path is: v2 now → D2 next → D3 if needed?

**Step 1 (v2):** Add `work_context` JSONB to deliverables. Wire reads and writes. Validate the concept — does scoped context actually improve TP↔headless quality? Does the Cowork-style page feel right? This is a ~2-day implementation.

**Step 2 (D2, if v2 validates):** Factor `work_context` into typed `workspace_files` rows. The JSONB sections become individual files. Frontend refactors from "read one blob" to "read typed files." The data migration is trivial: split JSONB sections into rows. This is a ~1-week refactor.

**Step 3 (D3, if D2 reveals the need):** Promote workspace to its own entity. Move `sources` from deliverables to workspaces. Add `workspace_id` to deliverables and sessions. Frontend gets `/workspaces/[id]` routes. This is a ~2-week project.

Each step validates the concept before committing to the next level of structural investment. And each step has a clean migration path from the previous one — no throwaway work.

### 11.8 The TP Chat Upgrade Question

Kevin also asked: can the Cowork-style layout benchmark an upgrade to the TP chat on the dashboard?

Currently the dashboard is a global TP chat — unscoped, no workspace context. With workspace files:

- **Dashboard as workspace selector:** The dashboard shows active workspaces (deliverables with recent activity). Clicking one enters the workspace view (chat + context + progress + artifacts). The "new chat" button starts an unscoped global session.
- **The global chat IS the unscoped workspace:** No `work_context` loaded, just the global `user_context` profile. This is the "home directory" — no project open.
- **Workspace chat IS the scoped chat:** `work_context` (or workspace files) loaded into working memory. Session tagged with deliverable_id. Everything the user says is in the context of this workspace.

The data accommodation question: does this require new data beyond what we've discussed? The workspace files (context, progress, history, feedback) plus the existing deliverable data (title, sources, schedule, versions) plus the existing session data (messages, summaries) should be sufficient. The dashboard workspace selector is a query: `SELECT id, title, mode, updated_at FROM deliverables WHERE user_id = ? AND status = 'active' ORDER BY updated_at DESC`. No new data needed — just a different page layout.

The frontend investment is the big variable. Rendering a Cowork-style workspace view with chat + context + progress + artifacts is a significant component build. But it's a frontend concern that doesn't block the backend data model decision.

### 11.9 Open Questions for Claude Code Assessment

These are the questions where a second opinion on the actual codebase would be most valuable:

1. **JSONB append patterns:** The `work_context` write path (and `workspace_files` content updates) require JSONB append operations. What's the current pattern in the codebase for JSONB mutations? Is it read-modify-write via Python, or do we use Postgres JSONB operators (`jsonb_set`, `||`, etc.)? What's the concurrency story — can two processes (TP session + nightly cron) safely append to the same JSONB field?

2. **Working memory token budget:** The current 2000-token budget for working memory is tight. Adding a full `work_context` document could blow it. How does `format_for_prompt()` currently handle truncation? Is there a prioritization mechanism, or is it all-or-nothing? The context document needs a token budget sub-allocation.

3. **Deliverable loading path:** How many places in the codebase load a deliverable dict? If `work_context` is a JSONB field, it comes along for free on every load. If it's `workspace_files`, each load needs a join or secondary query. What's the performance impact on the hot paths (headless execution, TP working memory build)?

4. **Frontend component architecture:** The current `/deliverables/[id]` page — how modular is it? Can it be refactored into a panel-based layout (chat + context + artifacts), or is it monolithic? What component library patterns exist for split-pane or panel layouts?

5. **`process_feedback()` write path:** This function already has `deliverable_id` and writes to `user_context`. How cleanly can it be redirected to write to `work_context` (or a workspace file) instead? Are there downstream consumers of the `user_context` rows it creates that would break?

6. **Session summary completeness:** `generate_session_summary()` runs nightly but `sessions.md` notes the writer may not be fully wired. What's the actual state? If session summaries aren't being generated, the `work_context` history accumulation (and the headless bridge) depends on fixing that first.

7. **ESSENCE.md domain model alignment:** ESSENCE.md defines a 7-entity domain model that includes `workspace` as a first-class entity. How far has implementation drifted from ESSENCE.md? Is the domain model still the target, or has it been superseded by what got built?

---

## 12. OpenClaw Architecture Deep-Dive (v4)

Before committing to an architecture, we analyzed OpenClaw's gateway framework — a system that has shipped and scaled the same "persistent AI agent with workspace context" problem YARNNN is solving.

### 12.1 What OpenClaw Actually Built

From the screenshots and docs, OpenClaw's architecture has five layers:

**Gateway inputs (Screenshot 1 — the 5 input types):**

| Input | What It Does | YARNNN Equivalent |
|-------|-------------|-------------------|
| **Messages** | User chat from any channel (WhatsApp, Slack, etc.) | POST /chat (TP messages) |
| **Heartbeats** | Periodic check-in tasks (HEARTBEAT.md defines schedule + prompt) | Unified scheduler (deliverable generation) |
| **Crons** | Time-based automated jobs | Platform sync scheduler, unified scheduler |
| **Hooks** | Event-triggered actions (file change, webhook receipt, etc.) | `process_feedback()`, platform sync on-demand |
| **Webhooks** | Inbound HTTP triggers from external systems | MCP server inbound, OAuth callbacks |

**Architecture components (Screenshot 2):**

| Component | OpenClaw | YARNNN Equivalent |
|-----------|----------|-------------------|
| **Channel Adapters** | Standardize messages from 24+ platforms into unified format | Platform sync worker (`_sync_slack`, `_sync_gmail`, etc.) |
| **Gateway** | Routes each request to correct session queue, manages concurrency isolation | POST /chat handler → `get_or_create_session()` |
| **Lane Queue** | Executes tasks serially per session to prevent race conditions and state drift | Not implemented — YARNNN has no concurrency isolation per session |
| **Agent Runner** | Assembles system prompt + history, calls LLM, invokes tools, feeds results back | `thinking_partner.py` agent loop |
| **Execution Layer** | Runs shell, file, and browser operations in sandboxed environment | Primitives (Execute, Write, Edit, etc.) |

### 12.2 The Workspace Directory Pattern

The critical learning is OpenClaw's workspace structure. Every agent has a workspace directory:

```
~/.openclaw/workspace/
├── AGENTS.md        # Operating manual (what to do on startup, safety rules)
├── SOUL.md          # Core personality, values, voice
├── IDENTITY.md      # External-facing name, role, emoji
├── USER.md          # About the human (name, timezone, preferences)
├── MEMORY.md        # Long-term curated facts and decisions
├── TOOLS.md         # Local tool configuration, API quirks
├── HEARTBEAT.md     # Periodic task definitions
├── memory/          # Daily logs (YYYY-MM-DD.md)
├── skills/          # Custom skill definitions
└── projects/        # Project-specific files
```

This is literally the filesystem-as-context pattern — but OpenClaw didn't stop at the analogy. They built it. Every file is a markdown file. Every file is readable and writable by both the agent and the user. The system reads these files at session start and injects them as bootstrap context. The LLM has no "memory" beyond what's written to disk.

### 12.3 Two Memory Layers (Not One)

OpenClaw splits memory into:

1. **MEMORY.md** — Long-term curated facts. Manually pruned. Loaded only in private/main sessions (never in group contexts for security). Think: preferences, decisions, relationship context.

2. **memory/YYYY-MM-DD.md** — Daily append-only logs. Agent writes notes at session end. System reads today + yesterday on startup. Over time, important items get promoted to MEMORY.md.

This is a compaction pattern: daily logs are the "hot" layer, MEMORY.md is the "cold" curated layer. The promotion from daily→curated can be manual or agent-assisted.

**YARNNN parallel:** This maps to `user_context` (curated, long-term) + `chat_sessions.summary` (per-session logs). But YARNNN's session summaries are flat — they don't accumulate into a per-workspace narrative the way OpenClaw's daily logs do. The `work_context` concept from v2 is closer: it would accumulate session-over-session within a deliverable's scope.

### 12.4 Context Assembly = File Reads

On every turn, OpenClaw runs `resolveBootstrapContextForRun()` which:

1. Reads workspace files (AGENTS.md, SOUL.md, MEMORY.md, etc.)
2. Caps total size via `bootstrapMaxChars` (default 20K per file) and `bootstrapTotalMaxChars` (default 150K total)
3. Injects them into the system prompt
4. Adds conversation history
5. Sends to LLM

This is exactly ADR-038's model. No database queries for "memory retrieval." No embedding search for "relevant context." Just: read files, cap tokens, inject. The simplicity is the feature.

**YARNNN parallel:** `build_working_memory()` does the same thing but reads from database tables instead of files. The data model is different but the pattern is identical. The question isn't whether to adopt OpenClaw's file-on-disk approach (YARNNN is a web platform, not a local CLI), but whether the *conceptual model* of "workspace = directory of typed files" should drive how we structure the data.

### 12.5 Lane Queue — The Missing Piece

The **Lane Queue** in Screenshot 2 is notable because YARNNN doesn't have an equivalent. OpenClaw executes tasks serially within each session lane to prevent race conditions and state drift. In YARNNN, if a user is chatting with TP about a deliverable while the headless scheduler is generating a new version of that same deliverable, there's no serialization — both could write to `work_context` (or workspace files) simultaneously.

This matters less with a JSONB field (single write replaces whole blob — last write wins) but matters more with typed workspace files (concurrent writes to different files are fine, but concurrent writes to the same file cause conflicts).

**Implication for our options:** Option D1 (JSONB fields on deliverables) has simpler concurrency than D2/D3 (workspace_files table). With D2/D3, we'd need either pessimistic locking per workspace or a conflict resolution strategy (last-write-wins with timestamps, or append-only with compaction).

### 12.6 Six Concrete Learnings for YARNNN

**Learning 1: Typed files work.** OpenClaw's SOUL.md / MEMORY.md / USER.md / AGENTS.md pattern validates our v3 hypothesis. Different types of context live in different files, each loaded contextually. This isn't theoretical — it's shipped and working at scale. Our Options D1/D2/D3 are on the right track.

**Learning 2: Two memory layers are better than one.** Daily logs (hot, append-only, short-lived) + curated memory (cold, pruned, persistent) is a better model than a single `user_context` table. YARNNN's nightly extraction cron already approximates this: session conversations (hot) get extracted into `user_context` entries (cold). But scoping this per-workspace (daily workspace logs → curated workspace memory) would be the natural extension.

**Learning 3: Bootstrap context injection is correct.** OpenClaw validates the ADR-038 model — read files at session start, cap tokens, inject into prompt. No runtime embedding search needed at current scale. YARNNN's `build_working_memory()` is architecturally the same. The v2/v3 extension (load `work_context` / workspace files per deliverable) fits this model perfectly.

**Learning 4: Concurrency isolation matters.** The Lane Queue exists because concurrent writes to workspace state cause bugs. If YARNNN moves to workspace files (D2/D3), concurrent TP chat + headless execution on the same workspace needs a serialization strategy. This is a real engineering cost that v1 (FK columns) and v2 (JSONB) largely avoid.

**Learning 5: The gateway separates routing from execution.** OpenClaw's Channel Adapters → Gateway → Lane Queue → Agent Runner pipeline cleanly separates "where did this message come from" from "what agent processes it." YARNNN conflates these: the POST /chat handler does routing, session management, AND agent invocation. This isn't a problem today but would become one if YARNNN adds more input channels (MCP, webhooks, scheduled prompts). Something to note for future architecture, not immediate action.

**Learning 6: Heartbeats are a deliverable primitive.** OpenClaw's HEARTBEAT.md (periodic check-in tasks with schedule + prompt) is structurally identical to a YARNNN recurring deliverable. The difference: OpenClaw treats heartbeats as workspace-level configuration (a file in the workspace), while YARNNN treats deliverables as the top-level entity. This validates the "workspace contains deliverables" hierarchy in Option D3, where a workspace could have multiple heartbeat-like recurring outputs plus ad-hoc goal work.

### 12.7 Updated Architecture Mapping (Three Systems)

Extending the ADR-038 mapping table with OpenClaw:

```
Claude Code              OpenClaw                       YARNNN
──────────              ────────                       ──────
Source files            Workspace dir + daily logs     Platform content + documents
Build output            Agent responses + artifacts    Deliverables + versions
CLAUDE.md               AGENTS.md + SOUL.md            Context injection (user profile + summaries)
                        USER.md                        user_context (preferences, facts)
                        MEMORY.md                      user_context (curated long-term)
                        memory/YYYY-MM-DD.md           chat_sessions.summary (per-session)
                        HEARTBEAT.md                   Deliverable schedule + type_config
                        TOOLS.md                       Primitives registry
Shell history           Session transcripts            Session messages
CI jobs                 Crons + Heartbeats             Unified scheduler + platform sync
Grep/Glob/Read          File reads                     List/Search/Read primitives
Write/Edit              File writes                    Write/Edit primitives
Bash (execute)          Execution Layer                Execute (sync/generate/publish)
—                       Gateway (routing)              POST /chat handler
—                       Lane Queue (concurrency)       Not implemented
—                       Channel Adapters               Platform sync workers
—                       Hooks/Webhooks                 MCP server, OAuth callbacks
```

### 12.8 What This Means for the Decision

The OpenClaw analysis strengthens the v3 direction but adds a nuance: **start with the simpler data model (v2 JSONB), not the full workspace-files model (D2/D3), because concurrency isolation is a real engineering cost that only matters when you have the concurrency.**

YARNNN today has exactly one user. TP chat and headless execution don't yet run concurrently on the same deliverable in practice (headless runs on a schedule, TP runs when Kevin is chatting — these rarely overlap). The Lane Queue problem is real but premature.

The updated incremental path:

1. **v2 now:** `work_context` JSONB on deliverables. Validates scoped context. Zero concurrency risk (single JSONB field, last-write-wins).
2. **D2 when multi-user:** Factor into typed workspace files when concurrent access becomes real. Add lightweight locking (advisory locks or optimistic concurrency via updated_at).
3. **D3 when workspace ≠ deliverable:** Promote workspace when users need containers that hold multiple deliverables. The OpenClaw model (workspace dir → multiple heartbeats + projects) validates this will eventually be needed.

### 12.9 Open Questions Updated

Adding to the Section 11.9 questions for Claude Code:

8. **Concurrency on deliverable writes:** Today, can TP chat and headless execution write to the same deliverable simultaneously? What's the actual concurrency profile? If they're effectively serialized by the schedule cadence, v2 (JSONB) is safe. If they could overlap (e.g., user chats about a deliverable while a scheduled generation is in-flight), we need to think about locking earlier.

9. **Session summary accumulation:** OpenClaw's daily logs accumulate into a narrative. YARNNN's session summaries are isolated per-session. Is there a natural place to accumulate a per-deliverable narrative from session summaries? Could `work_context.history` be that accumulation layer?

10. **Bootstrap context size budget:** OpenClaw caps at 20K per file, 150K total. YARNNN's working memory budget is ~2000 tokens. If we add `work_context` injection, what's the realistic token budget for workspace context? Is 2000 total still defensible, or does workspace scoping require expanding the budget?

---
---

## 13. V5 Consolidation: Two Separated Tracks

### 13.1 The Ghost Entity Discovery

The `projects` table exists in the live database — designed in migration 001, indexed, RLS'd, referenced by FKs on `chat_sessions`, `deliverables`, `work_tickets`, `agent_sessions`, and `project_resources`. The `get_or_create_chat_session` RPC already handles `project_id` scoping with null-safe matching. The `project_resources` table has a full backend service in `cross_platform_synthesizer.py` with resource mapping, auto-discovery, and context assembly.

**Zero rows.** Zero API routes. Zero frontend. The `project_tools.py` TP tools import from a non-existent `routes/projects.py`. It's a complete ghost entity — architecturally sound, never activated.

This was initially considered as the scoping entity (projects already have FKs on sessions, deliverables, and resources — exactly what ADR-087 v1 proposed to add via `deliverable_id`). But activating `projects` means building a new product surface: routes, CRUD UI, user education on what a "project" is, and an "assign deliverable to project" flow. That's architectural purity — the right container, but the wrong sequencing for validating whether scoped context improves output quality.

### 13.2 Why the Filesystem Analogy Is Already Strong

The fixation on replicating Claude Code's filesystem pattern comes from observing that both Claude Code and OpenClaw use files-on-disk for context. But the power of those systems isn't the filesystem itself — it's the **coherence between the tool substrate and the state substrate**:

- Claude Code: tools operate on files → context stored in files. Coherent.
- OpenClaw: tools operate on files → context stored in files. Coherent.
- YARNNN: tools operate on database records → context stored in database records. **Also coherent.**

YARNNN's primitives (Read, Write, Edit, List, Search, Execute, Todo, Respond, Clarify) operate on Supabase tables, not filesystem paths. When TP uses `Search(scope="platform_content")`, it queries Postgres. Storing context as markdown files on disk would break this coherence — the agent couldn't read its own context with its own tools without a new primitive.

The `work_context` JSONB field is a **database-native file**. It's one structured blob that:
- TP can read (via working memory injection at session start — same as Claude Code reading CLAUDE.md)
- TP can write (via memory extraction or explicit instruction — same as Claude Code updating MEMORY.md)
- Headless agent can read (injected into system prompt — same as OpenClaw's `resolveBootstrapContextForRun()`)
- User can read and edit (via deliverable detail page — same as a user editing CLAUDE.md in their editor)

The JSONB field IS the file. It's stored in Postgres because that's where YARNNN's tools operate. The filesystem analogy is strong in principle; it doesn't need to be literal.

### 13.3 Deliverables as YARNNN's Unit of Work

The codebase audit confirms that a deliverable already carries everything an agent needs to do a job:

```
deliverable row (existing)
├── What to produce:     title, deliverable_type, template_structure
├── Where to get input:  sources JSONB
├── When to run:         schedule, next_run_at
├── What triggers it:    trigger_type, trigger_config (via event_triggers.py)
├── Where to send:       destination, destinations
├── What was produced:   deliverable_versions (child table)
├── What triggered it:   origin (user_configured | analyst_suggested | signal_emergent)
└── [MISSING]            work_context — what the agent knows about this work
```

Adding `work_context` completes the deliverable as a self-contained work unit. This maps to OpenClaw's workspace directory, but flattened into a row:

| OpenClaw workspace file | YARNNN deliverable field |
|---|---|
| MEMORY.md | `work_context` (accumulated context) |
| HEARTBEAT.md | `schedule` + `trigger_config` |
| AGENTS.md | `template_structure` + `type_config` (type-specific instructions) |
| USER.md | Global `user_context` (injected via working memory) |
| Workspace dir listing | `sources` JSONB (which platform resources feed this work) |

### 13.4 Two Separated Tracks

The analysis surfaced two orthogonal concerns that were previously entangled:

**Track A: Data Model — where scoped context lives**

This is the deliverable `work_context` question. The incremental path:

1. **v2 (now):** `work_context` JSONB on deliverables + `mode` column + `chat_sessions.deliverable_id` as routing key. Validates whether scoped context improves output quality. 1-2 columns, minimal wiring.
2. **D2 (if JSONB gets unwieldy):** Factor `work_context` into typed `workspace_files` rows. One new table. Extensible. Per-file concurrent writes. Data migration: split JSONB sections into rows.
3. **D3 (if workspace ≠ deliverable):** Promote workspace to its own entity (or activate the existing `projects` table). Move sources from deliverable to workspace. Add `workspace_id` to deliverables and sessions. This is when N:1 workspace:deliverable becomes a real need.

Each step validates before committing to the next level of structural investment.

**Track B: Execution Architecture — how inputs flow and get serialized**

This is the gateway + Lane Queue question. It's orthogonal to where context lives.

YARNNN already has all five of OpenClaw's input types:

| Input | OpenClaw | YARNNN (exists today) |
|---|---|---|
| Messages | Gateway → Lane Queue | `POST /chat` → `get_or_create_session()` → TP agent loop (15 rounds) |
| Heartbeats | HEARTBEAT.md → scheduled prompt | `unified_scheduler.py` → `execute_deliverable_generation()` (5 min check) |
| Crons | Cron config | `platform_sync_scheduler.py` (tier-based), `unified_scheduler.py` (nightly memory, signals) |
| Hooks | File change / event triggers | `webhooks.py` → Slack events, Gmail push → `event_triggers.py` → immediate execution |
| Webhooks | Inbound HTTP | `POST /webhooks/slack/events`, `POST /webhooks/gmail/push`, MCP tool calls |

What's missing is the **Lane Queue** — serialization of work per deliverable. Today, if a Slack webhook triggers deliverable generation while the user is chatting about that same deliverable, they run concurrently with no coordination. With one user and temporal separation, this is safe. With `work_context` writes from both paths, it becomes a real concurrency concern.

A future ADR should address:
- Unified input routing (gateway pattern — not for today, but for when more input channels exist)
- Per-deliverable work serialization (Lane Queue — needed when concurrent `work_context` writes become real)
- This is infrastructure, not data modeling — it shouldn't block v2

### 13.5 Agent Loop Audit

The audit confirmed YARNNN has a real, multi-round agent loop — not single-shot generation:

**Chat mode (TP):** 15-round observe→think→act loop. `chat_completion_stream_with_tools()` in `anthropic.py`. Claude gets tools, uses them, sees results, decides whether to continue. Full primitives (Read, Write, Edit, Search, Execute, Todo, etc.). Streaming.

**Headless mode (deliverable generation):** 2-6 round agent loop, binding-aware (`generate_draft_inline()` in `deliverable_execution.py`). Read-only primitives (Search, Read, List, WebSearch, GetSystemState). Non-streaming.

| Binding | Max rounds | Rationale |
|---|---|---|
| `platform_bound` | 2 | Single platform, context already gathered |
| `cross_platform` | 3 | Multiple sources, may need to search |
| `research` | 6 | Web research, needs investigation loops |
| `hybrid` | 6 | Platform + web |

This is equivalent to Claude Code's agentic loop and OpenClaw's Agent Runner. The agent loop is not the gap.

### 13.6 Existing Event-Driven Paths (Already "Alive")

The "proactive and alive" feeling depends on whether these existing paths are activated:

1. **Slack Events API webhook** (`POST /webhooks/slack/events`) — @mentions, messages, reactions → matches to deliverables with `trigger_type='event'` → immediate `execute_deliverable_generation()`. A hook triggering a heartbeat.
2. **Gmail Push Notifications** (`POST /webhooks/gmail/push`) — new emails → same event matching → immediate execution.
3. **Signal Processing** (hourly via `unified_scheduler.py`) — reads accumulated `platform_content`, runs Haiku LLM reasoning, can create *new deliverables* with `origin=signal_emergent`. The most autonomous feature — the system notices something and proactively creates work.
4. **Event trigger system** (`event_triggers.py`) — platform-specific matching with cooldown tracking via `event_trigger_log`. Per-thread, per-channel, per-sender, and global cooldowns prevent duplicate triggering.

The architecture for "alive" exists. Whether it's activated depends on: Slack app Events API configured, Gmail Pub/Sub topic set up, signal processing enabled (Starter+ tier), deliverables with `trigger_type='event'` created. If these are wired, YARNNN is already doing what OpenClaw does with hooks and heartbeats.

### 13.7 Answers to Open Questions (11.9 + 12.9)

**Q8 (Concurrency on deliverable writes):** TP chat and headless execution CAN run concurrently today — there's no serialization. In practice they don't overlap: headless runs on a schedule (every 5 min check), TP runs when the user is chatting. With `work_context` JSONB, concurrent writes would be last-write-wins on the whole blob. This is safe for now (temporal separation). Would need a Lane Queue for true concurrent multi-user scenarios.

**Q9 (Session summary accumulation):** Yes, `work_context.session_summaries` is the natural accumulation layer. Nightly cron generates session summaries (already running — ADR-067 Phase 1 complete), and for sessions with `deliverable_id` set, appends the summary to `work_context` instead of (or in addition to) writing to `chat_sessions.summary`. This gives the deliverable a narrative that grows over time, like OpenClaw's daily logs.

**Q10 (Bootstrap context size budget):** The 2000-token working memory budget is declared but NOT enforced — `estimate_working_memory_tokens()` is dead code. Adding `work_context` needs a sub-allocation with active truncation. Proposed: cap `work_context` injection at ~500 tokens. The compaction strategy (summarize old session summaries, prune stale patterns) keeps it within budget. This parallels session compaction (ADR-067) but for the context document.

### 13.8 Updated v2 Implementation Path

Based on consolidation of v1-v4 analysis, the confirmed implementation:

**Phase 1: work_context + session routing (backend)**

Schema:
- `ALTER TABLE deliverables ADD COLUMN work_context JSONB DEFAULT '{}'`
- `ALTER TABLE deliverables ADD COLUMN mode TEXT DEFAULT 'recurring'`
- `ALTER TABLE chat_sessions ADD COLUMN deliverable_id UUID REFERENCES deliverables(id) ON DELETE SET NULL`

Wiring:
- `POST /chat`: Extract `deliverable_id` from `surface_context`, pass to `get_or_create_session()`, pass to `build_working_memory()`
- `build_working_memory()`: When deliverable provided, include `work_context` in output (new section: "About this deliverable")
- `chat_sessions.deliverable_id`: Set on session creation as routing key for summary compaction

What does NOT change: `user_context` table (no FK, no partial indexes, no constraint changes), session creation RPC (no parameter changes — deliverable_id set after session creation or via simple INSERT), `_write_memory()` signature.

**Phase 2: TP↔headless bridge + write paths (backend)**

- `_build_headless_system_prompt()`: Include `deliverable.work_context` (already loaded — it's on the deliverable dict)
- `process_feedback()`: Write feedback patterns to `work_context` instead of `user_context`
- Nightly cron: For sessions with `deliverable_id`, append session summary to `work_context.session_summaries`

**Phase 3: Frontend + goal mode**

- Deliverable detail page: context panel (view/edit `work_context`), scoped chat
- Mode selector on creation (recurring vs goal)
- Goal mode UI: progress, milestones, no schedule

**Phase 4: Memory extraction scoping**

- `process_conversation()`: Route deliverable-specific facts to `work_context`, global facts to `user_context`
- Extraction prompt: scope awareness, version bump per Prompt Change Protocol

### 13.9 Summary

The analysis evolved through five versions:

- **v1:** FK-scoping — correct problem, wrong paradigm (relational thinking wearing filesystem hat)
- **v2:** Context document — `work_context` JSONB as per-deliverable CLAUDE.md
- **v3:** Typed workspace files — extensible but premature (validate value before building structure)
- **v4:** OpenClaw comparison — validates YARNNN's existing capabilities (agent loop, webhooks, signals), reveals Lane Queue gap
- **v5:** Consolidation — separates data model (Track A) from execution architecture (Track B), resolves filesystem fixation (coherence between tool substrate and state substrate, not literal file replication), confirms v2 as implementation path

The deliverable is YARNNN's unit of work. `work_context` completes it. The filesystem analogy is strong in principle — YARNNN's database-native tools and database-native state are coherent, just as Claude Code's file-native tools and file-native state are coherent. The gateway/Lane Queue concern is real but orthogonal and future-facing.

**Decision: Proceed with v2 (ADR-087 rewrite). Separate gateway/Lane Queue into its own future ADR.**
