# ADR-196: `user_memory` Table Sunset

> **Status**: Proposed (2026-04-19). Targeted for implementation in the same commit cycle as this ADR.
> **Date**: 2026-04-19
> **Authors**: KVK, Claude
> **Extends**: FOUNDATIONS v5.1 Axiom 0 (filesystem is the substrate), ADR-059 (Simplified Context Model), ADR-106 (Agent Workspace Architecture), ADR-156 (Composer Sunset — in-session memory writes)
> **Triggered by**: Axiom 0 audit of FOUNDATIONS v5.1 identified `user_memory` as holding a legacy status (declared VESTIGIAL by code audit) that needs to be resolved under singular-implementation discipline.

---

## Context

### The legacy status

`user_memory` (migration 085, ADR-087) was the single key-value memory store that replaced four earlier knowledge tables (`knowledge_profile`, `knowledge_styles`, `knowledge_domains`, `knowledge_entries` — dropped by ADR-059).

ADR-156 (Composer Sunset, 2026-04-01) moved memory from batch-extracted-to-table to in-session-written-to-filesystem: YARNNN writes facts proactively via `UpdateContext(target="memory")` during conversation, which routes to `/workspace/memory/*.md` files via the `UserMemory` class (`api/services/workspace.py`).

Migration 102 (`user_memory_to_filesystem.sql`) backfilled existing rows into the filesystem. Since then, no production path writes to `user_memory`.

### Audit findings (2026-04-19)

A targeted audit identified the current state of `user_memory`:

**Writes to `user_memory` in production code: none.**
- `POST /user/memories` (`api/routes/memory.py:477`) routes to `UserMemory.add_note()` → `workspace_files` filesystem, NOT `user_memory`.
- `extract_from_text_to_user_memory()` (`api/services/memory.py:239`) has a legacy name but writes to `/memory/notes.md` in `workspace_files` (migrated per ADR-108).
- `api/services/primitives/write.py:152` (`WriteEntity(ref="memory:...")`) would route to `user_memory` via `TABLE_MAP["memory"]` — but this code path has **no live callers**. Chat primitives use `UpdateContext(target="memory")`, not raw entity writes.

**Reads from `user_memory` in production code: none.**
- `working_memory._get_user_memory_files_sync` (`working_memory.py:392`) reads `workspace_files` at `/memory/*`, not the table.
- `api/services/primitives/read.py:117,181`, `edit.py:331`, `list.py:152` reference `TABLE_MAP["memory"] = "user_memory"` — dead paths not exposed in the ADR-168 chat tool surface.

**Routes touching the table:**
- `api/routes/account.py:638` — account-deletion purge cascade.
- `api/routes/integrations.py:1484` — comment only.
- `api/scripts/purge_user_data.py:102,105` — ops script, delete-only.
- Test-only: `api/test_pipeline_e2e.py` — various assertions.

**Dual-source: no.** All writes and prompt-assembly reads go through `workspace_files`. Only dead entity-primitive paths still reference the table.

**Verdict: VESTIGIAL.** Safe to drop. Singular-implementation discipline says eliminate dead paths in the same commit as the drop.

### Why an ADR for a deletion

Under Axiom 0, any DB table that holds semantic content and has a filesystem replacement should be dropped as soon as its replacement is fully implemented. `user_memory` is exactly this case. The ADR exists to:

1. Document the VESTIGIAL verdict so future contributors don't re-introduce it.
2. Enumerate the code paths to strip in the same commit as the `DROP TABLE`.
3. Give the drop a canonical reference for the CHANGELOG and migration file.

---

## Decision

### 1. Drop `user_memory` table

Migration 151 (same migration as ADR-195's `action_outcomes` drop):

```sql
DROP TABLE IF EXISTS user_memory CASCADE;
```

Zero-row impact: the table has been write-dead since ADR-156 (2026-04-01, ~3 weeks) and read-dead for prompt assembly since the same date.

### 2. Strip dead primitive branches

Remove the `memory` and `domain` entries from `TABLE_MAP` in `api/services/primitives/refs.py` and delete the corresponding branches across the entity primitives.

**Files touched:**
- `api/services/primitives/refs.py` — remove `"memory"` + `"domain"` keys from `TABLE_MAP` (line 160–162)
- `api/services/primitives/read.py` — delete `memory`/`domain` branches around line 117, 181
- `api/services/primitives/write.py` — delete `memory`/`domain` branch around line 152
- `api/services/primitives/edit.py` — delete `memory`/`domain` branch around line 331
- `api/services/primitives/list.py` — delete `memory`/`domain` branch around line 152
- `api/services/primitives/search.py` — delete any remaining `memory`/`domain` references

**Why `domain` too:** `TABLE_MAP["domain"]` pointed to `knowledge_domains`, one of the four tables dropped by ADR-059. The reference has been orphaned since then; stripping it alongside `memory` is a free cleanup.

### 3. Strip purge-cascade references

- `api/routes/account.py` — remove the `user_memory` delete from the account-deletion cascade (line 638).
- `api/scripts/purge_user_data.py` — remove `user_memory` from the purge list (lines 102, 105).

### 4. Update test fixtures if needed

`api/test_pipeline_e2e.py` references `user_memory` in several places. Audit and remove any that assert against the table's existence. Replace with assertions against `workspace_files` under `/memory/`.

### 5. No filesystem change

The `/workspace/memory/*.md` path is already the authoritative store. No migration needed on the filesystem side — data already landed there via migration 102.

---

## Migration plan

Single commit (Commit 3 of this cycle):

1. Migration 151: `DROP TABLE action_outcomes CASCADE; DROP TABLE user_memory CASCADE;` (both drops in one migration file — both are Axiom 0 cleanups, both have zero live dependents).
2. Strip `TABLE_MAP` entries + dead primitive branches.
3. Update `routes/account.py` and `scripts/purge_user_data.py`.
4. Update test fixtures.
5. Apply migration via psql (per `docs/database/ACCESS.md`).
6. Smoke-test: import `services.primitives.{read,write,edit,list,search}`; assert no module-level errors.

---

## Impact table (per ADR-191 matrix gate)

| Domain | Impact | Notes |
|--------|--------|-------|
| **E-commerce** | Neutral | Memory writes already go through filesystem. No behavior change. |
| **Day trader** | Neutral | Same as above. |
| **AI influencer** | Neutral | Same as above. |
| **International trader** | Neutral | Same as above. |

**Cross-domain benefit (not a per-domain impact):** the deletion removes one of the remaining Axiom 0 violations identified in the v5.1 audit. Every future ADR reviewer can cite this one as proof that cleanup follows principle.

Gate passes trivially — no domain harmed.

---

## Verification (after Commit 3 lands)

- `\d user_memory` in psql returns "Did not find any relation".
- `grep -rn "user_memory" api/services/ api/routes/` returns only tests or comments referencing history.
- `grep -rn "TABLE_MAP\[.memory.\]" api/` returns nothing.
- `python3 -c "from services.primitives import read, write, edit, list_, search"` imports cleanly.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-19 | v1 — Initial and (expected) final. VESTIGIAL verdict ratified. Migration 151 targeted to drop `user_memory` alongside `action_outcomes` (ADR-195 v2). Dead entity-primitive branches (`memory`, `domain`) stripped in the same commit. |
